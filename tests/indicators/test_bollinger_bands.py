import pytest
import pandas as pd
import numpy as np
from strategies.indicators.bollinger_bands import BollingerBandsIndicator

class TestBollingerBandsIndicator:
    """
    Unit tests for the BollingerBandsIndicator class using pytest.
    """

    @pytest.fixture
    def sample_prices_series(self) -> pd.Series:
        """Provides a sample pandas Series of prices for testing."""
        return pd.Series([
            10, 12, 15, 14, 13, 16, 18, 20, 19, 22,
            25, 23, 21, 24, 27, 28, 30, 29, 26, 25
        ], dtype=float)

    @pytest.fixture
    def sample_prices_list(self, sample_prices_series: pd.Series) -> list[float]:
        """Provides a sample list of prices for testing."""
        return sample_prices_series.tolist()

    def test_indicator_creation_default(self):
        """Test BollingerBandsIndicator creation with default parameters."""
        indicator = BollingerBandsIndicator()
        assert indicator.period == 20
        assert indicator.num_std_dev == 2.0

    def test_indicator_creation_custom(self):
        """Test BollingerBandsIndicator creation with custom parameters."""
        indicator = BollingerBandsIndicator(period=10, num_std_dev=1.5)
        assert indicator.period == 10
        assert indicator.num_std_dev == 1.5

    @pytest.mark.parametrize("period, num_std_dev, error_msg_part", [
        (0, 2.0, "Period must be a positive integer."),
        (-5, 2.0, "Period must be a positive integer."),
        ("abc", 2.0, "Period must be a positive integer."),
        (20, 0, "Number of standard deviations must be a positive number."),
        (20, -2.0, "Number of standard deviations must be a positive number."),
        (20, "abc", "Number of standard deviations must be a positive number."),
    ])
    def test_init_invalid_parameters(self, period, num_std_dev, error_msg_part):
        """Test initialization with invalid parameters."""
        with pytest.raises(ValueError) as excinfo:
            BollingerBandsIndicator(period=period, num_std_dev=num_std_dev) # type: ignore
        assert error_msg_part in str(excinfo.value)

    def test_calculate_bollinger_bands_valid_data_series(self, sample_prices_series: pd.Series):
        """Test calculation with a pandas Series."""
        indicator = BollingerBandsIndicator(period=5, num_std_dev=2)
        bb_df = indicator.calculate(sample_prices_series)

        assert isinstance(bb_df, pd.DataFrame)
        assert all(col in bb_df.columns for col in ['MiddleBand', 'UpperBand', 'LowerBand'])
        assert len(bb_df) == len(sample_prices_series)

        # Check that initial values are NaN due to rolling window (period - 1)
        assert bb_df['MiddleBand'].iloc[:4].isna().all()
        assert bb_df['UpperBand'].iloc[:4].isna().all()
        assert bb_df['LowerBand'].iloc[:4].isna().all()

        # Check a specific calculated value (index 4, which is the 5th data point)
        prices_data = sample_prices_series.tolist()
        expected_middle_4 = np.mean(prices_data[0:5])
        expected_std_4 = np.std(prices_data[0:5], ddof=1) # Pandas default ddof=1 for rolling().std()
        expected_upper_4 = expected_middle_4 + 2 * expected_std_4
        expected_lower_4 = expected_middle_4 - 2 * expected_std_4

        assert abs(bb_df['MiddleBand'].iloc[4] - expected_middle_4) < 1e-5
        assert abs(bb_df['UpperBand'].iloc[4] - expected_upper_4) < 1e-5
        assert abs(bb_df['LowerBand'].iloc[4] - expected_lower_4) < 1e-5

        # Test last values
        expected_middle_last = np.mean(prices_data[-5:])
        expected_std_last = np.std(prices_data[-5:], ddof=1)
        expected_upper_last = expected_middle_last + 2 * expected_std_last
        expected_lower_last = expected_middle_last - 2 * expected_std_last
        
        assert abs(bb_df['MiddleBand'].iloc[-1] - expected_middle_last) < 1e-5
        assert abs(bb_df['UpperBand'].iloc[-1] - expected_upper_last) < 1e-5
        assert abs(bb_df['LowerBand'].iloc[-1] - expected_lower_last) < 1e-5

    def test_calculate_bollinger_bands_valid_data_list(self, sample_prices_list: list[float]):
        """Test calculation with a list input."""
        indicator = BollingerBandsIndicator(period=5, num_std_dev=2)
        bb_df = indicator.calculate(sample_prices_list)

        assert isinstance(bb_df, pd.DataFrame)
        assert all(col in bb_df.columns for col in ['MiddleBand', 'UpperBand', 'LowerBand'])
        assert len(bb_df) == len(sample_prices_list)
        assert bb_df['MiddleBand'].iloc[:4].isna().all() # First 4 are NaN for period 5

        # Check a specific value (index 4)
        expected_middle_4 = np.mean(sample_prices_list[0:5])
        expected_std_4 = np.std(sample_prices_list[0:5], ddof=1)
        expected_upper_4 = expected_middle_4 + 2 * expected_std_4
        
        assert abs(bb_df['UpperBand'].iloc[4] - expected_upper_4) < 1e-5


    def test_insufficient_data(self):
        """Test calculation when there is not enough data for the period."""
        prices = pd.Series([10, 12, 15], dtype=float)
        indicator = BollingerBandsIndicator(period=5, num_std_dev=2)
        bb_df = indicator.calculate(prices)

        assert isinstance(bb_df, pd.DataFrame)
        assert bb_df['MiddleBand'].isna().all()
        assert bb_df['UpperBand'].isna().all()
        assert bb_df['LowerBand'].isna().all()
        assert len(bb_df) == len(prices)

    def test_empty_data(self):
        """Test calculation with an empty price series."""
        prices = pd.Series([], dtype=float)
        indicator = BollingerBandsIndicator(period=5, num_std_dev=2)
        bb_df = indicator.calculate(prices)

        assert isinstance(bb_df, pd.DataFrame)
        assert bb_df.empty
        assert all(col in bb_df.columns for col in ['MiddleBand', 'UpperBand', 'LowerBand'])


    def test_calculate_invalid_input_type(self):
        """Test calculate method with input that is not a list or pandas Series."""
        indicator = BollingerBandsIndicator(period=5, num_std_dev=2)
        with pytest.raises(TypeError, match="Prices must be a list or pandas Series."):
            indicator.calculate("not a list or series") # type: ignore
        with pytest.raises(TypeError, match="Prices must be a list or pandas Series."):
            indicator.calculate(12345) # type: ignore
    
    def test_calculate_with_nans_in_prices(self):
        """
        Test calculation when input prices contain NaNs.
        Pandas rolling functions handle NaNs by default (skipna=True).
        """
        prices_data = [10, 12, np.nan, 14, 13, 16, np.nan, 20, 19, 22]
        prices = pd.Series(prices_data, dtype=float)
        indicator = BollingerBandsIndicator(period=3, num_std_dev=2)
        bb_df = indicator.calculate(prices)

        assert isinstance(bb_df, pd.DataFrame)
        
        # Middle band at index 2 (based on [10, 12, NaN]) should use skipna=True
        assert abs(bb_df['MiddleBand'].iloc[2] - np.mean([10.0,12.0])) < 1e-5
        # Middle band at index 3 (based on [12, NaN, 14])
        assert abs(bb_df['MiddleBand'].iloc[3] - np.mean([12.0,14.0])) < 1e-5
        # Middle band at index 6 (based on [13, 16, NaN])
        assert abs(bb_df['MiddleBand'].iloc[6] - np.mean([13.0,16.0])) < 1e-5

        # Check that bands are also calculated where possible and are not NaN if middle band is not NaN
        assert not np.isnan(bb_df['UpperBand'].iloc[2])
        assert not np.isnan(bb_df['LowerBand'].iloc[2])
        
        # Where middle band is NaN due to insufficient non-NaNs in window, bands should also be NaN
        # e.g. prices_nan_heavy = pd.Series([np.nan, np.nan, 10, np.nan, np.nan, 15])
        # indicator_nan = BollingerBandsIndicator(period=3)
        # bb_df_nan = indicator_nan.calculate(prices_nan_heavy)
        # self.assertTrue(bb_df_nan['MiddleBand'].iloc[2].isna()) # Based on [nan,nan,10]
        # self.assertTrue(bb_df_nan['UpperBand'].iloc[2].isna())
        # self.assertTrue(bb_df_nan['LowerBand'].iloc[2].isna())

# To run tests from command line: pytest tests/indicators/test_bollinger_bands.py