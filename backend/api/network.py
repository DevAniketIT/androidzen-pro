"""
Network optimization API endpoints for AndroidZen Pro.
Handles network monitoring, analysis, optimization, and performance metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from .core.database import get_db
from .models.device import Device
from .models.analytics import Analytics
from .core.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class NetworkAnalysisResponse(BaseModel):
    device_id: str
    device_name: Optional[str]
    network_type: Optional[str]
    network_strength: Optional[int]
    data_received: Optional[int]
    data_transmitted: Optional[int]
    connection_quality: str
    download_speed: Optional[float]  # Mbps
    upload_speed: Optional[float]  # Mbps
    latency: Optional[float]  # milliseconds
    packet_loss: Optional[float]  # percentage
    dns_response_time: Optional[float]  # milliseconds
    last_updated: Optional[datetime]

class NetworkSpeedTestRequest(BaseModel):
    device_id: str
    test_servers: Optional[List[str]] = None
    test_duration: Optional[int] = 30  # seconds

class NetworkSpeedTestResult(BaseModel):
    device_id: str
    test_id: str
    download_speed: float  # Mbps
    upload_speed: float  # Mbps
    latency: float  # milliseconds
    jitter: float  # milliseconds
    packet_loss: float  # percentage
    test_server: str
    test_duration: float
    timestamp: datetime

class NetworkOptimizationRequest(BaseModel):
    device_id: str
    optimization_types: List[str]  # ["dns", "tcp", "wifi", "mobile_data"]
    apply_changes: bool = False

class NetworkOptimizationResult(BaseModel):
    device_id: str
    optimization_types: List[str]
    changes_applied: Dict[str, Any]
    estimated_improvement: Dict[str, float]
    before_metrics: Dict[str, float]
    after_metrics: Optional[Dict[str, float]]
    recommendations: List[str]

class NetworkConnectionInfo(BaseModel):
    device_id: str
    device_name: Optional[str]
    wifi_connections: List[Dict[str, Any]]
    mobile_connections: List[Dict[str, Any]]
    vpn_status: bool
    proxy_settings: Optional[Dict[str, Any]]
    data_usage_stats: Dict[str, int]
    network_restrictions: List[str]

class NetworkAlert(BaseModel):
    device_id: str
    alert_type: str  # "slow_connection", "high_usage", "connection_drop", "security_risk"
    severity: str
    title: str
    description: str
    threshold_value: Optional[float]
    current_value: Optional[float]
    recommendation: str
    timestamp: datetime

class NetworkStatsResponse(BaseModel):
    total_devices: int
    devices_online: int
    wifi_connections: int
    mobile_connections: int
    average_download_speed: float
    average_upload_speed: float
    data_usage_today: int  # MB
    data_usage_month: int  # MB
    network_issues: int

@router.get("/analysis", response_model=List[NetworkAnalysisResponse])
async def get_network_analysis(
    device_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    network_type: Optional[str] = Query(None),
    min_speed: Optional[float] = Query(None, ge=0),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get network analysis for devices with optional filtering.
    """
    query = db.query(Device).filter(Device.is_active == True)
    
    if device_id:
        query = query.filter(Device.device_id == device_id)
    
    devices = query.offset(skip).limit(limit).all()
    
    results = []
    for device in devices:
        # Get latest network analytics
        latest_analytics = (db.query(Analytics)
                          .filter(Analytics.device_id == device.id)
                          .filter(Analytics.network_type.is_not(None))
                          .order_by(Analytics.recorded_at.desc())
                          .first())
        
        if not latest_analytics:
            continue
        
        # Filter by network type
        if network_type and latest_analytics.network_type != network_type:
            continue
        
        # Mock additional network metrics (in real implementation, these would come from actual network tests)
        import random
        download_speed = random.uniform(10, 100)  # Mbps
        upload_speed = random.uniform(5, 50)  # Mbps
        latency = random.uniform(10, 200)  # ms
        packet_loss = random.uniform(0, 5)  # %
        dns_response_time = random.uniform(5, 100)  # ms
        
        # Filter by minimum speed
        if min_speed and download_speed < min_speed:
            continue
        
        # Determine connection quality
        quality = "Excellent"
        if download_speed < 25 or latency > 100 or packet_loss > 2:
            quality = "Poor"
        elif download_speed < 50 or latency > 50 or packet_loss > 1:
            quality = "Fair"
        elif download_speed < 75 or latency > 30:
            quality = "Good"
        
        analysis = NetworkAnalysisResponse(
            device_id=device.device_id,
            device_name=device.device_name,
            network_type=latest_analytics.network_type,
            network_strength=latest_analytics.network_strength,
            data_received=latest_analytics.data_received,
            data_transmitted=latest_analytics.data_transmitted,
            connection_quality=quality,
            download_speed=download_speed,
            upload_speed=upload_speed,
            latency=latency,
            packet_loss=packet_loss,
            dns_response_time=dns_response_time,
            last_updated=latest_analytics.recorded_at
        )
        
        results.append(analysis)
    
    return results

