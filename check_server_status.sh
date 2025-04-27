#!/bin/bash

# Get script directory for relative paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Загружаем конфигурацию из текущей директории
CONFIG_FILE="$SCRIPT_DIR/critical_processes_config.sh"
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
else
  echo "Ошибка: Конфигурационный файл $CONFIG_FILE не найден."
  exit 1
fi

# Проверяем, заполнены ли параметры Telegram
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "Ошибка: Необходимо настроить TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в $CONFIG_FILE"
  exit 1
fi

# Функция для получения среднего значения CPU за несколько измерений
get_average_cpu() {
  local samples=$1
  local interval=$2
  local sum=0
  
  echo "Сбор данных о CPU за $samples измерений с интервалом $interval секунд..." >&2
  
  for i in $(seq 1 $samples); do
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')
    sum=$(echo "$sum + $cpu_usage" | bc)
    if [ $i -lt $samples ]; then
      sleep $interval
    fi
  done
  
  echo "scale=1; $sum / $samples" | bc
}

# Получаем основные параметры системы
HOSTNAME=$(hostname)
UPTIME=$(uptime -p)
LOAD=$(uptime | awk -F'[a-z]:' '{ print $2}' | awk '{print $1, $2, $3}' | tr -d ',')
LOAD_1=$(echo $LOAD | awk '{print $1}')
LOAD_5=$(echo $LOAD | awk '{print $2}')
LOAD_15=$(echo $LOAD | awk '{print $3}')
MEMORY=$(free -h)
MEM_PERCENT=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
DISK_USAGE=$(df -h | grep -v tmpfs | grep -v udev)
DISK_PERCENT=$(df -h | grep '/$' | awk '{print $5}' | tr -d '%')
TOP_CPU=$(ps aux --sort=-%cpu | head -6 | tail -5 | awk '{print $11, " (PID:", $2, "CPU:", $3"%)"}')
TOP_MEM=$(ps aux --sort=-%mem | head -6 | tail -5 | awk '{print $11, " (PID:", $2, "MEM:", $4"%)"}')
CPU_USAGE=$(get_average_cpu 3 1)
OPEN_PORTS=$(netstat -tuln | grep LISTEN | awk '{print $4}' | sort)

# Проверяем историю нагрузки из лог-файла, если он существует
LOAD_HISTORY=""
LOG_FILE="$SCRIPT_DIR/performance_stats.log"
if [ -f "$LOG_FILE" ]; then
  LOAD_HISTORY="📈 <b>История нагрузки:</b>
<pre>$(tail -n 5 $LOG_FILE)</pre>"
fi

# Формируем сообщение
MESSAGE="🖥️ <b>СТАТУС СЕРВЕРА</b> 🖥️

⏱️ <b>Время работы:</b> $UPTIME
🔄 <b>Загрузка системы:</b>
   - 1 мин: $LOAD_1
   - 5 мин: $LOAD_5
   - 15 мин: $LOAD_15
💻 <b>Использование CPU:</b> ${CPU_USAGE}%
💾 <b>Память:</b>
$MEMORY
Использовано: ${MEM_PERCENT}%

💿 <b>Диск:</b>
$DISK_USAGE
/ заполнен на: ${DISK_PERCENT}%

⚡ <b>Топ процессы по CPU:</b>
$TOP_CPU

🧠 <b>Топ процессы по памяти:</b>
$TOP_MEM

🔌 <b>Открытые порты:</b>
$OPEN_PORTS

$LOAD_HISTORY

🕒 Отчет сгенерирован: $(date '+%Y-%m-%d %H:%M:%S')"

# Отправляем сообщение в Telegram
send_telegram_notification "$MESSAGE"

echo "Отчет о состоянии сервера отправлен в Telegram"

# Проверка на критические значения
WARNINGS=""
CRIT_COUNT=0

# Lower the threshold for notification if it's a server with low CPU count
CPU_COUNT=$(grep -c ^processor /proc/cpuinfo)
if [ $CPU_COUNT -le 2 ]; then
  LOAD_WARNING_THRESHOLD=4.0 # для слабых серверов с 1-2 ядрами
  LOAD_INFO_THRESHOLD=3.0
elif [ $CPU_COUNT -le 4 ]; then
  LOAD_WARNING_THRESHOLD=6.0 # для средних серверов с 3-4 ядрами
  LOAD_INFO_THRESHOLD=4.0
else
  LOAD_WARNING_THRESHOLD=10.0 # для мощных серверов с 5+ ядрами (было 7.0)
  LOAD_INFO_THRESHOLD=7.0 # было 5.0
fi

# Adjust load thresholds based on CPU count - это не для общего LOAD_THRESHOLD, а только для уведомлений
ADJUSTED_LOAD_THRESHOLD=$(echo "scale=1; $CPU_COUNT * 1.5" | bc)
if (( $(echo "$ADJUSTED_LOAD_THRESHOLD < $LOAD_THRESHOLD" | bc -l) )); then
  EFFECTIVE_LOAD_THRESHOLD=$ADJUSTED_LOAD_THRESHOLD
else
  EFFECTIVE_LOAD_THRESHOLD=$LOAD_THRESHOLD
fi

# Check load average
if (( $(echo "$LOAD_1 > $EFFECTIVE_LOAD_THRESHOLD" | bc -l) )); then
  WARNINGS+="⚠️ Высокая нагрузка системы: $LOAD_1 (порог: $EFFECTIVE_LOAD_THRESHOLD)\n\n"
  CRIT_COUNT=$((CRIT_COUNT + 1))
  
  # Recommended actions for high load
  WARNINGS+="📋 Рекомендуемые действия при высокой нагрузке:\n"
  WARNINGS+="1. Проверьте процессы с высоким потреблением CPU: 'top -c'\n"
  WARNINGS+="2. Ограничьте ресурсы для неприоритетных процессов:\n   'nice -n 19 COMMAND' или 'renice 19 -p PID'\n"
  WARNINGS+="3. Для критических ситуаций рассмотрите остановку некритичных процессов\n\n"
elif (( $(echo "$LOAD_1 > $LOAD_WARNING_THRESHOLD" | bc -l) )); then
  WARNINGS+="⚠️ Предупреждение: Нагрузка системы повышена: $LOAD_1 (порог: $LOAD_WARNING_THRESHOLD)\n\n"
fi

# Check memory usage
if [ $MEM_PERCENT -ge $MEM_CRITICAL ]; then
  WARNINGS+="⚠️ Критическое использование памяти: ${MEM_PERCENT}% (порог: ${MEM_CRITICAL}%)\n\n"
  CRIT_COUNT=$((CRIT_COUNT + 1))
  
  # Recommended actions for high memory usage
  WARNINGS+="📋 Рекомендуемые действия при высоком использовании памяти:\n"
  WARNINGS+="1. Очистите кэш: 'echo 3 > /proc/sys/vm/drop_caches'\n"
  WARNINGS+="2. Проверьте процессы с высоким потреблением памяти: 'ps aux --sort=-%mem | head'\n"
  WARNINGS+="3. Рассмотрите возможность перезапуска приложений с утечками памяти\n\n"
elif [ $MEM_PERCENT -ge $MEM_WARNING ]; then
  WARNINGS+="⚠️ Предупреждение: Высокое использование памяти: ${MEM_PERCENT}% (порог: ${MEM_WARNING}%)\n\n"
fi

# Check disk usage
if [ $DISK_PERCENT -ge $DISK_CRITICAL ]; then
  WARNINGS+="⚠️ Критическое использование диска: ${DISK_PERCENT}% (порог: ${DISK_CRITICAL}%)\n\n"
  CRIT_COUNT=$((CRIT_COUNT + 1))
  
  # Recommended actions for high disk usage
  WARNINGS+="📋 Рекомендуемые действия при высоком использовании диска:\n"
  WARNINGS+="1. Очистите старые логи: 'find /var/log -type f -name \"*.gz\" -delete'\n"
  WARNINGS+="2. Найдите большие файлы: 'find / -type f -size +100M -exec ls -lh {} \\;'\n"
  WARNINGS+="3. Очистите кэш apt: 'apt-get clean'\n\n"
elif [ $DISK_PERCENT -ge $DISK_WARNING ]; then
  WARNINGS+="⚠️ Предупреждение: Высокое использование диска: ${DISK_PERCENT}% (порог: ${DISK_WARNING}%)\n\n"
fi

# Send warnings if any
if [ -n "$WARNINGS" ]; then
  SUBJECT="⚠️ ПРЕДУПРЕЖДЕНИЕ: Проблемы на сервере $HOSTNAME"
  send_telegram_notification "$SUBJECT\n\n$WARNINGS"
fi

# Добавляем текущую запись в файл статистики
STATS_FILE="$SCRIPT_DIR/performance_stats.log"
DATE=$(date +"%Y-%m-%d %H:%M:%S")
echo "$DATE | Load: $LOAD_1 $LOAD_5 $LOAD_15 | CPU: ${CPU_USAGE}% | Mem: ${MEM_PERCENT}% | Disk: ${DISK_PERCENT}%" >> "$STATS_FILE"

exit 0 