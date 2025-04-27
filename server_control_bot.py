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
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# Конфигурация
CONFIG_FILE = "/root/critical_processes_config.sh"
CREDENTIALS_FILE = "/root/.telegram_credentials"
LOG_FILE = "/var/log/server_control_bot.log"
HISTORY_FILE = "/var/log/server_stats_history.json"

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
bot = Bot(token=config['BOT_TOKEN'])
dp = Dispatcher(bot)

def get_main_keyboard():
    """
    Создает основную клавиатуру бота.
    
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Статус", callback_data="status"),
        InlineKeyboardButton("🔄 Процессы", callback_data="processes"),
        InlineKeyboardButton("⚡ Оптимизация", callback_data="optimize"),
        InlineKeyboardButton("📝 Логи", callback_data="logs"),
        InlineKeyboardButton("📈 Статистика", callback_data="stats"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        InlineKeyboardButton("❌ Очистка", callback_data="cleanup"),
        InlineKeyboardButton("🌙 Ночной режим", callback_data="night_mode")
    )
    return keyboard

def get_processes_keyboard():
    """
    Создает клавиатуру для управления процессами.
    
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔍 Показать все", callback_data="show_all_processes"),
        InlineKeyboardButton("⚠️ Тяжелые процессы", callback_data="heavy_processes"),
        InlineKeyboardButton("🛑 Ограничить CPU", callback_data="limit_cpu"),
        InlineKeyboardButton("🗑️ Очистить память", callback_data="clear_memory"),
        InlineKeyboardButton("💾 Статистика памяти", callback_data="memory_stats"),
        InlineKeyboardButton("📊 История нагрузки", callback_data="load_history"),
        InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    )
    return keyboard

