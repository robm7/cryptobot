## 3. Placing Orders

This section guides you through the process of placing trades using the CryptoBot trading panel.

### Selecting Symbol and Quantity

Before placing any order, you need to specify the asset you want to trade and the amount.

*   **Symbol**: Use the "Symbol" dropdown in the "New Order" panel to select the trading pair (e.g., BTC/USDT, ETH/USDT). The available symbols are pre-configured.
*   **Quantity**: Enter the amount of the *base currency* (the first currency in the pair, e.g., BTC in BTC/USDT) you wish to buy or sell in the "Quantity" input field. Ensure the quantity meets the minimum order size requirements for the selected symbol on the exchange.

### Market Orders

A **market order** is an order to buy or sell an asset immediately at the best available current price. It prioritizes speed of execution over a specific price.

**How to Place a Market Order:**

1.  **Select Symbol and Quantity**: As described above.
2.  **Click "Buy" or "Sell"**:
    *   To place a market buy order, click the green "Buy" button.
    *   To place a market sell order, click the red "Sell" button.
3.  The order will attempt to execute immediately.

**Considerations for Market Orders:**
*   **Slippage**: The price at which your market order executes might be slightly different from the price you saw when you placed the order, especially in volatile markets or for large orders. This difference is called slippage.
*   **Guaranteed Fill (Usually)**: Market orders are generally guaranteed to fill as long as there is liquidity, but not at a specific price.

### Limit Orders

A **limit order** is an order to buy or sell an asset at a specific price or better.
*   A buy limit order will only execute at your limit price or lower.
*   A sell limit order will only execute at your limit price or higher.

Limit orders give you control over the execution price but do not guarantee that the order will be filled.

**How to Place a Limit Order:**

*(Note: The current UI shown in `dashboard/pages/trade.js` primarily supports market orders through the "Buy" and "Sell" buttons. The following describes how limit orders would typically be placed if the UI were extended to support them directly from this panel, or if using an API that distinguishes them.)*

1.  **Select Symbol and Quantity**: As described above.
2.  **Specify Order Type**: Select "Limit" from an order type dropdown (if available in the UI).
3.  **Enter Limit Price**: An input field for "Price" would appear. Enter your desired limit price here.
4.  **Click "Buy" or "Sell"**:
    *   To place a limit buy order, click the "Buy" button.
    *   To place a limit sell order, click the "Sell" button.
5.  Your order will be placed on the exchange's order book and will only execute if the market price reaches your limit price.

**Considerations for Limit Orders:**
*   **No Guaranteed Fill**: If the market price never reaches your limit price, your order may not be executed.
*   **Price Control**: You have control over the execution price, protecting you from unfavorable price movements beyond your limit.

### Order Confirmation

After you submit an order (market or limit):

*   **Loading State**: The "Buy" and "Sell" buttons will be temporarily disabled, and a loading indicator might appear while the order is being processed.
*   **Position Update**: If your order is filled (fully or partially), your "Current Position" in the "Account Summary" panel will update to reflect the new holding.
*   **Balance Update**: Your "Balance" will also update to reflect the cost of the trade (for buys) or the proceeds from the trade (for sells), including any trading fees.
*   **Error Messages**: If the order fails for any reason, an error message will be displayed below the order buttons, providing information about the failure.

### Handling Order Errors

If an order cannot be placed or executed, an error message will appear in the "New Order" panel. Common reasons for errors include:

*   **Insufficient Funds**: You may not have enough balance in the required currency to cover the order amount and fees.
*   **Invalid Parameters**: The quantity, price (for limit orders), or symbol might be invalid or not meet exchange requirements (e.g., minimum order size, price precision).
*   **Risk Limit Exceeded**: The order might violate pre-set risk management rules (e.g., maximum position size, daily loss limit).
*   **Exchange Errors**: The exchange might be temporarily unavailable, the trading pair might be suspended, or there might be other API issues.
*   **Authentication Issues**: Your API key might be invalid or have insufficient permissions.

Review the error message carefully. You may need to adjust your order parameters, check your account balance, or wait and try again if it's a temporary exchange issue.