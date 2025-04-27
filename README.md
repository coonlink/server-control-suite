# Server Control Suite

Набор инструментов для мониторинга, управления и оптимизации сервера через Telegram-бота.

## Состав

- **server_control_bot.py** - Основной Telegram-бот для управления сервером
- **optimize_server.sh** - Скрипт оптимизации сервера
- **process_resource_manager.sh** - Управление процессами и ресурсами
- **check_server_status.sh** - Мониторинг состояния сервера
- **critical_processes_config.sh** - Конфигурация критических процессов
- **check_libraries.sh** - Проверка установленных библиотек и компонентов

## Установка

```bash
# Клонируйте репозиторий
git clone [URL_репозитория] /root/server-control-suite

# Перейдите в директорию
cd /root/server-control-suite

# Установите зависимости
apt update
apt install -y python3 python3-pip bc cpulimit curl wget

# Установите python зависимости
pip3 install aiogram requests

# Настройте конфигурацию
nano critical_processes_config.sh
# Настройте переменные под ваш сервер

# Сделайте скрипты исполняемыми
chmod +x *.sh
```

## ⚠️ Важно! Безопасность ⚠️

**НИКОГДА не храните реальные токены, ключи или учетные данные в репозитории!**

1. Создайте файл с реальными учетными данными из шаблона:
   ```bash
   cp .telegram_credentials.example .telegram_credentials
   nano .telegram_credentials  # Добавьте свои данные
   ```

2. Файл `.telegram_credentials` добавлен в `.gitignore` и не должен быть включен в репозиторий.

3. Периодически проверяйте, что конфиденциальные данные не были случайно добавлены в историю коммитов.

## Использование

### Запуск Telegram-бота

```bash
python3 server_control_bot.py
```

### Проверка состояния сервера

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
# Создайте systemd-сервис
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

# Включите и запустите сервис
systemctl enable server-control-bot
systemctl start server-control-bot
```

## Обновление

Для обновления скриптов:

```bash
cd /root/server-control-suite
git pull
systemctl restart server-control-bot
```

## Линтер (Pylint)

Проект использует Pylint для статического анализа кода. Настройки линтера хранятся в файле `.pylintrc`.

Для запуска линтера локально:

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите Pylint
pylint --rcfile=.pylintrc server_control_bot.py
```

В CI/CD пайплайне файл `.pylintrc` используется автоматически для согласованного форматирования кода.

### Альтернативные способы проверки кода

Помимо pylint, вы можете использовать более простые инструменты проверки:

```bash
# Установите flake8
pip install flake8

# Проверка только критических ошибок синтаксиса
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Или используйте tox для комплексной проверки
pip install tox
tox
```

## Проблемы с CI/CD

Если возникают проблемы с CI/CD пайплайном:

1. Убедитесь что все зависимости указаны в `requirements.txt`
2. Проверьте что версия Python соответствует требуемой (Python 3.9)
3. Запустите скрипт настройки CI локально: `./setup_ci.sh`

Для отладки проблем с пайплайном используйте более простой воркфлоу `python-basic-check.yml`.

### Решение проблемы с exit code 16 (pylint)

Exit code 16 от pylint означает, что линтер нашел ошибки/предупреждения, превышающие допустимый порог.

Для решения этой проблемы:

1. **Запустите pylint локально** для просмотра конкретных ошибок:
   ```bash
   pylint --rcfile=.pylintrc server_control_bot.py
   ```

2. **Исправьте указанные проблемы** или настройте порог ошибок в `.pylintrc`:
   ```ini
   # Допустимый порог качества кода (0-10)
   [REPORTS]
   evaluation=7.0
   ```

3. **Используйте параметр `--fail-under`** для контроля порога ошибок:
   ```bash
   pylint --fail-under=7.0 server_control_bot.py
   ```

4. **Игнорируйте код завершения pylint** в CI/CD пайплайне:
   ```bash
   # Запуск pylint без прерывания пайплайна при ошибках
   pylint $(git ls-files '*.py') || true
   ```

В нашей CI конфигурации мы используем комбинацию этих подходов для обеспечения продолжения работы пайплайна даже при наличии некритичных предупреждений. 