import os
import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock
import ccxt # Ensure ccxt is imported

# Corrected import based on actual content of exchange_clients.py
from utils.exchange_clients import (
    ExchangeClient,
    RateLimitError,
    AuthenticationError,
    OrderError,
    NetworkError,
    ExchangeError,
    get_exchange_client # Might be useful for direct ccxt instance if needed, but ExchangeClient is preferred
)

# Configure logging for the test module itself, if necessary for test logic.
# The ExchangeClient has its own internal logging.
logger = logging.getLogger(__name__)

# Helper to get paper trading credentials or skip test
def get_paper_trading_creds_for_skip():
    api_key = os.getenv('KRAKEN_PAPER_API_KEY')
    api_secret = os.getenv('KRAKEN_PAPER_API_SECRET')
    if not api_key or not api_secret:
        return False
    return True

@pytest.mark.skipif(not get_paper_trading_creds_for_skip(), reason="Kraken Paper Trading API credentials not configured (KRAKEN_PAPER_API_KEY, KRAKEN_PAPER_API_SECRET)")
@pytest.mark.asyncio
class TestKrakenPaperTrading:
    """Tests for Kraken paper trading interface using ExchangeClient"""

    @pytest.fixture
    async def paper_client(self):
        # ExchangeClient's get_exchange_client uses KRAKEN_PAPER_API_KEY for paper_trading=True
        client = ExchangeClient(exchange='kraken', paper_trading=True)
        # Note: The ExchangeClient(paper_trading=True) currently MOCKS order creation/cancellation.
        # To test against actual Kraken paper *endpoints*, paper_trading would be False,
        # and get_exchange_client would need to be configured with the paper URL.
        # For now, these tests will cover the ExchangeClient's paper_trading simulation.
        return client

    async def test_connectivity_paper(self, paper_client):
        """Test basic API connectivity by fetching balances (authenticated)"""
        balances = await paper_client.get_balances() # get_balances is mocked in paper_trading mode
        assert isinstance(balances, dict)
        assert 'USD' in balances # Mock balance

    async def test_market_data_paper(self, paper_client):
        """Test market data endpoints (get_ohlcv)"""
        # ExchangeClient's paper_trading=True does not mock get_ohlcv, so this might hit live if not careful.
        # However, get_exchange_client for Kraken in paper_trading=True mode uses paper keys.
        # The ccxt instance created by get_exchange_client for kraken does not set a demo URL.
        # This means get_ohlcv will hit the live Kraken API but with paper keys.
        # This might be okay for just fetching public market data.
        try:
            ohlcv = await paper_client.get_ohlcv('BTC/USD', timeframe='1m', limit=1)
            assert ohlcv is not None
            assert len(ohlcv) > 0
            assert len(ohlcv[0]) == 6
        except ExchangeError as e:
            pytest.skip(f"Skipping market data test due to ExchangeError (possibly paper keys on live endpoint): {e}")


    async def test_order_placement_and_cancel_paper(self, paper_client):
        """Test paper order placement and cancellation (mocked by ExchangeClient)"""
        order = await paper_client.create_order(
            symbol='BTC/USD',
            side='buy',
            amount=0.01,
            price=50000, # Mock price
            type='limit'  # 'type' is used by ExchangeClient
        )
        assert 'id' in order
        assert order['id'].startswith('PAPER-')
        assert order['status'] == 'open'

        # Verify order cancellation (mocked)
        cancel_result = await paper_client.cancel_order(order['id'], symbol='BTC/USD')
        assert cancel_result is True # Mocked cancel returns True

    async def test_balance_check_paper(self, paper_client):
        """Test paper balance retrieval (mocked by ExchangeClient)"""
        balances = await paper_client.get_balances()
        assert isinstance(balances, dict)
        assert 'USD' in balances
        assert isinstance(balances['USD'], float)


