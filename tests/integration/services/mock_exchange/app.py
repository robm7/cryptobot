"""
Mock Exchange Service for Integration Testing

This service simulates a cryptocurrency exchange API for integration testing.
It provides endpoints for market data, trading, and account information.
"""

import os
import json
import time
import logging
import random
import uuid
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock_exchange")

# Create FastAPI app
app = FastAPI(title="Mock Exchange API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simulated exchange delay
EXCHANGE_DELAY = float(os.environ.get("EXCHANGE_DELAY", "0.1"))

# In-memory storage
markets = {}
tickers = {}
orders = {}
balances = {}
trades = []

# Default market data
DEFAULT_MARKETS = {
    "BTC/USDT": {
        "id": "BTCUSDT",
        "symbol": "BTC/USDT",
        "base": "BTC",
        "quote": "USDT",
        "active": True,
        "precision": {
            "price": 2,
            "amount": 6
        },
        "limits": {
            "amount": {
                "min": 0.000001,
                "max": 1000.0
            },
            "price": {
                "min": 1.0,
                "max": 1000000.0
            },
            "cost": {
                "min": 10.0
            }
        }
    },
    "ETH/USDT": {
        "id": "ETHUSDT",
        "symbol": "ETH/USDT",
        "base": "ETH",
        "quote": "USDT",
        "active": True,
        "precision": {
            "price": 2,
            "amount": 5
        },
        "limits": {
            "amount": {
                "min": 0.00001,
                "max": 5000.0
            },
            "price": {
                "min": 1.0,
                "max": 100000.0
            },
            "cost": {
                "min": 10.0
            }
        }
    },
    "SOL/USDT": {
        "id": "SOLUSDT",
        "symbol": "SOL/USDT",
        "base": "SOL",
        "quote": "USDT",
        "active": True,
        "precision": {
            "price": 3,
            "amount": 2
        },
        "limits": {
            "amount": {
                "min": 0.01,
                "max": 10000.0
            },
            "price": {
                "min": 0.001,
                "max": 10000.0
            },
            "cost": {
                "min": 10.0
            }
        }
    }
}

# Default ticker data
DEFAULT_TICKERS = {
    "BTC/USDT": {
        "symbol": "BTC/USDT",
        "bid": 50000.0,
        "ask": 50050.0,
        "last": 50025.0,
        "high": 51000.0,
        "low": 49000.0,
        "volume": 100.5,
        "timestamp": int(time.time() * 1000)
    },
    "ETH/USDT": {
        "symbol": "ETH/USDT",
        "bid": 3000.0,
        "ask": 3010.0,
        "last": 3005.0,
        "high": 3100.0,
        "low": 2900.0,
        "volume": 500.25,
        "timestamp": int(time.time() * 1000)
    },
    "SOL/USDT": {
        "symbol": "SOL/USDT",
        "bid": 100.0,
        "ask": 100.5,
        "last": 100.25,
        "high": 105.0,
        "low": 95.0,
        "volume": 10000.5,
        "timestamp": int(time.time() * 1000)
    }
}

# Default balances
DEFAULT_BALANCES = {
    "BTC": {
        "free": 1.0,
        "used": 0.0,
        "total": 1.0
    },
    "ETH": {
        "free": 10.0,
        "used": 0.0,
        "total": 10.0
    },
    "SOL": {
        "free": 100.0,
        "used": 0.0,
        "total": 100.0
    },
    "USDT": {
        "free": 100000.0,
        "used": 0.0,
        "total": 100000.0
    }
}


# Models
class Ticker(BaseModel):
    symbol: str
    bid: float
    ask: float
    last: float
    high: float
    low: float
    volume: float
    timestamp: int


class OrderRequest(BaseModel):
    symbol: str
    type: str = Field(..., description="Order type: limit or market")
    side: str = Field(..., description="Order side: buy or sell")
    amount: float
    price: Optional[float] = None


class Order(BaseModel):
    id: str
    symbol: str
    type: str
    side: str
    amount: float
    price: Optional[float] = None
    status: str
    filled: float = 0.0
    cost: float = 0.0
    timestamp: int


class Balance(BaseModel):
    free: float
    used: float
    total: float


class Trade(BaseModel):
    id: str
    order_id: str
    symbol: str
    side: str
    amount: float
    price: float
    cost: float
    timestamp: int


# Simulate exchange delay
def simulate_delay():
    """Simulate exchange API delay."""
    time.sleep(EXCHANGE_DELAY)


# Initialize data
@app.on_event("startup")
def initialize_data():
    """Initialize exchange data."""
    global markets, tickers, balances
    
    # Initialize markets
    markets = DEFAULT_MARKETS.copy()
    
    # Initialize tickers
    tickers = DEFAULT_TICKERS.copy()
    
    # Initialize balances
    balances = DEFAULT_BALANCES.copy()
    
    logger.info("Initialized mock exchange data")


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Market data endpoints
@app.get("/api/markets")
def get_markets():
    """Get all markets."""
    simulate_delay()
    return {"markets": list(markets.values())}


@app.get("/api/ticker/{symbol}")
def get_ticker(symbol: str):
    """Get ticker for a symbol."""
    simulate_delay()
    
    # Normalize symbol
    symbol = symbol.replace("_", "/")
    
    if symbol not in tickers:
        raise HTTPException(status_code=404, detail=f"Ticker not found: {symbol}")
    
    # Update timestamp and add some price movement
    ticker = tickers[symbol].copy()
    ticker["timestamp"] = int(time.time() * 1000)
    
    # Add some random price movement (±0.5%)
    price_change = ticker["last"] * (random.uniform(-0.005, 0.005))
    ticker["last"] += price_change
    ticker["bid"] = ticker["last"] - (ticker["last"] * 0.001)
    ticker["ask"] = ticker["last"] + (ticker["last"] * 0.001)
    
    # Update ticker
    tickers[symbol] = ticker
    
    return ticker


@app.get("/api/tickers")
def get_tickers():
    """Get all tickers."""
    simulate_delay()
    
    # Update all tickers
    for symbol in tickers:
        # Update timestamp and add some price movement
        ticker = tickers[symbol].copy()
        ticker["timestamp"] = int(time.time() * 1000)
        
        # Add some random price movement (±0.5%)
        price_change = ticker["last"] * (random.uniform(-0.005, 0.005))
        ticker["last"] += price_change
        ticker["bid"] = ticker["last"] - (ticker["last"] * 0.001)
        ticker["ask"] = ticker["last"] + (ticker["last"] * 0.001)
        
        # Update ticker
        tickers[symbol] = ticker
    
    return {"tickers": list(tickers.values())}


# Trading endpoints
@app.post("/api/orders")
def create_order(order_request: OrderRequest, api_key: str = Header(None)):
    """Create a new order."""
    simulate_delay()
    
    # Validate API key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Normalize symbol
    symbol = order_request.symbol.replace("_", "/")
    
    # Validate symbol
    if symbol not in markets:
        raise HTTPException(status_code=404, detail=f"Market not found: {symbol}")
    
    # Validate order type
    if order_request.type not in ["limit", "market"]:
        raise HTTPException(status_code=400, detail=f"Invalid order type: {order_request.type}")
    
    # Validate order side
    if order_request.side not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail=f"Invalid order side: {order_request.side}")
    
    # Validate price for limit orders
    if order_request.type == "limit" and not order_request.price:
        raise HTTPException(status_code=400, detail="Price required for limit orders")
    
    # Get market data
    market = markets[symbol]
    
    # Validate amount
    min_amount = market["limits"]["amount"]["min"]
    max_amount = market["limits"]["amount"]["max"]
    
    if order_request.amount < min_amount:
        raise HTTPException(status_code=400, detail=f"Amount too small, minimum is {min_amount}")
    
    if order_request.amount > max_amount:
        raise HTTPException(status_code=400, detail=f"Amount too large, maximum is {max_amount}")
    
    # Get ticker
    ticker = tickers[symbol]
    
    # Calculate price for market orders
    price = order_request.price if order_request.type == "limit" else ticker["last"]
    
    # Calculate cost
    cost = order_request.amount * price
    
    # Validate cost
    min_cost = market["limits"]["cost"]["min"]
    
    if cost < min_cost:
        raise HTTPException(status_code=400, detail=f"Cost too small, minimum is {min_cost}")
    
    # Check balance
    base_currency = market["base"]
    quote_currency = market["quote"]
    
    if order_request.side == "sell":
        # Check if we have enough base currency
        if base_currency not in balances or balances[base_currency]["free"] < order_request.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient {base_currency} balance")
        
        # Update balance
        balances[base_currency]["free"] -= order_request.amount
        balances[base_currency]["used"] += order_request.amount
    else:
        # Check if we have enough quote currency
        if quote_currency not in balances or balances[quote_currency]["free"] < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient {quote_currency} balance")
        
        # Update balance
        balances[quote_currency]["free"] -= cost
        balances[quote_currency]["used"] += cost
    
    # Create order
    order_id = str(uuid.uuid4())
    timestamp = int(time.time() * 1000)
    
    order = {
        "id": order_id,
        "symbol": symbol,
        "type": order_request.type,
        "side": order_request.side,
        "amount": order_request.amount,
        "price": price,
        "status": "open",
        "filled": 0.0,
        "cost": 0.0,
        "timestamp": timestamp
    }
    
    orders[order_id] = order
    
    # For testing purposes, immediately fill market orders and 50% of limit orders
    if order_request.type == "market" or random.random() < 0.5:
        # Fill order
        fill_amount = order_request.amount
        fill_price = price
        fill_cost = fill_amount * fill_price
        
        # Update order
        order["filled"] = fill_amount
        order["cost"] = fill_cost
        order["status"] = "closed"
        
        # Create trade
        trade_id = str(uuid.uuid4())
        
        trade = {
            "id": trade_id,
            "order_id": order_id,
            "symbol": symbol,
            "side": order_request.side,
            "amount": fill_amount,
            "price": fill_price,
            "cost": fill_cost,
            "timestamp": timestamp
        }
        
        trades.append(trade)
        
        # Update balances
        if order_request.side == "sell":
            # Release used balance
            balances[base_currency]["used"] -= fill_amount
            
            # Add quote currency
            if quote_currency not in balances:
                balances[quote_currency] = {"free": 0.0, "used": 0.0, "total": 0.0}
            
            balances[quote_currency]["free"] += fill_cost
            balances[quote_currency]["total"] += fill_cost
        else:
            # Release used balance
            balances[quote_currency]["used"] -= fill_cost
            
            # Add base currency
            if base_currency not in balances:
                balances[base_currency] = {"free": 0.0, "used": 0.0, "total": 0.0}
            
            balances[base_currency]["free"] += fill_amount
            balances[base_currency]["total"] += fill_amount
    
    return order


