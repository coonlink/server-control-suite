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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .
COPY *.sh .
COPY .pylintrc .
COPY README.md .
COPY .telegram_credentials.example .

# Create necessary directories
RUN mkdir -p /app/config /app/logs

# Make shell scripts executable
RUN chmod +x *.sh

# Move example configuration to config directory
RUN cp .telegram_credentials.example /app/config/.telegram_credentials.example

# Set entrypoint
ENTRYPOINT ["python3"]
CMD ["server_control_bot.py"] 