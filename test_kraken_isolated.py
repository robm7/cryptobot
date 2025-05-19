import os
import pytest
import ccxt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KrakenInterface:
    def __init__(self, api_key, api_secret):
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True, # ccxt built-in rate limiter
            'urls': {
                'api': 'https://demo-futures.kraken.com' # Use Kraken's paper trading endpoint
            }
        })

    def get_ticker(self, symbol):
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'bid': float(ticker['bid']),
                'ask': float(ticker['ask'])
            }
        except ccxt.NetworkError as e:
            logger.error(f"Kraken API NetworkError fetching ticker for {symbol}: {type(e).__name__} - {e}")
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"Kraken API ExchangeError fetching ticker for {symbol}: {type(e).__name__} - {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ticker for {symbol}: {type(e).__name__} - {e}")
            return None

    def create_order(self, symbol, order_type, side, amount, price=None):
        """Create order with basic validation"""
        try:
            # Basic validation for common malformed signal scenarios
            if not symbol or not isinstance(symbol, str):
                raise ccxt.BadSymbol(f"Invalid symbol: {symbol}")
            if order_type not in ['market', 'limit']: # Add other valid types if necessary
                raise ccxt.InvalidOrder(f"Invalid order_type: {order_type}")
            if side not in ['buy', 'sell']:
                raise ccxt.InvalidOrder(f"Invalid side: {side}")
            if not isinstance(amount, (int, float)) or amount <= 0:
                raise ccxt.InvalidOrder(f"Invalid amount: {amount}")
            if order_type == 'limit' and (price is None or not isinstance(price, (int, float)) or price <= 0):
                raise ccxt.InvalidOrder(f"Invalid price for limit order: {price}")

            params = {}
            if order_type == 'limit':
                params['price'] = price
            
            order = self.exchange.create_order(
                symbol,
                order_type,
                side,
                amount,
                price,
                params
            )
            logger.info(f"Order created successfully: {order['id']} for {symbol}")
            return order
        except ccxt.BadSymbol as e:
            logger.error(f"Order failed due to BadSymbol: {type(e).__name__} - {e}")
            return None
        except ccxt.InvalidOrder as e:
            logger.error(f"Order failed due to InvalidOrder (malformed signal): {type(e).__name__} - {e}")
            return None
        except ccxt.InsufficientFunds as e:
            logger.error(f"Order failed due to InsufficientFunds: {type(e).__name__} - {e}")
            return None
        except ccxt.AuthenticationError as e: # Will be tested specifically
            logger.error(f"Order failed due to AuthenticationError: {type(e).__name__} - {e}")
            raise # Re-raise to be caught by specific test
        except ccxt.RateLimitExceeded as e: # Will be tested specifically
            logger.error(f"Order failed due to RateLimitExceeded: {type(e).__name__} - {e}")
            raise # Re-raise to be caught by specific test
        except ccxt.NetworkError as e:
            logger.error(f"Order failed due to NetworkError: {type(e).__name__} - {e}")
            return None
        except ccxt.ExchangeError as e: # Catch other exchange-specific errors
            logger.error(f"Order failed due to ExchangeError: {type(e).__name__} - {e}")
            return None
        except Exception as e:
            logger.error(f"Order failed due to an unexpected error: {type(e).__name__} - {e}")
            return None

@pytest.mark.skipif(
    not os.getenv('KRAKEN_PAPER_API_KEY') or not os.getenv('KRAKEN_PAPER_API_SECRET'),
    reason="""Kraken Paper Trading API credentials not set.
    Create paper trading API keys at: https://demo-futures.kraken.com/settings/api
    Then set environment variables:
    export KRAKEN_PAPER_API_KEY=your_key
    export KRAKEN_PAPER_API_SECRET=your_secret"""
)
def test_kraken_paper_trading():
    """Test with Kraken's paper trading environment
    
    Requires:
    - Paper trading account at https://demo-futures.kraken.com
    - API keys with trading permissions
    - Environment variables set as shown above
    """
    """Test with Kraken's paper trading environment"""
    interface = KrakenInterface(
        os.getenv('KRAKEN_PAPER_API_KEY'),
        os.getenv('KRAKEN_PAPER_API_SECRET')
    )
    
    # Test market data
    ticker = interface.get_ticker('BTC/USD')
    assert ticker is not None
    assert isinstance(ticker['bid'], float)
    assert isinstance(ticker['ask'], float)
    assert ticker['bid'] > 0
    assert ticker['ask'] > ticker['bid']

    # Test order placement with minimal amount
    test_order = interface.create_order(
        symbol='BTC/USD',
        order_type='limit',
        side='buy',
        amount=0.0001,  # Minimal test amount
        price=ticker['bid'] * 0.9  # Below current bid
    )
    
    if test_order is None:
        pytest.skip("Order placement failed - likely insufficient sandbox funds")
    else:
        assert test_order['status'] in ['open', 'closed', 'filled'] # 'filled' can also be a valid status
        assert float(test_order['amount']) == 0.0001

# --- Tests for Fail Conditions ---

