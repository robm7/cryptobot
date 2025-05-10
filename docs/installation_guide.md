# Cryptobot Installation Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Methods](#installation-methods)
3. [Windows Installation](#windows-installation)
4. [Linux Installation](#linux-installation)
5. [macOS Installation](#macos-installation)
6. [Docker Installation](#docker-installation)
7. [Development Installation](#development-installation)
8. [Configuration](#configuration)
9. [First-Time Setup](#first-time-setup)
10. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **CPU**: Dual-core processor, 2.0 GHz or higher
- **RAM**: 4 GB
- **Storage**: 1 GB free space
- **Operating System**:
  - Windows 10/11 (64-bit)
  - Ubuntu 20.04 LTS or newer
  - macOS 11 (Big Sur) or newer
- **Network**: Stable internet connection
- **Dependencies**:
  - For Docker installation: Docker and Docker Compose
  - For development installation: Python 3.8 or newer

### Recommended Requirements

- **CPU**: Quad-core processor, 2.5 GHz or higher
- **RAM**: 8 GB or more
- **Storage**: 5 GB free space
- **Network**: High-speed internet connection

## Installation Methods

Cryptobot can be installed using several methods:

1. **Standalone Executable**: Easiest method for most users
2. **Docker**: Best for production deployments and development
3. **Development Installation**: For developers who want to modify the code

Choose the method that best suits your needs and follow the corresponding instructions.

## Windows Installation

### Standalone Executable

1. **Download the Installer**:
   - Go to the [Releases page](https://github.com/yourusername/cryptobot/releases)
   - Download the latest Windows installer (`cryptobot-windows-[version].exe`)

2. **Run the Installer**:
   - Double-click the downloaded file
   - Follow the installation wizard instructions
   - Choose an installation directory when prompted

3. **Launch Cryptobot**:
   - After installation, launch Cryptobot from the Start menu
   - Alternatively, run `cryptobot.exe` from the installation directory

### Using the ZIP Archive

1. **Download the ZIP Archive**:
   - Go to the [Releases page](https://github.com/yourusername/cryptobot/releases)
   - Download the latest Windows ZIP archive (`cryptobot-windows-[version].zip`)

2. **Extract the Archive**:
   - Right-click the downloaded file and select "Extract All..."
   - Choose a destination folder
   - Click "Extract"

3. **Launch Cryptobot**:
   - Navigate to the extracted folder
   - Run `cryptobot.exe`

## Linux Installation

### Standalone Executable

1. **Download the Installer**:
   ```bash
   wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot-linux-1.0.0
   ```

2. **Make the File Executable**:
   ```bash
   chmod +x cryptobot-linux-1.0.0
   ```

3. **Run the Installer**:
   ```bash
   ./cryptobot-linux-1.0.0
   ```

4. **Launch Cryptobot**:
   ```bash
   cryptobot
   ```

### Using the Tarball Archive

1. **Download the Tarball Archive**:
   ```bash
   wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot-linux-1.0.0.tar.gz
   ```

2. **Extract the Archive**:
   ```bash
   tar -xzf cryptobot-linux-1.0.0.tar.gz
   ```

3. **Launch Cryptobot**:
   ```bash
   cd cryptobot
   ./cryptobot
   ```

## macOS Installation

### Standalone Executable

1. **Download the Installer**:
   - Go to the [Releases page](https://github.com/yourusername/cryptobot/releases)
   - Download the latest macOS installer (`cryptobot-macos-[version].dmg`)

2. **Open the Disk Image**:
   - Double-click the downloaded file
   - Drag the Cryptobot icon to the Applications folder

3. **Launch Cryptobot**:
   - Open the Applications folder
   - Double-click the Cryptobot icon
   - If prompted about security, go to System Preferences > Security & Privacy and allow the app to run

### Using the Tarball Archive

1. **Download the Tarball Archive**:
   ```bash
   curl -L -o cryptobot-macos-1.0.0.tar.gz https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot-macos-1.0.0.tar.gz
   ```

2. **Extract the Archive**:
   ```bash
   tar -xzf cryptobot-macos-1.0.0.tar.gz
   ```

3. **Launch Cryptobot**:
   ```bash
   cd cryptobot
   ./cryptobot
   ```

## Docker Installation

### Prerequisites

- Docker installed on your system
- Docker Compose installed on your system

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/cryptobot.git
   cd cryptobot
   ```

2. **Build the Docker Images**:
   ```bash
   docker-compose build
   ```

3. **Start the Services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the Dashboard**:
   - Open your web browser
   - Navigate to `http://localhost:8080`

### Docker Compose Configuration

The default `docker-compose.yml` file includes:

- Auth Service
- Strategy Service
- Data Service
- Trade Service
- Backtest Service
- Dashboard
- PostgreSQL database
- Redis cache

You can modify the `docker-compose.yml` file to suit your needs.

## Development Installation

### Prerequisites

- Python 3.8 or newer
- Git
- pip (Python package manager)

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/cryptobot.git
   cd cryptobot
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the Virtual Environment**:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/macOS:
     ```bash
     source venv/bin/activate
     ```

4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

5. **Initialize the Database**:
   ```bash
   python -m scripts.init_db
   ```

6. **Run Cryptobot**:
   ```bash
   python main.py --all
   ```

7. **Access the Dashboard**:
   - Open your web browser
   - Navigate to `http://localhost:8080`

## Configuration

Cryptobot can be configured using a configuration file or environment variables.

### Configuration File

Create a configuration file at `config/config.json`:

```json
{
  "services": {
    "auth": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8000
    },
    "strategy": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8001
    },
    "data": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8002
    },
    "trade": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8003
    },
    "backtest": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8004
    }
  },
  "database": {
    "url": "sqlite:///cryptobot.db"
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0
  },
  "logging": {
    "level": "INFO",
    "file": "cryptobot.log"
  }
}
```

Run Cryptobot with the configuration file:

```bash
cryptobot --config config/config.json --all
```

### Environment Variables

Configure Cryptobot using environment variables:

```bash
# Windows
set CRYPTOBOT_ENV=production
set CRYPTOBOT_DB_URL=sqlite:///cryptobot.db
set CRYPTOBOT_REDIS_HOST=localhost
set CRYPTOBOT_REDIS_PORT=6379
set CRYPTOBOT_LOG_LEVEL=INFO

# Linux/macOS
export CRYPTOBOT_ENV=production
export CRYPTOBOT_DB_URL=sqlite:///cryptobot.db
export CRYPTOBOT_REDIS_HOST=localhost
export CRYPTOBOT_REDIS_PORT=6379
export CRYPTOBOT_LOG_LEVEL=INFO
```

Run Cryptobot:

```bash
cryptobot --all
```

## First-Time Setup

When you first run Cryptobot, you'll need to complete the setup process:

1. **Create an Administrator Account**:
   - Open your web browser
   - Navigate to `http://localhost:8080`
   - Follow the setup wizard
   - Create an administrator account with a username and password

2. **Configure Exchanges**:
   - Add your exchange API keys
   - Set trading limits and preferences

3. **Set Up Notifications**:
   - Configure email or Telegram notifications
   - Set up alerts for important events

4. **Choose Default Strategy**:
   - Select a starter strategy or create your own

## Troubleshooting

### Common Issues

#### Installation Issues

- **Error**: "Permission denied"
  - **Solution**: Run the installer with administrator privileges

- **Error**: "File not found"
  - **Solution**: Ensure you downloaded the correct file for your operating system

#### Configuration Issues

- **Error**: "Could not connect to database"
  - **Solution**: Check your database configuration and ensure the database server is running

- **Error**: "Could not connect to Redis"
  - **Solution**: Check your Redis configuration and ensure the Redis server is running

#### Runtime Issues

- **Error**: "Service unavailable"
  - **Solution**: Check if all services are running and properly configured

- **Error**: "API key invalid"
  - **Solution**: Check your exchange API keys and ensure they have the correct permissions

### Logs

Check the logs for more information:

- **Standalone Installation**: Logs are stored in the `logs` directory
- **Docker Installation**: View logs using `docker-compose logs`
- **Development Installation**: Logs are printed to the console and stored in the `logs` directory

### Getting Help

If you encounter issues that you can't resolve:

- **Documentation**: Check the documentation for solutions
- **Community Forum**: Ask for help on the community forum
- **GitHub Issues**: Report bugs on GitHub
- **Support Email**: Contact support at support@example.com

## Next Steps

After installation, you can:

1. **Read the User Guide**: Learn how to use Cryptobot
2. **Explore the Dashboard**: Familiarize yourself with the interface
3. **Create a Strategy**: Develop your own trading strategy
4. **Run a Backtest**: Test your strategy against historical data
5. **Deploy for Live Trading**: Start trading with real or paper money