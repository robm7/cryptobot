from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Iterator
from datetime import datetime
import uuid
import itertools
import numpy as np # For arange with float steps

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Assuming db and celery_app are correctly set up in these modules
# For the optimization endpoint, direct DB interaction for each sub-backtest might be heavy.
# We'll focus on the logic and returning results as per instructions.
# If celery_config or models.backtest are not used in the new endpoint, they can be conditionally imported or removed if not used elsewhere.
try:
    from database.db import get_db # Assuming this is your DB session dependency
    from ..models.backtest import Backtest # Assuming this is your SQLAlchemy model
except ImportError:
    # Provide mock or placeholder if these are not available or not strictly needed for the sync optimization endpoint
    get_db = lambda: None
    Backtest = None

try:
    from ..celery_config import celery_app # For async tasks
except ImportError:
    celery_app = None


from ..schemas.backtest import (
    BacktestRequest,
    BacktestResult,
    PerformanceMetrics,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationRunResult,
    ParameterRange, # Added
    WalkForwardRequest,
    WalkForwardResponse,
    WalkForwardFoldResult,
    WalkForwardTaskStatus, # Assuming this might be used for async status later
    # PerformanceMetrics is already imported
)
from datetime import timedelta # For date calculations

router = APIRouter()

# --- Helper function to simulate a backtest run ---
# In a real scenario, this would trigger a full backtest execution,
# possibly using a Celery task or a direct call to a backtesting engine.
def _simulate_backtest_run(
    strategy_name: str,
    parameters: Dict[str, Any],
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str
) -> PerformanceMetrics:
    """
    Simulates a single backtest run and returns dummy performance metrics.
    Replace this with actual backtest execution logic.
    """
    # Dummy metrics, replace with actual calculations
    return PerformanceMetrics(
        profit=np.random.uniform(500, 5000),
        max_drawdown=np.random.uniform(0.05, 0.25),
        sharpe_ratio=np.random.uniform(0.5, 2.5),
        sortino_ratio=np.random.uniform(0.5, 3.5), # Added Sortino Ratio
        calmar_ratio=np.random.uniform(0.1, 1.5),  # Added Calmar Ratio
        win_rate=np.random.uniform(0.4, 0.7),
        total_trades=np.random.randint(50, 200),
        total_pnl=np.random.uniform(500, 5000) * (1 if np.random.rand() > 0.3 else -1), # Added Total P&L
        # other metrics can be added here
    )

# --- Helper function to generate parameter combinations ---
def _generate_parameter_combinations(
    parameter_ranges: List[ParameterRange]
) -> Iterator[Dict[str, Any]]:
    """
    Generates all possible combinations of parameters from the given ranges.
    """
    if not parameter_ranges:
        yield {}
        return

    param_names = [p.name for p in parameter_ranges]
    value_lists = []
    for p_range in parameter_ranges:
        # Use np.arange for float steps, then convert to list
        # Add a small epsilon to end_value to make it inclusive for np.arange
        values = np.arange(p_range.start_value, p_range.end_value + p_range.step / 2, p_range.step).tolist()
        value_lists.append(values)

    for combination_values in itertools.product(*value_lists):
        yield dict(zip(param_names, combination_values))


