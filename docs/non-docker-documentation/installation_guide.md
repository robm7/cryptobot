# Installation Guide

This guide provides detailed instructions for installing the non-Docker version of Cryptobot on various operating systems.

## Table of Contents
- [System Requirements](#system-requirements)
- [Windows Installation](#windows-installation)
- [macOS Installation](#macos-installation)
- [Linux Installation](#linux-installation)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting Installation Issues](#troubleshooting-installation-issues)

## System Requirements

### Minimum Requirements

- **CPU**: Dual-core processor, 2.0 GHz or higher
- **RAM**: 4 GB
- **Storage**: 1 GB free space
- **Operating System**:
  - Windows 10/11 (64-bit)
  - macOS 11 (Big Sur) or newer
  - Ubuntu 20.04 LTS, Debian 10, Fedora 32, or later
- **Network**: Stable internet connection
- **Dependencies**:
  - Python 3.8 or newer (included in the installer for Windows and macOS)

### Recommended Requirements

- **CPU**: Quad-core processor, 2.5 GHz or higher
- **RAM**: 8 GB or more
- **Storage**: 5 GB free space
- **Network**: High-speed internet connection

## Windows Installation

### Standard Installation

1. **Download the Installer**:
   - Go to the [Releases page](https://github.com/yourusername/cryptobot/releases)
   - Download the latest Windows installer (`cryptobot-setup.exe`)

2. **Run the Installer**:
   - Double-click the installer to start the installation process
   - Follow the on-screen instructions:
     - Choose the installation directory (default: `C:\Program Files\CryptoBot`)
     - Select components to install (Core Application, Trading Strategies, Exchange Connectors, etc.)
     - Choose whether to create desktop and Start Menu shortcuts
     - Choose whether to start CryptoBot at system startup

3. **Launch Cryptobot**:
   - After installation completes, you can launch CryptoBot from the Start Menu or desktop shortcut

### Silent Installation (for automated deployment)

```
cryptobot-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
```

Additional options:
- `/DIR="X:\path\to\install"` - Set the installation directory
- `/COMPONENTS="main,strategies,exchanges,dashboard"` - Select components to install
- `/TASKS="desktopicon,startmenu,autostart"` - Select tasks to perform

### Manual Installation from Source

1. **Install Python 3.8 or newer**:
   - Download and install Python from [python.org](https://www.python.org/downloads/)
   - Ensure you check "Add Python to PATH" during installation

2. **Download the Source Code**:
   - Clone the repository: `git clone https://github.com/yourusername/cryptobot.git`
   - Or download the ZIP file from the [Releases page](https://github.com/yourusername/cryptobot/releases)

3. **Install Dependencies**:
   - Open Command Prompt as Administrator
   - Navigate to the Cryptobot directory: `cd path\to\cryptobot`
   - Install dependencies: `pip install -r requirements.txt`

4. **Run the Setup Script**:
   - Run: `python setup.py install`

5. **Launch Cryptobot**:
   - Run: `cryptobot-launcher`

## macOS Installation

### Standard Installation

1. **Download the Installer**:
   - Go to the [Releases page](https://github.com/yourusername/cryptobot/releases)
   - Download the latest macOS installer (`CryptoBot-1.0.0.dmg`)

2. **Install the Application**:
   - Double-click the DMG file to mount it
   - Drag the CryptoBot application to the Applications folder
   - Optionally, drag the CryptoBot Launcher application to the Applications folder
   - Eject the DMG

3. **Launch Cryptobot**:
   - Open the Applications folder and double-click CryptoBot or CryptoBot Launcher to start the application

#### First Run on macOS

When you first run CryptoBot on macOS, you may see a security warning. To allow the application to run:

1. Open System Preferences > Security & Privacy
2. Click the "Open Anyway" button next to the message about CryptoBot
3. Confirm by clicking "Open" in the dialog that appears

### Manual Installation from Source

1. **Install Python 3.8 or newer**:
   - Download and install Python from [python.org](https://www.python.org/downloads/)
   - Or use Homebrew: `brew install python`

2. **Download the Source Code**:
   - Clone the repository: `git clone https://github.com/yourusername/cryptobot.git`
   - Or download the ZIP file from the [Releases page](https://github.com/yourusername/cryptobot/releases)

3. **Install Dependencies**:
   - Open Terminal
   - Navigate to the Cryptobot directory: `cd path/to/cryptobot`
   - Install dependencies: `pip install -r requirements.txt`

4. **Run the Setup Script**:
   - Run: `python setup.py install`

5. **Launch Cryptobot**:
   - Run: `cryptobot-launcher`

## Linux Installation

### Debian/Ubuntu (DEB package)

1. **Download the Package**:
   ```bash
   wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot_1.0.0_amd64.deb
   ```

2. **Install the Package**:
   ```bash
   sudo dpkg -i cryptobot_1.0.0_amd64.deb
   sudo apt-get install -f  # Install any missing dependencies
   ```

3. **Launch Cryptobot**:
   ```bash
   cryptobot
   ```
   or
   ```bash
   cryptobot-launcher
   ```

### Fedora/RHEL/CentOS (RPM package)

1. **Download the Package**:
   ```bash
   wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot-1.0.0-1.x86_64.rpm
   ```

2. **Install the Package**:
   ```bash
   sudo dnf install cryptobot-1.0.0-1.x86_64.rpm
   ```
   or
   ```bash
   sudo yum install cryptobot-1.0.0-1.x86_64.rpm
   ```

3. **Launch Cryptobot**:
   ```bash
   cryptobot
   ```
   or
   ```bash
   cryptobot-launcher
   ```

### Manual Installation from Source

1. **Install Python 3.8 or newer**:
   ```bash
   # Debian/Ubuntu
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv

   # Fedora
   sudo dnf install python3 python3-pip python3-virtualenv

   # Arch Linux
   sudo pacman -S python python-pip
   ```

2. **Download the Source Code**:
   ```bash
   git clone https://github.com/yourusername/cryptobot.git
   cd cryptobot
   ```

3. **Install Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Run the Setup Script**:
   ```bash
   python3 setup.py install
   ```

5. **Launch Cryptobot**:
   ```bash
   cryptobot-launcher
   ```

## Verifying Installation

After installing CryptoBot, you should verify that the installation was successful:

1. **Check Service Availability**:
   - Launch the CryptoBot Quick Start Launcher
   - Verify that all services are available for selection

2. **Start Core Services**:
   - Select and start the core services (Auth, Strategy, Data, Trade, Backtest)
   - Verify that all services start without errors

3. **Access the Dashboard**:
   - Click "Open in Browser" or navigate to `http://localhost:8080` in your web browser
   - Verify that you can access the dashboard

4. **Check Version Information**:
   - In the dashboard, navigate to Settings > About
   - Verify that the version information matches the expected version

## Troubleshooting Installation Issues

### Common Installation Issues

#### Windows

1. **Installer Fails to Run**:
   - Verify that you have administrator privileges
   - Check Windows Defender or antivirus settings
   - Try running the installer in compatibility mode

2. **Missing Dependencies**:
   - Run the installer again and select "Repair"
   - Manually install missing dependencies

#### macOS

1. **"App is damaged and can't be opened" Error**:
   - Open System Preferences > Security & Privacy
   - Allow apps downloaded from identified developers
   - Try downloading the installer again

2. **Permission Issues**:
   - Ensure you have administrator privileges
   - Check folder permissions

#### Linux

1. **Package Dependencies**:
   - If you encounter dependency issues with DEB or RPM packages:
     ```bash
     # Debian/Ubuntu
     sudo apt-get install -f

     # Fedora
     sudo dnf install --allowerasing cryptobot-1.0.0-1.x86_64.rpm
     ```

2. **Python Version Issues**:
   - Verify Python version: `python3 --version`
   - Install the correct Python version if needed

### Getting Help

If you encounter installation issues that you can't resolve:

1. **Check Documentation**:
   - Review this installation guide
   - Check the [troubleshooting guide](troubleshooting_guide.md)

2. **Community Support**:
   - Post on the community forum
   - Check for similar installation issues and solutions

3. **Professional Support**:
   - Contact support at support@example.com
   - Provide detailed information about the issue
   - Include logs and error messages