import pytest
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.exchange_interface import MockExchangeInterface

# Use a concrete implementation for testing, or mock BaseStrategy if needed
class ConcreteStrategy(BaseStrategy):
    def __init__(self, exchange_interface=None, **params):
        super().__init__(exchange_interface=exchange_interface, **params)

    @staticmethod
    def validate_parameters(params: dict) -> None:
        pass # No specific params for this test strategy

    async def process_realtime_data(self, data_point: dict) -> None:
        pass # Not needed for these tests

    def generate_signals(self, data: pd.DataFrame):
        pass # Not needed for these tests

@pytest.fixture
def strategy():
    """Provides a BaseStrategy instance for testing."""
    # Using MockExchangeInterface as it's simpler for these unit tests
    mock_interface = MockExchangeInterface()
    return ConcreteStrategy(exchange_interface=mock_interface)

# --- Test Cases for _update_position_from_fill --- 

def test_open_long(strategy):
    fill = {'side': 'buy', 'amount': 0.1, 'price': 50000.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(0.1)
    assert strategy.average_entry_price == pytest.approx(50000.0)

def test_increase_long(strategy):
    # Initial position
    strategy.position_size = 0.1
    strategy.average_entry_price = 50000.0
    # Additional fill
    fill = {'side': 'buy', 'amount': 0.05, 'price': 51000.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(0.15)
    # Expected avg price: (0.1 * 50000 + 0.05 * 51000) / 0.15 = 50333.33...
    assert strategy.average_entry_price == pytest.approx(50333.333333)

def test_reduce_long(strategy):
    # Initial position
    strategy.position_size = 0.15
    strategy.average_entry_price = 50333.333333
    # Partial closing fill
    fill = {'side': 'sell', 'amount': 0.05, 'price': 52000.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(0.10)
    # Average entry price should remain the same when reducing
    assert strategy.average_entry_price == pytest.approx(50333.333333)

def test_close_long(strategy):
    # Initial position
    strategy.position_size = 0.1
    strategy.average_entry_price = 50333.333333
    # Closing fill
    fill = {'side': 'sell', 'amount': 0.1, 'price': 52500.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(0.0)
    assert strategy.average_entry_price == pytest.approx(0.0)

def test_open_short(strategy):
    fill = {'side': 'sell', 'amount': 0.2, 'price': 49000.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(-0.2)
    assert strategy.average_entry_price == pytest.approx(49000.0)

def test_increase_short(strategy):
    # Initial position
    strategy.position_size = -0.2
    strategy.average_entry_price = 49000.0
    # Additional fill
    fill = {'side': 'sell', 'amount': 0.1, 'price': 48500.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(-0.3)
    # Expected avg price: (0.2 * 49000 + 0.1 * 48500) / 0.3 = 48833.33...
    assert strategy.average_entry_price == pytest.approx(48833.333333)

def test_reduce_short(strategy):
    # Initial position
    strategy.position_size = -0.3
    strategy.average_entry_price = 48833.333333
    # Partial closing fill
    fill = {'side': 'buy', 'amount': 0.1, 'price': 48000.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(-0.2)
    # Average entry price should remain the same when reducing
    assert strategy.average_entry_price == pytest.approx(48833.333333)

def test_close_short(strategy):
    # Initial position
    strategy.position_size = -0.2
    strategy.average_entry_price = 48833.333333
    # Closing fill
    fill = {'side': 'buy', 'amount': 0.2, 'price': 47500.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(0.0)
    assert strategy.average_entry_price == pytest.approx(0.0)

def test_flip_long_to_short(strategy):
    # Initial position
    strategy.position_size = 0.1
    strategy.average_entry_price = 50000.0
    # Flipping fill (sell more than current long size)
    fill = {'side': 'sell', 'amount': 0.15, 'price': 51000.0}
    strategy._update_position_from_fill(fill)
    # New position size = 0.1 (long) - 0.15 (sell) = -0.05 (short)
    assert strategy.position_size == pytest.approx(-0.05)
    # New average entry price is the price of the flipping fill
    assert strategy.average_entry_price == pytest.approx(51000.0)

def test_flip_short_to_long(strategy):
    # Initial position
    strategy.position_size = -0.2
    strategy.average_entry_price = 49000.0
    # Flipping fill (buy more than current short size)
    fill = {'side': 'buy', 'amount': 0.25, 'price': 48000.0}
    strategy._update_position_from_fill(fill)
    # New position size = -0.2 (short) + 0.25 (buy) = 0.05 (long)
    assert strategy.position_size == pytest.approx(0.05)
    # New average entry price is the price of the flipping fill
    assert strategy.average_entry_price == pytest.approx(48000.0)

def test_zero_amount_fill(strategy):
    strategy.position_size = 0.1
    strategy.average_entry_price = 50000.0
    fill = {'side': 'buy', 'amount': 0.0, 'price': 51000.0}
    strategy._update_position_from_fill(fill)
    # State should not change
    assert strategy.position_size == pytest.approx(0.1)
    assert strategy.average_entry_price == pytest.approx(50000.0)

def test_zero_price_fill(strategy):
    strategy.position_size = 0.1
    strategy.average_entry_price = 50000.0
    fill = {'side': 'buy', 'amount': 0.05, 'price': 0.0}
    strategy._update_position_from_fill(fill)
    # State should not change
    assert strategy.position_size == pytest.approx(0.1)
    assert strategy.average_entry_price == pytest.approx(50000.0)

def test_close_long_with_tolerance(strategy):
    strategy.position_size = 1e-10
    strategy.average_entry_price = 50000.0
    fill = {'side': 'sell', 'amount': 1e-10, 'price': 51000.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(0.0)
    assert strategy.average_entry_price == pytest.approx(0.0)

def test_close_short_with_tolerance(strategy):
    strategy.position_size = -1e-10
    strategy.average_entry_price = 50000.0
    fill = {'side': 'buy', 'amount': 1e-10, 'price': 49000.0}
    strategy._update_position_from_fill(fill)
    assert strategy.position_size == pytest.approx(0.0)
    assert strategy.average_entry_price == pytest.approx(0.0)

# Add more tests for edge cases if necessary