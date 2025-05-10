"""
Performance Dashboard Controller

This module provides route handlers for the performance dashboard web interface.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from auth_service import get_current_active_user
from utils.performance_optimizer import get_config

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create router
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/performance", response_class=HTMLResponse)
async def performance_dashboard(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """
    Render the performance dashboard.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        HTML response
    """
    # Get configuration
    config = get_config()
    
    # Render template
    return templates.TemplateResponse(
        "performance_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "config": config
        }
    )

@router.get("/performance/reports/{timestamp}", response_class=HTMLResponse)
async def performance_report(
    request: Request,
    timestamp: str,
    current_user = Depends(get_current_active_user)
):
    """
    Render a performance report.
    
    Args:
        request: FastAPI request object
        timestamp: Report timestamp
        current_user: Current authenticated user
        
    Returns:
        HTML response
    """
    # Generate report file path
    report_path = f"reports/performance_report_{timestamp}.json"
    
    # Check if report exists
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Load report
    import json
    try:
        with open(report_path, "r") as f:
            report = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse report file")
    
    # Render template
    return templates.TemplateResponse(
        "performance_report.html",
        {
            "request": request,
            "user": current_user,
            "report": report,
            "timestamp": timestamp
        }
    )

@router.get("/performance/config", response_class=HTMLResponse)
async def performance_config(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """
    Render the performance configuration page.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        HTML response
    """
    # Get configuration
    config = get_config()
    
    # Render template
    return templates.TemplateResponse(
        "performance_config.html",
        {
            "request": request,
            "user": current_user,
            "config": config
        }
    )

def register_routes(app):
    """
    Register routes with the FastAPI application.
    
    Args:
        app: FastAPI application
    """
    app.include_router(router)