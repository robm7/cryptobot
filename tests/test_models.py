import pytest
from datetime import datetime, timedelta
from database.models import Trade, Strategy, BacktestResult, User
import threading
from sqlalchemy.exc import IntegrityError

def test_trade_model(session):
    """Test Trade model creation and relationships"""
    # Create test user and strategy
    user = User(email="trade_test@example.com")
    user.set_password("password")
    strategy = Strategy(name="Test Strategy", parameters="{}", user=user)
    
    session.add_all([user, strategy])
    session.commit()

    # Test valid trade creation
    trade = Trade(
        symbol="BTC/USD",
        trade_type="buy",
        amount=0.1,
        price=50000,
        user=user,
        strategy=strategy
    )
    session.add(trade)
    session.commit()

    assert trade.id is not None
    assert trade.timestamp is not None
    assert trade.profit_loss == 0.0
    assert trade.is_backtest is False
    assert trade.to_dict()["symbol"] == "BTC/USD"

    # Test required fields
    with pytest.raises(Exception):
        invalid_trade = Trade(symbol="BTC/USD")  # Missing required fields
        session.add(invalid_trade)
        session.commit()

def test_strategy_model(session):
    """Test Strategy model creation and relationships"""
    user = User(email="strategy@example.com")
    user.set_password("password")
    session.add(user)
    session.commit()

    strategy = Strategy(
        name="Breakout Strategy",
        parameters='{"threshold": 0.05}',
        user=user
    )
    session.add(strategy)
    session.commit()

    assert strategy.id is not None
    assert strategy.created_at is not None
    assert strategy.updated_at is not None
    assert strategy.trades == []

    # Test relationship with trades
    trade = Trade(
        symbol="ETH/USD",
        trade_type="sell",
        amount=1.0,
        price=3000,
        user=user,
        strategy=strategy
    )
    session.add(trade)
    session.commit()

    assert len(strategy.trades) == 1
    assert strategy.trades[0].symbol == "ETH/USD"

def test_backtest_result_model(session):
    """Test BacktestResult model creation and relationships"""
    user = User(email="backtest@example.com")
    user.set_password("password")
    strategy = Strategy(name="Backtest Strategy", parameters="{}", user=user)
    session.add_all([user, strategy])
    session.commit()

    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()

    backtest = BacktestResult(
        strategy_id=strategy.id,
        symbol="BTC/USD",
        timeframe="1d",
        start_date=start_date,
        end_date=end_date,
        initial_capital=10000,
        final_capital=12000,
        return_pct=20.0,
        total_trades=15,
        win_rate=0.6
    )
    session.add(backtest)
    session.commit()

    assert backtest.id is not None
    assert backtest.created_at is not None
    assert backtest.to_dict()["return_pct"] == 20.0

    # Test relationship with trades
    trade = Trade(
        symbol="BTC/USD",
        trade_type="buy",
        amount=0.1,
        price=50000,
        user=user,
        backtest=backtest,
        is_backtest=True
    )
    session.add(trade)
    session.commit()

    assert len(backtest.trades) == 1
    assert backtest.trades[0].is_backtest is True

def test_user_model(session):
    """Test User model creation and authentication"""
    user = User(email="user@example.com")
    user.set_password("securepassword")
    session.add(user)
    session.commit()

    assert user.id is not None
    assert user.check_password("securepassword") is True
    assert user.check_password("wrongpassword") is False
    assert user.to_dict()["email"] == "user@example.com"

    # Test relationship with strategies
    strategy = Strategy(name="User Strategy", parameters="{}", user=user)
    session.add(strategy)
    session.commit()

    assert len(user.strategies) == 1
    assert user.strategies[0].name == "User Strategy"

    # Test unique email constraint
    with pytest.raises(Exception):
        duplicate_user = User(email="user@example.com")
        duplicate_user.set_password("password")
        session.add(duplicate_user)
        session.commit()

def test_transaction_atomicity(session):
    """Test that transactions are atomic (all or nothing)"""
    user = User(email="transaction@example.com")
    user.set_password("password")
    session.add(user)
    
    # This should fail due to missing required fields
    invalid_trade = Trade(symbol="BTC/USD")
    session.add(invalid_trade)
    
    with pytest.raises(Exception):
        session.commit()
    
    # Verify user wasn't persisted due to transaction rollback
    assert session.query(User).filter_by(email="transaction@example.com").first() is None

def test_concurrent_updates(session):
    """Test handling of concurrent updates to same record"""
    user = User(email="concurrent@example.com")
    user.set_password("password")
    session.add(user)
    session.commit()
    
    def update_user(user_id, new_email, session_factory):
        """Thread worker to update user"""
        session = session_factory()
        try:
            user = session.query(User).get(user_id)
            user.email = new_email
            session.commit()
        finally:
            session.close()
    
    # Simulate concurrent updates using session factory
    from database.db import session_factory
    t1 = threading.Thread(target=update_user,
                         args=(user.id, "email1@example.com", session_factory))
    t2 = threading.Thread(target=update_user,
                         args=(user.id, "email2@example.com", session_factory))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    # Verify one update succeeded and the other was lost (last write wins)
    updated_user = session.query(User).get(user.id)
    assert updated_user.email in ["email1@example.com", "email2@example.com"]

def test_session_isolation(session, session_factory):
    """Test that sessions are isolated from uncommitted changes"""
    user = User(email="isolation@example.com")
    user.set_password("password")
    session.add(user)
    
    # Create second isolated session using fixture
    other_session = session_factory()
    
    try:
        # Should not see uncommitted user in other session
        assert other_session.query(User).filter_by(email="isolation@example.com").first() is None
        
        session.commit()
        
        # Now should be visible
        assert other_session.query(User).filter_by(email="isolation@example.com").first() is not None
    finally:
        other_session.close()