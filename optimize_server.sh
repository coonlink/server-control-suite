#!/bin/bash

# Глобальные переменные
LOG_DIR="/var/log"
MAX_LOG_SIZE_MB=100
DATE=$(date '+%Y-%m-%d_%H-%M-%S')
OPTIMIZE_LOG="/var/log/optimize_server.log"
CONFIG_FILE="/root/critical_processes_config.sh"

# Загружаем конфигурацию
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
else
  echo "Конфигурационный файл $CONFIG_FILE не найден. Используем значения по умолчанию."
  # Базовые значения по умолчанию
  LOAD_THRESHOLD=5.0
  CPU_CRITICAL=80.0
  MEM_CRITICAL=80.0
  DISK_CRITICAL=90.0
  CPU_LIMIT_NORMAL=30
  CPU_LIMIT_STRICT=15
  CPU_LIMIT_CRITICAL=5
fi

log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $OPTIMIZE_LOG
}

# Записываем начало выполнения
log_message "=== Начало оптимизации сервера ==="

# Функция для проверки нагрузки
check_load() {
  LOAD=$(cat /proc/loadavg | cut -d' ' -f1)
  if (( $(echo "$LOAD > $LOAD_THRESHOLD" | bc -l) )); then
    return 0  # нагрузка высокая
  else
    return 1  # нагрузка нормальная
  fi
}

# Функция для отправки уведомления в Telegram при критической нагрузке
send_alert() {
  local load=$(cat /proc/loadavg | cut -d' ' -f1)
  local mem_usage=$(free -m | awk 'NR==2{printf "%.2f", $3*100/$2}')
  local disk_usage=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
  
  # Собираем информацию о топ процессах
  local top_processes=$(ps aux --sort=-%cpu | head -6)
  
  # Формируем сообщение
  local message="🚨 <b>КРИТИЧЕСКАЯ НАГРУЗКА НА СЕРВЕРЕ!</b> 🚨
  
📊 <b>Показатели:</b>
- Нагрузка: $load (порог: $LOAD_THRESHOLD)
- Использование памяти: ${mem_usage}% (порог: $MEM_CRITICAL%)
- Использование диска: ${disk_usage}% (порог: $DISK_CRITICAL%)

🔄 <b>Топ процессы:</b>
<pre>$(echo "$top_processes" | head -1)
$(echo "$top_processes" | tail -n +2 | head -5)</pre>

🕐 Время: $(date '+%Y-%m-%d %H:%M:%S')

🔧 Автоматическая оптимизация применена. Возможно потребуется ручное вмешательство."

  # Отправляем уведомление
  if type send_telegram_notification &>/dev/null; then
    log_message "Отправляем уведомление в Telegram о критической нагрузке"
    send_telegram_notification "$message"
  else
    log_message "Функция отправки в Telegram недоступна. Проверьте конфигурацию."
  fi
}

