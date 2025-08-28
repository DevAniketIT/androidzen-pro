# AndroidZen Pro Database Schema

This document describes the database schema for AndroidZen Pro, including all tables, relationships, and key features.

## Overview

The database is designed to store and manage:
- Android device information and connection history
- Performance analytics and storage trends
- User settings and optimization profiles
- Security events and alerts
- Threat intelligence data

## Database Configuration

- **Default Database**: SQLite (`androidzen.db`)
- **Production Support**: PostgreSQL, MySQL
- **ORM**: SQLAlchemy with Alembic migrations
- **Connection Pooling**: Implemented with optimized settings
- **SQLite Optimizations**: WAL mode, foreign keys enabled, performance tuning

## Core Tables

### 1. devices
Stores Android device information and current status.

**Key Fields:**
- `device_id`: Unique ADB device identifier
- `serial_number`: Device serial number
- `manufacturer`, `model`, `brand`: Device hardware info
- `android_version`, `api_level`: Android system info
- `connection_type`: "usb", "wireless", "emulator"
- `is_connected`: Current connection status
- `properties`: JSON field for extensibility

**Relationships:**
- One-to-many with `device_connection_history`
- One-to-many with `analytics`
- One-to-many with `security_events`

### 2. device_connection_history
Tracks all device connection/disconnection events.

**Key Fields:**
- `device_id`: Foreign key to devices table
- `event_type`: "connected", "disconnected", "reconnected"
- `connection_type`: Connection method used
- `session_duration`: Length of connection session
- `connection_quality`: "excellent", "good", "fair", "poor"

### 3. analytics
Stores performance metrics and device analytics data.

**Key Fields:**
- `device_id`: Foreign key to devices table
- `metric_type`: "performance", "storage", "battery", "network", "app_usage"
- `cpu_usage`, `memory_usage`: Performance percentages
- `storage_*`: Storage usage metrics
- `battery_*`: Battery status and health
- `performance_score`: Calculated overall score (0-100)
- `recorded_at`: When metrics were collected

**Features:**
- Automatic performance score calculation
- Support for anomaly detection flagging
- Flexible JSON fields for custom metrics

### 4. storage_trends
Aggregated storage usage trends over time periods.

**Key Fields:**
- `device_id`: Foreign key to devices table
- `period_type`: "hourly", "daily", "weekly", "monthly"
- `trend_direction`: "increasing", "decreasing", "stable"
- `growth_rate`: Storage growth rate per period
- `predicted_full_date`: When storage might be full

### 5. optimization_profiles
Predefined and custom device optimization configurations.

**Key Fields:**
- `name`: Profile name (e.g., "Battery Saver", "Performance")
- `profile_type`: "battery", "performance", "balanced", "gaming", "custom"
- `is_system`: System-defined vs user-created
- `cpu_governor`, `brightness_level`: Specific optimization settings
- `advanced_settings`: JSON field for complex configurations
- `effectiveness_score`: How well the profile performs

### 6. user_settings
User preferences and application configuration.

**Key Fields:**
- `user_id`: User identifier (for multi-user support)
- `theme`: "light", "dark", "auto"
- `optimization_profile_id`: Foreign key to active profile
- `alert_thresholds`: JSON with custom alert settings
- `dashboard_layout`: Custom dashboard configuration
- `advanced_preferences`: JSON field for extensibility

### 7. profile_applications
Tracks when optimization profiles are applied to devices.

**Key Fields:**
- `profile_id`: Foreign key to optimization_profiles
- `device_id`: Foreign key to devices
- `success`: Whether application succeeded
- `before_performance_score`, `after_performance_score`: Impact measurement
- `settings_changed`: JSON record of what was changed

## Security Tables

### 8. security_events
Stores security alerts and suspicious activities.

**Key Fields:**
- `device_id`: Foreign key to devices table
- `event_type`: "suspicious_app", "root_detection", "malware", etc.
- `severity`: "low", "medium", "high", "critical" (enum)
- `status`: "open", "investigating", "resolved", etc. (enum)
- `risk_score`: Calculated risk level (0-100)
- `threat_indicators`: JSON with IOCs
- `auto_response_taken`: Whether automated response occurred

