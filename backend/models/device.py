"""
Device model for storing Android device information.

This is a minimal stub implementation for database queries.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, relationship
from .core.database import Base
from typing import Dict, Any, Optional, List
from datetime import datetime


class Device(Base):
    """
    Model representing an Android device.
    
    This is a minimal stub implementation with core fields for database queries.
    """
    __tablename__ = "devices"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Device identification
    device_id = Column(String(255), unique=True, index=True, nullable=False)
    serial_number = Column(String(255), unique=True, index=True)
    
    # Basic device information
    device_name = Column(String(255), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    android_version = Column(String(50), nullable=True)
    
    # Connection status
    is_connected = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    last_seen = Column(DateTime(timezone=True), default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    connection_history = relationship("DeviceConnectionHistory", back_populates="device", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Device(id={self.id}, device_id='{self.device_id}', model='{self.model}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary representation."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "serial_number": self.serial_number,
            "device_name": self.device_name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "android_version": self.android_version,
            "is_connected": self.is_connected,
            "is_active": self.is_active,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_by_device_id(cls, db: Session, device_id: str) -> Optional['Device']:
        """
        Get device by device ID.
        
        Args:
            db: Database session
            device_id: Device ID to search for
            
        Returns:
            Device instance if found, None otherwise
        """
        return db.query(cls).filter(cls.device_id == device_id).first()
    
    @classmethod
    def get_all_active(cls, db: Session) -> List['Device']:
        """
        Get all active devices.
        
        Args:
            db: Database session
            
        Returns:
            List of active Device instances
        """
        return db.query(cls).filter(cls.is_active == True).all()
    
    @classmethod
    def get_connected_devices(cls, db: Session) -> List['Device']:
        """
        Get all currently connected devices.
        
        Args:
            db: Database session
            
        Returns:
            List of connected Device instances
        """
        return db.query(cls).filter(
            cls.is_connected == True, 
            cls.is_active == True
        ).all()
    
    @classmethod
    def create_device(cls, db: Session, device_data: Dict[str, Any]) -> 'Device':
        """
        Create a new device record.
        
        Args:
            db: Database session
            device_data: Dictionary containing device information
            
        Returns:
            Created Device instance
        """
        device = cls(**device_data)
        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    
    def update_status(self, db: Session, **kwargs) -> None:
        """
        Update device status.
        
        Args:
            db: Database session
            **kwargs: Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(self)


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

