#!/usr/bin/env python3
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

# Загрузка конфигурации
def load_config():
    config = {
        'BOT_TOKEN': None,
        'AUTHORIZED_ADMINS': [],
        'CPU_LIMITS': {},
        'MEMORY_LIMITS': {},
        'NOTIFICATION_LEVELS': {}
    }
    
    # Загружаем учетные данные Telegram
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            for line in f:
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    config['BOT_TOKEN'] = line.split('=')[1].strip().strip('"\'')
    except Exception as e:
        logging.error(f"Ошибка загрузки учетных данных: {e}")
        sys.exit(1)
    
    # Загружаем основную конфигурацию
    try:
        with open(CONFIG_FILE, 'r') as f:
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
    except Exception as e:
        logging.error(f"Ошибка загрузки конфигурации: {e}")
        sys.exit(1)
    
    return config

config = load_config()
bot = Bot(token=config['BOT_TOKEN'])
dp = Dispatcher(bot)

# Расширенные клавиатуры
def get_main_keyboard():
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
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔔 Уведомления", callback_data="notification_settings"),
        InlineKeyboardButton("⚡ Лимиты CPU", callback_data="cpu_limits"),
        InlineKeyboardButton("💾 Лимиты памяти", callback_data="memory_limits"),
        InlineKeyboardButton("🕒 Расписание", callback_data="schedule_settings"),
        InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    )
    return keyboard

# Функции для работы со статистикой
async def save_stats_history(stats):
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        
        # Добавляем новую статистику
        history.append({
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        })
        
        # Оставляем только последние 1000 записей
        if len(history) > 1000:
            history = history[-1000:]
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except Exception as e:
        logging.error(f"Ошибка сохранения статистики: {e}")

async def get_stats_history(hours=24):
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                
            # Фильтруем по времени
            current_time = datetime.now()
            filtered_history = [
                h for h in history 
                if (current_time - datetime.fromisoformat(h['timestamp'])).total_seconds() <= hours * 3600
            ]
            return filtered_history
    except Exception as e:
        logging.error(f"Ошибка чтения статистики: {e}")
    return []

# Проверка авторизации
def is_authorized(user_id):
    return user_id in config['AUTHORIZED_ADMINS']

# Декоратор для измерения времени выполнения
def measure_time(func):
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

# Обработчики команд
@dp.message_handler(commands=['start', 'help'])
@measure_time
async def send_welcome(message: types.Message):
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

# Обработчики callback
@dp.callback_query_handler(lambda c: True)
@measure_time
async def process_callback(callback_query: types.CallbackQuery):
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
            result = subprocess.check_output(["/root/check_server_status.sh", "--silent"], 
                                          stderr=subprocess.STDOUT, 
                                          universal_newlines=True)
            await callback_query.message.edit_text(
                f"📊 Статус сервера:\n\n{result}",
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
            subprocess.Popen(["sync && echo 3 > /proc/sys/vm/drop_caches"], shell=True)
            await callback_query.message.edit_text(
                "🧹 Очистка кэша выполнена",
                reply_markup=get_main_keyboard()
            )
        
        elif action == "show_all_processes":
            result = subprocess.check_output(["ps aux --sort=-%cpu | head -11"], 
                                          shell=True, 
                                          universal_newlines=True)
            await callback_query.message.edit_text(
                f"📊 Топ процессов по CPU:\n\n<pre>{result}</pre>",
                parse_mode="HTML",
                reply_markup=get_processes_keyboard()
            )
        
        elif action == "heavy_processes":
            result = subprocess.check_output(["/root/monitor_heavy_processes.sh", "--analyze"], 
                                          stderr=subprocess.STDOUT, 
                                          universal_newlines=True)
            await callback_query.message.edit_text(
                f"⚠️ Тяжелые процессы:\n\n{result}",
                reply_markup=get_processes_keyboard()
            )
        
        elif action == "main_menu":
            await callback_query.message.edit_text(
                "🤖 Главное меню\n\nВыберите действие:",
                reply_markup=get_main_keyboard()
            )
        
        elif action.startswith("logs_"):
            log_file = {
                "logs_system": "/var/log/syslog",
                "logs_cursor": "/var/log/cursor_monitor.log",
                "logs_optimize": "/var/log/optimize_server.log",
                "logs_bot": "/var/log/server_control_bot.log"
            }.get(action)
            
            if log_file:
                result = subprocess.check_output(f"tail -n 20 {log_file}", 
                                              shell=True, 
                                              universal_newlines=True)
                await callback_query.message.edit_text(
                    f"📝 Последние логи ({log_file}):\n\n<pre>{result}</pre>",
                    parse_mode="HTML",
                    reply_markup=get_processes_keyboard()
                )
    
    except Exception as e:
        logging.error(f"Ошибка при обработке callback {action}: {e}")
        await callback_query.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    
    await callback_query.answer()

# Периодический сбор статистики
async def stats_collector():
    while True:
        try:
            # Собираем текущую статистику
            cpu_usage = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'", shell=True).decode().strip()
            memory_usage = subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True).decode().strip()
            
            stats = {
                'cpu': float(cpu_usage),
                'memory': float(memory_usage)
            }
            
            # Сохраняем статистику
            await save_stats_history(stats)
            
        except Exception as e:
            logging.error(f"Ошибка сбора статистики: {e}")
        
        await asyncio.sleep(300)  # Собираем статистику каждые 5 минут

# Запуск бота
if __name__ == '__main__':
    logging.info("Бот запущен")
    
    # Запускаем сборщик статистики
    loop = asyncio.get_event_loop()
    loop.create_task(stats_collector())
    
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True) 