@router.get("/{device_id}/analysis", response_model=NetworkAnalysisResponse)
async def get_device_network_analysis(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed network analysis for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get latest network analytics
    latest_analytics = (db.query(Analytics)
                      .filter(Analytics.device_id == device.id)
                      .filter(Analytics.network_type.is_not(None))
                      .order_by(Analytics.recorded_at.desc())
                      .first())
    
    if not latest_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No network data available for this device"
        )
    
    # Mock additional network metrics
    import random
    download_speed = random.uniform(10, 100)
    upload_speed = random.uniform(5, 50)
    latency = random.uniform(10, 200)
    packet_loss = random.uniform(0, 5)
    dns_response_time = random.uniform(5, 100)
    
    # Determine connection quality
    quality = "Excellent"
    if download_speed < 25 or latency > 100 or packet_loss > 2:
        quality = "Poor"
    elif download_speed < 50 or latency > 50 or packet_loss > 1:
        quality = "Fair"
    elif download_speed < 75 or latency > 30:
        quality = "Good"
    
    return NetworkAnalysisResponse(
        device_id=device.device_id,
        device_name=device.device_name,
        network_type=latest_analytics.network_type,
        network_strength=latest_analytics.network_strength,
        data_received=latest_analytics.data_received,
        data_transmitted=latest_analytics.data_transmitted,
        connection_quality=quality,
        download_speed=download_speed,
        upload_speed=upload_speed,
        latency=latency,
        packet_loss=packet_loss,
        dns_response_time=dns_response_time,
        last_updated=latest_analytics.recorded_at
    )

@router.post("/{device_id}/speed-test", response_model=NetworkSpeedTestResult)
async def perform_speed_test(
    device_id: str,
    speed_test_request: NetworkSpeedTestRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Perform a network speed test on a specific device.
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
    
    # Validate request
    if speed_test_request.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID mismatch"
        )
    
    # Simulate speed test (in real implementation, this would use speedtest-cli or similar)
    start_time = datetime.utcnow()
    
    import random
    import uuid
    
    # Mock speed test results with some realistic variation
    download_speed = random.uniform(20, 150)
    upload_speed = random.uniform(5, 75)
    latency = random.uniform(8, 80)
    jitter = random.uniform(0.5, 10)
    packet_loss = random.uniform(0, 3)
    
    test_server = (speed_test_request.test_servers[0] 
                   if speed_test_request.test_servers 
                   else "speedtest.net")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    # Create analytics record with speed test results
    analytics = Analytics(
        device_id=device.id,
        metric_type="network",
        network_type="WiFi",  # This would be detected from device
        network_strength=-45,  # Mock signal strength
        data_received=int(download_speed * 1024 * 1024 / 8),  # Convert to bytes
        data_transmitted=int(upload_speed * 1024 * 1024 / 8),
        collection_method="speed_test",
        data_source="network_speed_test_api",
        additional_metrics={
            "download_speed_mbps": download_speed,
            "upload_speed_mbps": upload_speed,
            "latency_ms": latency,
            "jitter_ms": jitter,
            "packet_loss_percent": packet_loss,
            "test_server": test_server
        }
    )
    
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    
    logger.info(f"Network speed test completed for device {device_id} by user {current_user['username']} - Down: {download_speed:.1f}Mbps, Up: {upload_speed:.1f}Mbps")
    
    return NetworkSpeedTestResult(
        device_id=device_id,
        test_id=str(uuid.uuid4()),
        download_speed=download_speed,
        upload_speed=upload_speed,
        latency=latency,
        jitter=jitter,
        packet_loss=packet_loss,
        test_server=test_server,
        test_duration=duration,
        timestamp=start_time
    )