@app.get("/api/orders/{order_id}")
def get_order(order_id: str, api_key: str = Header(None)):
    """Get order by ID."""
    simulate_delay()
    
    # Validate API key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Check if order exists
    if order_id not in orders:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    
    return orders[order_id]


@app.get("/api/orders")
def get_orders(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    api_key: str = Header(None)
):
    """Get all orders."""
    simulate_delay()
    
    # Validate API key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Filter orders
    filtered_orders = list(orders.values())
    
    if symbol:
        # Normalize symbol
        symbol = symbol.replace("_", "/")
        filtered_orders = [o for o in filtered_orders if o["symbol"] == symbol]
    
    if status:
        filtered_orders = [o for o in filtered_orders if o["status"] == status]
    
    return {"orders": filtered_orders}


@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str, api_key: str = Header(None)):
    """Cancel an order."""
    simulate_delay()
    
    # Validate API key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Check if order exists
    if order_id not in orders:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    
    # Get order
    order = orders[order_id]
    
    # Check if order can be canceled
    if order["status"] != "open":
        raise HTTPException(status_code=400, detail=f"Cannot cancel order with status: {order['status']}")
    
    # Cancel order
    order["status"] = "canceled"
    
    # Get market data
    symbol = order["symbol"]
    market = markets[symbol]
    
    # Update balances
    base_currency = market["base"]
    quote_currency = market["quote"]
    
    if order["side"] == "sell":
        # Release used balance
        balances[base_currency]["used"] -= (order["amount"] - order["filled"])
        balances[base_currency]["free"] += (order["amount"] - order["filled"])
    else:
        # Release used balance
        cost = (order["amount"] - order["filled"]) * order["price"]
        balances[quote_currency]["used"] -= cost
        balances[quote_currency]["free"] += cost
    
    return order


