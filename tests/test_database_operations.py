"""Test database operations using test fixtures."""
import json
import pytest
import time
from sqlalchemy import select, inspect
from database.models import Trade, Strategy, User
from database.db import get_db, async_session

# Using the async_db fixture from conftest.py instead
@pytest.fixture(autouse=True)
def cleanup_after_tests(session):
    """Clean up database after each test."""
    yield
    try:
        # Clear all tables
        session.query(Trade).delete()
        session.query(Strategy).delete()
        session.query(User).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        pytest.fail(f"Cleanup failed: {str(e)}")

def test_trade_crud(session):
    """Test CRUD operations for Trade model."""
    try:
        # Create
        trade = Trade(
            symbol="BTCUSDT",
            trade_type="buy",
            price=50000.0,
            amount=0.1,
            user_id=1
        )
        session.add(trade)
        session.commit()
        
        # Verify create
        fetched = session.query(Trade).filter_by(symbol="BTCUSDT").first()
        assert fetched is not None, "Trade creation failed"
        assert fetched.symbol == "BTCUSDT"
        
        # Update
        fetched.price = 51000.0
        session.commit()
        
        # Verify update
        updated = session.query(Trade).filter_by(symbol="BTCUSDT").first()
        assert updated.price == 51000.0, "Trade update failed"
        
        # Delete
        session.delete(updated)
        session.commit()
        
        # Verify delete
        deleted = session.query(Trade).filter_by(symbol="BTCUSDT").first()
        assert deleted is None, "Trade deletion failed"
        
    except Exception as e:
        session.rollback()
        pytest.fail(f"Trade CRUD test failed: {str(e)}")

def test_strategy_crud(session):
    """Test CRUD operations for Strategy model."""
    try:
        import json
        # Create
        strategy = Strategy(
            name="Mean Reversion",
            description="Basic mean reversion strategy",
            parameters=json.dumps({"lookback": 14}),
            user_id=1
        )
        session.add(strategy)
        session.commit()
        
        # Verify create
        fetched = session.query(Strategy).filter_by(name="Mean Reversion").first()
        assert fetched is not None, "Strategy creation failed"
        assert fetched.name == "Mean Reversion"
        
        # Update
        fetched.parameters = json.dumps({"lookback": 20})
        session.commit()

        # Verify update
        updated = session.query(Strategy).filter_by(name="Mean Reversion").first()
        assert json.loads(updated.parameters)["lookback"] == 20, "Strategy update failed"
        
        # Delete
        session.delete(updated)
        session.commit()
        
        # Verify delete
        deleted = session.query(Strategy).filter_by(name="Mean Reversion").first()
        assert deleted is None, "Strategy deletion failed"
        
    except Exception as e:
        session.rollback()
        pytest.fail(f"Strategy CRUD test failed: {str(e)}")

def test_user_crud(session):
    """Test CRUD operations for User model."""
    try:
        # Create
        user = User(
            email="test@example.com",
            password_hash="hashed_test_password"
        )
        session.add(user)
        session.commit()
        
        # Verify create
        fetched = session.query(User).filter_by(email="test@example.com").first()
        assert fetched is not None, "User creation failed"
        assert fetched.email == "test@example.com"
        
        # Update
        fetched.email = "updated@example.com"
        session.commit()
        
        # Verify update
        updated = session.query(User).filter_by(email="updated@example.com").first()
        assert updated.email == "updated@example.com", "User update failed"
        
        # Delete
        session.delete(updated)
        session.commit()
        
        # Verify delete
        deleted = session.query(User).filter_by(email="updated@example.com").first()
        assert deleted is None, "User deletion failed"
        
    except Exception as e:
        session.rollback()
        pytest.fail(f"User CRUD test failed: {str(e)}")

def test_connection_performance(session):
    """Test database connection performance."""
    start = time.time()
    
    # Execute simple query 100 times to test pooling
    for _ in range(100):
        session.execute(select(1)).scalar()
    
    duration = time.time() - start
    assert duration < 1.0, "Database operations too slow"
    
    # Skip pool verification if using SQLite in-memory db
    if hasattr(session.bind, 'url') and not session.bind.url.database == ':memory:':
        pool = session.bind.pool
        assert pool.checkedin() > 0, "No connections in pool"
        assert pool.checkedout() > 0, "No connections checked out"
        assert pool.size() <= 10, "Pool size exceeded max"

