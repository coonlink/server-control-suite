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

The Server Control Suite supports the following environment variables for configuration:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Your Telegram bot token obtained from BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat ID (authorized administrator) |
| `TZ` | No | Timezone (default: UTC) |
| `PYTHONUNBUFFERED` | No | Set to 1 to ensure Python output is unbuffered |

#### Setting Environment Variables in Dokploy

If you're using Dokploy, you can set these variables in the Environment tab:

```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

#### Setting Environment Variables in docker-compose.yml

You can set these variables directly in your docker-compose.yml file:

```yaml
services:
  server-control-suite:
    # ... other settings ...
    environment:
      - TELEGRAM_BOT_TOKEN=your_token_here
      - TELEGRAM_CHAT_ID=your_chat_id_here
      - TZ=UTC
```

#### Using .env File

You can also create a `.env` file in the same directory as your docker-compose.yml:

```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

And then docker-compose will automatically use these variables.

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

## Building the Docker Image

To build the Docker image:

```bash
docker build -t server-control-suite .
```

## Running the Container

You can run the container with:

```bash
docker run -d --name server-control \
  -e TELEGRAM_BOT_TOKEN="your_token_here" \
  -e TELEGRAM_CHAT_ID="your_chat_id_here" \
  server-control-suite
```

## Using Docker Compose

A sample `docker-compose.yml` file is included in the repository:

```yaml
version: '3'

services:
  server-control:
    build: .
    container_name: server-control-bot
    restart: always
    environment:
      - TELEGRAM_BOT_TOKEN=your_token_here
      - TELEGRAM_CHAT_ID=your_chat_id_here
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
      - ./localization:/app/localization
```

Run with Docker Compose:

```bash
docker-compose up -d
```

## Localization in Docker

The Docker container automatically sets up localization files if they don't exist:

1. The entrypoint script creates the necessary directories: `/app/config`, `/app/localization`, `/app/logs`
2. If localization files aren't found, default English and Russian JSON files are created
3. If the localization config is missing, a default config is created

If you want to persist your localization settings between container restarts, mount the directories as volumes:

```bash
docker run -d --name server-control \
  -e TELEGRAM_BOT_TOKEN="your_token_here" \
  -e TELEGRAM_CHAT_ID="your_chat_id_here" \
  -v ./config:/app/config \
  -v ./localization:/app/localization \
  -v ./logs:/app/logs \
  server-control-suite
```

## Troubleshooting

### Missing Localization Files

If you see warnings like:

```
WARNING:root:Localization config file not found at /app/config/localization.conf
ERROR:root:Language file for 'en' not found at /app/localization/en.json
```

This means the localization files are not properly mounted or created. Solutions:

1. Make sure you're mounting the directories correctly in your Docker run command or docker-compose.yml
2. Try rebuilding the Docker image to include the latest entrypoint script that creates these files
3. Manually create the directories and files on your host and mount them using volumes

### Manual Copy of Localization Files

If you need to manually copy the files to the container:

```bash
# Copy English language file to the container
docker cp localization/en.json server-control:/app/localization/

# Copy Russian language file to the container
docker cp localization/ru.json server-control:/app/localization/

# Copy localization config
docker cp config/localization.conf server-control:/app/config/
```

Then restart the container:

```bash
docker restart server-control
``` 