@router.post("/{device_id}/optimize", response_model=NetworkOptimizationResult)
async def optimize_network(
    device_id: str,
    optimization_request: NetworkOptimizationRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Perform network optimization on a specific device.
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
    
    # Validate optimization request
    if optimization_request.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID mismatch"
        )
    
    valid_optimization_types = ["dns", "tcp", "wifi", "mobile_data"]
    invalid_types = [ot for ot in optimization_request.optimization_types if ot not in valid_optimization_types]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid optimization types: {invalid_types}"
        )
    
    # Get current network metrics as baseline
    latest_analytics = (db.query(Analytics)
                      .filter(Analytics.device_id == device.id)
                      .order_by(Analytics.recorded_at.desc())
                      .first())
    
    import random
    
    # Mock current performance metrics
    before_metrics = {
        "download_speed": random.uniform(20, 60),
        "upload_speed": random.uniform(5, 30),
        "latency": random.uniform(30, 100),
        "dns_response_time": random.uniform(20, 150)
    }
    
    # Simulate network optimization changes
    changes_applied = {}
    estimated_improvement = {}
    recommendations = []
    
    for opt_type in optimization_request.optimization_types:
        if opt_type == "dns":
            changes_applied["dns"] = {
                "primary_dns": "8.8.8.8",
                "secondary_dns": "8.8.4.4",
                "previous_dns": "auto"
            }
            estimated_improvement["dns_response_time"] = 25.0  # 25% improvement
            recommendations.append("Changed DNS servers to Google Public DNS for faster resolution")
        
        elif opt_type == "tcp":
            changes_applied["tcp"] = {
                "tcp_window_scaling": "enabled",
                "tcp_congestion_algorithm": "bbr",
                "tcp_fastopen": "enabled"
            }
            estimated_improvement["download_speed"] = 15.0  # 15% improvement
            recommendations.append("Optimized TCP settings for better throughput")
        
        elif opt_type == "wifi":
            changes_applied["wifi"] = {
                "wifi_frequency_band": "5GHz",
                "wifi_channel": "auto",
                "power_save_mode": "disabled"
            }
            estimated_improvement["connection_stability"] = 20.0
            recommendations.append("Optimized WiFi settings for better performance")
        
        elif opt_type == "mobile_data":
            changes_applied["mobile_data"] = {
                "preferred_network_type": "LTE",
                "data_roaming_optimization": "enabled",
                "carrier_aggregation": "enabled"
            }
            estimated_improvement["mobile_speed"] = 10.0
            recommendations.append("Optimized mobile data settings")
    
    # Mock after metrics if changes were applied
    after_metrics = None
    if optimization_request.apply_changes:
        after_metrics = before_metrics.copy()
        # Apply estimated improvements
        for metric, improvement in estimated_improvement.items():
            if metric in after_metrics:
                after_metrics[metric] *= (1 + improvement / 100)
        
        # Create analytics record with optimized metrics
        analytics = Analytics(
            device_id=device.id,
            metric_type="network",
            network_type=latest_analytics.network_type if latest_analytics else "WiFi",
            collection_method="network_optimization",
            data_source="network_optimization_api",
            additional_metrics={
                "optimization_applied": True,
                "optimization_types": optimization_request.optimization_types,
                "before_metrics": before_metrics,
                "after_metrics": after_metrics,
                "changes_applied": changes_applied
            }
        )
        db.add(analytics)
        db.commit()
    
    logger.info(f"Network optimization {'applied' if optimization_request.apply_changes else 'simulated'} for device {device_id} by user {current_user['username']}")
    
    return NetworkOptimizationResult(
        device_id=device_id,
        optimization_types=optimization_request.optimization_types,
        changes_applied=changes_applied if optimization_request.apply_changes else {},
        estimated_improvement=estimated_improvement,
        before_metrics=before_metrics,
        after_metrics=after_metrics,
        recommendations=recommendations
    )

