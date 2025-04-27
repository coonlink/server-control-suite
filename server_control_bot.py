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

# Импортируем модуль локализации
try:
    from utilities import get_text, get_user_language, set_user_language, load_localization_config
    LOCALIZATION_AVAILABLE = True
    logging.info("Модуль локализации подключен успешно")
    # Загружаем конфигурацию локализации
    LOCALIZATION_CONFIG = load_localization_config()
except ImportError:
    LOCALIZATION_AVAILABLE = False
    logging.warning("Модуль локализации не найден, используем значения по умолчанию")
    LOCALIZATION_CONFIG = {
        "DEFAULT_LANGUAGE": "en",
        "MULTI_LANGUAGE_SUPPORT": False
    }

# Более радикальный способ обхода проблем с импортом
def patch_telegram_dependencies():
    """Патчит систему импорта для решения проблем с отсутствующими модулями"""
    
    # Патч для imghdr
    if 'imghdr' not in sys.modules:
        try:
            import imghdr
        except ImportError:
            class ImghdrStub:
                def what(self, *args, **kwargs):
                    return None
            
            sys.modules['imghdr'] = ImghdrStub()
            print("Создана заглушка для модуля imghdr")
    
    # Патч для urllib3.contrib.appengine - создаем структуру модулей
    if 'urllib3.contrib.appengine' not in sys.modules:
        try:
            import urllib3.contrib.appengine
        except ImportError:
            try:
                # Проверяем, есть ли urllib3
                import urllib3
                
                # Создаем модуль contrib если его нет
                if not hasattr(urllib3, 'contrib'):
                    class ContribModule:
                        pass
                    urllib3.contrib = ContribModule()
                    sys.modules['urllib3.contrib'] = urllib3.contrib
                
                # Создаем модуль appengine
                class AppEngineModule:
                    @staticmethod
                    def is_appengine_sandbox():
                        return False
                    
                # Регистрируем модуль в системе
                urllib3.contrib.appengine = AppEngineModule()
                sys.modules['urllib3.contrib.appengine'] = urllib3.contrib.appengine
                
                print("Создана заглушка для модуля urllib3.contrib.appengine")
            except ImportError:
                print("Не удалось создать заглушку для urllib3.contrib.appengine - отсутствует urllib3")
    
    # Патчим telegram.utils.request напрямую, если возможно
    def patch_telegram_request():
        try:
            # Попытка импортировать модуль telegram.utils.request
            import importlib
            request_module = importlib.import_module('telegram.utils.request')
            
            # Переопределяем функцию is_appengine_sandbox
            original_is_appengine = getattr(request_module, '_is_appengine_sandbox', None)
            if original_is_appengine:
                def patched_is_appengine_sandbox():
                    return False
                
                request_module._is_appengine_sandbox = patched_is_appengine_sandbox
                print("Успешно патчим функцию _is_appengine_sandbox в telegram.utils.request")
                return True
        except Exception as e:
            print(f"Не удалось патчить telegram.utils.request: {e}")
            return False
    
    return patch_telegram_request()

# Применяем патчи перед импортом
patched = patch_telegram_dependencies()

# Импортируем с обработкой ошибок
MAX_IMPORT_ATTEMPTS = 3
for attempt in range(MAX_IMPORT_ATTEMPTS):
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
        from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
        print("Библиотека python-telegram-bot успешно импортирована")
        break
    except ImportError as e:
        logging.error("Ошибка импорта библиотеки python-telegram-bot (попытка %d/%d): %s", 
                     attempt + 1, MAX_IMPORT_ATTEMPTS, e)
        
        if attempt == MAX_IMPORT_ATTEMPTS - 1:
            logging.critical("Не удалось импортировать python-telegram-bot после %d попыток", MAX_IMPORT_ATTEMPTS)
            print(f"Критическая ошибка: {e}")
            print("Для решения выполните следующие действия:")
            print("1. Установите все необходимые зависимости: pip install python-telegram-bot==13.7 urllib3")
            print("2. Если это не помогает, попробуйте установить старую версию urllib3: pip install urllib3==1.26.6")
            print("3. Если проблема сохраняется, проверьте совместимость версий Python и python-telegram-bot")
            sys.exit(1)
        
        # Еще одна попытка патча перед следующей попыткой импорта
        print(f"Повторная попытка через 1 секунду ({attempt + 1}/{MAX_IMPORT_ATTEMPTS})...")
        time.sleep(1)
        patch_telegram_dependencies()

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Конфигурация - используем относительные пути
CONFIG_FILE = os.path.join(BASE_DIR, "critical_processes_config.sh")
CREDENTIALS_FILE = os.path.join(BASE_DIR, ".telegram_credentials")
LOG_FILE = os.path.join(BASE_DIR, "server_control_bot.log")
HISTORY_FILE = os.path.join(BASE_DIR, "server_stats_history.json")

