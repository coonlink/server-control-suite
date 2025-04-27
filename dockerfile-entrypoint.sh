#!/bin/bash
set -e

# Создание директорий, если они не существуют
mkdir -p /app/config
mkdir -p /app/localization
mkdir -p /app/logs

# Проверка и создание файла с учетными данными Telegram
if [ ! -f /app/.telegram_credentials ]; then
    echo "Creating default telegram credentials file"
    cp /app/.telegram_credentials.example /app/.telegram_credentials
    
    # Проверка и установка переменных окружения в файл учетных данных
    if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        echo "TELEGRAM_BOT_TOKEN=\"$TELEGRAM_BOT_TOKEN\"" > /app/.telegram_credentials
    fi
    
    if [ -n "$TELEGRAM_CHAT_ID" ]; then
        echo "TELEGRAM_CHAT_ID=\"$TELEGRAM_CHAT_ID\"" >> /app/.telegram_credentials
    fi
fi

# Создание конфигурационного файла локализации, если он не существует
if [ ! -f /app/config/localization.conf ]; then
    echo "Creating localization configuration file"
    cat > /app/config/localization.conf << EOL
# Localization Configuration
# Available languages: en (English), ru (Russian)

# Default language to use
DEFAULT_LANGUAGE="en"

# Enable multi-language support (true/false)
MULTI_LANGUAGE_SUPPORT=true

# Allow users to select language via bot commands (true/false)
USER_LANGUAGE_SELECTION=true

# Language selection button text
LANG_BUTTON_EN="🇬🇧 English"
LANG_BUTTON_RU="🇷🇺 Русский"

# Language selection menu title
LANG_MENU_TITLE="Select language / Выберите язык:"

# Language selection success messages
LANG_SELECTED_EN="Language set to English"
LANG_SELECTED_RU="Язык изменен на Русский"
EOL
fi

# Создание файлов локализации, если они не существуют
if [ ! -f /app/localization/en.json ]; then
    echo "Creating English localization file"
    cat > /app/localization/en.json << EOL
{
  "main": {
    "welcome": "🤖 Server Control Panel v1.0",
    "new_features": "🆕 New features:",
    "feature_stats": "- 📈 Statistics and load history",
    "feature_night": "- 🌙 Night mode",
    "feature_settings": "- ⚙️ Advanced settings",
    "feature_notifications": "- 🔔 Customizable notifications",
    "select_action": "Select an action:"
  },
  "buttons": {
    "status": "📊 Status",
    "processes": "🔄 Processes",
    "optimize": "⚡ Optimize",
    "logs": "📝 Logs",
    "stats": "📈 Statistics",
    "settings": "⚙️ Settings",
    "cleanup": "❌ Cleanup",
    "night_mode": "🌙 Night Mode",
    "show_all": "🔍 Show All",
    "heavy_processes": "⚠️ Heavy Processes",
    "limit_cpu": "🛑 Limit CPU",
    "clear_memory": "🗑️ Clear Memory",
    "memory_stats": "💾 Memory Stats",
    "load_history": "📊 Load History",
    "back": "◀️ Back",
    "confirm_yes": "✅ Yes",
    "confirm_no": "❌ Cancel",
    "notifications": "🔔 Notifications",
    "cpu_limits": "⚡ CPU Limits",
    "memory_limits": "💾 Memory Limits",
    "schedule": "🕒 Schedule"
  },
  "messages": {
    "unauthorized": "⛔ You don't have access to this bot.",
    "stats_unavailable": "📈 This feature is not available in this version",
    "night_mode_confirm": "🌙 Are you sure you want to enable night mode?\n\n⚠️ This action will limit server performance and may affect running services.",
    "night_mode_activated": "🌙 Night mode activated\n- CPU limit: 5%\n- Delayed tasks activated\n- Non-priority services suspended",
    "settings_title": "⚙️ Server Settings\n\nSelect a settings category:",
    "status_error": "❌ Error getting status: {error}",
    "processes_confirm": "🔄 Are you sure you want to manage processes?\n\n⚠️ Changing running processes can affect server stability.",
    "processes_title": "🔄 Process Management:",
    "optimize_confirm": "⚡ Are you sure you want to start server optimization?\n\n⚠️ During optimization, temporary performance degradation is possible.",
    "optimize_started": "⚡ Optimization started\nResults will be sent after completion.",
    "logs_title": "📝 Select log type:",
    "cleanup_confirm": "🧹 Are you sure you want to clear the server cache?\n\n⚠️ This action may temporarily slow down applications.",
    "cleanup_done": "🧹 Cache cleanup completed",
    "cleanup_error": "❌ Cache cleanup error: {error}",
    "top_processes_title": "📊 Top processes by CPU:",
    "heavy_processes_title": "⚠️ Heavy processes:",
    "heavy_processes_error": "❌ Process analysis error: {error}",
    "main_menu": "🤖 Main Menu\n\nSelect an action:",
    "logs_template": "📝 Recent logs ({log_file}):",
    "unknown_action": "⚠️ Unknown action: {action}",
    "command_error": "❌ Command execution error: {error}",
    "unexpected_error": "❌ Unexpected error: {error}",
    "script_not_found": "❌ Error: script {script} not found",
    "script_not_executable": "❌ Error: script does not have execution permissions",
    "script_timeout": "❌ Error: timeout while getting status",
    "missing_scripts_warning": "WARNING! Missing scripts: {scripts}\nSome bot functions may be unavailable!"
  },
  "report": {
    "title": "📊 *Periodic server status report*",
    "time": "📆 Time: {timestamp}",
    "host": "🖥️ Host: {hostname}",
    "load_warning": "⚠️ WARNING! High system load: {load}",
    "recommended_actions": "Recommended actions:\n1. Run server optimization: ./optimize_server.sh\n2. Check heavy processes: ./monitor_heavy_processes.sh"
  },
  "errors": {
    "config_access": "Error accessing configuration file: {error}",
    "unexpected": "Unexpected error: {error}",
    "token_missing": "Bot token not specified in environment variables or credentials file",
    "admins_missing": "Authorized administrators not specified. Bot access will be restricted.",
    "callback_error": "Error responding to callback: {error}",
    "unauthorized_access": "Unauthorized access attempt from ID: {user_id}",
    "unauthorized_message": "Error sending unauthorized access message: {error}",
    "status_script_error": "Error executing status script: {error}",
    "processing_action": "Error processing action '{action}': {error}",
    "edit_message": "Failed to edit message: {error}",
    "report_sending": "Error sending report to admin {admin_id}: {error}",
    "system_load_check": "Error checking system load: {error}"
  }
}
EOL
fi

