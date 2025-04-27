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

# Create necessary directories
RUN mkdir -p /app/config /app/logs

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script first and make it executable
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh
RUN ls -la /app

# Copy application code
COPY *.py .
COPY *.sh .
COPY .pylintrc .
COPY README.md .
COPY .telegram_credentials.example .

# Make sure scripts are executable
RUN chmod +x *.sh

# Move example configuration to config directory
RUN cp .telegram_credentials.example /app/config/.telegram_credentials.example
RUN cp critical_processes_config.sh /app/config/critical_processes_config.sh.example

# Make sure all files are readable and executable
RUN chmod -R 755 /app

# Set entrypoint 
ENTRYPOINT ["bash", "/app/entrypoint.sh"]
CMD ["server_control_bot.py"]