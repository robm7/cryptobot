import httpx
import logging
from typing import Optional
from datetime import datetime # Added import
from .schemas import StrategyTradeSignal # Updated import

logger = logging.getLogger(__name__)

class SignalDispatcher:
    """
    Dispatches trading signals to an execution service.
    """
    def __init__(self, execution_service_url: str):
        """
        Initializes the SignalDispatcher.

        Args:
            execution_service_url: The URL of the execution service.
        """
        self.execution_service_url = execution_service_url
        self.http_client = httpx.AsyncClient()
        logger.info(f"SignalDispatcher initialized with execution service URL: {self.execution_service_url}")

    async def dispatch(self, trade_signal: StrategyTradeSignal) -> bool:
        """
        Dispatches a trading signal to the execution service.

        Args:
            trade_signal: The trading signal object.

        Returns:
            True if the signal was dispatched successfully, False otherwise.
        """
        payload = {
            "symbol": trade_signal.symbol,
            "side": trade_signal.side.lower(), # side is now a string
            "quantity": float(trade_signal.quantity), # Ensure it's float, was 'amount' previously in some contexts
            "order_type": trade_signal.order_type.lower(), # order_type is now a string, was 'type'
            "strategy_id": trade_signal.strategy_id # Pass strategy_id
        }
        # 'exchange' and 'client_order_id' are removed as they are not in the new StrategyTradeSignal
        # and typically handled by the execution service or its configuration.

        if trade_signal.order_type.lower() == "limit" and trade_signal.price is not None:
            payload["price"] = float(trade_signal.price)

        endpoint_url = f"{self.execution_service_url}/orders"
        logger.debug(f"Dispatching signal to {endpoint_url} with payload: {payload}")

        try:
            response = await self.http_client.post(endpoint_url, json=payload)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses

            if response.status_code in [200, 201]:
                logger.info(
                    f"Successfully dispatched signal: {trade_signal.side} for {trade_signal.strategy_id} on {trade_signal.symbol}. "
                    f"Response: {response.text}"
                )
                return True
            else:
                # This case might be redundant due to raise_for_status, but kept for clarity
                logger.error(
                    f"Failed to dispatch signal: {trade_signal.side} for {trade_signal.strategy_id} on {trade_signal.symbol}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False
        except httpx.RequestError as e:
            logger.error(
                f"HTTP request error while dispatching signal {trade_signal.side} for {trade_signal.strategy_id} on {trade_signal.symbol} "
                f"to {endpoint_url}: {e.__class__.__name__} - {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while dispatching signal {trade_signal.side} for {trade_signal.strategy_id} on {trade_signal.symbol}: {e}"
            )
            return False

    async def close(self):
        """
        Closes the HTTP client.
        Should be called when the dispatcher is no longer needed.
        """
        await self.http_client.aclose()
        logger.info("HTTP client closed for SignalDispatcher.")

if __name__ == '__main__':
    # Example Usage (requires a running execution service)
    import asyncio
    from decimal import Decimal # Keep for example if needed, though StrategyTradeSignal uses float
    # from .schemas import InterfaceOrderSide, InterfaceOrderType # Removed, not used
    import time

    logging.basicConfig(level=logging.INFO)

    async def main():
        # Replace with your actual execution service URL
        execution_url = "http://localhost:8000" # Example URL, ensure your trade service is running here
        dispatcher = SignalDispatcher(execution_service_url=execution_url)

        # Example LIMIT BUY signal dispatch
        buy_signal_limit = StrategyTradeSignal(
            strategy_id="TestStrategyLimit", # Changed from strategy_name
            symbol="BTC/USD",
            side="buy", # Changed from InterfaceOrderSide.BUY
            order_type="limit", # Changed from InterfaceOrderType.LIMIT
            quantity=0.01, # Changed from Decimal
            price=60000.0, # Changed from Decimal
            timestamp=datetime.utcnow() # Changed to datetime object
            # 'exchange' and 'client_order_id' removed
        )
        success_buy_limit = await dispatcher.dispatch(trade_signal=buy_signal_limit)
        if success_buy_limit:
            print(f"LIMIT BUY signal for {buy_signal_limit.symbol} dispatched successfully.")
        else:
            print(f"Failed to dispatch LIMIT BUY signal for {buy_signal_limit.symbol}.")

        # Example MARKET SELL signal dispatch
        sell_signal_market = StrategyTradeSignal(
            strategy_id="TestStrategyMarket", # Changed from strategy_name
            symbol="ETH/USD",
            side="sell", # Changed from InterfaceOrderSide.SELL
            order_type="market", # Changed from InterfaceOrderType.MARKET
            quantity=0.5, # Changed from Decimal
            price=None, # Market orders don't have a price, remains float Optional
            timestamp=datetime.utcnow() # Changed to datetime object
            # 'exchange' and 'client_order_id' removed
        )
        success_sell_market = await dispatcher.dispatch(trade_signal=sell_signal_market)
        if success_sell_market:
            print(f"MARKET SELL signal for {sell_signal_market.symbol} dispatched successfully.")
        else:
            print(f"Failed to dispatch MARKET SELL signal for {sell_signal_market.symbol}.")

        await dispatcher.close()

    # To run this example, you would need an asyncio event loop:
    # try:
    #     asyncio.run(main())
    # except ImportError:
    #     print("Could not run example: Ensure this script is part of a package to use relative imports like '.schemas'")
    #     print("Alternatively, adjust imports if running as a standalone script and schemas.py is in the same directory.")
    # Note: This example won't run directly without an execution service
    # and might need adjustments based on your project structure if run as a script.
    pass