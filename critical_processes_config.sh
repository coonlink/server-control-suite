#!/bin/bash

# Конфигурационный файл для критичных процессов и настроек оптимизации

# Check if TELEGRAM_BOT_TOKEN is set in environment, otherwise use default
if [ -z "${TELEGRAM_BOT_TOKEN}" ]; then
  # If environment variable is not set, try to read from .telegram_credentials
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
  CREDENTIALS_FILE="$SCRIPT_DIR/.telegram_credentials"
  
  if [ -f "$CREDENTIALS_FILE" ]; then
    source "$CREDENTIALS_FILE"
  fi
fi

# Check if TELEGRAM_CHAT_ID is set in environment, otherwise use default
if [ -z "${TELEGRAM_CHAT_ID}" ]; then
  # Get from .telegram_credentials if already sourced above
  # If not set, define authorized admins array
  if [ -z "${AUTHORIZED_ADMINS}" ]; then
    AUTHORIZED_ADMINS=("CHAT_ID_HERE")
  fi
fi

# Настройки пороговых значений
LOAD_THRESHOLD=${LOAD_THRESHOLD:-5.0}        # Порог высокой нагрузки
CPU_CRITICAL=80.0         # Критически высокое использование CPU в %
MEM_CRITICAL=${MEM_CRITICAL:-90}        # Критическое использование памяти в %
DISK_CRITICAL=${DISK_CRITICAL:-90}        # Критическое использование диска в %

# Уровни уведомлений
NOTIFICATION_LEVELS=(
  "critical"    # Критические уведомления (всегда отправляются)
  "warning"     # Предупреждения (отправляются в рабочее время)
  "info"        # Информационные (отправляются по расписанию)
)

# Расписание уведомлений
NOTIFICATION_SCHEDULE=(
  "critical:*:*:*:*"      # Критические - всегда
  "warning:9-18:*:*:1-5"  # Предупреждения - в рабочее время по будням
  "info:10,14,18:*:*:1-5" # Информационные - три раза в день по будням
)

# Список критичных процессов, которые НЕЛЬЗЯ останавливать
CRITICAL_PROCESSES=(
  "nginx"
  "sshd"
  "systemd"
  "mysql"
  "postgres"
  "docker"
  "bash"
  "sh"
  "python"
)

# Список процессов, которые можно ограничить, но не останавливать
LIMIT_PROCESSES=(
  "php-fpm"
  "apache2"
  "node"
  "python"
)

# Список процессов, которые можно останавливать в экстренных случаях
STOPPABLE_PROCESSES=(
  "chrome"
  "rg"
  "find"
  "grep"
  "clamd"
)

# Ограничения CPU для процессов
CPU_LIMIT_NORMAL=${CPU_LIMIT_NORMAL:-50}       # Нормальное ограничение CPU
CPU_LIMIT_STRICT=${CPU_LIMIT_STRICT:-30}       # Строгое ограничение CPU
CPU_LIMIT_CRITICAL=${CPU_LIMIT_CRITICAL:-10}      # Критическое ограничение CPU

# Ограничения памяти (в МБ)
MEM_LIMIT_NORMAL=1024    # Обычное ограничение памяти
MEM_LIMIT_STRICT=512     # Строгое ограничение памяти
MEM_LIMIT_CRITICAL=256   # Критическое ограничение памяти

# Настройки ночного режима
NIGHT_START=22            # Начало ночного времени (час)
NIGHT_END=7               # Конец ночного времени (час)
NIGHT_CPU_LIMIT=10        # Ночное ограничение CPU
NIGHT_MEM_LIMIT=256     # Ночное ограничение памяти

# Настройки автоматической очистки
CLEANUP_SCHEDULE="0 */4 * * *"  # Каждые 4 часа
MAX_LOG_SIZE=100M              # Максимальный размер лог-файлов
MAX_HISTORY_DAYS=7            # Хранить историю 7 дней

# Стандартный ответ неавторизованным пользователям
UNAUTHORIZED_RESPONSE="Sorry, I'm not a real bot, they just made me for backward compatibility. I can't really answer any questions."

# Скрипт для webhook, который будет получать сообщения
WEBHOOK_SCRIPT="/root/telegram_bot.sh"

# Не задавайте значение здесь! Используйте .telegram_credentials вместо этого.
# TELEGRAM_BOT_TOKEN будет загружен из файла в начале скрипта.
# TELEGRAM_BOT_TOKEN="your_bot_token_here"

# Функция проверки авторизации пользователя
is_authorized_user() {
  local user_id="$1"
  
  # Проверяем, что user_id не пустой
  if [ -z "$user_id" ]; then
    return 1
  fi
  
  for admin_id in "${AUTHORIZED_ADMINS[@]}"; do
    if [[ "$user_id" == "$admin_id" ]]; then
      return 0  # Пользователь авторизован
    fi
  done
  
  return 1  # Пользователь не авторизован
}

