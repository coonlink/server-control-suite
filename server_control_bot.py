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
import time
from datetime import datetime
try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
except ImportError as e:
    logging.critical("Ошибка импорта библиотеки python-telegram-bot: %s", e)
    print(f"Критическая ошибка: {e}")
    print("Установите python-telegram-bot версии 13.7: pip install python-telegram-bot==13.7")
    sys.exit(1)

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Конфигурация - используем относительные пути
CONFIG_FILE = os.path.join(BASE_DIR, "critical_processes_config.sh")
CREDENTIALS_FILE = os.path.join(BASE_DIR, ".telegram_credentials")
LOG_FILE = os.path.join(BASE_DIR, "server_control_bot.log")
HISTORY_FILE = os.path.join(BASE_DIR, "server_stats_history.json")

# Периодический отчет - интервал в секундах
STATUS_REPORT_INTERVAL = 3600  # 1 час

# Логирование в консоль и файл
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def load_config():
    """
    Загружает конфигурацию из файлов и переменных окружения.
    Returns:
        dict: Словарь с конфигурацией
    """
    cfg = {
        'BOT_TOKEN': None,
        'AUTHORIZED_ADMINS': [],
        'CPU_LIMITS': {
            'normal': 50,    # Default values
            'strict': 30,
            'critical': 10
        },
        'MEMORY_LIMITS': {},
        'NOTIFICATION_LEVELS': {}
    }
    
    # Приоритетно загружаем токен из переменной окружения
    env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if env_token:
        cfg['BOT_TOKEN'] = env_token
        logging.info("Токен бота загружен из переменной окружения TELEGRAM_BOT_TOKEN")
    
    # Приоритетно загружаем chat_id из переменной окружения
    env_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if env_chat_id and env_chat_id.isdigit():
        cfg['AUTHORIZED_ADMINS'] = [int(env_chat_id)]
        logging.info("ID администратора загружен из переменной окружения TELEGRAM_CHAT_ID")
    
    # Если переменные окружения не установлены, пробуем загрузить из файла
    if not cfg['BOT_TOKEN'] or not cfg['AUTHORIZED_ADMINS']:
        # Загружаем учетные данные Telegram из файла
        try:
            if os.path.exists(CREDENTIALS_FILE):
                with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('TELEGRAM_BOT_TOKEN=') and not cfg['BOT_TOKEN']:
                            cfg['BOT_TOKEN'] = line.split('=')[1].strip().strip('"\'')
                        elif line.startswith('TELEGRAM_CHAT_ID=') and not cfg['AUTHORIZED_ADMINS']:
                            chat_id = line.split('=')[1].strip().strip('"\'')
                            if chat_id.isdigit():
                                cfg['AUTHORIZED_ADMINS'] = [int(chat_id)]
        except (IOError, OSError) as e:
            logging.error("Ошибка доступа к файлу учетных данных: %s", e)
            if not cfg['BOT_TOKEN'] or not cfg['AUTHORIZED_ADMINS']:
                logging.critical("Не удалось загрузить учетные данные ни из переменных окружения, ни из файла")
                sys.exit(1)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Неожиданная ошибка при загрузке учетных данных: %s", e)
            if not cfg['BOT_TOKEN'] or not cfg['AUTHORIZED_ADMINS']:
                logging.critical("Не удалось загрузить учетные данные ни из переменных окружения, ни из файла")
                sys.exit(1)
    
    # Загружаем основную конфигурацию
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                # Загружаем админов если они не были загружены из переменных окружения
                if not cfg['AUTHORIZED_ADMINS'] and 'AUTHORIZED_ADMINS=(' in content:
                    try:
                        admins = content.split('AUTHORIZED_ADMINS=(')[1].split(')')[0]
                        # Преобразуем строки в числа, фильтруя только целые числа
                        cfg['AUTHORIZED_ADMINS'] = [
                            int(x.strip().strip('"'))
                            for x in admins.split()
                            if x.strip('"').isdigit()
                        ]
                    except Exception as e:
                        logging.warning("Не удалось загрузить ID администраторов: %s", e)
            
            # Загружаем лимиты CPU
            try:
                # Ищем значения переменных, исключая shell-переменные с ${} и комментарии
                normal_pattern = r'CPU_LIMIT_NORMAL=(\d+)'
                strict_pattern = r'CPU_LIMIT_STRICT=(\d+)'
                critical_pattern = r'CPU_LIMIT_CRITICAL=(\d+)'
                
                import re
                normal_match = re.search(normal_pattern, content)
                strict_match = re.search(strict_pattern, content)
                critical_match = re.search(critical_pattern, content)
                
                if normal_match:
                    cfg['CPU_LIMITS']['normal'] = int(normal_match.group(1))
                if strict_match:
                    cfg['CPU_LIMITS']['strict'] = int(strict_match.group(1))
                if critical_match:
                    cfg['CPU_LIMITS']['critical'] = int(critical_match.group(1))
            except Exception as e:
                logging.warning("Ошибка при загрузке лимитов CPU, используются значения по умолчанию: %s", e)
    except (IOError, OSError) as e:
        logging.error("Ошибка доступа к файлу конфигурации: %s", e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Неожиданная ошибка при загрузке конфигурации: %s", e)
    
    # Проверяем наличие необходимых данных
    if not cfg['BOT_TOKEN']:
        logging.critical("Не указан токен бота в переменных окружения или файле учетных данных")
        sys.exit(1)
    
    if not cfg['AUTHORIZED_ADMINS']:
        logging.warning("Не указаны авторизованные администраторы. Доступ к боту будет ограничен.")
    
    # Log the configuration (without sensitive data)
    logging.info("Конфигурация загружена успешно")
    logging.info("CPU лимиты: %s", cfg['CPU_LIMITS'])
    
    return cfg

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
        logging.error("Ошибка доступа к файлу истории статистики: %s", e)
    except json.JSONDecodeError as e:
        logging.error("Ошибка декодирования JSON: %s", e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Неожиданная ошибка при сохранении статистики: %s", e)

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
            hours_in_seconds = hours * 3600
            filtered_history = [
                h for h in history
                if (current_time - datetime.fromisoformat(h['timestamp'])).total_seconds() <= hours_in_seconds
            ]
            return filtered_history
    except (IOError, OSError) as e:
        logging.error("Ошибка доступа к файлу истории статистики: %s", e)
    except json.JSONDecodeError as e:
        logging.error("Ошибка декодирования JSON: %s", e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Неожиданная ошибка при чтении статистики: %s", e)
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
        # Конвертируем в миллисекунды
        _ = (end_time - start_time) * 1000
        
        return result
    return wrapper

# Обработчики команд
def start_command(update: Update, _context: CallbackContext):
    """Обработчик команд /start и /help."""
    if not is_authorized(update.effective_user.id):
        update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return
    
    update.message.reply_text(
        "🤖 Панель управления сервером v1.0\n\n"
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
def button_callback(update: Update, _context: CallbackContext):  # pylint: disable=too-many-branches,too-many-statements
    """Обработчик нажатий на кнопки."""
    query = update.callback_query
    
    # Добавляем подробное логирование
    logging.info("Получен callback: %s от пользователя %s", 
                 query.data, query.from_user.id)
    
    # Отвечаем на callback, чтобы убрать часы загрузки
    try:
        query.answer()
    except Exception as e:
        logging.error("Ошибка при ответе на callback: %s", e)
    
    if not is_authorized(query.from_user.id):
        try:
            query.edit_message_text("⛔ У вас нет доступа к этому действию.")
            logging.warning("Попытка неавторизованного доступа от ID: %s", 
                           query.from_user.id)
        except Exception as e:
            logging.error("Ошибка при отправке сообщения о неавторизованном доступе: %s", e)
        return
    
    action = query.data
    
    try:
        logging.info("Начинаем обработку действия: %s", action)
        
        if action == "stats":
            # Использование синхронного подхода вместо асинхронного
            stats_text = "📈 Статистика недоступна в этой версии"
            
            query.edit_message_text(
                stats_text,
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
        
        elif action == "night_mode":
            # Запрос подтверждения перед включением ночного режима
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, включить", callback_data="confirm_night_mode"),
                    InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🌙 Вы уверены, что хотите включить ночной режим?\n\n"
                "⚠️ Это действие ограничит производительность сервера "
                "и может повлиять на работающие сервисы.",
                reply_markup=reply_markup
            )
        
        elif action == "confirm_night_mode":
            # Включаем ночной режим после подтверждения
            night_script = os.path.join(BASE_DIR, "night_optimize.sh")
            with subprocess.Popen([night_script]) as _:
                pass
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
                status_script = os.path.join(BASE_DIR, "check_server_status.sh")
                cmd = [status_script, "--silent"]
                result = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, universal_newlines=True
                )
                query.edit_message_text(
                    f"📊 Статус сервера:\n\n{result}",
                    reply_markup=get_main_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error("Ошибка выполнения скрипта статуса: %s", e)
                query.edit_message_text(
                    f"❌ Ошибка получения статуса: {e.output}",
                    reply_markup=get_main_keyboard()
                )
        
        elif action == "processes":
            # Запрос подтверждения перед управлением процессами
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, продолжить", callback_data="confirm_processes"),
                    InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🔄 Вы уверены, что хотите управлять процессами?\n\n"
                "⚠️ Изменение работающих процессов может повлиять "
                "на стабильность работы сервера.",
                reply_markup=reply_markup
            )
        
        elif action == "confirm_processes":
            # Показываем меню управления процессами после подтверждения
            query.edit_message_text(
                "🔄 Управление процессами:",
                reply_markup=get_processes_keyboard()
            )
        
        elif action == "optimize":
            # Запрос подтверждения перед оптимизацией
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, оптимизировать", callback_data="confirm_optimize"),
                    InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "⚡ Вы уверены, что хотите запустить оптимизацию сервера?\n\n"
                "⚠️ Во время оптимизации возможно временное снижение производительности.",
                reply_markup=reply_markup
            )
        
        elif action == "confirm_optimize":
            # Запускаем оптимизацию после подтверждения
            optimize_script = os.path.join(BASE_DIR, "optimize_server.sh")
            with subprocess.Popen([optimize_script]) as _:
                pass
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
            # Запрос подтверждения перед очисткой кэша
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, очистить", callback_data="confirm_cleanup"),
                    InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🧹 Вы уверены, что хотите очистить кэш сервера?\n\n"
                "⚠️ Это действие может на короткое время замедлить работу приложений.",
                reply_markup=reply_markup
            )
        
        elif action == "confirm_cleanup":
            # Выполняем очистку кэша после подтверждения
            try:
                subprocess.run(
                    "sync && echo 3 > /proc/sys/vm/drop_caches",
                    shell=True, check=True, stderr=subprocess.PIPE
                )
                query.edit_message_text(
                    "🧹 Очистка кэша выполнена",
                    reply_markup=get_main_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error("Ошибка очистки кэша: %s", e)
                error_msg = e.stderr.decode() if e.stderr else str(e)
                query.edit_message_text(
                    f"❌ Ошибка очистки кэша: {error_msg}",
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
                logging.error("Ошибка получения списка процессов: %s", e)
                query.edit_message_text(
                    f"❌ Ошибка получения списка процессов: {e.output}",
                    reply_markup=get_processes_keyboard()
                )
        
        elif action == "heavy_processes":
            try:
                heavy_script = os.path.join(BASE_DIR, "monitor_heavy_processes.sh")
                cmd = [heavy_script, "--analyze"]
                result = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, universal_newlines=True
                )
                query.edit_message_text(
                    f"⚠️ Тяжелые процессы:\n\n{result}",
                    reply_markup=get_processes_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error("Ошибка анализа тяжелых процессов: %s", e)
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
                    logging.error("Ошибка чтения лог-файла %s: %s", log_file, e)
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
        logging.error("Ошибка выполнения subprocess при обработке callback %s: %s", action, e)
        try:
            query.edit_message_text(
                f"❌ Ошибка выполнения команды: {str(e)}",
                reply_markup=get_main_keyboard()
            )
        except Exception as edit_err:
            logging.error("Не удалось отредактировать сообщение: %s", edit_err)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Ошибка при обработке callback %s: %s", action, e, exc_info=True)
        try:
            query.edit_message_text(
                f"❌ Неожиданная ошибка: {str(e)}",
                reply_markup=get_main_keyboard()
            )
        except Exception as edit_err:
            logging.error("Не удалось отредактировать сообщение: %s", edit_err)

# Функция для получения статуса сервера
def get_server_status():
    """
    Получает текущий статус сервера, используя скрипт check_server_status.sh
    Returns:
        str: Текстовое представление статуса сервера
    """
    try:
        status_script = os.path.join(BASE_DIR, "check_server_status.sh")
        cmd = [status_script, "--silent"]
        result = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, universal_newlines=True
        )
        return result
    except subprocess.CalledProcessError as e:
        logging.error("Ошибка выполнения скрипта статуса: %s", e)
        return f"❌ Ошибка получения статуса: {e.output}"
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Неожиданная ошибка при получении статуса: %s", e)
        return f"❌ Неожиданная ошибка: {str(e)}"

# Функция для отправки периодического отчета о статусе
def send_status_report(context: CallbackContext):
    """
    Отправляет периодический отчет о статусе сервера всем администраторам.
    Args:
        context (CallbackContext): Контекст вызова
    """
    status = get_server_status()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = subprocess.check_output("hostname", universal_newlines=True).strip()
    
    message = f"📊 *Периодический отчет о статусе сервера*\n\n" \
              f"📆 Время: {timestamp}\n" \
              f"🖥️ Хост: {hostname}\n\n" \
              f"{status}"
    
    # Отправляем сообщение всем администраторам
    for admin_id in config['AUTHORIZED_ADMINS']:
        try:
            context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="Markdown"
            )
            logging.info("Отправлен периодический отчет администратору %s", admin_id)
        except Exception as e:
            logging.error("Ошибка отправки отчета администратору %s: %s", admin_id, e)

# Функция для проверки нагрузки системы и отправки предупреждений
def check_system_load(context: CallbackContext):
    """
    Проверяет текущую нагрузку системы и отправляет предупреждения если она превышает лимиты.
    
    Args:
        context (CallbackContext): Контекст вызова
    """
    try:
        # Получаем текущую нагрузку системы
        load_avg = os.getloadavg()
        one_min_load = load_avg[0]
        
        # Проверяем превышение лимитов
        critical_limit = config['CPU_LIMITS'].get('critical', 10)
        strict_limit = config['CPU_LIMITS'].get('strict', 30)
        normal_limit = config['CPU_LIMITS'].get('normal', 50)
        
        # Высокая нагрузка - отправляем предупреждение
        if one_min_load > normal_limit:
            message = f"⚠️ ВНИМАНИЕ! Высокая нагрузка системы: {one_min_load:.2f}\n\n"
            message += "Рекомендуемые действия:\n"
            message += "1. Запустите оптимизацию сервера: ./optimize_server.sh\n"
            message += "2. Проверьте тяжелые процессы: ./monitor_heavy_processes.sh"
            
            # Формируем клавиатуру с быстрыми действиями
            keyboard = [
                [
                    InlineKeyboardButton("⚡ Оптимизировать", callback_data="optimize"),
                    InlineKeyboardButton("🔍 Тяжелые процессы", callback_data="heavy_processes")
                ],
                [
                    InlineKeyboardButton("📊 Статус", callback_data="status"),
                    InlineKeyboardButton("🌙 Ночной режим", callback_data="night_mode")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем предупреждение всем администраторам
            for admin_id in config['AUTHORIZED_ADMINS']:
                try:
                    context.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        reply_markup=reply_markup
                    )
                    logging.info("Отправлено предупреждение о высокой нагрузке админу %s", admin_id)
                except Exception as e:
                    logging.error("Ошибка отправки предупреждения админу %s: %s", admin_id, e)
    
    except Exception as e:
        logging.error("Ошибка при проверке нагрузки системы: %s", e)

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
        
        # Регистрируем обработчик callback кнопок
        callback_handler = CallbackQueryHandler(button_callback)
        dispatcher.add_handler(callback_handler)
        
        # Запускаем планировщик периодических отчетов
        job_queue = updater.job_queue
        job_queue.run_repeating(
            send_status_report, 
            interval=STATUS_REPORT_INTERVAL,
            first=300  # Первый отчет через 5 минут после запуска
        )
        logging.info("Планировщик периодических отчетов запущен. Интервал: %s секунд", STATUS_REPORT_INTERVAL)
        
        # Запускаем планировщик проверки нагрузки системы
        job_queue.run_repeating(
            check_system_load,
            interval=600,  # Проверяем каждые 10 минут
            first=120  # Первая проверка через 2 минуты после запуска
        )
        logging.info("Планировщик проверки нагрузки системы запущен. Интервал: 600 секунд")
        
        # Удаляем проблемную строку, которая вызывает ошибку
        # Просто информируем о регистрации обработчиков
        logging.info("Обработчики команд и callback зарегистрированы")
        
        # Запуск бота с подробным логированием
        logging.info("Запускаем polling...")
        print("Бот запущен. Нажмите Ctrl+C для остановки.")
        
        # Запускаем бота с более частой проверкой обновлений и подробным логированием
        updater.start_polling(poll_interval=1.0, timeout=30, drop_pending_updates=False, read_latency=2.0)
        logging.info("Polling запущен успешно")
        updater.idle()
        
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
        print("Бот остановлен пользователем")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.critical("Критическая ошибка при запуске бота: %s", e, exc_info=True)
        print(f"Критическая ошибка при запуске бота: {e}")
