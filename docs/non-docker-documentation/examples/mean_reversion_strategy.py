"""
Mean Reversion Strategy Example

This is an example of a mean reversion strategy implementation for Cryptobot.
The strategy buys when the price is below the lower Bollinger Band and sells
when the price returns to the middle band or touches the upper band.
"""

from cryptobot.strategies import BaseStrategy
from cryptobot.indicators import BollingerBands, RSI
from cryptobot.enums import OrderType, OrderSide, PositionSide


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy using Bollinger Bands and RSI.
    
    This strategy:
    - Buys when price touches the lower Bollinger Band and RSI is below oversold threshold
    - Sells when price returns to the middle band or touches the upper band
    - Uses RSI as a confirmation indicator
    - Implements dynamic position sizing based on distance from the mean
    """
    
    def __init__(self, config):
        """
        Initialize the strategy with configuration parameters.
        
        Args:
            config (dict): Strategy configuration parameters
        """
        super().__init__(config)
        
        # Extract strategy parameters from config
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std_dev = self.params.get('bb_std_dev', 2.0)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)
        self.risk_per_trade = self.params.get('risk_per_trade', 0.01)  # 1% risk per trade
        self.take_profit = self.params.get('take_profit', 0.05)  # 5% take profit
        self.stop_loss = self.params.get('stop_loss', 0.02)  # 2% stop loss
        
        # Initialize indicators
        self.bollinger = BollingerBands(self.bb_period, self.bb_std_dev)
        self.rsi = RSI(self.rsi_period)
        
        # Initialize strategy state
        self.last_upper_band = None
        self.last_middle_band = None
        self.last_lower_band = None
        self.last_rsi = None
        
        self.logger.info(f"Initialized Mean Reversion Strategy with parameters: "
                         f"BB Period={self.bb_period}, BB StdDev={self.bb_std_dev}, "
                         f"RSI Period={self.rsi_period}, RSI Oversold={self.rsi_oversold}, "
                         f"RSI Overbought={self.rsi_overbought}")
    
    def analyze(self, candle):
        """
        Analyze the current market data and generate trading signals.
        
        Args:
            candle (Candle): The current price candle
        """
        # Update indicators with new data
        upper_band, middle_band, lower_band = self.bollinger.update(candle.close)
        rsi_value = self.rsi.update(candle.close)
        
        # Store indicator values for logging and analysis
        self.last_upper_band = upper_band
        self.last_middle_band = middle_band
        self.last_lower_band = lower_band
        self.last_rsi = rsi_value
        
        # Log indicator values for debugging
        self.logger.debug(f"Price={candle.close}, Upper Band={upper_band}, "
                          f"Middle Band={middle_band}, Lower Band={lower_band}, RSI={rsi_value}")
        
        # Check if we have an open position
        if self.has_position():
            self._handle_exit_signals(candle)
        else:
            self._handle_entry_signals(candle)
    
    def _handle_entry_signals(self, candle):
        """
        Handle entry signals when we don't have an open position.
        
        Args:
            candle (Candle): The current price candle
        """
        # Check for buy signal: price below lower band and RSI oversold
        if (candle.close <= self.last_lower_band and 
                self.last_rsi <= self.rsi_oversold):
            
            # Calculate position size based on risk
            position_size = self._calculate_position_size(candle.close)
            
            # Log entry signal
            self.logger.info(f"BUY SIGNAL: Price={candle.close} below Lower Band={self.last_lower_band}, "
                             f"RSI={self.last_rsi} below oversold threshold={self.rsi_oversold}")
            
            # Execute buy order
            self.buy(
                order_type=OrderType.MARKET,
                quantity=position_size,
                stop_loss_price=candle.close * (1 - self.stop_loss),
                take_profit_price=candle.close * (1 + self.take_profit)
            )
    
    def _handle_exit_signals(self, candle):
        """
        Handle exit signals when we have an open position.
        
        Args:
            candle (Candle): The current price candle
        """
        # Get current position
        position = self.get_position()
        
        # Check for sell signals
        if position.side == PositionSide.LONG:
            # Sell if price returns to middle band
            if candle.close >= self.last_middle_band:
                self.logger.info(f"SELL SIGNAL (Middle Band): Price={candle.close} reached "
                                 f"Middle Band={self.last_middle_band}")
                self.sell(OrderType.MARKET, position.quantity)
            
            # Sell if RSI becomes overbought
            elif self.last_rsi >= self.rsi_overbought:
                self.logger.info(f"SELL SIGNAL (Overbought): RSI={self.last_rsi} above "
                                 f"overbought threshold={self.rsi_overbought}")
                self.sell(OrderType.MARKET, position.quantity)
    
    def _calculate_position_size(self, price):
        """
        Calculate position size based on risk per trade.
        
        Args:
            price (float): Current price
            
        Returns:
            float: Position size in base currency
        """
        # Get account balance
        account_balance = self.get_balance()
        
        # Calculate risk amount in quote currency
        risk_amount = account_balance * self.risk_per_trade
        
        # Calculate stop loss distance
        stop_loss_distance = price * self.stop_loss
        
        # Calculate position size: risk amount / stop loss distance
        if stop_loss_distance > 0:
            position_size = risk_amount / stop_loss_distance
        else:
            position_size = 0
            self.logger.warning("Stop loss distance is zero or negative, setting position size to zero")
        
        # Convert to base currency
        position_size_base = position_size / price
        
        # Log position sizing calculation
        self.logger.debug(f"Position Size Calculation: Account Balance={account_balance}, "
                          f"Risk Amount={risk_amount}, Stop Loss Distance={stop_loss_distance}, "
                          f"Position Size (Quote)={position_size}, Position Size (Base)={position_size_base}")
        
        return position_size_base
    
    def on_order_filled(self, order):
        """
        Handle order filled events.
        
        Args:
            order (Order): The filled order
        """
        self.logger.info(f"Order filled: {order.id}, Side: {order.side}, "
                         f"Quantity: {order.filled_quantity}, Price: {order.average_fill_price}")
    
    def on_stop_loss_triggered(self, order):
        """
        Handle stop loss triggered events.
        
        Args:
            order (Order): The stop loss order
        """
        self.logger.warning(f"Stop loss triggered: {order.id}, "
                            f"Quantity: {order.filled_quantity}, Price: {order.average_fill_price}")
        
        # Implement additional risk management if needed
        # For example, reduce position size for next trade
    
    def on_take_profit_triggered(self, order):
        """
        Handle take profit triggered events.
        
        Args:
            order (Order): The take profit order
        """
        self.logger.info(f"Take profit triggered: {order.id}, "
                         f"Quantity: {order.filled_quantity}, Price: {order.average_fill_price}")
    
    def on_strategy_start(self):
        """Handle strategy start event."""
        self.logger.info("Mean Reversion Strategy started")
    
    def on_strategy_stop(self):
        """Handle strategy stop event."""
        self.logger.info("Mean Reversion Strategy stopped")
        
        # Close any open positions when strategy stops
        if self.has_position():
            position = self.get_position()
            self.logger.info(f"Closing position on strategy stop: {position.quantity} @ market price")
            self.sell(OrderType.MARKET, position.quantity)


# Register the strategy with Cryptobot
def register():
    """Register the strategy with the system."""
    return {
        "name": "Mean Reversion",
        "description": "A mean reversion strategy using Bollinger Bands and RSI",
        "class": MeanReversionStrategy,
        "default_params": {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "risk_per_trade": 0.01,
            "take_profit": 0.05,
            "stop_loss": 0.02
        }
    }