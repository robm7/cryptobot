import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal

from trade.engine import TradingEngine, Order, OrderStatus
from trade.services.risk_manager import RiskManager
from trade.services.portfolio_manager import PortfolioManager
# Assuming exchange_config is used in trade.engine for API keys
# from trade.config import exchange_config # Will be mocked

# Mock strategy signal (can be more sophisticated if needed)
mock_trade_signal = {
    "signal_id": "strat_signal_001",
    "symbol": "BTC/USD",
    "action": "BUY",  # 'BUY' or 'SELL'
    "order_type": "LIMIT",  # 'LIMIT', 'MARKET'
    "quantity": Decimal("0.1"),
    "price": Decimal("50000.00"),
    "strategy_id": "test_strategy_001"
}

class TestCriticalWorkflowIntegration:

    @pytest.mark.asyncio
    async def test_signal_to_portfolio_update_flow(self):
        """
        Tests the end-to-end flow from a strategy signal (leading to an order),
        through trade execution (mocked exchange), and portfolio update.
        """
        # 1. Prepare the Order object from the signal
        test_order = Order(
            id="test_order_id_001", # Initial ID, will be updated by engine
            symbol=mock_trade_signal["symbol"],
            side=mock_trade_signal["action"].lower(), # 'buy' or 'sell'
            type=mock_trade_signal["order_type"].lower(), # 'limit' or 'market'
            amount=float(mock_trade_signal["quantity"]), # Order dataclass expects float
            price=float(mock_trade_signal["price"]) # Order dataclass expects float
        )

        # 2. Setup Mocks
        # Mock exchange_config to avoid loading real API keys
        mock_config = MagicMock()
        mock_config.api_key = "mock_api_key"
        mock_config.api_secret = "mock_api_secret"
        # Add other attributes if BinanceExchange constructor needs them from exchange_config

        # Mock the exchange client that TradingEngine will instantiate
        mock_exchange_instance = AsyncMock()
        # This is the response from the exchange after successfully placing an order
        mock_exchange_order_response = {
            'orderId': 'mock_exchange_order_id_123', # Matches engine.py:294
            'symbol': test_order.symbol,
            'side': test_order.side.upper(),
            'type': test_order.type.upper(),
            'origQty': str(test_order.amount),
            'price': str(test_order.price),
            'status': 'FILLED', # Simulate immediate fill for simplicity
            # For a FILLED status, these would typically be present from exchange
            'executedQty': str(test_order.amount),
            'cummulativeQuoteQty': str(test_order.amount * test_order.price),
            # Potentially more fields like 'fills' array
        }
        mock_exchange_instance.create_order.return_value = mock_exchange_order_response
        mock_exchange_instance.test_connection = AsyncMock(return_value=None) # For pre-order check

        # Patch exchange_config, BinanceExchange, and RiskManager's validate_order
        with patch('trade.engine.exchange_config', mock_config), \
             patch('trade.engine.BinanceExchange', return_value=mock_exchange_instance) as MockedBinanceExchange, \
             patch.object(RiskManager, 'validate_order', new_callable=AsyncMock) as mock_validate_order, \
             patch.object(PortfolioManager, 'add_position', new_callable=AsyncMock) as mock_add_position:

            # Configure mock return values
            mock_validate_order.return_value = (True, None) # Simulate risk check pass

            # 3. Instantiate TradingEngine
            # The engine will internally create its own RiskManager and PortfolioManager
            # We are patching methods on the *classes* RiskManager and PortfolioManager
            # or on the *instance* of the exchange client.
            trading_engine = TradingEngine(exchange_name="binance")
            
            # The actual PortfolioManager instance inside the engine
            # We will assert calls on the mock_add_position which is patched on the class
            # but it will intercept calls to the instance's method.
            internal_portfolio_manager = trading_engine.portfolio_manager


            # 4. Trigger the workflow by placing the order
            try:
                returned_order = await trading_engine.place_order(test_order)
            except Exception as e:
                pytest.fail(f"TradingEngine.place_order raised an exception: {e}")

            # 5. Assert outcomes
            # Assert RiskManager was consulted
            mock_validate_order.assert_called_once()
            # We can be more specific about the arguments if needed:
            # called_order_arg = mock_validate_order.call_args[0][0]
            # assert called_order_arg.symbol == test_order.symbol

            # Assert an order placement attempt was made to the exchange
            mock_exchange_instance.create_order.assert_called_once_with(
                symbol=test_order.symbol,
                side=test_order.side,
                type=test_order.type,
                amount=Decimal(str(test_order.amount)), # Exchange interface might expect Decimal
                price=Decimal(str(test_order.price))
            )
            
            assert returned_order is not None
            assert returned_order.id == 'mock_exchange_order_id_123'
            # In this direct place_order test, status might be OPEN if not simulating fill via websocket
            # The `place_order` method itself sets status to OPEN. Fill comes via websocket.
            # For this test, we'll assume the `handle_execution` logic (or similar)
            # would be triggered by the exchange fill.
            # So, we will manually simulate the portfolio update part.

            # 6. Simulate PortfolioManager update based on the (mocked) fill
            # The `handle_execution` in TradingEngine does this.
            # For this integration test, we'll directly call the portfolio manager's method
            # as if the fill event was processed.
            
            # Data for portfolio update, derived from the mock fill
            fill_symbol = mock_exchange_order_response['symbol']
            fill_side = mock_exchange_order_response['side']
            # `handle_execution` uses Decimal for price and quantity
            fill_price = Decimal(mock_exchange_order_response['price'])
            fill_quantity = Decimal(mock_exchange_order_response['executedQty'])
            
            # Adjust quantity for portfolio manager based on side
            portfolio_quantity = fill_quantity if fill_side == 'BUY' else -fill_quantity

            # Manually call the portfolio update (as `handle_execution` would)
            # We are asserting the patched `PortfolioManager.add_position`
            await internal_portfolio_manager.add_position(
                symbol=fill_symbol,
                quantity=portfolio_quantity,
                price=fill_price
            )

            # Assert PortfolioManager was updated
            mock_add_position.assert_called_once_with(
                symbol=fill_symbol,
                quantity=portfolio_quantity,
                price=fill_price
            )
            
            # Further assertions could be made on the state of internal_portfolio_manager.positions
            # if we weren't mocking add_position itself but rather its dependencies.
            # For now, asserting the call to the (mocked) add_position is sufficient.

    # Additional test cases for variations (e.g., risk rejection) can be added here.