from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from decimal import Decimal
from typing import Dict
import uvicorn

from . import PaperTradingExchange
from .config import PaperTradingConfig

app = FastAPI(title="Paper Trading API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize paper trading exchange
config = PaperTradingConfig()
exchange = PaperTradingExchange(config.initial_balances)

@app.get("/balances")
async def get_balances() -> Dict[str, float]:
    """Get current account balances"""
    return {k: float(v) for k, v in exchange.get_balances().items()}

@app.post("/orders")
async def create_order(
    symbol: str,
    side: str,
    amount: float,
    price: float,
    order_type: str = "limit"
) -> Dict:
    """Create a new paper trade order"""
    try:
        return exchange.create_order(
            symbol=symbol,
            side=side,
            amount=Decimal(str(amount)),
            price=Decimal(str(price)),
            order_type=order_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders/{order_id}")
async def get_order(order_id: str) -> Dict:
    """Get order status"""
    if order_id not in exchange.orders:
        raise HTTPException(status_code=404, detail="Order not found")
    return exchange.orders[order_id]

@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "balances": {k: float(v) for k, v in exchange.get_balances().items()},
        "open_orders": len(exchange.orders)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)