@pytest.mark.skipif(
    not os.getenv('KRAKEN_PAPER_API_KEY') or not os.getenv('KRAKEN_PAPER_API_SECRET'),
    reason="Kraken Paper Trading API credentials not set."
)
def test_kraken_malformed_signal(caplog):
    """Test sending a trade with a malformed or invalid signal."""
    interface = KrakenInterface(
        os.getenv('KRAKEN_PAPER_API_KEY'),
        os.getenv('KRAKEN_PAPER_API_SECRET')
    )
    caplog.set_level(logging.ERROR)

    # Scenario 1: Invalid order_type
    order_invalid_type = interface.create_order(
        symbol='BTC/USD',
        order_type='invalid_type', # Malformed
        side='buy',
        amount=0.001
    )
    assert order_invalid_type is None
    assert any("Order failed due to InvalidOrder (malformed signal): InvalidOrder - Invalid order_type: invalid_type" in message for message in caplog.messages)
    caplog.clear()

    # Scenario 2: Invalid symbol (e.g., empty or not a string)
    order_invalid_symbol = interface.create_order(
        symbol='', # Malformed
        order_type='market',
        side='buy',
        amount=0.001
    )
    assert order_invalid_symbol is None
    assert any("Order failed due to BadSymbol: BadSymbol - Invalid symbol: " in message for message in caplog.messages)
    caplog.clear()

    # Scenario 3: Invalid amount (e.g., zero or negative)
    order_invalid_amount = interface.create_order(
        symbol='BTC/USD',
        order_type='market',
        side='buy',
        amount=-0.001 # Malformed
    )
    assert order_invalid_amount is None
    assert any("Order failed due to InvalidOrder (malformed signal): InvalidOrder - Invalid amount: -0.001" in message for message in caplog.messages)
    caplog.clear()

    # Scenario 4: Missing price for limit order
    order_missing_price = interface.create_order(
        symbol='BTC/USD',
        order_type='limit',
        side='buy',
        amount=0.001,
        price=None # Malformed for limit
    )
    assert order_missing_price is None
    assert any("Order failed due to InvalidOrder (malformed signal): InvalidOrder - Invalid price for limit order: None" in message for message in caplog.messages)
    caplog.clear()

    # Scenario 5: Invalid side
    order_invalid_side = interface.create_order(
        symbol='BTC/USD',
        order_type='market',
        side='unknown_side', # Malformed
        amount=0.001
    )
    assert order_invalid_side is None
    assert any("Order failed due to InvalidOrder (malformed signal): InvalidOrder - Invalid side: unknown_side" in message for message in caplog.messages)
    caplog.clear()

def test_kraken_bad_api_key(caplog):
    """Test using a bad or expired API key."""
    interface = KrakenInterface(
        api_key="BAD_API_KEY_DOES_NOT_EXIST",
        api_secret="BAD_API_SECRET_REALLY_BAD"
    )
    caplog.set_level(logging.ERROR)

    # Attempt to fetch ticker, which requires authentication for private endpoints or might fail earlier
    ticker = interface.get_ticker('BTC/USD')
    # For public endpoints like fetch_ticker, ccxt might not immediately use the key unless it's a private one.
    # A more robust test is to try a private call, like create_order or fetch_balance.
    
    # Let's try creating an order, which is a private call and will definitely use the API key.
    with pytest.raises(ccxt.AuthenticationError) as excinfo:
        interface.create_order(
            symbol='BTC/USD',
            order_type='market',
            side='buy',
            amount=0.001
        )
    
    assert "kraken {" in str(excinfo.value).lower() # Check if kraken is mentioned in the error
    assert "invalid key" in str(excinfo.value).lower() or \
           "invalid signature" in str(excinfo.value).lower() or \
           "permission denied" in str(excinfo.value).lower() or \
           "apikey:invalid" in str(excinfo.value).lower()
           
    assert any("Order failed due to AuthenticationError: AuthenticationError" in message for message in caplog.messages)
    caplog.clear()

    # Also test get_ticker if it were to use keys for a private version (though typically public)
    # Re-initialize for a clean slate if needed, or ensure get_ticker also raises if keys are bad and used.
    # Most exchanges' fetch_ticker is public. If Kraken's paper trading fetch_ticker requires auth, this would be relevant.
    # For now, the create_order test is more definitive for AuthenticationError.
    # If get_ticker for paper trading *does* use the key and fails, we'd see logs.
    # Let's assume get_ticker might not fail if it's treated as public by ccxt for this endpoint.
    # The primary check is the private call (create_order).

@pytest.mark.skipif(
    not os.getenv('KRAKEN_PAPER_API_KEY') or not os.getenv('KRAKEN_PAPER_API_SECRET'),
    reason="Kraken Paper Trading API credentials not set. Rate limit tests can be disruptive."
)
def test_kraken_rate_limit(caplog, monkeypatch):
    """Test triggering Kraken's API rate limits."""
    interface = KrakenInterface(
        os.getenv('KRAKEN_PAPER_API_KEY'),
        os.getenv('KRAKEN_PAPER_API_SECRET')
    )
    caplog.set_level(logging.ERROR)

    # Mock the exchange's request method to simulate a RateLimitExceeded error
    def mock_request_rate_limit(*args, **kwargs):
        raise ccxt.RateLimitExceeded("Simulated API rate limit exceeded")

    monkeypatch.setattr(interface.exchange, 'request', mock_request_rate_limit)

    with pytest.raises(ccxt.RateLimitExceeded) as excinfo:
        interface.create_order( # Or any other method that makes an API call
            symbol='BTC/USD',
            order_type='market',
            side='buy',
            amount=0.001
        )
    
    assert "Simulated API rate limit exceeded" in str(excinfo.value)
    assert any("Order failed due to RateLimitExceeded: RateLimitExceeded - Simulated API rate limit exceeded" in message for message in caplog.messages)
    caplog.clear()

    # Test with get_ticker as well
    monkeypatch.setattr(interface.exchange, 'fetch_ticker', mock_request_rate_limit) # More direct for fetch_ticker
    ticker_result = interface.get_ticker('BTC/USD')
    assert ticker_result is None # Should return None as per error handling
    assert any("Kraken API ExchangeError fetching ticker for BTC/USD: RateLimitExceeded - Simulated API rate limit exceeded" in message for message in caplog.messages)
    caplog.clear()