from datetime import datetime
from sqlalchemy import Column, String, Enum, Float, DateTime, Boolean
from database.db import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, index=True)
    exchange = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    order_type = Column(Enum("market", "limit", name="order_type"), nullable=False)
    side = Column(Enum("buy", "sell", name="trade_side"), nullable=False)
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Nullable for market orders
    status = Column(Enum("open", "filled", "canceled", name="trade_status"), default="open")
    is_open = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Trade {self.id} {self.symbol} {self.side} {self.amount}>"