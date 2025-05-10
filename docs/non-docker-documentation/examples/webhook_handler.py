"""
Custom Webhook Handler Example

This example demonstrates how to create a custom webhook handler for Cryptobot.
The webhook handler processes incoming alerts from TradingView and executes trades.
"""

from cryptobot.api import WebhookHandler
from cryptobot.models import Order, Position
from cryptobot.enums import OrderType, OrderSide, TimeInForce
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import hmac
import hashlib
import json
import logging
import time
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class TradingViewAlert(BaseModel):
    """Model for TradingView webhook alerts."""
    
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTCUSDT')")
    exchange: str = Field(..., description="Exchange name (e.g., 'binance')")
    action: str = Field(..., description="Action to take (buy, sell, close)")
    price: float = Field(..., description="Current price")
    strategy: str = Field(..., description="Strategy name")
    timeframe: str = Field(..., description="Chart timeframe")
    volume: Optional[float] = Field(None, description="Trade volume (optional)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price (optional)")
    take_profit: Optional[float] = Field(None, description="Take profit price (optional)")
    risk_percent: Optional[float] = Field(None, description="Risk percentage (optional)")
    message: Optional[str] = Field(None, description="Additional message")
    timestamp: Optional[int] = Field(None, description="Alert timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "exchange": "binance",
                "action": "buy",
                "price": 50000.0,
                "strategy": "SuperTrend",
                "timeframe": "1h",
                "volume": 0.1,
                "stop_loss": 49000.0,
                "take_profit": 52000.0,
                "risk_percent": 1.0,
                "message": "SuperTrend buy signal",
                "timestamp": 1625097600000
            }
        }


