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
  local total=0
  
  echo "Сбор данных о CPU за $samples измерений с интервалом $interval секунд..." >&2
  
  for ((i=1; i<=$samples; i++)); do
    local cpu_idle=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}')
    local cpu_usage=$(echo "100 - $cpu_idle" | bc)
    total=$(echo "$total + $cpu_usage" | bc)
    
    # Если это не последнее измерение, ждем интервал
    if [ $i -lt $samples ]; then
      sleep $interval
    fi
  done
  
  # Вычисляем среднее значение
  echo "scale=1; $total / $samples" | bc
}

# Получаем основные параметры системы
LOAD=$(cat /proc/loadavg | cut -d' ' -f1-3)
UPTIME=$(uptime -p)
MEMORY=$(free -h | awk 'NR==2 {print "Всего: " $2 ", Использовано: " $3 ", Свободно: " $4}')
DISK=$(df -h / | awk 'NR==2 {print "Всего: " $2 ", Использовано: " $3 " (" $5 ")"}')

# Собираем более точную информацию о CPU - среднее за 5 измерений с интервалом 2 секунды
CPU_USAGE=$(get_average_cpu 5 2)

# Получаем нагрузку за последние 1, 5 и 15 минут
LOAD_1M=$(echo $LOAD | cut -d' ' -f1)
LOAD_5M=$(echo $LOAD | cut -d' ' -f2)
LOAD_15M=$(echo $LOAD | cut -d' ' -f3)

# Получаем топ процессы по CPU
TOP_CPU=$(ps aux --sort=-%cpu | head -6)

# Получаем топ процессы по памяти
TOP_MEM=$(ps aux --sort=-%mem | head -6)

# Проверяем открытые порты
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
   - 1 мин: $LOAD_1M
   - 5 мин: $LOAD_5M
   - 15 мин: $LOAD_15M
💻 <b>Использование CPU:</b> ${CPU_USAGE}% (среднее за 10 сек)
💾 <b>Память:</b> $MEMORY
💿 <b>Диск (/):</b> $DISK

⚡ <b>Топ процессы по CPU:</b>
<pre>$(echo "$TOP_CPU" | head -1)
$(echo "$TOP_CPU" | tail -n +2 | head -5)</pre>

🧠 <b>Топ процессы по памяти:</b>
<pre>$(echo "$TOP_MEM" | head -1)
$(echo "$TOP_MEM" | tail -n +2 | head -5)</pre>

🔌 <b>Открытые порты:</b>
<pre>$(echo "$OPEN_PORTS" | head -10)</pre>

$LOAD_HISTORY

🕒 Отчет сгенерирован: $(date '+%Y-%m-%d %H:%M:%S')"

# Отправляем сообщение в Telegram
send_telegram_notification "$MESSAGE"

echo "Отчет о состоянии сервера отправлен в Telegram"

# Проверка на критические значения
MEM_PERCENT=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
DISK_PERCENT=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')

# Добавляем текущую запись в файл статистики
STATS_FILE="$SCRIPT_DIR/performance_stats.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') LOAD: $LOAD CPU: ${CPU_USAGE}% MEM: ${MEM_PERCENT}%" >> $STATS_FILE

# Проверяем критические значения и предлагаем действия
if (( $(echo "$LOAD_1M > $LOAD_THRESHOLD" | bc -l) )); then
  WARNING_MESSAGE="⚠️ <b>ВНИМАНИЕ!</b> Высокая нагрузка системы: $LOAD_1M

<b>Рекомендуемые действия:</b>
1. Запустите оптимизацию сервера: <code>./optimize_server.sh</code>
2. Проверьте тяжелые процессы: <code>./monitor_heavy_processes.sh</code>"

  send_telegram_notification "$WARNING_MESSAGE"
fi

# Проверка памяти с использованием bc вместо арифметики bash
if (( $(echo "$MEM_PERCENT > $MEM_CRITICAL" | bc -l) )); then
  MEM_WARNING="⚠️ <b>ВНИМАНИЕ!</b> Критическое использование памяти: $MEM_PERCENT%

<b>Рекомендуемые действия:</b>
1. Очистите кэш памяти: <code>sync && echo 3 > /proc/sys/vm/drop_caches</code>
2. Перезапустите проблемные сервисы"

  send_telegram_notification "$MEM_WARNING"
fi

# Проверка диска с использованием bc вместо арифметики bash
if (( $(echo "$DISK_PERCENT > $DISK_CRITICAL" | bc -l) )); then
  DISK_WARNING="⚠️ <b>ВНИМАНИЕ!</b> Критическое заполнение диска: $DISK_PERCENT%

<b>Рекомендуемые действия:</b>
1. Очистите старые логи: <code>find /var/log -type f -name \"*.gz\" -delete</code>
2. Проверьте большие файлы: <code>find / -type f -size +100M | xargs ls -lh</code>"

  send_telegram_notification "$DISK_WARNING"
fi

exit 0 