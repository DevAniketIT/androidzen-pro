"""
Settings optimization API endpoints for AndroidZen Pro.
Handles optimization profiles, user preferences, and system settings management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from .core.database import get_db
from .models.device import Device
from .models.settings import OptimizationProfile, UserSettings, ProfileApplication
from .core.auth import get_current_active_user
from .core.adb_manager import AdbManager
from .services.settings_service import SettingsService, OptimizationRecommendation as ServiceRecommendation

logger = logging.getLogger(__name__)

# Initialize ADB Manager as a global singleton
adb_manager = AdbManager(auto_connect=True)

router = APIRouter()

# Pydantic models for request/response
class OptimizationProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    profile_type: str  # "battery", "performance", "balanced", "gaming", "custom"
    cpu_governor: Optional[str] = None
    cpu_max_frequency: Optional[int] = None
    cpu_min_frequency: Optional[int] = None
    brightness_level: Optional[int] = None
    screen_timeout: Optional[int] = None
    adaptive_brightness: Optional[bool] = None
    wifi_optimization: Optional[bool] = True
    battery_saver_enabled: Optional[bool] = False
    animation_scale: Optional[float] = 1.0
    advanced_settings: Optional[Dict[str, Any]] = None

class OptimizationProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    cpu_governor: Optional[str] = None
    cpu_max_frequency: Optional[int] = None
    brightness_level: Optional[int] = None
    screen_timeout: Optional[int] = None
    battery_saver_enabled: Optional[bool] = None
    animation_scale: Optional[float] = None
    advanced_settings: Optional[Dict[str, Any]] = None

class OptimizationProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    profile_type: str
    is_active: bool
    is_default: bool
    is_system: bool
    cpu_governor: Optional[str]
    brightness_level: Optional[int]
    screen_timeout: Optional[int]
    battery_saver_enabled: Optional[bool]
    animation_scale: Optional[float]
    times_applied: int
    effectiveness_score: Optional[float]
    last_applied: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class UserSettingsCreate(BaseModel):
    user_id: Optional[str] = None
    device_id: Optional[int] = None
    theme: Optional[str] = "light"
    language: Optional[str] = "en"
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = True
    auto_monitoring_enabled: Optional[bool] = True
    monitoring_interval: Optional[int] = 300
    optimization_profile_id: Optional[int] = None
    auto_optimization: Optional[bool] = False

class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    auto_monitoring_enabled: Optional[bool] = None
    monitoring_interval: Optional[int] = None
    optimization_profile_id: Optional[int] = None
    auto_optimization: Optional[bool] = None
    alert_thresholds: Optional[Dict[str, float]] = None
    advanced_preferences: Optional[Dict[str, Any]] = None

class UserSettingsResponse(BaseModel):
    id: int
    user_id: Optional[str]
    device_id: Optional[int]
    theme: str
    language: str
    timezone: Optional[str]
    notifications_enabled: bool
    auto_monitoring_enabled: bool
    monitoring_interval: int
    optimization_profile_id: Optional[int]
    auto_optimization: bool
    data_retention_days: int
    created_at: datetime
    updated_at: datetime

class ProfileApplicationRequest(BaseModel):
    device_id: str
    profile_id: int
    application_method: Optional[str] = "manual"

class ProfileApplicationResponse(BaseModel):
    id: int
    profile_id: int
    device_id: int
    applied_by: Optional[str]
    application_method: Optional[str]
    success: bool
    error_message: Optional[str]
    performance_improvement: Optional[float]
    applied_at: datetime

class OptimizationRecommendation(BaseModel):
    device_id: str
    recommendation_type: str
    title: str
    description: str
    potential_improvement: str
    difficulty: str  # "easy", "medium", "advanced"
    estimated_impact: int  # 1-10 scale
    recommended_profile: Optional[int] = None
    action_required: str
    
class SettingsBackupCreate(BaseModel):
    device_id: str
    backup_name: str
    
class SettingsBackupResponse(BaseModel):
    backup_id: str
    device_id: str
    backup_name: str
    created_at: datetime
    size: int
    checksum: str
    settings_count: Dict[str, int]
    
class SettingsRestoreRequest(BaseModel):
    device_id: str
    backup_id: str
    namespaces: Optional[List[str]] = None

# Optimization Profiles endpoints
@router.get("/profiles", response_model=List[OptimizationProfileResponse])
async def list_optimization_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    profile_type: Optional[str] = Query(None),
    active_only: bool = Query(False),
    system_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get list of optimization profiles with optional filtering.
    """
    query = db.query(OptimizationProfile)
    
    if profile_type:
        query = query.filter(OptimizationProfile.profile_type == profile_type)
    
    if active_only:
        query = query.filter(OptimizationProfile.is_active == True)
    
    if system_only:
        query = query.filter(OptimizationProfile.is_system == True)
    
    profiles = query.offset(skip).limit(limit).all()
    
    return [OptimizationProfileResponse(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        profile_type=profile.profile_type,
        is_active=profile.is_active,
        is_default=profile.is_default,
        is_system=profile.is_system,
        cpu_governor=profile.cpu_governor,
        brightness_level=profile.brightness_level,
        screen_timeout=profile.screen_timeout,
        battery_saver_enabled=profile.battery_saver_enabled,
        animation_scale=profile.animation_scale,
        times_applied=profile.times_applied,
        effectiveness_score=profile.effectiveness_score,
        last_applied=profile.last_applied,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    ) for profile in profiles]

@router.post("/profiles", response_model=OptimizationProfileResponse)
async def create_optimization_profile(
    profile_data: OptimizationProfileCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Create a new optimization profile.
    """
    # Validate profile type
    valid_types = ["battery", "performance", "balanced", "gaming", "custom"]
    if profile_data.profile_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid profile type. Must be one of: {valid_types}"
        )
    
    # Check if profile name already exists
    existing_profile = db.query(OptimizationProfile).filter(
        OptimizationProfile.name == profile_data.name
    ).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile with this name already exists"
        )
    
    profile = OptimizationProfile(
        name=profile_data.name,
        description=profile_data.description,
        profile_type=profile_data.profile_type,
        is_system=False,  # User-created profiles are not system profiles
        cpu_governor=profile_data.cpu_governor,
        cpu_max_frequency=profile_data.cpu_max_frequency,
        cpu_min_frequency=profile_data.cpu_min_frequency,
        brightness_level=profile_data.brightness_level,
        screen_timeout=profile_data.screen_timeout,
        adaptive_brightness=profile_data.adaptive_brightness,
        wifi_optimization=profile_data.wifi_optimization,
        battery_saver_enabled=profile_data.battery_saver_enabled,
        animation_scale=profile_data.animation_scale,
        advanced_settings=profile_data.advanced_settings
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    logger.info(f"Optimization profile created: {profile.name} by user {current_user['username']}")
    
    return OptimizationProfileResponse(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        profile_type=profile.profile_type,
        is_active=profile.is_active,
        is_default=profile.is_default,
        is_system=profile.is_system,
        cpu_governor=profile.cpu_governor,
        brightness_level=profile.brightness_level,
        screen_timeout=profile.screen_timeout,
        battery_saver_enabled=profile.battery_saver_enabled,
        animation_scale=profile.animation_scale,
        times_applied=profile.times_applied,
        effectiveness_score=profile.effectiveness_score,
        last_applied=profile.last_applied,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )

@router.get("/profiles/{profile_id}", response_model=OptimizationProfileResponse)
async def get_optimization_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed information about a specific optimization profile.
    """
    profile = db.query(OptimizationProfile).filter(OptimizationProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization profile not found"
        )
    
    return OptimizationProfileResponse(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        profile_type=profile.profile_type,
        is_active=profile.is_active,
        is_default=profile.is_default,
        is_system=profile.is_system,
        cpu_governor=profile.cpu_governor,
        brightness_level=profile.brightness_level,
        screen_timeout=profile.screen_timeout,
        battery_saver_enabled=profile.battery_saver_enabled,
        animation_scale=profile.animation_scale,
        times_applied=profile.times_applied,
        effectiveness_score=profile.effectiveness_score,
        last_applied=profile.last_applied,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )

@router.put("/profiles/{profile_id}", response_model=OptimizationProfileResponse)
async def update_optimization_profile(
    profile_id: int,
    profile_data: OptimizationProfileUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update an optimization profile.
    """
    profile = db.query(OptimizationProfile).filter(OptimizationProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization profile not found"
        )
    
    # Don't allow updating system profiles unless user is admin
    if profile.is_system and not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system profiles"
        )
    
    # Update profile fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    
    profile.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(profile)
    
    logger.info(f"Optimization profile updated: {profile.name} by user {current_user['username']}")
    
    return OptimizationProfileResponse(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        profile_type=profile.profile_type,
        is_active=profile.is_active,
        is_default=profile.is_default,
        is_system=profile.is_system,
        cpu_governor=profile.cpu_governor,
        brightness_level=profile.brightness_level,
        screen_timeout=profile.screen_timeout,
        battery_saver_enabled=profile.battery_saver_enabled,
        animation_scale=profile.animation_scale,
        times_applied=profile.times_applied,
        effectiveness_score=profile.effectiveness_score,
        last_applied=profile.last_applied,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )

@router.delete("/profiles/{profile_id}")
async def delete_optimization_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Delete an optimization profile.
    """
    profile = db.query(OptimizationProfile).filter(OptimizationProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization profile not found"
        )
    
    # Don't allow deleting system profiles or default profiles
    if profile.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system profiles"
        )
    
    if profile.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete default profiles"
        )
    
    db.delete(profile)
    db.commit()
    
    logger.info(f"Optimization profile deleted: {profile.name} by user {current_user['username']}")
    
    return {"message": "Optimization profile deleted successfully"}

@router.post("/profiles/{profile_id}/apply", response_model=ProfileApplicationResponse)
async def apply_optimization_profile(
    profile_id: int,
    application_request: ProfileApplicationRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Apply an optimization profile to a device.
    """
    # Validate profile
    profile = db.query(OptimizationProfile).filter(OptimizationProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization profile not found"
        )
    
    # Validate device
    device = db.query(Device).filter(
        Device.device_id == application_request.device_id,
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
    
    # Use the settings service to apply the profile
    start_time = datetime.utcnow()
    settings_service = SettingsService(adb_manager, db)
    
    try:
        success = await settings_service.apply_optimization_profile(
            device_id=application_request.device_id,
            profile_id=profile_id,
            applied_by=current_user["username"]
        )
        
        # Get the application record that was created by the service
        application = db.query(ProfileApplication).filter(
            ProfileApplication.profile_id == profile_id,
            ProfileApplication.device_id == device.id,
            ProfileApplication.applied_at >= start_time
        ).order_by(ProfileApplication.applied_at.desc()).first()
        
        if not application:
            # If for some reason the application record wasn't found, create one
            application = ProfileApplication(
                profile_id=profile.id,
                device_id=device.id,
                applied_by=current_user["username"],
                application_method=application_request.application_method,
                success=success,
                error_message="Application record not created by service" if success else "Failed to apply profile",
                applied_at=datetime.utcnow()
            )
            db.add(application)
            db.commit()
            db.refresh(application)
    
    except Exception as e:
        logger.error(f"Error applying profile: {e}")
        # Create failure record
        application = ProfileApplication(
            profile_id=profile.id,
            device_id=device.id,
            applied_by=current_user["username"],
            application_method=application_request.application_method,
            success=False,
            error_message=str(e),
            applied_at=datetime.utcnow()
        )
        db.add(application)
        db.commit()
        db.refresh(application)
    
    logger.info(f"Optimization profile {'applied' if application.success else 'failed to apply'}: {profile.name} to device {device.device_id} by user {current_user['username']}")
    
    return ProfileApplicationResponse(
        id=application.id,
        profile_id=application.profile_id,
        device_id=application.device_id,
        applied_by=application.applied_by,
        application_method=application.application_method,
        success=application.success,
        error_message=application.error_message,
        performance_improvement=application.performance_improvement,
        applied_at=application.applied_at
    )

# User Settings endpoints
@router.get("/user-settings", response_model=List[UserSettingsResponse])
async def get_user_settings(
    user_id: Optional[str] = Query(None),
    device_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get user settings with optional filtering.
    """
    query = db.query(UserSettings)
    
    # Non-admin users can only see their own settings
    if not current_user.get("is_admin", False):
        query = query.filter(UserSettings.user_id == current_user["id"])
    elif user_id:
        query = query.filter(UserSettings.user_id == user_id)
    
    if device_id:
        query = query.filter(UserSettings.device_id == device_id)
    
    settings_list = query.all()
    
    return [UserSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        device_id=settings.device_id,
        theme=settings.theme,
        language=settings.language,
        timezone=settings.timezone,
        notifications_enabled=settings.notifications_enabled,
        auto_monitoring_enabled=settings.auto_monitoring_enabled,
        monitoring_interval=settings.monitoring_interval,
        optimization_profile_id=settings.optimization_profile_id,
        auto_optimization=settings.auto_optimization,
        data_retention_days=settings.data_retention_days,
        created_at=settings.created_at,
        updated_at=settings.updated_at
    ) for settings in settings_list]