# Функция обработки входящих сообщений от Telegram
process_telegram_message() {
  local user_id="$1"
  local message="$2"
  
  if is_authorized_user "$user_id"; then
    # Пользователь авторизован, обрабатываем сообщение
    process_admin_command "$user_id" "$message"
  else
    # Пользователь не авторизован, отправляем стандартный ответ
    send_telegram_message "$user_id" "$UNAUTHORIZED_RESPONSE"
  fi
}

# Обработка команд от авторизованных пользователей
process_admin_command() {
  local user_id="$1"
  local message="$2"
  
  # Обработка различных команд от админов
  case "$message" in
    /status)
      # Отправить статус сервера
      server_status=$(check_server_status)
      send_telegram_message "$user_id" "$server_status"
      ;;
    /restart*)
      # Перезапустить сервис
      service_name=$(echo "$message" | awk '{print $2}')
      if [ -n "$service_name" ]; then
        result=$(systemctl restart "$service_name" 2>&1 || echo "Ошибка при перезапуске $service_name")
        send_telegram_message "$user_id" "Перезапуск $service_name: $result"
      else
        send_telegram_message "$user_id" "Укажите имя сервиса: /restart [service_name]"
      fi
      ;;
    /help)
      # Отправить справку по командам
      help_text="Доступные команды:
/status - проверить статус сервера
/restart [service] - перезапустить сервис
/optimize - запустить оптимизацию
/logs [service] - показать логи сервиса
/help - показать эту справку"
      send_telegram_message "$user_id" "$help_text"
      ;;
    *)
      # Неизвестная команда
      send_telegram_message "$user_id" "Неизвестная команда. Отправьте /help для списка команд."
      ;;
  esac
}

# Функция отправки сообщения конкретному пользователю Telegram
send_telegram_message() {
  local chat_id="$1"
  local message="$2"
  
  # Проверка параметров
  if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "ОШИБКА: Не задан токен бота Telegram"
    return 1
  fi
  
  if [ -z "$chat_id" ]; then
    echo "ОШИБКА: Не указан ID чата для отправки"
    return 1
  fi
  
  # Логируем отправляемое сообщение
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Отправка сообщения в чат $chat_id" >> /var/log/telegram_messages.log
  echo "--------------------" >> /var/log/telegram_messages.log
  echo "$message" >> /var/log/telegram_messages.log
  echo "--------------------" >> /var/log/telegram_messages.log
  
  # Отправляем сообщение
  response=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d chat_id="$chat_id" \
    -d text="$message" \
    -d parse_mode="HTML" \
    --connect-timeout 10 \
    --max-time 15)
  
  # Проверяем ответ от API Telegram
  if echo "$response" | grep -q '"ok":true'; then
    echo "Сообщение успешно отправлено в чат $chat_id"
    return 0
  else
    error_msg=$(echo "$response" | grep -o '"description":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    
    if [[ "$error_msg" == *"chat not found"* ]]; then
      echo "ОШИБКА: Пользователь с ID $chat_id не начал чат с ботом"
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] ОШИБКА: Пользователь с ID $chat_id не начал чат с ботом" >> /var/log/telegram_errors.log
    else
      echo "ОШИБКА при отправке сообщения: $response" 
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] ОШИБКА при отправке сообщения: $response" >> /var/log/telegram_errors.log
    fi
    
    return 1
  fi
}

# Функция отправки уведомления в Telegram
send_telegram_notification() {
  local message="$1"
  
  # Check if Telegram credentials are available
  if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "Ошибка: Не настроены учетные данные Telegram"
    return 1
  fi
  
  # Отправляем сообщение
  curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" \
    -d text="$message" \
    -d parse_mode="HTML" > /dev/null
}

# Функция для определения критичных процессов
is_critical_process() {
    local process_name="$1"
    
    # Список критичных для системы процессов
    if echo "$process_name" | grep -qE 'systemd|sshd|nginx|mysql|postgres|mariadb|docker|containerd|cron|udevd|rsyslog|fail2ban|supervisord'; then
        return 0  # Это критичный процесс
    fi
    
    # Добавляем проверку на критичные процессы вашего бота
    if echo "$process_name" | grep -qE 'python3|game_card_bot.py'; then
        return 0  # Это критичный процесс бота
    fi
    
    return 1  # Не критичный процесс
}

# Функция для определения процессов, которые можно ограничить
is_limitable_process() {
    local process_name="$1"
    
    # Процессы, которые можно ограничивать, но не останавливать
    if echo "$process_name" | grep -qE 'node|python|php|java|ruby|perl|bash'; then
        return 0  # Это ограничиваемый процесс
    fi
    
    return 1  # Не ограничиваемый процесс
}

# Функция для определения процессов, которые можно остановить
is_stoppable_process() {
    local process_name="$1"
    
    # Процессы, которые можно безопасно останавливать
    if echo "$process_name" | grep -qE 'chrome|firefox|rg|find|grep|unused_service|test|ripgrep'; then
        return 0  # Это останавливаемый процесс
    fi
    
    # Проверяем, чтобы не остановить критичные процессы
    if is_critical_process "$process_name"; then
        return 1  # Не останавливаем критичные процессы
    fi
    
    # Проверяем процессы Cursor IDE
    if echo "$process_name" | grep -qE 'cursor|vscode|rg'; then
        return 0  # Можно остановить процессы IDE
    fi
    
    return 1  # По умолчанию не останавливаем
}

