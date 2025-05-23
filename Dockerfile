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
RUN mkdir -p /app/config /app/logs /app/localization

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy our new entrypoint script and make it executable
COPY dockerfile-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application code
COPY *.py .
COPY *.sh .
COPY .pylintrc .
COPY README.md .
COPY .telegram_credentials.example .

# Copy localization files
COPY config/localization.conf /app/config/localization.conf
COPY localization/*.json /app/localization/

# Make sure scripts are executable
RUN chmod +x *.sh

# Move example configuration to config directory
RUN cp .telegram_credentials.example /app/config/.telegram_credentials.example
RUN cp critical_processes_config.sh /app/config/critical_processes_config.sh.example

# Make sure all files are readable and executable
RUN chmod -R 755 /app

# Set entrypoint 
ENTRYPOINT ["bash", "/app/entrypoint.sh"]