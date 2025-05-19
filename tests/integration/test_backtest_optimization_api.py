import pytest
from httpx import AsyncClient
from typing import List, Dict, Any

# Assuming your FastAPI application instance is accessible for testing.
# Adjust the import path according to your project structure.
# For example, if your FastAPI app is defined in backtest/main.py:
from backtest.main import app # Placeholder: Ensure this import is correct
from backtest.schemas.backtest import (
   OptimizationRequest,
   ParameterRange,
   OptimizationResponse,
   WalkForwardRequest, # Added
   WalkForwardResponse # Added
)
from datetime import datetime # Added for WalkForwardRequest

# Test using a live test server (if needed and configured) or TestClient
# For simplicity, TestClient with httpx.AsyncClient is often used.

@pytest.mark.asyncio
async def test_optimize_endpoint_success():
    """Test the /backtest/optimize endpoint with valid parameters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = OptimizationRequest(
            strategy_name="test_strategy_rsi_sma",
            parameter_ranges=[
                ParameterRange(name="rsi_period", start_value=10, end_value=12, step=1), # 10, 11, 12 (3 values)
                ParameterRange(name="sma_window", start_value=20, end_value=20, step=1)  # 20 (1 value)
            ],
            symbol="BTC/USDT",
            timeframe="1h",
            start_date="2023-01-01T00:00:00",
            end_date="2023-06-30T00:00:00"
        )
        
        response = await client.post("/backtest/optimize", json=request_data.model_dump())
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "optimization_id" in response_data
        assert response_data["strategy_name"] == request_data.strategy_name
        assert response_data["symbol"] == request_data.symbol
        assert response_data["timeframe"] == request_data.timeframe
        assert "results" in response_data
        
        results = response_data["results"]
        assert len(results) == 3 * 1 # rsi_period (3) * sma_window (1)
        
        for run_result in results:
            assert "parameters" in run_result
            assert "metrics" in run_result
            assert "rsi_period" in run_result["parameters"]
            assert "sma_window" in run_result["parameters"]
            
            metrics = run_result["metrics"]
            assert "profit" in metrics
            assert "max_drawdown" in metrics
            assert "sharpe_ratio" in metrics
            assert "win_rate" in metrics
            assert "total_trades" in metrics
            # Check for the aliased field if it's expected in the output JSON
            assert metrics.get("total_pnl") is not None or metrics.get("Total P&L") is not None


@pytest.mark.asyncio
async def test_optimize_endpoint_no_parameter_ranges():
    """Test the /backtest/optimize endpoint with no parameter ranges provided.
    It should run one backtest with default/empty parameters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = OptimizationRequest(
            strategy_name="default_param_strategy",
            parameter_ranges=[], # Empty list
            symbol="ETH/USDT",
            timeframe="4h",
            start_date="2024-01-01T00:00:00",
            end_date="2024-03-31T00:00:00"
        )
        
        response = await client.post("/backtest/optimize", json=request_data.model_dump())
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["strategy_name"] == request_data.strategy_name
        assert "results" in response_data
        results = response_data["results"]
        
        # Expect one result, corresponding to a single run with empty/default parameters
        assert len(results) == 1
        assert results[0]["parameters"] == {} # Expecting empty dict for parameters
        assert "metrics" in results[0]
        assert results[0]["metrics"]["profit"] is not None # Basic check for metrics


@pytest.mark.asyncio
async def test_optimize_endpoint_single_parameter_single_value():
    """Test with a single parameter having a single value in its range."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = OptimizationRequest(
            strategy_name="single_val_strategy",
            parameter_ranges=[
                ParameterRange(name="fixed_param", start_value=50, end_value=50, step=1) # 1 value
            ],
            symbol="ADA/USDT",
            timeframe="1d",
            start_date="2023-01-01T00:00:00",
            end_date="2023-02-01T00:00:00"
        )
        
        response = await client.post("/backtest/optimize", json=request_data.model_dump())
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert len(response_data["results"]) == 1
        assert response_data["results"][0]["parameters"] == {"fixed_param": 50.0}


@pytest.mark.asyncio
async def test_optimize_endpoint_float_step_parameter():
    """Test with a parameter using a float step."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = OptimizationRequest(
            strategy_name="float_step_strategy",
            parameter_ranges=[
                ParameterRange(name="tolerance", start_value=0.1, end_value=0.3, step=0.1) # 0.1, 0.2, 0.3 (3 values)
            ],
            symbol="LINK/USDT",
            timeframe="1h",
            start_date="2023-05-01T00:00:00",
            end_date="2023-05-10T00:00:00"
        )
        
        response = await client.post("/backtest/optimize", json=request_data.model_dump())
        
        assert response.status_code == 200
        response_data = response.json()
        
        results = response_data["results"]
        assert len(results) == 3
        
        expected_tolerances = [0.1, 0.2, 0.3]
        actual_tolerances = sorted([run["parameters"]["tolerance"] for run in results])
        
        for i in range(len(expected_tolerances)):
            assert abs(actual_tolerances[i] - expected_tolerances[i]) < 1e-9 # Compare floats


