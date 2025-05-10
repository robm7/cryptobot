from database.models import User
from auth.auth_service import create_token_pair
from database.db import db

import pytest
import logging
from unittest.mock import MagicMock
from app import create_app
import os

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for tests."""
    # Configure test app with in-memory database
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    app.config['REDIS_HOST'] = 'localhost'
    app.config['REDIS_PORT'] = 6379
    
    # Initialize database and register routes
    from database.db import db, init_db
    from api.routes import register_api_routes
    
    # Initialize database first - ensure proper binding
    db.init_app(app)  # Initialize SQLAlchemy first
    
    with app.app_context():
        # Then create tables
        db.create_all()
        
        # Finally initialize async components
        init_db()
    
    # Then register routes
    register_api_routes(app)
    
    try:
        # Verify tables exist
        with app.app_context():
            inspector = db.inspect(db.engine)
            sync_tables = inspector.get_table_names()
            required_tables = {'users', 'trades', 'strategies', 'backtest_results'}
            if not required_tables.issubset(sync_tables):
                raise RuntimeError(f"Missing tables: {required_tables - set(sync_tables)}")
            
        # Create test user
        with app.app_context():
            test_user = User(email='test@example.com')
            test_user.set_password('testpassword')
            db.session.add(test_user)
            db.session.commit()
            
            # Verify user was created
            if not User.query.filter_by(email='test@example.com').first():
                raise RuntimeError("Test user creation failed")
                
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        raise RuntimeError(f"Database setup failed: {str(e)}")
    
    # Mock Redis
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    mock_redis.set.return_value = True
    mock_redis.incr.return_value = 1
    mock_redis.delete.return_value = True
    
    # Patch auth service Redis
    from auth import auth_service
    auth_service.get_redis = lambda: mock_redis
    
    yield app, test_user, mock_redis
    
    # Clean up
    with app.app_context():
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    flask_app, _, _ = app
    flask_app.logger.setLevel(logging.DEBUG)
    return flask_app.test_client()

@pytest.fixture
def auth_headers(app):
    """Generate JWT auth headers for test user"""
    flask_app, test_user, _ = app
    if not test_user:
        raise RuntimeError("Test user not found - check test setup")
    
    with flask_app.app_context():
        token_pair = create_token_pair(test_user)
        access_token = token_pair['access_token']
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

@pytest.fixture
def session(app):
    """Creates a new database session for a test."""
    flask_app, _, _ = app
    with flask_app.app_context():
        # Ensure session is bound to engine
        if not hasattr(db.session.bind, 'engine'):
            db.session.bind = db.engine
        yield db.session
        db.session.rollback()
        db.session.expire_all()

@pytest.fixture
def test_user(app):
    """Get the test user"""
    _, test_user, _ = app
    # Create new session to ensure we see committed data
    with app[0].app_context():
        db.session.expire_all()
    return test_user

@pytest.fixture
def mock_redis(app):
    """Get the mock Redis instance"""
    _, _, mock_redis = app
    return mock_redis

@pytest.fixture
async def async_db():
    """Async database session fixture with proper test isolation."""
    from database.db import get_db, engine, Base
    from sqlalchemy.ext.asyncio import AsyncSession
    from database.models import User, Trade, Strategy, BacktestResult
    from sqlalchemy import MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
    
    # Ensure all tables exist for the async database
    metadata = MetaData()
    
    # Define tables manually to ensure they match the Flask-SQLAlchemy models
    users = Table(
        'users', metadata,
        Column('id', Integer, primary_key=True),
        Column('email', String(120), unique=True, nullable=False),
        Column('password_hash', String(256), nullable=False),
        Column('created_at', DateTime),
        Column('updated_at', DateTime)
    )
    
    strategies = Table(
        'strategies', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False),
        Column('description', Text),
        Column('parameters', Text, nullable=False),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('created_at', DateTime),
        Column('updated_at', DateTime)
    )
    
    trades = Table(
        'trades', metadata,
        Column('id', Integer, primary_key=True),
        Column('symbol', String(20), nullable=False),
        Column('trade_type', String(10), nullable=False),
        Column('amount', Float, nullable=False),
        Column('price', Float, nullable=False),
        Column('timestamp', DateTime),
        Column('strategy_id', Integer, ForeignKey('strategies.id')),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('profit_loss', Float),
        Column('is_backtest', Boolean),
        Column('backtest_id', Integer, ForeignKey('backtest_results.id'))
    )
    
    backtest_results = Table(
        'backtest_results', metadata,
        Column('id', Integer, primary_key=True),
        Column('strategy_id', Integer, ForeignKey('strategies.id')),
        Column('symbol', String(20), nullable=False),
        Column('timeframe', String(10), nullable=False),
        Column('start_date', DateTime, nullable=False),
        Column('end_date', DateTime, nullable=False),
        Column('initial_capital', Float, nullable=False),
        Column('final_capital', Float, nullable=False),
        Column('return_pct', Float, nullable=False),
        Column('total_trades', Integer, nullable=False),
        Column('win_rate', Float, nullable=False),
        Column('sharpe_ratio', Float),
        Column('max_drawdown', Float),
        Column('profit_factor', Float),
        Column('avg_win', Float),
        Column('avg_loss', Float),
        Column('avg_trade_duration', Float),
        Column('created_at', DateTime)
    )
    
    # Create all tables in the async database
    async with engine.begin() as conn:
        await conn.run_sync(lambda conn: metadata.create_all(conn))
    
    # Use the existing context manager from db.py
    async with get_db() as session:
        yield session