import pytest
import pandas as pd
import numpy as np
from strategies.indicators.macd import MACDIndicator

class TestMACDIndicator:
    """
    Unit tests for the MACDIndicator class.
    """

    @pytest.fixture
    def sample_prices_long(self) -> pd.Series:
        """
        Provides a longer sample pandas Series of prices for testing.
        This data is taken from a known source for MACD calculation.
        Source: https://school.stockcharts.com/doku.php?id=technical_indicators:moving_average_convergence_divergence_macd
        (Using the table values for the first ~40 days)
        """
        return pd.Series([
            22.27, 22.19, 22.08, 22.17, 22.18, 22.13, 22.23, 22.43, 22.24, 22.29, # 10
            22.15, 22.39, 22.38, 22.61, 23.36, 24.05, 23.75, 23.83, 23.95, 23.63, # 20
            23.82, 23.87, 23.65, 23.19, 23.10, 23.33, 22.68, 23.10, 22.40, 22.17, # 30
            21.90, 21.30, 21.51, 21.22, 21.01, 21.34, 20.90, 21.11, 21.23, 21.00  # 40
        ])

    @pytest.fixture
    def sample_prices_short(self) -> pd.Series:
        """Provides a short sample pandas Series of prices (less than long_period)."""
        return pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])

    @pytest.fixture
    def empty_prices(self) -> pd.Series:
        """Provides an empty pandas Series of prices."""
        return pd.Series([], dtype=float)

    def test_macd_indicator_creation_default(self):
        """Test MACDIndicator creation with default parameters."""
        indicator = MACDIndicator()
        assert indicator.short_period == 12
        assert indicator.long_period == 26
        assert indicator.signal_period == 9
        assert repr(indicator) == "MACDIndicator(short_period=12, long_period=26, signal_period=9)"

    def test_macd_indicator_creation_custom(self):
        """Test MACDIndicator creation with custom parameters."""
        indicator = MACDIndicator(short_period=10, long_period=20, signal_period=5)
        assert indicator.short_period == 10
        assert indicator.long_period == 20
        assert indicator.signal_period == 5

    @pytest.mark.parametrize("short, long, signal, error_msg_part", [
        (0, 26, 9, "short_period must be a positive integer"),
        (12, 0, 9, "long_period must be a positive integer"),
        (12, 26, 0, "signal_period must be a positive integer"),
        (-5, 26, 9, "short_period must be a positive integer"),
        (12, -5, 9, "long_period must be a positive integer"),
        (12, 26, -5, "signal_period must be a positive integer"),
        (26, 12, 9, "short_period must be less than long_period"),
        (12, 12, 9, "short_period must be less than long_period"),
        ("12", 26, 9, "short_period must be a positive integer"),
        (12, "26", 9, "long_period must be a positive integer"),
        (12, 26, "9", "signal_period must be a positive integer"),
    ])
    def test_macd_indicator_creation_invalid_params(self, short, long, signal, error_msg_part):
        """Test MACDIndicator creation with invalid parameters."""
        with pytest.raises(ValueError) as excinfo:
            MACDIndicator(short_period=short, long_period=long, signal_period=signal)
        assert error_msg_part in str(excinfo.value)

    def test_calculate_macd_valid_data(self, sample_prices_long: pd.Series):
        """
        Test MACD calculation with a known dataset.
        Values are cross-referenced with online calculators and manual checks.
        Note: Exact EMA values can differ slightly based on initialization (simple vs. exponential start).
        Pandas ewm default `adjust=False` uses a recursive formula that matches common implementations.
        """
        indicator = MACDIndicator(short_period=12, long_period=26, signal_period=9)
        results_df = indicator.calculate(sample_prices_long)

        assert isinstance(results_df, pd.DataFrame)
        assert "MACD" in results_df.columns
        assert "Signal" in results_df.columns
        assert "Histogram" in results_df.columns
        assert len(results_df) == len(sample_prices_long)
        
        macd_line = results_df["MACD"]
        signal_line = results_df["Signal"]
        histogram = results_df["Histogram"]

        # Check for NaNs at the beginning
        # EMA long (26) will have its first value at index 25 (0-indexed).
        # So, MACD line will also have its first value at index 25.
        assert pd.isna(macd_line.iloc[:25]).all()
        assert pd.notna(macd_line.iloc[25])

        # Signal line needs `signal_period` (9) values from macd_line.
        # So, first non-NaN MACD is at index 25.
        # First non-NaN Signal is at index 25 + (9 - 1) = 33.
        assert pd.isna(signal_line.iloc[:33]).all()
        assert pd.notna(signal_line.iloc[33])

        # Histogram depends on MACD and Signal
        assert pd.isna(histogram.iloc[:33]).all()
        assert pd.notna(histogram.iloc[33])

        # Spot check some calculated values (approximations based on common MACD calculations)
        # These values are from the example in the MACDIndicator class itself,
        # which uses pandas ewm with adjust=False.
        # For the sample_prices_long data:
        # Expected values at index 39 (last value):
        # EMA12[39] = 21.196010
        # EMA26[39] = 21.800418
        # MACD[39] = EMA12[39] - EMA26[39] = 21.196010 - 21.800418 = -0.604408
        # Signal[39] (needs previous 8 MACD values to calculate 9-day EMA of MACD)
        #   MACD values from index 31 to 39:
        #   31: -0.636972 (prices[31]=21.30)
        #   32: -0.593781 (prices[32]=21.51)
        #   33: -0.623503 (prices[33]=21.22)
        #   34: -0.706108 (prices[34]=21.01)
        #   35: -0.640331 (prices[35]=21.34)
        #   36: -0.720000 (prices[36]=20.90)
        #   37: -0.676364 (prices[37]=21.11)
        #   38: -0.620133 (prices[38]=21.23)
        #   39: -0.604408 (prices[39]=21.00)
        #   Signal[33] = -0.401232 (first non-NaN signal)
        #   Signal[39] = -0.589009 (calculated using pandas ewm on the MACD series)
        # Histogram[39] = MACD[39] - Signal[39] = -0.604408 - (-0.589009) = -0.015399

        assert np.isclose(macd_line.iloc[39], -0.604408, atol=1e-5)
        assert np.isclose(signal_line.iloc[39], -0.589009, atol=1e-5)
        assert np.isclose(histogram.iloc[39], -0.015399, atol=1e-5)

        # Check a value in the middle where signal is defined
        # MACD[33] = -0.623503
        # Signal[33] = -0.401232 (this is the first non-NaN signal value)
        # Histogram[33] = -0.623503 - (-0.401232) = -0.222271
        assert np.isclose(macd_line.iloc[33], -0.623503, atol=1e-5)
        assert np.isclose(signal_line.iloc[33], -0.401232, atol=1e-5)
        assert np.isclose(histogram.iloc[33], -0.222271, atol=1e-5)


    def test_calculate_macd_insufficient_data(self, sample_prices_short: pd.Series):
        """Test MACD calculation with insufficient data (less than long_period)."""
        indicator = MACDIndicator(short_period=12, long_period=26, signal_period=9)
        results_df = indicator.calculate(sample_prices_short)

        assert isinstance(results_df, pd.DataFrame)
        assert "MACD" in results_df.columns
        assert "Signal" in results_df.columns
        assert "Histogram" in results_df.columns

        macd_line = results_df["MACD"]
        signal_line = results_df["Signal"]
        histogram = results_df["Histogram"]

        # Expect all NaN series with the same index as input
        assert macd_line.isna().all()
        assert signal_line.isna().all()
        assert histogram.isna().all()
        assert macd_line.index.equals(sample_prices_short.index)
        assert signal_line.index.equals(sample_prices_short.index)
        assert histogram.index.equals(sample_prices_short.index)
        assert len(macd_line) == len(sample_prices_short)


    def test_calculate_macd_empty_data(self, empty_prices: pd.Series):
        """Test MACD calculation with empty input data."""
        indicator = MACDIndicator()
        results_df = indicator.calculate(empty_prices)

        assert isinstance(results_df, pd.DataFrame)
        assert "MACD" in results_df.columns
        assert "Signal" in results_df.columns
        assert "Histogram" in results_df.columns
        assert results_df["MACD"].empty
        assert results_df["Signal"].empty
        assert results_df["Histogram"].empty
        assert results_df["MACD"].dtype == 'float64'
        assert results_df["Signal"].dtype == 'float64'
        assert results_df["Histogram"].dtype == 'float64'

    def test_calculate_macd_just_enough_for_long_ema(self):
        """Test with data just enough for long_period EMA but not signal."""
        indicator = MACDIndicator(short_period=3, long_period=5, signal_period=3)
        # Long period is 5, so need at least 5 data points for first MACD value.
        # Signal period is 3, so need 5 + (3-1) = 7 data points for first signal value.
        prices = pd.Series(range(1, 7)) # 6 data points

        results_df = indicator.calculate(prices)
        macd_line = results_df["MACD"]
        signal_line = results_df["Signal"]
        histogram = results_df["Histogram"]

        # EMA_long (5) first value at index 4. MACD first value at index 4.
        assert pd.isna(macd_line.iloc[:4]).all()
        assert pd.notna(macd_line.iloc[4])
        assert pd.notna(macd_line.iloc[5])

        # Signal line needs 3 MACD values. First MACD at index 4.
        # So, first signal at index 4 + (3-1) = 6.
        # With 6 data points (index 0-5), signal line should be all NaN.
        assert signal_line.isna().all()
        assert histogram.isna().all() # Histogram depends on signal line

    def test_calculate_macd_just_enough_for_signal(self):
        """Test with data just enough for the signal line to have one value."""
        indicator = MACDIndicator(short_period=3, long_period=5, signal_period=3)
        # Long period is 5. Signal period is 3.
        # Need 5 + (3-1) = 7 data points for first signal value (at index 6).
        prices = pd.Series(range(1, 8)) # 7 data points (index 0-6)

        results_df = indicator.calculate(prices)
        macd_line = results_df["MACD"]
        signal_line = results_df["Signal"]
        histogram = results_df["Histogram"]

        # MACD first value at index 4.
        assert pd.isna(macd_line.iloc[:4]).all()
        assert pd.notna(macd_line.iloc[4])
        assert pd.notna(macd_line.iloc[5])
        assert pd.notna(macd_line.iloc[6])

        # Signal line first value at index 6.
        assert pd.isna(signal_line.iloc[:6]).all()
        assert pd.notna(signal_line.iloc[6])

        # Histogram first value at index 6.
        assert pd.isna(histogram.iloc[:6]).all()
        assert pd.notna(histogram.iloc[6])

    def test_calculate_with_non_series_input(self):
        """Test calculate method with invalid input type for prices."""
        indicator = MACDIndicator()
        # The MACDIndicator.calculate now accepts list or pd.Series
        # This test should check for other invalid types if necessary,
        # or be removed if list and Series are the only intended valid types.
        # For now, let's assume the type check in the method is sufficient.
        # If we want to test for other specific invalid types:
        with pytest.raises(TypeError, match="Prices must be a list or pandas Series"):
             indicator.calculate("not a list or series") # type: ignore
        with pytest.raises(TypeError, match="Prices must be a list or pandas Series"):
             indicator.calculate(12345) # type: ignore

    def test_repr_method(self):
        """Test the __repr__ method."""
        indicator = MACDIndicator(short_period=10, long_period=20, signal_period=5)
        expected_repr = "MACDIndicator(short_period=10, long_period=20, signal_period=5)"
        assert repr(indicator) == expected_repr

# Example of how to run tests from the command line (if this file is run directly):
# pytest tests/indicators/test_macd.py