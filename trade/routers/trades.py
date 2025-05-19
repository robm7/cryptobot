from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional, List, Union, Dict, Any
import os
import logging

from ..models.trade import Trade # Corrected import
from ..schemas.trade import MarketOrder, LimitOrder, TradeStatus, TradeResponse # Corrected import, changed OrderStatus to TradeStatus
from utils.exchange_interface import ExchangeInterface
from ..services.risk import RiskService # Corrected import

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Rate limit: 10 requests per minute
@limiter.limit("10/minute")
async def rate_limiter(request: Request):
    pass

# API Key Header for authentication
api_key_header = APIKeyHeader(name="X-API-KEY")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != os.getenv("TRADE_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

@router.post(
    "",
    response_model=TradeResponse, # Assuming TradeResponse is the common structure for order creation
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trading order",
    description="Places a new market or limit order on the specified exchange after passing risk checks.",
    response_description="Details of the created order as reported by the exchange.",
    responses={
        201: {
            "description": "Order created successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "market_order": {
                            "summary": "Example Market Order Response",
                            "value": {
                                "id": "12345", "exchange": "binance", "symbol": "BTC/USDT",
                                "order_type": "MARKET", "side": "BUY", "amount": "0.1",
                                "status": "FILLED", "created_at": "2025-05-17T11:10:00Z", "updated_at": "2025-05-17T11:10:00Z"
                            }
                        },
                        "limit_order": {
                            "summary": "Example Limit Order Response",
                            "value": {
                                "id": "67890", "exchange": "binance", "symbol": "ETH/USDT",
                                "order_type": "LIMIT", "side": "SELL", "amount": "1.0", "price": "3000.0",
                                "status": "NEW", "created_at": "2025-05-17T11:15:00Z", "updated_at": "2025-05-17T11:15:00Z"
                            }
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid order request (e.g., risk validation failed, insufficient funds, invalid parameters)"},
        401: {"description": "Unauthorized (Invalid API Key)"},
        # Add other relevant error codes like 429 (Rate Limit), 500 (Exchange Error) if specifically handled
    }
)
async def create_order(order: Union[MarketOrder, LimitOrder]): # Use Union for type hint
    """Create a new order (market or limit).
    
    - Validates order against risk parameters.
    - Executes on the specified exchange.
    """
    try:
        # Risk checks
        await RiskService.validate_order(order)
        
        exchange = ExchangeInterface.get_exchange(order.exchange)
        
        if isinstance(order, MarketOrder):
            trade = await exchange.create_market_order(
                symbol=order.symbol,
                side=order.side,
                amount=order.amount
            )
        else:
            trade = await exchange.create_limit_order(
                symbol=order.symbol,
                side=order.side,
                amount=order.amount,
                price=order.price
            )
            
        logger.info(f"Order executed: {trade}")
        # Assuming 'trade' dict matches TradeResponse structure or can be converted
        return TradeResponse(**trade) if isinstance(trade, dict) else trade
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e))

@router.get(
    "/{order_id}",
    response_model=TradeResponse, # Assuming TradeResponse can represent order status
    dependencies=[Depends(rate_limiter), Depends(verify_api_key)],
    summary="Get order status",
    description="Retrieves the current status of a specific order from the specified exchange.",
    response_description="Details of the order including its current status.",
    responses={
        200: {
            "description": "Order status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "12345", "exchange": "binance", "symbol": "BTC/USDT",
                        "order_type": "MARKET", "side": "BUY", "amount": "0.1",
                        "status": "FILLED", "created_at": "2025-05-17T11:10:00Z", "updated_at": "2025-05-17T11:10:00Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request (e.g., order not found on exchange)"},
        401: {"description": "Unauthorized (Invalid API Key)"},
        404: {"description": "Order not found (if exchange distinguishes this from general errors)"}
    }
)
async def get_order_status(order_id: str, exchange: str):
    """Get status of an existing order.
    
    Requires `order_id` and the `exchange` name where the order was placed.
    """
    try:
        exchange_interface = ExchangeInterface.get_exchange(exchange)
        order_status_data = await exchange_interface.get_order_status(order_id)
        logger.info(f"Retrieved order status for {order_id} on {exchange}")
        # Assuming order_status_data matches TradeResponse structure or can be converted
        return TradeResponse(**order_status_data) if isinstance(order_status_data, dict) else order_status_data
    except Exception as e:
        logger.error(f"Failed to get order status for {order_id} on {exchange}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Or more specific if error type is known
            detail=str(e))

@router.delete(
    "/{order_id}",
    response_model=Dict[str, Any], # Or a more specific CancelResponse schema
    dependencies=[Depends(rate_limiter), Depends(verify_api_key)],
    summary="Cancel an order",
    description="Cancels an open order on the specified exchange.",
    response_description="Confirmation of the cancellation attempt.",
    responses={
        200: {
            "description": "Order cancellation request processed",
            "content": {
                "application/json": {
                    "example": {"status": "cancelled", "order_id": "67890", "response": "some_exchange_specific_data"}
                }
            }
        },
        400: {"description": "Invalid request (e.g., order already filled or cannot be cancelled)"},
        401: {"description": "Unauthorized (Invalid API Key)"},
        404: {"description": "Order not found"}
    }
)
async def cancel_order(order_id: str, exchange: str):
    """Cancel an existing order.
    
    Requires `order_id` and the `exchange` name.
    """
    exchange_interface = ExchangeInterface.get_exchange(exchange)
    try:
        result = await exchange_interface.cancel_order(order_id)
        logger.info(f"Cancellation request for order {order_id} on {exchange} processed.")
        return result # ExchangeInterface.cancel_order should return a dict
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id} on {exchange}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Or more specific
            detail=str(e)
        )