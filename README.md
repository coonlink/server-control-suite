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

## Linting and Code Quality

This project uses Pylint for code quality checks. The CI pipeline requires a minimum Pylint score of 8.0/10.

### Running Pylint Locally

To check your code before committing:

```bash
# Install pylint
pip install pylint

# Run pylint on all Python files
pylint $(git ls-files '*.py')

# Or with specific configuration
pylint --rcfile=.pylintrc $(git ls-files '*.py')
```

### Common Pylint Issues and Fixes

- **Missing docstrings**: Add descriptive docstrings to modules, classes, and functions
- **Line too long**: Keep lines under 120 characters
- **Unused imports**: Remove imports that aren't used
- **Too many arguments**: Consider refactoring functions with many parameters

You can disable specific checks in the `.pylintrc` file or inline in your code:

```python
# pylint: disable=unused-import
import os
```

## Проблемы с CI/CD

Если возникают проблемы с CI/CD пайплайном:

1. Убедитесь что все зависимости указаны в `requirements.txt`
2. Проверьте что версия Python соответствует требуемой (Python 3.9)
3. Запустите скрипт настройки CI локально: `./setup_ci.sh`

Для отладки проблем с пайплайном используйте более простой воркфлоу `python-basic-check.yml`.

### Решение проблемы с exit code 16 (pylint)

Exit code 16 от pylint означает, что линтер нашел ошибки/предупреждения, превышающие допустимый порог.

Для решения этой проблемы есть несколько подходов:

1. **Запустите pylint локально** для просмотра конкретных ошибок:
   ```bash
   pylint --rcfile=.pylintrc server_control_bot.py
   ```

2. **Исправьте указанные проблемы** в коде или отключите конкретные проверки в `.pylintrc`:
   ```ini
   [MESSAGES CONTROL]
   disable=trailing-whitespace,
           trailing-newlines,
           line-too-long,
           broad-exception-caught
   ```

3. **Используйте параметр `--fail-under`** непосредственно в команде для контроля порога ошибок:
   ```bash
   # Позволяет проходить проверку при рейтинге 8.0/10 и выше
   pylint --fail-under=8.0 $(git ls-files '*.py')
   ```

4. **Игнорируйте код завершения pylint** в CI/CD пайплайне:
   ```bash
   # Запуск pylint без прерывания пайплайна при ошибках
   pylint $(git ls-files '*.py') || true
   ```

5. **Проверяйте на разных версиях Python** - иногда разные версии имеют разные строгости проверок:
   ```yaml
   strategy:
     matrix:
       python-version: ["3.8", "3.9", "3.10"]
   ```

6. **Создавайте отчеты pylint** для удобства отладки:
   ```bash
   # Создание отчета и вывод в файл
   pylint $(git ls-files '*.py') > pylint-report.txt
   
   # Просмотр отчета
   cat pylint-report.txt
   ```

В нашей CI конфигурации мы используем комбинацию этих подходов, проверяя код на нескольких версиях Python, устанавливая порог качества в 8.0/10 и создавая отчеты, которые сохраняются как артефакты сборки для дальнейшего анализа. 
