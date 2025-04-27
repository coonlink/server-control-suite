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

# Run the main application
exec python "$@"