**Features:**
- Automatic risk score calculation
- Support for recurring event detection
- Investigation workflow tracking
- Integration with threat intelligence

### 9. security_alerts
Notification alerts sent to users for security events.

**Key Fields:**
- `security_event_id`: Foreign key to security_events
- `alert_type`: "email", "push", "dashboard", "sms"
- `status`: "pending", "sent", "delivered", "acknowledged"
- `response_required`: Whether user response is needed
- `response_data`: JSON with user's response

### 10. threat_intelligence
IOCs (Indicators of Compromise) and threat data.

**Key Fields:**
- `threat_type`: "malware", "phishing", "c2_server"
- `ioc_type`: "hash", "domain", "ip", "package_name"
- `ioc_value`: The actual indicator value
- `severity`: Threat severity level
- `detection_count`: How many times detected
- `confidence_score`: Reliability of the intelligence

## Key Features

### 1. Connection Pooling
```python
# SQLite configuration with StaticPool
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    pool_pre_ping=True,
    # SQLite optimizations
)

# PostgreSQL/MySQL with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
)
```

### 2. Database Migrations with Alembic
- Automatic schema versioning
- Safe database upgrades
- Environment-specific configurations
- Rollback support

### 3. Performance Optimizations
- Appropriate indexing on frequently queried columns
- JSON fields for flexible schema extension
- Calculated scores with caching
- Automated data cleanup utilities

### 4. Data Integrity
- Foreign key constraints enabled
- Cascade deletion for related records
- Transaction support with rollback
- Input validation and sanitization

## Usage Examples

### Initialize Database
```python
from backend.utils.database_utils import DatabaseManager

# Initialize with sample data
DatabaseManager.initialize_database(create_sample_data=True)

# Check database health
health = DatabaseManager.health_check()
```

### Query Device Information
```python
from backend.models import Device, Analytics

# Get connected devices
devices = session.query(Device).filter(Device.is_connected == True).all()

# Get recent performance data
recent_analytics = session.query(Analytics)\
    .filter(Analytics.device_id == device_id)\
    .order_by(Analytics.recorded_at.desc())\
    .limit(10).all()
```

### Create Security Event
```python
from backend.models.security import SecurityEvent, SeverityLevel

event = SecurityEvent(
    device_id=device.id,
    event_type="suspicious_app",
    event_title="Suspicious App Detected",
    severity=SeverityLevel.HIGH,
    app_package_name="com.malicious.app"
)
event.calculate_risk_score()
session.add(event)
session.commit()
```

## Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Check current version
alembic current

# Rollback to previous version
alembic downgrade -1
```

## Database Utilities

The `database_utils.py` script provides command-line utilities:

```bash
# Initialize database
python backend/utils/database_utils.py --init

# Create sample data
python backend/utils/database_utils.py --sample-data

# Show database info
python backend/utils/database_utils.py --info

# Health check
python backend/utils/database_utils.py --health

# Clean up old data (keep 30 days)
python backend/utils/database_utils.py --cleanup 30
```

## Environment Variables

- `DATABASE_URL`: Database connection string (default: SQLite)
- `SQL_DEBUG`: Enable SQL query logging (true/false)

## Best Practices

1. **Use transactions** for related operations
2. **Index frequently queried columns** (already implemented)
3. **Use JSON fields sparingly** for truly flexible data
4. **Regular cleanup** of old analytics and history data
5. **Monitor database performance** with health checks
6. **Backup before schema changes** in production

## Schema Evolution

The schema supports evolution through:
- **JSON fields** for adding new properties without schema changes
- **Alembic migrations** for structural changes
- **Backward compatibility** considerations in model changes
- **Versioned APIs** to handle schema updates

This schema provides a robust foundation for AndroidZen Pro while maintaining flexibility for future enhancements.
