"""
Settings Enhancement Hub for AndroidZen Pro

This module provides comprehensive settings management including:
- Safe system settings reader via ADB
- Battery optimization recommendation engine
- Performance tuning suggestions (animation scales, background processes)
- Network configuration optimizer
- Settings backup and restore functionality
- User-friendly optimization profiles (Battery Saver, Performance, Balanced)
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from sqlalchemy.orm import Session
from .core.adb_manager import AdbManager
from .models.settings import OptimizationProfile, UserSettings, ProfileApplication
from .models.device import Device


class SettingType(Enum):
    """Types of Android settings"""
    SYSTEM = "system"
    SECURE = "secure" 
    GLOBAL = "global"


class OptimizationType(Enum):
    """Types of optimization profiles"""
    BATTERY_SAVER = "battery_saver"
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    GAMING = "gaming"
    CUSTOM = "custom"


@dataclass
class SystemSetting:
    """Android system setting container"""
    namespace: str  # system, secure, or global
    key: str
    value: str
    value_type: str  # string, int, float, boolean
    description: Optional[str] = None
    safe_to_modify: bool = True
    requires_root: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation container"""
    category: str  # battery, performance, network, etc.
    title: str
    description: str
    impact: str  # low, medium, high
    current_value: Any
    recommended_value: Any
    setting_command: str
    safety_level: str  # safe, caution, risky
    estimated_improvement: float  # percentage
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SettingsBackup:
    """Settings backup container"""
    backup_id: str
    device_id: str
    backup_name: str
    created_at: datetime
    settings: Dict[str, Dict[str, str]]  # namespace -> {key: value}
    size: int  # backup size in bytes
    checksum: str
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