# Account endpoints
@app.get("/api/balance")
def get_balance(api_key: str = Header(None)):
    """Get account balance."""
    simulate_delay()
    
    # Validate API key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    return {"balances": balances}


@app.get("/api/trades")
def get_trades(
    symbol: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    api_key: str = Header(None)
):
    """Get trades."""
    simulate_delay()
    
    # Validate API key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Filter trades
    filtered_trades = trades
    
    if symbol:
        # Normalize symbol
        symbol = symbol.replace("_", "/")
        filtered_trades = [t for t in filtered_trades if t["symbol"] == symbol]
    
    # Sort by timestamp (newest first)
    filtered_trades = sorted(filtered_trades, key=lambda t: t["timestamp"], reverse=True)
    
    # Apply limit
    filtered_trades = filtered_trades[:limit]
    
    return {"trades": filtered_trades}


# Control endpoints (for testing)
@app.post("/control/reset")
def reset_exchange():
    """Reset exchange data."""
    global markets, tickers, orders, balances, trades
    
    # Reset data
    markets = DEFAULT_MARKETS.copy()
    tickers = DEFAULT_TICKERS.copy()
    orders = {}
    balances = DEFAULT_BALANCES.copy()
    trades = []
    
    logger.info("Reset mock exchange data")
    return {"status": "ok"}


@app.post("/control/set_ticker")
def set_ticker(ticker: Ticker):
    """Set ticker data."""
    # Normalize symbol
    symbol = ticker.symbol.replace("_", "/")
    
    # Validate symbol
    if symbol not in markets:
        raise HTTPException(status_code=404, detail=f"Market not found: {symbol}")
    
    # Update ticker
    tickers[symbol] = ticker.dict()
    
    logger.info(f"Updated ticker for {symbol}")
    return {"status": "ok"}


@app.post("/control/set_balance/{currency}")
def set_balance(currency: str, amount: float):
    """Set balance for a currency."""
    # Update balance
    balances[currency] = {
        "free": amount,
        "used": 0.0,
        "total": amount
    }
    
    logger.info(f"Updated balance for {currency}: {amount}")
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)