"""
Settings model for optimization profiles and user preferences.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from .core.database import Base
from datetime import datetime
from typing import Dict, Any, Optional, List
import json


class OptimizationProfile(Base):
    """
    Model for storing device optimization profiles and configurations.
    """
    __tablename__ = "optimization_profiles"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Profile identification
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    profile_type = Column(String(50), nullable=False, index=True)  # "battery", "performance", "balanced", "gaming", "custom"
    
    # Profile status
    is_active = Column(Boolean, default=False, index=True)
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # System-defined vs user-created
    
    # Optimization settings
    cpu_governor = Column(String(50), nullable=True)  # CPU governor mode
    cpu_max_frequency = Column(Integer, nullable=True)  # Max CPU frequency in MHz
    cpu_min_frequency = Column(Integer, nullable=True)  # Min CPU frequency in MHz
    
    # Display settings
    brightness_level = Column(Integer, nullable=True)  # Screen brightness (0-255)
    screen_timeout = Column(Integer, nullable=True)  # Screen timeout in seconds
    adaptive_brightness = Column(Boolean, nullable=True)
    
    # Network settings
    wifi_optimization = Column(Boolean, default=True)
    mobile_data_limit = Column(Integer, nullable=True)  # Data limit in MB
    background_data_restriction = Column(Boolean, default=False)
    
    # Battery optimization
    battery_saver_enabled = Column(Boolean, default=False)
    doze_mode_enabled = Column(Boolean, default=True)
    app_standby_enabled = Column(Boolean, default=True)
    background_app_limit = Column(Integer, nullable=True)  # Max background apps
    
    # Performance settings
    animation_scale = Column(Float, default=1.0)  # Animation scale (0.0-2.0)
    force_gpu_rendering = Column(Boolean, default=False)
    hardware_acceleration = Column(Boolean, default=True)
    
    # Storage optimization
    auto_cache_clear = Column(Boolean, default=False)
    cache_clear_interval = Column(Integer, nullable=True)  # Interval in hours
    storage_cleanup_enabled = Column(Boolean, default=False)
    storage_threshold = Column(Integer, default=90)  # Storage usage threshold (%)
    
    # Security settings
    app_verification_enabled = Column(Boolean, default=True)
    unknown_sources_allowed = Column(Boolean, default=False)
    auto_security_updates = Column(Boolean, default=True)
    
    # Advanced settings (JSON for complex configurations)
    advanced_settings = Column(JSON, nullable=True)
    
    # Profile usage statistics
    times_applied = Column(Integer, default=0)
    last_applied = Column(DateTime(timezone=True), nullable=True)
    effectiveness_score = Column(Float, nullable=True)  # Effectiveness rating (0-100)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user_settings = relationship("UserSettings", back_populates="optimization_profile")
    profile_applications = relationship("ProfileApplication", back_populates="profile", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OptimizationProfile(id={self.id}, name='{self.name}', type='{self.profile_type}', active={self.is_active})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert optimization profile to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "profile_type": self.profile_type,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "is_system": self.is_system,
            "cpu_governor": self.cpu_governor,
            "cpu_max_frequency": self.cpu_max_frequency,
            "brightness_level": self.brightness_level,
            "screen_timeout": self.screen_timeout,
            "battery_saver_enabled": self.battery_saver_enabled,
            "animation_scale": self.animation_scale,
            "auto_cache_clear": self.auto_cache_clear,
            "advanced_settings": self.advanced_settings,
            "times_applied": self.times_applied,
            "effectiveness_score": self.effectiveness_score,
            "last_applied": self.last_applied.isoformat() if self.last_applied else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def apply_profile(self):
        """Mark profile as applied and update statistics."""
        self.times_applied += 1
        self.last_applied = datetime.utcnow()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get an advanced setting value."""
        if self.advanced_settings is None:
            return default
        return self.advanced_settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Set an advanced setting value."""
        if self.advanced_settings is None:
            self.advanced_settings = {}
        self.advanced_settings[key] = value


class UserSettings(Base):
    """
    Model for storing user preferences and application settings.
    """
    __tablename__ = "user_settings"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User identification (if multi-user support is needed)
    user_id = Column(String(100), nullable=True, index=True)  # User identifier
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True, index=True)
    
    # General preferences
    theme = Column(String(20), default="light")  # "light", "dark", "auto"
    language = Column(String(10), default="en")  # Language code
    timezone = Column(String(50), nullable=True)
    
    # Notification preferences
    notifications_enabled = Column(Boolean, default=True)
    alert_thresholds = Column(JSON, nullable=True)  # Custom alert thresholds
    notification_frequency = Column(String(20), default="normal")  # "low", "normal", "high"
    
    # Monitoring preferences
    auto_monitoring_enabled = Column(Boolean, default=True)
    monitoring_interval = Column(Integer, default=300)  # Monitoring interval in seconds
    detailed_logging = Column(Boolean, default=False)
    
    # Optimization preferences
    optimization_profile_id = Column(Integer, ForeignKey("optimization_profiles.id"), nullable=True)
    auto_optimization = Column(Boolean, default=False)
    optimization_schedule = Column(JSON, nullable=True)  # Scheduled optimization times
    
    # Display preferences
    dashboard_layout = Column(JSON, nullable=True)  # Custom dashboard configuration
    chart_preferences = Column(JSON, nullable=True)  # Chart display preferences
    data_retention_days = Column(Integer, default=30)  # How long to keep analytics data
    
    # Security preferences
    require_confirmation = Column(Boolean, default=True)  # Require confirmation for actions
    auto_backup_settings = Column(Boolean, default=True)
    privacy_mode = Column(Boolean, default=False)  # Hide sensitive information
    
    # Performance preferences
    refresh_rate = Column(Integer, default=30)  # UI refresh rate in seconds
    animation_enabled = Column(Boolean, default=True)
    sound_enabled = Column(Boolean, default=True)
    
    # Advanced preferences (JSON for flexibility)
    advanced_preferences = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    optimization_profile = relationship("OptimizationProfile", back_populates="user_settings")
    
    def __repr__(self):
        return f"<UserSettings(id={self.id}, user_id='{self.user_id}', theme='{self.theme}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user settings to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "notifications_enabled": self.notifications_enabled,
            "alert_thresholds": self.alert_thresholds,
            "auto_monitoring_enabled": self.auto_monitoring_enabled,
            "monitoring_interval": self.monitoring_interval,
            "optimization_profile_id": self.optimization_profile_id,
            "auto_optimization": self.auto_optimization,
            "dashboard_layout": self.dashboard_layout,
            "data_retention_days": self.data_retention_days,
            "require_confirmation": self.require_confirmation,
            "privacy_mode": self.privacy_mode,
            "advanced_preferences": self.advanced_preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get an advanced preference value."""
        if self.advanced_preferences is None:
            return default
        return self.advanced_preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any):
        """Set an advanced preference value."""
        if self.advanced_preferences is None:
            self.advanced_preferences = {}
        self.advanced_preferences[key] = value
    
    def get_alert_threshold(self, metric: str, default: float = None) -> float:
        """Get alert threshold for a specific metric."""
        if self.alert_thresholds is None:
            return default
        return self.alert_thresholds.get(metric, default)
    
    def set_alert_threshold(self, metric: str, threshold: float):
        """Set alert threshold for a specific metric."""
        if self.alert_thresholds is None:
            self.alert_thresholds = {}
        self.alert_thresholds[metric] = threshold


