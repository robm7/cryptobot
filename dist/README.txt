==============================================
CryptoBot Trading System
==============================================

Thank you for downloading CryptoBot Trading System!

This README provides essential information to help you get started with CryptoBot.

==============================================
CONTENTS
==============================================

1. System Requirements
2. Installation
3. Getting Started
4. Command-Line Options
5. Configuration
6. Troubleshooting
7. Support

==============================================
1. SYSTEM REQUIREMENTS
==============================================

Windows:
- Windows 10 or later (64-bit)
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space

Linux:
- Ubuntu 20.04 or later, or equivalent (64-bit)
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space

macOS:
- macOS 10.15 (Catalina) or later (64-bit)
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space

==============================================
2. INSTALLATION
==============================================

Windows:
1. Extract the ZIP archive to a location of your choice
2. Run cryptobot.exe from the extracted folder

Linux:
1. Extract the tarball archive: tar -xzf cryptobot-linux.tar.gz
2. Make the executable file executable: chmod +x cryptobot/cryptobot
3. Run the executable: ./cryptobot/cryptobot

macOS:
1. Mount the DMG file by double-clicking it
2. Drag the CryptoBot application to your Applications folder
3. Run the application from your Applications folder

==============================================
3. GETTING STARTED
==============================================

To start CryptoBot with the dashboard:
```
cryptobot --dashboard
```

This will start the dashboard interface, which you can access in your web browser at:
http://localhost:8080

To start all services:
```
cryptobot --all
```

To run a specific service:
```
cryptobot --service auth
cryptobot --service data
cryptobot --service trade
cryptobot --service backtest
cryptobot --service strategy
```

==============================================
4. COMMAND-LINE OPTIONS
==============================================

CryptoBot supports the following command-line options:

--config PATH       Path to configuration file
--dashboard         Run the dashboard
--cli               Run the command-line interface
--service NAME      Run a specific service (auth, strategy, data, trade, backtest)
--all               Run all services
--config-ui         Run the configuration UI
--environment ENV   Set the environment (dev, test, stage, prod)
--profile PROFILE   Set the profile (default, docker, kubernetes)
--version           Show version information

Examples:
```
cryptobot --config my_config.json --all
cryptobot --dashboard --environment prod
cryptobot --service data --profile default
```

==============================================
5. CONFIGURATION
==============================================

CryptoBot uses a configuration file to control its behavior. By default, it uses the built-in default configuration.

To use a custom configuration file:
```
cryptobot --config path/to/config.json
```

You can also use the configuration UI to create and edit configuration files:
```
cryptobot --config-ui
```

This will start a web interface for configuring CryptoBot, which you can access in your web browser at:
http://localhost:8081

==============================================
6. TROUBLESHOOTING
==============================================

Common Issues:

1. "Port already in use" error:
   - Another application is using the same port
   - Stop the other application or change the port in the configuration file

2. "Cannot connect to exchange" error:
   - Check your internet connection
   - Verify your API keys in the configuration file
   - Ensure the exchange is operational

3. "Database connection error":
   - Ensure the database server is running
   - Check the database connection settings in the configuration file

4. Application crashes on startup:
   - Check the log file (cryptobot.log) for error messages
   - Ensure all dependencies are installed
   - Try running with a clean configuration file

For more troubleshooting information, please refer to the documentation.

==============================================
7. SUPPORT
==============================================

If you encounter any issues or have questions, please contact our support team:

- Documentation: https://cryptobot.example.com/docs
- Email: support@cryptobot.example.com
- GitHub Issues: https://github.com/cryptobot/cryptobot/issues

Thank you for using CryptoBot Trading System!