def get_settings_keyboard():
    """
    Создает клавиатуру для настроек.
    
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔔 Уведомления", callback_data="notification_settings"),
        InlineKeyboardButton("⚡ Лимиты CPU", callback_data="cpu_limits"),
        InlineKeyboardButton("💾 Лимиты памяти", callback_data="memory_limits"),
        InlineKeyboardButton("🕒 Расписание", callback_data="schedule_settings"),
        InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    )
    return keyboard

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
        
        if isinstance(result, str):
            result = f"{result}\n\n<i>⚡ Сгенерировано за {generation_time:.1f}мс</i>"
        elif isinstance(result, types.Message):
            if result.text:
                await result.edit_text(
                    f"{result.text}\n\n<i>⚡ Сгенерировано за {generation_time:.1f}мс</i>",
                    reply_markup=result.reply_markup,
                    parse_mode="HTML"
                )
        return result
    return wrapper

@dp.message_handler(commands=['start', 'help'])
@measure_time
async def send_welcome(message: types.Message):
    """
    Обработчик команд /start и /help.
    
    Args:
        message (types.Message): Объект сообщения
        
    Returns:
        types.Message: Ответное сообщение
    """
    if not is_authorized(message.from_user.id):
        return await message.reply("⛔ У вас нет доступа к этому боту.")
    
    return await message.reply(
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

@dp.callback_query_handler(lambda c: True)
@measure_time
async def process_callback(callback_query: types.CallbackQuery):
    """
    Обработчик нажатий на кнопки.
    
    Args:
        callback_query (types.CallbackQuery): Объект запроса обратного вызова
        
    Returns:
        types.Message: Ответное сообщение
    """
    if not is_authorized(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет доступа к этому действию.")
        return
    
    action = callback_query.data
    
    try:
        if action == "stats":
            # Получаем статистику за последние 24 часа
            history = await get_stats_history(24)
            if history:
                stats_text = "📈 Статистика за 24 часа:\n\n"
                for entry in history[-5:]:  # Показываем последние 5 записей
                    timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
                    stats = entry['stats']
                    stats_text += f"🕒 {timestamp}\n"
                    stats_text += f"CPU: {stats.get('cpu', 'N/A')}%\n"
                    stats_text += f"RAM: {stats.get('memory', 'N/A')}%\n"
                    stats_text += "-------------------\n"
            else:
                stats_text = "📊 Статистика пока не накоплена"
            
            await callback_query.message.edit_text(
                stats_text,
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
        
        elif action == "night_mode":
            # Включаем ночной режим
            subprocess.Popen(["/root/night_optimize.sh"])
            await callback_query.message.edit_text(
                "🌙 Ночной режим активирован\n"
                "- Ограничение CPU: 5%\n"
                "- Отложенные задачи активированы\n"
                "- Неприоритетные сервисы приостановлены",
                reply_markup=get_main_keyboard()
            )
        
        elif action == "settings":
            await callback_query.message.edit_text(
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
                await callback_query.message.edit_text(
                    f"📊 Статус сервера:\n\n{result}",
                    reply_markup=get_main_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка выполнения скрипта статуса: {e}")
                await callback_query.message.edit_text(
                    f"❌ Ошибка получения статуса: {e.output}",
                    reply_markup=get_main_keyboard()
                )
        
        elif action == "processes":
            await callback_query.message.edit_text(
                "🔄 Управление процессами:",
                reply_markup=get_processes_keyboard()
            )
        
        elif action == "optimize":
            subprocess.Popen(["/root/optimize_server.sh"])
            await callback_query.message.edit_text(
                "⚡ Оптимизация запущена\n"
                "Результаты будут отправлены после завершения.",
                reply_markup=get_main_keyboard()
            )
        
        elif action == "logs":
            await callback_query.message.edit_text(
                "📝 Выберите тип логов:",
                reply_markup=get_processes_keyboard()
            )
        
        elif action == "cleanup":
            try:
                subprocess.run("sync && echo 3 > /proc/sys/vm/drop_caches", 
                               shell=True, 
                               check=True, 
                               stderr=subprocess.PIPE)
                await callback_query.message.edit_text(
                    "🧹 Очистка кэша выполнена",
                    reply_markup=get_main_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка очистки кэша: {e}")
                await callback_query.message.edit_text(
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
                
                await callback_query.message.edit_text(
                    f"📊 Топ процессов по CPU:\n\n<pre>{result}</pre>",
                    parse_mode="HTML",
                    reply_markup=get_processes_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка получения списка процессов: {e}")
                await callback_query.message.edit_text(
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
                await callback_query.message.edit_text(
                    f"⚠️ Тяжелые процессы:\n\n{result}",
                    reply_markup=get_processes_keyboard()
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка анализа тяжелых процессов: {e}")
                await callback_query.message.edit_text(
                    f"❌ Ошибка анализа процессов: {e.output}",
                    reply_markup=get_processes_keyboard()
                )
        
        elif action == "main_menu":
            await callback_query.message.edit_text(
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
                    await callback_query.message.edit_text(
                        f"📝 Последние логи ({log_file}):\n\n<pre>{result}</pre>",
                        parse_mode="HTML",
                        reply_markup=get_processes_keyboard()
                    )
                except subprocess.CalledProcessError as e:
                    logging.error(f"Ошибка чтения лог-файла {log_file}: {e}")
                    await callback_query.message.edit_text(
                        f"❌ Ошибка чтения лог-файла: {e.output}",
                        reply_markup=get_processes_keyboard()
                    )
        else:
            await callback_query.message.edit_text(
                f"⚠️ Неизвестное действие: {action}",
                reply_markup=get_main_keyboard()
            )
    
    except subprocess.SubprocessError as e:
        logging.error(f"Ошибка выполнения subprocess при обработке callback {action}: {e}")
        await callback_query.message.edit_text(
            f"❌ Ошибка выполнения команды: {str(e)}",
            reply_markup=get_main_keyboard()
        )
    except asyncio.CancelledError:
        logging.warning(f"Операция отменена для callback {action}")
        raise
    except Exception as e:
        logging.error(f"Ошибка при обработке callback {action}: {e}", exc_info=True)
        await callback_query.message.edit_text(
            f"❌ Неожиданная ошибка: {str(e)}",
            reply_markup=get_main_keyboard()
        )
    
    await callback_query.answer()

async def stats_collector():
    """
    Периодический сбор статистики о системе.
    Запускается в фоновом режиме и сохраняет данные каждые 5 минут.
    """
    while True:
        try:
            # Собираем текущую статистику с помощью более безопасных команд
            cpu_process = subprocess.run(
                ["top", "-bn1"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            cpu_usage = subprocess.run(
                ["grep", "Cpu(s)", "-"], 
                input=cpu_process.stdout,
                capture_output=True, 
                text=True, 
                check=True
            )
            cpu_value = subprocess.run(
                ["awk", "{print $2}"], 
                input=cpu_usage.stdout,
                capture_output=True, 
                text=True, 
                check=True
            )
            
            memory_process = subprocess.run(
                ["free"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            memory_usage = subprocess.run(
                ["grep", "Mem"], 
                input=memory_process.stdout,
                capture_output=True, 
                text=True, 
                check=True
            )
            memory_value = subprocess.run(
                ["awk", "{print $3/$2 * 100.0}"], 
                input=memory_usage.stdout,
                capture_output=True, 
                text=True, 
                check=True
            )
            
            stats = {
                'cpu': float(cpu_value.stdout.strip()),
                'memory': float(memory_value.stdout.strip())
            }
            
            # Сохраняем статистику
            await save_stats_history(stats)
            
        except ValueError as e:
            logging.error(f"Ошибка преобразования данных статистики: {e}")
        except subprocess.SubprocessError as e:
            logging.error(f"Ошибка выполнения команд статистики: {e}")
        except Exception as e:
            logging.error(f"Непредвиденная ошибка сбора статистики: {e}", exc_info=True)
        
        try:
            await asyncio.sleep(300)  # Собираем статистику каждые 5 минут
        except asyncio.CancelledError:
            logging.info("Сборщик статистики остановлен")
            break

# Запуск бота
if __name__ == '__main__':
    try:
        logging.info("Бот запущен")
        
        # Запускаем сборщик статистики
        loop = asyncio.get_event_loop()
        loop.create_task(stats_collector())
        
        # Запускаем бота
        executor.start_polling(dp, skip_updates=True)
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True) 
