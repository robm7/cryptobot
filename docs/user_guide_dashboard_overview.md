## 1. Dashboard Overview & Navigation

Welcome to the CryptoBot Dashboard! This guide provides an overview of the main sections and how to navigate the application.

### Main Layout

The dashboard is designed to give you a comprehensive interface for managing your trading strategies, executing trades, monitoring performance, and configuring the bot. It typically consists of:

*   **Navigation Bar/Sidebar**: Usually located on the top or left side of the screen, this provides links to the major sections of the application.
*   **Main Content Area**: This is where the specific information and controls for the currently selected section are displayed.

### Key Dashboard Sections

While the exact layout and names might vary slightly, here are the common sections you'll find and their purpose:

1.  **Trading Panel (`/trade`)**:
    *   **Purpose**: This is your primary interface for manual trading and monitoring real-time market data.
    *   **Features**:
        *   Price chart for selected symbols.
        *   Account summary (balance, current positions, P&L).
        *   Order entry panel for placing market (and potentially limit) orders.
    *   *Covered in detail in the "Placing Orders" section.*

2.  **Strategies (`/strategies`)**:
    *   **Purpose**: Manage your automated trading strategies.
    *   **Features**:
        *   List of all your defined strategies.
        *   View details of each strategy (name, description, parameters, version, active status).
        *   (Potentially) Create new strategies, update existing ones, or delete them.
        *   Activate or deactivate strategies for live trading.
        *   Links to initiate backtests for each strategy.
    *   *Covered in detail in the "Strategy Management" section.*

3.  **Backtest (`/backtest` or `/backtest?strategy={id}`)**:
    *   **Purpose**: Test your strategies on historical data to evaluate their potential performance.
    *   **Features**:
        *   View detailed reports of completed backtests.
        *   Reports include performance metrics (Total Return, Sharpe Ratio, Max Drawdown), trade statistics (Win Rate, Total Trades), an equity curve chart, and a history of trades made during the backtest.
    *   *Covered in detail in the "Backtesting Strategies" section.*

4.  **Optimization (`/optimize`)**:
    *   **Purpose**: Find the best parameter settings for your strategies by running multiple backtests across a range of parameter values.
    *   **Features**:
        *   Select a strategy to optimize.
        *   Define ranges for its parameters (start, end, step).
        *   Configure backtest settings (symbol, timeframe, date range).
        *   View a table of results showing performance metrics for each parameter combination.
    *   *Covered in detail in the "Strategy Parameter Optimization" section.*

5.  **Settings (`/settings` or `/config-wizard`)**:
    *   **Purpose**: Configure application-wide settings, API keys for exchanges, database connections, notification preferences, etc.
    *   **Features**:
        *   **Configuration Wizard**: A guided setup for initial configuration of essential parameters.
        *   **API Key Management**: Add, update, or remove API keys for connecting to exchanges.
        *   **Notification Preferences**: Configure how you receive alerts (e.g., email, Slack).
        *   **Logging Levels**: Adjust application logging verbosity.
    *   *(Parts of this are covered in "Account Management & API Keys" and potentially a future "System Configuration" section).*

6.  **Login (`/login`)**:
    *   **Purpose**: Secure access to the dashboard. Users need to authenticate to use most features.

### General Navigation Tips

*   **Use the Navigation Bar/Sidebar**: This is your primary tool for moving between different sections.
*   **Browser Back/Forward**: Standard browser navigation buttons should work as expected for moving between viewed pages.
*   **Links and Buttons**: Look for buttons and links within pages that lead to related actions or detailed views (e.g., a "Backtest" button on a strategy card).

This overview should help you get familiar with the main areas of the CryptoBot dashboard. Each key section is, or will be, covered in more detail in subsequent parts of this user guide.