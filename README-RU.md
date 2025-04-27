<h1 align="center">Server Control Suite</h1>

<div align="center">
  <img src="https://github.com/user-attachments/assets/b1f6a9f3-2690-41ef-8c7a-c3119f29bab3" alt="Preview" width="600px">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <br>
  <a href="https://t.me/coonlink">
    <img src="https://img.shields.io/badge/developer-@coonlink-blue.svg" alt="Developer">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="./README-RU.md">Русский</a>
</p>

## О проекте

Server Control Suite - это мощный набор инструментов для мониторинга, управления и оптимизации сервера через интерфейс Telegram бота. Он позволяет системным администраторам удаленно контролировать серверные ресурсы, отслеживать производительность и автоматически оптимизировать систему при необходимости.

## Возможности

- **Мониторинг в реальном времени**: Получение текущего статуса сервера, включая использование CPU, памяти и дискового пространства
- **Управление процессами**: Просмотр, ограничение или завершение ресурсоемких процессов
- **Автоматическая оптимизация**: Планирование или ручной запуск процедур оптимизации сервера
- **Ночной режим**: Включение энергосберегающего ночного режима с более строгими ограничениями ресурсов
- **Настраиваемые оповещения**: Получение уведомлений, когда нагрузка системы превышает заданные пороги
- **Многоязычная поддержка**: Доступно на английском и русском языках

## Компоненты

- **server_control_bot.py** - Основной Telegram бот для управления сервером
- **optimize_server.sh** - Скрипт оптимизации сервера
- **process_resource_manager.sh** - Управление процессами и ресурсами
- **check_server_status.sh** - Мониторинг статуса сервера
- **critical_processes_config.sh** - Конфигурация критичных процессов
- **check_libraries.sh** - Проверка зависимостей библиотек и компонентов

## Установка

```bash
# Клонирование репозитория
git clone [repository_URL] /root/server-control-suite

# Переход в директорию
cd /root/server-control-suite

# Установка зависимостей
apt update
apt install -y python3 python3-pip bc cpulimit curl wget

# Установка Python зависимостей
pip3 install aiogram requests

# ВАЖНО: Для server_control_bot.py используйте специфическую версию python-telegram-bot
pip3 install python-telegram-bot==13.7 urllib3==1.26.6

# Настройка параметров
nano critical_processes_config.sh
# Настройте переменные для вашего сервера

# Сделайте скрипты исполняемыми
chmod +x *.sh
```

## Настройка безопасности

**НИКОГДА не храните настоящие токены, ключи или учетные данные в репозитории!**

1. Создайте файл с реальными учетными данными из шаблона:
   ```bash
   cp .telegram_credentials.example .telegram_credentials
   nano .telegram_credentials  # Добавьте ваши данные
   ```

2. Файл `.telegram_credentials` добавлен в `.gitignore` и не должен включаться в репозиторий.

3. Регулярно проверяйте, что конфиденциальные данные не были случайно добавлены в историю коммитов.

## Использование

### Запуск Telegram бота

```bash
python3 server_control_bot.py
```

### Проверка статуса сервера

```bash
./check_server_status.sh
```

### Оптимизация сервера

```bash
./optimize_server.sh
```

### Проверка установленных библиотек

```bash
./check_libraries.sh
```

## Настройка автозапуска

Для автоматического запуска бота после перезагрузки сервера:

```bash
# Создание systemd сервиса
cat > /etc/systemd/system/server-control-bot.service << EOL
[Unit]
Description=Server Control Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/server-control-suite
ExecStart=/usr/bin/python3 /root/server-control-suite/server_control_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# Включение и запуск сервиса
systemctl enable server-control-bot
systemctl start server-control-bot
```

## Распространенные проблемы и их решение

### Проблемы с модулями Python

Если вы столкнулись с ошибками, связанными с отсутствием модулей Python (например, `No module named 'imghdr'`, `No module named 'urllib3.contrib.appengine'`), вы должны:

1. Убедиться, что у вас установлена полная версия Python:
   ```bash
   # Для Debian/Ubuntu
   apt install python3-full
   
   # Для CentOS/RHEL
   yum install python3 python3-libs
   ```

2. Установить все необходимые зависимости:
   ```bash
   pip3 install python-telegram-bot==13.7 urllib3==1.26.6
   ```

3. Проверить, что все зависимости установлены:
   ```bash
   ./check_libraries.sh
   ```

Последняя версия бота включает заглушки для часто отсутствующих модулей:
- `imghdr` - используется для определения типа изображения
- `urllib3.contrib.appengine` - используется для проверки среды AppEngine

### Проблемы с обработкой запросов обратного вызова

Если нажатие кнопок в Telegram боте не вызывает никаких действий:

1. **Проверьте логи**:
   ```bash
   tail -f server_control_bot.log
   ```
   Логи покажут, какие ошибки возникают при обработке запросов обратного вызова.

2. **Проверьте доступность скриптов**:
   Убедитесь, что все необходимые скрипты существуют и имеют права на выполнение:
   ```bash
   ls -la *.sh
   chmod +x *.sh
   ```
   
   Минимальный набор требуемых скриптов:
   - `check_server_status.sh`
   - `optimize_server.sh`
   - `monitor_heavy_processes.sh`

3. **Правильные версии зависимостей**:
   ```bash
   pip3 install python-telegram-bot==13.7 urllib3==1.26.6
   ```
   
   Более новые версии urllib3 могут вызывать проблемы. Версия 1.26.6 протестирована и работает с python-telegram-bot 13.7.

4. **Проверьте соединение с API Telegram**:
   ```bash
   curl -s https://api.telegram.org/bot<YOUR_TOKEN>/getMe | grep "ok"
   ```
   
## Настройка языка

Бот поддерживает английский и русский языки. Для настройки предпочитаемого языка:

1. Отредактируйте файл конфигурации языка:
   ```bash
   nano config/localization.conf
   ```

2. Установите язык по умолчанию и другие языковые параметры:
   ```
   DEFAULT_LANGUAGE="ru"  # Измените на "en" для английского
   MULTI_LANGUAGE_SUPPORT=true
   USER_LANGUAGE_SELECTION=true
   ```

3. В Telegram боте используйте команду `/language` для изменения языка интерфейса.

## 🛡 License

MIT © [Coonlink](https://coonlink.fun)

## Создано с ❤️ от Coonlink 