"""Test database connection pooling and resilience."""
import pytest
import asyncio
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from database.db import engine, async_session, get_db
from database.models import Trade
from datetime import datetime

@pytest.mark.asyncio
async def test_connection_pool_reuse():
    """Test that connections are properly reused from the pool."""
    async with get_db() as db1:
        # Create a trade
        trade = Trade(
            symbol="BTCUSDT",
            side="BUY",
            price=50000.0,
            quantity=0.1,
            timestamp=datetime.utcnow()
        )
        db1.add(trade)
        await db1.commit()

    # Get another session - should reuse connection from pool
    async with get_db() as db2:
        result = await db2.execute(select(Trade))
        trades = result.scalars().all()
        assert len(trades) == 1
        assert trades[0].symbol == "BTCUSDT"

@pytest.mark.asyncio
async def test_connection_pool_exhaustion():
    """Test behavior when connection pool is exhausted."""
    if engine.pool.__class__.__name__ == "NullPool":
        pytest.skip("Not applicable for NullPool")

    # Exhaust the connection pool
    connections = []
    for _ in range(engine.pool.size() + engine.pool.max_overflow() + 1):
        try:
            conn = await engine.connect()
            connections.append(conn)
        except OperationalError as e:
            assert "TimeoutError" in str(e) or "pool" in str(e).lower()
            break

    # Cleanup
    for conn in connections:
        await conn.close()

@pytest.mark.asyncio
async def test_connection_recycling():
    """Test that connections are properly recycled."""
    if engine.pool.__class__.__name__ == "NullPool":
        pytest.skip("Not applicable for NullPool")

    # Get initial connection info
    async with engine.connect() as conn:
        initial_conn = await conn.get_raw_connection()

    # Simulate connection aging
    engine.pool._pool.queue[0].record["starttime"] -= 4000  # Make connection appear old

    # Get new connection - should recycle the old one
    async with engine.connect() as conn:
        new_conn = await conn.get_raw_connection()
        assert new_conn != initial_conn

@pytest.mark.asyncio
async def test_connection_resilience():
    """Test that connection recovers from errors."""
    # Force a connection error
    async with engine.connect() as conn:
        raw_conn = await conn.get_raw_connection()
        await raw_conn.close()  # Forcefully close the underlying connection

    # Should recover and create new connection
    async with engine.connect() as conn:
        result = await conn.execute(select(1))
        assert result.scalar() == 1

def test_sync_connection_pooling(session):
    """Test sync connection pooling behavior."""
    from sqlalchemy import text

    # Verify connection works
    result = session.execute(text("SELECT 1"))
    assert result.scalar() == 1

    # Test multiple connections
    for _ in range(5):
        session.execute(text("SELECT 1"))