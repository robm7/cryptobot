"""
Custom Indicator Example

This example demonstrates how to create a custom technical indicator for Cryptobot.
The indicator implements a custom RSI with adjustable smoothing and overbought/oversold levels.
"""

from cryptobot.indicators import Indicator
import numpy as np


class EnhancedRSI(Indicator):
    """
    Enhanced RSI indicator with adjustable smoothing and dynamic thresholds.
    
    This indicator extends the traditional RSI by adding:
    1. Adjustable smoothing factor
    2. Dynamic overbought/oversold thresholds based on volatility
    3. Signal line (similar to MACD) for additional confirmation
    4. Divergence detection
    """
    
    def __init__(self, period=14, smoothing=1, signal_period=9):
        """
        Initialize the Enhanced RSI indicator.
        
        Args:
            period (int): The period for calculating RSI
            smoothing (float): Smoothing factor (1 = standard RSI)
            signal_period (int): Period for the signal line
        """
        super().__init__()
        self.name = "Enhanced RSI"
        self.period = period
        self.smoothing = smoothing
        self.signal_period = signal_period
        
        # Initialize data arrays
        self.price_history = []
        self.rsi_history = []
        self.signal_line = []
        self.gains = []
        self.losses = []
        self.prev_value = None
        self.prev_rsi = None
        
        # Initialize thresholds
        self.overbought_threshold = 70
        self.oversold_threshold = 30
        
        # Initialize divergence detection
        self.price_highs = []
        self.price_lows = []
        self.rsi_highs = []
        self.rsi_lows = []
    
    def update(self, value):
        """
        Update the indicator with a new price value.
        
        Args:
            value (float): The new price value
            
        Returns:
            dict: A dictionary containing RSI, signal line, and divergence information
        """
        # Store price history
        self.price_history.append(value)
        if len(self.price_history) > self.period * 3:
            self.price_history.pop(0)
        
        # Calculate RSI
        rsi_value = self._calculate_rsi(value)
        
        # Store RSI history
        if rsi_value is not None:
            self.rsi_history.append(rsi_value)
            if len(self.rsi_history) > self.period * 3:
                self.rsi_history.pop(0)
        
        # Calculate signal line
        signal_value = None
        if len(self.rsi_history) >= self.signal_period:
            signal_value = np.mean(self.rsi_history[-self.signal_period:])
            self.signal_line.append(signal_value)
            if len(self.signal_line) > self.period * 3:
                self.signal_line.pop(0)
        
        # Update dynamic thresholds based on volatility
        if len(self.price_history) >= self.period:
            self._update_dynamic_thresholds()
        
        # Detect divergence
        divergence = self._detect_divergence()
        
        # Store previous values for next update
        self.prev_value = value
        if rsi_value is not None:
            self.prev_rsi = rsi_value
        
        # Return results
        return {
            'rsi': rsi_value,
            'signal': signal_value,
            'overbought': self.overbought_threshold,
            'oversold': self.oversold_threshold,
            'divergence': divergence
        }
    
    def _calculate_rsi(self, value):
        """
        Calculate the RSI value.
        
        Args:
            value (float): The new price value
            
        Returns:
            float: The calculated RSI value or None if not enough data
        """
        if self.prev_value is None:
            self.prev_value = value
            return None
        
        # Calculate price change
        change = value - self.prev_value
        
        # Track gains and losses
        if change > 0:
            self.gains.append(change)
            self.losses.append(0)
        else:
            self.gains.append(0)
            self.losses.append(abs(change))
        
        # Trim arrays to period length
        if len(self.gains) > self.period:
            self.gains.pop(0)
            self.losses.pop(0)
        
        # Need at least 'period' data points
        if len(self.gains) < self.period:
            return None
        
        # Calculate average gain and loss with smoothing
        avg_gain = np.mean(self.gains) * self.smoothing
        avg_loss = np.mean(self.losses) * self.smoothing
        
        # Calculate RS and RSI
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _update_dynamic_thresholds(self):
        """
        Update overbought/oversold thresholds based on market volatility.
        Higher volatility = wider thresholds
        Lower volatility = narrower thresholds
        """
        # Calculate price volatility (standard deviation)
        volatility = np.std(self.price_history[-self.period:])
        
        # Calculate volatility ratio (current volatility / average volatility)
        avg_volatility = np.mean([np.std(self.price_history[i:i+self.period]) 
                                 for i in range(0, len(self.price_history) - self.period, self.period // 2)])
        
        if avg_volatility > 0:
            volatility_ratio = volatility / avg_volatility
        else:
            volatility_ratio = 1.0
        
        # Adjust thresholds based on volatility ratio
        # Higher volatility = wider thresholds
        base_overbought = 70
        base_oversold = 30
        
        self.overbought_threshold = min(85, base_overbought + (volatility_ratio - 1) * 15)
        self.oversold_threshold = max(15, base_oversold - (volatility_ratio - 1) * 15)
    
    def _detect_divergence(self):
        """
        Detect bullish and bearish divergences between price and RSI.
        
        Returns:
            dict: Divergence information
        """
        if len(self.price_history) < self.period * 2 or len(self.rsi_history) < self.period * 2:
            return {'bullish': False, 'bearish': False}
        
        # Find local price highs and lows
        price_data = np.array(self.price_history[-self.period*2:])
        rsi_data = np.array(self.rsi_history[-self.period*2:])
        
        # Simple method to find local extrema
        # In a real implementation, you would use a more sophisticated method
        price_highs_idx = self._find_local_extrema(price_data, max_mode=True)
        price_lows_idx = self._find_local_extrema(price_data, max_mode=False)
        
        # Check for divergence
        bullish_divergence = False
        bearish_divergence = False
        
        # Bearish divergence: Price making higher highs, RSI making lower highs
        if len(price_highs_idx) >= 2:
            price_high_values = price_data[price_highs_idx]
            rsi_high_values = rsi_data[price_highs_idx]
            
            if (price_high_values[-1] > price_high_values[-2] and 
                rsi_high_values[-1] < rsi_high_values[-2]):
                bearish_divergence = True
        
        # Bullish divergence: Price making lower lows, RSI making higher lows
        if len(price_lows_idx) >= 2:
            price_low_values = price_data[price_lows_idx]
            rsi_low_values = rsi_data[price_lows_idx]
            
            if (price_low_values[-1] < price_low_values[-2] and 
                rsi_low_values[-1] > rsi_low_values[-2]):
                bullish_divergence = True
        
        return {
            'bullish': bullish_divergence,
            'bearish': bearish_divergence
        }
    
    def _find_local_extrema(self, data, max_mode=True, window=5):
        """
        Find local maxima or minima in data.
        
        Args:
            data (numpy.array): The data array
            max_mode (bool): If True, find maxima, otherwise find minima
            window (int): Window size for finding extrema
            
        Returns:
            list: Indices of local extrema
        """
        if len(data) < window * 2:
            return []
        
        indices = []
        
        for i in range(window, len(data) - window):
            if max_mode:
                # Find local maxima
                if data[i] == max(data[i-window:i+window+1]):
                    indices.append(i)
            else:
                # Find local minima
                if data[i] == min(data[i-window:i+window+1]):
                    indices.append(i)
        
        return indices


# Example usage
if __name__ == "__main__":
    # Sample price data
    prices = [
        100.0, 101.5, 103.0, 102.5, 101.0, 99.5, 100.0, 102.0, 104.0, 103.5,
        105.0, 107.5, 108.0, 107.0, 106.5, 105.0, 103.0, 101.0, 100.5, 102.0,
        103.5, 105.0, 106.0, 107.5, 109.0, 108.5, 107.0, 105.5, 106.0, 108.0
    ]
    
    # Create Enhanced RSI indicator
    enhanced_rsi = EnhancedRSI(period=14, smoothing=1.5, signal_period=9)
    
    # Process price data
    results = []
    for price in prices:
        result = enhanced_rsi.update(price)
        results.append(result)
    
    # Print results
    print("Enhanced RSI Results:")
    print("--------------------")
    for i, (price, result) in enumerate(zip(prices, results)):
        if result['rsi'] is not None:
            print(f"Day {i+1}: Price = {price:.2f}, RSI = {result['rsi']:.2f}, "
                  f"Signal = {result['signal']:.2f if result['signal'] is not None else 'N/A'}, "
                  f"Thresholds = [{result['oversold']:.2f}, {result['overbought']:.2f}], "
                  f"Divergence = {result['divergence']}")


# Register the indicator with Cryptobot
def register():
    """Register the indicator with the system."""
    return {
        "name": "Enhanced RSI",
        "description": "RSI with adjustable smoothing, dynamic thresholds, and divergence detection",
        "class": EnhancedRSI,
        "default_params": {
            "period": 14,
            "smoothing": 1.5,
            "signal_period": 9
        }
    }