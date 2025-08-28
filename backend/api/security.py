"""
Security monitoring API endpoints for AndroidZen Pro.
Handles security events, threat detection, alerts, and security analysis.
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
from .models.security import SecurityEvent, SecurityAlert, ThreatIntelligence, SeverityLevel, EventStatus
from .core.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class SecurityEventCreate(BaseModel):
    device_id: str
    event_type: str
    event_category: Optional[str] = None
    event_title: str
    event_description: Optional[str] = None
    severity: str  # "low", "medium", "high", "critical"
    detection_method: Optional[str] = None
    app_package_name: Optional[str] = None
    app_name: Optional[str] = None
    network_address: Optional[str] = None
    file_path: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None

class SecurityEventResponse(BaseModel):
    id: int
    device_id: int
    event_type: str
    event_category: Optional[str]
    event_title: str
    event_description: Optional[str]
    severity: str
    status: str
    risk_score: Optional[float]
    confidence_level: Optional[float]
    detection_method: Optional[str]
    app_package_name: Optional[str]
    app_name: Optional[str]
    network_address: Optional[str]
    file_path: Optional[str]
    auto_response_taken: bool
    is_mitigated: bool
    event_count: int
    is_recurring: bool
    detected_at: datetime
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class SecurityEventUpdate(BaseModel):
    status: Optional[str] = None
    investigation_notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolution_action: Optional[str] = None

class SecurityAlertResponse(BaseModel):
    id: int
    security_event_id: int
    alert_type: str
    alert_title: str
    alert_message: str
    alert_priority: str
    recipient_type: Optional[str]
    status: str
    delivery_attempts: int
    response_required: bool
    response_received: bool
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    created_at: datetime

class ThreatIntelligenceResponse(BaseModel):
    id: int
    threat_type: str
    threat_name: Optional[str]
    threat_family: Optional[str]
    ioc_type: str
    ioc_value: str
    ioc_description: Optional[str]
    severity: str
    confidence_score: Optional[float]
    reputation_score: Optional[float]
    intelligence_source: Optional[str]
    detection_count: int
    is_active: bool
    valid_from: datetime
    valid_until: Optional[datetime]
    created_at: datetime

class SecurityStatsResponse(BaseModel):
    total_events: int
    events_by_severity: Dict[str, int]
    events_by_type: Dict[str, int]
    open_events: int
    resolved_events: int
    high_risk_devices: int
    recent_threats: int
    mitigation_rate: float

class SecurityScanRequest(BaseModel):
    device_id: str
    scan_types: List[str]  # ["malware", "permissions", "network", "system"]
    deep_scan: bool = False

class SecurityScanResult(BaseModel):
    device_id: str
    scan_types: List[str]
    threats_found: int
    warnings_found: int
    scan_duration: float
    scan_results: Dict[str, Any]
    recommendations: List[str]

@router.get("/events", response_model=List[SecurityEventResponse])
async def list_security_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get list of security events with optional filtering.
    """
    query = db.query(SecurityEvent).join(Device).filter(Device.is_active == True)
    
    # Filter by device if specified
    if device_id:
        query = query.filter(Device.device_id == device_id)
    
    # Filter by event type
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    
    # Filter by severity
    if severity:
        try:
            severity_enum = SeverityLevel(severity.lower())
            query = query.filter(SecurityEvent.severity == severity_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity level: {severity}"
            )
    
    # Filter by status
    if status:
        try:
            status_enum = EventStatus(status.lower())
            query = query.filter(SecurityEvent.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    # Filter by date range
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(SecurityEvent.detected_at >= start_date)
    
    # Order by most recent first
    events = query.order_by(SecurityEvent.detected_at.desc()).offset(skip).limit(limit).all()
    
    return [SecurityEventResponse(
        id=event.id,
        device_id=event.device_id,
        event_type=event.event_type,
        event_category=event.event_category,
        event_title=event.event_title,
        event_description=event.event_description,
        severity=event.severity.value if event.severity else None,
        status=event.status.value if event.status else None,
        risk_score=event.risk_score,
        confidence_level=event.confidence_level,
        detection_method=event.detection_method,
        app_package_name=event.app_package_name,
        app_name=event.app_name,
        network_address=event.network_address,
        file_path=event.file_path,
        auto_response_taken=event.auto_response_taken,
        is_mitigated=event.is_mitigated,
        event_count=event.event_count,
        is_recurring=event.is_recurring,
        detected_at=event.detected_at,
        resolved_at=event.resolved_at,
        created_at=event.created_at,
        updated_at=event.updated_at
    ) for event in events]

@router.post("/events", response_model=SecurityEventResponse)
async def create_security_event(
    event_data: SecurityEventCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Create a new security event.
    """
    # Validate device
    device = db.query(Device).filter(
        Device.device_id == event_data.device_id,
        Device.is_active == True
    ).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Validate severity level
    try:
        severity_enum = SeverityLevel(event_data.severity.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity level: {event_data.severity}"
        )
    
    # Check for duplicate events (similar events within last hour)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    existing_event = (db.query(SecurityEvent)
                     .filter(SecurityEvent.device_id == device.id)
                     .filter(SecurityEvent.event_type == event_data.event_type)
                     .filter(SecurityEvent.detected_at >= one_hour_ago)
                     .filter(SecurityEvent.status != EventStatus.RESOLVED)
                     .first())
    
    if existing_event:
        # Update existing event instead of creating new one
        existing_event.increment_occurrence()
        existing_event.calculate_risk_score()
        db.commit()
        db.refresh(existing_event)
        
        logger.info(f"Updated recurring security event: {existing_event.event_type} for device {device.device_id}")
        
        return SecurityEventResponse(
            id=existing_event.id,
            device_id=existing_event.device_id,
            event_type=existing_event.event_type,
            event_category=existing_event.event_category,
            event_title=existing_event.event_title,
            event_description=existing_event.event_description,
            severity=existing_event.severity.value,
            status=existing_event.status.value,
            risk_score=existing_event.risk_score,
            confidence_level=existing_event.confidence_level,
            detection_method=existing_event.detection_method,
            app_package_name=existing_event.app_package_name,
            app_name=existing_event.app_name,
            network_address=existing_event.network_address,
            file_path=existing_event.file_path,
            auto_response_taken=existing_event.auto_response_taken,
            is_mitigated=existing_event.is_mitigated,
            event_count=existing_event.event_count,
            is_recurring=existing_event.is_recurring,
            detected_at=existing_event.detected_at,
            resolved_at=existing_event.resolved_at,
            created_at=existing_event.created_at,
            updated_at=existing_event.updated_at
        )
    
    # Create new security event
    security_event = SecurityEvent(
        device_id=device.id,
        event_type=event_data.event_type,
        event_category=event_data.event_category,
        event_title=event_data.event_title,
        event_description=event_data.event_description,
        severity=severity_enum,
        detection_method=event_data.detection_method,
        app_package_name=event_data.app_package_name,
        app_name=event_data.app_name,
        network_address=event_data.network_address,
        file_path=event_data.file_path,
        context_data=event_data.context_data
    )
    
    # Calculate risk score
    security_event.calculate_risk_score()
    
    db.add(security_event)
    db.commit()
    db.refresh(security_event)
    
    logger.info(f"Security event created: {security_event.event_type} for device {device.device_id} by user {current_user['username']}")
    
    return SecurityEventResponse(
        id=security_event.id,
        device_id=security_event.device_id,
        event_type=security_event.event_type,
        event_category=security_event.event_category,
        event_title=security_event.event_title,
        event_description=security_event.event_description,
        severity=security_event.severity.value,
        status=security_event.status.value,
        risk_score=security_event.risk_score,
        confidence_level=security_event.confidence_level,
        detection_method=security_event.detection_method,
        app_package_name=security_event.app_package_name,
        app_name=security_event.app_name,
        network_address=security_event.network_address,
        file_path=security_event.file_path,
        auto_response_taken=security_event.auto_response_taken,
        is_mitigated=security_event.is_mitigated,
        event_count=security_event.event_count,
        is_recurring=security_event.is_recurring,
        detected_at=security_event.detected_at,
        resolved_at=security_event.resolved_at,
        created_at=security_event.created_at,
        updated_at=security_event.updated_at
    )

@router.get("/events/{event_id}", response_model=SecurityEventResponse)
async def get_security_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed information about a specific security event.
    """
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    
    return SecurityEventResponse(
        id=event.id,
        device_id=event.device_id,
        event_type=event.event_type,
        event_category=event.event_category,
        event_title=event.event_title,
        event_description=event.event_description,
        severity=event.severity.value if event.severity else None,
        status=event.status.value if event.status else None,
        risk_score=event.risk_score,
        confidence_level=event.confidence_level,
        detection_method=event.detection_method,
        app_package_name=event.app_package_name,
        app_name=event.app_name,
        network_address=event.network_address,
        file_path=event.file_path,
        auto_response_taken=event.auto_response_taken,
        is_mitigated=event.is_mitigated,
        event_count=event.event_count,
        is_recurring=event.is_recurring,
        detected_at=event.detected_at,
        resolved_at=event.resolved_at,
        created_at=event.created_at,
        updated_at=event.updated_at
    )

@router.put("/events/{event_id}", response_model=SecurityEventResponse)
async def update_security_event(
    event_id: int,
    event_data: SecurityEventUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update a security event (typically for status changes, investigation notes, etc.).
    """
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    
    # Update fields
    update_data = event_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            try:
                status_enum = EventStatus(value.lower())
                event.status = status_enum
                if status_enum == EventStatus.RESOLVED:
                    event.mark_as_resolved(
                        current_user["username"],
                        event_data.resolution_notes,
                        event_data.resolution_action
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {value}"
                )
        elif hasattr(event, field):
            setattr(event, field, value)
    
    event.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(event)
    
    logger.info(f"Security event updated: {event.id} by user {current_user['username']}")
    
    return SecurityEventResponse(
        id=event.id,
        device_id=event.device_id,
        event_type=event.event_type,
        event_category=event.event_category,
        event_title=event.event_title,
        event_description=event.event_description,
        severity=event.severity.value if event.severity else None,
        status=event.status.value if event.status else None,
        risk_score=event.risk_score,
        confidence_level=event.confidence_level,
        detection_method=event.detection_method,
        app_package_name=event.app_package_name,
        app_name=event.app_name,
        network_address=event.network_address,
        file_path=event.file_path,
        auto_response_taken=event.auto_response_taken,
        is_mitigated=event.is_mitigated,
        event_count=event.event_count,
        is_recurring=event.is_recurring,
        detected_at=event.detected_at,
        resolved_at=event.resolved_at,
        created_at=event.created_at,
        updated_at=event.updated_at
    )

@router.get("/alerts", response_model=List[SecurityAlertResponse])
async def list_security_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    alert_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get list of security alerts with optional filtering.
    """
    query = db.query(SecurityAlert)
    
    if alert_type:
        query = query.filter(SecurityAlert.alert_type == alert_type)
    
    if status:
        query = query.filter(SecurityAlert.status == status)
    
    # Filter by date range
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(SecurityAlert.created_at >= start_date)
    
    alerts = query.order_by(SecurityAlert.created_at.desc()).offset(skip).limit(limit).all()
    
    return [SecurityAlertResponse(
        id=alert.id,
        security_event_id=alert.security_event_id,
        alert_type=alert.alert_type,
        alert_title=alert.alert_title,
        alert_message=alert.alert_message,
        alert_priority=alert.alert_priority,
        recipient_type=alert.recipient_type,
        status=alert.status,
        delivery_attempts=alert.delivery_attempts,
        response_required=alert.response_required,
        response_received=alert.response_received,
        sent_at=alert.sent_at,
        delivered_at=alert.delivered_at,
        acknowledged_at=alert.acknowledged_at,
        created_at=alert.created_at
    ) for alert in alerts]

@router.post("/{device_id}/scan", response_model=SecurityScanResult)
async def perform_security_scan(
    device_id: str,
    scan_request: SecurityScanRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Perform a security scan on a specific device.
    """
    # Validate device
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.is_active == True
    ).first()
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
    
    # Validate scan request
    if scan_request.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID mismatch"
        )
    
    valid_scan_types = ["malware", "permissions", "network", "system"]
    invalid_types = [st for st in scan_request.scan_types if st not in valid_scan_types]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scan types: {invalid_types}"
        )
    
    # Simulate security scan (in real implementation, this would use various security tools)
    start_time = datetime.utcnow()
    
    threats_found = 0
    warnings_found = 0
    scan_results = {}
    recommendations = []
    
    # Mock scan results based on scan types
    import random
    
    for scan_type in scan_request.scan_types:
        if scan_type == "malware":
            malware_threats = random.randint(0, 2)
            threats_found += malware_threats
            scan_results["malware"] = {
                "threats_detected": malware_threats,
                "suspicious_apps": random.randint(0, 3),
                "scan_coverage": "95%"
            }
            if malware_threats > 0:
                recommendations.append("Remove or quarantine detected malware applications")
        
        elif scan_type == "permissions":
            excessive_perms = random.randint(0, 5)
            warnings_found += excessive_perms
            scan_results["permissions"] = {
                "apps_with_excessive_permissions": excessive_perms,
                "high_risk_permissions": random.randint(0, 2),
                "apps_scanned": random.randint(50, 150)
            }
            if excessive_perms > 0:
                recommendations.append("Review and revoke unnecessary app permissions")
        
        elif scan_type == "network":
            network_threats = random.randint(0, 1)
            threats_found += network_threats
            scan_results["network"] = {
                "suspicious_connections": network_threats,
                "open_ports": random.randint(0, 3),
                "wifi_security": "WPA2" if random.random() > 0.2 else "WEP"
            }
            if network_threats > 0:
                recommendations.append("Block suspicious network connections")
        
        elif scan_type == "system":
            system_issues = random.randint(0, 3)
            warnings_found += system_issues
            scan_results["system"] = {
                "security_patch_level": "2023-10-01",
                "developer_options_enabled": random.random() > 0.7,
                "unknown_sources_enabled": random.random() > 0.8,
                "system_integrity": "Good" if system_issues < 2 else "Warning"
            }
            if system_issues > 0:
                recommendations.append("Update system security patches and disable developer options if not needed")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    # If threats were found, create security events
    if threats_found > 0:
        for scan_type in scan_request.scan_types:
            if scan_results.get(scan_type, {}).get("threats_detected", 0) > 0:
                security_event = SecurityEvent(
                    device_id=device.id,
                    event_type="security_scan_threat",
                    event_category="automated_scan",
                    event_title=f"Security threat detected during {scan_type} scan",
                    event_description=f"Automated security scan found {scan_results[scan_type]['threats_detected']} threats",
                    severity=SeverityLevel.HIGH if threats_found > 1 else SeverityLevel.MEDIUM,
                    detection_method="security_scan_api",
                    context_data={"scan_type": scan_type, "scan_results": scan_results[scan_type]}
                )
                security_event.calculate_risk_score()
                db.add(security_event)
    
    db.commit()
    
    logger.info(f"Security scan completed for device {device_id} by user {current_user['username']} - Threats: {threats_found}, Warnings: {warnings_found}")
    
    return SecurityScanResult(
        device_id=device_id,
        scan_types=scan_request.scan_types,
        threats_found=threats_found,
        warnings_found=warnings_found,
        scan_duration=duration,
        scan_results=scan_results,
        recommendations=recommendations
    )

@router.get("/stats", response_model=SecurityStatsResponse)
async def get_security_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get security statistics and metrics.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total events
    total_events = db.query(SecurityEvent).filter(SecurityEvent.detected_at >= start_date).count()
    
    # Events by severity
    events_by_severity = {}
    for severity in SeverityLevel:
        count = (db.query(SecurityEvent)
                .filter(SecurityEvent.detected_at >= start_date)
                .filter(SecurityEvent.severity == severity)
                .count())
        events_by_severity[severity.value] = count
    
    # Events by type
    event_types = (db.query(SecurityEvent.event_type, func.count(SecurityEvent.id))
                   .filter(SecurityEvent.detected_at >= start_date)
                   .group_by(SecurityEvent.event_type)
                   .all())
    events_by_type = {event_type: count for event_type, count in event_types}
    
    # Open vs resolved events
    open_events = (db.query(SecurityEvent)
                   .filter(SecurityEvent.detected_at >= start_date)
                   .filter(SecurityEvent.status != EventStatus.RESOLVED)
                   .count())
    resolved_events = (db.query(SecurityEvent)
                       .filter(SecurityEvent.detected_at >= start_date)
                       .filter(SecurityEvent.status == EventStatus.RESOLVED)
                       .count())
    
    # High risk devices (devices with high or critical severity events)
    high_risk_devices = (db.query(func.count(func.distinct(SecurityEvent.device_id)))
                         .filter(SecurityEvent.detected_at >= start_date)
                         .filter(or_(
                             SecurityEvent.severity == SeverityLevel.HIGH,
                             SecurityEvent.severity == SeverityLevel.CRITICAL
                         ))
                         .scalar() or 0)
    
    # Recent threats (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_threats = (db.query(SecurityEvent)
                      .filter(SecurityEvent.detected_at >= seven_days_ago)
                      .count())
    
    # Mitigation rate
    mitigation_rate = 0.0
    if total_events > 0:
        mitigation_rate = (resolved_events / total_events) * 100
    
    return SecurityStatsResponse(
        total_events=total_events,
        events_by_severity=events_by_severity,
        events_by_type=events_by_type,
        open_events=open_events,
        resolved_events=resolved_events,
        high_risk_devices=high_risk_devices,
        recent_threats=recent_threats,
        mitigation_rate=mitigation_rate
    )

@router.get("/threats", response_model=List[ThreatIntelligenceResponse])
async def list_threat_intelligence(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    threat_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get threat intelligence data and IOCs.
    """
    query = db.query(ThreatIntelligence)
    
    if threat_type:
        query = query.filter(ThreatIntelligence.threat_type == threat_type)
    
    if active_only:
        query = query.filter(ThreatIntelligence.is_active == True)
        query = query.filter(or_(
            ThreatIntelligence.valid_until.is_(None),
            ThreatIntelligence.valid_until > datetime.utcnow()
        ))
    
    threats = query.order_by(ThreatIntelligence.created_at.desc()).offset(skip).limit(limit).all()
    
    return [ThreatIntelligenceResponse(
        id=threat.id,
        threat_type=threat.threat_type,
        threat_name=threat.threat_name,
        threat_family=threat.threat_family,
        ioc_type=threat.ioc_type,
        ioc_value=threat.ioc_value,
        ioc_description=threat.ioc_description,
        severity=threat.severity.value if threat.severity else None,
        confidence_score=threat.confidence_score,
        reputation_score=threat.reputation_score,
        intelligence_source=threat.intelligence_source,
        detection_count=threat.detection_count,
        is_active=threat.is_active,
        valid_from=threat.valid_from,
        valid_until=threat.valid_until,
        created_at=threat.created_at
    ) for threat in threats]

@router.post("/events/{event_id}/acknowledge")
async def acknowledge_security_event(
    event_id: int,
    acknowledgment_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Acknowledge a security event (typically sets status to investigating).
    """
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    
    # Update event status
    event.status = EventStatus.INVESTIGATING
    event.investigation_started_at = datetime.utcnow()
    event.investigated_by = current_user["username"]
    
    if acknowledgment_data and acknowledgment_data.get("notes"):
        event.investigation_notes = acknowledgment_data["notes"]
    
    event.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Security event acknowledged: {event.id} by user {current_user['username']}")
    
    return {"message": "Security event acknowledged successfully", "event_id": event_id}

