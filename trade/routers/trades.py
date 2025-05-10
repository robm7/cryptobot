from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional, List
import os
import logging

from models.trade import Trade
from schemas.trade import MarketOrder, LimitOrder, OrderStatus
from utils.exchange_interface import ExchangeInterface
from services.risk import RiskService

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

@router.post("", dependencies=[Depends(rate_limiter), Depends(verify_api_key)])
async def create_order(order: MarketOrder | LimitOrder):
    """Create a new order (market or limit)"""
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
        return JSONResponse(content=trade, status_code=status.HTTP_201_CREATED)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e))

@router.get("/{order_id}", dependencies=[Depends(rate_limiter), Depends(verify_api_key)])
async def get_order_status(order_id: str, exchange: str):
    """Get status of an existing order"""
    try:
        exchange = ExchangeInterface.get_exchange(exchange)
        status = await exchange.get_order_status(order_id)
        logger.info(f"Retrieved order status: {order_id}")
        return JSONResponse(content=status, status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to get order status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e))

@router.delete("/{order_id}", dependencies=[Depends(rate_limiter), Depends(verify_api_key)])
async def cancel_order(order_id: str, exchange: str):
    """Cancel an existing order"""
    exchange = ExchangeInterface.get_exchange(exchange)
    try:
        result = await exchange.cancel_order(order_id)
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )