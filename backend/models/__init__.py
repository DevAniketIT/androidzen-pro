# Models package
from .user import User, UserSession
from .device import Device, DeviceConnectionHistory
from .analytics import Analytics, StorageTrend
from .settings import OptimizationProfile, UserSettings, ProfileApplication
from .security import SecurityEvent, SecurityAlert, ThreatIntelligence, SeverityLevel, EventStatus

# Import Base for database initialization
from .core.database import Base

# List all models for easy access
__all__ = [
    "User",
    "UserSession",
    "Device",
    "DeviceConnectionHistory", 
    "Analytics",
    "StorageTrend",
    "OptimizationProfile",
    "UserSettings", 
    "ProfileApplication",
    "SecurityEvent",
    "SecurityAlert",
    "ThreatIntelligence",
    "SeverityLevel",
    "EventStatus",
    "Base"
]

