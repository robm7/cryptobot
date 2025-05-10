"""
Performance API Router

This module provides API endpoints for the performance dashboard.
"""

import os
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from utils.query_optimizer import get_query_stats, reset_query_stats, optimize_database
from utils.cache_manager import get_cache_stats, reset_cache_stats
from utils.rate_limiter import get_rate_limit_stats, reset_rate_limit_stats
from utils.memory_optimizer import get_memory_stats, reset_memory_stats, optimize_memory
from utils.performance_monitor import get_performance_stats, reset_performance_stats, save_performance_report
from utils.performance_optimizer import (
    get_config, update_config, save_config, apply_profile, optimize_all
)
from database import get_db
from auth_service import get_current_active_user

router = APIRouter(prefix="/performance", tags=["performance"])

class PerformanceConfig(BaseModel):
    """Performance configuration model"""
    query_optimizer: Optional[Dict[str, Any]] = None
    cache_manager: Optional[Dict[str, Any]] = None
    rate_limiter: Optional[Dict[str, Any]] = None
    memory_optimizer: Optional[Dict[str, Any]] = None
    performance_monitor: Optional[Dict[str, Any]] = None

@router.get("/stats")
async def get_stats(current_user = Depends(get_current_active_user)):
    """
    Get performance statistics.
    
    Returns:
        Performance statistics
    """
    # Get statistics from all components
    stats = {
        "query_stats": get_query_stats(),
        "cache_stats": get_cache_stats(),
        "rate_limit_stats": get_rate_limit_stats(),
        "memory_stats": get_memory_stats(),
        "performance_stats": get_performance_stats()
    }
    
    # Extract bottlenecks
    stats["bottlenecks"] = stats["performance_stats"].get("bottlenecks", [])
    
    # Extract slow queries
    stats["slow_queries"] = stats["performance_stats"].get("slow_queries", [])
    
    # Extract slow functions
    stats["slow_functions"] = stats["performance_stats"].get("slow_functions", [])
    
    # Extract slow endpoints
    stats["slow_endpoints"] = stats["performance_stats"].get("slow_endpoints", [])
    
    # Extract system stats
    stats["system_stats"] = stats["performance_stats"].get("system_stats", {})
    
    # Extract database stats
    stats["database_stats"] = stats["performance_stats"].get("database_stats", {})
    
    # Extract function stats
    stats["function_stats"] = stats["performance_stats"].get("function_stats", {})
    
    # Extract endpoint stats
    stats["endpoint_stats"] = stats["performance_stats"].get("endpoint_stats", {})
    
    # Extract exchange stats
    stats["exchange_stats"] = stats["performance_stats"].get("exchange_stats", {})
    
    return stats

@router.post("/reset")
async def reset_stats(current_user = Depends(get_current_active_user)):
    """
    Reset performance statistics.
    
    Returns:
        Success message
    """
    # Reset statistics for all components
    reset_query_stats()
    reset_cache_stats()
    reset_rate_limit_stats()
    reset_memory_stats()
    reset_performance_stats()
    
    return {"message": "Performance statistics reset successfully"}

@router.get("/config")
async def get_configuration(current_user = Depends(get_current_active_user)):
    """
    Get performance configuration.
    
    Returns:
        Performance configuration
    """
    return get_config()

@router.post("/config")
async def update_configuration(
    config: PerformanceConfig,
    current_user = Depends(get_current_active_user)
):
    """
    Update performance configuration.
    
    Args:
        config: Performance configuration
        
    Returns:
        Success message
    """
    # Update configuration
    success = update_config(config.dict(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )
    
    # Save configuration to file
    save_config()
    
    return {"success": True, "message": "Configuration updated successfully"}

@router.post("/profile/{profile}")
async def apply_configuration_profile(
    profile: str,
    current_user = Depends(get_current_active_user)
):
    """
    Apply a configuration profile.
    
    Args:
        profile: Profile name
        
    Returns:
        Success message
    """
    # Apply profile
    success = apply_profile(profile)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile '{profile}' not found"
        )
    
    return {"success": True, "message": f"Profile '{profile}' applied successfully"}

@router.post("/optimize")
async def optimize_performance(
    current_user = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    Optimize performance.
    
    Returns:
        Optimization results
    """
    # Optimize all components
    results = optimize_all(db)
    
    # Optimize memory
    memory_results = optimize_memory()
    results["memory"] = memory_results
    
    return results

@router.post("/report")
async def generate_report(
    current_user = Depends(get_current_active_user)
):
    """
    Generate a performance report.
    
    Returns:
        Report file path
    """
    # Create reports directory if it doesn't exist
    os.makedirs("reports", exist_ok=True)
    
    # Generate timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Generate report file path
    report_path = f"reports/performance_report_{timestamp}.json"
    
    # Save report
    save_performance_report(report_path)
    
    return {"report_path": report_path}

@router.get("/reports")
async def list_reports(current_user = Depends(get_current_active_user)):
    """
    List performance reports.
    
    Returns:
        List of report files
    """
    # Check if reports directory exists
    if not os.path.exists("reports"):
        return {"reports": []}
    
    # List report files
    reports = []
    for filename in os.listdir("reports"):
        if filename.startswith("performance_report_") and filename.endswith(".json"):
            file_path = os.path.join("reports", filename)
            file_stat = os.stat(file_path)
            
            # Get report timestamp from filename
            timestamp_str = filename.replace("performance_report_", "").replace(".json", "")
            
            try:
                # Parse timestamp
                from datetime import datetime
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                
                reports.append({
                    "filename": filename,
                    "path": file_path,
                    "size": file_stat.st_size,
                    "created_at": timestamp.isoformat(),
                    "timestamp": timestamp_str
                })
            except ValueError:
                # Skip files with invalid timestamps
                continue
    
    # Sort reports by timestamp (newest first)
    reports.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"reports": reports}

@router.get("/reports/{timestamp}")
async def get_report(
    timestamp: str,
    current_user = Depends(get_current_active_user)
):
    """
    Get a performance report.
    
    Args:
        timestamp: Report timestamp
        
    Returns:
        Report data
    """
    # Generate report file path
    report_path = f"reports/performance_report_{timestamp}.json"
    
    # Check if report exists
    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with timestamp '{timestamp}' not found"
        )
    
    # Load report
    try:
        with open(report_path, "r") as f:
            report = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse report file"
        )
    
    return report

@router.delete("/reports/{timestamp}")
async def delete_report(
    timestamp: str,
    current_user = Depends(get_current_active_user)
):
    """
    Delete a performance report.
    
    Args:
        timestamp: Report timestamp
        
    Returns:
        Success message
    """
    # Generate report file path
    report_path = f"reports/performance_report_{timestamp}.json"
    
    # Check if report exists
    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with timestamp '{timestamp}' not found"
        )
    
    # Delete report
    try:
        os.remove(report_path)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete report: {str(e)}"
        )
    
    return {"message": f"Report with timestamp '{timestamp}' deleted successfully"}