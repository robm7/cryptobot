import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from fastapi import HTTPException

# Assuming your schemas and router functions are accessible for testing
# Adjust the import path based on your project structure
from backtest.schemas.backtest import (
    ParameterRange,
    PerformanceMetrics,
    OptimizationRunResult,
    WalkForwardRequest,
    WalkForwardResponse,
    WalkForwardFoldResult
)
from backtest.routers.backtest import (
    _generate_parameter_combinations, # Already in optimization tests?
    _find_best_parameters,
    _aggregate_performance_metrics,
    run_walk_forward_analysis, # To test its internal logic by mocking sub-calls
    _simulate_backtest_run # For mocking
)

# Mock for _simulate_backtest_run and optimization calls
def mock_simulate_backtest_run(
    strategy_name: str,
    parameters: Dict[str, Any],
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str
) -> PerformanceMetrics:
    # print(f"Mock run: {strategy_name}, {parameters}, {symbol}, {timeframe}, {start_date}, {end_date}")
    return PerformanceMetrics(
        profit=parameters.get("p1", 1000) * 1.0, # Make profit dependent on a param for testing best_param selection
        max_drawdown=0.1,
        sharpe_ratio=parameters.get("p1", 1.0) * 0.1, # Make sharpe dependent
        win_rate=0.6,
        total_trades=10,
        total_pnl=parameters.get("p1", 1000) * 0.9
    )

@pytest.fixture
def mock_btrun(monkeypatch):
    monkeypatch.setattr("backtest.routers.backtest._simulate_backtest_run", mock_simulate_backtest_run)

# --- Tests for Helper Functions ---

def test_find_best_parameters():
    results = [
        OptimizationRunResult(parameters={"p1": 10}, metrics=PerformanceMetrics(profit=100, max_drawdown=0.1, sharpe_ratio=1.0, win_rate=0.5, total_trades=5)),
        OptimizationRunResult(parameters={"p1": 20}, metrics=PerformanceMetrics(profit=200, max_drawdown=0.1, sharpe_ratio=2.0, win_rate=0.5, total_trades=5)),
        OptimizationRunResult(parameters={"p1": 5}, metrics=PerformanceMetrics(profit=50, max_drawdown=0.1, sharpe_ratio=0.5, win_rate=0.5, total_trades=5)),
    ]
    best_params = _find_best_parameters(results)
    assert best_params == {"p1": 20}

def test_find_best_parameters_empty():
    assert _find_best_parameters([]) == {}

def test_aggregate_performance_metrics():
    metrics_list = [
        PerformanceMetrics(profit=100, max_drawdown=0.1, sharpe_ratio=1.0, win_rate=0.5, total_trades=10, total_pnl=90),
        PerformanceMetrics(profit=200, max_drawdown=0.2, sharpe_ratio=1.5, win_rate=0.6, total_trades=20, total_pnl=180),
    ]
    aggregated = _aggregate_performance_metrics(metrics_list)
    assert aggregated.profit == 150
    assert aggregated.max_drawdown == pytest.approx(0.15)
    assert aggregated.sharpe_ratio == pytest.approx(1.25)
    assert aggregated.win_rate == pytest.approx(0.55)
    assert aggregated.total_trades == 30 # Sum of trades
    assert aggregated.total_pnl == pytest.approx(135)

def test_aggregate_performance_metrics_empty():
    aggregated = _aggregate_performance_metrics([])
    assert aggregated.profit == 0
    assert aggregated.total_trades == 0

# --- Tests for Walk-Forward Data Windowing and Core Logic ---

@pytest.mark.asyncio
async def test_walk_forward_windowing_basic(mock_btrun):
    request = WalkForwardRequest(
        strategy_name="test_strategy",
        parameter_ranges=[ParameterRange(name="p1", start_value=10, end_value=20, step=10)], # Will produce 2 param sets
        symbol="BTCUSDT",
        timeframe="1h",
        total_start_date=datetime(2023, 1, 1),
        total_end_date=datetime(2023, 1, 20), # 20 days total
        in_sample_period_days=7,
        out_of_sample_period_days=3 # 10 days per fold
    )
    # Expected: 2 folds (20 days / 10 days_per_fold = 2)
    
    response = await run_walk_forward_analysis(request)
    
    assert response.num_folds == 2
    assert len(response.fold_results) == 2

    # Fold 1
    fold1 = response.fold_results[0]
    assert fold1.fold_number == 1
    assert fold1.in_sample_start_date == datetime(2023, 1, 1)
    assert fold1.in_sample_end_date == datetime(2023, 1, 7) # 7 days
    assert fold1.out_of_sample_start_date == datetime(2023, 1, 8)
    assert fold1.out_of_sample_end_date == datetime(2023, 1, 10) # 3 days
    # Check if best params from in-sample (p1=20 due to higher sharpe) were used for out-of-sample
    assert fold1.optimized_parameters == {"p1": 20.0} 
    assert fold1.out_of_sample_metrics.profit == 20.0 # Based on mock_simulate_backtest_run

    # Fold 2
    fold2 = response.fold_results[1]
    assert fold2.fold_number == 2
    assert fold2.in_sample_start_date == datetime(2023, 1, 1 + 3) # Shifted by out_of_sample_period_days (3)
    assert fold2.in_sample_start_date == datetime(2023, 1, 4)
    assert fold2.in_sample_end_date == datetime(2023, 1, 10)
    assert fold2.out_of_sample_start_date == datetime(2023, 1, 11)
    assert fold2.out_of_sample_end_date == datetime(2023, 1, 13)
    assert fold2.optimized_parameters == {"p1": 20.0}
    assert fold2.out_of_sample_metrics.profit == 20.0

    # Check aggregation (simple average for profit based on mock)
    assert response.aggregated_out_of_sample_metrics.profit == 20.0


