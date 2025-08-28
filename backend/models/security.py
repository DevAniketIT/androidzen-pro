"""
Security events model for storing alerts and suspicious activities.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from .core.database import Base
from datetime import datetime
from typing import Dict, Any, Optional, List
import enum


class SeverityLevel(enum.Enum):
    """Enumeration for security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(enum.Enum):
    """Enumeration for security event status."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    IGNORED = "ignored"


class SecurityEvent(Base):
    """
    Model for storing security events, alerts, and suspicious activities.
    """
    __tablename__ = "security_events"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to device
    device_id = Column(Integer, ForeignKey("devices.id"), index=True, nullable=False)
    
    # Event identification
    event_type = Column(String(50), nullable=False, index=True)  # "suspicious_app", "root_detection", "malware", "unauthorized_access", "data_breach", "system_modification"
    event_category = Column(String(50), nullable=True, index=True)  # Category grouping
    event_title = Column(String(200), nullable=False)
    event_description = Column(Text, nullable=True)
    
    # Severity and status
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    status = Column(Enum(EventStatus), default=EventStatus.OPEN, index=True)
    risk_score = Column(Float, nullable=True)  # Risk score (0-100)
    confidence_level = Column(Float, nullable=True)  # Confidence in detection (0-1)
    
    # Source information
    detection_method = Column(String(50), nullable=True)  # "adb", "system_log", "app_scan", "behavior_analysis"
    source_component = Column(String(100), nullable=True)  # Component that detected the event
    source_data = Column(JSON, nullable=True)  # Raw source data
    
    # App-related information (if applicable)
    app_package_name = Column(String(255), nullable=True, index=True)
    app_name = Column(String(200), nullable=True)
    app_version = Column(String(50), nullable=True)
    app_permissions = Column(JSON, nullable=True)  # Suspicious permissions
    
    # Network-related information
    network_address = Column(String(45), nullable=True)  # IP address involved
    network_port = Column(Integer, nullable=True)
    network_protocol = Column(String(20), nullable=True)
    network_data_size = Column(Integer, nullable=True)  # Data transferred in bytes
    
    # File system information
    file_path = Column(String(500), nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash
    file_size = Column(Integer, nullable=True)
    file_permissions = Column(String(20), nullable=True)
    
    # System information
    system_process = Column(String(200), nullable=True)
    system_user = Column(String(100), nullable=True)
    system_command = Column(Text, nullable=True)
    
    # Location and context
    location_lat = Column(Float, nullable=True)  # GPS coordinates if relevant
    location_lon = Column(Float, nullable=True)
    location_accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    context_data = Column(JSON, nullable=True)  # Additional context information
    
    # Response and mitigation
    auto_response_taken = Column(Boolean, default=False)
    response_actions = Column(JSON, nullable=True)  # Actions taken automatically
    mitigation_steps = Column(Text, nullable=True)  # Recommended mitigation steps
    is_mitigated = Column(Boolean, default=False)
    
    # Analysis results
    threat_indicators = Column(JSON, nullable=True)  # IOCs (Indicators of Compromise)
    behavioral_patterns = Column(JSON, nullable=True)  # Detected patterns
    anomaly_score = Column(Float, nullable=True)  # Anomaly detection score
    
    # Metadata
    event_count = Column(Integer, default=1)  # Number of similar events
    last_occurrence = Column(DateTime(timezone=True), default=func.now())
    first_occurrence = Column(DateTime(timezone=True), default=func.now())
    is_recurring = Column(Boolean, default=False, index=True)
    
    # Investigation
    investigated_by = Column(String(100), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    investigation_started_at = Column(DateTime(timezone=True), nullable=True)
    investigation_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Resolution
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolution_action = Column(String(100), nullable=True)  # What was done to resolve
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    device = relationship("Device", back_populates="security_events")
    security_alerts = relationship("SecurityAlert", back_populates="security_event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, device_id={self.device_id}, type='{self.event_type}', severity='{self.severity.value}', status='{self.status.value}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security event to dictionary representation."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "event_title": self.event_title,
            "event_description": self.event_description,
            "severity": self.severity.value if self.severity else None,
            "status": self.status.value if self.status else None,
            "risk_score": self.risk_score,
            "confidence_level": self.confidence_level,
            "detection_method": self.detection_method,
            "app_package_name": self.app_package_name,
            "app_name": self.app_name,
            "network_address": self.network_address,
            "file_path": self.file_path,
            "auto_response_taken": self.auto_response_taken,
            "is_mitigated": self.is_mitigated,
            "event_count": self.event_count,
            "is_recurring": self.is_recurring,
            "context_data": self.context_data,
            "threat_indicators": self.threat_indicators,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def calculate_risk_score(self):
        """Calculate risk score based on event properties."""
        base_score = 0
        
        # Severity-based scoring
        severity_scores = {
            SeverityLevel.LOW: 25,
            SeverityLevel.MEDIUM: 50,
            SeverityLevel.HIGH: 75,
            SeverityLevel.CRITICAL: 100
        }
        base_score = severity_scores.get(self.severity, 0)
        
        # Adjust based on confidence level
        if self.confidence_level:
            base_score *= self.confidence_level
        
        # Adjust based on recurrence
        if self.is_recurring:
            base_score *= 1.2  # 20% increase for recurring events
        
        # Adjust based on event count
        if self.event_count > 1:
            base_score *= min(1.5, 1 + (self.event_count - 1) * 0.1)
        
        self.risk_score = min(100, round(base_score, 2))
        return self.risk_score
    
    def mark_as_resolved(self, resolved_by: str, resolution_notes: str = None, resolution_action: str = None):
        """Mark the security event as resolved."""
        self.status = EventStatus.RESOLVED
        self.resolved_by = resolved_by
        self.resolution_notes = resolution_notes
        self.resolution_action = resolution_action
        self.resolved_at = datetime.utcnow()
        self.is_mitigated = True
    
    def increment_occurrence(self):
        """Increment occurrence count for recurring events."""
        self.event_count += 1
        self.last_occurrence = datetime.utcnow()
        if self.event_count > 1:
            self.is_recurring = True


class SecurityAlert(Base):
    """
    Model for storing security alerts and notifications sent to users.
    """
    __tablename__ = "security_alerts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to security event
    security_event_id = Column(Integer, ForeignKey("security_events.id"), index=True, nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False, index=True)  # "email", "push", "dashboard", "sms"
    alert_title = Column(String(200), nullable=False)
    alert_message = Column(Text, nullable=False)
    alert_priority = Column(String(20), default="normal")  # "low", "normal", "high", "urgent"
    
    # Recipient information
    recipient_type = Column(String(20), nullable=True)  # "user", "admin", "system"
    recipient_id = Column(String(100), nullable=True)
    recipient_address = Column(String(255), nullable=True)  # Email, phone number, etc.
    
    # Delivery status
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status tracking
    status = Column(String(20), default="pending", index=True)  # "pending", "sent", "delivered", "failed", "acknowledged"
    delivery_attempts = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Alert configuration
    is_automatic = Column(Boolean, default=True)  # Auto-generated vs manual
    suppress_similar = Column(Boolean, default=False)  # Suppress similar alerts
    expiry_time = Column(DateTime(timezone=True), nullable=True)  # When alert expires
    
    # Response tracking
    response_required = Column(Boolean, default=False)
    response_deadline = Column(DateTime(timezone=True), nullable=True)
    response_received = Column(Boolean, default=False)
    response_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    security_event = relationship("SecurityEvent", back_populates="security_alerts")
    
    def __repr__(self):
        return f"<SecurityAlert(id={self.id}, event_id={self.security_event_id}, type='{self.alert_type}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security alert to dictionary representation."""
        return {
            "id": self.id,
            "security_event_id": self.security_event_id,
            "alert_type": self.alert_type,
            "alert_title": self.alert_title,
            "alert_message": self.alert_message,
            "alert_priority": self.alert_priority,
            "recipient_type": self.recipient_type,
            "recipient_id": self.recipient_id,
            "status": self.status,
            "delivery_attempts": self.delivery_attempts,
            "response_required": self.response_required,
            "response_received": self.response_received,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mark_as_sent(self):
        """Mark alert as sent."""
        self.status = "sent"
        self.sent_at = datetime.utcnow()
        self.delivery_attempts += 1
    
    def mark_as_delivered(self):
        """Mark alert as delivered."""
        self.status = "delivered"
        self.delivered_at = datetime.utcnow()
    
    def mark_as_acknowledged(self, response_data: Dict[str, Any] = None):
        """Mark alert as acknowledged by recipient."""
        self.status = "acknowledged"
        self.acknowledged_at = datetime.utcnow()
        self.response_received = True
        if response_data:
            self.response_data = response_data


class ThreatIntelligence(Base):
    """
    Model for storing threat intelligence data and IOCs.
    """
    __tablename__ = "threat_intelligence"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Threat identification
    threat_type = Column(String(50), nullable=False, index=True)  # "malware", "phishing", "c2_server", "malicious_domain"
    threat_name = Column(String(200), nullable=True)
    threat_family = Column(String(100), nullable=True, index=True)
    
    # IOC (Indicator of Compromise) information
    ioc_type = Column(String(50), nullable=False, index=True)  # "hash", "domain", "ip", "url", "email", "package_name"
    ioc_value = Column(String(500), nullable=False, index=True)
    ioc_description = Column(Text, nullable=True)
    
    # Threat metadata
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    confidence_score = Column(Float, nullable=True)  # Confidence in the intelligence (0-1)
    reputation_score = Column(Float, nullable=True)  # Reputation score (-100 to 100)
    
    # Source information
    intelligence_source = Column(String(100), nullable=True)  # Source of the intelligence
    source_reliability = Column(String(20), nullable=True)  # "A", "B", "C", "D", "E", "F"
    source_url = Column(Text, nullable=True)
    
    # Temporal information
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    valid_from = Column(DateTime(timezone=True), default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Classification
    tags = Column(JSON, nullable=True)  # Classification tags
    tlp_marking = Column(String(20), default="white")  # Traffic Light Protocol marking
    is_active = Column(Boolean, default=True, index=True)
    
    # Usage statistics
    detection_count = Column(Integer, default=0)  # How many times this IOC was detected
    last_detected = Column(DateTime(timezone=True), nullable=True)
    
    # Additional context
    context_data = Column(JSON, nullable=True)  # Additional context information
    related_threats = Column(JSON, nullable=True)  # Related threat indicators
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ThreatIntelligence(id={self.id}, type='{self.threat_type}', ioc='{self.ioc_type}:{self.ioc_value[:50]}...')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert threat intelligence to dictionary representation."""
        return {
            "id": self.id,
            "threat_type": self.threat_type,
            "threat_name": self.threat_name,
            "threat_family": self.threat_family,
            "ioc_type": self.ioc_type,
            "ioc_value": self.ioc_value,
            "ioc_description": self.ioc_description,
            "severity": self.severity.value if self.severity else None,
            "confidence_score": self.confidence_score,
            "reputation_score": self.reputation_score,
            "intelligence_source": self.intelligence_source,
            "tags": self.tags,
            "detection_count": self.detection_count,
            "is_active": self.is_active,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def increment_detection(self):
        """Increment detection count when IOC is matched."""
        self.detection_count += 1
        self.last_detected = datetime.utcnow()