@router.post("/optimize", response_model=OptimizationResponse, status_code=status.HTTP_200_OK)
async def optimize_strategy_parameters(
    request: OptimizationRequest,
    # db: AsyncSession = Depends(get_db) # DB might not be needed if not storing each sub-run
):
    """
    Run parameter optimization for a given strategy.
    Iterates through parameter combinations, simulates backtests, and returns results.
    """
    optimization_id = str(uuid.uuid4())
    all_run_results: List[OptimizationRunResult] = []

    parameter_combinations = _generate_parameter_combinations(request.parameter_ranges)

    for params in parameter_combinations:
        # Simulate running a backtest with the current set of parameters
        # In a real system, this would be a more complex call:
        # metrics = await run_actual_backtest_task(request.strategy_name, params, request.symbol, ...)
        metrics = _simulate_backtest_run(
            strategy_name=request.strategy_name,
            parameters=params,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        all_run_results.append(
            OptimizationRunResult(parameters=params, metrics=metrics)
        )

    if not all_run_results and request.parameter_ranges: # If ranges were given but no combos (e.g. empty range)
        # This case should ideally be caught by validation in ParameterRange or _generate_parameter_combinations
        # or if no parameter_ranges are provided at all.
        # If parameter_ranges is empty, _generate_parameter_combinations yields one empty dict.
        pass # Let it return empty results list if that's the desired behavior for no params.
    
    # If parameter_ranges is empty, one run with default/empty params will occur.
    # If this is not desired, add a check:
    if not request.parameter_ranges and not all_run_results:
         # If no parameter ranges are provided, run one backtest with empty/default parameters
         # This assumes the strategy can handle empty parameters or has defaults.
        default_params = {}
        metrics = _simulate_backtest_run(
            strategy_name=request.strategy_name,
            parameters=default_params,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date
        )
        all_run_results.append(
            OptimizationRunResult(parameters=default_params, metrics=metrics)
        )


    return OptimizationResponse(
        optimization_id=optimization_id,
        strategy_name=request.strategy_name,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        results=all_run_results
    )


# --- Existing Endpoints (ensure they are compatible or adjust as needed) ---

@router.post("/start", response_model=BacktestResult, status_code=status.HTTP_202_ACCEPTED)
async def start_backtest(
    request: BacktestRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a new backtest"""
    if not Backtest or not celery_app or not db: # Check if dependencies are available
        raise HTTPException(status_code=503, detail="Service dependencies (DB or Celery) not configured for this operation.")

    # Ensure strategy_id is handled; the schema uses 'strategy' (name)
    # This part assumes Backtest model expects a strategy_id (int)
    # If strategies are identified by name, this needs adjustment or a lookup.
    # For now, let's assume request.strategy is the name and we need an ID.
    # This is a placeholder for how strategy_id might be resolved.
    # If your Backtest model uses strategy_name, then use request.strategy directly.
    
    # Placeholder: Resolve strategy_name to strategy_id if necessary
    # For this example, let's assume Backtest model can take strategy_name directly
    # or that strategy_id is not strictly enforced/used in the model for this example.
    # If Backtest model has `strategy_name: str` then use `strategy_name=request.strategy`
    # If it has `strategy_id: int`, you'd need to resolve `request.strategy` (name) to an ID.
    # The original code had `strategy_id=request.strategy_id` which is not in BacktestRequest.
    # Let's assume Backtest model has a `strategy_name` field or `strategy` field.
    # For simplicity, if Backtest model has `strategy: str`, then:
    
    # The original code had `strategy_id=request.strategy_id`
    # The `BacktestRequest` has `strategy: str`.
    # Let's assume the `Backtest` model has a field like `strategy_name` or `strategy`.
    # If it's `strategy_id`, we'd need to look it up.
    # For now, let's assume the model field is `strategy` and it takes the name.
    
    try:
        start_dt = datetime.fromisoformat(request.start_date)
        end_dt = datetime.fromisoformat(request.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format.")

    backtest_entry = Backtest(
        # strategy_id=request.strategy, # This was likely an error in original, assuming it means name
        strategy=request.strategy, # Assuming Backtest model has 'strategy' field for name
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=start_dt,
        end_date=end_dt,
        parameters=request.parameters,
        status="pending",
        # Ensure all required fields for Backtest model are provided
        # id is usually auto-generated; results, start_time, end_time are set later
    )
    
    db.add(backtest_entry)
    await db.commit()
    await db.refresh(backtest_entry)
    
    task_id = celery_app.send_task(
        "execute_backtest", # Name of the Celery task
        args=[backtest_entry.id], # Pass the database ID of the backtest entry
        queue="backtest" # Specify the queue
    )
    
    # The BacktestResult expects 'id' as string, 'start_time' as string.
    # The model might have 'id' as int and 'start_time' as datetime.
    # Need to adapt. The original `backtest.to_dict()` handled this.
    # If `to_dict()` is not available or suitable, manually construct the response.
    
    # Assuming backtest_entry.id is int, convert to str for response
    # Assuming backtest_entry.start_time is datetime, convert to isoformat str
    # This is a simplified representation. `to_dict()` would be better if it exists and is correct.
    return BacktestResult(
        id=str(backtest_entry.id), # Assuming id is int in model
        strategy=backtest_entry.strategy,
        parameters=backtest_entry.parameters,
        start_time=datetime.utcnow().isoformat(), # Placeholder for actual task start time
        status=backtest_entry.status
        # end_time and results will be None initially
    )


@router.get("/status/{backtest_id_str}", response_model=BacktestResult)
async def get_backtest_status(
    backtest_id_str: str, # Changed to str to handle potential UUIDs or other string IDs
    db: AsyncSession = Depends(get_db)
):
    """Get status of a backtest"""
    if not Backtest or not db:
        raise HTTPException(status_code=503, detail="Service dependencies (DB) not configured.")
    
    try:
        # Assuming backtest_id in DB is int. If it can be UUID, adjust query.
        backtest_id = int(backtest_id_str) 
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid backtest ID format.")

    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id))
    backtest = result.scalars().first()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    # Assuming a to_dict() method or similar for conversion
    # For now, manual conversion:
    return BacktestResult(
        id=str(backtest.id),
        strategy=backtest.strategy, # or backtest.strategy_name
        parameters=backtest.parameters,
        start_time=backtest.start_time.isoformat() if backtest.start_time else None,
        end_time=backtest.end_time.isoformat() if backtest.end_time else None,
        status=backtest.status,
        results=backtest.results # This should be Dict or None
    )

@router.get("/results/{backtest_id_str}", response_model=BacktestResult) # Ensure response_model matches return
async def get_backtest_results(
    backtest_id_str: str,
    db: AsyncSession = Depends(get_db)
):
    """Get results of a completed backtest"""
    if not Backtest or not db:
        raise HTTPException(status_code=503, detail="Service dependencies (DB) not configured.")

    try:
        backtest_id = int(backtest_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid backtest ID format.")

    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id))
    backtest = result.scalars().first()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    if backtest.status != "completed":
        # Return current status and whatever results are available, or error as before
        # For now, sticking to original behavior of raising error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Or 202 if still processing
            detail=f"Backtest not completed. Current status: {backtest.status}"
        )
    
    return BacktestResult( # Manual construction
        id=str(backtest.id),
        strategy=backtest.strategy,
        parameters=backtest.parameters,
        start_time=backtest.start_time.isoformat() if backtest.start_time else None,
        end_time=backtest.end_time.isoformat() if backtest.end_time else None,
        status=backtest.status,
        results=backtest.results
    )


@router.get("/performance/{backtest_id_str}", response_model=PerformanceMetrics)
async def get_performance_metrics(
    backtest_id_str: str,
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics for a completed backtest"""
    if not Backtest or not db:
        raise HTTPException(status_code=503, detail="Service dependencies (DB) not configured.")
    
    try:
        backtest_id = int(backtest_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid backtest ID format.")

    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id))
    backtest = result.scalars().first()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    if backtest.status != "completed" or not backtest.results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backtest not completed or no results (metrics) available"
        )
    
    # Assuming backtest.results is a dict that matches PerformanceMetrics schema
    # If not, transformation is needed.
    try:
        # Validate that backtest.results can be parsed into PerformanceMetrics
        metrics_data = backtest.results.get("performance_metrics", backtest.results) # if nested
        if not isinstance(metrics_data, dict):
             raise ValueError("Performance metrics are not in the expected dictionary format.")
        performance_data = PerformanceMetrics(**metrics_data)
        return performance_data
    except Exception as e: # Catch Pydantic validation errors or others
        # Log the error: logging.error(f"Error parsing performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not parse performance metrics from stored results: {str(e)}"
        )

