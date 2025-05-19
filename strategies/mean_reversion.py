import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy

    This strategy identifies when price deviates significantly from its mean (based on z-score)
    and enters trades expecting price to revert to the mean. Exits occur when price returns
    to the mean or hits profit/stop targets.

    Parameters:
    -----------
    lookback_period : int (5-200)
        Number of periods used to calculate mean and standard deviation.
        Example: 20 (default) uses last 20 periods for calculations.

    entry_z_score : float (1.0-3.0)
        Z-score threshold for entering trades. Higher values require larger deviations.
        Example: 2.0 (default) means enter when price is 2 standard deviations from mean.

    exit_z_score : float (0.1-1.5)
        Z-score threshold for exiting trades. Lower values exit closer to the mean.
        Example: 0.5 (default) means exit when price is 0.5 standard deviations from mean.

    take_profit : float (0.001-1.0)
        Profit target as percentage of entry price (0.1 = 10%).
        Example: 0.03 (default) means 3% take profit target.

    stop_loss : float (0.001-1.0)
        Stop loss as percentage of entry price (0.1 = 10%).
        Example: 0.02 (default) means 2% stop loss.

    Usage Example:
    -------------
    strategy = MeanReversionStrategy(
        lookback_period=20,
        entry_z_score=2.0,
        exit_z_score=0.5,
        take_profit=0.03,
        stop_loss=0.02
    )
    """

    @staticmethod
    def validate_parameters(params: Dict[str, Any]) -> None:
        """Validate strategy parameters"""
        param_definitions = {
            'lookback_period': (int, 5, 200),
            'entry_z_score': (float, 1.0, 3.0),
            'exit_z_score': (float, 0.1, 1.5),
            'take_profit': (float, 0.001, 1.0),
            'stop_loss': (float, 0.001, 1.0)
        }

        # First check all required parameters are present
        required_params = ['lookback_period', 'entry_z_score']
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")

        # Then validate parameters that were provided
        for param, value in params.items():
            if param not in param_definitions:
                raise ValueError(f"Unknown parameter: {param}")

            # Skip None values (optional parameters)
            if value is None:
                continue

            param_type, min_val, max_val = param_definitions[param]

            if not isinstance(value, param_type):
                raise ValueError(f"Parameter {param} must be {param_type.__name__}")

            if not min_val <= value <= max_val:
                raise ValueError(f"Parameter {param} must be between {min_val} and {max_val}")

    def __init__(self, lookback_period=None, entry_z_score=None,
                 exit_z_score=None, take_profit=0.03, stop_loss=0.02, risk_per_trade_pct=None, max_drawdown_pct=None, volatility_multiplier=None, position_size_pct=0.1, exchange_interface=None, **kwargs):
        super().__init__(exchange_interface=exchange_interface, lookback_period=lookback_period, entry_z_score=entry_z_score, exit_z_score=exit_z_score, take_profit=take_profit, stop_loss=stop_loss, risk_per_trade_pct=risk_per_trade_pct, max_drawdown_pct=max_drawdown_pct, volatility_multiplier=volatility_multiplier, position_size_pct=position_size_pct, **kwargs)
        self.logger = logger
        self.lookback_period = lookback_period
        self.entry_z_score = entry_z_score
        self.exit_z_score = exit_z_score
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.volatility_multiplier = volatility_multiplier
        self.position_size_pct = position_size_pct
        self._initialized = False

    def calculate_z_scores(self, data):
        """Calculate z-scores for price relative to rolling mean"""
        data['mean'] = data['close'].rolling(window=self.lookback_period, min_periods=self.lookback_period).mean()
        data['std_dev'] = data['close'].rolling(window=self.lookback_period, min_periods=self.lookback_period).std()
        # Round to handle floating point precision issues
        data['std_dev'] = data['std_dev'].round(10)
        data['z_score'] = (data['close'] - data['mean']) / data['std_dev'].replace(0, np.nan)
        return data

    def generate_signals(self, data):
        """Generate trading signals based on mean reversion strategy"""
        if data.empty:
            raise ValueError("Data cannot be empty")
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.position_size = 0.0
            self.average_entry_price = 0.0
        if 'close' not in data.columns:
            raise ValueError("Data must contain 'close' column")
        if len(data) < self.lookback_period:
            raise ValueError(f"Insufficient data - need at least {self.lookback_period} periods")
        self.data = self.calculate_z_scores(data)
        self.data['signal'] = 0
        self.data['position'] = 0
        if 'entry_price' not in self.data.columns:
            self.data['entry_price'] = np.nan
        if 'exit_price' not in self.data.columns:
            self.data['exit_price'] = np.nan
        if 'trade_profit' not in self.data.columns:
            self.data['trade_profit'] = 0.0
        if 'cumulative_profit' not in self.data.columns:
            self.data['cumulative_profit'] = 0.0
        for i in range(self.lookback_period, len(self.data)):
            current_price = self.data.iloc[i]['close']
            current_z = self.data.iloc[i]['z_score']
            # If no position is open
            if abs(self.position_size) < 1e-9:
                if current_z < -self.entry_z_score:
                    fill = {'side': 'buy', 'amount': 1.0, 'price': current_price}
                    self._update_position_from_fill(fill)
                    self.data.loc[self.data.index[i], 'signal'] = 1
                    self.data.loc[self.data.index[i], 'position'] = 1
                    self.data.loc[self.data.index[i], 'entry_price'] = current_price
                    self.logger.debug(f"New long entry at price {current_price:.2f}, z={current_z:.2f}")
                elif current_z > self.entry_z_score:
                    fill = {'side': 'sell', 'amount': 1.0, 'price': current_price}
                    self._update_position_from_fill(fill)
                    self.data.loc[self.data.index[i], 'signal'] = -1
                    self.data.loc[self.data.index[i], 'position'] = -1
                    self.data.loc[self.data.index[i], 'entry_price'] = current_price
                    self.logger.info(f"New short entry at price {current_price:.2f}, z={current_z:.2f}")
            else:
                self.data.loc[self.data.index[i], 'position'] = 1 if self.position_size > 0 else -1
                self.data.loc[self.data.index[i], 'entry_price'] = self.average_entry_price
                self.data.loc[self.data.index[i], 'signal'] = 0
                if self.position_size > 0:
                    current_profit = (current_price - self.average_entry_price) / self.average_entry_price
                else:
                    current_profit = (self.average_entry_price - current_price) / self.average_entry_price
                self.data.loc[self.data.index[i], 'trade_profit'] = current_profit
                exit_condition = False
                if ((self.position_size > 0 and current_profit >= self.take_profit) or
                    (self.position_size < 0 and current_profit <= -self.take_profit)):
                    exit_side = 'sell' if self.position_size > 0 else 'buy'
                    fill = {'side': exit_side, 'amount': abs(self.position_size), 'price': current_price}
                    self._update_position_from_fill(fill)
                    self.data.loc[self.data.index[i], 'signal'] = 0
                    self.data.loc[self.data.index[i], 'position'] = 0
                    self.data.loc[self.data.index[i], 'exit_price'] = current_price
                    self.logger.info(f"Take profit condition met: {current_profit:.2%}")
                    continue
                elif abs(current_profit + self.stop_loss) < 1e-6 or current_profit < -self.stop_loss:
                    exit_side = 'sell' if self.position_size > 0 else 'buy'
                    fill = {'side': exit_side, 'amount': abs(self.position_size), 'price': current_price}
                    self._update_position_from_fill(fill)
                    self.data.loc[self.data.index[i], 'signal'] = 0
                    self.data.loc[self.data.index[i], 'position'] = 0
                    self.data.loc[self.data.index[i], 'exit_price'] = current_price
                    self.logger.info(f"Stop loss condition met: {current_profit:.2%}")
                    continue
                elif ((self.position_size > 0 and current_z >= -self.exit_z_score) or
                      (self.position_size < 0 and current_z <= self.exit_z_score)) and abs(current_profit) < (abs(self.take_profit) * 0.5):
                    exit_side = 'sell' if self.position_size > 0 else 'buy'
                    fill = {'side': exit_side, 'amount': abs(self.position_size), 'price': current_price}
                    self._update_position_from_fill(fill)
                    self.data.loc[self.data.index[i], 'signal'] = 0
                    self.data.loc[self.data.index[i], 'position'] = 0
                    self.data.loc[self.data.index[i], 'exit_price'] = current_price
                    self.logger.info(f"Z-score exit condition met: {abs(current_z):.2f} <= {self.exit_z_score:.2f}")
        self.data['cumulative_profit'] = self.data['trade_profit'].cumsum()
        return self.data

    async def process_realtime_data(self, data_point: dict) -> Optional[str]:
        """
        Processes a single real-time data point and generates a trading signal.

        Args:
            data_point: A dictionary containing the latest market data
                        (e.g., {'timestamp': ..., 'open': ..., 'high': ...,
                                'low': ..., 'close': ..., 'volume': ...}).

        Returns:
            A string signal ("BUY", "SELL") or None if no action is warranted.
        """
        self._update_buffer(data_point)

        if len(self.data_buffer) < self.lookback_period:
            self.logger.debug(f"Data buffer size {len(self.data_buffer)} insufficient, need {self.lookback_period}")
            return None

        # Extract close prices from the buffer for z-score calculation
        # The buffer stores dictionaries, so we need to get the 'close' price from each
        close_prices = pd.Series([dp['close'] for dp in self.data_buffer])

        if len(close_prices) < self.lookback_period:
             # This check is technically redundant due to the earlier buffer check,
             # but good for safety if buffer logic changes.
            return None

        # Calculate rolling mean and standard deviation for the current buffer
        rolling_mean = close_prices.rolling(window=self.lookback_period, min_periods=self.lookback_period).mean().iloc[-1]
        rolling_std = close_prices.rolling(window=self.lookback_period, min_periods=self.lookback_period).std().iloc[-1]

        if pd.isna(rolling_mean) or pd.isna(rolling_std) or rolling_std == 0:
            self.logger.warning(f"Could not calculate rolling mean/std. Mean: {rolling_mean}, Std: {rolling_std}. Buffer size: {len(self.data_buffer)}")
            return None

        current_close_price = close_prices.iloc[-1]
        current_z_score = (current_close_price - rolling_mean) / rolling_std
        
        self.logger.debug(f"Realtime data: Price={current_close_price:.2f}, Z-Score={current_z_score:.2f}, PosSize={self.position_size}")

        # Signal Logic
        if self.position_size == 0:  # No open position
            if current_z_score < -self.entry_z_score:
                self.logger.info(f"REALTIME SIGNAL: BUY triggered. Z-score: {current_z_score:.2f} < {-self.entry_z_score:.2f}")
                return "BUY"
            elif current_z_score > self.entry_z_score:
                self.logger.info(f"REALTIME SIGNAL: SELL triggered. Z-score: {current_z_score:.2f} > {self.entry_z_score:.2f}")
                return "SELL"
        elif self.position_size > 0:  # Long position is open
            if current_z_score >= -self.exit_z_score: # Exit long condition (price moved up towards/above mean)
                self.logger.info(f"REALTIME SIGNAL: SELL (Exit Long) triggered. Z-score: {current_z_score:.2f} >= {-self.exit_z_score:.2f}")
                return "SELL"
        elif self.position_size < 0:  # Short position is open
            if current_z_score <= self.exit_z_score: # Exit short condition (price moved down towards/below mean)
                self.logger.info(f"REALTIME SIGNAL: BUY (Exit Short) triggered. Z-score: {current_z_score:.2f} <= {self.exit_z_score:.2f}")
                return "BUY"

        return None

    def get_parameters(self):
        """Return the strategy parameters as a dictionary"""
        return self.params