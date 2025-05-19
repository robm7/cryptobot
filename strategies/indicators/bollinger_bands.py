import pandas as pd
from typing import Union, List

class BollingerBandsIndicator:
    """
    Calculates Bollinger Bands technical indicator.
    """

    def __init__(self, period: int = 20, num_std_dev: float = 2.0):
        """
        Initializes the BollingerBandsIndicator.

        Args:
            period (int): The period for the moving average and standard deviation. Default is 20.
            num_std_dev (float): The number of standard deviations for the upper and lower bands. Default is 2.0.
        """
        if not isinstance(period, int) or period <= 0:
            raise ValueError("Period must be a positive integer.")
        if not isinstance(num_std_dev, (int, float)) or num_std_dev <= 0:
            raise ValueError("Number of standard deviations must be a positive number.")
            
        self.period = period
        self.num_std_dev = num_std_dev

    def calculate(self, prices: Union[List[float], pd.Series]) -> pd.DataFrame:
        """
        Calculates the Middle Band, Upper Band, and Lower Band.

        Args:
            prices (Union[List[float], pd.Series]): A list or pandas Series of closing prices.

        Returns:
            pd.DataFrame: A pandas DataFrame with columns 'MiddleBand', 'UpperBand', 'LowerBand'.
                          Initial values will be NaN where calculation is not possible.
        """
        if not isinstance(prices, (list, pd.Series)):
            raise TypeError("Prices must be a list or pandas Series.")

        if isinstance(prices, list):
            prices_series = pd.Series(prices, dtype=float)
        else:
            prices_series = prices.astype(float)

        if len(prices_series) < self.period:
            # Not enough data, return DataFrame with NaNs
            nan_df = pd.DataFrame({
                'MiddleBand': [float('nan')] * len(prices_series),
                'UpperBand': [float('nan')] * len(prices_series),
                'LowerBand': [float('nan')] * len(prices_series)
            }, index=prices_series.index)
            return nan_df

        # Calculate Middle Band (SMA)
        middle_band = prices_series.rolling(window=self.period, min_periods=self.period).mean()

        # Calculate Standard Deviation
        std_dev = prices_series.rolling(window=self.period, min_periods=self.period).std()

        # Calculate Upper Band
        upper_band = middle_band + (std_dev * self.num_std_dev)

        # Calculate Lower Band
        lower_band = middle_band - (std_dev * self.num_std_dev)

        # Create DataFrame
        bb_df = pd.DataFrame({
            'MiddleBand': middle_band,
            'UpperBand': upper_band,
            'LowerBand': lower_band
        }, index=prices_series.index)

        return bb_df

if __name__ == '__main__':
    # Example Usage:
    sample_prices_data = [
        22.27, 22.19, 22.08, 22.17, 22.18, 22.13, 22.23, 22.43, 22.24, 22.29,
        22.15, 22.39, 22.38, 22.61, 23.36, 24.05, 23.75, 23.83, 23.95, 23.63,
        23.82, 23.87, 23.65, 23.19, 23.10, 23.33, 22.94, 23.00, 22.70, 22.69
    ] # 30 data points
    prices_series = pd.Series(sample_prices_data)

    bb_calculator = BollingerBandsIndicator(period=20, num_std_dev=2)
    bb_results = bb_calculator.calculate(prices_series)

    print("Sample Prices:")
    print(prices_series)
    print("\nBollinger Bands (20, 2):")
    print(bb_results.tail(15)) # Print last 15 to see calculated values

    # Test with list input
    bb_results_list = bb_calculator.calculate(sample_prices_data)
    print("\nBollinger Bands from list input (tail):")
    print(bb_results_list.tail(15))

    # Test with insufficient data
    insufficient_data = sample_prices_data[:15] # Only 15 data points, less than period (20)
    bb_insufficient = bb_calculator.calculate(insufficient_data)
    print("\nBollinger Bands with insufficient data:")
    print(bb_insufficient)