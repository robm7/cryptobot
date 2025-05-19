from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime

class BacktestRequest(BaseModel):
    """Request schema for starting a new backtest"""
    strategy: str
    parameters: Dict[str, Any]
    timeframe: str
    symbol: str
    start_date: str
    end_date: str

class BacktestResult(BaseModel):
    """Response schema for backtest results"""
    id: str
    strategy: str
    parameters: Dict[str, Any]
    start_time: str
    end_time: Optional[str] = None
    status: str
    results: Optional[Dict[str, Any]] = None

class PerformanceMetrics(BaseModel):
    """Schema for backtest performance metrics"""
    profit: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    downside_volatility: Optional[float] = None
    ulcer_index: Optional[float] = None
    pain_index: Optional[float] = None
    pain_ratio: Optional[float] = None
    omega_ratio: Optional[float] = None
    avg_drawdown_duration: Optional[float] = None
    max_drawdown_duration: Optional[float] = None
    volatility: Optional[float] = None
    # Adding common metrics that might be useful
    total_pnl: Optional[float] = Field(None, alias="Total P&L") # Alias for Total P&L
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    expectancy: Optional[float] = None


class DrawdownPeriod(BaseModel):
    """Schema for drawdown period information"""
    start_date: str
    end_date: str
    duration: int
    max_drawdown: float
    max_drawdown_date: str

# New schemas for Parameter Optimization

class ParameterRange(BaseModel):
    """Defines the range for a single parameter to be optimized."""
    name: str
    start_value: float
    end_value: float
    step: float

class OptimizationRequest(BaseModel):
    """Request schema for starting a parameter optimization task."""
    strategy_name: str
    parameter_ranges: List[ParameterRange]
    symbol: str
    timeframe: str
    start_date: str # Consider using datetime
    end_date: str   # Consider using datetime

class OptimizationRunResult(BaseModel):
    """Stores the parameters and performance metrics for a single backtest run within an optimization task."""
    parameters: Dict[str, Any]
    metrics: PerformanceMetrics

class OptimizationResponse(BaseModel):
    """Response schema for the parameter optimization task, containing results for all combinations."""
    optimization_id: str # Could be a task ID if run asynchronously
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    results: List[OptimizationRunResult]

class OptimizationTaskStatus(BaseModel):
    """Schema to get the status of an optimization task if run asynchronously."""
    task_id: str
    status: str
    message: Optional[str] = None
    progress: Optional[float] = None # e.g., 0.0 to 1.0
    results_summary: Optional[List[OptimizationRunResult]] = None # Partial results or summary
# New schemas for Walk-Forward Testing

class WalkForwardFoldResult(BaseModel):
    """Stores the results of a single walk-forward fold."""
    fold_number: int
    in_sample_start_date: datetime
    in_sample_end_date: datetime
    out_of_sample_start_date: datetime
    out_of_sample_end_date: datetime
    optimized_parameters: Dict[str, Any]
    out_of_sample_metrics: PerformanceMetrics

class WalkForwardRequest(BaseModel):
    """Request schema for starting a walk-forward testing task."""
    strategy_name: str
    parameter_ranges: List[ParameterRange]
    symbol: str
    timeframe: str
    total_start_date: datetime
    total_end_date: datetime
    in_sample_period_days: int # Length of the in-sample period in days
    out_of_sample_period_days: int # Length of the out-of-sample period in days
    num_folds: Optional[int] = None # Optional: if not provided, it's derived

class WalkForwardResponse(BaseModel):
    """Response schema for the walk-forward testing task."""
    walk_forward_id: str # Could be a task ID if run asynchronously
    strategy_name: str
    symbol: str
    timeframe: str
    total_start_date: datetime
    total_end_date: datetime
    in_sample_period_days: int
    out_of_sample_period_days: int
    num_folds: int
    fold_results: List[WalkForwardFoldResult]
    aggregated_out_of_sample_metrics: PerformanceMetrics # This would be an aggregation (e.g., average) of metrics from all folds

class WalkForwardTaskStatus(BaseModel):
    """Schema to get the status of a walk-forward task if run asynchronously."""
    task_id: str
    status: str
    message: Optional[str] = None
    progress: Optional[float] = None  # e.g., 0.0 to 1.0
    current_fold: Optional[int] = None
    total_folds: Optional[int] = None
    results_summary: Optional[WalkForwardResponse] = None # Partial or full results