#!/bin/bash
# Docker entrypoint script

# Copy configuration files if they do not exist
if [ ! -f "/app/config/.telegram_credentials" ]; then
  echo "Creating default telegram credentials file"
  if [ -f "/app/.telegram_credentials.example" ]; then
    cp /app/.telegram_credentials.example /app/config/.telegram_credentials
  else
    touch /app/config/.telegram_credentials
  fi
  
  if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" > /app/config/.telegram_credentials
    echo "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID" >> /app/config/.telegram_credentials
  fi
fi

# Print debug info
echo "Container started with:"
echo "Files in /app:"
ls -la /app
echo "Environment variables:"
env | grep TELEGRAM || echo "No Telegram environment variables set"

# Send startup message to Telegram if credentials are available
if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
  echo "Sending startup notification to Telegram..."
  
  # Current time for the message
  CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
  
  # Create the message
  MESSAGE="🤖 *Server Control Bot запущен*
  
📅 Время запуска: $CURRENT_TIME
🖥️ Хост: $(hostname)

Для управления сервером отправьте команду /start"

  # Send message via Telegram API
  curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d "chat_id=$TELEGRAM_CHAT_ID" \
    -d "text=$MESSAGE" \
    -d "parse_mode=Markdown" > /dev/null
  
  echo "Startup notification sent"
fi

# Run the main application
exec python "$@"