class TradingViewWebhookHandler(WebhookHandler):
    """
    Custom webhook handler for TradingView alerts.
    
    This handler processes incoming alerts from TradingView and executes trades
    based on the alert parameters.
    """
    
    def __init__(self):
        """Initialize the TradingView webhook handler."""
        super().__init__(name="tradingview_webhook", version="1.0.0")
        self.secret = "your-webhook-secret"  # Replace with your actual secret
        self.max_risk_percent = 2.0  # Maximum risk percentage per trade
        self.default_risk_percent = 1.0  # Default risk percentage if not specified
        self.default_volume = 0.01  # Default volume if not specified and can't calculate
        
    def setup(self):
        """Set up the webhook handler routes."""
        router = APIRouter(prefix="/webhooks", tags=["webhooks"])
        
        @router.post("/tradingview")
        async def tradingview_webhook(
            request: Request,
            alert: TradingViewAlert,
            x_signature: Optional[str] = Header(None)
        ):
            """
            Process TradingView webhook alerts.
            
            Args:
                request: The FastAPI request object
                alert: The TradingView alert data
                x_signature: The HMAC signature for verification
                
            Returns:
                dict: Response with status and message
            """
            # Verify webhook signature if provided
            if x_signature:
                if not self.verify_signature(alert.dict(), x_signature):
                    logger.warning(f"Invalid signature for alert: {alert.symbol}")
                    raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Log the incoming alert
            logger.info(f"Received TradingView alert: {alert.dict()}")
            
            try:
                # Process the alert
                result = await self.process_alert(alert)
                
                # Return success response
                return {
                    "status": "success",
                    "message": f"Processed {alert.action} signal for {alert.symbol}",
                    "result": result
                }
            except Exception as e:
                logger.error(f"Error processing alert: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        # Add the router to the handler
        self.add_router(router)
    
    async def process_alert(self, alert: TradingViewAlert) -> Dict[str, Any]:
        """
        Process the TradingView alert and execute the appropriate action.
        
        Args:
            alert: The TradingView alert data
            
        Returns:
            dict: Result of the action
        """
        # Normalize symbol format if needed
        symbol = self.normalize_symbol(alert.symbol, alert.exchange)
        
        # Get account balance
        account = await self.services.trade.get_account(alert.exchange)
        balance = account.balance
        
        # Calculate position size if not provided
        quantity = alert.volume
        if not quantity and alert.action in ["buy", "sell"]:
            quantity = self.calculate_position_size(
                alert.exchange,
                symbol,
                alert.price,
                alert.stop_loss,
                alert.risk_percent or self.default_risk_percent,
                balance
            )
        
        # Execute the appropriate action
        if alert.action == "buy":
            return await self.execute_buy(alert, symbol, quantity)
        elif alert.action == "sell":
            return await self.execute_sell(alert, symbol, quantity)
        elif alert.action == "close":
            return await self.execute_close(alert, symbol)
        else:
            raise ValueError(f"Unknown action: {alert.action}")
    
    async def execute_buy(self, alert: TradingViewAlert, symbol: str, quantity: float) -> Dict[str, Any]:
        """
        Execute a buy order based on the alert.
        
        Args:
            alert: The TradingView alert data
            symbol: The normalized symbol
            quantity: The quantity to buy
            
        Returns:
            dict: Order result
        """
        logger.info(f"Executing buy order for {symbol}, quantity: {quantity}")
        
        # Check if we already have an open position
        position = await self.services.trade.get_position(alert.exchange, symbol)
        if position and position.side == "long" and position.quantity > 0:
            logger.warning(f"Already have a long position for {symbol}, skipping buy")
            return {"status": "skipped", "reason": "position_exists", "position": position.dict()}
        
        # Create the order
        order = await self.services.trade.create_order(
            exchange=alert.exchange,
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=quantity,
            time_in_force=TimeInForce.GTC
        )
        
        # Set stop loss and take profit if provided
        if order.status == "filled" and (alert.stop_loss or alert.take_profit):
            await self.set_exit_orders(alert, symbol, order)
        
        return {"status": "success", "order": order.dict()}
    
    async def execute_sell(self, alert: TradingViewAlert, symbol: str, quantity: float) -> Dict[str, Any]:
        """
        Execute a sell order based on the alert.
        
        Args:
            alert: The TradingView alert data
            symbol: The normalized symbol
            quantity: The quantity to sell
            
        Returns:
            dict: Order result
        """
        logger.info(f"Executing sell order for {symbol}, quantity: {quantity}")
        
        # Check if we already have an open position
        position = await self.services.trade.get_position(alert.exchange, symbol)
        if position and position.side == "short" and position.quantity > 0:
            logger.warning(f"Already have a short position for {symbol}, skipping sell")
            return {"status": "skipped", "reason": "position_exists", "position": position.dict()}
        
        # Create the order
        order = await self.services.trade.create_order(
            exchange=alert.exchange,
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            quantity=quantity,
            time_in_force=TimeInForce.GTC
        )
        
        # Set stop loss and take profit if provided
        if order.status == "filled" and (alert.stop_loss or alert.take_profit):
            await self.set_exit_orders(alert, symbol, order)
        
        return {"status": "success", "order": order.dict()}
    
    async def execute_close(self, alert: TradingViewAlert, symbol: str) -> Dict[str, Any]:
        """
        Close an existing position based on the alert.
        
        Args:
            alert: The TradingView alert data
            symbol: The normalized symbol
            
        Returns:
            dict: Order result
        """
        logger.info(f"Closing position for {symbol}")
        
        # Check if we have an open position
        position = await self.services.trade.get_position(alert.exchange, symbol)
        if not position or position.quantity == 0:
            logger.warning(f"No open position for {symbol}, skipping close")
            return {"status": "skipped", "reason": "no_position"}
        
        # Close the position
        order = await self.services.trade.close_position(
            exchange=alert.exchange,
            symbol=symbol
        )
        
        return {"status": "success", "order": order.dict()}
    
    async def set_exit_orders(self, alert: TradingViewAlert, symbol: str, entry_order: Order) -> None:
        """
        Set stop loss and take profit orders for an entry order.
        
        Args:
            alert: The TradingView alert data
            symbol: The normalized symbol
            entry_order: The entry order
        """
        # Set stop loss if provided
        if alert.stop_loss:
            stop_side = OrderSide.SELL if entry_order.side == OrderSide.BUY else OrderSide.BUY
            await self.services.trade.create_order(
                exchange=alert.exchange,
                symbol=symbol,
                order_type=OrderType.STOP_LOSS,
                side=stop_side,
                quantity=entry_order.filled_quantity,
                price=alert.stop_loss,
                time_in_force=TimeInForce.GTC
            )
        
        # Set take profit if provided
        if alert.take_profit:
            tp_side = OrderSide.SELL if entry_order.side == OrderSide.BUY else OrderSide.BUY
            await self.services.trade.create_order(
                exchange=alert.exchange,
                symbol=symbol,
                order_type=OrderType.LIMIT,
                side=tp_side,
                quantity=entry_order.filled_quantity,
                price=alert.take_profit,
                time_in_force=TimeInForce.GTC
            )
    
    def calculate_position_size(
        self,
        exchange: str,
        symbol: str,
        price: float,
        stop_loss: Optional[float],
        risk_percent: float,
        balance: float
    ) -> float:
        """
        Calculate position size based on risk percentage and stop loss.
        
        Args:
            exchange: The exchange name
            symbol: The trading pair symbol
            price: The current price
            stop_loss: The stop loss price
            risk_percent: The risk percentage
            balance: The account balance
            
        Returns:
            float: The calculated position size
        """
        # Cap risk percentage at maximum
        risk_percent = min(risk_percent, self.max_risk_percent)
        
        # Calculate risk amount
        risk_amount = balance * (risk_percent / 100)
        
        # If stop loss is provided, calculate position size based on risk
        if stop_loss:
            # Calculate stop loss distance
            if price > stop_loss:  # Long position
                stop_distance = price - stop_loss
            else:  # Short position
                stop_distance = stop_loss - price
            
            # Calculate position size
            if stop_distance > 0:
                position_size_in_quote = risk_amount / (stop_distance / price)
                position_size = position_size_in_quote / price
                return position_size
        
        # If no stop loss or calculation failed, use default volume
        logger.warning(f"Using default volume for {symbol}: {self.default_volume}")
        return self.default_volume
    
    def normalize_symbol(self, symbol: str, exchange: str) -> str:
        """
        Normalize the symbol format for the specified exchange.
        
        Args:
            symbol: The symbol to normalize
            exchange: The exchange name
            
        Returns:
            str: The normalized symbol
        """
        # Remove spaces and convert to uppercase
        symbol = symbol.replace(" ", "").upper()
        
        # Handle specific exchange formats
        if exchange.lower() == "binance":
            # Binance uses symbols without separator
            return symbol
        elif exchange.lower() == "kraken":
            # Kraken uses symbols with /
            if "/" not in symbol:
                parts = []
                # Try to split at common boundaries
                for pair in ["USD", "USDT", "BTC", "ETH"]:
                    if pair in symbol:
                        parts = [symbol.replace(pair, ""), pair]
                        break
                
                if parts:
                    symbol = f"{parts[0]}/{parts[1]}"
        
        return symbol
    
    def verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """
        Verify the HMAC signature of the webhook data.
        
        Args:
            data: The webhook data
            signature: The provided signature
            
        Returns:
            bool: True if the signature is valid, False otherwise
        """
        # Create message from data
        message = json.dumps(data, sort_keys=True).encode()
        
        # Calculate expected signature
        expected_signature = hmac.new(
            self.secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)


# Register the webhook handler with Cryptobot
def register():
    """Register the webhook handler with the system."""
    return TradingViewWebhookHandler()


# Example usage
if __name__ == "__main__":
    # This code would be used for testing the webhook handler locally
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI()
    
    # Create webhook handler
    handler = TradingViewWebhookHandler()
    
    # Set up routes
    handler.setup()
    
    # Add routes to app
    app.include_router(handler.router)
    
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)