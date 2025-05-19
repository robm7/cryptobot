import pandas as pd
import numpy as np
import logging
import time
import json
from datetime import datetime, timedelta
from math import sqrt
from utils.exchange_clients import get_exchange_client
from utils.performance_metrics import calculate_risk_metrics

logger = logging.getLogger(__name__)

class Backtester:
    """
    Backtesting utility for trading strategies

    This class runs backtests for trading strategies on historical data.
    """

    def __init__(self, strategy, symbol, timeframe, start_date, end_date,
                 initial_capital=10000, position_size_pct=0.1, max_slippage_pct=0.1,
                 risk_per_trade_pct=None, max_drawdown_pct=None, volatility_multiplier=None):
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.max_slippage_pct = max_slippage_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.volatility_multiplier = volatility_multiplier
        self.data = None

    def fetch_data(self):
        """Fetch OHLCV data from exchange"""
        exchange = get_exchange_client()
        since = int(self.start_date.timestamp() * 1000)
        until = int(self.end_date.timestamp() * 1000)
        
        all_ohlcv = []
        current_since = since
        
        # Fetch data in chunks with retries
        max_retries = 3
        retry_delay = 5  # seconds
        
        while current_since < until:
            retries = 0
            while retries < max_retries:
                try:
                    ohlcv = exchange.fetch_ohlcv(
                        self.symbol,
                        self.timeframe,
                        since=current_since,
                        limit=1000
                    )
                    
                    if not ohlcv:
                        break
                        
                    all_ohlcv.extend(ohlcv)
                    current_since = ohlcv[-1][0] + 1  # Next ms after last candle
                    break
                    
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Failed to fetch data after {max_retries} attempts: {str(e)}")
                        raise
                    logger.warning(f"Retry {retries}/{max_retries} after error: {str(e)}")
                    time.sleep(retry_delay)

        # Convert to DataFrame
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('date', inplace=True)
        return df

    def run(self):
        """Run the backtest (API-compatible interface)"""
        return self.run_backtest()

    def run_backtest(self):
        """Run the backtest and return performance metrics"""
        if self.data is None:
            self.data = self.fetch_data()
            
        if self.data.empty:
            raise ValueError("No data available")
            
        # Apply strategy
        data = self.strategy.generate_signals(self.data.copy())

        initial_capital = self.initial_capital
        transaction_fee_pct = 0.001 # Consider making this configurable
        # Use instance attributes for risk/sizing parameters
        position_size_pct = self.position_size_pct 
        risk_per_trade_pct = self.risk_per_trade_pct
        max_drawdown_pct = self.max_drawdown_pct
        volatility_multiplier = self.volatility_multiplier # Keep this if used for dynamic sizing

        # --- Position Sizing Logic --- 
        # Initialize position size series based on base percentage
        position_size_series = pd.Series(index=data.index, data=0.0)
        active_trade_mask = (data['signal'] != 0)
        position_size_series[active_trade_mask] = position_size_pct

        # Dynamic position sizing based on volatility (if enabled)
        if volatility_multiplier is not None:
            # Ensure required columns exist for ATR calculation if needed
            if 'high' not in data.columns or 'low' not in data.columns or 'close' not in data.columns:
                 raise ValueError("OHLC data required for volatility-based sizing")
            rolling_vol = data['close'].pct_change().rolling(window=20).std()
            inv_vol = 1 / (rolling_vol + 1e-8) # Add epsilon to avoid division by zero
            norm_inv_vol = inv_vol / inv_vol.max() # Normalize
            # Apply volatility adjustment only where a signal exists
            position_size_series[active_trade_mask] *= norm_inv_vol[active_trade_mask]

        # Risk per trade sizing (if enabled)
        if risk_per_trade_pct is not None:
            # Ensure required columns exist for ATR calculation
            if 'high' not in data.columns or 'low' not in data.columns or 'close' not in data.columns:
                 raise ValueError("OHLC data required for risk-per-trade sizing")
            # Calculate ATR if not present
            if 'atr' not in data.columns:
                data['tr'] = np.maximum(data['high'] - data['low'],
                                       np.abs(data['high'] - data['close'].shift()),
                                       np.abs(data['low'] - data['close'].shift()))
                data['atr'] = data['tr'].rolling(window=14).mean()
            
            # Calculate stop loss distance (e.g., 2 * ATR)
            stop_loss_distance = 2 * data['atr']
            # Avoid division by zero or negative stop loss
            stop_loss_distance = stop_loss_distance.replace(0, np.nan).fillna(method='ffill').fillna(1e-8) 
            
            # Calculate risk amount based on current capital (needs simulation loop)
            # This part is complex as capital changes. Simplified approach for now:
            # Calculate size based on initial capital risk. A full simulation loop is better.
            risk_amount_per_trade = initial_capital * risk_per_trade_pct 
            trade_size_based_on_risk = risk_amount_per_trade / stop_loss_distance
            
            # Apply the minimum of the calculated sizes where a signal exists
            position_size_series[active_trade_mask] = np.minimum(
                position_size_series[active_trade_mask],
                trade_size_based_on_risk[active_trade_mask] / data['close'][active_trade_mask] # Convert currency risk to asset quantity risk
            )
            # Ensure position size doesn't exceed 1 (100%)
            position_size_series = np.minimum(position_size_series, 1.0)

        # --- Backtesting Loop --- 
        cash = initial_capital
        holdings = 0.0
        portfolio_value = initial_capital
        peak_value = initial_capital
        current_drawdown = 0.0
        trades = []
        portfolio_history = []

        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data['close'].iloc[i]
            signal = data['signal'].iloc[i]
            size_pct = position_size_series.iloc[i]
            
            # Update portfolio value with current price
            portfolio_value = cash + holdings * current_price
            portfolio_history.append({'timestamp': current_date, 'value': portfolio_value, 'cash': cash, 'holdings': holdings, 'position_size': size_pct if signal != 0 else 0})

            # Update peak value and drawdown
            peak_value = max(peak_value, portfolio_value)
            current_drawdown = (portfolio_value - peak_value) / peak_value if peak_value > 0 else 0

            # Max Drawdown Control (Stop Trading if Exceeded)
            if max_drawdown_pct is not None and current_drawdown < -max_drawdown_pct:
                logger.warning(f"Max drawdown {max_drawdown_pct:.2%} exceeded at {current_date}. Stopping trades.")
                # Optionally: Close existing position
                if holdings > 0:
                    sell_price = current_price * (1 - self.max_slippage_pct)
                    proceeds = holdings * sell_price
                    fee = proceeds * transaction_fee_pct
                    cash += proceeds - fee
                    trades.append({'timestamp': current_date, 'type': 'sell', 'price': sell_price, 'amount': holdings, 'fee': fee, 'reason': 'max_drawdown'})
                    holdings = 0
                signal = 0 # Prevent further trades

            # Calculate trade size based on current portfolio value and size_pct
            target_position_value = portfolio_value * size_pct
            target_holdings = target_position_value / current_price if current_price > 0 else 0

            # Execute Trades
            if signal == 1 and cash > 0: # Buy Signal
                buy_price = current_price * (1 + self.max_slippage_pct)
                amount_to_buy = min(target_holdings - holdings, cash / buy_price) # Can't buy more than cash allows
                if amount_to_buy > 1e-8: # Minimum trade size check
                    cost = amount_to_buy * buy_price
                    fee = cost * transaction_fee_pct
                    if cash >= cost + fee:
                        cash -= (cost + fee)
                        holdings += amount_to_buy
                        trades.append({'timestamp': current_date, 'type': 'buy', 'price': buy_price, 'amount': amount_to_buy, 'fee': fee})
            elif signal == -1 and holdings > 0: # Sell Signal
                sell_price = current_price * (1 - self.max_slippage_pct)
                amount_to_sell = min(holdings - target_holdings, holdings) # Sell down to target or sell all
                if amount_to_sell > 1e-8:
                    proceeds = amount_to_sell * sell_price
                    fee = proceeds * transaction_fee_pct
                    cash += proceeds - fee
                    holdings -= amount_to_sell
                    trades.append({'timestamp': current_date, 'type': 'sell', 'price': sell_price, 'amount': amount_to_sell, 'fee': fee})

        # Final portfolio value update
        portfolio_value = cash + holdings * data['close'].iloc[-1]
        portfolio_history.append({'timestamp': data.index[-1], 'value': portfolio_value, 'cash': cash, 'holdings': holdings, 'position_size': 0})

        portfolio_df = pd.DataFrame(portfolio_history).set_index('timestamp')
        trades_df = pd.DataFrame(trades)
        if not portfolio_df.empty:
            returns = portfolio_df['value'].pct_change().fillna(0)
            risk_metrics = calculate_risk_metrics(returns) # Assumes calculate_risk_metrics exists
        else:
            returns = pd.Series(dtype=float)
            risk_metrics = { # Default metrics for no trades/data
                'sharpe_ratio': 0, 'sortino_ratio': 0, 'calmar_ratio': 0,
                'max_drawdown': 0, 'total_return': 0, 'volatility': 0,
                'win_rate': 0, 'profit_factor': 0, 'max_consecutive_wins': 0,
                'max_consecutive_losses': 0, 'avg_daily_return': 0
            }

        # Add trade count and win rate if possible from trades_df
        # This requires calculating PnL per trade, which is more involved
        risk_metrics['total_trades'] = len(trades_df) // 2 if not trades_df.empty else 0 # Approx pairs
        # risk_metrics['win_rate'] = calculate_win_rate(trades_df) # Needs implementation

        return {
            'portfolio': portfolio_df,
            'returns': returns,
            'trades': trades_df,
            'sharpe': risk_metrics.get('sharpe_ratio'),
            'sortino': risk_metrics.get('sortino_ratio'),
            'calmar': risk_metrics.get('calmar_ratio'),
            'max_drawdown': risk_metrics.get('max_drawdown'),
            'total_return': risk_metrics.get('total_return'),
            'volatility': risk_metrics.get('volatility'),
            'downside_volatility': risk_metrics.get('downside_volatility'),
            'ulcer_index': risk_metrics.get('ulcer_index'),
            'pain_index': risk_metrics.get('pain_index'),
            'pain_ratio': risk_metrics.get('pain_ratio'),
            'omega_ratio': risk_metrics.get('omega_ratio'),
            'avg_drawdown_duration': risk_metrics.get('avg_drawdown_duration'),
            'max_drawdown_duration': risk_metrics.get('max_drawdown_duration'),
            'win_rate': risk_metrics.get('win_rate'),
            'profit_factor': risk_metrics.get('profit_factor'),
            'total_trades': risk_metrics.get('total_trades'),
            'drawdown_periods': risk_metrics.get('drawdown_periods')
        }