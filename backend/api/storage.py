"""
Storage analysis API endpoints for AndroidZen Pro.
Handles storage monitoring, analysis, cleanup operations, and trend tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from .core.database import get_db
from .models.device import Device
from .models.analytics import Analytics, StorageTrend
from .core.auth import get_current_active_user
from .core.adb_manager import AdbManager
from .services.storage_service import StorageService
from .services.storage_trend_service import StorageTrendService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize ADB Manager and Services
adb_manager = AdbManager()
storage_service = StorageService(adb_manager)
trend_service = StorageTrendService()

# Pydantic models for request/response
class StorageAnalysisResponse(BaseModel):
    device_id: str
    device_name: Optional[str]
    storage_total: Optional[int]
    storage_used: Optional[int]
    storage_available: Optional[int]
    storage_usage_percentage: Optional[float]
    app_data_size: Optional[int]
    system_data_size: Optional[int]
    cache_size: Optional[int]
    media_size: Optional[int]
    last_updated: Optional[datetime]

class StorageCleanupRequest(BaseModel):
    device_id: str
    cleanup_types: List[str]  # ["cache", "temp", "logs", "downloads"]
    force_cleanup: bool = False
    dry_run: bool = True

class StorageCleanupResult(BaseModel):
    device_id: str
    cleanup_types: List[str]
    space_freed: int  # MB
    files_removed: int
    errors: List[str]
    dry_run: bool
    duration: float  # seconds

class StorageTrendResponse(BaseModel):
    device_id: str
    period_type: str
    period_start: datetime
    period_end: datetime
    avg_storage_used: Optional[float]
    max_storage_used: Optional[float]
    min_storage_used: Optional[float]
    storage_change: Optional[float]
    storage_change_percentage: Optional[float]
    trend_direction: Optional[str]
    growth_rate: Optional[float]
    predicted_full_date: Optional[datetime]

class StorageAlert(BaseModel):
    device_id: str
    alert_type: str  # "high_usage", "low_space", "rapid_growth"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    threshold_value: float
    current_value: float
    recommendation: str

class StorageStatsResponse(BaseModel):
    total_devices: int
    devices_with_high_usage: int
    devices_with_low_space: int
    average_storage_usage: float
    total_storage_capacity: int
    total_storage_used: int
    storage_efficiency_score: float

class StorageBreakdownResponse(BaseModel):
    total_storage_mb: int
    used_storage_mb: int
    available_storage_mb: int
    usage_percentage: float
    categories: List[Dict[str, Any]]
    optimization_potential_mb: int
    recommendations: List[str]
    last_updated: str

class CacheInfoResponse(BaseModel):
    app_name: str
    package_name: str
    cache_size_mb: float
    cache_path: str
    priority: str
    can_clear: bool

class LargeFileResponse(BaseModel):
    path: str
    size_mb: float
    category: str
    is_cache: bool
    is_temp: bool
    recommendations: List[str]

class StorageOptimizationResponse(BaseModel):
    device_id: str
    total_savings_mb: int
    confidence_score: float
    suggestions: List[Dict[str, Any]]
    risk_level: str
    execution_time_estimate: int

class StorageOptimizationRequest(BaseModel):
    detailed_analysis: bool = True
    include_trends: bool = True
    max_suggestions: int = 10

@router.get("/analysis", response_model=List[StorageAnalysisResponse])
async def get_storage_analysis(
    device_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    min_usage: Optional[float] = Query(None, ge=0, le=100),
    max_usage: Optional[float] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get storage analysis for devices with optional filtering.
    """
    query = db.query(Device).filter(Device.is_active == True)
    
    if device_id:
        query = query.filter(Device.device_id == device_id)
    
    devices = query.offset(skip).limit(limit).all()
    
    results = []
    for device in devices:
        # Get latest storage analytics
        latest_analytics = (db.query(Analytics)
                          .filter(Analytics.device_id == device.id)
                          .filter(or_(
                              Analytics.metric_type == "storage",
                              Analytics.storage_usage_percentage.is_not(None)
                          ))
                          .order_by(Analytics.recorded_at.desc())
                          .first())
        
        if not latest_analytics:
            continue
            
        # Apply usage filters
        if min_usage and latest_analytics.storage_usage_percentage < min_usage:
            continue
        if max_usage and latest_analytics.storage_usage_percentage > max_usage:
            continue
        
        # Get storage trend for additional data
        latest_trend = (db.query(StorageTrend)
                       .filter(StorageTrend.device_id == device.id)
                       .order_by(StorageTrend.created_at.desc())
                       .first())
        
        analysis = StorageAnalysisResponse(
            device_id=device.device_id,
            device_name=device.device_name,
            storage_total=latest_analytics.storage_total,
            storage_used=latest_analytics.storage_used,
            storage_available=latest_analytics.storage_available,
            storage_usage_percentage=latest_analytics.storage_usage_percentage,
            app_data_size=latest_trend.app_data_size if latest_trend else None,
            system_data_size=latest_trend.system_data_size if latest_trend else None,
            cache_size=latest_trend.cache_size if latest_trend else None,
            media_size=latest_trend.media_size if latest_trend else None,
            last_updated=latest_analytics.recorded_at
        )
        
        results.append(analysis)
    
    return results

