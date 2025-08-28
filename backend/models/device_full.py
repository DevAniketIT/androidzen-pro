"""
Device model for storing Android device information and connection history.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .core.database import Base
import json
from datetime import datetime
from typing import Dict, Any, Optional


class Device(Base):
    """
    Model representing an Android device and its properties.
    """
    __tablename__ = "devices"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Device identification
    device_id = Column(String(255), unique=True, index=True, nullable=False)  # ADB device ID
    serial_number = Column(String(255), unique=True, index=True)
    imei = Column(String(50), unique=True, nullable=True)
    
    # Device information
    device_name = Column(String(255), nullable=True)  # User-assigned name
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    product = Column(String(100), nullable=True)
    
    # System information
    android_version = Column(String(50), nullable=True)
    api_level = Column(Integer, nullable=True)
    build_number = Column(String(255), nullable=True)
    security_patch = Column(String(50), nullable=True)
    
    # Hardware information
    cpu_architecture = Column(String(50), nullable=True)
    ram_total = Column(Integer, nullable=True)  # in MB
    storage_total = Column(Integer, nullable=True)  # in MB
    screen_resolution = Column(String(50), nullable=True)  # e.g., "1920x1080"
    screen_density = Column(Integer, nullable=True)  # DPI
    
    # Connection information
    connection_type = Column(String(20), nullable=True)  # "usb", "wireless", "emulator"
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    port = Column(Integer, nullable=True)
    is_connected = Column(Boolean, default=False, index=True)
    is_rooted = Column(Boolean, default=False)
    developer_options_enabled = Column(Boolean, default=False)
    usb_debugging_enabled = Column(Boolean, default=False)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, index=True)
    last_seen = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    first_connected = Column(DateTime(timezone=True), default=func.now())
    total_connections = Column(Integer, default=1)
    
    # Additional properties (JSON field for flexibility)
    properties = Column(JSON, nullable=True)  # Store additional device properties
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    connection_history = relationship("DeviceConnectionHistory", back_populates="device", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="device", cascade="all, delete-orphan")
    security_events = relationship("SecurityEvent", back_populates="device", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Device(id={self.id}, device_id='{self.device_id}', model='{self.model}', connected={self.is_connected})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary representation."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "serial_number": self.serial_number,
            "device_name": self.device_name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "brand": self.brand,
            "android_version": self.android_version,
            "api_level": self.api_level,
            "connection_type": self.connection_type,
            "is_connected": self.is_connected,
            "is_rooted": self.is_rooted,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "properties": self.properties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_connection_status(self, connected: bool):
        """Update device connection status and increment connection count."""
        self.is_connected = connected
        self.last_seen = datetime.utcnow()
        if connected:
            self.total_connections += 1
    
    def set_property(self, key: str, value: Any):
        """Set a custom property for the device."""
        if self.properties is None:
            self.properties = {}
        self.properties[key] = value
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a custom property value."""
        if self.properties is None:
            return default
        return self.properties.get(key, default)


class DeviceConnectionHistory(Base):
    """
    Model for tracking device connection history and events.
    """
    __tablename__ = "device_connection_history"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to device
    device_id = Column(Integer, ForeignKey("devices.id"), index=True, nullable=False)
    
    # Connection details
    connection_type = Column(String(20), nullable=False)  # "usb", "wireless", "emulator"
    event_type = Column(String(20), nullable=False)  # "connected", "disconnected", "reconnected"
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)
    
    # Session information
    session_duration = Column(Integer, nullable=True)  # Duration in seconds
    connection_quality = Column(String(20), nullable=True)  # "excellent", "good", "fair", "poor"
    
    # Event metadata
    error_message = Column(Text, nullable=True)
    additional_info = Column(JSON, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    
    # Relationship back to device
    device = relationship("Device", back_populates="connection_history")
    
    def __repr__(self):
        return f"<DeviceConnectionHistory(id={self.id}, device_id={self.device_id}, event='{self.event_type}', timestamp={self.timestamp})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection history to dictionary representation."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "connection_type": self.connection_type,
            "event_type": self.event_type,
            "ip_address": self.ip_address,
            "port": self.port,
            "session_duration": self.session_duration,
            "connection_quality": self.connection_quality,
            "error_message": self.error_message,
            "additional_info": self.additional_info,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

