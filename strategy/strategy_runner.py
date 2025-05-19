import asyncio
import time
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime # Added import
from .schemas import StrategyTradeSignal # Updated import
# Assuming MeanReversionStrategy is in strategies.mean_reversion
# If the path is different, this import will need to be adjusted.
# from strategies.mean_reversion import MeanReversionStrategy
# For now, let's define a mock strategy if the actual one is not available
# or to simplify the example if its constructor is complex.

class MockExchangeInterface:
    """A mock exchange interface for placeholder purposes."""
    def __init__(self):
        logging.info("MockExchangeInterface initialized.")

    async def get_historical_data(self, symbol: str, timeframe: str, limit: int) -> list:
        return [] # Return empty list or mock data as needed

    async def get_current_price(self, symbol: str) -> Optional[float]:
        return None


class MeanReversionStrategy:
    """
    A simplified mock of MeanReversionStrategy for demonstration.
    In a real scenario, this would be imported from strategies.mean_reversion.
    """
    def __init__(self, exchange_interface: Optional[Any], symbol: str, lookback_period: int, entry_z_score: float, exit_z_score: float):
        self.exchange_interface = exchange_interface
        self.symbol = symbol
        self.lookback_period = lookback_period
        self.entry_z_score = entry_z_score
        self.exit_z_score = exit_z_score
        self.prices = []
        self._iteration_count = 0  # To generate alternating signals for demo
        logging.info(
            f"MeanReversionStrategy initialized for {symbol} with lookback={lookback_period}, "
            f"entry_z={entry_z_score}, exit_z={exit_z_score}"
        )

    async def process_realtime_data(self, data_point: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processes a real-time data point and generates a trading signal.
        Mock implementation: Generates BUY/SELL signals alternately for demo.
        """
        self.prices.append(data_point['close'])
        if len(self.prices) < 2: # Not enough data to do anything meaningful
            return None

        self._iteration_count += 1
        logging.debug(f"Processing data point {self._iteration_count}: {data_point['close']}")

        # Mock signal generation:
        if self._iteration_count % 4 == 1: # Buy
            return {"signal": "BUY", "price": data_point['close']}
        elif self._iteration_count % 4 == 3: # Sell
            return {"signal": "SELL", "price": data_point['close']}
        return None # No signal

from .signal_dispatcher import SignalDispatcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration (placeholders)
EXECUTION_SERVICE_URL = "http://localhost:8002" # Example URL, dispatcher appends /api/execute
STRATEGY_NAME = "MeanReversion_BTCUSD_Demo_Runner"
SYMBOL = "BTC/USD"
EXCHANGE_NAME = "binance"  # Example exchange
DEFAULT_QUANTITY = Decimal("0.01") # Example quantity

async def main():
    """
    Main function to demonstrate running a strategy and dispatching signals.
    """
    logging.info(f"Starting strategy runner for {STRATEGY_NAME} on {SYMBOL}")

    # Instantiate SignalDispatcher
    # In a real app, you might pass a pre-configured httpx.AsyncClient
    dispatcher = SignalDispatcher(execution_service_url=EXECUTION_SERVICE_URL)
    logging.info(f"SignalDispatcher initialized for URL: {EXECUTION_SERVICE_URL}")

    # Instantiate MeanReversionStrategy
    # Using None for exchange_interface as process_realtime_data might not use it directly
    # or a MockExchangeInterface if initialization requires it.
    mock_exchange = MockExchangeInterface() # Or None, depending on strategy's __init__
    strategy_instance = MeanReversionStrategy(
        exchange_interface=mock_exchange, # Using mock for this example
        symbol=SYMBOL,
        lookback_period=20,      # Example value
        entry_z_score=2.0,       # Example value
        exit_z_score=0.5         # Example value
    )
    logging.info("MeanReversionStrategy instance created.")

    # Simulated Data Feed (Loop)
    logging.info("Starting simulated data feed...")
    base_price = 60000  # Starting price for BTC/USD simulation

    for i in range(10):  # Simulate 10 data points
        # Simulate slight price variation
        price_variation = (i % 3 - 1) * 50  # Varies by -50, 0, +50
        current_close_price = base_price + price_variation + (i * 10) # Gradual increase with variation

        data_point: Dict[str, Any] = {
            'timestamp': time.time() * 1000,  # Milliseconds
            'open': current_close_price - 10,
            'high': current_close_price + 20,
            'low': current_close_price - 20,
            'close': current_close_price,
            'volume': 10 + i  # Simulate varying volume
        }
        logging.info(f"Processing data point {i+1}/10: {data_point}")

        # Signal Generation
        signal_data = await strategy_instance.process_realtime_data(data_point)

        # Signal Dispatching
        if signal_data:
            logging.info(f"Generated signal data: {signal_data} for {SYMBOL}")
            try:
                order_side_str = "buy" if signal_data["signal"] == "BUY" else "sell"
                
                current_price_float: Optional[float] = None
                order_type_str = "market"
                if signal_data.get("price") is not None:
                    order_type_str = "limit"
                    current_price_float = float(signal_data["price"])
                
                # Convert timestamp from ms to datetime object
                signal_timestamp_dt = datetime.utcfromtimestamp(data_point['timestamp'] / 1000)

                trade_signal = StrategyTradeSignal(
                    strategy_id=STRATEGY_NAME, # Use STRATEGY_NAME for strategy_id
                    symbol=SYMBOL,
                    side=order_side_str,
                    quantity=float(DEFAULT_QUANTITY), # Ensure quantity is float
                    order_type=order_type_str,
                    price=current_price_float,
                    timestamp=signal_timestamp_dt
                )
                logging.info(f"Constructed StrategyTradeSignal: {trade_signal.model_dump_json(indent=2)}")

                # The client_order_id was part of the old logging, let's keep a similar log message
                log_identifier = f"{STRATEGY_NAME}_{SYMBOL}_{int(time.time())}"
                success = await dispatcher.dispatch(trade_signal=trade_signal)
                if success:
                    logging.info(f"Trade signal dispatched successfully to execution service: {log_identifier}")
                else:
                    logging.warning(f"Failed to dispatch trade signal to execution service: {log_identifier}")
            except Exception as e:
                logging.error(f"Error processing or dispatching signal data '{signal_data}': {e}")
        else:
            logging.info("No signal generated for this data point.")

        await asyncio.sleep(1)  # Simulate time between data points

    # Cleanup
    logging.info("Simulated data feed finished. Closing dispatcher.")
    await dispatcher.close()
    logging.info("Dispatcher closed. Strategy runner finished.")

if __name__ == "__main__":
    asyncio.run(main())