class SettingsService:
    """Comprehensive Settings Management Service"""
    
    def __init__(self, adb_manager: AdbManager, db_session: Session, backup_dir: str = "data/backups"):
        self.logger = logging.getLogger(__name__)
        self.adb_manager = adb_manager
        self.db = db_session
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for settings to reduce ADB calls
        self.settings_cache: Dict[str, Dict[str, SystemSetting]] = {}
        self.cache_expires: Dict[str, datetime] = {}
        
        # Predefined optimization profiles
        self._initialize_default_profiles()
        
        # Safe settings whitelist (settings safe to modify without root)
        self.safe_settings = {
            "system": {
                "window_animation_scale",
                "transition_animation_scale", 
                "animator_duration_scale",
                "screen_brightness",
                "screen_off_timeout",
                "accelerometer_rotation",
                "haptic_feedback_enabled",
                "sound_effects_enabled",
                "lockscreen_sounds_enabled"
            },
            "secure": {
                "android_id",
                "bluetooth_name",
                "default_input_method",
                "enabled_input_methods",
                "location_providers_allowed",
                "install_non_market_apps"
            },
            "global": {
                "airplane_mode_on",
                "auto_time",
                "auto_time_zone",
                "data_roaming",
                "development_settings_enabled",
                "stay_on_while_plugged_in",
                "usb_mass_storage_enabled",
                "wifi_sleep_policy"
            }
        }
    
    def _initialize_default_profiles(self):
        """Initialize default optimization profiles if they don't exist"""
        try:
            # Check if default profiles exist
            existing_profiles = self.db.query(OptimizationProfile).filter(
                OptimizationProfile.is_system == True
            ).all()
            
            if existing_profiles:
                return  # Default profiles already exist
            
            # Create default profiles
            profiles = [
                {
                    "name": "Battery Saver",
                    "description": "Maximizes battery life by reducing performance and limiting background activity",
                    "profile_type": "battery_saver",
                    "is_system": True,
                    "is_default": True,
                    "cpu_governor": "powersave",
                    "brightness_level": 50,
                    "screen_timeout": 30,
                    "adaptive_brightness": True,
                    "wifi_optimization": True,
                    "background_data_restriction": True,
                    "battery_saver_enabled": True,
                    "doze_mode_enabled": True,
                    "app_standby_enabled": True,
                    "background_app_limit": 3,
                    "animation_scale": 0.5,
                    "force_gpu_rendering": False,
                    "auto_cache_clear": True,
                    "cache_clear_interval": 6,
                    "advanced_settings": {
                        "location_mode": "battery_saving",
                        "sync_frequency": "manual",
                        "notification_led": False,
                        "vibration_intensity": "low"
                    }
                },
                {
                    "name": "Performance",
                    "description": "Optimizes for maximum performance and responsiveness",
                    "profile_type": "performance",
                    "is_system": True,
                    "cpu_governor": "performance",
                    "brightness_level": 200,
                    "screen_timeout": 120,
                    "adaptive_brightness": False,
                    "wifi_optimization": False,
                    "background_data_restriction": False,
                    "battery_saver_enabled": False,
                    "doze_mode_enabled": False,
                    "app_standby_enabled": False,
                    "animation_scale": 1.0,
                    "force_gpu_rendering": True,
                    "hardware_acceleration": True,
                    "auto_cache_clear": False,
                    "advanced_settings": {
                        "location_mode": "high_accuracy",
                        "sync_frequency": "real_time",
                        "developer_options": True,
                        "force_msaa": True,
                        "force_hardware_ui": True
                    }
                },
                {
                    "name": "Balanced",
                    "description": "Balances performance and battery life for everyday use",
                    "profile_type": "balanced",
                    "is_system": True,
                    "cpu_governor": "ondemand",
                    "brightness_level": 120,
                    "screen_timeout": 60,
                    "adaptive_brightness": True,
                    "wifi_optimization": True,
                    "background_data_restriction": False,
                    "battery_saver_enabled": False,
                    "doze_mode_enabled": True,
                    "app_standby_enabled": True,
                    "background_app_limit": 10,
                    "animation_scale": 1.0,
                    "force_gpu_rendering": False,
                    "hardware_acceleration": True,
                    "auto_cache_clear": False,
                    "advanced_settings": {
                        "location_mode": "high_accuracy",
                        "sync_frequency": "auto",
                        "notification_led": True,
                        "vibration_intensity": "medium"
                    }
                }
            ]
            
            for profile_data in profiles:
                profile = OptimizationProfile(**profile_data)
                self.db.add(profile)
            
            self.db.commit()
            self.logger.info("Default optimization profiles created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize default profiles: {e}")
            self.db.rollback()
    
    async def read_system_settings(self, device_id: str, 
                                  namespace: Optional[str] = None,
                                  keys: Optional[List[str]] = None,
                                  use_cache: bool = True) -> Dict[str, SystemSetting]:
        """
        Safely read Android system settings via ADB
        
        Args:
            device_id: Target device ID
            namespace: Settings namespace (system, secure, global). If None, reads all
            keys: Specific setting keys to read. If None, reads all available
            use_cache: Whether to use cached settings (if available)
            
        Returns:
            Dictionary of setting key -> SystemSetting
        """
        cache_key = f"{device_id}_{namespace or 'all'}"
        
        # Check cache first
        if (use_cache and cache_key in self.settings_cache and
            cache_key in self.cache_expires and
            self.cache_expires[cache_key] > datetime.now()):
            
            cached_settings = self.settings_cache[cache_key]
            if keys:
                return {k: v for k, v in cached_settings.items() if k in keys}
            return cached_settings
        
        try:
            settings = {}
            namespaces = [namespace] if namespace else ["system", "secure", "global"]
            
            for ns in namespaces:
                # Read all settings from namespace
                command = f"settings list {ns}"
                result = await self.adb_manager.execute_command(device_id, command, timeout=30)
                
                if not result.success:
                    self.logger.warning(f"Failed to read {ns} settings: {result.error}")
                    continue
                
                # Parse settings output
                for line in result.output.strip().split('\n'):
                    if '=' in line and line.strip():
                        try:
                            key, value = line.split('=', 1)
                            
                            # Skip if specific keys requested and this key not in list
                            if keys and key not in keys:
                                continue
                            
                            # Determine value type and convert
                            value_type = self._determine_value_type(value)
                            
                            # Check if setting is safe to modify
                            safe_to_modify = key in self.safe_settings.get(ns, set())
                            
                            setting = SystemSetting(
                                namespace=ns,
                                key=key,
                                value=value,
                                value_type=value_type,
                                safe_to_modify=safe_to_modify,
                                requires_root=not safe_to_modify
                            )
                            
                            settings[key] = setting
                            
                        except ValueError:
                            continue  # Skip malformed lines
            
            # Cache the results
            self.settings_cache[cache_key] = settings
            self.cache_expires[cache_key] = datetime.now() + timedelta(minutes=5)
            
            return settings
            
        except Exception as e:
            self.logger.error(f"Error reading system settings for device {device_id}: {e}")
            return {}
    
    def _determine_value_type(self, value: str) -> str:
        """Determine the type of a setting value"""
        if value.lower() in ('true', 'false'):
            return 'boolean'
        
        try:
            int(value)
            return 'int'
        except ValueError:
            pass
        
        try:
            float(value)
            return 'float'
        except ValueError:
            pass
        
        return 'string'
    
    async def get_setting_value(self, device_id: str, namespace: str, key: str) -> Optional[str]:
        """Get a specific setting value"""
        command = f"settings get {namespace} {key}"
        result = await self.adb_manager.execute_command(device_id, command, timeout=10)
        
        if result.success and result.output.strip() != "null":
            return result.output.strip()
        return None
    
    async def set_setting_value(self, device_id: str, namespace: str, key: str, 
                               value: str, verify_safety: bool = True) -> bool:
        """
        Safely set a system setting value
        
        Args:
            device_id: Target device ID
            namespace: Settings namespace (system, secure, global)
            key: Setting key
            value: Setting value
            verify_safety: Whether to verify setting is safe to modify
            
        Returns:
            True if successful
        """
        try:
            # Verify setting is safe to modify if requested
            if verify_safety and key not in self.safe_settings.get(namespace, set()):
                self.logger.warning(f"Setting {namespace}.{key} may not be safe to modify")
                return False
            
            # Set the value
            command = f"settings put {namespace} {key} {value}"
            result = await self.adb_manager.execute_command(device_id, command, timeout=10)
            
            if result.success:
                # Clear cache for this device
                cache_keys_to_remove = [k for k in self.settings_cache.keys() if k.startswith(device_id)]
                for cache_key in cache_keys_to_remove:
                    self.settings_cache.pop(cache_key, None)
                    self.cache_expires.pop(cache_key, None)
                
                self.logger.info(f"Successfully set {namespace}.{key} = {value} on device {device_id}")
                return True
            else:
                self.logger.error(f"Failed to set setting {namespace}.{key}: {result.error}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting {namespace}.{key} on device {device_id}: {e}")
            return False
    
    async def generate_battery_recommendations(self, device_id: str) -> List[OptimizationRecommendation]:
        """Generate battery optimization recommendations"""
        recommendations = []
        
        try:
            # Get current settings
            settings = await self.read_system_settings(device_id)
            
            # Screen brightness recommendation
            brightness_setting = settings.get("screen_brightness")
            if brightness_setting and int(brightness_setting.value) > 150:
                recommendations.append(OptimizationRecommendation(
                    category="battery",
                    title="Reduce Screen Brightness",
                    description="Lower screen brightness to conserve battery",
                    impact="high",
                    current_value=brightness_setting.value,
                    recommended_value="120",
                    setting_command=f"settings put system screen_brightness 120",
                    safety_level="safe",
                    estimated_improvement=15.0
                ))
            
            # Animation scale recommendations
            animation_settings = [
                ("window_animation_scale", "Window Animation"),
                ("transition_animation_scale", "Transition Animation"), 
                ("animator_duration_scale", "Animator Duration")
            ]
            
            for setting_key, display_name in animation_settings:
                setting = settings.get(setting_key)
                if setting and float(setting.value) > 0.5:
                    recommendations.append(OptimizationRecommendation(
                        category="battery",
                        title=f"Reduce {display_name} Scale",
                        description=f"Reduce {display_name.lower()} scale to improve battery life",
                        impact="medium",
                        current_value=setting.value,
                        recommended_value="0.5",
                        setting_command=f"settings put global {setting_key} 0.5",
                        safety_level="safe",
                        estimated_improvement=5.0
                    ))
            
            # Screen timeout recommendation
            timeout_setting = settings.get("screen_off_timeout")
            if timeout_setting and int(timeout_setting.value) > 60000:  # More than 1 minute
                recommendations.append(OptimizationRecommendation(
                    category="battery",
                    title="Reduce Screen Timeout",
                    description="Shorter screen timeout saves battery",
                    impact="medium",
                    current_value=f"{int(timeout_setting.value) // 1000}s",
                    recommended_value="30s",
                    setting_command="settings put system screen_off_timeout 30000",
                    safety_level="safe",
                    estimated_improvement=8.0
                ))
            
            # Get battery stats for more recommendations
            battery_stats = await self._get_battery_stats(device_id)
            if battery_stats:
                # Add app-specific recommendations based on battery usage
                heavy_apps = self._identify_battery_heavy_apps(battery_stats)
                for app in heavy_apps[:3]:  # Top 3 battery consumers
                    recommendations.append(OptimizationRecommendation(
                        category="battery",
                        title=f"Optimize {app['name']}",
                        description=f"App is using {app['battery_percentage']:.1f}% of battery",
                        impact="high",
                        current_value="Running",
                        recommended_value="Optimized",
                        setting_command=f"cmd appops set {app['package']} RUN_IN_BACKGROUND ignore",
                        safety_level="caution",
                        estimated_improvement=app['battery_percentage'] * 0.3
                    ))
            
        except Exception as e:
            self.logger.error(f"Error generating battery recommendations: {e}")
        
        return recommendations
    
    async def generate_performance_recommendations(self, device_id: str) -> List[OptimizationRecommendation]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        try:
            settings = await self.read_system_settings(device_id)
            
            # Animation scale recommendations for performance
            animation_settings = [
                ("window_animation_scale", "Window Animation"),
                ("transition_animation_scale", "Transition Animation"),
                ("animator_duration_scale", "Animator Duration")
            ]
            
            for setting_key, display_name in animation_settings:
                setting = settings.get(setting_key)
                if setting and float(setting.value) > 1.0:
                    recommendations.append(OptimizationRecommendation(
                        category="performance",
                        title=f"Optimize {display_name} Scale",
                        description=f"Set optimal {display_name.lower()} scale for performance",
                        impact="medium",
                        current_value=setting.value,
                        recommended_value="1.0",
                        setting_command=f"settings put global {setting_key} 1.0",
                        safety_level="safe",
                        estimated_improvement=10.0
                    ))
            
            # Force GPU rendering for better performance
            gpu_setting = await self.get_setting_value(device_id, "global", "force_hw_ui")
            if gpu_setting != "1":
                recommendations.append(OptimizationRecommendation(
                    category="performance",
                    title="Enable Hardware UI Rendering",
                    description="Force hardware acceleration for UI rendering",
                    impact="high",
                    current_value="Disabled",
                    recommended_value="Enabled", 
                    setting_command="settings put global force_hw_ui 1",
                    safety_level="safe",
                    estimated_improvement=20.0
                ))
            
            # Background process limit
            background_limit = await self._get_background_process_limit(device_id)
            if background_limit > 4:
                recommendations.append(OptimizationRecommendation(
                    category="performance",
                    title="Limit Background Processes",
                    description="Reduce background processes to improve performance",
                    impact="high",
                    current_value=f"{background_limit} processes",
                    recommended_value="4 processes",
                    setting_command="cmd activity set-bg-limit 4",
                    safety_level="caution",
                    estimated_improvement=15.0
                ))
            
        except Exception as e:
            self.logger.error(f"Error generating performance recommendations: {e}")
        
        return recommendations
    
    async def generate_network_recommendations(self, device_id: str) -> List[OptimizationRecommendation]:
        """Generate network configuration optimization recommendations"""
        recommendations = []
        
        try:
            # WiFi sleep policy
            wifi_sleep = await self.get_setting_value(device_id, "global", "wifi_sleep_policy")
            if wifi_sleep != "2":  # 2 = Never sleep
                recommendations.append(OptimizationRecommendation(
                    category="network",
                    title="Optimize WiFi Sleep Policy",
                    description="Keep WiFi on during sleep for better connectivity",
                    impact="medium",
                    current_value="Sleep when screen off",
                    recommended_value="Never sleep",
                    setting_command="settings put global wifi_sleep_policy 2",
                    safety_level="safe",
                    estimated_improvement=10.0
                ))
            
            # Data roaming (recommend disable for cost saving)
            data_roaming = await self.get_setting_value(device_id, "global", "data_roaming")
            if data_roaming == "1":
                recommendations.append(OptimizationRecommendation(
                    category="network",
                    title="Disable Data Roaming",
                    description="Disable data roaming to avoid unexpected charges",
                    impact="low",
                    current_value="Enabled",
                    recommended_value="Disabled",
                    setting_command="settings put global data_roaming 0",
                    safety_level="safe",
                    estimated_improvement=0.0  # Cost saving, not performance
                ))
            
            # Network location (for better location accuracy)
            location_providers = await self.get_setting_value(device_id, "secure", "location_providers_allowed")
            if location_providers and "network" not in location_providers:
                recommendations.append(OptimizationRecommendation(
                    category="network",
                    title="Enable Network Location",
                    description="Enable network-based location for better accuracy",
                    impact="low",
                    current_value="GPS only",
                    recommended_value="GPS + Network",
                    setting_command="settings put secure location_providers_allowed +network",
                    safety_level="safe",
                    estimated_improvement=5.0
                ))
            
        except Exception as e:
            self.logger.error(f"Error generating network recommendations: {e}")
        
        return recommendations
    
    async def _get_battery_stats(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get battery statistics from device"""
        try:
            command = "dumpsys batterystats --charged"
            result = await self.adb_manager.execute_command(device_id, command, timeout=30)
            
            if result.success:
                # Parse battery stats (simplified parsing)
                stats = {"apps": []}
                lines = result.output.split('\n')
                
                for line in lines:
                    if "%" in line and "uid" in line.lower():
                        # Extract app battery usage info
                        # This is a simplified parser - real implementation would be more robust
                        try:
                            parts = line.strip().split()
                            if len(parts) > 2:
                                percentage = float(parts[0].replace('%', ''))
                                if percentage > 1.0:  # Only apps using > 1%
                                    stats["apps"].append({
                                        "name": parts[-1],
                                        "package": parts[-1],  # Simplified
                                        "battery_percentage": percentage
                                    })
                        except:
                            continue
                
                return stats
            
        except Exception as e:
            self.logger.debug(f"Could not get battery stats: {e}")
        
        return None
    
    def _identify_battery_heavy_apps(self, battery_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify apps that are heavy battery consumers"""
        apps = battery_stats.get("apps", [])
        # Sort by battery percentage and return top consumers
        return sorted(apps, key=lambda x: x["battery_percentage"], reverse=True)
    
    async def _get_background_process_limit(self, device_id: str) -> int:
        """Get current background process limit"""
        try:
            command = "cmd activity get-bg-limit"
            result = await self.adb_manager.execute_command(device_id, command, timeout=10)
            
            if result.success and result.output.strip().isdigit():
                return int(result.output.strip())
        except:
            pass
        
        return 10  # Default assumption
    
    async def create_settings_backup(self, device_id: str, backup_name: str) -> Optional[SettingsBackup]:
        """Create a complete backup of device settings"""
        try:
            backup_id = f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_data = {"system": {}, "secure": {}, "global": {}}
            
            # Read all settings from all namespaces
            for namespace in ["system", "secure", "global"]:
                settings = await self.read_system_settings(device_id, namespace, use_cache=False)
                backup_data[namespace] = {k: v.value for k, v in settings.items()}
            
            # Create backup file
            backup_file = self.backup_dir / f"{backup_id}.json"
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Calculate file size and checksum
            file_size = backup_file.stat().st_size
            checksum = self._calculate_checksum(backup_file)
            
            backup = SettingsBackup(
                backup_id=backup_id,
                device_id=device_id,
                backup_name=backup_name,
                created_at=datetime.now(),
                settings=backup_data,
                size=file_size,
                checksum=checksum
            )
            
            # Save backup metadata to JSON file
            metadata_file = self.backup_dir / f"{backup_id}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(backup.to_dict(), f, indent=2)
            
            self.logger.info(f"Settings backup created: {backup_id}")
            return backup
            
        except Exception as e:
            self.logger.error(f"Failed to create settings backup: {e}")
            return None
    
    async def restore_settings_backup(self, device_id: str, backup_id: str, 
                                    namespace_filter: Optional[List[str]] = None) -> bool:
        """Restore settings from backup"""
        try:
            # Load backup data
            backup_file = self.backup_dir / f"{backup_id}.json"
            if not backup_file.exists():
                self.logger.error(f"Backup file not found: {backup_id}")
                return False
            
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            namespaces = namespace_filter or ["system", "secure", "global"]
            success_count = 0
            total_count = 0
            
            for namespace in namespaces:
                if namespace not in backup_data:
                    continue
                
                settings = backup_data[namespace]
                for key, value in settings.items():
                    total_count += 1
                    try:
                        # Only restore safe settings
                        if key in self.safe_settings.get(namespace, set()):
                            success = await self.set_setting_value(
                                device_id, namespace, key, str(value), verify_safety=False
                            )
                            if success:
                                success_count += 1
                            
                            # Small delay to avoid overwhelming the device
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        self.logger.debug(f"Failed to restore {namespace}.{key}: {e}")
            
            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            self.logger.info(f"Settings restore completed: {success_count}/{total_count} settings restored ({success_rate:.1f}%)")
            
            return success_rate > 50  # Consider successful if > 50% restored
            
        except Exception as e:
            self.logger.error(f"Failed to restore settings backup: {e}")
            return False
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        import hashlib
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_backup_list(self, device_id: Optional[str] = None) -> List[SettingsBackup]:
        """Get list of available backups"""
        backups = []
        
        try:
            for metadata_file in self.backup_dir.glob("*_metadata.json"):
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                
                # Filter by device if specified
                if device_id and data.get("device_id") != device_id:
                    continue
                
                backup = SettingsBackup(
                    backup_id=data["backup_id"],
                    device_id=data["device_id"],
                    backup_name=data["backup_name"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    settings=data["settings"],
                    size=data["size"],
                    checksum=data["checksum"]
                )
                backups.append(backup)
                
        except Exception as e:
            self.logger.error(f"Error loading backup list: {e}")
        
        return sorted(backups, key=lambda x: x.created_at, reverse=True)
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a settings backup"""
        try:
            backup_file = self.backup_dir / f"{backup_id}.json"
            metadata_file = self.backup_dir / f"{backup_id}_metadata.json"
            
            success = True
            if backup_file.exists():
                backup_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            self.logger.info(f"Backup deleted: {backup_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    async def apply_optimization_profile(self, device_id: str, profile_id: int,
                                       applied_by: str = "system") -> bool:
        """Apply an optimization profile to a device"""
        try:
            # Get the optimization profile
            profile = self.db.query(OptimizationProfile).filter(
                OptimizationProfile.id == profile_id
            ).first()
            
            if not profile:
                self.logger.error(f"Optimization profile {profile_id} not found")
                return False
            
            # Get device info
            device = self.db.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                self.logger.error(f"Device {device_id} not found in database")
                return False
            
            # Record application attempt
            application = ProfileApplication(
                profile_id=profile_id,
                device_id=device.id,
                applied_by=applied_by,
                application_method="manual"
            )
            
            settings_changed = {}
            success_count = 0
            total_settings = 0
            
            # Apply profile settings
            profile_settings = [
                ("system", "screen_brightness", profile.brightness_level),
                ("system", "screen_off_timeout", profile.screen_timeout * 1000 if profile.screen_timeout else None),
                ("global", "window_animation_scale", profile.animation_scale),
                ("global", "transition_animation_scale", profile.animation_scale), 
                ("global", "animator_duration_scale", profile.animation_scale),
            ]
            
            for namespace, key, value in profile_settings:
                if value is not None:
                    total_settings += 1
                    try:
                        current_value = await self.get_setting_value(device_id, namespace, key)
                        success = await self.set_setting_value(
                            device_id, namespace, key, str(value)
                        )
                        
                        if success:
                            success_count += 1
                            settings_changed[f"{namespace}.{key}"] = {
                                "old_value": current_value,
                                "new_value": str(value)
                            }
                        
                        await asyncio.sleep(0.1)  # Small delay between settings
                        
                    except Exception as e:
                        self.logger.debug(f"Failed to apply setting {namespace}.{key}: {e}")
            
            # Apply advanced settings if any
            if profile.advanced_settings:
                for key, value in profile.advanced_settings.items():
                    total_settings += 1
                    try:
                        # Map advanced settings to actual Android settings
                        namespace, setting_key = self._map_advanced_setting(key)
                        if namespace and setting_key:
                            success = await self.set_setting_value(
                                device_id, namespace, setting_key, str(value)
                            )
                            if success:
                                success_count += 1
                                settings_changed[f"{namespace}.{setting_key}"] = {
                                    "old_value": None,
                                    "new_value": str(value)
                                }
                    except Exception as e:
                        self.logger.debug(f"Failed to apply advanced setting {key}: {e}")
            
            # Update application record
            application.success = success_count > 0
            application.settings_changed = settings_changed
            
            if success_count == 0:
                application.error_message = "No settings could be applied"
            
            self.db.add(application)
            
            # Update profile statistics
            if application.success:
                profile.apply_profile()
            
            self.db.commit()
            
            success_rate = (success_count / total_settings) * 100 if total_settings > 0 else 0
            self.logger.info(f"Profile '{profile.name}' applied to device {device_id}: {success_count}/{total_settings} settings ({success_rate:.1f}%)")
            
            return application.success
            
        except Exception as e:
            self.logger.error(f"Failed to apply optimization profile: {e}")
            self.db.rollback()
            return False
    
    def _map_advanced_setting(self, key: str) -> Tuple[Optional[str], Optional[str]]:
        """Map advanced setting key to Android namespace and setting key"""
        mapping = {
            "location_mode": ("secure", "location_mode"),
            "sync_frequency": ("system", "sync_settings"),
            "notification_led": ("system", "notification_light_pulse"),
            "vibration_intensity": ("system", "haptic_feedback_enabled"),
            "developer_options": ("global", "development_settings_enabled"),
            "force_msaa": ("global", "debug.egl.force_msaa"),
            "force_hardware_ui": ("global", "force_hw_ui")
        }
        
        return mapping.get(key, (None, None))
    
    def get_optimization_profiles(self, profile_type: Optional[str] = None,
                                include_custom: bool = True) -> List[OptimizationProfile]:
        """Get available optimization profiles"""
        query = self.db.query(OptimizationProfile)
        
        if profile_type:
            query = query.filter(OptimizationProfile.profile_type == profile_type)
        
        if not include_custom:
            query = query.filter(OptimizationProfile.is_system == True)
        
        return query.order_by(OptimizationProfile.is_system.desc(), 
                            OptimizationProfile.name).all()
    
    def create_custom_profile(self, name: str, description: str, base_profile_id: Optional[int] = None,
                            **settings) -> Optional[OptimizationProfile]:
        """Create a custom optimization profile"""
        try:
            profile_data = {
                "name": name,
                "description": description,
                "profile_type": "custom",
                "is_system": False,
                "is_default": False
            }
            
            # Copy settings from base profile if provided
            if base_profile_id:
                base_profile = self.db.query(OptimizationProfile).filter(
                    OptimizationProfile.id == base_profile_id
                ).first()
                
                if base_profile:
                    # Copy relevant settings
                    for attr in ['cpu_governor', 'brightness_level', 'screen_timeout',
                               'animation_scale', 'battery_saver_enabled', 'advanced_settings']:
                        if hasattr(base_profile, attr):
                            profile_data[attr] = getattr(base_profile, attr)
            
            # Override with provided settings
            profile_data.update(settings)
            
            profile = OptimizationProfile(**profile_data)
            self.db.add(profile)
            self.db.commit()
            
            self.logger.info(f"Custom optimization profile created: {name}")
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to create custom profile: {e}")
            self.db.rollback()
            return None
    
    def delete_optimization_profile(self, profile_id: int) -> bool:
        """Delete an optimization profile (only custom profiles)"""
        try:
            profile = self.db.query(OptimizationProfile).filter(
                OptimizationProfile.id == profile_id,
                OptimizationProfile.is_system == False  # Only allow deletion of custom profiles
            ).first()
            
            if not profile:
                self.logger.error(f"Profile {profile_id} not found or is a system profile")
                return False
            
            self.db.delete(profile)
            self.db.commit()
            
            self.logger.info(f"Custom profile deleted: {profile.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete profile {profile_id}: {e}")
            self.db.rollback()
            return False
    
    async def get_comprehensive_recommendations(self, device_id: str) -> Dict[str, List[OptimizationRecommendation]]:
        """Get comprehensive optimization recommendations for all categories"""
        recommendations = {
            "battery": await self.generate_battery_recommendations(device_id),
            "performance": await self.generate_performance_recommendations(device_id),
            "network": await self.generate_network_recommendations(device_id)
        }
        
        # Sort recommendations by impact and estimated improvement
        for category in recommendations:
            recommendations[category].sort(
                key=lambda x: (
                    {"high": 3, "medium": 2, "low": 1}[x.impact],
                    x.estimated_improvement
                ),
                reverse=True
            )
        
        return recommendations
    
    async def apply_recommendations(self, device_id: str, 
                                  recommendation_ids: List[str]) -> Dict[str, bool]:
        """Apply selected optimization recommendations"""
        results = {}
        
        try:
            # Get all recommendations
            all_recommendations = await self.get_comprehensive_recommendations(device_id)
            
            # Flatten recommendations with unique IDs
            recommendation_map = {}
            for category, recs in all_recommendations.items():
                for i, rec in enumerate(recs):
                    rec_id = f"{category}_{i}"
                    recommendation_map[rec_id] = rec
            
            # Apply selected recommendations
            for rec_id in recommendation_ids:
                if rec_id in recommendation_map:
                    recommendation = recommendation_map[rec_id]
                    try:
                        # Execute the setting command
                        result = await self.adb_manager.execute_command(
                            device_id, 
                            recommendation.setting_command,
                            timeout=15
                        )
                        results[rec_id] = result.success
                        
                        if result.success:
                            self.logger.info(f"Applied recommendation: {recommendation.title}")
                        else:
                            self.logger.warning(f"Failed to apply recommendation {recommendation.title}: {result.error}")
                            
                    except Exception as e:
                        self.logger.error(f"Error applying recommendation {rec_id}: {e}")
                        results[rec_id] = False
                else:
                    self.logger.warning(f"Recommendation {rec_id} not found")
                    results[rec_id] = False
        
        except Exception as e:
            self.logger.error(f"Error applying recommendations: {e}")
        
        return results
    
    def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
        """Clean up old backup files"""
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            backups = self.get_backup_list()
            for backup in backups:
                if backup.created_at < cutoff_date:
                    if self.delete_backup(backup.backup_id):
                        deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} old backups")
            
        except Exception as e:
            self.logger.error(f"Error during backup cleanup: {e}")
        
        return deleted_count
    
    def get_settings_summary(self, device_id: str) -> Dict[str, Any]:
        """Get a summary of current device settings and optimization status"""
        try:
            # This would be populated with actual data in a real implementation
            summary = {
                "device_id": device_id,
                "last_updated": datetime.now().isoformat(),
                "active_profile": None,
                "settings_count": {
                    "system": 0,
                    "secure": 0, 
                    "global": 0
                },
                "optimization_score": 0,
                "recommendations_count": 0,
                "backup_count": len([b for b in self.get_backup_list() if b.device_id == device_id])
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting settings summary: {e}")
            return {}