@pytest.mark.asyncio
async def test_walk_forward_windowing_exact_fit(mock_btrun):
    request = WalkForwardRequest(
        strategy_name="test_strategy",
        parameter_ranges=[], # No optimization, use default
        symbol="BTCUSDT",
        timeframe="1h",
        total_start_date=datetime(2023, 1, 1),
        total_end_date=datetime(2023, 1, 10), # 10 days
        in_sample_period_days=7,
        out_of_sample_period_days=3 # 10 days per fold
    )
    # Expected: 1 fold
    response = await run_walk_forward_analysis(request)
    assert response.num_folds == 1
    assert len(response.fold_results) == 1
    fold1 = response.fold_results[0]
    assert fold1.in_sample_start_date == datetime(2023, 1, 1)
    assert fold1.in_sample_end_date == datetime(2023, 1, 7)
    assert fold1.out_of_sample_start_date == datetime(2023, 1, 8)
    assert fold1.out_of_sample_end_date == datetime(2023, 1, 10)
    assert fold1.optimized_parameters == {} # Default params

@pytest.mark.asyncio
async def test_walk_forward_windowing_partial_last_fold(mock_btrun):
    # The current logic breaks if the last fold overruns.
    # This test verifies that behavior.
    request = WalkForwardRequest(
        strategy_name="test_strategy",
        parameter_ranges=[],
        symbol="BTCUSDT",
        timeframe="1h",
        total_start_date=datetime(2023, 1, 1),
        total_end_date=datetime(2023, 1, 12), # 12 days
        in_sample_period_days=7,
        out_of_sample_period_days=3 # 10 days per fold
    )
    # Expected: 1 full fold, the second fold (starting day 4 for in-sample) would be:
    # In-sample: Jan 4 - Jan 10
    # Out-sample: Jan 11 - Jan 13. But total_end_date is Jan 12. So it breaks.
    response = await run_walk_forward_analysis(request)
    assert response.num_folds == 1 
    assert len(response.fold_results) == 1
    assert response.fold_results[0].out_of_sample_end_date == datetime(2023,1,10)


@pytest.mark.asyncio
async def test_walk_forward_not_enough_data_for_one_fold(mock_btrun):
    request = WalkForwardRequest(
        strategy_name="test_strategy",
        parameter_ranges=[],
        symbol="BTCUSDT",
        timeframe="1h",
        total_start_date=datetime(2023, 1, 1),
        total_end_date=datetime(2023, 1, 5), # 5 days
        in_sample_period_days=7, # Needs 7
        out_of_sample_period_days=3 # Needs 3
    )
    with pytest.raises(HTTPException) as excinfo:
        await run_walk_forward_analysis(request)
    assert excinfo.value.status_code == 400
    assert "Total data range too short" in excinfo.value.detail

@pytest.mark.asyncio
async def test_walk_forward_num_folds_provided(mock_btrun):
    request = WalkForwardRequest(
        strategy_name="test_strategy",
        parameter_ranges=[],
        symbol="BTCUSDT",
        timeframe="1h",
        total_start_date=datetime(2023, 1, 1),
        total_end_date=datetime(2023, 1, 30), # 30 days
        in_sample_period_days=7,
        out_of_sample_period_days=3,
        num_folds=2 # Explicitly request 2 folds
    )
    # Even if more data is available, it should respect num_folds
    response = await run_walk_forward_analysis(request)
    assert response.num_folds == 2
    assert len(response.fold_results) == 2

@pytest.mark.asyncio
async def test_walk_forward_zero_fold_duration(mock_btrun):
    request = WalkForwardRequest(
        strategy_name="test_strategy",
        parameter_ranges=[],
        symbol="BTCUSDT",
        timeframe="1h",
        total_start_date=datetime(2023, 1, 1),
        total_end_date=datetime(2023, 1, 5),
        in_sample_period_days=0,
        out_of_sample_period_days=0
    )
    with pytest.raises(HTTPException) as excinfo:
        await run_walk_forward_analysis(request)
    assert excinfo.value.status_code == 400
    assert "In-sample and out-of-sample periods cannot both be zero." in excinfo.value.detail

@pytest.mark.asyncio
async def test_walk_forward_no_parameter_ranges(mock_btrun):
    request = WalkForwardRequest(
        strategy_name="test_strategy",
        parameter_ranges=[], # No parameters to optimize
        symbol="BTCUSDT",
        timeframe="1h",
        total_start_date=datetime(2023, 1, 1),
        total_end_date=datetime(2023, 1, 10),
        in_sample_period_days=7,
        out_of_sample_period_days=3
    )
    response = await run_walk_forward_analysis(request)
    assert response.num_folds == 1
    assert len(response.fold_results) == 1
    # Check that default/empty parameters were used
    assert response.fold_results[0].optimized_parameters == {}
    # Check that the mock_simulate_backtest_run was called with these empty params
    # The mock uses p1, so profit will be based on default p1=1000 if not present
    # Let's adjust mock_simulate_backtest_run to handle empty params better for this test
    # For now, the current mock would use its default for "p1" if not in params.
    # If params is {}, then parameters.get("p1", 1000) yields 1000.
    assert response.fold_results[0].out_of_sample_metrics.profit == 1000.0

# TODO: Add integration tests for the API endpoint (in a different file, e.g., tests/integration/test_backtest_integration.py)
# These would involve actual HTTP calls to the service.