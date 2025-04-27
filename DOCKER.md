# Docker Deployment Guide

This guide explains how to deploy the Server Control Suite using Docker and docker-compose.

## Prerequisites

- Docker installed on your server
- Docker Compose installed on your server
- Git (for cloning the repository)

## Quick Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/coonlink/server-control-suite.git
   cd server-control-suite
   ```

2. Create a configuration file:
   ```bash
   mkdir -p config
   cp .telegram_credentials.example config/.telegram_credentials
   # Edit the credentials file with your Telegram bot token and chat ID
   nano config/.telegram_credentials
   ```

3. Deploy with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Check the logs:
   ```bash
   docker-compose logs -f
   ```

## Configuration

### Volumes

The docker-compose.yml defines two volumes:
- `./config:/app/config` - Configuration files
- `./logs:/app/logs` - Log files

### Environment Variables

You can customize the deployment by setting environment variables in the docker-compose.yml file:
- `TZ` - Timezone (default: UTC)
- `PYTHONUNBUFFERED` - Ensures Python output is sent straight to the container logs

## Customization

To customize the deployment, edit the `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  server-control-suite:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: server-control-suite
    restart: unless-stopped
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - TZ=Europe/London  # Change to your timezone
      - PYTHONUNBUFFERED=1
    command: python3 server_control_bot.py
```

## Updating

To update to a new version:

1. Pull the latest changes:
   ```bash
   git pull
   ```

2. Rebuild and restart the containers:
   ```bash
   docker-compose up -d --build
   ```

## Troubleshooting

If you encounter issues:

1. Check the container logs:
   ```bash
   docker-compose logs -f
   ```

2. Ensure your configuration files are correct:
   ```bash
   docker exec -it server-control-suite cat /app/config/.telegram_credentials
   ```

3. Try rebuilding the container:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ``` 