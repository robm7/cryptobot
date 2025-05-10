from abc import ABC, abstractmethod
import pandas as pd
import logging
# Import the exchange interface
from utils.exchange_interface import ExchangeInterface, MockExchangeInterface # Added import

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, exchange_interface: ExchangeInterface = None, **params):
        """Initialize the strategy with given parameters and an exchange interface."""
        self.params = params
        self.position_size = 0.0  # Current position size (positive for long, negative for short)
        self.average_entry_price = 0.0 # Average entry price of the current position
        self.data_buffer = pd.DataFrame() # Buffer to store recent data for calculations
        self.max_buffer_size = params.get('lookback_period', 50) * 2 # Default buffer size, adjust as needed
        # Store the exchange interface
        self.exchange_interface = exchange_interface or MockExchangeInterface() # Use Mock if none provided
        logger.info(f"Initialized {self.__class__.__name__} with params: {params} and interface: {self.exchange_interface.__class__.__name__}")

    @staticmethod
    @abstractmethod
    def validate_parameters(params: dict) -> None:
        """Validate the parameters specific to the strategy implementation."""
        pass

    @abstractmethod
    async def process_realtime_data(self, data_point: dict) -> None:
        """
        Process a single incoming real-time data point (e.g., kline update).
        Update internal state, indicators, and generate trading signals.
        This method should be implemented by subclasses.

        Args:
            data_point (dict): A dictionary containing the latest market data,
                               e.g., {'timestamp': ..., 'open': ..., 'high': ..., 
                                     'low': ..., 'close': ..., 'volume': ...}
        """
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame):
        """
        Generate trading signals based on historical data (primarily for backtesting).
        This method might be adapted or deprecated for purely real-time strategies.
        """
        pass

    def _update_buffer(self, data_point: dict):
        """Appends a new data point to the buffer and trims it."""
        # Convert data_point dictionary to a DataFrame row
        # Ensure timestamp is suitable for indexing if needed
        try:
            timestamp = pd.to_datetime(data_point['timestamp'], unit='ms')
            new_row = pd.DataFrame([data_point], index=[timestamp])
            
            # Convert numeric columns
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                if col in new_row.columns:
                    new_row[col] = pd.to_numeric(new_row[col], errors='coerce')

            # Append new data
            self.data_buffer = pd.concat([self.data_buffer, new_row])

            # Keep buffer size manageable
            if len(self.data_buffer) > self.max_buffer_size:
                self.data_buffer = self.data_buffer.iloc[-self.max_buffer_size:]
                
            # logger.debug(f"{self.__class__.__name__} buffer updated. Size: {len(self.data_buffer)}")
        except Exception as e:
            logger.error(f"Error updating buffer in {self.__class__.__name__}: {e} - Data point: {data_point}")

    # Optional: Add common helper methods like risk checks etc.
    def _update_position_from_fill(self, fill_details: dict):
        """
        Updates the strategy's internal position state based on an order fill.
        Assumes fill_details contains keys like 'side', 'amount', 'price'.

        Args:
            fill_details (dict): A dictionary containing details of the fill,
                               e.g., {'side': 'buy', 'amount': 0.1, 'price': 50000.0}
        """
        try:
            side = fill_details['side']
            filled_amount = float(fill_details['amount'])
            fill_price = float(fill_details['price'])

            if filled_amount <= 0 or fill_price <= 0:
                logger.warning(f"{self.__class__.__name__}: Ignoring fill with non-positive amount or price: {fill_details}")
                return

            logger.info(f"{self.__class__.__name__}: Processing fill: Side={side}, Amount={filled_amount}, Price={fill_price}. Current Pos: Size={self.position_size}, AvgEntry={self.average_entry_price}")

            current_size = self.position_size
            current_avg_price = self.average_entry_price

            # Determine the signed amount based on side
            signed_filled_amount = filled_amount if side == 'buy' else -filled_amount

            new_position_size = current_size + signed_filled_amount

            if abs(new_position_size) < 1e-9: # Position closed or flattened (using tolerance for float comparison)
                self.position_size = 0.0
                self.average_entry_price = 0.0
                logger.info(f"{self.__class__.__name__}: Position closed by fill. New Size=0.0, AvgEntry=0.0")

            elif (current_size >= 0 and signed_filled_amount > 0) or (current_size <= 0 and signed_filled_amount < 0):
                # Increasing position size (or opening new position)
                if abs(current_size) < 1e-9: # Opening new position
                    self.average_entry_price = fill_price
                else: # Increasing existing position
                    # Calculate new average entry price: (old_value + new_value) / new_total_size
                    old_value = abs(current_size) * current_avg_price
                    new_value = filled_amount * fill_price
                    self.average_entry_price = (old_value + new_value) / abs(new_position_size)
                self.position_size = new_position_size
                logger.info(f"{self.__class__.__name__}: Position opened/increased. New Size={self.position_size:.8f}, New AvgEntry={self.average_entry_price:.4f}")

            elif (current_size > 0 and signed_filled_amount < 0) or (current_size < 0 and signed_filled_amount > 0):
                # Reducing position size (opposite direction fill)
                if abs(signed_filled_amount) >= abs(current_size) - 1e-9: # Position closed or flipped (using tolerance)
                    # If flipped, calculate new entry price based on the overshoot
                    self.position_size = new_position_size
                    self.average_entry_price = fill_price # Entry price for the new flipped position is the fill price
                    logger.info(f"{self.__class__.__name__}: Position flipped by fill. New Size={self.position_size:.8f}, New AvgEntry={self.average_entry_price:.4f}")
                else:
                    # Just reducing size, average entry price remains the same
                    self.position_size = new_position_size
                    # self.average_entry_price remains unchanged
                    logger.info(f"{self.__class__.__name__}: Position reduced. New Size={self.position_size:.8f}, AvgEntry remains {self.average_entry_price:.4f}")
            else:
                 logger.error(f"{self.__class__.__name__}: Unhandled position update scenario. Current={current_size}, Fill={signed_filled_amount}")

        except KeyError as e:
            logger.error(f"{self.__class__.__name__}: Missing key in fill_details for position update: {e}. Details: {fill_details}")
        except ValueError as e:
            logger.error(f"{self.__class__.__name__}: Invalid numeric value in fill_details: {e}. Details: {fill_details}")
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: Unexpected error updating position from fill: {e}. Details: {fill_details}")

    async def _execute_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, params: dict = None):
        """Executes an order using the provided exchange interface."""
        if not self.exchange_interface:
            logger.error(f"{self.__class__.__name__}: Cannot execute order, exchange interface not set.")
            return None
        try:
            logger.info(f"{self.__class__.__name__}: Placing {side} {order_type} order for {amount} {symbol} at {price or 'market'}")
            order_result = await self.exchange_interface.place_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params
            )
            logger.info(f"{self.__class__.__name__}: Order placement result: {order_result}")
            # Potentially update internal state based on order result (e.g., pending order ID)
            return order_result
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: Error executing order: {e}")