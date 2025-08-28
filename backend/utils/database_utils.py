"""
Database utilities for AndroidZen Pro.
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .core.database import get_db, create_tables, drop_tables, engine, SessionLocal
from .models import (
    Device, DeviceConnectionHistory, Analytics, StorageTrend,
    OptimizationProfile, UserSettings, ProfileApplication,
    SecurityEvent, SecurityAlert, ThreatIntelligence, SeverityLevel
)
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database management utilities."""
    
    @staticmethod
    def initialize_database(create_sample_data: bool = False) -> bool:
        """
        Initialize the database with all tables and optionally create sample data.
        
        Args:
            create_sample_data: Whether to create sample data for testing
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Initializing database...")
            
            # Create all tables
            create_tables()
            logger.info("Database tables created successfully")
            
            if create_sample_data:
                DatabaseManager.create_sample_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    @staticmethod
    def reset_database() -> bool:
        """
        Drop and recreate all database tables.
        WARNING: This will delete all data!
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.warning("Resetting database - all data will be lost!")
            
            # Drop all tables
            drop_tables()
            logger.info("Database tables dropped")
            
            # Recreate all tables
            create_tables()
            logger.info("Database tables recreated")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            return False
    
    @staticmethod
    def create_sample_data() -> bool:
        """
        Create sample data for testing and demonstration.
        
        Returns:
            bool: True if successful, False otherwise
        """
        db = SessionLocal()
        try:
            logger.info("Creating sample data...")
            
            # Create sample optimization profiles
            profiles = [
                OptimizationProfile(
                    name="Battery Saver",
                    description="Maximize battery life with conservative settings",
                    profile_type="battery",
                    is_system=True,
                    cpu_governor="powersave",
                    brightness_level=50,
                    screen_timeout=30,
                    battery_saver_enabled=True,
                    animation_scale=0.5,
                    auto_cache_clear=True
                ),
                OptimizationProfile(
                    name="Performance Mode",
                    description="Maximum performance for demanding applications",
                    profile_type="performance",
                    is_system=True,
                    cpu_governor="performance",
                    brightness_level=200,
                    screen_timeout=600,
                    animation_scale=1.0,
                    force_gpu_rendering=True
                ),
                OptimizationProfile(
                    name="Balanced",
                    description="Balanced performance and battery life",
                    profile_type="balanced",
                    is_system=True,
                    is_default=True,
                    cpu_governor="ondemand",
                    brightness_level=128,
                    screen_timeout=120,
                    animation_scale=1.0
                )
            ]
            
            for profile in profiles:
                db.add(profile)
            
            # Create sample device
            sample_device = Device(
                device_id="emulator-5554",
                serial_number="emulator-5554",
                device_name="Android Emulator",
                manufacturer="Google",
                model="Android SDK built for x86",
                brand="Android",
                android_version="11",
                api_level=30,
                connection_type="usb",
                is_connected=True,
                ram_total=2048,
                storage_total=8192,
                screen_resolution="1080x1920",
                screen_density=420
            )
            db.add(sample_device)
            db.commit()
            
            # Create sample analytics data
            analytics_data = [
                Analytics(
                    device_id=sample_device.id,
                    metric_type="performance",
                    cpu_usage=45.5,
                    memory_usage=62.3,
                    memory_available=1200,
                    memory_total=2048,
                    battery_level=85,
                    battery_health="Good"
                ),
                Analytics(
                    device_id=sample_device.id,
                    metric_type="storage",
                    storage_used=3500,
                    storage_available=4692,
                    storage_total=8192,
                    storage_usage_percentage=42.7
                )
            ]
            
            for analytics in analytics_data:
                analytics.calculate_performance_score()
                db.add(analytics)
            
            # Create sample security event
            security_event = SecurityEvent(
                device_id=sample_device.id,
                event_type="app_scan",
                event_title="Potentially Suspicious App Detected",
                event_description="An app with excessive permissions was detected",
                severity=SeverityLevel.MEDIUM,
                app_package_name="com.example.suspicious",
                app_name="Suspicious App",
                detection_method="app_scan"
            )
            security_event.calculate_risk_score()
            db.add(security_event)
            
            # Create sample user settings
            user_settings = UserSettings(
                user_id="default_user",
                device_id=sample_device.id,
                theme="dark",
                notifications_enabled=True,
                auto_monitoring_enabled=True,
                monitoring_interval=300,
                optimization_profile_id=profiles[2].id  # Balanced profile
            )
            db.add(user_settings)
            
            db.commit()
            logger.info("Sample data created successfully")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error while creating sample data: {e}")
            db.rollback()
            return False
        except Exception as e:
            logger.error(f"Failed to create sample data: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_database_info() -> Dict[str, Any]:
        """
        Get information about the database and its tables.
        
        Returns:
            Dict containing database information
        """
        db = SessionLocal()
        try:
            info = {
                "database_url": os.getenv("DATABASE_URL", "sqlite:///./androidzen.db"),
                "tables": {},
                "total_records": 0
            }
            
            # Count records in each table
            table_models = [
                ("devices", Device),
                ("device_connection_history", DeviceConnectionHistory),
                ("analytics", Analytics),
                ("storage_trends", StorageTrend),
                ("optimization_profiles", OptimizationProfile),
                ("user_settings", UserSettings),
                ("profile_applications", ProfileApplication),
                ("security_events", SecurityEvent),
                ("security_alerts", SecurityAlert),
                ("threat_intelligence", ThreatIntelligence)
            ]
            
            for table_name, model in table_models:
                try:
                    count = db.query(model).count()
                    info["tables"][table_name] = count
                    info["total_records"] += count
                except Exception as e:
                    info["tables"][table_name] = f"Error: {e}"
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Perform a database health check.
        
        Returns:
            Dict containing health check results
        """
        try:
            db = SessionLocal()
            
            # Test basic connectivity
            start_time = datetime.now()
            db.execute("SELECT 1")
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            
            db.close()
            
            return {
                "status": "healthy",
                "query_time_ms": round(query_time, 2),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def cleanup_old_data(days_to_keep: int = 30) -> Dict[str, int]:
        """
        Clean up old data from the database.
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            Dict with counts of deleted records
        """
        db = SessionLocal()
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted_counts = {}
            
            # Clean up old analytics data
            analytics_deleted = db.query(Analytics).filter(
                Analytics.created_at < cutoff_date
            ).delete()
            deleted_counts["analytics"] = analytics_deleted
            
            # Clean up old connection history
            history_deleted = db.query(DeviceConnectionHistory).filter(
                DeviceConnectionHistory.timestamp < cutoff_date
            ).delete()
            deleted_counts["connection_history"] = history_deleted
            
            # Clean up resolved security events older than cutoff
            security_deleted = db.query(SecurityEvent).filter(
                SecurityEvent.resolved_at < cutoff_date,
                SecurityEvent.status == "resolved"
            ).delete()
            deleted_counts["security_events"] = security_deleted
            
            db.commit()
            logger.info(f"Cleaned up old data: {deleted_counts}")
            return deleted_counts
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()


def main():
    """Main function for running database utilities from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AndroidZen Pro Database Utilities")
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--reset", action="store_true", help="Reset database (WARNING: deletes all data)")
    parser.add_argument("--sample-data", action="store_true", help="Create sample data")
    parser.add_argument("--info", action="store_true", help="Show database information")
    parser.add_argument("--health", action="store_true", help="Perform health check")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Clean up data older than specified days")
    
    args = parser.parse_args()
    
    if args.init:
        success = DatabaseManager.initialize_database(create_sample_data=args.sample_data)
        print("Database initialization:", "SUCCESS" if success else "FAILED")
    
    elif args.reset:
        confirm = input("WARNING: This will delete all data! Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            success = DatabaseManager.reset_database()
            print("Database reset:", "SUCCESS" if success else "FAILED")
        else:
            print("Reset cancelled.")
    
    elif args.sample_data:
        success = DatabaseManager.create_sample_data()
        print("Sample data creation:", "SUCCESS" if success else "FAILED")
    
    elif args.info:
        info = DatabaseManager.get_database_info()
        print("Database Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    elif args.health:
        health = DatabaseManager.health_check()
        print("Database Health Check:")
        for key, value in health.items():
            print(f"  {key}: {value}")
    
    elif args.cleanup is not None:
        results = DatabaseManager.cleanup_old_data(args.cleanup)
        print("Cleanup Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

