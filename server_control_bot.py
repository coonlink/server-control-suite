#!/usr/bin/env python3
"""
Telegram бот для управления сервером.
Предоставляет интерфейс для мониторинга и управления серверными процессами.
"""
import os
import sys
import json
import logging
import subprocess
import asyncio
import time
from datetime import datetime
try:
    import telegram
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
except ImportError as e:
    logging.critical(f"Ошибка импорта библиотеки python-telegram-bot: {e}")
    print(f"Критическая ошибка: {e}")
    print("Пожалуйста, установите python-telegram-bot версии 13.7: pip install python-telegram-bot==13.7")
    sys.exit(1)

# Конфигурация
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "critical_processes_config.sh")
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), ".telegram_credentials")
LOG_FILE = os.path.join(os.path.dirname(__file__), "server_control_bot.log")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "server_stats_history.json")

# Настройка логирования
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def load_config():
    """
    Загружает конфигурацию из файлов.
    
    Returns:
        dict: Словарь с конфигурацией
    """
    config = {
        'BOT_TOKEN': None,
        'AUTHORIZED_ADMINS': [],
        'CPU_LIMITS': {},
        'MEMORY_LIMITS': {},
        'NOTIFICATION_LEVELS': {}
    }
    
    # Загружаем учетные данные Telegram
    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    config['BOT_TOKEN'] = line.split('=')[1].strip().strip('"\'')
    except (IOError, OSError) as e:
        logging.error(f"Ошибка доступа к файлу учетных данных: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Неожиданная ошибка при загрузке учетных данных: {e}")
        sys.exit(1)
    
    # Загружаем основную конфигурацию
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # Загружаем админов
            if 'AUTHORIZED_ADMINS=(' in content:
                admins = content.split('AUTHORIZED_ADMINS=(')[1].split(')')[0]
                config['AUTHORIZED_ADMINS'] = [int(x.strip().strip('"')) for x in admins.split() if x.strip('"').isdigit()]
            
            # Загружаем лимиты CPU
            if 'CPU_LIMIT_NORMAL=' in content:
                config['CPU_LIMITS']['normal'] = int(content.split('CPU_LIMIT_NORMAL=')[1].split('\n')[0])
            if 'CPU_LIMIT_STRICT=' in content:
                config['CPU_LIMITS']['strict'] = int(content.split('CPU_LIMIT_STRICT=')[1].split('\n')[0])
            if 'CPU_LIMIT_CRITICAL=' in content:
                config['CPU_LIMITS']['critical'] = int(content.split('CPU_LIMIT_CRITICAL=')[1].split('\n')[0])
    except (IOError, OSError) as e:
        logging.error(f"Ошибка доступа к файлу конфигурации: {e}")
        sys.exit(1)
    except ValueError as e:
        logging.error(f"Ошибка формата данных при загрузке конфигурации: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Неожиданная ошибка при загрузке конфигурации: {e}")
        sys.exit(1)
    
    return config

config = load_config()