@router.post("/user-settings", response_model=UserSettingsResponse)
async def create_user_settings(
    settings_data: UserSettingsCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Create new user settings.
    """
    # Set user_id to current user if not provided or if not admin
    if not current_user.get("is_admin", False) or not settings_data.user_id:
        settings_data.user_id = current_user["id"]
    
    # Validate optimization profile if provided
    if settings_data.optimization_profile_id:
        profile = db.query(OptimizationProfile).filter(
            OptimizationProfile.id == settings_data.optimization_profile_id
        ).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid optimization profile ID"
            )
    
    settings = UserSettings(
        user_id=settings_data.user_id,
        device_id=settings_data.device_id,
        theme=settings_data.theme,
        language=settings_data.language,
        timezone=settings_data.timezone,
        notifications_enabled=settings_data.notifications_enabled,
        auto_monitoring_enabled=settings_data.auto_monitoring_enabled,
        monitoring_interval=settings_data.monitoring_interval,
        optimization_profile_id=settings_data.optimization_profile_id,
        auto_optimization=settings_data.auto_optimization
    )
    
    db.add(settings)
    db.commit()
    db.refresh(settings)
    
    logger.info(f"User settings created for user {settings.user_id} by {current_user['username']}")
    
    return UserSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        device_id=settings.device_id,
        theme=settings.theme,
        language=settings.language,
        timezone=settings.timezone,
        notifications_enabled=settings.notifications_enabled,
        auto_monitoring_enabled=settings.auto_monitoring_enabled,
        monitoring_interval=settings.monitoring_interval,
        optimization_profile_id=settings.optimization_profile_id,
        auto_optimization=settings.auto_optimization,
        data_retention_days=settings.data_retention_days,
        created_at=settings.created_at,
        updated_at=settings.updated_at
    )

@router.get("/recommendations/{device_id}", response_model=List[OptimizationRecommendation])
async def get_optimization_recommendations(
    device_id: str,
    category: Optional[str] = Query(None, description="Filter by category: battery, performance, network"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get optimization recommendations for a specific device based on its current state.
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
    
    # Use the settings service to generate recommendations
    settings_service = SettingsService(adb_manager, db)
    api_recommendations = []
    
    try:
        # Get recommendations from the service
        if category:
            if category == "battery":
                service_recs = await settings_service.generate_battery_recommendations(device_id)
            elif category == "performance":
                service_recs = await settings_service.generate_performance_recommendations(device_id)
            elif category == "network":
                service_recs = await settings_service.generate_network_recommendations(device_id)
            else:
                service_recs = []
        else:
            # Get all recommendations
            all_recs = await settings_service.get_comprehensive_recommendations(device_id)
            service_recs = []
            for cat_recs in all_recs.values():
                service_recs.extend(cat_recs)
        
        # Convert service recommendations to API format
        for i, rec in enumerate(service_recs):
            # Map impact level to difficulty
            difficulty_map = {"high": "easy", "medium": "medium", "low": "advanced"}
            difficulty = difficulty_map.get(rec.impact, "medium")
            
            # Map estimated improvement to impact scale (1-10)
            impact_scale = min(10, max(1, int(rec.estimated_improvement / 10) + 1))
            
            api_recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                recommendation_type=rec.category,
                title=rec.title,
                description=rec.description,
                potential_improvement=f"Improve {rec.category} by approximately {rec.estimated_improvement:.1f}%",
                difficulty=difficulty,
                estimated_impact=impact_scale,
                recommended_profile=None,  # Could be mapped to actual profiles if needed
                action_required=rec.setting_command
            ))
    
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        # Fallback to basic recommendations if service fails
        api_recommendations = [OptimizationRecommendation(
            device_id=device_id,
            recommendation_type="general",
            title="General Device Optimization",
            description="Apply general optimization settings to improve device performance.",
            potential_improvement="Improve overall device performance",
            difficulty="medium",
            estimated_impact=5,
            action_required="Apply a general optimization profile"
        )]
    
    return api_recommendations

@router.post("/recommendations/apply", status_code=status.HTTP_200_OK)
async def apply_recommendation(
    device_id: str = Query(..., description="Target device ID"),
    recommendation_ids: List[str] = Query(..., description="List of recommendation IDs to apply"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Apply selected optimization recommendations.
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
    
    settings_service = SettingsService(adb_manager, db)
    
    try:
        results = await settings_service.apply_recommendations(device_id, recommendation_ids)
        
        # Count successful and failed recommendations
        success_count = sum(1 for success in results.values() if success)
        failed_count = len(results) - success_count
        
        return {
            "success": True,
            "message": f"Applied {success_count} recommendations. {failed_count} failed.",
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error applying recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply recommendations: {str(e)}"
        )

@router.post("/settings/backup", response_model=SettingsBackupResponse)
async def backup_settings(
    backup_request: SettingsBackupCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Create a backup of device settings.
    """
    device = db.query(Device).filter(Device.device_id == backup_request.device_id, Device.is_active == True).first()
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
    
    settings_service = SettingsService(adb_manager, db)
    
    try:
        backup = await settings_service.create_settings_backup(
            device_id=backup_request.device_id,
            backup_name=backup_request.backup_name
        )
        
        if not backup:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create settings backup"
            )
        
        # Count settings in each namespace
        settings_count = {
            "system": len(backup.settings.get("system", {})),
            "secure": len(backup.settings.get("secure", {})),
            "global": len(backup.settings.get("global", {}))
        }
        
        return SettingsBackupResponse(
            backup_id=backup.backup_id,
            device_id=backup.device_id,
            backup_name=backup.backup_name,
            created_at=backup.created_at,
            size=backup.size,
            checksum=backup.checksum,
            settings_count=settings_count
        )
    
    except Exception as e:
        logger.error(f"Error creating settings backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create settings backup: {str(e)}"
        )