@pytest.mark.asyncio
async def test_async_trade_crud(async_db):
    """Test async CRUD operations for Trade model."""
    async for session in async_db:
        # Create
        trade = Trade(
            symbol="BTCUSDT",
            trade_type="buy",
            price=50000.0,
            amount=0.1,
            user_id=1
        )
        # Use the session directly
        session.add(trade)
        await session.commit()
    
        # Read
        result = await session.execute(select(Trade).filter_by(symbol="BTCUSDT"))
        fetched = result.scalars().first()
        assert fetched is not None, "Trade creation failed"
        assert fetched.symbol == "BTCUSDT"
        
        # Update
        fetched.price = 51000.0
        await session.commit()
        
        # Verify update
        result = await session.execute(select(Trade).filter_by(symbol="BTCUSDT"))
        updated = result.scalars().first()
        assert updated.price == 51000.0, "Trade update failed"
        
        # Delete
        session.delete(updated)
        await session.commit()
        
        # Verify delete
        result = await session.execute(select(Trade).filter_by(symbol="BTCUSDT"))
        assert result.scalars().first() is None, "Trade deletion failed"

@pytest.mark.asyncio
async def test_async_strategy_crud(async_db):
    """Test async CRUD operations for Strategy model."""
    async for session in async_db:
        # Create
        strategy = Strategy(
            name="Async Strategy",
            description="Test async strategy",
            parameters=json.dumps({"param": "value"}),
            user_id=1
        )
        # Use the session directly
        session.add(strategy)
        await session.commit()
        
        # Read
        result = await session.execute(select(Strategy).filter_by(name="Async Strategy"))
        fetched = result.scalars().first()
        assert fetched is not None, "Strategy creation failed"
        assert fetched.name == "Async Strategy"
            
        # Cleanup
        session.delete(fetched)
        await session.commit()

@pytest.mark.asyncio
async def test_async_user_crud(async_db):
    """Test async CRUD operations for User model."""
    async for session in async_db:
        # Create
        user = User(
            email="async@example.com",
            password_hash="hashed_test_password"
        )
        # Use the session directly
        session.add(user)
        await session.commit()
        
        # Read
        result = await session.execute(select(User).filter_by(email="async@example.com"))
        fetched = result.scalars().first()
        assert fetched is not None, "User creation failed"
        assert fetched.email == "async@example.com"
            
        # Cleanup
        session.delete(fetched)
        await session.commit()

def test_crud_strategy(session):
    """Test CRUD operations for Strategy model."""
    from database.models import Strategy, User
    
    # Create user first
    user = User(email="strategy_crud@example.com")
    user.set_password("password")
    session.add(user)
    session.commit()
    
    # Create
    strategy = Strategy(
        name="Test Strategy",
        parameters='{"param": "value"}',
        user_id=user.id
    )
    session.add(strategy)
    session.commit()
    
    # Read
    fetched = session.query(Strategy).filter_by(name="Test Strategy").first()
    assert fetched.parameters == '{"param": "value"}'
    
    # Update
    fetched.parameters = '{"new_param": "new_value"}'
    session.commit()
    
    # Verify update
    updated = session.query(Strategy).filter_by(name="Test Strategy").first()
    assert updated.parameters == '{"new_param": "new_value"}'
    
    # Delete
    session.delete(fetched)
    session.commit()
    
    # Verify delete
    deleted = session.query(Strategy).filter_by(name="Test Strategy").first()
    assert deleted is None

def test_crud_user(session):
    """Test CRUD operations for User model."""
    from database.models import User
    
    # Create
    user = User(email="user_crud@example.com")
    user.set_password("password")
    session.add(user)
    session.commit()
    
    # Read
    fetched = session.query(User).filter_by(email="user_crud@example.com").first()
    assert fetched.check_password("password") is True
    
    # Update
    fetched.email = "updated@example.com"
    session.commit()
    
    # Verify update
    updated = session.query(User).filter_by(email="updated@example.com").first()
    assert updated is not None
    
    # Delete
    session.delete(fetched)
    session.commit()
    
    # Verify delete
    deleted = session.query(User).filter_by(email="updated@example.com").first()
    assert deleted is None

