## 4. Backtesting Strategies

Backtesting allows you to test your trading strategies on historical market data to see how they would have performed. This is a crucial step before deploying a strategy with real funds.

### Accessing the Backtest Feature

1.  Navigate to the "Strategies" page from the main dashboard.
2.  For each strategy listed, you will see a "Backtest" button.
3.  Clicking this button for a specific strategy will typically take you to a backtest configuration page or directly to the backtest results page if a default backtest has been run or is configured.

*(Assumption: The UI flow is `Strategies Page -> Click Backtest -> Backtest Config/Results Page` like `dashboard/pages/backtest.js`)*

### Configuring a Backtest

On the backtest page for a selected strategy (e.g., `dashboard/pages/backtest.js` when navigated with a `strategy` query parameter):

*   **Strategy Name**: The name of the strategy you are backtesting will be displayed.
*   **Symbol**: Select the trading pair you want to backtest against (e.g., BTC/USDT).
*   **Timeframe**: Choose the chart timeframe for the historical data (e.g., 1h, 4h, 1d).
*   **Start Date**: Select the beginning date for the historical data period.
*   **End Date**: Select the end date for the historical data period.
*   **Strategy Parameters (If configurable for backtest)**: Some strategies may allow you to override their default parameters specifically for a backtest run. If so, input fields for these parameters will be available.

Once configured, click a "Run Backtest" button (if the UI supports re-running with new parameters from this page).

### Understanding the Backtest Report

After a backtest is completed, a report will be displayed, typically including the following sections:

*   **Strategy Name**: Confirms the strategy that was tested.
*   **Performance Metrics**:
    *   **Total Return (%)**: The overall profit or loss of the strategy over the backtest period, expressed as a percentage of the initial capital.
    *   **Sharpe Ratio**: A measure of risk-adjusted return. Higher is generally better.
    *   **Max Drawdown (%)**: The largest peak-to-trough decline during a specific period, indicating the biggest loss from a single peak.
    *   *(Other metrics like Sortino Ratio, Calmar Ratio, Alpha, Beta may also be present).*
*   **Trade Statistics**:
    *   **Total Trades**: The total number of trades executed during the backtest.
    *   **Win Rate (%)**: The percentage of trades that were profitable.
    *   **Avg Win/Loss Ratio**: The average profit of winning trades divided by the average loss of losing trades.
    *   **Average Trade PnL**: The average profit or loss per trade.
    *   **Longest Winning/Losing Streak**: The number of consecutive winning or losing trades.
*   **Time Period**:
    *   **Start Date**: The start date of the backtest.
    *   **End Date**: The end date of the backtest.
    *   **Duration (Days)**: The total number of days covered by the backtest.
*   **Equity Curve Chart**:
    *   A visual representation of your account equity over the backtest period. This helps you see how the strategy performed over time, including periods of growth and drawdown.
*   **Trade History**:
    *   A detailed list of all trades executed by the strategy during the backtest.
    *   Typically includes: Date/Time, Type (Buy/Sell), Price, Size (Quantity), and PnL (Profit/Loss) for each trade.
    *   On mobile devices, this might be presented as a list of cards for better readability, while on desktops, it's often a table.

### Interpreting Results

*   **Positive Total Return and Sharpe Ratio**: Generally indicate a potentially profitable strategy.
*   **Max Drawdown**: Pay close attention to this. A high drawdown means the strategy experienced significant losses at some point, which might be unacceptable depending on your risk tolerance.
*   **Win Rate vs. Avg Win/Loss Ratio**: A strategy doesn't need a very high win rate if its winning trades are significantly larger than its losing trades.
*   **Equity Curve**: Look for a generally upward-sloping curve. Steep drops indicate periods of significant loss. A very volatile curve might indicate a risky strategy.
*   **Number of Trades**: Too few trades might mean the results are not statistically significant. Too many trades might incur high transaction costs.

### Parameter Optimization

The "Optimize" section of the dashboard allows you to run multiple backtests with different sets of parameters for a chosen strategy to find the optimal settings. See the "Strategy Parameter Optimization" section of this guide for more details.

**Important Considerations:**
*   **Past performance is not indicative of future results.** Backtesting shows how a strategy *would have* performed, but market conditions change.
*   **Overfitting**: Be careful not to over-optimize parameters to fit the historical data too perfectly, as this may lead to poor performance on live data.
*   **Slippage and Fees**: Ensure your backtesting engine realistically accounts for potential slippage and trading fees, as these can significantly impact profitability.