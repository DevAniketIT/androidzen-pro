"""
Reports API endpoints for AndroidZen Pro.
Handles generation of various reports including device analytics, security reports, and system usage reports.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from .core.auth import get_current_user, get_admin_user
from .core.database import get_db
from .models.user import User, UserSession
from .models.device import Device, DeviceConnectionHistory
from .models.analytics import Analytics, StorageTrend
from .models.security import SecurityEvent, SecurityAlert
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for reports
class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

class DeviceReport(BaseModel):
    device_id: str
    device_name: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    total_connections: int
    average_session_duration: float
    performance_score: float
    storage_usage: Dict[str, Any]
    security_events: int

class SystemUsageReport(BaseModel):
    report_period: DateRange
    total_devices: int
    active_devices: int
    total_connections: int
    total_sessions: int
    average_uptime: float
    storage_statistics: Dict[str, Any]
    performance_statistics: Dict[str, Any]

class SecurityReport(BaseModel):
    report_period: DateRange
    total_events: int
    critical_events: int
    high_priority_events: int
    resolved_events: int
    top_threats: List[Dict[str, Any]]
    threat_trends: Dict[str, Any]

class AnalyticsReport(BaseModel):
    report_period: DateRange
    device_count: int
    performance_trends: Dict[str, Any]
    storage_trends: Dict[str, Any]
    optimization_effectiveness: Dict[str, Any]

# Device Reports
@router.get("/devices/summary")
async def get_devices_summary_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a summary report of all devices.
    """
    try:
        # Set default date range if not provided (last 30 days)
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get all devices
        devices = db.query(Device).all()
        device_reports = []
        
        for device in devices:
            # Get connection history
            connections = db.query(DeviceConnectionHistory).filter(
                DeviceConnectionHistory.device_id == device.id,
                DeviceConnectionHistory.timestamp >= start_date,
                DeviceConnectionHistory.timestamp <= end_date
            ).all()
            
            # Calculate connection statistics
            total_connections = len([c for c in connections if c.event_type == "connected"])
            avg_session_duration = 0
            if connections:
                durations = [c.session_duration for c in connections if c.session_duration]
                if durations:
                    avg_session_duration = sum(durations) / len(durations)
            
            # Get performance data
            analytics = db.query(Analytics).filter(
                Analytics.device_id == device.id,
                Analytics.recorded_at >= start_date,
                Analytics.recorded_at <= end_date
            ).all()
            
            avg_performance = 0
            if analytics:
                scores = [a.performance_score for a in analytics if a.performance_score]
                if scores:
                    avg_performance = sum(scores) / len(scores)
            
            # Get security events
            security_events_count = db.query(SecurityEvent).filter(
                SecurityEvent.device_id == device.id,
                SecurityEvent.detected_at >= start_date,
                SecurityEvent.detected_at <= end_date
            ).count()
            
            # Get storage information
            storage_info = {}
            if analytics:
                latest_analytics = sorted(analytics, key=lambda x: x.recorded_at, reverse=True)
                if latest_analytics:
                    latest = latest_analytics[0]
                    storage_info = {
                        "total": latest.storage_total,
                        "used": latest.storage_used,
                        "free": latest.storage_free,
                        "usage_percentage": latest.storage_used_percentage
                    }
            
            device_reports.append(DeviceReport(
                device_id=device.device_id,
                device_name=device.device_name,
                manufacturer=device.manufacturer,
                model=device.model,
                total_connections=total_connections,
                average_session_duration=avg_session_duration,
                performance_score=avg_performance,
                storage_usage=storage_info,
                security_events=security_events_count
            ))
        
        logger.info(f"User {current_user['username']} generated devices summary report")
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_devices": len(devices),
            "devices": device_reports
        }
    
    except Exception as e:
        logger.error(f"Error generating devices summary report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate devices summary report"
        )

