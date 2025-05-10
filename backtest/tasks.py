import asyncio
from datetime import datetime
from typing import Dict
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models.backtest import Backtest
from database.db import async_session
from utils.performance_metrics import calculate_metrics
import httpx

@shared_task(bind=True, name='execute_backtest')
def execute_backtest(self, backtest_id: int):
    """Celery task to execute backtest"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_async_execute_backtest(self, backtest_id))

async def _async_execute_backtest(task, backtest_id: int):
    """Async backtest execution"""
    async with async_session() as session:
        # Get backtest from database
        result = await session.execute(select(Backtest).where(Backtest.id == backtest_id))
        backtest = result.scalars().first()
        
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")
        
        try:
            # Update status to running
            backtest.status = "running"
            await session.commit()
            
            # Get historical data from Data Service
            async with httpx.AsyncClient() as client:
                data_response = await client.get(
                    "http://data-service/api/data/historical",
                    params={
                        "symbol": backtest.symbol,
                        "timeframe": backtest.timeframe,
                        "start": backtest.start_date.isoformat(),
                        "end": backtest.end_date.isoformat()
                    }
                )
                data_response.raise_for_status()
                historical_data = data_response.json()
            
            # Get strategy from Strategy Service
            async with httpx.AsyncClient() as client:
                strategy_response = await client.get(
                    f"http://strategy-service/api/strategies/{backtest.strategy_id}"
                )
                strategy_response.raise_for_status()
                strategy = strategy_response.json()
            
            # Execute backtest (simplified for example)
            # TODO: Implement actual backtest execution with strategy
            trades = []  # This would be populated with actual trades
            
            # Calculate performance metrics
            metrics = calculate_metrics(trades, backtest.initial_capital)
            
            # Update backtest results
            backtest.status = "completed"
            backtest.completed_at = datetime.utcnow()
            backtest.results = metrics
            await session.commit()
            
            return {"status": "completed", "backtest_id": backtest_id}
            
        except Exception as e:
            backtest.status = "failed"
            backtest.results = {"error": str(e)}
            await session.commit()
            raise