# Функция для проверки и остановки крупных процессов
check_and_handle_heavy_processes() {
  log_message "Проверяем ресурсоемкие процессы..."
  
  # Получаем топ-10 процессов по CPU
  TOP_CPU_PROCESSES=$(ps aux --sort=-%cpu | head -11)
  log_message "Топ процессы по CPU:"
  echo "$TOP_CPU_PROCESSES" | tee -a $OPTIMIZE_LOG
  
  # Получаем топ-10 процессов по памяти
  TOP_MEM_PROCESSES=$(ps aux --sort=-%mem | head -11)
  log_message "Топ процессы по памяти:"
  echo "$TOP_MEM_PROCESSES" | tee -a $OPTIMIZE_LOG
  
  # Ограничиваем процессы с высоким потреблением CPU
  for i in {1..5}; do
    PID=$(ps aux --sort=-%cpu | awk -v line=$((i+1)) 'NR==line {print $2}')
    if [ -n "$PID" ]; then
      CPU_PERCENT=$(ps aux --sort=-%cpu | awk -v line=$((i+1)) 'NR==line {print $3}')
      COMM=$(ps -p $PID -o comm=)
      
      if (( $(echo "$CPU_PERCENT > 50" | bc -l) )); then
        log_message "Обнаружен тяжелый процесс: $COMM (PID: $PID) с CPU: $CPU_PERCENT%"
        
        # Проверяем тип процесса используя функции из конфига
        if type is_critical_process &>/dev/null && is_critical_process "$COMM"; then
          log_message "Процесс $COMM является критичным, ограничиваем до $CPU_LIMIT_NORMAL% CPU"
          cpulimit -p $PID -l $CPU_LIMIT_NORMAL -b 2>/dev/null
        elif type is_limitable_process &>/dev/null && is_limitable_process "$COMM"; then
          log_message "Ограничиваем процесс $COMM (PID: $PID) до $CPU_LIMIT_STRICT% CPU"
          cpulimit -p $PID -l $CPU_LIMIT_STRICT -b 2>/dev/null
        elif type is_stoppable_process &>/dev/null && is_stoppable_process "$COMM"; then
          log_message "Останавливаем процесс $COMM (PID: $PID)"
          kill $PID 2>/dev/null
        else
          # Если функций из конфига нет, используем старую логику
          if echo "$COMM" | grep -qE 'nginx|sshd|systemd|mysql|postgres|docker'; then
            log_message "Процесс $COMM является критичным, ограничиваем до 30% CPU"
            cpulimit -p $PID -l 30 -b 2>/dev/null
          else
            log_message "Ограничиваем процесс $COMM (PID: $PID) до 15% CPU"
            cpulimit -p $PID -l 15 -b 2>/dev/null
            
            # Если процесс явно не нужен, останавливаем его
            if echo "$COMM" | grep -qE 'chrome|rg|find|grep'; then
              log_message "Останавливаем ненужный процесс $COMM (PID: $PID)"
              kill $PID 2>/dev/null
            fi
          fi
        fi
      fi
    fi
  done
  
  # Ограничиваем процессы с высоким потреблением памяти
  for i in {1..5}; do
    PID=$(ps aux --sort=-%mem | awk -v line=$((i+1)) 'NR==line {print $2}')
    if [ -n "$PID" ]; then
      MEM_PERCENT=$(ps aux --sort=-%mem | awk -v line=$((i+1)) 'NR==line {print $4}')
      COMM=$(ps -p $PID -o comm=)
      
      if (( $(echo "$MEM_PERCENT > 30" | bc -l) )); then
        log_message "Обнаружен процесс с высоким потреблением памяти: $COMM (PID: $PID) с MEM: $MEM_PERCENT%"
        
        # Проверяем тип процесса с помощью функций из конфига
        if type is_critical_process &>/dev/null && is_critical_process "$COMM"; then
          log_message "Процесс $COMM является критичным, перезапускаем его"
          if systemctl list-unit-files | grep -q "$COMM"; then
            systemctl restart $COMM 2>/dev/null
          fi
        elif type is_stoppable_process &>/dev/null && is_stoppable_process "$COMM"; then
          log_message "Останавливаем процесс с высоким потреблением памяти: $COMM (PID: $PID)"
          kill $PID 2>/dev/null
        else
          # Если функций из конфига нет, используем старую логику
          if echo "$COMM" | grep -qE 'nginx|sshd|systemd|mysql|postgres'; then
            log_message "Процесс $COMM является критичным, перезапускаем его"
            if systemctl list-unit-files | grep -q "$COMM"; then
              systemctl restart $COMM 2>/dev/null
            fi
          else
            log_message "Останавливаем процесс с высоким потреблением памяти: $COMM (PID: $PID)"
            kill $PID 2>/dev/null
          fi
        fi
      fi
    fi
  done
}

# Проверка установленных библиотек и зависимостей
check_dependencies() {
  log_message "Проверяем установленные библиотеки и зависимости..."
  
  # Проверяем наличие необходимых утилит
  for cmd in cpulimit bc docker systemctl curl; do
    if ! command -v $cmd &> /dev/null; then
      log_message "ВНИМАНИЕ: Утилита $cmd не установлена. Устанавливаем..."
      apt-get update && apt-get install -y $cmd 2>/dev/null || yum install -y $cmd 2>/dev/null
    fi
  done
  
  # Проверяем наличие ошибок в логах
  log_message "Проверяем логи на наличие ошибок..."
  ERROR_LOGS=$(grep -i "error\|failed\|warning" /var/log/syslog /var/log/messages /var/log/dmesg 2>/dev/null | tail -n 50)
  if [ -n "$ERROR_LOGS" ]; then
    log_message "Обнаружены ошибки в системных логах:"
    echo "$ERROR_LOGS" | tee -a $OPTIMIZE_LOG
  fi
}

# Останавливаем неиспользуемые процессы Chrome
log_message "Останавливаем неиспользуемые процессы Chrome..."
pkill chrome 2>/dev/null

# Останавливаем процессы поиска ripgrep
log_message "Останавливаем процессы поиска ripgrep..."
pkill rg 2>/dev/null