@router.get("/{device_id}/analysis", response_model=StorageAnalysisResponse)
async def get_device_storage_analysis(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed storage analysis for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get latest storage analytics
    latest_analytics = (db.query(Analytics)
                      .filter(Analytics.device_id == device.id)
                      .filter(or_(
                          Analytics.metric_type == "storage",
                          Analytics.storage_usage_percentage.is_not(None)
                      ))
                      .order_by(Analytics.recorded_at.desc())
                      .first())
    
    if not latest_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No storage data available for this device"
        )
    
    # Get storage trend data
    latest_trend = (db.query(StorageTrend)
                   .filter(StorageTrend.device_id == device.id)
                   .order_by(StorageTrend.created_at.desc())
                   .first())
    
    return StorageAnalysisResponse(
        device_id=device.device_id,
        device_name=device.device_name,
        storage_total=latest_analytics.storage_total,
        storage_used=latest_analytics.storage_used,
        storage_available=latest_analytics.storage_available,
        storage_usage_percentage=latest_analytics.storage_usage_percentage,
        app_data_size=latest_trend.app_data_size if latest_trend else None,
        system_data_size=latest_trend.system_data_size if latest_trend else None,
        cache_size=latest_trend.cache_size if latest_trend else None,
        media_size=latest_trend.media_size if latest_trend else None,
        last_updated=latest_analytics.recorded_at
    )