# Функция для определения каких процессов не нужно ограничивать вообще
is_exempted_process() {
    local process_name="$1"
    
    # Процессы, которые не нужно ограничивать вообще
    if echo "$process_name" | grep -qE 'bash$|sh$|^ps$|^grep$|^awk$|^sed$|^top$|^htop$'; then
        return 0  # Это исключённый процесс
    fi
    
    return 1  # Не исключённый процесс
}

# Функция для определения процессов IDE Cursor, которые можно остановить
is_cursor_process() {
    local process_name="$1"
    local cmdline=$(cat /proc/$2/cmdline 2>/dev/null | tr '\0' ' ')
    
    if echo "$process_name" | grep -qE 'node|rg|cursor'; then
        if echo "$cmdline" | grep -qE 'cursor|vscode'; then
            return 0  # Это процесс Cursor IDE
        fi
    fi
    
    return 1  # Не процесс Cursor IDE
}

# Функция интеллектуального ограничения процессов
limit_process_smart() {
    local pid="$1"
    local process_name=$(ps -p $pid -o comm= 2>/dev/null)
    local cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
    local cpu_percent=$(ps -p $pid -o %cpu= 2>/dev/null | tr -d ' ')
    local mem_percent=$(ps -p $pid -o %mem= 2>/dev/null | tr -d ' ')
    
    # Проверяем исключения
    if is_exempted_process "$process_name"; then
        echo "Процесс $process_name (PID: $pid) исключен из ограничений"
        return 0
    fi
    
    # Проверяем Cursor IDE процессы
    if echo "$cmdline" | grep -qE 'cursor|vscode'; then
        if (( $(echo "$cpu_percent > 50" | bc -l) )); then
            echo "Ограничиваем процесс Cursor IDE $process_name (PID: $pid) до $CPU_LIMIT_STRICT% CPU"
            cpulimit -p $pid -l $CPU_LIMIT_STRICT -b >/dev/null 2>&1
            return 0
        fi
    fi
    
    # Особое ограничение для bash процессов, использующих много CPU
    if echo "$process_name" | grep -qE 'bash' && (( $(echo "$cpu_percent > 80" | bc -l) )); then
        echo "Ограничиваем высоконагруженный bash $process_name (PID: $pid) до $CPU_LIMIT_CRITICAL% CPU"
        cpulimit -p $pid -l $CPU_LIMIT_CRITICAL -b >/dev/null 2>&1
        return 0
    fi
    
    # Стандартная логика для других процессов
    if is_critical_process "$process_name"; then
        if (( $(echo "$cpu_percent > $CPU_CRITICAL" | bc -l) )); then
            echo "Ограничиваем критичный процесс $process_name (PID: $pid) до $CPU_LIMIT_NORMAL% CPU"
            cpulimit -p $pid -l $CPU_LIMIT_NORMAL -b >/dev/null 2>&1
        fi
    elif is_limitable_process "$process_name"; then
        if (( $(echo "$cpu_percent > 50" | bc -l) )); then
            echo "Ограничиваем лимитируемый процесс $process_name (PID: $pid) до $CPU_LIMIT_STRICT% CPU"
            cpulimit -p $pid -l $CPU_LIMIT_STRICT -b >/dev/null 2>&1
        fi
    elif is_stoppable_process "$process_name"; then
        if (( $(echo "$cpu_percent > 60" | bc -l) )); then
            echo "Останавливаем ненужный процесс $process_name (PID: $pid) с CPU $cpu_percent%"
            kill $pid >/dev/null 2>&1
        fi
    fi
}

# Функция для оптимизации системы без необходимости перезапуска
optimize_system_fast() {
    echo "Выполняю быструю оптимизацию системы..."
    
    # Останавливаем процессы Cursor IDE
    pkill -f rg >/dev/null 2>&1
    
    # Ограничиваем процессы bash с высоким потреблением CPU
    for pid in $(ps aux | grep bash | grep -v grep | awk '$3>80 {print $2}'); do
        echo "Ограничиваем высоконагруженный bash (PID: $pid)"
        cpulimit -p $pid -l $CPU_LIMIT_CRITICAL -b >/dev/null 2>&1
    done
    
    # Очищаем кэш памяти
    echo 3 > /proc/sys/vm/drop_caches
    
    echo "Быстрая оптимизация завершена"
}

# Экспортируем все функции
export -f is_critical_process
export -f is_limitable_process
export -f is_stoppable_process
export -f is_exempted_process
export -f send_telegram_notification
export -f is_cursor_process
export -f limit_process_smart
export -f optimize_system_fast

# Функции проверки и управления
source /root/server_control_functions.sh 