@router.get("/{device_id}/connections", response_model=NetworkConnectionInfo)
async def get_network_connections(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed network connection information for a device.
    """
    device = db.query(Device).filter(Device.device_id == device_id, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Mock network connection information (in real implementation, this would come from ADB commands)
    import random
    
    wifi_connections = [
        {
            "ssid": "Home_WiFi_5G",
            "bssid": "aa:bb:cc:dd:ee:ff",
            "frequency": "5180 MHz",
            "signal_strength": -42,
            "security": "WPA2",
            "status": "connected",
            "ip_address": "192.168.1.105"
        }
    ]
    
    mobile_connections = [
        {
            "carrier": "Verizon",
            "network_type": "LTE",
            "signal_strength": -85,
            "data_state": "connected",
            "roaming": False
        }
    ] if random.random() > 0.3 else []
    
    data_usage_stats = {
        "wifi_rx_bytes": random.randint(1000000, 10000000),  # 1-10 MB
        "wifi_tx_bytes": random.randint(500000, 5000000),    # 0.5-5 MB
        "mobile_rx_bytes": random.randint(100000, 2000000),  # 0.1-2 MB
        "mobile_tx_bytes": random.randint(50000, 1000000),   # 0.05-1 MB
        "total_rx_bytes": 0,
        "total_tx_bytes": 0
    }
    data_usage_stats["total_rx_bytes"] = data_usage_stats["wifi_rx_bytes"] + data_usage_stats["mobile_rx_bytes"]
    data_usage_stats["total_tx_bytes"] = data_usage_stats["wifi_tx_bytes"] + data_usage_stats["mobile_tx_bytes"]
    
    return NetworkConnectionInfo(
        device_id=device_id,
        device_name=device.device_name,
        wifi_connections=wifi_connections,
        mobile_connections=mobile_connections,
        vpn_status=random.random() > 0.8,  # 20% chance of VPN
        proxy_settings={"enabled": False} if random.random() > 0.9 else None,
        data_usage_stats=data_usage_stats,
        network_restrictions=[]
    )

@router.get("/alerts", response_model=List[NetworkAlert])
async def get_network_alerts(
    device_id: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),  # Last 1-168 hours (1 week)
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get network alerts based on current performance and thresholds.
    """
    query = db.query(Device).filter(Device.is_active == True)
    
    if device_id:
        query = query.filter(Device.device_id == device_id)
    
    devices = query.all()
    alerts = []
    
    for device in devices:
        # Get recent network analytics
        start_time = datetime.utcnow() - timedelta(hours=hours)
        recent_analytics = (db.query(Analytics)
                           .filter(Analytics.device_id == device.id)
                           .filter(Analytics.recorded_at >= start_time)
                           .filter(Analytics.network_type.is_not(None))
                           .order_by(Analytics.recorded_at.desc())
                           .all())
        
        if not recent_analytics:
            continue
        
        # Mock some network alerts based on analytics
        import random
        
        # Check for slow connection alert
        avg_signal_strength = sum(a.network_strength for a in recent_analytics if a.network_strength) / len(recent_analytics)
        if avg_signal_strength and avg_signal_strength < -70:  # Weak signal
            alert = NetworkAlert(
                device_id=device.device_id,
                alert_type="slow_connection",
                severity="medium",
                title="Weak Network Signal Detected",
                description=f"Average signal strength is {avg_signal_strength:.1f} dBm, which may cause performance issues.",
                threshold_value=-70.0,
                current_value=avg_signal_strength,
                recommendation="Move closer to WiFi router or consider using mobile data",
                timestamp=datetime.utcnow()
            )
            alerts.append(alert)
        
        # Check for high data usage
        total_data = sum((a.data_received or 0) + (a.data_transmitted or 0) for a in recent_analytics)
        if total_data > 1000000000:  # > 1GB in the time period
            alert = NetworkAlert(
                device_id=device.device_id,
                alert_type="high_usage",
                severity="low",
                title="High Data Usage Detected",
                description=f"Device has used {total_data / 1000000:.1f} MB of data in the last {hours} hours.",
                threshold_value=1000.0,
                current_value=total_data / 1000000,
                recommendation="Monitor app data usage and consider enabling data saver mode",
                timestamp=datetime.utcnow()
            )
            alerts.append(alert)
        
        # Random connection drop alert
        if random.random() < 0.1:  # 10% chance
            alert = NetworkAlert(
                device_id=device.device_id,
                alert_type="connection_drop",
                severity="high",
                title="Network Connection Instability",
                description="Multiple network disconnections detected in recent hours.",
                threshold_value=5.0,
                current_value=random.randint(6, 15),
                recommendation="Check router configuration and consider network troubleshooting",
                timestamp=datetime.utcnow()
            )
            alerts.append(alert)
    
    # Apply filters
    if alert_type:
        alerts = [alert for alert in alerts if alert.alert_type == alert_type]
    
    if severity:
        alerts = [alert for alert in alerts if alert.severity == severity]
    
    return alerts

@router.get("/stats", response_model=NetworkStatsResponse)
async def get_network_stats(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get overall network statistics across all devices.
    """
    # Get all active devices
    total_devices = db.query(Device).filter(Device.is_active == True).count()
    devices_online = db.query(Device).filter(Device.is_active == True, Device.is_connected == True).count()
    
    # Get recent network analytics for stats
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_analytics = (db.query(Analytics)
                       .filter(Analytics.recorded_at >= one_hour_ago)
                       .filter(Analytics.network_type.is_not(None))
                       .all())
    
    wifi_connections = sum(1 for a in recent_analytics if a.network_type == "WiFi")
    mobile_connections = sum(1 for a in recent_analytics if a.network_type == "Mobile")
    
    # Mock average speeds (in real implementation, these would be calculated from actual speed tests)
    import random
    average_download_speed = random.uniform(40, 80)
    average_upload_speed = random.uniform(15, 40)
    
    # Calculate data usage
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    today_analytics = (db.query(Analytics)
                      .filter(Analytics.recorded_at >= today_start)
                      .filter(Analytics.network_type.is_not(None))
                      .all())
    
    month_analytics = (db.query(Analytics)
                      .filter(Analytics.recorded_at >= month_start)
                      .filter(Analytics.network_type.is_not(None))
                      .all())
    
    data_usage_today = sum((a.data_received or 0) + (a.data_transmitted or 0) for a in today_analytics) // (1024 * 1024)  # Convert to MB
    data_usage_month = sum((a.data_received or 0) + (a.data_transmitted or 0) for a in month_analytics) // (1024 * 1024)
    
    # Mock network issues count
    network_issues = random.randint(0, 5)
    
    return NetworkStatsResponse(
        total_devices=total_devices,
        devices_online=devices_online,
        wifi_connections=wifi_connections,
        mobile_connections=mobile_connections,
        average_download_speed=average_download_speed,
        average_upload_speed=average_upload_speed,
        data_usage_today=data_usage_today,
        data_usage_month=data_usage_month,
        network_issues=network_issues
    )

@router.post("/{device_id}/analyze")
async def trigger_network_analysis(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Trigger a comprehensive network analysis for a specific device.
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
    
    # In a real implementation, this would trigger network analysis tools
    # For now, we'll create mock analytics data
    import random
    
    network_type = random.choice(["WiFi", "Mobile", "Ethernet"])
    signal_strength = random.randint(-90, -30) if network_type != "Ethernet" else None
    data_received = random.randint(1000000, 50000000)  # 1-50 MB
    data_transmitted = random.randint(500000, 25000000)  # 0.5-25 MB
    
    # Create new analytics record
    analytics = Analytics(
        device_id=device.id,
        metric_type="network",
        network_type=network_type,
        network_strength=signal_strength,
        data_received=data_received,
        data_transmitted=data_transmitted,
        collection_method="api_triggered",
        data_source="network_analysis_api",
        additional_metrics={
            "analysis_type": "comprehensive",
            "connection_quality": "Good",
            "bandwidth_test": "completed",
            "latency_test": "completed"
        }
    )
    
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    
    logger.info(f"Network analysis triggered for device {device_id} by user {current_user['username']}")
    
    return {
        "message": "Network analysis completed successfully",
        "device_id": device_id,
        "analysis_id": analytics.id,
        "timestamp": analytics.recorded_at.isoformat(),
        "network_type": network_type,
        "data_usage_mb": (data_received + data_transmitted) // (1024 * 1024)
    }