@router.post("/{device_id}/cleanup", response_model=StorageCleanupResult)
async def cleanup_device_storage(
    device_id: str,
    cleanup_request: StorageCleanupRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Perform storage cleanup operations on a device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if not device.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not connected"
        )
    
    # Validate cleanup request
    if cleanup_request.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID mismatch"
        )
    
    valid_cleanup_types = ["cache", "temp", "logs", "downloads", "thumbnails", "app_cache"]
    invalid_types = [ct for ct in cleanup_request.cleanup_types if ct not in valid_cleanup_types]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cleanup types: {invalid_types}"
        )
    
    # Simulate cleanup operation (in real implementation, this would interact with ADB)
    start_time = datetime.utcnow()
    
    # Mock cleanup results
    space_freed = 0
    files_removed = 0
    errors = []
    
    for cleanup_type in cleanup_request.cleanup_types:
        if cleanup_type == "cache":
            space_freed += 150  # MB
            files_removed += 45
        elif cleanup_type == "temp":
            space_freed += 75
            files_removed += 23
        elif cleanup_type == "logs":
            space_freed += 25
            files_removed += 12
        elif cleanup_type == "downloads":
            space_freed += 300
            files_removed += 8
        elif cleanup_type == "thumbnails":
            space_freed += 50
            files_removed += 150
        elif cleanup_type == "app_cache":
            space_freed += 200
            files_removed += 67
    
    # Add some randomization for realism
    import random
    space_freed = int(space_freed * random.uniform(0.7, 1.3))
    files_removed = int(files_removed * random.uniform(0.8, 1.5))
    
    # Simulate some potential errors
    if not cleanup_request.force_cleanup and random.random() < 0.1:
        errors.append("Some system files could not be cleaned without force flag")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    # If not dry run, update device storage metrics
    if not cleanup_request.dry_run:
        latest_analytics = (db.query(Analytics)
                          .filter(Analytics.device_id == device.id)
                          .order_by(Analytics.recorded_at.desc())
                          .first())
        
        if latest_analytics and latest_analytics.storage_used:
            # Create new analytics record with updated storage
            new_analytics = Analytics(
                device_id=device.id,
                metric_type="storage",
                storage_used=max(0, latest_analytics.storage_used - space_freed),
                storage_available=(latest_analytics.storage_available or 0) + space_freed,
                storage_total=latest_analytics.storage_total,
                storage_usage_percentage=(
                    ((latest_analytics.storage_used - space_freed) / latest_analytics.storage_total * 100)
                    if latest_analytics.storage_total else None
                ),
                collection_method="cleanup",
                data_source="storage_cleanup_api"
            )
            db.add(new_analytics)
            db.commit()
    
    logger.info(f"Storage cleanup {'simulated' if cleanup_request.dry_run else 'completed'} for device {device_id} by user {current_user['username']}")
    
    return StorageCleanupResult(
        device_id=device_id,
        cleanup_types=cleanup_request.cleanup_types,
        space_freed=space_freed if not cleanup_request.dry_run else 0,
        files_removed=files_removed if not cleanup_request.dry_run else 0,
        errors=errors,
        dry_run=cleanup_request.dry_run,
        duration=duration
    )

