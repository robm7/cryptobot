import pandas as pd
from typing import Union, List

class MACDIndicator:
    """
    Calculates the Moving Average Convergence Divergence (MACD) technical indicator.
    """

    def __init__(self, short_period: int = 12, long_period: int = 26, signal_period: int = 9):
        """
        Initializes the MACDIndicator.

        Args:
            short_period (int): The period for the short-term EMA. Default is 12.
            long_period (int): The period for the long-term EMA. Default is 26.
            signal_period (int): The period for the signal line EMA. Default is 9.
        """
        if not all(isinstance(p, int) and p > 0 for p in [short_period, long_period, signal_period]):
            raise ValueError("All periods must be positive integers.")
        if short_period >= long_period:
            raise ValueError("Short period must be less than long period.")
            
        self.short_period = short_period
        self.long_period = long_period
        self.signal_period = signal_period

    def calculate(self, prices: Union[List[float], pd.Series]) -> pd.DataFrame:
        """
        Calculates the MACD, Signal Line, and Histogram.

        Args:
            prices (Union[List[float], pd.Series]): A list or pandas Series of closing prices.

        Returns:
            pd.DataFrame: A pandas DataFrame with columns 'MACD', 'Signal', 'Histogram'.
                          Initial values will be NaN where calculation is not possible.
        """
        if not isinstance(prices, (list, pd.Series)):
            raise TypeError("Prices must be a list or pandas Series.")

        if isinstance(prices, list):
            prices_series = pd.Series(prices, dtype=float)
        else:
            prices_series = prices.astype(float)

        if len(prices_series) < self.long_period:
            # Not enough data, return DataFrame with NaNs
            nan_df = pd.DataFrame({
                'MACD': [float('nan')] * len(prices_series),
                'Signal': [float('nan')] * len(prices_series),
                'Histogram': [float('nan')] * len(prices_series)
            }, index=prices_series.index)
            return nan_df

        # Calculate Short-term EMA
        ema_short = prices_series.ewm(span=self.short_period, adjust=False, min_periods=self.short_period).mean()

        # Calculate Long-term EMA
        ema_long = prices_series.ewm(span=self.long_period, adjust=False, min_periods=self.long_period).mean()

        # Calculate MACD Line
        macd_line = ema_short - ema_long

        # Calculate Signal Line (EMA of MACD Line)
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False, min_periods=self.signal_period).mean()

        # Calculate MACD Histogram
        histogram = macd_line - signal_line

        # Create DataFrame
        macd_df = pd.DataFrame({
            'MACD': macd_line,
            'Signal': signal_line,
            'Histogram': histogram
        }, index=prices_series.index)

        return macd_df

if __name__ == '__main__':
    # Example Usage:
    sample_prices_data = [
        26.86, 26.81, 26.35, 26.22, 26.31, 25.88, 25.93, 25.55, 25.91, 25.98,
        26.41, 26.40, 26.03, 26.08, 25.93, 25.58, 25.34, 25.07, 25.03, 24.80,
        24.60, 24.35, 24.58, 24.31, 23.79, 23.63, 23.63, 23.95, 24.20, 24.50,
        24.45, 24.13, 24.25, 24.63, 25.00, 25.38, 25.38, 25.21, 25.08, 25.00
    ] # 40 data points
    prices_series = pd.Series(sample_prices_data)

    macd_calculator = MACDIndicator(short_period=12, long_period=26, signal_period=9)
    macd_results = macd_calculator.calculate(prices_series)

    print("Sample Prices:")
    print(prices_series)
    print("\nMACD Results (12, 26, 9):")
    print(macd_results.tail(15)) # Print last 15 to see calculated values

    # Test with list input
    macd_results_list = macd_calculator.calculate(sample_prices_data)
    print("\nMACD Results from list input (tail):")
    print(macd_results_list.tail(15))

    # Test with insufficient data
    insufficient_data = sample_prices_data[:20] # Only 20 data points, less than long_period (26)
    macd_insufficient = macd_calculator.calculate(insufficient_data)
    print("\nMACD with insufficient data:")
    print(macd_insufficient)