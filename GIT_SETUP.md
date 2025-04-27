# Настройка Git репозитория

## ⚠️ Меры безопасности перед началом работы ⚠️

**НИКОГДА не добавляйте файлы с реальными токенами, паролями или другими учетными данными в репозиторий!**

1. Проверьте, нет ли конфиденциальных данных в файлах:
   ```bash
   grep -r "token\|password\|secret\|key" --include="*.*" .
   ```

2. Удалите любые найденные конфиденциальные данные и замените их шаблонами.

3. Убедитесь, что файл `.gitignore` включает все необходимые правила:
   ```
   .telegram_credentials
   *.env
   *.key
   *secret*
   *token*
   *password*
   ```

## Инициализация локального репозитория

```bash
# Перейдите в директорию с проектом
cd server-control-suite

# Инициализируйте репозиторий
git init

# Добавьте все файлы в индекс
git add .

# Создайте первый коммит
git commit -m "Initial commit"
```

## Подключение к удаленному репозиторию

```bash
# Создайте репозиторий на GitHub, GitLab или другой платформе

# Подключите локальный репозиторий к удаленному
git remote add origin https://github.com/username/server-control-suite.git

# Отправьте изменения в удаленный репозиторий
git push -u origin master
```

## Клонирование репозитория на сервер

```bash
# На сервере выполните:
git clone https://github.com/username/server-control-suite.git /root/server-control-suite

# Перейдите в директорию
cd /root/server-control-suite

# Сделайте скрипты исполняемыми
chmod +x *.sh

# Создайте файл с учетными данными Telegram
cp .telegram_credentials.example .telegram_credentials
nano .telegram_credentials  # Отредактируйте файл, добавив свои данные
```

## Безопасное управление секретами

Никогда не храните реальные токены и пароли в Git-репозитории. Вместо этого:

1. Используйте переменные окружения:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token_here"
   ```

2. Или храните секреты в отдельном файле:
   ```bash
   echo 'TELEGRAM_BOT_TOKEN="your_token_here"' > /root/.telegram_credentials
   echo 'source /root/.telegram_credentials' >> ~/.bashrc
   ```

3. Для продакшн-окружения рассмотрите использование Vault, Docker secrets или других безопасных хранилищ секретов.

## Настройка автоматического обновления с GitHub

### Способ 1: Cron

```bash
# Добавьте задачу в cron для ежедневного обновления
(crontab -l 2>/dev/null; echo "0 4 * * * cd /root/server-control-suite && git pull") | crontab -
```

### Способ 2: Webhook

Если у вас есть веб-сервер, вы можете настроить webhook для автоматического обновления при пуше в репозиторий.

1. Создайте скрипт `/var/www/html/webhook.php`:

```php
<?php
$secret = "ваш_секретный_ключ";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $headers = getallheaders();
    $signature = isset($headers['X-Hub-Signature']) ? $headers['X-Hub-Signature'] : '';
    
    $payload = file_get_contents('php://input');
    $calculated_signature = 'sha1=' . hash_hmac('sha1', $payload, $secret);
    
    if (hash_equals($signature, $calculated_signature)) {
        echo shell_exec('cd /root/server-control-suite && git pull 2>&1');
        echo "Repository updated!";
    } else {
        http_response_code(403);
        echo "Forbidden";
    }
} else {
    http_response_code(405);
    echo "Method Not Allowed";
}
```

2. В настройках webhook на GitHub/GitLab укажите URL: `https://your-server.com/webhook.php` 