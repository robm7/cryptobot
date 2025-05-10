from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db import get_db
from .celery_config import celery_app
from .models.backtest import Backtest
from .schemas.backtest import (
    BacktestRequest,
    BacktestResult,
    PerformanceMetrics
)

router = APIRouter()

@router.post("/start", response_model=BacktestResult, status_code=status.HTTP_202_ACCEPTED)
async def start_backtest(
    request: BacktestRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a new backtest"""
    backtest = Backtest(
        strategy_id=request.strategy_id,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=datetime.fromisoformat(request.start_date),
        end_date=datetime.fromisoformat(request.end_date),
        parameters=request.parameters,
        status="pending"
    )
    
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)
    
    # Start backtest task
    celery_app.send_task(
        "execute_backtest",
        args=[backtest.id],
        queue="backtest"
    )
    
    return backtest.to_dict()

@router.get("/status/{backtest_id}", response_model=BacktestResult)
async def get_backtest_status(
    backtest_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get status of a backtest"""
    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id))
    backtest = result.scalars().first()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    return backtest.to_dict()

@router.get("/results/{backtest_id}", response_model=BacktestResult)
async def get_backtest_results(
    backtest_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get results of a completed backtest"""
    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id))
    backtest = result.scalars().first()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    if backtest.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backtest not completed"
        )
    
    return backtest.to_dict()

@router.get("/performance/{backtest_id}", response_model=PerformanceMetrics)
async def get_performance_metrics(
    backtest_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics for a completed backtest"""
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
            detail="Backtest not completed or no results available"
        )
    
    return backtest.results