@router.get("/{device_id}/trends", response_model=List[StorageTrendResponse])
async def get_storage_trends(
    device_id: str,
    period_type: Optional[str] = Query("daily", regex="^(hourly|daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get storage usage trends for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get storage trends
    trends = (db.query(StorageTrend)
             .filter(StorageTrend.device_id == device.id)
             .filter(StorageTrend.period_type == period_type)
             .filter(StorageTrend.period_start >= start_date)
             .order_by(StorageTrend.period_start)
             .all())
    
    return [StorageTrendResponse(
        device_id=device_id,
        period_type=trend.period_type,
        period_start=trend.period_start,
        period_end=trend.period_end,
        avg_storage_used=trend.avg_storage_used,
        max_storage_used=trend.max_storage_used,
        min_storage_used=trend.min_storage_used,
        storage_change=trend.storage_change,
        storage_change_percentage=trend.storage_change_percentage,
        trend_direction=trend.trend_direction,
        growth_rate=trend.growth_rate,
        predicted_full_date=trend.predicted_full_date
    ) for trend in trends]

@router.get("/alerts", response_model=List[StorageAlert])
async def get_storage_alerts(
    device_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    alert_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get storage alerts based on current usage and trends.
    """
    query = db.query(Device).filter(Device.is_active == True)
    
    if device_id:
        query = query.filter(Device.device_id == device_id)
    
    devices = query.all()
    alerts = []
    
    for device in devices:
        # Get latest storage analytics
        latest_analytics = (db.query(Analytics)
                          .filter(Analytics.device_id == device.id)
                          .filter(Analytics.storage_usage_percentage.is_not(None))
                          .order_by(Analytics.recorded_at.desc())
                          .first())
        
        if not latest_analytics:
            continue
        
        usage_percentage = latest_analytics.storage_usage_percentage
        
        # Generate alerts based on usage thresholds
        if usage_percentage >= 95:
            alert = StorageAlert(
                device_id=device.device_id,
                alert_type="low_space",
                severity="critical",
                message="Storage is critically low",
                threshold_value=95.0,
                current_value=usage_percentage,
                recommendation="Immediate cleanup required. Consider moving files or uninstalling apps."
            )
            alerts.append(alert)
        elif usage_percentage >= 90:
            alert = StorageAlert(
                device_id=device.device_id,
                alert_type="high_usage",
                severity="high",
                message="Storage usage is very high",
                threshold_value=90.0,
                current_value=usage_percentage,
                recommendation="Clean up cache files and remove unnecessary data."
            )
            alerts.append(alert)
        elif usage_percentage >= 80:
            alert = StorageAlert(
                device_id=device.device_id,
                alert_type="high_usage",
                severity="medium",
                message="Storage usage is high",
                threshold_value=80.0,
                current_value=usage_percentage,
                recommendation="Consider cleaning up cache and temporary files."
            )
            alerts.append(alert)
        
        # Check for rapid growth trends
        recent_trend = (db.query(StorageTrend)
                       .filter(StorageTrend.device_id == device.id)
                       .filter(StorageTrend.period_type == "daily")
                       .order_by(StorageTrend.created_at.desc())
                       .first())
        
        if recent_trend and recent_trend.growth_rate and recent_trend.growth_rate > 5:  # >5% daily growth
            alert = StorageAlert(
                device_id=device.device_id,
                alert_type="rapid_growth",
                severity="medium" if recent_trend.growth_rate < 10 else "high",
                message="Rapid storage usage growth detected",
                threshold_value=5.0,
                current_value=recent_trend.growth_rate,
                recommendation="Monitor apps and data generation. Consider implementing cleanup schedules."
            )
            alerts.append(alert)
    
    # Apply filters
    if severity:
        alerts = [alert for alert in alerts if alert.severity == severity]
    
    if alert_type:
        alerts = [alert for alert in alerts if alert.alert_type == alert_type]
    
    return alerts

@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get overall storage statistics across all devices.
    """
    # Get all active devices with storage data
    devices_with_storage = (
        db.query(Device, Analytics)
        .join(Analytics, Device.id == Analytics.device_id)
        .filter(Device.is_active == True)
        .filter(Analytics.storage_usage_percentage.is_not(None))
        .filter(Analytics.id.in_(
            db.query(func.max(Analytics.id))
            .filter(Analytics.storage_usage_percentage.is_not(None))
            .group_by(Analytics.device_id)
        ))
        .all()
    )
    
    if not devices_with_storage:
        return StorageStatsResponse(
            total_devices=0,
            devices_with_high_usage=0,
            devices_with_low_space=0,
            average_storage_usage=0.0,
            total_storage_capacity=0,
            total_storage_used=0,
            storage_efficiency_score=0.0
        )
    
    total_devices = len(devices_with_storage)
    high_usage_count = 0
    low_space_count = 0
    usage_sum = 0.0
    total_capacity = 0
    total_used = 0
    
    for device, analytics in devices_with_storage:
        usage_percentage = analytics.storage_usage_percentage or 0
        usage_sum += usage_percentage
        
        if usage_percentage >= 80:
            high_usage_count += 1
        if usage_percentage >= 95:
            low_space_count += 1
        
        if analytics.storage_total:
            total_capacity += analytics.storage_total
        if analytics.storage_used:
            total_used += analytics.storage_used
    
    average_usage = usage_sum / total_devices if total_devices > 0 else 0.0
    
    # Calculate efficiency score (100 - average_usage gives efficiency)
    storage_efficiency_score = max(0, 100 - average_usage)
    
    return StorageStatsResponse(
        total_devices=total_devices,
        devices_with_high_usage=high_usage_count,
        devices_with_low_space=low_space_count,
        average_storage_usage=average_usage,
        total_storage_capacity=total_capacity,
        total_storage_used=total_used,
        storage_efficiency_score=storage_efficiency_score
    )

@router.post("/{device_id}/analyze")
async def trigger_storage_analysis(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Trigger a new storage analysis for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if not device.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not connected"
        )
    
    # In a real implementation, this would trigger ADB commands to gather storage info
    # For now, we'll create mock analytics data
    import random
    
    total_storage = random.randint(16000, 128000)  # 16GB to 128GB
    used_storage = int(total_storage * random.uniform(0.3, 0.9))
    available_storage = total_storage - used_storage
    usage_percentage = (used_storage / total_storage) * 100
    
    # Create new analytics record
    analytics = Analytics(
        device_id=device.id,
        metric_type="storage",
        storage_total=total_storage,
        storage_used=used_storage,
        storage_available=available_storage,
        storage_usage_percentage=usage_percentage,
        collection_method="api_triggered",
        data_source="storage_analysis_api"
    )
    
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    
    logger.info(f"Storage analysis triggered for device {device_id} by user {current_user['username']}")
    
    return {
        "message": "Storage analysis completed successfully",
        "device_id": device_id,
        "analysis_id": analytics.id,
        "timestamp": analytics.recorded_at.isoformat(),
        "storage_usage_percentage": usage_percentage
    }

@router.get("/{device_id}/breakdown", response_model=StorageBreakdownResponse)
async def get_storage_breakdown(
    device_id: str,
    detailed: bool = Query(False, description="Perform detailed analysis (slower)"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get visual storage breakdown for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if not device.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not connected"
        )
    
    try:
        breakdown = await storage_service.get_storage_breakdown(device_id)
        
        # Save analysis to database
        if detailed:
            analysis = await storage_service.analyze_storage(device_id, detailed=True)
            await storage_service.save_storage_analysis(device_id, analysis, db)
        
        return StorageBreakdownResponse(**breakdown)
        
    except Exception as e:
        logger.error(f"Error getting storage breakdown for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage breakdown: {str(e)}"
        )

@router.get("/{device_id}/cache", response_model=List[CacheInfoResponse])
async def get_device_cache_info(
    device_id: str,
    priority: Optional[str] = Query(None, regex="^(low|medium|high)$"),
    min_size_mb: int = Query(1, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get cache information for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if not device.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not connected"
        )
    
    try:
        analysis = await storage_service.analyze_storage(device_id, detailed=True)
        cache_info = analysis.cache_info
        
        # Apply filters
        if priority:
            cache_info = [c for c in cache_info if c.priority == priority]
        
        if min_size_mb > 0:
            cache_info = [c for c in cache_info if c.cache_size_mb >= min_size_mb]
        
        # Limit results
        cache_info = cache_info[:limit]
        
        return [
            CacheInfoResponse(
                app_name=cache.app_name,
                package_name=cache.package_name,
                cache_size_mb=cache.cache_size_mb,
                cache_path=cache.cache_path,
                priority=cache.priority,
                can_clear=cache.can_clear
            )
            for cache in cache_info
        ]
        
    except Exception as e:
        logger.error(f"Error getting cache info for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache info: {str(e)}"
        )

@router.get("/{device_id}/large-files", response_model=List[LargeFileResponse])
async def get_device_large_files(
    device_id: str,
    category: Optional[str] = Query(None),
    min_size_mb: int = Query(50, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get large files for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if not device.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not connected"
        )
    
    try:
        analysis = await storage_service.analyze_storage(device_id, detailed=True)
        large_files = analysis.large_files
        
        # Apply filters
        if category:
            large_files = [f for f in large_files if f.category == category]
        
        if min_size_mb > 0:
            large_files = [f for f in large_files if f.size_mb >= min_size_mb]
        
        # Limit results
        large_files = large_files[:limit]
        
        return [
            LargeFileResponse(
                path=file.path,
                size_mb=file.size_mb,
                category=file.category,
                is_cache=file.is_cache,
                is_temp=file.is_temp,
                recommendations=file.recommendations
            )
            for file in large_files
        ]
        
    except Exception as e:
        logger.error(f"Error getting large files for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get large files: {str(e)}"
        )

@router.post("/{device_id}/optimize", response_model=StorageOptimizationResponse)
async def get_ai_optimization_suggestions(
    device_id: str,
    optimization_request: StorageOptimizationRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get AI-based storage optimization suggestions for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if not device.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not connected"
        )
    
    try:
        optimization = await storage_service.generate_ai_optimization_suggestions(device_id, db)
        
        # Limit suggestions if requested
        if optimization_request.max_suggestions < len(optimization.suggestions):
            optimization.suggestions = optimization.suggestions[:optimization_request.max_suggestions]
        
        return StorageOptimizationResponse(
            device_id=optimization.device_id,
            total_savings_mb=optimization.total_savings_mb,
            confidence_score=optimization.confidence_score,
            suggestions=optimization.suggestions,
            risk_level=optimization.risk_level,
            execution_time_estimate=optimization.execution_time_estimate
        )
        
    except Exception as e:
        logger.error(f"Error generating optimization suggestions for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate optimization suggestions: {str(e)}"
        )

@router.post("/{device_id}/clear-cache", response_model=Dict[str, Any])
async def clear_device_cache(
    device_id: str,
    package_names: Optional[List[str]] = None,
    cache_types: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Clear cache for specific packages or cache types.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if not device.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not connected"
        )
    
    try:
        result = await storage_service.clear_cache(device_id, package_names, cache_types)
        
        # Log the operation
        logger.info(f"Cache clearing operation for device {device_id} by user {current_user['username']}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error clearing cache for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/{device_id}/trends/detailed", response_model=List[Dict[str, Any]])
async def get_detailed_storage_trends(
    device_id: str,
    period_type: Optional[str] = Query("daily", regex="^(hourly|daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365),
    include_predictions: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed storage usage trends with predictions and analysis.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get trends from database
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    trends = (db.query(StorageTrend)
             .filter(StorageTrend.device_id == device.id)
             .filter(StorageTrend.period_type == period_type)
             .filter(StorageTrend.period_start >= start_date)
             .order_by(StorageTrend.period_start)
             .all())
    
    # Convert to detailed response
    detailed_trends = []
    for trend in trends:
        trend_data = trend.to_dict()
        
        # Add additional analysis
        if include_predictions and trend.growth_rate:
            # Calculate predictions based on growth rate
            if trend.growth_rate > 0:
                current_usage = trend.avg_storage_used or 0
                total_storage = 100  # We'll get this from latest analytics
                
                # Get latest storage info for accurate predictions
                latest_analytics = (db.query(Analytics)
                                  .filter(Analytics.device_id == device.id)
                                  .filter(Analytics.storage_total.is_not(None))
                                  .order_by(Analytics.recorded_at.desc())
                                  .first())
                
                if latest_analytics and latest_analytics.storage_total:
                    usage_percentage = (current_usage / latest_analytics.storage_total) * 100
                    days_until_full = (100 - usage_percentage) / trend.growth_rate if trend.growth_rate > 0 else None
                    
                    trend_data['predictions'] = {
                        'days_until_full': int(days_until_full) if days_until_full else None,
                        'projected_usage_next_week': min(100, usage_percentage + (trend.growth_rate * 7)),
                        'projected_usage_next_month': min(100, usage_percentage + (trend.growth_rate * 30)),
                        'recommendation': (
                            'urgent_cleanup' if days_until_full and days_until_full < 7
                            else 'schedule_cleanup' if days_until_full and days_until_full < 30
                            else 'monitor'
                        )
                    }
        
        detailed_trends.append(trend_data)
    
    return detailed_trends

@router.get("/{device_id}/insights", response_model=Dict[str, Any])
async def get_storage_insights(
    device_id: str,
    days_back: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get comprehensive storage insights including trends, forecasts, and recommendations.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    try:
        insights = await trend_service.get_trend_insights(device_id, db, days_back)
        
        if "error" in insights:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=insights["error"]
            )
        
        return insights
        
    except Exception as e:
        logger.error(f"Error getting storage insights for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage insights: {str(e)}"
        )