def test_connection_pooling(session):
    """Test database connection pooling functionality."""
    from sqlalchemy import inspect
    
    # Skip if using SQLite in-memory db
    if not hasattr(session.bind, 'url') or session.bind.url.database == ':memory:':
        pytest.skip("Pooling tests not applicable for SQLite in-memory db")
    
    # Get connection info
    inspector = inspect(session.bind)
    pool = session.bind.pool
    
    # Verify pool stats
    assert pool.checkedin() > 0, "No connections in pool"
    assert pool.checkedout() > 0, "No connections checked out"
    
    # Test connection reuse
    conn1 = session.bind.connect()
    conn2 = session.bind.connect()
    
    assert conn1.connection.connection != conn2.connection.connection, "Connections should be different"
    
    # Cleanup
    conn1.close()
    conn2.close()
    
    # Verify connections returned to pool
    assert pool.checkedin() >= 2, "Connections not returned to pool"

def test_db_connection_verification():
    """Test database connection verification."""
    from database.db import verify_db_connection
    
    # Should pass with valid connection
    verify_db_connection()
    
    # Test with invalid URL
    import os
    from unittest.mock import patch
    
    with patch.dict(os.environ, {"DATABASE_URL": "invalid://url"}):
        with pytest.raises(ConnectionError):
            verify_db_connection()

def test_database_url_validation():
    """Test database URL validation for all supported protocols."""
    from database.db import _get_database_url
    from pathlib import Path
    
    # Test valid protocols
    test_cases = [
        ("sqlite:///absolute.db", True),
        ("sqlite+aiosqlite:///absolute.db", True),
        ("postgresql://user:pass@localhost/db", True),
        ("postgres://user:pass@localhost/db", True),
        ("mysql://user:pass@localhost/db", True),
        ("mysql+pymysql://user:pass@localhost/db", True),
        ("invalid://url", False),
        ("missing_protocol", False),
    ]
    
    for url, should_pass in test_cases:
        if should_pass:
            # Handle SQLite special case
            if url.startswith("sqlite"):
                abs_path = str(Path("database/test.db").absolute())
                url = url.replace("absolute.db", abs_path)
            
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                result = _get_database_url()
                assert url.split("://")[0].lower() in result.lower()
        else:
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                with pytest.raises(ValueError) as excinfo:
                    _get_database_url()
                assert "must use one of these protocols" in str(excinfo.value)
    
    # Test SQLite relative path conversion
    with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///relative.db"}):
        result = _get_database_url()
        assert "relative.db" not in result  # Should be converted to absolute path
        assert Path(result.split("///")[-1]).is_absolute()
        
    # Test invalid path cases
    invalid_paths = [
        ("sqlite:///", "Empty path"),
        ("sqlite:///invalid/dir/db.db", "Non-existent parent directory"),
        ("sqlite:///existing_dir", "Path is directory not file")
    ]
    
    for url, desc in invalid_paths:
        with patch.dict(os.environ, {"DATABASE_URL": url}):
            if desc == "Path is directory not file":
                # Create test directory first
                test_dir = Path("tests/test_dir")
                test_dir.mkdir(exist_ok=True)
                try:
                    with pytest.raises(ValueError, match="exists but is not a file"):
                        _get_database_url()
                finally:
                    test_dir.rmdir()
            else:
                with pytest.raises(ValueError):
                    _get_database_url()

def test_test_db_configuration():
    """Test test database configuration options."""
    from database.db import _get_sync_db_url, _get_database_url
    
    # Test in-memory default
    with patch.dict(os.environ, {"TESTING": "1"}, clear=True):
        assert _get_sync_db_url() == "sqlite:///:memory:"
        assert _get_database_url() == "sqlite+aiosqlite:///:memory:"
    
    # Test with custom test db path (relative and absolute)
    test_paths = [
        "tests/test.db",  # Relative path
        str(Path("tests/test.db").absolute())  # Absolute path
    ]
    
    for test_path in test_paths:
        with patch.dict(os.environ, {"TESTING": "1", "TEST_DB_PATH": test_path}):
            sync_url = _get_sync_db_url()
            async_url = _get_database_url()
            
            # Verify both URLs point to same absolute path
            sync_path = Path(sync_url.split("///")[-1]).resolve()
            async_path = Path(async_url.split("///")[-1]).resolve()
            assert sync_path == async_path
            
            # Verify path exists or can be created
            assert sync_path.parent.exists()
            if not sync_path.exists():
                sync_path.touch()
                sync_path.unlink()