# Проверяем доступность директории для логов и создаем файл если нужно
log_dir = os.path.dirname(LOG_FILE)
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir, exist_ok=True)
        print(f"Создана директория для логов: {log_dir}")
    except Exception as e:
        print(f"Ошибка при создании директории для логов: {e}")
        # Используем директорию по умолчанию
        LOG_FILE = "server_control_bot.log"
        print(f"Используем файл логов в текущей директории: {LOG_FILE}")

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

def get_main_keyboard(user_id=None):
    """
    Создает основную клавиатуру бота.
    
    Args:
        user_id (int, optional): ID пользователя для локализации
        
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [
            InlineKeyboardButton(_("buttons.status", user_id), callback_data="status"),
            InlineKeyboardButton(_("buttons.processes", user_id), callback_data="processes")
        ],
        [
            InlineKeyboardButton(_("buttons.optimize", user_id), callback_data="optimize"),
            InlineKeyboardButton(_("buttons.logs", user_id), callback_data="logs")
        ],
        [
            InlineKeyboardButton(_("buttons.stats", user_id), callback_data="stats"),
            InlineKeyboardButton(_("buttons.settings", user_id), callback_data="settings")
        ],
        [
            InlineKeyboardButton(_("buttons.cleanup", user_id), callback_data="cleanup"),
            InlineKeyboardButton(_("buttons.night_mode", user_id), callback_data="night_mode")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_processes_keyboard(user_id=None):
    """
    Создает клавиатуру для управления процессами.
    
    Args:
        user_id (int, optional): ID пользователя для локализации
        
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [
            InlineKeyboardButton(_("buttons.show_all", user_id), callback_data="show_all_processes"),
            InlineKeyboardButton(_("buttons.heavy_processes", user_id), callback_data="heavy_processes")
        ],
        [
            InlineKeyboardButton(_("buttons.limit_cpu", user_id), callback_data="limit_cpu"),
            InlineKeyboardButton(_("buttons.clear_memory", user_id), callback_data="clear_memory")
        ],
        [
            InlineKeyboardButton(_("buttons.memory_stats", user_id), callback_data="memory_stats"),
            InlineKeyboardButton(_("buttons.load_history", user_id), callback_data="load_history")
        ],
        [
            InlineKeyboardButton(_("buttons.back", user_id), callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(user_id=None):
    """
    Создает клавиатуру для настроек.
    
    Args:
        user_id (int, optional): ID пользователя для локализации
        
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [
            InlineKeyboardButton(_("buttons.notifications", user_id), callback_data="notification_settings"),
            InlineKeyboardButton(_("buttons.cpu_limits", user_id), callback_data="cpu_limits")
        ],
        [
            InlineKeyboardButton(_("buttons.memory_limits", user_id), callback_data="memory_limits"),
            InlineKeyboardButton(_("buttons.schedule", user_id), callback_data="schedule_settings")
        ],
        [
            InlineKeyboardButton(_("buttons.back", user_id), callback_data="main_menu")
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

# Функция для получения локализованного текста
def _(key, user_id=None):
    """
    Получает локализованный текст по ключу для конкретного пользователя
    
    Args:
        key (str): Ключ текста в формате 'раздел.ключ'
        user_id (int, optional): ID пользователя для определения языка
    
    Returns:
        str: Локализованный текст или сам ключ, если текст не найден
    """
    if not LOCALIZATION_AVAILABLE:
        # Используем хардкодированные значения если модуль не доступен
        text_map = {
            "main.welcome": "🤖 Панель управления сервером v1.0",
            "main.new_features": "🆕 Новые функции:",
            "main.feature_stats": "- 📈 Статистика и история нагрузки",
            "main.feature_night": "- 🌙 Ночной режим",
            "main.feature_settings": "- ⚙️ Расширенные настройки",
            "main.feature_notifications": "- 🔔 Настраиваемые уведомления",
            "main.select_action": "Выберите действие:",
            "messages.unauthorized": "⛔ У вас нет доступа к этому боту."
        }
        return text_map.get(key, key)
    
    # Определяем язык пользователя
    lang_code = LOCALIZATION_CONFIG["DEFAULT_LANGUAGE"]
    if user_id is not None and LOCALIZATION_CONFIG.get("MULTI_LANGUAGE_SUPPORT", False):
        lang_code = get_user_language(user_id)
    
    # Получаем локализованный текст
    return get_text(key, lang_code)

# Функция для получения клавиатуры выбора языка
def get_language_keyboard():
    """
    Создает клавиатуру для выбора языка.
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [
            InlineKeyboardButton(
                LOCALIZATION_CONFIG.get("LANG_BUTTON_EN", "🇬🇧 English"), 
                callback_data="set_lang_en"
            ),
            InlineKeyboardButton(
                LOCALIZATION_CONFIG.get("LANG_BUTTON_RU", "🇷🇺 Русский"), 
                callback_data="set_lang_ru"
            )
        ],
        [
            InlineKeyboardButton(_("buttons.back", None), callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Обработчики команд
def start_command(update: Update, _context: CallbackContext):
    """Обработчик команд /start и /help."""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        update.message.reply_text(_("messages.unauthorized", user_id))
        return
    
    update.message.reply_text(
        f"{_('main.welcome', user_id)}\n\n"
        f"{_('main.new_features', user_id)}\n"
        f"{_('main.feature_stats', user_id)}\n"
        f"{_('main.feature_night', user_id)}\n"
        f"{_('main.feature_settings', user_id)}\n"
        f"{_('main.feature_notifications', user_id)}\n\n"
        f"{_('main.select_action', user_id)}",
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

def language_command(update: Update, _context: CallbackContext):
    """Обработчик команды /language."""
    if not is_authorized(update.effective_user.id):
        update.message.reply_text(_("messages.unauthorized"))
        return
    
    if not LOCALIZATION_AVAILABLE or not LOCALIZATION_CONFIG.get("USER_LANGUAGE_SELECTION", False):
        update.message.reply_text(_("messages.stats_unavailable", update.effective_user.id))
        return
    
    update.message.reply_text(
        LOCALIZATION_CONFIG.get("LANG_MENU_TITLE", "Select language / Выберите язык:"),
        reply_markup=get_language_keyboard()
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
        logging.info("Успешно отправлен ответ на callback")
    except Exception as e:
        logging.error("Ошибка при ответе на callback: %s", e)
    
    if not is_authorized(query.from_user.id):
        try:
            query.edit_message_text(_("messages.unauthorized", query.from_user.id))
            logging.warning("Попытка неавторизованного доступа от ID: %s", 
                           query.from_user.id)
        except Exception as e:
            logging.error("Ошибка при отправке сообщения о неавторизованном доступе: %s", e)
        return

    # Обработка выбора языка
    if query.data.startswith("set_lang_"):
        lang_code = query.data.replace("set_lang_", "")
        if LOCALIZATION_AVAILABLE:
            if set_user_language(query.from_user.id, lang_code):
                success_key = f"LANG_SELECTED_{lang_code.upper()}"
                success_msg = LOCALIZATION_CONFIG.get(success_key, f"Language set to {lang_code}")
                query.edit_message_text(
                    success_msg,
                    reply_markup=get_main_keyboard(query.from_user.id)
                )
                logging.info("Пользователь %s установил язык: %s", query.from_user.id, lang_code)
            else:
                query.edit_message_text(
                    "❌ Error setting language",
                    reply_markup=get_language_keyboard()
                )
        else:
            query.edit_message_text(
                "🌐 Language selection is not available",
                reply_markup=get_main_keyboard(query.from_user.id)
            )
        return

    action = query.data
    
    try:
        logging.info("Начинаем обработку действия: %s", action)
        
        # Оборачиваем каждое редактирование сообщения в try-except для обнаружения конкретных ошибок
        if action == "stats":
            try:
                # Использование синхронного подхода вместо асинхронного
                stats_text = "📈 Статистика недоступна в этой версии"
                
                query.edit_message_text(
                    stats_text,
                    reply_markup=get_main_keyboard(query.from_user.id),
                    parse_mode="HTML"
                )
                logging.info("Успешно обработано действие: %s", action)
            except Exception as e:
                logging.error("Ошибка при обработке действия '%s': %s", action, e)
        
        elif action == "night_mode":
            try:
                # Запрос подтверждения перед включением ночного режима
                keyboard = [
                    [
                        InlineKeyboardButton(_("buttons.confirm_yes", query.from_user.id), callback_data="confirm_night_mode"),
                        InlineKeyboardButton(_("buttons.confirm_no", query.from_user.id), callback_data="main_menu")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    _("messages.night_mode_confirm", query.from_user.id),
                    reply_markup=reply_markup
                )
                logging.info("Успешно обработано действие: %s", action)
            except Exception as e:
                logging.error("Ошибка при обработке действия '%s': %s", action, e)
        
        elif action == "confirm_night_mode":
            try:
                # Включаем ночной режим после подтверждения
                night_script = os.path.join(BASE_DIR, "night_optimize.sh")
                logging.info("Пытаемся запустить скрипт: %s", night_script)
                # Проверяем существование скрипта
                if not os.path.exists(night_script):
                    logging.error("Скрипт %s не найден", night_script)
                    query.edit_message_text(
                        f"❌ Ошибка: скрипт {night_script} не найден",
                        reply_markup=get_main_keyboard(query.from_user.id)
                    )
                    return
                    
                # Запускаем скрипт с обработкой возможных ошибок
                try:
                    with subprocess.Popen([night_script]) as _:
                        pass
                    logging.info("Скрипт %s успешно запущен", night_script)
                except Exception as script_err:
                    logging.error("Ошибка при запуске скрипта %s: %s", night_script, script_err)
                    query.edit_message_text(
                        f"❌ Ошибка при запуске ночного режима: {str(script_err)}",
                        reply_markup=get_main_keyboard(query.from_user.id)
                    )
                    return
                
                query.edit_message_text(
                    _("messages.night_mode_activated", query.from_user.id),
                    reply_markup=get_main_keyboard(query.from_user.id)
                )
                logging.info("Успешно обработано действие: %s", action)
            except Exception as e:
                logging.error("Ошибка при обработке действия '%s': %s", action, e)
        
        elif action == "settings":
            try:
                query.edit_message_text(
                    _("messages.settings_title", query.from_user.id),
                    reply_markup=get_settings_keyboard(query.from_user.id)
                )
                logging.info("Успешно обработано действие: %s", action)
            except Exception as e:
                logging.error("Ошибка при обработке действия '%s': %s", action, e)
        
        elif action == "status":
            try:
                status_script = os.path.join(BASE_DIR, "check_server_status.sh")
                success, result, error = run_script_safely(status_script, query, args=["--silent"], timeout=15)
                
                if success:
                    query.edit_message_text(
                        f"📊 Статус сервера:\n\n{result}",
                        reply_markup=get_main_keyboard(query.from_user.id)
                    )
                    logging.info("Успешно обработано действие: %s", action)
                # В случае неудачи сообщение об ошибке уже будет показано в run_script_safely
            except Exception as e:
                logging.error("Неожиданная ошибка при обработке действия '%s': %s", action, e, exc_info=True)
                try:
                    query.edit_message_text(
                        f"❌ Неожиданная ошибка при получении статуса: {str(e)}",
                        reply_markup=get_main_keyboard(query.from_user.id)
                    )
                except Exception as edit_err:
                    logging.error("Не удалось обновить сообщение: %s", edit_err)
        
        elif action == "processes":
            # Запрос подтверждения перед управлением процессами
            keyboard = [
                [
                    InlineKeyboardButton(_("buttons.confirm_yes", query.from_user.id), callback_data="confirm_processes"),
                    InlineKeyboardButton(_("buttons.confirm_no", query.from_user.id), callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                _("messages.processes_confirm", query.from_user.id),
                reply_markup=reply_markup
            )
        
        elif action == "confirm_processes":
            # Показываем меню управления процессами после подтверждения
            query.edit_message_text(
                _("messages.processes_title", query.from_user.id),
                reply_markup=get_processes_keyboard(query.from_user.id)
            )
        
        elif action == "optimize":
            # Запрос подтверждения перед оптимизацией
            keyboard = [
                [
                    InlineKeyboardButton(_("buttons.confirm_yes", query.from_user.id), callback_data="confirm_optimize"),
                    InlineKeyboardButton(_("buttons.confirm_no", query.from_user.id), callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                _("messages.optimize_confirm", query.from_user.id),
                reply_markup=reply_markup
            )
        
        elif action == "confirm_optimize":
            try:
                # Запускаем оптимизацию после подтверждения
                optimize_script = os.path.join(BASE_DIR, "optimize_server.sh")
                
                # Просто запускаем скрипт в фоне, не ждем результат
                success, _, error = run_script_safely(optimize_script, query, timeout=5)
                
                if success:
                    query.edit_message_text(
                        _("messages.optimize_started", query.from_user.id),
                        reply_markup=get_main_keyboard(query.from_user.id)
                    )
                    logging.info("Успешно обработано действие: %s", action)
                # В случае неудачи сообщение об ошибке уже будет показано в run_script_safely
            except Exception as e:
                logging.error("Неожиданная ошибка при обработке действия '%s': %s", action, e, exc_info=True)
                try:
                    query.edit_message_text(
                        f"❌ Неожиданная ошибка при запуске оптимизации: {str(e)}",
                        reply_markup=get_main_keyboard(query.from_user.id)
                    )
                except Exception as edit_err:
                    logging.error("Не удалось обновить сообщение: %s", edit_err)
        
        elif action == "logs":
            query.edit_message_text(
                _("messages.logs_title", query.from_user.id),
                reply_markup=get_processes_keyboard(query.from_user.id)
            )
        
        elif action == "cleanup":
            # Запрос подтверждения перед очисткой кэша
            keyboard = [
                [
                    InlineKeyboardButton(_("buttons.confirm_yes", query.from_user.id), callback_data="confirm_cleanup"),
                    InlineKeyboardButton(_("buttons.confirm_no", query.from_user.id), callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                _("messages.cleanup_confirm", query.from_user.id),
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
                    _("messages.cleanup_done", query.from_user.id),
                    reply_markup=get_main_keyboard(query.from_user.id)
                )
            except subprocess.CalledProcessError as e:
                logging.error("Ошибка очистки кэша: %s", e)
                error_msg = e.stderr.decode() if e.stderr else str(e)
                query.edit_message_text(
                    _("messages.cleanup_error", query.from_user.id).format(error=error_msg),
                    reply_markup=get_main_keyboard(query.from_user.id)
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
                    f"{_('messages.top_processes_title', query.from_user.id)}\n\n<pre>{result}</pre>",
                    parse_mode="HTML",
                    reply_markup=get_processes_keyboard(query.from_user.id)
                )
            except subprocess.CalledProcessError as e:
                logging.error("Ошибка получения списка процессов: %s", e)
                query.edit_message_text(
                    _("messages.command_error", query.from_user.id).format(error=e.output),
                    reply_markup=get_processes_keyboard(query.from_user.id)
                )
        
        elif action == "heavy_processes":
            try:
                heavy_script = os.path.join(BASE_DIR, "monitor_heavy_processes.sh")
                cmd = [heavy_script, "--analyze"]
                result = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, universal_newlines=True
                )
                query.edit_message_text(
                    f"{_('messages.heavy_processes_title', query.from_user.id)}\n\n{result}",
                    reply_markup=get_processes_keyboard(query.from_user.id)
                )
            except subprocess.CalledProcessError as e:
                logging.error("Ошибка анализа тяжелых процессов: %s", e)
                query.edit_message_text(
                    _("messages.heavy_processes_error", query.from_user.id).format(error=e.output),
                    reply_markup=get_processes_keyboard(query.from_user.id)
                )
        
        elif action == "main_menu":
            query.edit_message_text(
                f"{_('messages.main_menu', query.from_user.id)}",
                reply_markup=get_main_keyboard(query.from_user.id)
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
                        _("messages.logs_template", query.from_user.id).format(log_file=log_file) + f"\n\n<pre>{result}</pre>",
                        parse_mode="HTML",
                        reply_markup=get_processes_keyboard(query.from_user.id)
                    )
                except subprocess.CalledProcessError as e:
                    logging.error("Ошибка чтения лог-файла %s: %s", log_file, e)
                    query.edit_message_text(
                        _("messages.command_error", query.from_user.id).format(error=e.output),
                        reply_markup=get_processes_keyboard(query.from_user.id)
                    )
        else:
            query.edit_message_text(
                _("messages.unknown_action", query.from_user.id).format(action=action),
                reply_markup=get_main_keyboard(query.from_user.id)
            )
    
    except subprocess.SubprocessError as e:
        logging.error("Ошибка выполнения subprocess при обработке callback %s: %s", action, e)
        try:
            query.edit_message_text(
                f"❌ Ошибка выполнения команды: {str(e)}",
                reply_markup=get_main_keyboard(query.from_user.id)
            )
        except Exception as edit_err:
            logging.error("Не удалось отредактировать сообщение: %s", edit_err)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Ошибка при обработке callback %s: %s", action, e, exc_info=True)
        try:
            query.edit_message_text(
                f"❌ Неожиданная ошибка: {str(e)}",
                reply_markup=get_main_keyboard(query.from_user.id)
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
        return _("errors.status_script_error", None).format(error=e.output)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Неожиданная ошибка при получении статуса: %s", e)
        return _("errors.unexpected", None).format(error=str(e))

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
    
    # Отправляем сообщение всем администраторам на их языке
    for admin_id in config['AUTHORIZED_ADMINS']:
        try:
            message = f"{_('report.title', admin_id)}\n\n" \
                    f"{_('report.time', admin_id).format(timestamp=timestamp)}\n" \
                    f"{_('report.host', admin_id).format(hostname=hostname)}\n\n" \
                    f"{status}"
            
            context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="Markdown"
            )
            logging.info("Отправлен периодический отчет администратору %s", admin_id)
        except Exception as e:
            logging.error(_("errors.report_sending", None).format(admin_id=admin_id, error=e))

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
            # Для каждого админа отправляем на его языке
            for admin_id in config['AUTHORIZED_ADMINS']:
                message = f"{_('report.load_warning', admin_id).format(load=f'{one_min_load:.2f}')}\n\n"
                message += f"{_('report.recommended_actions', admin_id)}"
                
                # Формируем клавиатуру с быстрыми действиями
                keyboard = [
                    [
                        InlineKeyboardButton(_("buttons.optimize", admin_id), callback_data="optimize"),
                        InlineKeyboardButton(_("buttons.heavy_processes", admin_id), callback_data="heavy_processes")
                    ],
                    [
                        InlineKeyboardButton(_("buttons.status", admin_id), callback_data="status"),
                        InlineKeyboardButton(_("buttons.night_mode", admin_id), callback_data="night_mode")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
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

# Функция-помощник для проверки и запуска внешних скриптов
def run_script_safely(script_path, query, args=None, timeout=30):
    """
    Безопасно запускает внешний скрипт с обработкой ошибок.
    
    Args:
        script_path (str): Путь к скрипту
        query: Объект callback query для обновления сообщения при ошибке
        args (list, optional): Дополнительные аргументы для скрипта. По умолчанию None.
        timeout (int, optional): Таймаут выполнения скрипта в секундах. По умолчанию 30.
        
    Returns:
        tuple: (success (bool), output (str), error (str))
    """
    logging.info("Пытаемся запустить скрипт: %s", script_path)
    
    # Проверяем существование скрипта
    if not os.path.exists(script_path):
        error_msg = f"Скрипт {script_path} не найден"
        logging.error(error_msg)
        try:
            query.edit_message_text(
                f"❌ Ошибка: {error_msg}",
                reply_markup=get_main_keyboard(query.from_user.id)
            )
        except Exception as edit_err:
            logging.error("Не удалось обновить сообщение: %s", edit_err)
        return False, "", error_msg
    
    # Проверяем права на выполнение
    if not os.access(script_path, os.X_OK):
        logging.warning("Скрипт %s не имеет прав на выполнение, пробуем установить", script_path)
        try:
            os.chmod(script_path, 0o755)
            logging.info("Установлены права на выполнение для %s", script_path)
        except Exception as chmod_err:
            error_msg = f"Не удалось установить права на выполнение для {script_path}: {chmod_err}"
            logging.error(error_msg)
            try:
                query.edit_message_text(
                    f"❌ Ошибка: {error_msg}",
                    reply_markup=get_main_keyboard(query.from_user.id)
                )
            except Exception as edit_err:
                logging.error("Не удалось обновить сообщение: %s", edit_err)
            return False, "", error_msg
    
    # Подготавливаем команду
    cmd = [script_path]
    if args:
        cmd.extend(args)
    
    logging.info("Выполняем команду: %s", " ".join(cmd))
    
    # Запускаем скрипт и получаем результат
    try:
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=timeout
        )
        logging.info("Скрипт успешно выполнен")
        return True, output, ""
    except subprocess.TimeoutExpired as timeout_err:
        error_msg = f"Таймаут выполнения скрипта (превышено {timeout} секунд)"
        logging.error(error_msg)
        try:
            query.edit_message_text(
                f"❌ Ошибка: {error_msg}",
                reply_markup=get_main_keyboard(query.from_user.id)
            )
        except Exception as edit_err:
            logging.error("Не удалось обновить сообщение: %s", edit_err)
        return False, "", error_msg
    except subprocess.CalledProcessError as e:
        error_output = e.output if hasattr(e, 'output') else str(e)
        error_msg = f"Ошибка выполнения скрипта (код {e.returncode}): {error_output}"
        logging.error(error_msg)
        try:
            query.edit_message_text(
                f"❌ Ошибка: {error_msg}",
                reply_markup=get_main_keyboard(query.from_user.id)
            )
        except Exception as edit_err:
            logging.error("Не удалось обновить сообщение: %s", edit_err)
        return False, "", error_msg
    except Exception as e:
        error_msg = f"Неожиданная ошибка при выполнении скрипта: {str(e)}"
        logging.error(error_msg)
        try:
            query.edit_message_text(
                f"❌ Ошибка: {error_msg}",
                reply_markup=get_main_keyboard(query.from_user.id)
            )
        except Exception as edit_err:
            logging.error("Не удалось обновить сообщение: %s", edit_err)
        return False, "", error_msg

# Запуск бота
if __name__ == '__main__':
    try:
        logging.info("Бот запущен")
        
        # Проверяем наличие всех необходимых скриптов
        required_scripts = [
            "check_server_status.sh",
            "optimize_server.sh",
            "monitor_heavy_processes.sh"
        ]
        missing_scripts = []
        
        for script in required_scripts:
            script_path = os.path.join(BASE_DIR, script)
            if not os.path.exists(script_path):
                missing_scripts.append(script)
                logging.error("Скрипт %s не найден!", script)
            elif not os.access(script_path, os.X_OK):
                try:
                    os.chmod(script_path, 0o755)
                    logging.info("Установлены права на выполнение для %s", script_path)
                except Exception as e:
                    logging.error("Не удалось установить права на выполнение для %s: %s", script_path, e)
        
        if missing_scripts:
            print(f"ВНИМАНИЕ! Отсутствуют следующие скрипты: {', '.join(missing_scripts)}")
            print("Некоторые функции бота могут быть недоступны!")
        
        # Создаем Updater и передаем ему токен бота
        updater = Updater(config['BOT_TOKEN'])
        
        # Получаем диспетчер для регистрации обработчиков
        dispatcher = updater.dispatcher
        
        # Регистрируем обработчики
        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(CommandHandler("help", start_command))
        
        # Регистрируем обработчик выбора языка
        if LOCALIZATION_AVAILABLE and LOCALIZATION_CONFIG.get("USER_LANGUAGE_SELECTION", False):
            dispatcher.add_handler(CommandHandler("language", language_command))
            logging.info("Обработчик команды выбора языка зарегистрирован")
        
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