# --- Helper function to find best parameters from an optimization run ---
# This is a simplified version. In reality, you'd define "best" based on a specific metric.
def _find_best_parameters(optimization_results: List[OptimizationRunResult]) -> Dict[str, Any]:
    """
    Finds the best parameters from a list of optimization run results.
    Currently, it picks the parameters from the run with the highest Sharpe ratio.
    """
    if not optimization_results:
        return {} # Or raise an error

    best_run = max(optimization_results, key=lambda r: r.metrics.sharpe_ratio if r.metrics else -float('inf'))
    return best_run.parameters if best_run else {}

# --- Helper function to aggregate performance metrics ---
def _aggregate_performance_metrics(fold_metrics: List[PerformanceMetrics]) -> PerformanceMetrics:
    """
    Aggregates performance metrics from multiple folds.
    This is a simple average for now. More sophisticated aggregation might be needed.
    """
    if not fold_metrics:
        return PerformanceMetrics(profit=0, max_drawdown=0, sharpe_ratio=0, win_rate=0, total_trades=0)

    num_metrics = len(fold_metrics)
    agg_metrics = {
        "profit": sum(m.profit for m in fold_metrics) / num_metrics,
        "max_drawdown": sum(m.max_drawdown for m in fold_metrics) / num_metrics,
        "sharpe_ratio": sum(m.sharpe_ratio for m in fold_metrics) / num_metrics,
        "win_rate": sum(m.win_rate for m in fold_metrics) / num_metrics,
        "total_trades": sum(m.total_trades for m in fold_metrics), # Sum of trades
        "total_pnl": sum(m.total_pnl for m in fold_metrics if m.total_pnl is not None) / num_metrics if any(m.total_pnl is not None for m in fold_metrics) else None,
        # Add other metrics as needed
    }
    return PerformanceMetrics(**agg_metrics)