if [ ! -f /app/localization/ru.json ]; then
    echo "Creating Russian localization file"
    cat > /app/localization/ru.json << EOL
{
  "main": {
    "welcome": "🤖 Панель управления сервером v1.0",
    "new_features": "🆕 Новые функции:",
    "feature_stats": "- 📈 Статистика и история нагрузки",
    "feature_night": "- 🌙 Ночной режим",
    "feature_settings": "- ⚙️ Расширенные настройки",
    "feature_notifications": "- 🔔 Настраиваемые уведомления",
    "select_action": "Выберите действие:"
  },
  "buttons": {
    "status": "📊 Статус",
    "processes": "🔄 Процессы",
    "optimize": "⚡ Оптимизация",
    "logs": "📝 Логи",
    "stats": "📈 Статистика",
    "settings": "⚙️ Настройки",
    "cleanup": "❌ Очистка",
    "night_mode": "🌙 Ночной режим",
    "show_all": "🔍 Показать все",
    "heavy_processes": "⚠️ Тяжелые процессы",
    "limit_cpu": "🛑 Ограничить CPU",
    "clear_memory": "🗑️ Очистить память",
    "memory_stats": "💾 Статистика памяти",
    "load_history": "📊 История нагрузки",
    "back": "◀️ Назад",
    "confirm_yes": "✅ Да",
    "confirm_no": "❌ Отмена",
    "notifications": "🔔 Уведомления",
    "cpu_limits": "⚡ Лимиты CPU",
    "memory_limits": "💾 Лимиты памяти",
    "schedule": "🕒 Расписание"
  },
  "messages": {
    "unauthorized": "⛔ У вас нет доступа к этому боту.",
    "stats_unavailable": "📈 Эта функция недоступна в данной версии",
    "night_mode_confirm": "🌙 Вы уверены, что хотите включить ночной режим?\n\n⚠️ Это действие ограничит производительность сервера и может повлиять на работающие сервисы.",
    "night_mode_activated": "🌙 Ночной режим активирован\n- Ограничение CPU: 5%\n- Отложенные задачи активированы\n- Неприоритетные сервисы приостановлены",
    "settings_title": "⚙️ Настройки сервера\n\nВыберите категорию настроек:",
    "status_error": "❌ Ошибка получения статуса: {error}",
    "processes_confirm": "🔄 Вы уверены, что хотите управлять процессами?\n\n⚠️ Изменение работающих процессов может повлиять на стабильность работы сервера.",
    "processes_title": "🔄 Управление процессами:",
    "optimize_confirm": "⚡ Вы уверены, что хотите запустить оптимизацию сервера?\n\n⚠️ Во время оптимизации возможно временное снижение производительности.",
    "optimize_started": "⚡ Оптимизация запущена\nРезультаты будут отправлены после завершения.",
    "logs_title": "📝 Выберите тип логов:",
    "cleanup_confirm": "🧹 Вы уверены, что хотите очистить кэш сервера?\n\n⚠️ Это действие может на короткое время замедлить работу приложений.",
    "cleanup_done": "🧹 Очистка кэша выполнена",
    "cleanup_error": "❌ Ошибка очистки кэша: {error}",
    "top_processes_title": "📊 Топ процессов по CPU:",
    "heavy_processes_title": "⚠️ Тяжелые процессы:",
    "heavy_processes_error": "❌ Ошибка анализа процессов: {error}",
    "main_menu": "🤖 Главное меню\n\nВыберите действие:",
    "logs_template": "📝 Последние логи ({log_file}):",
    "unknown_action": "⚠️ Неизвестное действие: {action}",
    "command_error": "❌ Ошибка выполнения команды: {error}",
    "unexpected_error": "❌ Неожиданная ошибка: {error}",
    "script_not_found": "❌ Ошибка: скрипт {script} не найден",
    "script_not_executable": "❌ Ошибка: скрипт не имеет прав на выполнение",
    "script_timeout": "❌ Ошибка: превышено время ожидания при получении статуса",
    "missing_scripts_warning": "ВНИМАНИЕ! Отсутствуют следующие скрипты: {scripts}\nНекоторые функции бота могут быть недоступны!"
  },
  "report": {
    "title": "📊 *Периодический отчет о статусе сервера*",
    "time": "📆 Время: {timestamp}",
    "host": "🖥️ Хост: {hostname}",
    "load_warning": "⚠️ ВНИМАНИЕ! Высокая нагрузка системы: {load}",
    "recommended_actions": "Рекомендуемые действия:\n1. Запустите оптимизацию сервера: ./optimize_server.sh\n2. Проверьте тяжелые процессы: ./monitor_heavy_processes.sh"
  },
  "errors": {
    "config_access": "Ошибка доступа к файлу конфигурации: {error}",
    "unexpected": "Неожиданная ошибка: {error}",
    "token_missing": "Не указан токен бота в переменных окружения или файле учетных данных",
    "admins_missing": "Не указаны авторизованные администраторы. Доступ к боту будет ограничен.",
    "callback_error": "Ошибка при ответе на callback: {error}",
    "unauthorized_access": "Попытка неавторизованного доступа от ID: {user_id}",
    "unauthorized_message": "Ошибка при отправке сообщения о неавторизованном доступе: {error}",
    "status_script_error": "Ошибка выполнения скрипта статуса: {error}",
    "processing_action": "Ошибка при обработке действия '{action}': {error}",
    "edit_message": "Не удалось отредактировать сообщение: {error}",
    "report_sending": "Ошибка отправки отчета администратору {admin_id}: {error}",
    "system_load_check": "Ошибка при проверке нагрузки системы: {error}"
  }
}
EOL
fi

# Вывод информации о контейнере
echo "Container started with:"
echo "Files in /app:"
ls -la /app
echo "Environment variables:"
env | grep TELEGRAM
echo

# Отправка уведомления о запуске в Telegram
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    echo "Sending startup notification to Telegram..."
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
         -d chat_id="$TELEGRAM_CHAT_ID" \
         -d text="🤖 *Server Control Bot* started on $(hostname) at $(date)" \
         -d parse_mode="Markdown" > /dev/null
    echo "Startup notification sent"
fi

# Запуск бота
cd /app
exec python server_control_bot.py 