@pytest.mark.skipif(get_paper_trading_creds_for_skip(), reason="Skipping mock tests when paper trading configured")
@pytest.mark.asyncio
class TestKrakenMockedClient:
    """Fallback mock tests for ExchangeClient when paper trading not configured"""

    @patch('utils.exchange_clients.get_exchange_client') # Patch the factory function
    async def test_mock_connectivity(self, mock_get_exchange_client):
        # Configure the mock ccxt instance that get_exchange_client would return
        # The method 'fetch_balance' on the ccxt instance is what ExchangeClient.get_balances awaits
        mock_ccxt_fetch_balance = AsyncMock(return_value={'USD': {'free': 10000, 'total': 10000}})
        mock_ccxt_instance = AsyncMock()
        mock_ccxt_instance.fetch_balance = mock_ccxt_fetch_balance # Assign the async mock method
        
        mock_get_exchange_client.return_value = mock_ccxt_instance
        
        # Now, ExchangeClient will use this mock_ccxt_instance
        client = ExchangeClient(exchange='kraken', paper_trading=False) # paper_trading=False to use the actual methods
        
        balances_result = await client.get_balances() # This will await mock_ccxt_fetch_balance()
        assert 'USD' in balances_result
        mock_get_exchange_client.assert_called_with('kraken', False)
        mock_ccxt_fetch_balance.assert_called_once() # Assert the method mock was called


# --- Tests for Fail Conditions ---
# These tests ideally should run against an environment that can produce these errors.
# Using paper_trading=False with paper keys might hit live API structure.
# The get_exchange_client in exchange_clients.py needs to be configured with demo URLs
# if we want to hit a paper *trading server* instead of just using paper *keys* on live.
# For now, these tests assume KRAKEN_PAPER_API_KEY/SECRET are set and will be used
# by get_exchange_client when paper_trading=True is passed to ExchangeClient constructor.
# The ExchangeClient itself will then use the ccxt instance configured by get_exchange_client.

@pytest.mark.asyncio
class TestKrakenFailConditions:

    @pytest.fixture # Reverted to function scope
    async def resolved_fail_client(self): # Renamed back
        if not get_paper_trading_creds_for_skip():
             pytest.skip("Kraken Paper Trading API credentials not set, skipping fail condition tests that might use them.")
        client_instance = ExchangeClient(exchange='kraken', paper_trading=False)
        return client_instance

    async def test_kraken_malformed_signal_async(self, resolved_fail_client, caplog):
        """Test sending a trade with a malformed or invalid signal via ExchangeClient."""
        client = await resolved_fail_client  # Await the coroutine to resolve
        caplog.set_level(logging.ERROR)

        with pytest.raises(OrderError) as excinfo:
            await client.create_order(
                symbol='BTC/USD', type='invalid_type_for_kraken', side='buy', amount=0.01
            )

    async def test_kraken_bad_api_key_async(self, caplog): # This test creates its own client
        """Test using a bad or expired API key with ExchangeClient."""
        original_env = os.environ.copy()
        os.environ["KRAKEN_API_KEY"] = "BAD_API_KEY_DOES_NOT_EXIST_FOR_TEST"
        os.environ["KRAKEN_API_SECRET"] = "REALLY_BAD_API_SECRET_FOR_TESTING"
        
        client = ExchangeClient(exchange='kraken', paper_trading=False)
        caplog.set_level(logging.ERROR)
        
        with pytest.raises(AuthenticationError) as excinfo:
            await client.get_balances()
        
        assert "Authentication error" in str(excinfo.value)
        assert any("Authentication error for kraken" in rec.message for rec in caplog.records if rec.levelname == 'ERROR')
        assert any("invalid key" in rec.message.lower() for rec in caplog.records if rec.levelname == 'ERROR')
        
        os.environ.clear()
        os.environ.update(original_env)
        caplog.clear()

@patch('utils.exchange_clients.ccxt.kraken')
async def test_kraken_rate_limit_async(self, mock_ccxt_kraken, caplog, monkeypatch, resolved_fail_client):
    """Test triggering Kraken's API rate limits with ExchangeClient, mocking ccxt."""
    client = await resolved_fail_client  # Await the coroutine

    # Patch _handle_rate_limits so it doesn't interfere
    monkeypatch.setattr(client, '_handle_rate_limits', AsyncMock())

    # Simulate a rate limit error from the mock ccxt instance
    mock_instance = mock_ccxt_kraken.return_value
    mock_instance.create_order.side_effect = RateLimitError("Simulated rate limit")

    caplog.set_level(logging.ERROR)
    with pytest.raises(RateLimitError):
        await client.create_order(symbol='BTC/USD', type='limit', side='buy', amount=1)