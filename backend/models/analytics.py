"""
Analytics model for storing device performance metrics and trends.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from .core.database import Base
from datetime import datetime
from typing import Dict, Any, Optional


class Analytics(Base):
    """
    Model for storing device analytics data including performance metrics.
    """
    __tablename__ = "analytics"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to device
    device_id = Column(Integer, ForeignKey("devices.id"), index=True, nullable=False)
    
    # Metric identification
    metric_type = Column(String(50), nullable=False, index=True)  # "performance", "storage", "battery", "network", "app_usage"
    metric_category = Column(String(50), nullable=True, index=True)  # subcategory for grouping
    
    # Performance metrics
    cpu_usage = Column(Float, nullable=True)  # Percentage (0-100)
    memory_usage = Column(Float, nullable=True)  # Percentage (0-100)
    memory_available = Column(Integer, nullable=True)  # Available RAM in MB
    memory_total = Column(Integer, nullable=True)  # Total RAM in MB
    
    # Storage metrics
    storage_used = Column(Integer, nullable=True)  # Used storage in MB
    storage_available = Column(Integer, nullable=True)  # Available storage in MB
    storage_total = Column(Integer, nullable=True)  # Total storage in MB
    storage_usage_percentage = Column(Float, nullable=True)  # Percentage (0-100)
    
    # Battery metrics
    battery_level = Column(Integer, nullable=True)  # Battery percentage (0-100)
    battery_temperature = Column(Float, nullable=True)  # Temperature in Celsius
    battery_voltage = Column(Float, nullable=True)  # Voltage
    battery_health = Column(String(20), nullable=True)  # "Good", "Fair", "Poor"
    charging_status = Column(String(20), nullable=True)  # "Charging", "Discharging", "Full"
    
    # Network metrics
    network_type = Column(String(20), nullable=True)  # "WiFi", "Mobile", "Ethernet"
    network_strength = Column(Integer, nullable=True)  # Signal strength (-100 to 0 dBm)
    data_received = Column(Integer, nullable=True)  # Bytes received
    data_transmitted = Column(Integer, nullable=True)  # Bytes transmitted
    
    # Application metrics
    app_count_total = Column(Integer, nullable=True)  # Total installed apps
    app_count_system = Column(Integer, nullable=True)  # System apps
    app_count_user = Column(Integer, nullable=True)  # User-installed apps
    running_processes = Column(Integer, nullable=True)  # Number of running processes
    
    # Temperature and thermal metrics
    cpu_temperature = Column(Float, nullable=True)  # CPU temperature in Celsius
    gpu_temperature = Column(Float, nullable=True)  # GPU temperature in Celsius
    thermal_state = Column(String(20), nullable=True)  # "Normal", "Warning", "Critical"
    
    # Performance scores (calculated metrics)
    performance_score = Column(Float, nullable=True)  # Overall performance score (0-100)
    optimization_score = Column(Float, nullable=True)  # Optimization score (0-100)
    health_score = Column(Float, nullable=True)  # Device health score (0-100)
    
    # Additional metrics (JSON for flexibility)
    additional_metrics = Column(JSON, nullable=True)
    
    # Metadata
    collection_method = Column(String(50), nullable=True)  # "adb", "system", "app"
    data_source = Column(String(100), nullable=True)  # Source of the metrics
    is_anomaly = Column(Boolean, default=False, index=True)  # Flag for anomalous readings
    confidence_level = Column(Float, nullable=True)  # Confidence in the data (0-1)
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    device = relationship("Device", back_populates="analytics")
    
    def __repr__(self):
        return f"<Analytics(id={self.id}, device_id={self.device_id}, type='{self.metric_type}', recorded_at={self.recorded_at})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analytics record to dictionary representation."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "metric_type": self.metric_type,
            "metric_category": self.metric_category,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "memory_available": self.memory_available,
            "memory_total": self.memory_total,
            "storage_used": self.storage_used,
            "storage_available": self.storage_available,
            "storage_total": self.storage_total,
            "storage_usage_percentage": self.storage_usage_percentage,
            "battery_level": self.battery_level,
            "battery_temperature": self.battery_temperature,
            "battery_health": self.battery_health,
            "charging_status": self.charging_status,
            "network_type": self.network_type,
            "network_strength": self.network_strength,
            "app_count_total": self.app_count_total,
            "running_processes": self.running_processes,
            "performance_score": self.performance_score,
            "optimization_score": self.optimization_score,
            "health_score": self.health_score,
            "additional_metrics": self.additional_metrics,
            "is_anomaly": self.is_anomaly,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def calculate_performance_score(self):
        """Calculate overall performance score based on available metrics."""
        score = 100.0
        weight_count = 0
        
        # CPU usage impact (higher usage = lower score)
        if self.cpu_usage is not None:
            cpu_score = max(0, 100 - self.cpu_usage)
            score = (score * weight_count + cpu_score) / (weight_count + 1)
            weight_count += 1
        
        # Memory usage impact
        if self.memory_usage is not None:
            memory_score = max(0, 100 - self.memory_usage)
            score = (score * weight_count + memory_score) / (weight_count + 1)
            weight_count += 1
        
        # Storage usage impact
        if self.storage_usage_percentage is not None:
            storage_score = max(0, 100 - self.storage_usage_percentage)
            score = (score * weight_count + storage_score * 0.5) / (weight_count + 0.5)  # Lower weight
            weight_count += 0.5
        
        # Battery level impact
        if self.battery_level is not None:
            battery_score = self.battery_level
            score = (score * weight_count + battery_score * 0.3) / (weight_count + 0.3)  # Lower weight
            weight_count += 0.3
        
        self.performance_score = round(score, 2) if weight_count > 0 else None
        return self.performance_score


class StorageTrend(Base):
    """
    Model for tracking storage usage trends over time.
    """
    __tablename__ = "storage_trends"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to device
    device_id = Column(Integer, ForeignKey("devices.id"), index=True, nullable=False)
    
    # Trend data
    period_type = Column(String(20), nullable=False, index=True)  # "hourly", "daily", "weekly", "monthly"
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Storage metrics
    avg_storage_used = Column(Float, nullable=True)  # Average storage used in MB
    max_storage_used = Column(Float, nullable=True)  # Maximum storage used in MB
    min_storage_used = Column(Float, nullable=True)  # Minimum storage used in MB
    storage_change = Column(Float, nullable=True)  # Change in storage usage (MB)
    storage_change_percentage = Column(Float, nullable=True)  # Percentage change
    
    # Application breakdown
    app_data_size = Column(Integer, nullable=True)  # Total app data in MB
    system_data_size = Column(Integer, nullable=True)  # System data in MB
    cache_size = Column(Integer, nullable=True)  # Cache size in MB
    media_size = Column(Integer, nullable=True)  # Media files size in MB
    
    # Trend analysis
    trend_direction = Column(String(20), nullable=True)  # "increasing", "decreasing", "stable"
    growth_rate = Column(Float, nullable=True)  # Storage growth rate per period
    predicted_full_date = Column(DateTime(timezone=True), nullable=True)  # When storage might be full
    
    # Metadata
    data_points = Column(Integer, nullable=True)  # Number of data points in the trend
    confidence_level = Column(Float, nullable=True)  # Confidence in the trend analysis (0-1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<StorageTrend(id={self.id}, device_id={self.device_id}, period='{self.period_type}', trend='{self.trend_direction}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert storage trend to dictionary representation."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "avg_storage_used": self.avg_storage_used,
            "max_storage_used": self.max_storage_used,
            "min_storage_used": self.min_storage_used,
            "storage_change": self.storage_change,
            "storage_change_percentage": self.storage_change_percentage,
            "trend_direction": self.trend_direction,
            "growth_rate": self.growth_rate,
            "predicted_full_date": self.predicted_full_date.isoformat() if self.predicted_full_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

