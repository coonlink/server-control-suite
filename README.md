<h1 align="center">Server Control Suite</h1>

<div align="center">
  <img src="https://github.com/user-attachments/assets/b1f6a9f3-2690-41ef-8c7a-c3119f29bab3" alt="Preview" width="600px">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <br>
  <a href="https://t.me/coonlink">
    <img src="https://img.shields.io/badge/developer-@coonlink-blue.svg" alt="Developer">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="./README-RU.md">Русский</a>
</p>

## About

Server Control Suite is a powerful set of tools for server monitoring, management, and optimization through a Telegram bot interface. It allows system administrators to remotely control server resources, monitor performance, and automatically optimize the system when needed.

## Features

- **Real-time Monitoring**: Get current server status including CPU, memory, and disk usage
- **Process Management**: View, limit, or terminate resource-intensive processes
- **Automatic Optimization**: Schedule or manually trigger server optimization routines
- **Night Mode**: Enable energy-saving night mode with stricter resource limits
- **Customizable Alerts**: Receive notifications when system load exceeds defined thresholds
- **Multi-language Support**: Available in English and Russian

## Components

- **server_control_bot.py** - Main Telegram bot for server management
- **optimize_server.sh** - Server optimization script
- **process_resource_manager.sh** - Process and resource management
- **check_server_status.sh** - Server status monitoring
- **critical_processes_config.sh** - Critical process configuration
- **check_libraries.sh** - Library and component dependency checker

## Installation

```bash
# Clone the repository
git clone [repository_URL] /root/server-control-suite

# Navigate to the directory
cd /root/server-control-suite

# Install dependencies
apt update
apt install -y python3 python3-pip bc cpulimit curl wget

# Install Python dependencies
pip3 install aiogram requests

# IMPORTANT: For server_control_bot.py use the specific version of python-telegram-bot
pip3 install python-telegram-bot==13.7 urllib3==1.26.6

# Configure settings
nano critical_processes_config.sh
# Configure variables for your server

# Make scripts executable
chmod +x *.sh
```

## Security Configuration

**NEVER store actual tokens, keys, or credentials in the repository!**

1. Create a file with real credentials from the template:
   ```bash
   cp .telegram_credentials.example .telegram_credentials
   nano .telegram_credentials  # Add your data
   ```

2. The `.telegram_credentials` file is added to `.gitignore` and should not be included in the repository.

3. Regularly check that confidential data hasn't been accidentally added to commit history.

## Usage

### Starting the Telegram Bot

```bash
python3 server_control_bot.py
```

### Checking Server Status

```bash
./check_server_status.sh
```

### Optimizing the Server

```bash
./optimize_server.sh
```

### Checking Installed Libraries

```bash
./check_libraries.sh
```

## Autostart Configuration

For automatic bot startup after server reboot:

```bash
# Create systemd service
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

# Enable and start the service
systemctl enable server-control-bot
systemctl start server-control-bot
```

## Common Issues and Troubleshooting

### Python Module Issues

If you encounter errors related to missing Python modules (e.g., `No module named 'imghdr'`, `No module named 'urllib3.contrib.appengine'`), you should:

1. Ensure you're using a complete Python installation:
   ```bash
   # For Debian/Ubuntu
   apt install python3-full
   
   # For CentOS/RHEL
   yum install python3 python3-libs
   ```

2. Install all necessary dependencies:
   ```bash
   pip3 install python-telegram-bot==13.7 urllib3==1.26.6
   ```

3. Check that all dependencies are installed:
   ```bash
   ./check_libraries.sh
   ```

The latest version of the bot includes stubs for commonly missing modules:
- `imghdr` - used for image type detection
- `urllib3.contrib.appengine` - used for AppEngine environment checks

### Callback Request Issues

If pressing buttons in the Telegram bot doesn't trigger any action:

1. **Check logs**:
   ```bash
   tail -f server_control_bot.log
   ```
   Logs will show what errors occur during callback request processing.

2. **Verify script availability**:
   Ensure all necessary scripts exist and have execution permissions:
   ```bash
   ls -la *.sh
   chmod +x *.sh
   ```
   
   Minimum set of scripts required:
   - `check_server_status.sh`
   - `optimize_server.sh`
   - `monitor_heavy_processes.sh`

3. **Correct dependency versions**:
   ```bash
   pip3 install python-telegram-bot==13.7 urllib3==1.26.6
   ```
   
   Newer versions of urllib3 may cause issues. Version 1.26.6 is tested and works with python-telegram-bot 13.7.

4. **Verify connection to Telegram API**:
   ```bash
   curl -s https://api.telegram.org/bot<YOUR_TOKEN>/getMe | grep "ok"
   ```
   
## Language Configuration

The bot supports English and Russian languages. To configure your preferred language:

1. Edit the language configuration file:
   ```bash
   nano config/localization.conf
   ```

2. Set the default language and other language options:
   ```
   DEFAULT_LANGUAGE="en"  # Change to "ru" for Russian
   MULTI_LANGUAGE_SUPPORT=true
   USER_LANGUAGE_SELECTION=true
   ```

3. In the Telegram bot, use the command `/language` to change the interface language.

## 🛡 License

MIT © [Coonlink](https://coonlink.fun)

## Built with ❤️ by Coonlink 