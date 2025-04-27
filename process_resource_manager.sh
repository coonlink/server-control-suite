#!/bin/bash

# Скрипт для мониторинга процессов, выделения ресурсов и очистки
CONFIG_FILE="/root/critical_processes_config.sh"
LOG_FILE="/var/log/process_resource_manager.log"
CGROUP_DIR="/sys/fs/cgroup"
PROCESS_LIST_FILE="/root/managed_processes.conf"

# Загружаем конфигурацию, если она существует
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
fi

# Функция логирования
log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log_message "=== Запуск менеджера ресурсов процессов ==="

# Создаем файл конфигурации управляемых процессов, если он не существует
if [ ! -f "$PROCESS_LIST_FILE" ]; then
  cat > "$PROCESS_LIST_FILE" << EOF
# Формат: имя_процесса:лимит_памяти_мб:лимит_диска_мб:директория_для_очистки
# Пример:
# mysql:1024:2048:/var/lib/mysql/tmp
# apache2:512:1024:/var/www/cache
# node:256:512:/tmp/node_cache
EOF
  log_message "Создан шаблон конфигурации процессов: $PROCESS_LIST_FILE"
  log_message "Отредактируйте файл $PROCESS_LIST_FILE, чтобы добавить процессы для управления"
  exit 0
fi

# Проверяем наличие необходимых инструментов
check_tools() {
  for cmd in cgroup-tools cgcreate cgexec cgdelete inotify-tools; do
    if ! command -v $cmd &> /dev/null; then
      log_message "ВНИМАНИЕ: Не установлен инструмент $cmd. Устанавливаем..."
      apt-get update && apt-get install -y $cmd 2>/dev/null || {
        log_message "Ошибка: Не удалось установить $cmd. Проверьте вручную."
        exit 1
      }
    fi
  done
}

# Функция для настройки cgroup для процесса
setup_cgroup() {
  local process_name=$1
  local mem_limit=$2
  local pid=$3
  
  if [ -d "$CGROUP_DIR/memory" ]; then
    # Используем cgroup v1
    cgcreate -g memory,cpu:/$process_name
    echo "$mem_limit"M > $CGROUP_DIR/memory/$process_name/memory.limit_in_bytes
    
    if [ -n "$pid" ]; then
      echo $pid > $CGROUP_DIR/memory/$process_name/tasks
      echo $pid > $CGROUP_DIR/cpu/$process_name/tasks
    fi
    
    log_message "Настроен cgroup для $process_name с лимитом памяти ${mem_limit}MB (PID: $pid)"
  elif [ -d "$CGROUP_DIR/system.slice" ]; then
    # Используем cgroup v2
    systemd-run --unit="$process_name" --scope -p MemoryLimit="${mem_limit}M" --remain-after-exit
    log_message "Настроен systemd slice для $process_name с лимитом памяти ${mem_limit}MB"
  else
    log_message "Ошибка: Не удалось определить версию cgroup"
    return 1
  fi
  
  return 0
}

# Функция для выделения места на диске (создание ограниченного tmpfs)
allocate_disk_space() {
  local process_name=$1
  local disk_limit=$2
  local directory=$3
  
  if [ ! -d "$directory" ]; then
    mkdir -p "$directory"
  fi
  
  mount -t tmpfs -o size=${disk_limit}M tmpfs "$directory"
  log_message "Выделено ${disk_limit}MB дискового пространства для $process_name в $directory"
}

# Функция для очистки ресурсов после завершения процесса
cleanup_resources() {
  local process_name=$1
  local directory=$2
  
  log_message "Процесс $process_name завершен. Начинаем очистку ресурсов..."
  
  # Очищаем cgroup
  if [ -d "$CGROUP_DIR/memory/$process_name" ]; then
    cgdelete -r memory,cpu:/$process_name
    log_message "Удален cgroup для $process_name"
  fi
  
  # Очищаем выделенное дисковое пространство
  if mountpoint -q "$directory"; then
    umount "$directory"
    log_message "Размонтирован tmpfs для $process_name"
  fi
  
  # Очищаем содержимое директории
  if [ -d "$directory" ]; then
    rm -rf "${directory:?}"/* 2>/dev/null
    log_message "Очищено содержимое директории $directory"
  fi
  
  # Отправляем уведомление в Telegram если функция доступна
  if type send_telegram_notification &>/dev/null; then
    local message="🧹 <b>Очистка ресурсов</b>\n\nПроцесс <code>$process_name</code> завершен.\nРесурсы очищены.\nДиректория: $directory"
    send_telegram_notification "$message"
  fi
}

# Функция для отслеживания запуска процесса
watch_process_start() {
  local process_name=$1
  local mem_limit=$2
  local disk_limit=$3
  local directory=$4
  
  # Цикл проверки запуска процесса
  while true; do
    pid=$(pgrep -f "$process_name" | head -1)
    
    if [ -n "$pid" ]; then
      log_message "Обнаружен запуск процесса $process_name (PID: $pid)"
      
      # Настраиваем cgroup
      setup_cgroup "$process_name" "$mem_limit" "$pid"
      
      # Выделяем дисковое пространство
      allocate_disk_space "$process_name" "$disk_limit" "$directory"
      
      # Ждем завершения процесса
      while kill -0 $pid 2>/dev/null; do
        sleep 5
      done
      
      # Процесс завершен, очищаем ресурсы
      cleanup_resources "$process_name" "$directory"
    fi
    
    sleep 10
  done
}

# Основная функция для запуска мониторинга
main() {
  check_tools
  
  # Читаем список процессов из файла конфигурации
  while IFS=: read -r process_name mem_limit disk_limit directory || [ -n "$process_name" ]; do
    # Пропускаем комментарии и пустые строки
    [[ $process_name =~ ^#.*$ || -z "$process_name" ]] && continue
    
    log_message "Настройка мониторинга для процесса: $process_name"
    log_message "  Лимит памяти: ${mem_limit}MB"
    log_message "  Лимит диска: ${disk_limit}MB"
    log_message "  Директория: $directory"
    
    # Запускаем мониторинг процесса в фоновом режиме
    watch_process_start "$process_name" "$mem_limit" "$disk_limit" "$directory" &
  done < "$PROCESS_LIST_FILE"
  
  # Ожидаем сигналы для завершения
  log_message "Менеджер ресурсов запущен и работает в фоновом режиме"
  log_message "Для остановки нажмите Ctrl+C"
  
  # Обработка сигнала завершения
  trap "log_message 'Остановка менеджера ресурсов...'; kill $(jobs -p) 2>/dev/null; exit 0" SIGINT SIGTERM
  
  # Ждем завершения
  wait
}

# Запускаем главную функцию
main 