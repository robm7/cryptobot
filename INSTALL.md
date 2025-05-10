# CryptoBot Installation Guide

This guide provides instructions for installing CryptoBot on Windows, macOS, and Linux platforms.

## System Requirements

### Windows
- Windows 10 or later
- 4GB RAM minimum (8GB recommended)
- 500MB free disk space
- Python 3.7 or later (included in installer)

### macOS
- macOS 10.14 (Mojave) or later
- 4GB RAM minimum (8GB recommended)
- 500MB free disk space
- Python 3.7 or later (included in installer)

### Linux
- Ubuntu 20.04 LTS, Debian 10, Fedora 32, or later
- 4GB RAM minimum (8GB recommended)
- 500MB free disk space
- Python 3.7 or later

## Installation Instructions

### Windows

1. Download the latest Windows installer (`cryptobot-setup.exe`) from the releases page.
2. Double-click the installer to start the installation process.
3. Follow the on-screen instructions:
   - Choose the installation directory (default: `C:\Program Files\CryptoBot`)
   - Select components to install (Core Application, Trading Strategies, Exchange Connectors, etc.)
   - Choose whether to create desktop and Start Menu shortcuts
   - Choose whether to start CryptoBot at system startup
4. Click "Install" to begin the installation.
5. After installation completes, you can launch CryptoBot from the Start Menu or desktop shortcut.

#### Silent Installation

For automated deployment, you can use the following command to perform a silent installation:

```
cryptobot-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
```

Additional options:
- `/DIR="X:\path\to\install"` - Set the installation directory
- `/COMPONENTS="main,strategies,exchanges,dashboard"` - Select components to install
- `/TASKS="desktopicon,startmenu,autostart"` - Select tasks to perform

### macOS

1. Download the latest macOS installer (`CryptoBot-1.0.0.dmg`) from the releases page.
2. Double-click the DMG file to mount it.
3. Drag the CryptoBot application to the Applications folder.
4. Optionally, drag the CryptoBot Launcher application to the Applications folder.
5. Eject the DMG.
6. Open the Applications folder and double-click CryptoBot or CryptoBot Launcher to start the application.

#### First Run on macOS

When you first run CryptoBot on macOS, you may see a security warning. To allow the application to run:

1. Open System Preferences > Security & Privacy.
2. Click the "Open Anyway" button next to the message about CryptoBot.
3. Confirm by clicking "Open" in the dialog that appears.

### Linux

#### Debian/Ubuntu (DEB package)

1. Download the latest DEB package (`cryptobot_1.0.0_amd64.deb`) from the releases page.
2. Install the package using one of the following methods:

   Using the GUI:
   - Double-click the DEB file to open it with your package manager
   - Click "Install"

   Using the terminal:
   ```
   sudo dpkg -i cryptobot_1.0.0_amd64.deb
   sudo apt-get install -f  # Install any missing dependencies
   ```

3. Launch CryptoBot from the application menu or by running `cryptobot` or `cryptobot-launcher` in the terminal.

#### Fedora/RHEL/CentOS (RPM package)

1. Download the latest RPM package (`cryptobot-1.0.0-1.x86_64.rpm`) from the releases page.
2. Install the package using one of the following methods:

   Using the GUI:
   - Double-click the RPM file to open it with your package manager
   - Click "Install"

   Using the terminal:
   ```
   sudo dnf install cryptobot-1.0.0-1.x86_64.rpm
   ```
   or
   ```
   sudo yum install cryptobot-1.0.0-1.x86_64.rpm
   ```

3. Launch CryptoBot from the application menu or by running `cryptobot` or `cryptobot-launcher` in the terminal.

## Post-Installation Configuration

After installing CryptoBot, you'll need to configure it for your specific needs:

1. Launch the CryptoBot Quick Start Launcher.
2. Configure your environment settings:
   - Environment: dev, test, stage, prod
   - Profile: default, docker, kubernetes
   - Log Level: DEBUG, INFO, WARNING, ERROR
3. Select the services you want to start:
   - Core Services: Authentication, Strategy, Data, Trade, Backtest
   - MCP Services: Exchange Gateway, Market Data, Order Execution, etc.
   - Dashboard: Web interface for monitoring and control
4. Click "Start Selected Services" to start the selected services.
5. Click "Open in Browser" to open the dashboard in your web browser.

## Configuration Files

The main configuration file is located at:

- Windows: `%APPDATA%\CryptoBot\config.json`
- macOS: `~/Library/Application Support/CryptoBot/config.json`
- Linux: `/etc/cryptobot/config.json`

You can edit this file to customize CryptoBot's behavior. See the [Configuration Guide](docs/configuration.md) for more information.

## Running as a Service

### Windows

The Windows installer includes an option to run CryptoBot at system startup. If you didn't select this option during installation, you can enable it later:

1. Open the Start Menu and search for "Task Scheduler".
2. Click "Create Basic Task".
3. Enter a name and description for the task.
4. Select "When the computer starts" as the trigger.
5. Select "Start a program" as the action.
6. Browse to the CryptoBot executable (`C:\Program Files\CryptoBot\cryptobot.exe`).
7. Add any command-line arguments you need.
8. Complete the wizard.

### macOS

To run CryptoBot as a service on macOS:

1. Create a LaunchAgent plist file at `~/Library/LaunchAgents/com.cryptobot.trading.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.trading</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/CryptoBot.app/Contents/MacOS/CryptoBot</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>~/Library/Logs/CryptoBot/cryptobot.log</string>
    <key>StandardErrorPath</key>
    <string>~/Library/Logs/CryptoBot/cryptobot.log</string>
</dict>
</plist>
```

2. Load the LaunchAgent:

```
launchctl load ~/Library/LaunchAgents/com.cryptobot.trading.plist
```

### Linux

The Linux packages include a systemd service file. To manage the service:

```
# Start the service
sudo systemctl start cryptobot

# Stop the service
sudo systemctl stop cryptobot

# Enable the service to start at boot
sudo systemctl enable cryptobot

# Disable the service from starting at boot
sudo systemctl disable cryptobot

# Check the service status
sudo systemctl status cryptobot
```

## Uninstallation

### Windows

1. Open the Control Panel.
2. Go to "Programs and Features" or "Apps & features".
3. Find CryptoBot in the list of installed programs.
4. Click "Uninstall" and follow the on-screen instructions.

### macOS

1. Open the Applications folder.
2. Drag CryptoBot and CryptoBot Launcher to the Trash.
3. Empty the Trash.

To remove all associated files:

```
rm -rf ~/Library/Application\ Support/CryptoBot
rm -rf ~/Library/Logs/CryptoBot
rm ~/Library/LaunchAgents/com.cryptobot.trading.plist
```

### Linux

#### Debian/Ubuntu

```
sudo apt-get remove cryptobot
```

To remove all configuration files:

```
sudo apt-get purge cryptobot
```

#### Fedora/RHEL/CentOS

```
sudo dnf remove cryptobot
```

or

```
sudo yum remove cryptobot
```

## Troubleshooting

### Common Issues

#### Windows

- **Issue**: "The application was unable to start correctly (0xc000007b)"
  - **Solution**: Install the Visual C++ Redistributable for Visual Studio 2015-2019.

- **Issue**: "Python not found" error
  - **Solution**: The installer should include Python, but if you encounter this error, install Python 3.7 or later manually.

#### macOS

- **Issue**: "CryptoBot cannot be opened because the developer cannot be verified"
  - **Solution**: See the "First Run on macOS" section above.

- **Issue**: "Python not found" error
  - **Solution**: Install Python 3.7 or later using Homebrew: `brew install python`.

#### Linux

- **Issue**: Missing dependencies
  - **Solution**: Run `sudo apt-get install -f` (Debian/Ubuntu) or `sudo dnf install --allowerasing cryptobot` (Fedora/RHEL/CentOS) to install missing dependencies.

- **Issue**: "Permission denied" when running CryptoBot
  - **Solution**: Ensure the executable has the correct permissions: `sudo chmod +x /opt/cryptobot/cryptobot`.

### Logs

Check the following log files for troubleshooting:

- Windows: `%APPDATA%\CryptoBot\logs\cryptobot.log`
- macOS: `~/Library/Logs/CryptoBot/cryptobot.log`
- Linux: `/var/log/cryptobot/cryptobot.log`

### Getting Help

If you encounter any issues not covered in this guide, please:

1. Check the [Troubleshooting Guide](docs/troubleshooting.md) for more detailed information.
2. Visit the [Discussions](https://github.com/yourrepo/discussions) page for community support.
3. Open an [Issue](https://github.com/yourrepo/issues) if you believe you've found a bug.

## Updating

CryptoBot includes a built-in update mechanism that can automatically check for, download, and install updates across all supported platforms (Windows, macOS, and Linux).

### Automatic Updates

The update mechanism can be configured to automatically check for updates at regular intervals. To enable automatic updates:

1. Open the CryptoBot Quick Start Launcher
2. Click "Check for Updates"
3. In the update dialog, you can configure automatic update settings

### Manual Updates

You can manually check for updates at any time:

1. Open the CryptoBot Quick Start Launcher
2. Click "Check for Updates"
3. If an update is available, you can download and install it

### Update Configuration

The update mechanism can be configured through the main configuration file:

- Windows: `%APPDATA%\CryptoBot\config.json`
- macOS: `~/Library/Application Support/CryptoBot/config.json`
- Linux: `/etc/cryptobot/config.json`

Example configuration:

```json
{
  "update": {
    "update_url": "https://api.cryptobot.com/updates",
    "check_interval": 86400,
    "auto_check": true,
    "auto_download": false,
    "auto_install": false
  }
}
```

### Update Process

The update process consists of the following steps:

1. **Check for Updates**: The system checks for updates from the update server
2. **Download Update**: If an update is available, it is downloaded and verified
3. **Backup Current Installation**: Before installing the update, a backup of the current installation is created
4. **Install Update**: The update is installed
5. **Restart Application**: The application is restarted after the update is installed

If any step fails, the update process is aborted and the system is rolled back to the previous state.

### Rollback

If an update fails or causes issues, you can roll back to the previous version:

1. Open the CryptoBot Quick Start Launcher
2. Click "Check for Updates"
3. In the update dialog, click "Rollback"

For more detailed information about the update mechanism, see the [Update Mechanism Documentation](docs/update_mechanism.md).