@router.get("/settings/backups", response_model=List[SettingsBackupResponse])
async def list_settings_backups(
    device_id: Optional[str] = Query(None, description="Filter backups by device ID"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    List available settings backups.
    """
    settings_service = SettingsService(adb_manager, db)
    
    try:
        backups = settings_service.get_backup_list(device_id)
        
        return [SettingsBackupResponse(
            backup_id=backup.backup_id,
            device_id=backup.device_id,
            backup_name=backup.backup_name,
            created_at=backup.created_at,
            size=backup.size,
            checksum=backup.checksum,
            settings_count={
                "system": len(backup.settings.get("system", {})),
                "secure": len(backup.settings.get("secure", {})),
                "global": len(backup.settings.get("global", {}))
            }
        ) for backup in backups]
    
    except Exception as e:
        logger.error(f"Error listing settings backups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list settings backups: {str(e)}"
        )

@router.post("/settings/restore", status_code=status.HTTP_200_OK)
async def restore_settings(
    restore_request: SettingsRestoreRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Restore settings from a backup.
    """
    device = db.query(Device).filter(Device.device_id == restore_request.device_id, Device.is_active == True).first()
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
    
    settings_service = SettingsService(adb_manager, db)
    
    try:
        success = await settings_service.restore_settings_backup(
            device_id=restore_request.device_id,
            backup_id=restore_request.backup_id,
            namespace_filter=restore_request.namespaces
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore settings"
            )
        
        return {
            "success": True,
            "message": "Settings restored successfully"
        }
    
    except Exception as e:
        logger.error(f"Error restoring settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore settings: {str(e)}"
        )

@router.delete("/settings/backups/{backup_id}", status_code=status.HTTP_200_OK)
async def delete_settings_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Delete a settings backup.
    """
    settings_service = SettingsService(adb_manager, db)
    
    try:
        success = settings_service.delete_backup(backup_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backup not found or could not be deleted"
            )
        
        return {
            "success": True,
            "message": "Backup deleted successfully"
        }
    
    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete backup: {str(e)}"
        )

