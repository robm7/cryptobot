from typing import Dict, Optional
from pydantic import BaseModel
from datetime import datetime

class BacktestRequest(BaseModel):
    """Request schema for starting a new backtest"""
    strategy: str
    parameters: Dict
    timeframe: str
    symbol: str
    start_date: str
    end_date: str

class BacktestResult(BaseModel):
    """Response schema for backtest results"""
    id: str
    strategy: str
    parameters: Dict
    start_time: str
    end_time: Optional[str] = None
    status: str
    results: Optional[Dict] = None

class PerformanceMetrics(BaseModel):
    """Schema for backtest performance metrics"""
    profit: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: Optional[float] = None
    sortino_ratio: Optional[float] = None