@router.post("/walkforward", response_model=WalkForwardResponse, status_code=status.HTTP_200_OK)
async def run_walk_forward_analysis(
    request: WalkForwardRequest,
    # db: AsyncSession = Depends(get_db) # If storing results or task status
):
    """
    Run walk-forward analysis for a given strategy.
    Divides data into folds, optimizes in-sample, tests out-of-sample.
    """
    walk_forward_id = str(uuid.uuid4())
    all_fold_results: List[WalkForwardFoldResult] = []

    # 1. Data Windowing Logic
    total_duration_days = (request.total_end_date - request.total_start_date).days
    in_sample_delta = timedelta(days=request.in_sample_period_days)
    out_of_sample_delta = timedelta(days=request.out_of_sample_period_days)
    fold_duration_delta = in_sample_delta + out_of_sample_delta

    if request.num_folds:
        num_folds = request.num_folds
        # Optional: Adjust period_days if num_folds is given and conflicts, or raise error
        # For now, assume num_folds is consistent or derived if not provided.
    else:
        if fold_duration_delta.days == 0:
            raise HTTPException(status_code=400, detail="In-sample and out-of-sample periods cannot both be zero.")
        num_folds = total_duration_days // fold_duration_delta.days
        if num_folds == 0:
             raise HTTPException(status_code=400, detail="Not enough data for a single fold with the given in-sample/out-of-sample periods.")


    current_fold_start_date = request.total_start_date

    for i in range(num_folds):
        fold_number = i + 1
        in_sample_start_date = current_fold_start_date
        in_sample_end_date = in_sample_start_date + in_sample_delta - timedelta(days=1) # Inclusive end date

        out_of_sample_start_date = in_sample_end_date + timedelta(days=1)
        out_of_sample_end_date = out_of_sample_start_date + out_of_sample_delta - timedelta(days=1) # Inclusive end date

        if out_of_sample_end_date > request.total_end_date:
            # This fold would extend beyond the total data range, so break.
            # Or, adjust the last fold's out-of-sample period if desired.
            # For simplicity, we break if it overruns.
            if i == 0: # if even the first fold is too long
                 raise HTTPException(status_code=400, detail=f"Total data range too short for even one fold. In-sample: {request.in_sample_period_days} days, Out-of-sample: {request.out_of_sample_period_days} days.")
            break

        # 2.a. In-sample Optimization
        # Simulate calling the optimization endpoint/logic
        # In a real system, this would be an internal call or a task.
        # For now, we'll generate combinations and simulate runs like the /optimize endpoint.
        
        in_sample_optimization_runs: List[OptimizationRunResult] = []
        parameter_combinations = _generate_parameter_combinations(request.parameter_ranges)

        for params in parameter_combinations:
            # TODO: Replace with actual call to optimization service/task
            # This simulation assumes the optimization service would run backtests on the in-sample period
            metrics = _simulate_backtest_run(
                strategy_name=request.strategy_name,
                parameters=params,
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_date=in_sample_start_date.isoformat(),
                end_date=in_sample_end_date.isoformat()
            )
            in_sample_optimization_runs.append(
                OptimizationRunResult(parameters=params, metrics=metrics)
            )
        
        if not in_sample_optimization_runs and request.parameter_ranges:
             # Handle case where no optimization runs happened (e.g. bad ranges)
             # For simplicity, we might get an empty dict for best_params if this list is empty
             optimized_parameters = {}
        elif not request.parameter_ranges: # No parameters to optimize, run with empty/default
            default_params = {}
            metrics = _simulate_backtest_run(
                strategy_name=request.strategy_name,
                parameters=default_params,
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_date=in_sample_start_date.isoformat(),
                end_date=in_sample_end_date.isoformat()
            )
            in_sample_optimization_runs.append(
                OptimizationRunResult(parameters=default_params, metrics=metrics)
            )
            optimized_parameters = default_params
        else:
            optimized_parameters = _find_best_parameters(in_sample_optimization_runs)


        # 2.b. Out-of-sample Testing with best parameters
        # TODO: Replace with actual call to backtest service/task
        out_of_sample_metrics = _simulate_backtest_run(
            strategy_name=request.strategy_name,
            parameters=optimized_parameters,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=out_of_sample_start_date.isoformat(),
            end_date=out_of_sample_end_date.isoformat()
        )

        all_fold_results.append(
            WalkForwardFoldResult(
                fold_number=fold_number,
                in_sample_start_date=in_sample_start_date,
                in_sample_end_date=in_sample_end_date,
                out_of_sample_start_date=out_of_sample_start_date,
                out_of_sample_end_date=out_of_sample_end_date,
                optimized_parameters=optimized_parameters,
                out_of_sample_metrics=out_of_sample_metrics
            )
        )
        
        # Move to the start of the next fold (which is the start of the next in-sample period)
        # This typically means shifting by the out-of-sample period length, or by a fixed step.
        # For sequential, non-overlapping out-of-sample periods, the next fold starts after the current out-of-sample.
        # However, walk-forward can also have overlapping windows or a fixed step.
        # Assuming sequential folds where next in-sample starts after current out-of-sample:
        # current_fold_start_date = out_of_sample_end_date + timedelta(days=1)
        # A more common approach for walk-forward is to shift the window by the out-of-sample period length.
        current_fold_start_date = current_fold_start_date + out_of_sample_delta


    if not all_fold_results:
        # This could happen if num_folds was 0 or became 0 after adjustments.
        # Or if the loop broke immediately.
        # Consider raising an error or returning an empty response based on requirements.
        # For now, let's allow an empty list of folds if no valid folds were processed.
        # The num_folds in response will reflect the actual number of processed folds.
        pass

    # 3. Aggregate Performance Metrics
    aggregated_metrics = _aggregate_performance_metrics(
        [fold.out_of_sample_metrics for fold in all_fold_results]
    )

    return WalkForwardResponse(
        walk_forward_id=walk_forward_id,
        strategy_name=request.strategy_name,
        symbol=request.symbol,
        timeframe=request.timeframe,
        total_start_date=request.total_start_date,
        total_end_date=request.total_end_date,
        in_sample_period_days=request.in_sample_period_days,
        out_of_sample_period_days=request.out_of_sample_period_days,
        num_folds=len(all_fold_results), # Actual number of folds processed
        fold_results=all_fold_results,
        aggregated_out_of_sample_metrics=aggregated_metrics
    )