class ProfileApplication(Base):
    """
    Model for tracking when optimization profiles are applied to devices.
    """
    __tablename__ = "profile_applications"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    profile_id = Column(Integer, ForeignKey("optimization_profiles.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    
    # Application details
    applied_by = Column(String(100), nullable=True)  # User or system
    application_method = Column(String(50), nullable=True)  # "manual", "automatic", "scheduled"
    
    # Results
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    settings_changed = Column(JSON, nullable=True)  # What settings were actually changed
    
    # Performance impact
    before_performance_score = Column(Float, nullable=True)
    after_performance_score = Column(Float, nullable=True)
    performance_improvement = Column(Float, nullable=True)  # Percentage improvement
    
    # Timestamps
    applied_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    reverted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    profile = relationship("OptimizationProfile", back_populates="profile_applications")
    
    def __repr__(self):
        return f"<ProfileApplication(id={self.id}, profile_id={self.profile_id}, device_id={self.device_id}, success={self.success})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile application to dictionary representation."""
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "device_id": self.device_id,
            "applied_by": self.applied_by,
            "application_method": self.application_method,
            "success": self.success,
            "error_message": self.error_message,
            "settings_changed": self.settings_changed,
            "before_performance_score": self.before_performance_score,
            "after_performance_score": self.after_performance_score,
            "performance_improvement": self.performance_improvement,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "reverted_at": self.reverted_at.isoformat() if self.reverted_at else None
        }

