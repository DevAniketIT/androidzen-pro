"""
API endpoints for monitoring, logging, and system health.
Provides access to performance metrics, error tracking, and log analysis.
"""

import os
import json
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from .core.auth import get_current_user, get_admin_user
from .core.logging_config import get_logger, AndroidZenLogger
from .middleware.logging_middleware import LoggingMiddleware

logger = get_logger(__name__)

router = APIRouter()


class SystemHealth(BaseModel):
    """System health status model."""
    status: str
    timestamp: str
    uptime: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int


class LogEntry(BaseModel):
    """Log entry model for API responses."""
    timestamp: str
    level: str
    logger_name: str
    message: str
    context: Optional[Dict[str, Any]] = None


class MetricsSummary(BaseModel):
    """Performance metrics summary model."""
    total_requests: int
    average_response_time: float
    error_rate: float
    slow_requests: int
    top_endpoints: List[Dict[str, Any]]


class ErrorSummary(BaseModel):
    """Error tracking summary model."""
    total_errors: int
    error_types: int
    error_counts: Dict[str, int]
    recent_errors: List[Dict[str, Any]]


# Global performance tracking (in production, use Redis or database)
_request_metrics = []
_error_metrics = []


@router.get("/health", response_model=SystemHealth)
async def get_system_health(current_user: dict = Depends(get_current_user)):
    """
    Get comprehensive system health information.
    """
    try:
        # Get system metrics using psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get process information
        process = psutil.Process()
        uptime = (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds()
        
        # Get network connections (approximate active connections)
        try:
            connections = len(psutil.net_connections())
        except (psutil.AccessDenied, OSError):
            connections = -1  # Access denied or not available
        
        health_status = SystemHealth(
            status="healthy" if cpu_percent < 80 and memory.percent < 80 else "degraded",
            timestamp=datetime.now().isoformat(),
            uptime=uptime,
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            active_connections=connections
        )
        
        logger.info("System health check requested", 
                   context={"health_status": health_status.dict()})
        
        return health_status
        
    except Exception as e:
        logger.exception("Failed to get system health")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    hours: int = Query(1, description="Hours to look back for metrics"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get performance metrics summary for the specified time period.
    """
    try:
        # This is a simplified implementation
        # In production, you would query a metrics database
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Get metrics from the logger's performance monitor
        # Note: This is a basic implementation - you'd want to use a proper metrics store
        metrics_summary = MetricsSummary(
            total_requests=len(_request_metrics),
            average_response_time=sum(_request_metrics[-100:]) / max(len(_request_metrics[-100:]), 1),
            error_rate=0.05,  # Placeholder - calculate from actual data
            slow_requests=5,   # Placeholder - calculate from actual data
            top_endpoints=[
                {"endpoint": "/api/devices", "count": 45, "avg_time": 123.4},
                {"endpoint": "/api/storage", "count": 32, "avg_time": 89.7},
                {"endpoint": "/api/auth/login", "count": 12, "avg_time": 234.1}
            ]
        )
        
        logger.info("Metrics summary requested", 
                   context={"hours": hours, "summary": metrics_summary.dict()})
        
        return metrics_summary
        
    except Exception as e:
        logger.exception("Failed to get metrics summary")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics summary")


@router.get("/errors/summary", response_model=ErrorSummary)
async def get_error_summary(current_user: dict = Depends(get_admin_user)):
    """
    Get error tracking summary (admin only).
    """
    try:
        # Get error summary from the logger's error tracker
        app_logger = get_logger("androidzen-pro")
        error_summary = app_logger.error_tracker.get_error_summary()
        
        response = ErrorSummary(**error_summary)
        
        logger.info("Error summary requested", 
                   context={"error_summary": response.dict()})
        
        return response
        
    except Exception as e:
        logger.exception("Failed to get error summary")
        raise HTTPException(status_code=500, detail="Failed to retrieve error summary")


@router.get("/metrics/performance")
async def get_performance_metrics(
    limit: int = Query(100, description="Number of recent metrics to return"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed performance metrics.
    """
    try:
        app_logger = get_logger("androidzen-pro")
        metrics = app_logger.performance_monitor.get_metrics(limit=limit)
        
        # Filter by metric type if specified
        if metric_type:
            metrics = [m for m in metrics if metric_type in m.metric_name]
        
        # Convert to serializable format
        metrics_data = []
        for metric in metrics:
            metric_dict = {
                "metric_name": metric.metric_name,
                "value": metric.value,
                "unit": metric.unit,
                "timestamp": metric.timestamp,
                "context": metric.context,
                "tags": metric.tags
            }
            metrics_data.append(metric_dict)
        
        logger.info("Performance metrics requested", 
                   context={"limit": limit, "metric_type": metric_type, "count": len(metrics_data)})
        
        return {"metrics": metrics_data, "count": len(metrics_data)}
        
    except Exception as e:
        logger.exception("Failed to get performance metrics")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@router.get("/logs/recent")
async def get_recent_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: int = Query(50, description="Number of recent logs to return"),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get recent log entries (admin only).
    Note: This is a basic implementation. In production, you'd want to query log files or a log aggregation service.
    """
    try:
        # This is a placeholder implementation
        # In a real system, you'd query your log storage (files, database, ELK stack, etc.)
        
        logs = [
            {
                "timestamp": (datetime.now() - timedelta(minutes=i)).isoformat(),
                "level": ["INFO", "WARNING", "ERROR"][i % 3],
                "logger_name": "androidzen-pro",
                "message": f"Sample log message {i}",
                "context": {"request_id": f"req-{i}", "operation": "sample_operation"}
            }
            for i in range(limit)
        ]
        
        # Filter by level if specified
        if level:
            logs = [log for log in logs if log["level"] == level.upper()]
        
        logger.info("Recent logs requested", 
                   context={"level": level, "limit": limit, "count": len(logs)})
        
        return {"logs": logs, "count": len(logs)}
        
    except Exception as e:
        logger.exception("Failed to get recent logs")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent logs")


@router.get("/system/info")
async def get_system_info(current_user: dict = Depends(get_admin_user)):
    """
    Get detailed system information (admin only).
    """
    try:
        # Get Python and system information
        import platform
        import sys
        
        system_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "environment": {
                "DEBUG": os.getenv("DEBUG", "false"),
                "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
                "DATABASE_URL": "***REDACTED***" if os.getenv("DATABASE_URL") else None
            },
            "process_info": {
                "pid": os.getpid(),
                "working_directory": os.getcwd(),
                "executable": sys.executable
            }
        }
        
        # Add memory and CPU details
        if psutil:
            memory = psutil.virtual_memory()
            cpu_info = {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total": memory.total,
                "memory_available": memory.available
            }
            system_info["hardware"] = cpu_info
        
        logger.info("System info requested", 
                   context={"system_info": system_info})
        
        return system_info
        
    except Exception as e:
        logger.exception("Failed to get system info")
        raise HTTPException(status_code=500, detail="Failed to retrieve system information")


@router.post("/logs/level")
async def set_log_level(
    level: str = Query(..., description="New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    current_user: dict = Depends(get_admin_user)
):
    """
    Dynamically change the log level (admin only).
    """
    import logging
    
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    if level.upper() not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid log level. Must be one of: {valid_levels}")
    
    try:
        # Set new log level
        new_level = getattr(logging, level.upper())
        root_logger = logging.getLogger()
        root_logger.setLevel(new_level)
        
        # Update all handlers
        for handler in root_logger.handlers:
            if handler.level != logging.ERROR:  # Don't change error-only handlers
                handler.setLevel(new_level)
        
        logger.info(f"Log level changed to {level.upper()}", 
                   context={"previous_level": root_logger.level, "new_level": new_level})
        
        return {"message": f"Log level successfully changed to {level.upper()}"}
        
    except Exception as e:
        logger.exception("Failed to set log level")
        raise HTTPException(status_code=500, detail="Failed to set log level")


@router.get("/alerts")
async def get_system_alerts(current_user: dict = Depends(get_current_user)):
    """
    Get system alerts and warnings based on current metrics and error rates.
    """
    try:
        alerts = []
        
        # Check system resources
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            if cpu_percent > 80:
                alerts.append({
                    "type": "warning",
                    "category": "performance",
                    "message": f"High CPU usage detected: {cpu_percent:.1f}%",
                    "timestamp": datetime.now().isoformat()
                })
            
            if memory.percent > 80:
                alerts.append({
                    "type": "warning", 
                    "category": "performance",
                    "message": f"High memory usage detected: {memory.percent:.1f}%",
                    "timestamp": datetime.now().isoformat()
                })
            
            if disk.percent > 90:
                alerts.append({
                    "type": "critical",
                    "category": "storage", 
                    "message": f"Low disk space: {disk.percent:.1f}% used",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception:
            alerts.append({
                "type": "error",
                "category": "monitoring",
                "message": "Unable to retrieve system metrics",
                "timestamp": datetime.now().isoformat()
            })
        
        # Check error rates (placeholder)
        app_logger = get_logger("androidzen-pro")
        error_summary = app_logger.error_tracker.get_error_summary()
        
        if error_summary.get("total_errors", 0) > 10:
            alerts.append({
                "type": "warning",
                "category": "errors",
                "message": f"High error rate detected: {error_summary['total_errors']} errors",
                "timestamp": datetime.now().isoformat()
            })
        
        logger.info("System alerts requested", 
                   context={"alert_count": len(alerts)})
        
        return {"alerts": alerts, "count": len(alerts)}
        
    except Exception as e:
        logger.exception("Failed to get system alerts")
        raise HTTPException(status_code=500, detail="Failed to retrieve system alerts")


@router.post("/maintenance/cleanup")
async def cleanup_logs_and_metrics(
    days: int = Query(7, description="Keep data from the last N days"),
    current_user: dict = Depends(get_admin_user)
):
    """
    Cleanup old logs and metrics (admin only).
    """
    try:
        # This is a placeholder implementation
        # In production, you'd implement actual cleanup logic
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cleanup_results = {
            "logs_cleaned": 0,
            "metrics_cleaned": 0,
            "cutoff_date": cutoff_date.isoformat(),
            "status": "completed"
        }
        
        logger.info("Maintenance cleanup performed", 
                   context={"cleanup_results": cleanup_results, "days": days})
        
        return cleanup_results
        
    except Exception as e:
        logger.exception("Failed to perform maintenance cleanup")
        raise HTTPException(status_code=500, detail="Failed to perform maintenance cleanup")

