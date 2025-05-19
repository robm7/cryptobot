import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # Added import
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

@pytest.mark.asyncio
async def test_optimize_strategy_parameters_includes_new_metrics(client: TestClient):
    """
    Test that the /optimize endpoint returns PerformanceMetrics
    including sortino_ratio and calmar_ratio.
    """
    optimization_request_payload = {
        "strategy_name": "TestStrategy",
        "parameter_ranges": [
            {"name": "param1", "start_value": 1.0, "end_value": 5.0, "step": 1.0},
            {"name": "param2", "start_value": 0.1, "end_value": 0.5, "step": 0.1}
        ],
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "start_date": "2023-01-01T00:00:00Z",
        "end_date": "2023-01-31T23:59:59Z"
    }
    response = client.post("/api/backtest/optimize", json=optimization_request_payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert len(data["results"]) > 0  # Expecting multiple simulation runs
    
    for run_result in data["results"]:
        assert "metrics" in run_result
        metrics = run_result["metrics"]
        assert "sortino_ratio" in metrics
        assert "calmar_ratio" in metrics
        assert isinstance(metrics["sortino_ratio"], float)
        assert isinstance(metrics["calmar_ratio"], float)
        # We can't assert specific dummy values as they are random,
        # but checking type and presence is sufficient for this test.

@pytest.mark.asyncio
async def test_run_walk_forward_analysis_success(client: TestClient):
    """Test successful walk-forward analysis run."""
    request_payload = {
        "strategy_name": "TestStrategyWF",
        "parameter_ranges": [
            {"name": "param1", "start_value": 10.0, "end_value": 20.0, "step": 5.0}, # 10, 15, 20 (3 values)
            {"name": "param2", "start_value": 0.1, "end_value": 0.2, "step": 0.1}    # 0.1, 0.2 (2 values) -> 3*2=6 combos
        ],
        "symbol": "ETH/USDT",
        "timeframe": "4h",
        "total_start_date": "2023-01-01T00:00:00Z",
        "total_end_date": "2023-03-31T23:59:59Z", # Approx 90 days
        "in_sample_period_days": 30,
        "out_of_sample_period_days": 15,
        # num_folds will be calculated: 90 / (30+15) = 90 / 45 = 2 folds
    }
    response = client.post("/api/backtest/walkforward", json=request_payload)
    assert response.status_code == 200
    data = response.json()

    assert "walk_forward_id" in data
    assert data["strategy_name"] == "TestStrategyWF"
    assert len(data["fold_results"]) == 2 # Expect 2 folds

    for fold_result in data["fold_results"]:
        assert "fold_number" in fold_result
        assert "in_sample_start_date" in fold_result
        assert "out_of_sample_metrics" in fold_result
        assert "optimized_parameters" in fold_result
        # Each optimization run within a fold should have 6 combinations
        assert len(fold_result["in_sample_optimization_results"]) >= 1 # Could be 6 if all params valid
        # Check if metrics are present in out_of_sample_metrics
        assert "sharpe_ratio" in fold_result["out_of_sample_metrics"]
    
    assert "aggregated_metrics" in data
    assert "sharpe_ratio" in data["aggregated_metrics"]

@pytest.mark.asyncio
async def test_run_walk_forward_analysis_not_enough_data_for_fold(client: TestClient):
    request_payload = {
        "strategy_name": "TestStrategyWFShort",
        "parameter_ranges": [{"name": "param1", "start_value": 1.0, "end_value": 2.0, "step": 1.0}],
        "symbol": "BTC/USDT",
        "timeframe": "1d",
        "total_start_date": "2023-01-01T00:00:00Z",
        "total_end_date": "2023-01-10T23:59:59Z", # 10 days total
        "in_sample_period_days": 7,
        "out_of_sample_period_days": 5  # 7 + 5 = 12 days per fold, more than 10 available
    }
    response = client.post("/api/backtest/walkforward", json=request_payload)
    assert response.status_code == 400
    data = response.json()
    assert "Total data range too short for even one fold" in data.get("detail", "")

@pytest.mark.asyncio
async def test_run_walk_forward_analysis_zero_fold_duration(client: TestClient):
    request_payload = {
        "strategy_name": "TestStrategyWFZero",
        "parameter_ranges": [], # No optimization params
        "symbol": "BTC/USDT",
        "timeframe": "1d",
        "total_start_date": "2023-01-01T00:00:00Z",
        "total_end_date": "2023-01-30T23:59:59Z",
        "in_sample_period_days": 0, # Invalid
        "out_of_sample_period_days": 0 # Invalid
    }
    response = client.post("/api/backtest/walkforward", json=request_payload)
    assert response.status_code == 400
    data = response.json()
    assert "In-sample and out-of-sample periods cannot both be zero" in data.get("detail", "")