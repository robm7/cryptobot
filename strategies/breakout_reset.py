import pandas as pd
import numpy as np
import logging # Added
from .base_strategy import BaseStrategy
from utils.exchange_interface import ExchangeInterface

logger = logging.getLogger(__name__) # Added logger instance

class BreakoutResetStrategy(BaseStrategy): # Inherit from BaseStrategy
    """Strategy based on Bollinger Band breakouts and mean reversion."""

    def __init__(self, symbol: str, exchange_interface: ExchangeInterface, **params):
        # Validate parameters before initializing
        self.validate_parameters(params)
        # Call BaseStrategy init correctly (only exchange_interface and **params)
        super().__init__(exchange_interface=exchange_interface, **params)
        self.symbol = symbol # Set symbol specifically for this strategy instance
        # Default parameters (can be overridden by params)
        self.lookback_period = params.get('lookback_period', 20)
        self.volatility_multiplier = params.get('volatility_multiplier', 2.0)
        self.reset_threshold = params.get('reset_threshold', 0.5) # Percentage of band width for reset
        self.take_profit = params.get('take_profit', None) # Optional TP percentage
        self.stop_loss = params.get('stop_loss', None) # Optional SL percentage
        self.position_size_pct = params.get('position_size_pct', 0.1) # Default 10% of available capital

        # self.data_buffer is initialized in BaseStrategy
        # self.position_size and self.average_entry_price are inherited from BaseStrategy
        logger.info(f"Initialized BreakoutResetStrategy for {self.symbol} with params: {params}")

    @staticmethod
    def validate_parameters(params: dict) -> None:
        """Validate parameters specific to BreakoutResetStrategy."""
        required_numeric = {
            'lookback_period': int,
            'volatility_multiplier': float,
            'reset_threshold': float,
            'position_size_pct': float
        }
        optional_numeric = {
            'take_profit': float,
            'stop_loss': float
        }

        for param, expected_type in required_numeric.items():
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
            try:
                value = expected_type(params[param])
                if param == 'lookback_period' and value <= 0:
                    raise ValueError(f"Parameter '{param}' must be positive.")
                if param in ['volatility_multiplier', 'reset_threshold', 'position_size_pct'] and value <= 0:
                     raise ValueError(f"Parameter '{param}' must be positive.")
                if param == 'position_size_pct' and not (0 < value <= 1):
                     raise ValueError(f"Parameter '{param}' must be between 0 (exclusive) and 1 (inclusive).")
            except (ValueError, TypeError):
                raise ValueError(f"Parameter '{param}' must be a valid {expected_type.__name__}. Got: {params[param]}")

        for param, expected_type in optional_numeric.items():
            if param in params and params[param] is not None:
                try:
                    value = expected_type(params[param])
                    if value <= 0:
                         raise ValueError(f"Optional parameter '{param}' must be positive if provided. Got: {value}")
                except (ValueError, TypeError):
                    raise ValueError(f"Optional parameter '{param}' must be a valid {expected_type.__name__} or None. Got: {params[param]}")

    def _calculate_bands(self):
        """Calculates Bollinger Bands based on the current data buffer."""
        if len(self.data_buffer) < self.lookback_period:
            return None, None, None # Not enough data

        closes = self.data_buffer['close'].tail(self.lookback_period)
        sma = closes.mean()
        std_dev = closes.std()

        upper_band = sma + self.volatility_multiplier * std_dev
        lower_band = sma - self.volatility_multiplier * std_dev

        return sma, upper_band, lower_band

    def generate_signals(self, candles: pd.DataFrame) -> pd.Series:
        """Generates trading signals based on historical candle data (for backtesting)."""
        if candles.empty or len(candles) < self.lookback_period:
            logger.warning(f"[{self.symbol}] Not enough historical data for signal generation ({len(candles)} < {self.lookback_period})")
            return pd.Series(0, index=candles.index)

        signals = pd.Series(0, index=candles.index)
        # Backtest simulation needs its own local position tracking
        backtest_position = 0
        backtest_entry_price = None

        # Calculate Bollinger Bands
        closes = candles['close']
        sma = closes.rolling(window=self.lookback_period).mean()
        std_dev = closes.rolling(window=self.lookback_period).std()
        upper_band = sma + self.volatility_multiplier * std_dev
        lower_band = sma - self.volatility_multiplier * std_dev
        band_width = upper_band - lower_band

        logger.info(f"[{self.symbol}] Generating signals for {len(candles)} candles...")

        for i in range(self.lookback_period, len(candles)):
            current_close = candles['close'].iloc[i]
            prev_close = candles['close'].iloc[i-1]
            current_upper = upper_band.iloc[i]
            current_lower = lower_band.iloc[i]
            current_sma = sma.iloc[i]
            current_width = band_width.iloc[i]

            # --- Entry Logic ---
            if backtest_position == 0:
                # Breakout Long Entry
                if current_close > current_upper and prev_close <= upper_band.iloc[i-1]:
                    signals.iloc[i] = 1
                    backtest_position = 1
                    backtest_entry_price = current_close
                    logger.debug(f"[{self.symbol}] Backtest Signal: Long Entry at {current_close:.2f} on {candles.index[i]}")
                # Breakdown Short Entry
                elif current_close < current_lower and prev_close >= lower_band.iloc[i-1]:
                    signals.iloc[i] = -1
                    backtest_position = -1
                    backtest_entry_price = current_close
                    logger.debug(f"[{self.symbol}] Backtest Signal: Short Entry at {current_close:.2f} on {candles.index[i]}")

            # --- Exit Logic ---
            elif backtest_position == 1: # Currently Long
                # Take Profit
                if self.take_profit and current_close >= backtest_entry_price * (1 + self.take_profit):
                    signals.iloc[i] = -1 # Signal to close long
                    logger.debug(f"[{self.symbol}] Backtest Signal: Long Take Profit at {current_close:.2f} on {candles.index[i]}")
                    backtest_position = 0
                    backtest_entry_price = None
                # Stop Loss
                elif self.stop_loss and current_close <= backtest_entry_price * (1 - self.stop_loss):
                    signals.iloc[i] = -1 # Signal to close long
                    logger.debug(f"[{self.symbol}] Backtest Signal: Long Stop Loss at {current_close:.2f} on {candles.index[i]}")
                    backtest_position = 0
                    backtest_entry_price = None
                # Mean Reversion Exit (Reset)
                elif current_close < current_sma - (current_width * self.reset_threshold * 0.5): # Below mid-point adjusted by threshold
                    signals.iloc[i] = -1 # Signal to close long
                    logger.debug(f"[{self.symbol}] Backtest Signal: Long Mean Reversion Exit at {current_close:.2f} on {candles.index[i]}")
                    backtest_position = 0
                    backtest_entry_price = None

            elif backtest_position == -1: # Currently Short
                # Take Profit
                if self.take_profit and current_close <= backtest_entry_price * (1 - self.take_profit):
                    signals.iloc[i] = 1 # Signal to close short
                    logger.debug(f"[{self.symbol}] Backtest Signal: Short Take Profit at {current_close:.2f} on {candles.index[i]}")
                    backtest_position = 0
                    backtest_entry_price = None
                # Stop Loss
                elif self.stop_loss and current_close >= backtest_entry_price * (1 + self.stop_loss):
                    signals.iloc[i] = 1 # Signal to close short
                    logger.debug(f"[{self.symbol}] Backtest Signal: Short Stop Loss at {current_close:.2f} on {candles.index[i]}")
                    backtest_position = 0
                    backtest_entry_price = None
                # Mean Reversion Exit (Reset)
                elif current_close > current_sma + (current_width * self.reset_threshold * 0.5): # Above mid-point adjusted by threshold
                    signals.iloc[i] = 1 # Signal to close short
                    logger.debug(f"[{self.symbol}] Backtest Signal: Short Mean Reversion Exit at {current_close:.2f} on {candles.index[i]}")
                    backtest_position = 0
                    backtest_entry_price = None

        logger.info(f"[{self.symbol}] Signal generation complete. Found {sum(signals != 0)} potential trade signals.")
        return signals

    async def process_realtime_data(self, data_point: dict) -> None:
        """Processes a single real-time data point (e.g., from WebSocket)."""
        # Validate data_point structure if necessary
        required_keys = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(key in data_point for key in required_keys):
            logger.warning(f"[{self.symbol}] Received incomplete data point: {data_point}. Skipping.")
            return

        logger.debug(f"[{self.symbol}] Processing data point: Time={data_point['timestamp']}, Close={data_point['close']}")

        # Append new data
        # Convert timestamp if it's not already in a compatible format (e.g., pd.Timestamp)
        try:
            # Assuming timestamp is milliseconds epoch
            ts = pd.to_datetime(data_point['timestamp'], unit='ms')
        except Exception as e:
            logger.error(f"[{self.symbol}] Error converting timestamp {data_point['timestamp']}: {e}")
            return

        new_row = pd.DataFrame([data_point])
        new_row['timestamp'] = ts
        new_row = new_row.set_index('timestamp')

        # Use concat instead of append
        self.data_buffer = pd.concat([self.data_buffer, new_row[required_keys]], ignore_index=False)

        # Keep buffer size manageable (optional, depends on memory constraints)
        # if len(self.data_buffer) > self.lookback_period * 5: # Example: keep 5x lookback
        #     self.data_buffer = self.data_buffer.iloc[-(self.lookback_period * 5):]

        # Calculate Bands
        sma, upper_band, lower_band = self._calculate_bands()

        if sma is None:
            logger.debug(f"[{self.symbol}] Not enough data yet ({len(self.data_buffer)}/{self.lookback_period}) to calculate bands.")
            return

        current_close = data_point['close']
        band_width = upper_band - lower_band
        logger.debug(f"[{self.symbol}] Bands calculated: Lower={lower_band:.2f}, SMA={sma:.2f}, Upper={upper_band:.2f}")

        # --- Trading Logic ---
        try:
            # --- Exit Logic (Check before Entry) ---
            # Use inherited position_size with tolerance
            if self.position_size > 1e-9: # Currently Long
                # Take Profit
                # Use inherited average_entry_price
                if self.take_profit and current_close >= self.average_entry_price * (1 + self.take_profit):
                    logger.info(f"[{self.symbol}] Long Take Profit triggered at {current_close:.2f} (Entry: {self.average_entry_price:.2f})")
                    await self._place_exit_order('sell')
                # Stop Loss
                # Use inherited average_entry_price
                elif self.stop_loss and current_close <= self.average_entry_price * (1 - self.stop_loss):
                    logger.info(f"[{self.symbol}] Long Stop Loss triggered at {current_close:.2f} (Entry: {self.average_entry_price:.2f})")
                    await self._place_exit_order('sell')
                # Mean Reversion Exit
                elif current_close < sma - (band_width * self.reset_threshold * 0.5):
                    logger.info(f"[{self.symbol}] Long Mean Reversion Exit triggered at {current_close:.2f} (SMA: {sma:.2f})")
                    await self._place_exit_order('sell')

            # Use inherited position_size with tolerance
            elif self.position_size < -1e-9: # Currently Short
                # Take Profit
                # Use inherited average_entry_price
                if self.take_profit and current_close <= self.average_entry_price * (1 - self.take_profit):
                    logger.info(f"[{self.symbol}] Short Take Profit triggered at {current_close:.2f} (Entry: {self.average_entry_price:.2f})")
                    await self._place_exit_order('buy')
                # Stop Loss
                # Use inherited average_entry_price
                elif self.stop_loss and current_close >= self.average_entry_price * (1 + self.stop_loss):
                    logger.info(f"[{self.symbol}] Short Stop Loss triggered at {current_close:.2f} (Entry: {self.average_entry_price:.2f})")
                    await self._place_exit_order('buy')
                # Mean Reversion Exit
                elif current_close > sma + (band_width * self.reset_threshold * 0.5):
                    logger.info(f"[{self.symbol}] Short Mean Reversion Exit triggered at {current_close:.2f} (SMA: {sma:.2f})")
                    await self._place_exit_order('buy')

            # --- Entry Logic (Only if flat) ---
            # Check if position is effectively flat using tolerance and inherited position_size
            elif abs(self.position_size) < 1e-9:
                # Breakout Long Entry
                # Check previous close if available
                prev_close = self.data_buffer['close'].iloc[-2] if len(self.data_buffer) > 1 else None
                prev_upper = self.data_buffer['upper_band'].iloc[-2] if 'upper_band' in self.data_buffer.columns and len(self.data_buffer) > 1 else None # Need to store bands in buffer for this

                # Simplified check: just current close vs current band
                if current_close > upper_band: # Add prev_close check if needed
                    logger.info(f"[{self.symbol}] Long Breakout triggered at {current_close:.2f} (Upper Band: {upper_band:.2f})")
                    await self._place_entry_order('buy', current_close)

                # Breakdown Short Entry
                elif current_close < lower_band: # Add prev_close check if needed
                    logger.info(f"[{self.symbol}] Short Breakdown triggered at {current_close:.2f} (Lower Band: {lower_band:.2f})")
                    await self._place_entry_order('sell', current_close)
                else:
                    logger.debug(f"[{self.symbol}] No entry signal. Close={current_close:.2f} within bands [{lower_band:.2f}, {upper_band:.2f}]")

        except Exception as e:
            logger.error(f"[{self.symbol}] Error during real-time processing logic: {e}", exc_info=True)
            # Decide how to handle errors - e.g., reset position state?
            # self.position = 0
            # self.entry_price = None

    async def _place_entry_order(self, side: str, current_price: float): # Renamed arg for clarity
        """Places an entry order and updates strategy state."""
        # Use inherited position_size with tolerance
        if abs(self.position_size) > 1e-9:
            logger.warning(f"[{self.symbol}] Attempted to enter {side} while already in position {self.position_size}. Ignoring.")
            return

        amount_to_trade = await self._calculate_position_size(current_price)
        if amount_to_trade <= 0:
            logger.warning(f"[{self.symbol}] Calculated position size {amount_to_trade} is zero or negative. Cannot place {side} entry order.")
            return

        logger.info(f"[{self.symbol}] Attempting to place {side} entry order for {amount_to_trade} at market price (ref: {current_price:.2f})")
        try:
            order = await self.exchange.place_order(
                symbol=self.symbol,
                order_type='market', # Use market orders for simplicity in real-time
                side=side,
                amount=amount_to_trade
            )
            # IMPORTANT: Need to handle order fills properly.
            # This mock logic assumes immediate fill and updates state directly.
            # In a real system, we should wait for fill confirmation (e.g., via WebSocket or polling)
            # and then call self._update_position_from_fill(fill_details).
            # For now, we simulate the state update based on the order request.
            if order and order.get('status') in ['filled', 'closed']: # Adjust based on actual return
                # Simulate fill details for the update method
                simulated_fill = {
                    'side': side,
                    'amount': amount_to_trade,
                    'price': order.get('average') or order.get('price') or current_price # Use best available price
                }
                self._update_position_from_fill(simulated_fill)
                logger.info(f"[{self.symbol}] Entry order {order.get('id')} likely filled. Updated internal state: Size={self.position_size:.8f}, AvgEntry={self.average_entry_price:.2f}")
            elif order:
                logger.warning(f"[{self.symbol}] Entry order {order.get('id')} placed but status is {order.get('status')}. Position not updated yet.")
                # Need logic to track open orders and update position on fill
            else:
                 logger.error(f"[{self.symbol}] Entry order placement failed or returned unexpected result: {order}")

        except Exception as e:
            logger.error(f"[{self.symbol}] Error placing {side} entry order: {e}", exc_info=True)
            # Consider if state should be reset on error
            pass # No state reset for now

    async def _place_exit_order(self, side: str):
        """Places an exit order (closes the entire position) and resets strategy state upon confirmation."""
        """Places an exit order and resets strategy state."""
        # Use inherited position_size with tolerance
        if abs(self.position_size) < 1e-9:
            logger.warning(f"[{self.symbol}] Attempted to place {side} exit order while flat. Ignoring.")
            return

        # Use the internally tracked position size
        amount_to_close = abs(self.position_size)

        if amount_to_close < 1e-9: # Use tolerance
            logger.error(f"[{self.symbol}] Cannot place exit order. Internal position size is {self.position_size}. Fetching from exchange as fallback.")
            # Fallback: Try fetching from exchange if internal state seems wrong
            try:
                current_position_info = await self.exchange.get_position(self.symbol)
                amount_to_close = abs(current_position_info.get('amount', 0.0))
                if amount_to_close < 1e-9:
                    logger.error(f"[{self.symbol}] Exchange also reports zero position. Cannot place exit order.")
                    return
                else:
                    logger.warning(f"[{self.symbol}] Using position size from exchange ({amount_to_close}) for exit order.")
            except Exception as e:
                logger.error(f"[{self.symbol}] Failed to fetch position from exchange during exit attempt: {e}")
                return

        if amount_to_close <= 0:
            logger.error(f"[{self.symbol}] Calculated amount to close is zero or negative. Cannot place {side} exit order.")
            return

        logger.info(f"[{self.symbol}] Attempting to place {side} exit order for {amount_to_close} at market price.")
        try:
            order = await self.exchange.place_order(
                symbol=self.symbol,
                order_type='market',
                side=side,
                amount=amount_to_close
            )
            # IMPORTANT: Similar to entry, proper fill handling is needed.
            # Assuming fill and updating state directly for now.
            if order and order.get('status') in ['filled', 'closed']:
                # Simulate fill details for the update method
                simulated_fill = {
                    'side': side,
                    'amount': amount_to_close,
                    'price': order.get('average') or order.get('price') or 0 # Price less critical for closing fill update
                }
                self._update_position_from_fill(simulated_fill)
                logger.info(f"[{self.symbol}] Exit order {order.get('id')} likely filled. Updated internal state: Size={self.position_size:.8f}, AvgEntry={self.average_entry_price:.2f}")
                # Double-check state after update (should be close to zero)
                if abs(self.position_size) > 1e-9:
                    logger.warning(f"[{self.symbol}] Position size is {self.position_size} after exit fill update. Expected near zero.")
            elif order:
                 logger.warning(f"[{self.symbol}] Exit order {order.get('id')} placed but status is {order.get('status')}. Position not reset yet.")
                 # Need logic to track exit orders
            else:
                 logger.error(f"[{self.symbol}] Exit order placement failed or returned unexpected result: {order}")

        except Exception as e:
            logger.error(f"[{self.symbol}] Error placing {side} exit order: {e}", exc_info=True)
            # Consider if state should be reset on error
            pass # No state reset for now

    async def _calculate_position_size(self, current_price: float) -> float:
        """Calculates the position size based on available capital and risk percentage."""
        try:
            # Assumes USDT is the quote currency
            balance_info = await self.exchange.get_balance('USDT')
            available_capital = balance_info.get('USDT', {}).get('free', 0.0) # Use free balance

            if available_capital <= 0:
                logger.warning(f"[{self.symbol}] No available capital (USDT) to calculate position size.")
                return 0.0

            position_value = available_capital * self.position_size_pct
            amount = position_value / current_price

            # TODO: Add exchange-specific minimum order size checks and precision adjustments
            logger.debug(f"[{self.symbol}] Calculated position size: {amount:.8f} based on capital {available_capital:.2f} USDT and price {current_price:.2f}")
            return amount
        except Exception as e:
            logger.error(f"[{self.symbol}] Error calculating position size: {e}", exc_info=True)
            return 0.0