# Note: To run these tests, you'll need:
# 1. `httpx` installed (`pip install httpx`).
# 2. A way to provide the FastAPI `app` instance. This often involves a `conftest.py`
#    or a fixture that sets up the TestClient.
# 3. The `backtest.main.app` import path must be correct. If your app is in `backtest/app.py`,
#    change it to `from backtest.app import app`.
# 4. Ensure that the `_simulate_backtest_run` in `backtest/routers/backtest.py`
#    is robust enough not to cause unexpected errors during these tests (e.g., division by zero if random values are not handled).
#    The current simulation uses `np.random` which should be fine.


@pytest.mark.asyncio
async def test_walk_forward_endpoint_success():
    """Test the /backtest/walkforward endpoint with valid parameters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = WalkForwardRequest(
            strategy_name="wf_strategy",
            parameter_ranges=[
                ParameterRange(name="p1", start_value=10, end_value=20, step=10) # 10, 20 (2 values)
            ],
            symbol="BTC/USDT",
            timeframe="1h",
            total_start_date=datetime(2023, 1, 1),
            total_end_date=datetime(2023, 1, 20), # 20 days
            in_sample_period_days=7,
            out_of_sample_period_days=3 # 10 days per fold, so 2 folds
        )
        
        # Need to convert datetime objects to string for JSON serialization
        json_request_data = request_data.model_dump()
        json_request_data["total_start_date"] = request_data.total_start_date.isoformat()
        json_request_data["total_end_date"] = request_data.total_end_date.isoformat()

        response = await client.post("/api/backtest/walkforward", json=json_request_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "walk_forward_id" in response_data
        assert response_data["strategy_name"] == request_data.strategy_name
        assert response_data["symbol"] == request_data.symbol
        assert response_data["num_folds"] == 2 # Expected number of folds
        
        assert "fold_results" in response_data
        assert len(response_data["fold_results"]) == 2
        
        for fold_result in response_data["fold_results"]:
            assert "fold_number" in fold_result
            assert "in_sample_start_date" in fold_result
            assert "out_of_sample_metrics" in fold_result
            assert "optimized_parameters" in fold_result
            # Based on mock, p1=20 should be chosen (higher sharpe)
            assert fold_result["optimized_parameters"].get("p1") == 20.0
            assert fold_result["out_of_sample_metrics"]["profit"] is not None

        assert "aggregated_out_of_sample_metrics" in response_data
        assert response_data["aggregated_out_of_sample_metrics"]["profit"] is not None


@pytest.mark.asyncio
async def test_walk_forward_endpoint_insufficient_data():
    """Test /backtest/walkforward when data is insufficient for even one fold."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = WalkForwardRequest(
            strategy_name="wf_short_data",
            parameter_ranges=[],
            symbol="ETH/USDT",
            timeframe="1d",
            total_start_date=datetime(2023, 1, 1),
            total_end_date=datetime(2023, 1, 5), # Only 5 days
            in_sample_period_days=7, # Needs 7
            out_of_sample_period_days=3  # Needs 3 (total 10)
        )
        json_request_data = request_data.model_dump()
        json_request_data["total_start_date"] = request_data.total_start_date.isoformat()
        json_request_data["total_end_date"] = request_data.total_end_date.isoformat()

        response = await client.post("/api/backtest/walkforward", json=json_request_data)
        
        assert response.status_code == 400 # Expecting Bad Request
        response_data = response.json()
        assert "detail" in response_data
        assert "Total data range too short" in response_data["detail"]