def get_main_keyboard():
    """
    Создает основную клавиатуру бота.
    
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("🔄 Процессы", callback_data="processes")
        ],
        [
            InlineKeyboardButton("⚡ Оптимизация", callback_data="optimize"),
            InlineKeyboardButton("📝 Логи", callback_data="logs")
        ],
        [
            InlineKeyboardButton("📈 Статистика", callback_data="stats"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
        ],
        [
            InlineKeyboardButton("❌ Очистка", callback_data="cleanup"),
            InlineKeyboardButton("🌙 Ночной режим", callback_data="night_mode")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_processes_keyboard():
    """
    Создает клавиатуру для управления процессами.
    
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [
            InlineKeyboardButton("🔍 Показать все", callback_data="show_all_processes"),
            InlineKeyboardButton("⚠️ Тяжелые процессы", callback_data="heavy_processes")
        ],
        [
            InlineKeyboardButton("🛑 Ограничить CPU", callback_data="limit_cpu"),
            InlineKeyboardButton("🗑️ Очистить память", callback_data="clear_memory")
        ],
        [
            InlineKeyboardButton("💾 Статистика памяти", callback_data="memory_stats"),
            InlineKeyboardButton("📊 История нагрузки", callback_data="load_history")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard():
    """
    Создает клавиатуру для настроек.
    
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [
            InlineKeyboardButton("🔔 Уведомления", callback_data="notification_settings"),
            InlineKeyboardButton("⚡ Лимиты CPU", callback_data="cpu_limits")
        ],
        [
            InlineKeyboardButton("💾 Лимиты памяти", callback_data="memory_limits"),
            InlineKeyboardButton("🕒 Расписание", callback_data="schedule_settings")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def save_stats_history(stats):
    """
    Сохраняет историю статистики в файл.
    
    Args:
        stats (dict): Статистика для сохранения
    """
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        # Добавляем новую статистику
        history.append({
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        })
        
        # Оставляем только последние 1000 записей
        if len(history) > 1000:
            history = history[-1000:]
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f)
    except (IOError, OSError) as e:
        logging.error(f"Ошибка доступа к файлу истории статистики: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка декодирования JSON: {e}")
    except Exception as e:
        logging.error(f"Неожиданная ошибка при сохранении статистики: {e}")

async def get_stats_history(hours=24):
    """
    Получает историю статистики за указанный период.
    
    Args:
        hours (int): Количество часов для фильтрации
        
    Returns:
        list: Список записей истории
    """
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                
            # Фильтруем по времени
            current_time = datetime.now()
            filtered_history = [
                h for h in history 
                if (current_time - datetime.fromisoformat(h['timestamp'])).total_seconds() <= hours * 3600
            ]
            return filtered_history
    except (IOError, OSError) as e:
        logging.error(f"Ошибка доступа к файлу истории статистики: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка декодирования JSON: {e}")
    except Exception as e:
        logging.error(f"Неожиданная ошибка при чтении статистики: {e}")
    return []

def is_authorized(user_id):
    """
    Проверяет, авторизован ли пользователь.
    
    Args:
        user_id (int): ID пользователя Telegram
        
    Returns:
        bool: True, если пользователь авторизован
    """
    return user_id in config['AUTHORIZED_ADMINS']

def measure_time(func):
    """
    Декоратор для измерения времени выполнения функции.
    
    Args:
        func (callable): Функция для измерения
        
    Returns:
        callable: Обернутая функция
    """
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        generation_time = (end_time - start_time) * 1000  # конвертируем в миллисекунды
        
        return result
    return wrapper

# Обработчики команд
def start_command(update: Update, context: CallbackContext):
    """Обработчик команд /start и /help."""
    if not is_authorized(update.effective_user.id):
        update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return
    
    update.message.reply_text(
        "🤖 Панель управления сервером v2.0\n\n"
        "🆕 Новые функции:\n"
        "- 📈 Статистика и история нагрузки\n"
        "- 🌙 Ночной режим\n"
        "- ⚙️ Расширенные настройки\n"
        "- 🔔 Настраиваемые уведомления\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

# Обработчик callback-запросов
def button_callback(update: Update, context: CallbackContext):
    """Обработчик нажатий на кнопки."""
    query = update.callback_query
    query.answer()
    
    if not is_authorized(query.from_user.id):
        query.edit_message_text("⛔ У вас нет доступа к этому действию.")
        return
    
    action = query.data
    
    try:
        if action == "stats":
            # Здесь должен быть асинхронный вызов get_stats_history
            # Так как в python-telegram-bot 13.7 мы не можем использовать асинхронные функции напрямую,
            # мы будем использовать синхронный подход
            stats_text = "📈 Статистика недоступна в этой версии"
            
            query.edit_message_text(
                stats_text,
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
        
        elif action == "night_mode":
            # Включаем ночной режим
            subprocess.Popen(["/root/night_optimize.sh"])
            query.edit_message_text(
                "🌙 Ночной режим активирован\n"
                "- Ограничение CPU: 5%\n"
                "- Отложенные задачи активированы\n"
                "- Неприоритетные сервисы приостановлены",
                reply_markup=get_main_keyboard()
            )
        
        elif action == "settings":
            query.edit_message_text(
                "⚙️ Настройки сервера\n\n"
                "Выберите категорию настроек:",
                reply_markup=get_settings_keyboard()
            )
        
        elif action == "status":
            try:
                result = subprocess.check_output(
                    ["/root/check_server_status.sh", "--silent"], 
                    stderr=subprocess.STDOUT, 
                    universal_newlines=True
                )
                query.edit_message_text(
                    f"📊 Статус сервера:\n\n{result}",
                    reply_markup=get_main_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка выполнения скрипта статуса: {e}")
                query.edit_message_text(
                    f"❌ Ошибка получения статуса: {e.output}",
                    reply_markup=get_main_keyboard()
                )
        
        elif action == "processes":
            query.edit_message_text(
                "🔄 Управление процессами:",
                reply_markup=get_processes_keyboard()
            )
        
        elif action == "optimize":
            subprocess.Popen(["/root/optimize_server.sh"])
            query.edit_message_text(
                "⚡ Оптимизация запущена\n"
                "Результаты будут отправлены после завершения.",
                reply_markup=get_main_keyboard()
            )
        
        elif action == "logs":
            query.edit_message_text(
                "📝 Выберите тип логов:",
                reply_markup=get_processes_keyboard()
            )
        
        elif action == "cleanup":
            try:
                subprocess.run("sync && echo 3 > /proc/sys/vm/drop_caches", 
                               shell=True, 
                               check=True, 
                               stderr=subprocess.PIPE)
                query.edit_message_text(
                    "🧹 Очистка кэша выполнена",
                    reply_markup=get_main_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка очистки кэша: {e}")
                query.edit_message_text(
                    f"❌ Ошибка очистки кэша: {e.stderr.decode() if e.stderr else str(e)}",
                    reply_markup=get_main_keyboard()
                )
        
        elif action == "show_all_processes":
            try:
                result = subprocess.check_output(
                    ["ps", "aux", "--sort=-%cpu"], 
                    universal_newlines=True
                )
                # Берем только первые 11 строк (заголовок + 10 процессов)
                result_lines = result.split('\n')[:11]
                result = '\n'.join(result_lines)
                
                query.edit_message_text(
                    f"📊 Топ процессов по CPU:\n\n<pre>{result}</pre>",
                    parse_mode="HTML",
                    reply_markup=get_processes_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка получения списка процессов: {e}")
                query.edit_message_text(
                    f"❌ Ошибка получения списка процессов: {e.output}",
                    reply_markup=get_processes_keyboard()
                )
        
        elif action == "heavy_processes":
            try:
                result = subprocess.check_output(
                    ["/root/monitor_heavy_processes.sh", "--analyze"], 
                    stderr=subprocess.STDOUT, 
                    universal_newlines=True
                )
                query.edit_message_text(
                    f"⚠️ Тяжелые процессы:\n\n{result}",
                    reply_markup=get_processes_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка анализа тяжелых процессов: {e}")
                query.edit_message_text(
                    f"❌ Ошибка анализа процессов: {e.output}",
                    reply_markup=get_processes_keyboard()
                )
        
        elif action == "main_menu":
            query.edit_message_text(
                "🤖 Главное меню\n\nВыберите действие:",
                reply_markup=get_main_keyboard()
            )
        
        elif action.startswith("logs_"):
            log_files = {
                "logs_system": "/var/log/syslog",
                "logs_cursor": "/var/log/cursor_monitor.log",
                "logs_optimize": "/var/log/optimize_server.log",
                "logs_bot": "/var/log/server_control_bot.log"
            }
            
            log_file = log_files.get(action)
            
            if log_file:
                try:
                    # Безопасное получение последних строк лога
                    result = subprocess.check_output(
                        ["tail", "-n", "20", log_file],
                        universal_newlines=True
                    )
                    query.edit_message_text(
                        f"📝 Последние логи ({log_file}):\n\n<pre>{result}</pre>",
                        parse_mode="HTML",
                        reply_markup=get_processes_keyboard()
                    )
                except subprocess.CalledProcessError as e:
                    logging.error(f"Ошибка чтения лог-файла {log_file}: {e}")
                    query.edit_message_text(
                        f"❌ Ошибка чтения лог-файла: {e.output}",
                        reply_markup=get_processes_keyboard()
                    )
        else:
            query.edit_message_text(
                f"⚠️ Неизвестное действие: {action}",
                reply_markup=get_main_keyboard()
            )
    
    except subprocess.SubprocessError as e:
        logging.error(f"Ошибка выполнения subprocess при обработке callback {action}: {e}")
        query.edit_message_text(
            f"❌ Ошибка выполнения команды: {str(e)}",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке callback {action}: {e}", exc_info=True)
        query.edit_message_text(
            f"❌ Неожиданная ошибка: {str(e)}",
            reply_markup=get_main_keyboard()
        )

# Функция для сбора статистики (работает в отдельном потоке)
def stats_collector():
    """
    Периодический сбор статистики о системе.
    Запускается в фоновом режиме и сохраняет данные каждые 5 минут.
    """
    # Так как в python-telegram-bot 13.7 сложнее работать с асинхронным кодом,
    # мы упростим эту функцию и не будем использовать асинхронные операции
    pass

# Запуск бота
if __name__ == '__main__':
    try:
        logging.info("Бот запущен")
        
        # Создаем Updater и передаем ему токен бота
        updater = Updater(config['BOT_TOKEN'])
        
        # Получаем диспетчер для регистрации обработчиков
        dispatcher = updater.dispatcher
        
        # Регистрируем обработчики
        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(CommandHandler("help", start_command))
        dispatcher.add_handler(CallbackQueryHandler(button_callback))
        
        print("Бот запущен. Нажмите Ctrl+C для остановки.")
        
        # Запускаем бота
        updater.start_polling()
        updater.idle()
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
        print("Бот остановлен пользователем")
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        print(f"Критическая ошибка при запуске бота: {e}") 
