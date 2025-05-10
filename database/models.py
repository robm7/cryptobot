from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .db import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

class Trade(db.Model):
    __tablename__ = 'trades'
    """Model for storing trade information"""
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    trade_type = Column(String(10), nullable=False)  # 'buy' or 'sell'
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    strategy_id = Column(Integer, ForeignKey('strategies.id'))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    profit_loss = Column(Float, default=0.0)
    is_backtest = Column(Boolean, default=False)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=True)

    def __repr__(self):
        return f"<Trade {self.id} {self.symbol} {self.trade_type} {self.amount} @ {self.price}>"

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'trade_type': self.trade_type,
            'amount': self.amount,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'profit_loss': self.profit_loss,
            'is_backtest': self.is_backtest
        }

class Strategy(db.Model):
    __tablename__ = 'strategies'
    """Model for storing strategy configurations"""
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(Text, nullable=False)  # JSON string of parameters
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trades = relationship('Trade', backref='strategy', lazy=True)

    def __repr__(self):
        return f"<Strategy {self.id} {self.name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parameters': json.loads(self.parameters),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    """Model for storing audit trail records"""
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)  # login, config_change, trade, etc.
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Null for system events
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action_details = Column(Text, nullable=False)  # JSON payload
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    status = Column(String(20), nullable=False)  # success, failure, warning
    resource_type = Column(String(50), nullable=True)  # trade, strategy, user, etc.
    resource_id = Column(Integer, nullable=True)  # ID of affected resource

    user = relationship('User', backref='audit_logs')

    def __repr__(self):
        return f"<AuditLog {self.id} {self.event_type} {self.timestamp}>"

    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'action_details': json.loads(self.action_details),
            'ip_address': self.ip_address,
            'status': self.status,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id
        }

class BacktestResult(db.Model):
    __tablename__ = 'backtest_results'
    """Model for storing backtest results"""
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'))
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    return_pct = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    avg_trade_duration = Column(Float, nullable=True)  # in hours
    created_at = Column(DateTime, default=datetime.utcnow)
    trades = relationship('Trade', backref='backtest', lazy=True)

    def __repr__(self):
        return f"<BacktestResult {self.id} {self.symbol} {self.start_date} - {self.end_date}>"

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'return_pct': self.return_pct,
            'total_trades': self.total_trades,
            'win_rate': self.win_rate,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'profit_factor': self.profit_factor,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'avg_trade_duration': self.avg_trade_duration,
            'created_at': self.created_at.isoformat()
        }

class User(db.Model):
    __tablename__ = 'users'
    """Model for user accounts"""
    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    strategies = relationship('Strategy', backref='user', lazy=True)
    trades = relationship('Trade', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.id} {self.email}>"

    def set_password(self, password):
        """Create hashed password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check hashed password"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Return user data as dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }