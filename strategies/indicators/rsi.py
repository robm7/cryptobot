import pandas as pd
from typing import List, Union

class RSIIndicator:
    """
    Calculates the Relative Strength Index (RSI) technical indicator.
    """

    def __init__(self, period: int = 14):
        """
        Initializes the RSIIndicator.

        Args:
            period (int): The period for RSI calculation. Default is 14.
        """
        if not isinstance(period, int) or period <= 0:
            raise ValueError("Period must be a positive integer.")
        self.period = period

    def calculate(self, prices: Union[List[float], pd.Series]) -> pd.Series:
        """
        Calculates the RSI values for a given series of prices.

        Args:
            prices (Union[List[float], pd.Series]): A list or pandas Series of closing prices.

        Returns:
            pd.Series: A pandas Series containing the RSI values.
                       The first (period) values will be NaN as RSI cannot be calculated.
        """
        if not isinstance(prices, (list, pd.Series)):
            raise TypeError("Prices must be a list or pandas Series.")

        if isinstance(prices, list):
            prices_series = pd.Series(prices, dtype=float)
        else:
            prices_series = prices.astype(float)

        if len(prices_series) < self.period + 1:
            # Not enough data to calculate RSI, return series of NaNs
            return pd.Series([float('nan')] * len(prices_series), index=prices_series.index)

        delta = prices_series.diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate initial average gain and loss using simple moving average
        avg_gain = gain.rolling(window=self.period, min_periods=self.period).mean().iloc[self.period-1:self.period]
        avg_loss = loss.rolling(window=self.period, min_periods=self.period).mean().iloc[self.period-1:self.period]


        # Subsequent calculations use Wilder's smoothing method (exponential moving average)
        # For the first RSI value, the average gain/loss is a simple average.
        # For subsequent values, it's: Previous AvgGain * (period - 1) + Current Gain) / period

        gains = [avg_gain.iloc[0]]
        losses = [avg_loss.iloc[0]]

        for i in range(self.period, len(prices_series)):
            current_gain = gain.iloc[i]
            current_loss = loss.iloc[i]
            gains.append((gains[-1] * (self.period - 1) + current_gain) / self.period)
            losses.append((losses[-1] * (self.period - 1) + current_loss) / self.period)

        avg_gain_series = pd.Series([float('nan')] * (self.period -1) + gains, index=prices_series.index[:len(gains) + self.period -1])
        avg_loss_series = pd.Series([float('nan')] * (self.period -1) + losses, index=prices_series.index[:len(losses) + self.period -1])


        rs = avg_gain_series / avg_loss_series
        rsi = 100 - (100 / (1 + rs))

        # Fill initial NaNs for the period where RSI cannot be calculated
        # The first valid RSI is at index `period`
        final_rsi = pd.Series([float('nan')] * self.period, index=prices_series.index[:self.period])
        final_rsi = pd.concat([final_rsi, rsi.iloc[self.period-1:]]) # rsi series starts effectively from period-1 due to how gains/losses were built

        # Ensure the output series has the same length as input, padding with NaNs at the beginning
        if len(final_rsi) < len(prices_series):
            nan_padding = pd.Series([float('nan')] * (len(prices_series) - len(final_rsi)),
                                    index=prices_series.index[len(final_rsi):])
            final_rsi = pd.concat([final_rsi, nan_padding])
        
        # Correcting the index for the final_rsi to match prices_series
        final_rsi.index = prices_series.index

        return final_rsi

if __name__ == '__main__':
    # Example Usage:
    sample_prices = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
        45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
        46.21 # 21 data points
    ]
    rsi_calculator = RSIIndicator(period=14)
    rsi_values = rsi_calculator.calculate(pd.Series(sample_prices))
    print("Sample Prices:")
    print(pd.Series(sample_prices))
    print("\nRSI (14):")
    print(rsi_values)

    # Test with a list
    sample_prices_list = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
        45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
        46.21
    ]
    rsi_values_list = rsi_calculator.calculate(sample_prices_list)
    print("\nRSI (14) from list:")
    print(rsi_values_list)

    # Test with insufficient data
    insufficient_prices = [44.34, 44.09, 44.15, 43.61]
    rsi_insufficient = rsi_calculator.calculate(insufficient_prices)
    print("\nRSI (14) with insufficient data:")
    print(rsi_insufficient)

    rsi_calculator_5 = RSIIndicator(period=5)
    rsi_values_5 = rsi_calculator_5.calculate(sample_prices)
    print("\nRSI (5):")
    print(rsi_values_5)