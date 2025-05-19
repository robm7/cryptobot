import pytest
import numpy as np
from typing import List, Dict, Any, Iterator

# Assuming the schemas and router logic are accessible for import
# Adjust the import path based on your project structure
from backtest.schemas.backtest import ParameterRange, PerformanceMetrics, OptimizationRunResult
from backtest.routers.backtest import _generate_parameter_combinations, _simulate_backtest_run

# Test cases for _generate_parameter_combinations
@pytest.mark.parametrize("parameter_ranges, expected_combinations", [
    (
        [ParameterRange(name="p1", start_value=1, end_value=2, step=1)],
        [{"p1": 1.0}, {"p1": 2.0}]
    ),
    (
        [
            ParameterRange(name="p1", start_value=10, end_value=11, step=1),
            ParameterRange(name="p2", start_value=100, end_value=100, step=1)
        ],
        [{"p1": 10.0, "p2": 100.0}, {"p1": 11.0, "p2": 100.0}]
    ),
    (
        [
            ParameterRange(name="fast_ma", start_value=5, end_value=7, step=1),
            ParameterRange(name="slow_ma", start_value=10, end_value=11, step=1)
        ],
        [
            {"fast_ma": 5.0, "slow_ma": 10.0}, {"fast_ma": 5.0, "slow_ma": 11.0},
            {"fast_ma": 6.0, "slow_ma": 10.0}, {"fast_ma": 6.0, "slow_ma": 11.0},
            {"fast_ma": 7.0, "slow_ma": 10.0}, {"fast_ma": 7.0, "slow_ma": 11.0}
        ]
    ),
    (
        [ParameterRange(name="p_float", start_value=0.1, end_value=0.3, step=0.1)],
        [{"p_float": 0.1}, {"p_float": 0.2}, {"p_float": 0.3}]
    ),
    (
        [], # No parameter ranges
        [{}] # Should yield one empty dictionary
    ),
    (
        [ParameterRange(name="p_single", start_value=5, end_value=5, step=1)],
        [{"p_single": 5.0}]
    )
])
def test_generate_parameter_combinations(parameter_ranges: List[ParameterRange], expected_combinations: List[Dict[str, Any]]):
    combinations = list(_generate_parameter_combinations(parameter_ranges))
    
    # Convert numpy float types in actual combinations to standard floats for comparison
    actual_combinations_std_float = []
    for combo in combinations:
        actual_combinations_std_float.append({k: float(v) if isinstance(v, (np.float32, np.float64)) else v for k, v in combo.items()})

    assert len(actual_combinations_std_float) == len(expected_combinations)
    for expected_combo in expected_combinations:
        assert expected_combo in actual_combinations_std_float
    for actual_combo in actual_combinations_std_float:
        assert actual_combo in expected_combinations


def test_generate_parameter_combinations_empty_range_value():
    # Test case where a range might effectively be empty (e.g. start > end with positive step)
    # np.arange(5, 2, 1) yields an empty array.
    # itertools.product with an empty list for one parameter will result in no combinations overall.
    parameter_ranges = [
        ParameterRange(name="p1", start_value=5, end_value=2, step=1), # This range is empty
        ParameterRange(name="p2", start_value=10, end_value=11, step=1)
    ]
    combinations = list(_generate_parameter_combinations(parameter_ranges))
    assert len(combinations) == 0

    parameter_ranges_valid_then_empty = [
        ParameterRange(name="p1", start_value=1, end_value=1, step=1),
        ParameterRange(name="p2", start_value=5, end_value=2, step=1) # Empty
    ]
    combinations_valid_empty = list(_generate_parameter_combinations(parameter_ranges_valid_then_empty))
    assert len(combinations_valid_empty) == 0


# Test for _simulate_backtest_run (basic check as it's a mock)
def test_simulate_backtest_run():
    metrics = _simulate_backtest_run(
        strategy_name="test_strat",
        parameters={"p1": 10, "p2": 20},
        symbol="BTC/USD",
        timeframe="1h",
        start_date="2023-01-01",
        end_date="2023-01-31"
    )
    assert isinstance(metrics, PerformanceMetrics)
    assert metrics.profit >= 0  # Or some other basic assertion
    assert metrics.total_trades >= 0
    assert metrics.sharpe_ratio is not None # Check a few key fields
    assert "Total P&L" in metrics.model_fields_set or metrics.total_pnl is not None


# More comprehensive tests would involve mocking the actual backtest execution
# and verifying the interaction if the _simulate_backtest_run was more complex
# or if we were testing the main /optimize endpoint logic here.

# For the main optimization logic within the endpoint, that's better tested
# via an integration test that calls the endpoint.
# However, we can test a simplified version of the iteration logic if needed.

def mock_backtest_runner(strategy_name: str, parameters: Dict[str, Any], **kwargs) -> PerformanceMetrics:
    # A mock runner that returns predictable results based on params
    profit = parameters.get("p1", 0) * 100
    if "p2" in parameters and parameters["p2"] < 5:
        profit = -profit # Make some params result in loss
    return PerformanceMetrics(
        profit=profit,
        max_drawdown=0.1,
        sharpe_ratio=1.5,
        win_rate=0.6,
        total_trades=10,
        total_pnl=profit
    )

def test_optimization_iteration_logic_example():
    """
    This test simulates the core iteration and result aggregation part
    of the /optimize endpoint, using a mock backtest runner.
    """
    parameter_ranges = [
        ParameterRange(name="p1", start_value=1, end_value=2, step=1), # p1: 1, 2
        ParameterRange(name="p2", start_value=3, end_value=4, step=1)  # p2: 3, 4
    ]
    # Expected combinations:
    # {"p1": 1, "p2": 3} -> profit 100
    # {"p1": 1, "p2": 4} -> profit 100
    # {"p1": 2, "p2": 3} -> profit 200
    # {"p1": 2, "p2": 4} -> profit 200

    all_run_results: List[OptimizationRunResult] = []
    
    param_combinations = _generate_parameter_combinations(parameter_ranges)

    for params in param_combinations:
        metrics = mock_backtest_runner(strategy_name="test_opt", parameters=params)
        all_run_results.append(OptimizationRunResult(parameters=params, metrics=metrics))

    assert len(all_run_results) == 4
    
    expected_results_summary = [
        ({"p1": 1.0, "p2": 3.0}, 100.0),
        ({"p1": 1.0, "p2": 4.0}, 100.0),
        ({"p1": 2.0, "p2": 3.0}, 200.0),
        ({"p1": 2.0, "p2": 4.0}, 200.0),
    ]

    for i, run_result in enumerate(all_run_results):
        # Convert actual param values to float for comparison if they are numpy types
        actual_params_float = {k: float(v) if isinstance(v, (np.float32, np.float64)) else v for k, v in run_result.parameters.items()}
        
        found = False
        for expected_param_set, expected_profit in expected_results_summary:
            if actual_params_float == expected_param_set:
                assert run_result.metrics.profit == expected_profit
                assert run_result.metrics.total_pnl == expected_profit
                found = True
                break
        assert found, f"Unexpected or missing result for params: {actual_params_float}"