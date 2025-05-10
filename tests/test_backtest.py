import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from backtest.main import app
from backtest.models.backtest import Backtest
from database.db import async_session, init_db
import asyncio

@pytest.fixture
async def db_session():
    await init_db()
    async with async_session() as session:
        yield session

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def sample_backtest(db_session: AsyncSession):
    backtest = Backtest(
        strategy_id=1,
        symbol="BTC/USDT",
        timeframe="1d",
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow(),
        parameters={"param1": "value1"},
        status="completed",
        results={
            "profit": 0.15,
            "max_drawdown": 0.05,
            "sharpe_ratio": 1.8,
            "win_rate": 0.65
        },
        completed_at=datetime.utcnow()
    )
    db_session.add(backtest)
    await db_session.commit()
    return backtest

@pytest.mark.asyncio
async def test_start_backtest(client: TestClient, db_session: AsyncSession):
    response = client.post("/api/backtest/start", json={
        "strategy_id": 1,
        "symbol": "BTC/USDT",
        "timeframe": "1d",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "parameters": {"param1": "value1"}
    })
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["strategy_id"] == 1
    
    # Verify backtest was created in database
    result = await db_session.execute(select(Backtest).where(Backtest.id == data["id"]))
    assert result.scalars().first() is not None

@pytest.mark.asyncio
async def test_get_backtest_status(client: TestClient, sample_backtest: Backtest):
    response = client.get(f"/api/backtest/status/{sample_backtest.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_backtest.id
    assert data["status"] == "completed"

@pytest.mark.asyncio
async def test_get_backtest_results(client: TestClient, sample_backtest: Backtest):
    response = client.get(f"/api/backtest/results/{sample_backtest.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["results"]["profit"] == 0.15

@pytest.mark.asyncio
async def test_get_performance_metrics(client: TestClient, sample_backtest: Backtest):
    response = client.get(f"/api/backtest/performance/{sample_backtest.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["profit"] == 0.15
    assert data["sharpe_ratio"] == 1.8

@pytest.mark.asyncio
async def test_not_found_errors(client: TestClient):
    # Test status for non-existent backtest
    response = client.get("/api/backtest/status/999")
    assert response.status_code == 404
    
    # Test results for non-existent backtest
    response = client.get("/api/backtest/results/999")
    assert response.status_code == 404
    
    # Test performance for non-existent backtest
    response = client.get("/api/backtest/performance/999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_results_not_ready(client: TestClient, db_session: AsyncSession):
    # Create a pending backtest
    backtest = Backtest(
        strategy_id=1,
        symbol="BTC/USDT",
        timeframe="1d",
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow(),
        parameters={"param1": "value1"},
        status="pending"
    )
    db_session.add(backtest)
    await db_session.commit()
    
    # Test results when not completed
    response = client.get(f"/api/backtest/results/{backtest.id}")
    assert response.status_code == 400