# Ограничиваем потребление CPU для процессов Node.js
log_message "Ограничиваем потребление CPU для процессов Node.js..."
for pid in $(ps aux | grep node | grep -v grep | awk '{print $2}'); do
  cpulimit -p $pid -l $CPU_LIMIT_NORMAL -b 2>/dev/null
done

# Ограничиваем потребление CPU для Python процессов
log_message "Ограничиваем потребление CPU для Python процессов..."
for pid in $(ps aux | grep python | grep -v grep | awk '{print $2}'); do
  cpulimit -p $pid -l $CPU_LIMIT_NORMAL -b 2>/dev/null
done

# Проверяем и очищаем большие лог-файлы
log_message "Проверяем и очищаем большие лог-файлы..."
find /home -name "*.log" -size +${MAX_LOG_SIZE_MB}M -type f | while read file; do
  log_message "Архивирую большой лог-файл: $file"
  cp "$file" "${file}.${DATE}.bak"
  echo "Log rotated on ${DATE}" > "$file"
done

# Очищаем кэш памяти
log_message "Очищаем кэш памяти..."
sync && echo 3 > /proc/sys/vm/drop_caches

# Управление clamd процессом, который потребляет много памяти
log_message "Проверяем потребление памяти процессом clamd..."
CLAMD_MEM_PERCENT=$(ps aux | grep clamd | grep -v grep | awk '{print $4}' | head -1)
if [ -n "$CLAMD_MEM_PERCENT" ]; then
  if (( $(echo "$CLAMD_MEM_PERCENT > 20" | bc -l) )); then
    log_message "clamd потребляет ${CLAMD_MEM_PERCENT}% памяти, останавливаем контейнер..."
    docker stop mailcowdockerized-clamd-mailcow-1 >/dev/null 2>&1
    log_message "Ожидаем 30 секунд перед перезапуском clamd с ограничением памяти..."
    sleep 30
    log_message "Перезапускаем clamd с ограничением памяти..."
    docker start mailcowdockerized-clamd-mailcow-1 >/dev/null 2>&1
    docker update --memory=256m --memory-swap=384m mailcowdockerized-clamd-mailcow-1 >/dev/null 2>&1
  fi
fi

# Первая проверка тяжелых процессов
check_and_handle_heavy_processes

# Проверка зависимостей
check_dependencies

# Ждем и проверяем, снизилась ли нагрузка
log_message "Ожидаем 60 секунд для проверки эффективности оптимизации..."
sleep 60

# Проверяем текущую нагрузку
INITIAL_LOAD=$(cat /proc/loadavg | cut -d' ' -f1)
log_message "Текущая нагрузка после первой оптимизации: $INITIAL_LOAD"

