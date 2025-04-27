FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bc \
    cpulimit \
    curl \
    wget \
    zip \
    unzip \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create entrypoint script directly
RUN echo '#!/bin/bash\n\
# Copy configuration files if they do not exist\n\
if [ ! -f "/app/config/.telegram_credentials" ]; then\n\
  echo "Creating default telegram credentials file"\n\
  if [ -f "/app/.telegram_credentials.example" ]; then\n\
    cp /app/.telegram_credentials.example /app/config/.telegram_credentials\n\
  else\n\
    touch /app/config/.telegram_credentials\n\
  fi\n\
  \n\
  if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then\n\
    echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" > /app/config/.telegram_credentials\n\
    echo "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID" >> /app/config/.telegram_credentials\n\
  fi\n\
fi\n\
\n\
# Print debug info\n\
echo "Container started with:"\n\
echo "Files in /app:"\n\
ls -la /app\n\
echo "Environment variables:"\n\
env | grep TELEGRAM\n\
\n\
# Run the main application\n\
exec python "$@"' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/config /app/logs

# Copy application code
COPY *.py .
COPY *.sh .
COPY .pylintrc .
COPY README.md .
COPY .telegram_credentials.example .

# Make shell scripts executable
RUN chmod +x *.sh

# Move example configuration to config directory
RUN cp .telegram_credentials.example /app/config/.telegram_credentials.example
RUN cp critical_processes_config.sh /app/config/critical_processes_config.sh.example

# Make sure all files are readable
RUN chmod -R 755 /app

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["server_control_bot.py"] 