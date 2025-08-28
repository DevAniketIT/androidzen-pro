"""
Example usage and demonstration of the Settings Service

This script shows how to use the comprehensive Settings Service for AndroidZen Pro.
"""

import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .core.adb_manager import AdbManager
from .services.settings_service import SettingsService, OptimizationType
from .core.database import Base


async def main():
    """Example usage of the Settings Service"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize database (using SQLite for example)
    engine = create_engine("sqlite:///./test.db", echo=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Initialize ADB Manager and Settings Service
    adb_manager = AdbManager()
    settings_service = SettingsService(adb_manager, db)
    
    # Example device ID (you would get this from connected devices)
    device_id = "test_device_001"
    
    try:
        logger.info("=== Settings Service Demonstration ===")
        
        # 1. Read system settings safely
        logger.info("\n1. Reading system settings...")
        settings = await settings_service.read_system_settings(device_id, namespace="system")
        logger.info(f"Found {len(settings)} system settings")
        
        for key, setting in list(settings.items())[:5]:  # Show first 5
            logger.info(f"  {setting.key}: {setting.value} ({setting.value_type}, safe: {setting.safe_to_modify})")
        
        # 2. Generate battery optimization recommendations
        logger.info("\n2. Generating battery optimization recommendations...")
        battery_recs = await settings_service.generate_battery_recommendations(device_id)
        
        for i, rec in enumerate(battery_recs[:3]):  # Show first 3
            logger.info(f"  Battery Recommendation {i+1}:")
            logger.info(f"    Title: {rec.title}")
            logger.info(f"    Impact: {rec.impact} ({rec.estimated_improvement}% improvement)")
            logger.info(f"    Current: {rec.current_value} -> Recommended: {rec.recommended_value}")
            logger.info(f"    Command: {rec.setting_command}")
        
        # 3. Generate performance recommendations
        logger.info("\n3. Generating performance recommendations...")
        perf_recs = await settings_service.generate_performance_recommendations(device_id)
        
        for i, rec in enumerate(perf_recs[:3]):
            logger.info(f"  Performance Recommendation {i+1}:")
            logger.info(f"    Title: {rec.title}")
            logger.info(f"    Impact: {rec.impact} ({rec.estimated_improvement}% improvement)")
        
        # 4. Generate network recommendations
        logger.info("\n4. Generating network recommendations...")
        network_recs = await settings_service.generate_network_recommendations(device_id)
        
        for i, rec in enumerate(network_recs[:3]):
            logger.info(f"  Network Recommendation {i+1}:")
            logger.info(f"    Title: {rec.title}")
            logger.info(f"    Safety Level: {rec.safety_level}")
        
        # 5. Get all recommendations together
        logger.info("\n5. Getting comprehensive recommendations...")
        all_recs = await settings_service.get_comprehensive_recommendations(device_id)
        
        total_recs = sum(len(recs) for recs in all_recs.values())
        logger.info(f"Total recommendations: {total_recs}")
        
        for category, recs in all_recs.items():
            logger.info(f"  {category.title()}: {len(recs)} recommendations")
        
        # 6. Create a settings backup
        logger.info("\n6. Creating settings backup...")
        backup = await settings_service.create_settings_backup(device_id, "Demo Backup")
        
        if backup:
            logger.info(f"Backup created: {backup.backup_id}")
            logger.info(f"  Size: {backup.size} bytes")
            logger.info(f"  Settings: {len(backup.settings['system'])} system, {len(backup.settings['secure'])} secure, {len(backup.settings['global'])} global")
        
        # 7. List available backups
        logger.info("\n7. Listing available backups...")
        backups = settings_service.get_backup_list(device_id)
        
        for backup in backups:
            logger.info(f"  Backup: {backup.backup_name} ({backup.backup_id})")
            logger.info(f"    Created: {backup.created_at}")
            logger.info(f"    Size: {backup.size} bytes")
        
        # 8. Get optimization profiles
        logger.info("\n8. Getting optimization profiles...")
        profiles = settings_service.get_optimization_profiles()
        
        for profile in profiles:
            logger.info(f"  Profile: {profile.name} ({profile.profile_type})")
            logger.info(f"    System: {profile.is_system}, Active: {profile.is_active}")
            logger.info(f"    Description: {profile.description}")
        
        # 9. Create a custom profile
        logger.info("\n9. Creating custom optimization profile...")
        custom_profile = settings_service.create_custom_profile(
            name="Demo Custom Profile",
            description="A custom profile for demonstration",
            brightness_level=100,
            animation_scale=0.8,
            screen_timeout=45,
            advanced_settings={
                "location_mode": "battery_saving",
                "sync_frequency": "manual"
            }
        )
        
        if custom_profile:
            logger.info(f"Custom profile created: {custom_profile.name} (ID: {custom_profile.id})")
        
        # 10. Apply an optimization profile
        logger.info("\n10. Applying optimization profile...")
        battery_profile = next((p for p in profiles if p.profile_type == "battery_saver"), None)
        
        if battery_profile:
            success = await settings_service.apply_optimization_profile(
                device_id, battery_profile.id, applied_by="demo_script"
            )
            logger.info(f"Profile application {'successful' if success else 'failed'}")
        
        # 11. Apply specific recommendations
        logger.info("\n11. Applying specific recommendations...")
        if battery_recs:
            # Apply first battery recommendation
            rec_id = "battery_0"  # First battery recommendation
            results = await settings_service.apply_recommendations(device_id, [rec_id])
            
            for rec_id, success in results.items():
                logger.info(f"  Recommendation {rec_id}: {'Applied' if success else 'Failed'}")
        
        # 12. Get settings summary
        logger.info("\n12. Getting settings summary...")
        summary = settings_service.get_settings_summary(device_id)
        
        logger.info(f"Settings Summary for {device_id}:")
        logger.info(f"  Backup count: {summary.get('backup_count', 0)}")
        logger.info(f"  Last updated: {summary.get('last_updated', 'Unknown')}")
        
        # 13. Cleanup old backups (demo with 0 days to clean everything)
        logger.info("\n13. Cleaning up old backups...")
        deleted_count = settings_service.cleanup_old_backups(days_to_keep=0)  # Clean all for demo
        logger.info(f"Cleaned up {deleted_count} old backups")
        
        logger.info("\n=== Settings Service Demonstration Complete ===")
        
    except Exception as e:
        logger.error(f"Error during demonstration: {e}")
    finally:
        # Cleanup
        adb_manager.shutdown()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