@pytest.mark.asyncio
async def test_walk_forward_endpoint_no_param_ranges():
    """Test /backtest/walkforward with no parameter ranges (should use default params)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = WalkForwardRequest(
            strategy_name="wf_default_params",
            parameter_ranges=[], # No optimization
            symbol="ADA/USDT",
            timeframe="4h",
            total_start_date=datetime(2023, 2, 1),
            total_end_date=datetime(2023, 2, 10), # 10 days
            in_sample_period_days=6,
            out_of_sample_period_days=4 # 1 fold
        )
        json_request_data = request_data.model_dump()
        json_request_data["total_start_date"] = request_data.total_start_date.isoformat()
        json_request_data["total_end_date"] = request_data.total_end_date.isoformat()

        response = await client.post("/api/backtest/walkforward", json=json_request_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["num_folds"] == 1
        assert len(response_data["fold_results"]) == 1
        fold1_result = response_data["fold_results"][0]
        assert fold1_result["optimized_parameters"] == {} # Default/empty params
        # The mock _simulate_backtest_run uses a default for "p1" if not found in params.
        # If params is {}, parameters.get("p1", 1000) yields 1000.
        # So, profit for out-of-sample should be 1000.0 based on the mock.
        assert fold1_result["out_of_sample_metrics"]["profit"] == 1000.0


@pytest.mark.asyncio
async def test_walk_forward_endpoint_success():
    """Test the /backtest/walkforward endpoint with valid parameters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = WalkForwardRequest(
            strategy_name="wf_strategy",
            parameter_ranges=[
                ParameterRange(name="p1", start_value=10, end_value=20, step=10) # 10, 20 (2 values)
            ],
            symbol="BTC/USDT",
            timeframe="1h",
            total_start_date=datetime(2023, 1, 1),
            total_end_date=datetime(2023, 1, 20), # 20 days
            in_sample_period_days=7,
            out_of_sample_period_days=3 # 10 days per fold, so 2 folds
        )
        
        # Need to convert datetime objects to string for JSON serialization
        json_request_data = request_data.model_dump()
        json_request_data["total_start_date"] = request_data.total_start_date.isoformat()
        json_request_data["total_end_date"] = request_data.total_end_date.isoformat()

        response = await client.post("/api/backtest/walkforward", json=json_request_data) # Corrected prefix
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "walk_forward_id" in response_data
        assert response_data["strategy_name"] == request_data.strategy_name
        assert response_data["symbol"] == request_data.symbol
        assert response_data["num_folds"] == 2 # Expected number of folds
        
        assert "fold_results" in response_data
        assert len(response_data["fold_results"]) == 2
        
        for fold_result in response_data["fold_results"]:
            assert "fold_number" in fold_result
            assert "in_sample_start_date" in fold_result
            assert "out_of_sample_metrics" in fold_result
            assert "optimized_parameters" in fold_result
            # Based on mock, p1=20 should be chosen (higher sharpe)
            assert fold_result["optimized_parameters"].get("p1") == 20.0
            assert fold_result["out_of_sample_metrics"]["profit"] is not None

        assert "aggregated_out_of_sample_metrics" in response_data
        assert response_data["aggregated_out_of_sample_metrics"]["profit"] is not None


@pytest.mark.asyncio
async def test_walk_forward_endpoint_insufficient_data():
    """Test /backtest/walkforward when data is insufficient for even one fold."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = WalkForwardRequest(
            strategy_name="wf_short_data",
            parameter_ranges=[],
            symbol="ETH/USDT",
            timeframe="1d",
            total_start_date=datetime(2023, 1, 1),
            total_end_date=datetime(2023, 1, 5), # Only 5 days
            in_sample_period_days=7, # Needs 7
            out_of_sample_period_days=3  # Needs 3 (total 10)
        )
        json_request_data = request_data.model_dump()
        json_request_data["total_start_date"] = request_data.total_start_date.isoformat()
        json_request_data["total_end_date"] = request_data.total_end_date.isoformat()

        response = await client.post("/api/backtest/walkforward", json=json_request_data) # Corrected prefix
        
        assert response.status_code == 400 # Expecting Bad Request
        response_data = response.json()
        assert "detail" in response_data
        assert "Total data range too short" in response_data["detail"]

@pytest.mark.asyncio
async def test_walk_forward_endpoint_no_param_ranges():
    """Test /backtest/walkforward with no parameter ranges (should use default params)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = WalkForwardRequest(
            strategy_name="wf_default_params",
            parameter_ranges=[], # No optimization
            symbol="ADA/USDT",
            timeframe="4h",
            total_start_date=datetime(2023, 2, 1),
            total_end_date=datetime(2023, 2, 10), # 10 days
            in_sample_period_days=6,
            out_of_sample_period_days=4 # 1 fold
        )
        json_request_data = request_data.model_dump()
        json_request_data["total_start_date"] = request_data.total_start_date.isoformat()
        json_request_data["total_end_date"] = request_data.total_end_date.isoformat()

        response = await client.post("/api/backtest/walkforward", json=json_request_data) # Corrected prefix
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["num_folds"] == 1
        assert len(response_data["fold_results"]) == 1
        fold1_result = response_data["fold_results"][0]
        assert fold1_result["optimized_parameters"] == {} # Default/empty params
        # The mock _simulate_backtest_run uses a default for "p1" if not found in params.
        # If params is {}, parameters.get("p1", 1000) yields 1000.
        # So, profit for out-of-sample should be 1000.0 based on the mock.
        assert fold1_result["out_of_sample_metrics"]["profit"] == 1000.0