"""
Reconciliation API Router

This module provides API endpoints for order reconciliation reporting.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Union, float

from services.mcp.reporting.basic_reporter import BasicReporter
from services.mcp.order_execution.reconciliation_job import ReconciliationJob
from auth_service import get_current_active_user

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

class ReconciliationFilter(BaseModel):
    """Reconciliation filter model"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    exchange: Optional[str] = None
    symbol: Optional[str] = None
    time_period: Optional[str] = None
    alert_triggered: Optional[bool] = None
    
class ThresholdConfig(BaseModel):
    """Alert threshold configuration model"""
    mismatch_percentage: float
    missing_orders: int
    extra_orders: int

# Dependency to get the reconciliation reporter
def get_reconciliation_reporter():
    """
    Get the reconciliation reporter.
    
    Returns:
        BasicReporter instance with reconciliation_job
    """
    # In a real implementation, this would get the reconciliation job from a service
    # For now, we'll create a new instance with the default configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        },
        "reporting": {
            "file": "reconciliation_reports.json",
            "history_days": 30
        }
    }
    
    reconciliation_job = ReconciliationJob(config)
    reporter = BasicReporter(reconciliation_job=reconciliation_job)
    
    return reporter

@router.get("/reports")
async def get_reconciliation_reports(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
    time_period: Optional[str] = None,
    alert_triggered: Optional[bool] = None,
    current_user = Depends(get_current_active_user),
    reporter = Depends(get_reconciliation_reporter)
):
    """
    Get reconciliation reports with optional filtering.
    
    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        exchange: Optional exchange filter
        symbol: Optional symbol filter
        time_period: Optional time period filter (daily, hourly, weekly)
        alert_triggered: Optional filter for reports with alerts
        
    Returns:
        Reconciliation report data
    """
    # Build filters
    filters = {}
    if exchange:
        filters["exchange"] = exchange
    if symbol:
        filters["symbol"] = symbol
    if time_period:
        filters["time_period"] = time_period
    if alert_triggered is not None:
        filters["alert_triggered"] = alert_triggered
    
    # Generate report
    report = reporter.generate_reconciliation_report(
        start_date=start_date,
        end_date=end_date,
        filters=filters if filters else None
    )
    
    if report.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=report.get("error", "Failed to generate reconciliation report")
        )
    
    return report

@router.post("/run")
async def run_reconciliation(
    current_user = Depends(get_current_active_user),
    reporter = Depends(get_reconciliation_reporter)
):
    """
    Run reconciliation job manually.
    
    Returns:
        Reconciliation result
    """
    try:
        # Get the reconciliation job from the reporter
        job = reporter.reconciliation_job
        
        # Run reconciliation
        result = await job.run_reconciliation()
        
        return {
            "status": "success",
            "message": "Reconciliation completed successfully",
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run reconciliation: {str(e)}"
        )

@router.get("/status")
async def get_reconciliation_status(
    current_user = Depends(get_current_active_user),
    reporter = Depends(get_reconciliation_reporter)
):
    """
    Get reconciliation job status.
    
    Returns:
        Reconciliation job status
    """
    try:
        # Get the reconciliation job from the reporter
        job = reporter.reconciliation_job
        
        # Get status
        status = job.get_status()
        
        return {
            "status": "success",
            "job_status": status
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reconciliation status: {str(e)}"
        )

@router.get("/summary")
async def get_reconciliation_summary(
    days: int = Query(7, description="Number of days to include in summary"),
    current_user = Depends(get_current_active_user),
    reporter = Depends(get_reconciliation_reporter)
):
    """
    Get reconciliation summary for the specified number of days.
    
    Args:
        days: Number of days to include in summary
        
    Returns:
        Reconciliation summary
    """
    # Calculate start date
    from datetime import datetime, timedelta
    start_date = datetime.now() - timedelta(days=days)
    
    # Generate report
    report = reporter.generate_reconciliation_report(start_date=start_date)
    
    if report.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=report.get("error", "Failed to generate reconciliation summary")
        )
    
    # Extract summary
    summary = report.get("summary", {})
    summary["period_days"] = days
    
    return {
        "status": "success",
        "summary": summary
    }
    
@router.get("/config/thresholds")
async def get_alert_thresholds(
    current_user = Depends(get_current_active_user),
    reporter = Depends(get_reconciliation_reporter)
):
    """
    Get current alert threshold configuration.
    
    Returns:
        Current threshold configuration
    """
    try:
        # Get the reconciliation job from the reporter
        job = reporter.reconciliation_job
        
        # Get thresholds from the job
        thresholds = job.alert_thresholds
        
        return {
            "status": "success",
            "thresholds": thresholds
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert thresholds: {str(e)}"
        )

@router.post("/config/thresholds")
async def update_alert_thresholds(
    thresholds: Dict[str, Union[float, int]] = Body(..., embed=True),
    current_user = Depends(get_current_active_user),
    reporter = Depends(get_reconciliation_reporter)
):
    """
    Update alert threshold configuration.
    
    Args:
        thresholds: New threshold configuration
        
    Returns:
        Updated threshold configuration
    """
    try:
        # Validate thresholds
        required_keys = ['mismatch_percentage', 'missing_orders', 'extra_orders']
        for key in required_keys:
            if key not in thresholds:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required threshold: {key}"
                )
        
        # Validate threshold values
        if thresholds['mismatch_percentage'] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mismatch percentage threshold must be non-negative"
            )
        
        if thresholds['missing_orders'] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing orders threshold must be non-negative"
            )
            
        if thresholds['extra_orders'] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extra orders threshold must be non-negative"
            )
        
        # Get the reconciliation job from the reporter
        job = reporter.reconciliation_job
        
        # Update thresholds
        job.alert_thresholds = thresholds
        
        # Save configuration to persistent storage (implementation depends on your system)
        # This is a placeholder for actual configuration persistence
        # In a real implementation, you would save this to a database or config file
        
        return {
            "status": "success",
            "message": "Alert thresholds updated successfully",
            "thresholds": job.alert_thresholds
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert thresholds: {str(e)}"
        )