@router.get("/devices/{device_id}/detailed")
async def get_device_detailed_report(
    device_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a detailed report for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get detailed analytics
    analytics = db.query(Analytics).filter(
        Analytics.device_id == device.id,
        Analytics.recorded_at >= start_date,
        Analytics.recorded_at <= end_date
    ).order_by(Analytics.recorded_at.desc()).all()
    
    # Get connection history
    connections = db.query(DeviceConnectionHistory).filter(
        DeviceConnectionHistory.device_id == device.id,
        DeviceConnectionHistory.timestamp >= start_date,
        DeviceConnectionHistory.timestamp <= end_date
    ).order_by(DeviceConnectionHistory.timestamp.desc()).all()
    
    # Get security events
    security_events = db.query(SecurityEvent).filter(
        SecurityEvent.device_id == device.id,
        SecurityEvent.detected_at >= start_date,
        SecurityEvent.detected_at <= end_date
    ).order_by(SecurityEvent.detected_at.desc()).all()
    
    # Get storage trends
    storage_trends = db.query(StorageTrend).filter(
        StorageTrend.device_id == device.id,
        StorageTrend.period_start >= start_date,
        StorageTrend.period_start <= end_date
    ).all()
    
    logger.info(f"User {current_user['username']} generated detailed report for device {device_id}")
    
    return {
        "device": device.to_dict(),
        "report_period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "analytics": [a.to_dict() for a in analytics],
        "connection_history": [c.to_dict() for c in connections],
        "security_events": [s.to_dict() for s in security_events],
        "storage_trends": [t.to_dict() for t in storage_trends]
    }

# System Usage Reports
@router.get("/system/usage", response_model=SystemUsageReport)
async def get_system_usage_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a system usage report.
    """
    try:
        # Set default date range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get system statistics
        total_devices = db.query(Device).count()
        active_devices = db.query(Device).filter(Device.is_active == True).count()
        
        # Connection statistics
        total_connections = db.query(DeviceConnectionHistory).filter(
            DeviceConnectionHistory.timestamp >= start_date,
            DeviceConnectionHistory.timestamp <= end_date
        ).count()
        
        # User session statistics
        total_sessions = db.query(UserSession).filter(
            UserSession.created_at >= start_date,
            UserSession.created_at <= end_date
        ).count()
        
        # Calculate average uptime (simplified)
        avg_uptime = 95.5  # This would be calculated from actual uptime data
        
        # Storage statistics
        storage_analytics = db.query(Analytics).filter(
            Analytics.recorded_at >= start_date,
            Analytics.recorded_at <= end_date
        ).all()
        
        storage_stats = {}
        if storage_analytics:
            total_storage = sum([a.storage_total for a in storage_analytics if a.storage_total]) or 0
            total_used = sum([a.storage_used for a in storage_analytics if a.storage_used]) or 0
            avg_usage = (total_used / total_storage * 100) if total_storage > 0 else 0
            
            storage_stats = {
                "total_storage_gb": total_storage / (1024**3),
                "total_used_gb": total_used / (1024**3),
                "average_usage_percent": avg_usage
            }
        
        # Performance statistics
        performance_stats = {}
        if storage_analytics:
            performance_scores = [a.performance_score for a in storage_analytics if a.performance_score]
            if performance_scores:
                performance_stats = {
                    "average_performance_score": sum(performance_scores) / len(performance_scores),
                    "min_performance_score": min(performance_scores),
                    "max_performance_score": max(performance_scores)
                }
        
        return SystemUsageReport(
            report_period=DateRange(start_date=start_date, end_date=end_date),
            total_devices=total_devices,
            active_devices=active_devices,
            total_connections=total_connections,
            total_sessions=total_sessions,
            average_uptime=avg_uptime,
            storage_statistics=storage_stats,
            performance_statistics=performance_stats
        )
    
    except Exception as e:
        logger.error(f"Error generating system usage report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate system usage report"
        )

# Security Reports
@router.get("/security/summary", response_model=SecurityReport)
async def get_security_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a security summary report.
    """
    try:
        # Set default date range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get security events
        security_events = db.query(SecurityEvent).filter(
            SecurityEvent.detected_at >= start_date,
            SecurityEvent.detected_at <= end_date
        ).all()
        
        total_events = len(security_events)
        critical_events = len([e for e in security_events if e.severity == "critical"])
        high_priority_events = len([e for e in security_events if e.severity == "high"])
        resolved_events = len([e for e in security_events if e.status == "resolved"])
        
        # Get top threats
        threat_counts = {}
        for event in security_events:
            threat_type = event.event_type
            if threat_type in threat_counts:
                threat_counts[threat_type] += 1
            else:
                threat_counts[threat_type] = 1
        
        top_threats = [
            {"threat_type": threat, "count": count}
            for threat, count in sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Calculate threat trends (simplified)
        threat_trends = {
            "trend": "stable",  # This would be calculated from historical data
            "change_percentage": 0.0
        }
        
        logger.info(f"User {current_user['username']} generated security report")
        
        return SecurityReport(
            report_period=DateRange(start_date=start_date, end_date=end_date),
            total_events=total_events,
            critical_events=critical_events,
            high_priority_events=high_priority_events,
            resolved_events=resolved_events,
            top_threats=top_threats,
            threat_trends=threat_trends
        )
    
    except Exception as e:
        logger.error(f"Error generating security report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate security report"
        )

# Analytics Reports
@router.get("/analytics/summary", response_model=AnalyticsReport)
async def get_analytics_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an analytics summary report.
    """
    try:
        # Set default date range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get analytics data
        analytics = db.query(Analytics).filter(
            Analytics.recorded_at >= start_date,
            Analytics.recorded_at <= end_date
        ).all()
        
        device_count = db.query(Device).filter(
            Device.created_at <= end_date
        ).count()
        
        # Calculate performance trends
        performance_trends = {}
        if analytics:
            performance_scores = [a.performance_score for a in analytics if a.performance_score]
            cpu_usage = [a.cpu_usage for a in analytics if a.cpu_usage]
            memory_usage = [a.memory_usage for a in analytics if a.memory_usage]
            
            if performance_scores:
                performance_trends["average_performance_score"] = sum(performance_scores) / len(performance_scores)
            if cpu_usage:
                performance_trends["average_cpu_usage"] = sum(cpu_usage) / len(cpu_usage)
            if memory_usage:
                performance_trends["average_memory_usage"] = sum(memory_usage) / len(memory_usage)
        
        # Get storage trends
        storage_trends_data = db.query(StorageTrend).filter(
            StorageTrend.period_start >= start_date,
            StorageTrend.period_start <= end_date
        ).all()
        
        storage_trends = {}
        if storage_trends_data:
            growth_rates = [t.growth_rate for t in storage_trends_data if t.growth_rate]
            if growth_rates:
                storage_trends["average_growth_rate"] = sum(growth_rates) / len(growth_rates)
        
        # Optimization effectiveness (simplified)
        optimization_effectiveness = {
            "total_optimizations": 0,  # This would be tracked from optimization actions
            "average_improvement": 0.0,
            "success_rate": 0.0
        }
        
        logger.info(f"User {current_user['username']} generated analytics report")
        
        return AnalyticsReport(
            report_period=DateRange(start_date=start_date, end_date=end_date),
            device_count=device_count,
            performance_trends=performance_trends,
            storage_trends=storage_trends,
            optimization_effectiveness=optimization_effectiveness
        )
    
    except Exception as e:
        logger.error(f"Error generating analytics report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analytics report"
        )

# Export Reports (Admin only)
@router.post("/export/csv")
async def export_report_csv(
    report_type: str = Query(..., description="Type of report to export"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Export a report as CSV format.
    Admin only endpoint.
    """
    # TODO: Implement CSV export functionality
    
    logger.info(f"Admin {admin_user['username']} requested CSV export for {report_type}")
    
    return {
        "message": f"CSV export for {report_type} - implementation pending",
        "report_type": report_type,
        "format": "csv"
    }

@router.post("/export/pdf")
async def export_report_pdf(
    report_type: str = Query(..., description="Type of report to export"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Export a report as PDF format.
    Admin only endpoint.
    """
    # TODO: Implement PDF export functionality
    
    logger.info(f"Admin {admin_user['username']} requested PDF export for {report_type}")
    
    return {
        "message": f"PDF export for {report_type} - implementation pending",
        "report_type": report_type,
        "format": "pdf"
    }