# Если нагрузка все еще высокая, применяем более строгие меры
if check_load; then
  log_message "Нагрузка все еще высокая, применяем более строгие меры..."
  
  # Отправляем уведомление в Telegram о критической нагрузке
  send_alert
  
  # Вторая проверка тяжелых процессов с более строгими ограничениями
  for i in {1..10}; do
    PID=$(ps aux --sort=-%cpu | awk -v line=$((i+1)) 'NR==line {print $2}')
    if [ -n "$PID" ]; then
      COMM=$(ps -p $PID -o comm=)
      CPU_PERCENT=$(ps aux --sort=-%cpu | awk -v line=$((i+1)) 'NR==line {print $3}')
      
      log_message "Строгое ограничение для процесса $COMM (PID: $PID) с CPU: $CPU_PERCENT%"
      
      # Используем функции из конфига если доступны
      if type is_critical_process &>/dev/null && type is_stoppable_process &>/dev/null; then
        if is_stoppable_process "$COMM"; then
          log_message "Останавливаем некритичный процесс $COMM (PID: $PID)"
          kill -15 $PID 2>/dev/null
        elif is_critical_process "$COMM"; then
          log_message "Строго ограничиваем критичный процесс $COMM (PID: $PID) до $CPU_LIMIT_CRITICAL% CPU"
          cpulimit -p $PID -l $CPU_LIMIT_CRITICAL -b 2>/dev/null
        else 
          log_message "Ограничиваем процесс $COMM (PID: $PID) до $CPU_LIMIT_STRICT% CPU"
          cpulimit -p $PID -l $CPU_LIMIT_STRICT -b 2>/dev/null
        fi
      else
        # Используем старую логику если функций нет
        if ! echo "$COMM" | grep -qE 'nginx|sshd|systemd|mysql|postgres|docker|bash|sh'; then
          log_message "Останавливаем некритичный процесс $COMM (PID: $PID)"
          kill -15 $PID 2>/dev/null
        else
          # Иначе сильно ограничиваем
          log_message "Строго ограничиваем критичный процесс $COMM (PID: $PID) до 5% CPU"
          cpulimit -p $PID -l 5 -b 2>/dev/null
        fi
      fi
    fi
  done
  
  # Останавливаем некритичные сервисы
  log_message "Останавливаем некритичные сервисы..."
  for service in nginx apache2 cron atd cups bluetooth; do
    # Проверяем, является ли сервис критичным согласно конфигурации
    if type is_critical_process &>/dev/null && is_critical_process "$service"; then
      log_message "Сервис $service отмечен как критичный, не останавливаем"
      continue
    fi
    
    if systemctl is-active $service &>/dev/null; then
      log_message "Останавливаем сервис $service"
      systemctl stop $service 2>/dev/null
    fi
  done
  
  # Ждем и проверяем снова
  log_message "Ожидаем 60 секунд после строгих мер..."
  sleep 60
  
  # Проверяем нагрузку снова
  FINAL_LOAD=$(cat /proc/loadavg | cut -d' ' -f1)
  log_message "Нагрузка после строгих мер: $FINAL_LOAD"
  
  # Если нагрузка снизилась, запускаем некоторые сервисы обратно
  if ! check_load; then
    log_message "Нагрузка снизилась, запускаем критичные сервисы..."
    systemctl start nginx 2>/dev/null
  else
    log_message "Нагрузка все еще высокая! Выполняем полную проверку системы..."
    
    # Отправляем второе уведомление с полной диагностикой
    DISK_INFO=$(df -h)
    NET_INFO=$(netstat -tuln | head -20)
    
    if type send_telegram_notification &>/dev/null; then
      log_message "Отправляем расширенное уведомление в Telegram"
      send_telegram_notification "🚨 <b>КРИТИЧЕСКАЯ СИТУАЦИЯ ПРОДОЛЖАЕТСЯ!</b> 🚨
      
📊 <b>Нагрузка остается высокой:</b> $FINAL_LOAD

💾 <b>Диски:</b>
<pre>$(echo "$DISK_INFO" | head -6)</pre>

🌐 <b>Сеть:</b>
<pre>$(echo "$NET_INFO" | head -10)</pre>

⚠️ <b>ТРЕБУЕТСЯ РУЧНОЕ ВМЕШАТЕЛЬСТВО</b>"
    fi
    
    # Проверяем диски
    log_message "Проверяем состояние дисков..."
    df -h | tee -a $OPTIMIZE_LOG
    
    # Проверяем сетевые соединения
    log_message "Проверяем сетевые соединения..."
    netstat -tuln | tee -a $OPTIMIZE_LOG
    
    # Проверяем открытые файлы
    log_message "Проверяем количество открытых файлов..."
    lsof | wc -l | tee -a $OPTIMIZE_LOG
    
    # Проверяем запущенные контейнеры Docker
    if command -v docker &> /dev/null; then
      log_message "Проверяем контейнеры Docker..."
      docker stats --no-stream | tee -a $OPTIMIZE_LOG
    fi
    
    # Последняя мера - перезагрузка некритичных сервисов
    log_message "Перезапускаем некритичные сервисы..."
    systemctl daemon-reload
    systemctl restart cron atd 2>/dev/null
  fi
fi

# Более строгое ограничение для ночного времени
HOUR=$(date +%H)
if [ $HOUR -ge $NIGHT_START ] && [ $HOUR -lt $NIGHT_END ]; then
  # Ночное время - более строгие ограничения
  log_message "Ночное время - применяем строгие ограничения ресурсов"
  for pid in $(ps aux | grep node | grep -v grep | awk '{print $2}'); do
    cpulimit -p $pid -l $NIGHT_CPU_LIMIT -b 2>/dev/null
  done
  
  # Временно остановить clamd на ночь
  log_message "Ночное время - останавливаем clamd до утра"
  docker stop mailcowdockerized-clamd-mailcow-1 >/dev/null 2>&1
fi

log_message "=== Завершение оптимизации сервера ==="
log_message "Итоговая нагрузка: $(cat /proc/loadavg)"
log_message "Использование памяти: $(free -h)"

# В конец скрипта
STATS_FILE="/var/log/performance_stats.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') $(cat /proc/loadavg | cut -d' ' -f1-3) $(free -m | awk 'NR==2 {print $3}')" >> $STATS_FILE
