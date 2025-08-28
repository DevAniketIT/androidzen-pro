# Settings Enhancement Hub - AndroidZen Pro

## Overview

The Settings Enhancement Hub is a comprehensive settings management system for AndroidZen Pro that provides:

- **Safe System Settings Reader**: Securely read Android system settings via ADB
- **Battery Optimization Recommendations**: AI-powered suggestions for extending battery life
- **Performance Tuning**: Animation scales, background process optimization, hardware acceleration
- **Network Configuration Optimizer**: WiFi, mobile data, and connectivity optimizations
- **Settings Backup & Restore**: Complete device settings preservation and restoration
- **User-friendly Optimization Profiles**: Pre-built and custom optimization configurations

## Key Features

### 🔒 Safe Settings Management
- Whitelist-based safe settings modification
- Root requirement detection
- Settings validation and type checking
- Automatic cache invalidation for consistency

### 🔋 Battery Optimization Engine
- Real-time battery usage analysis
- App-specific battery optimization suggestions
- Screen brightness and timeout recommendations
- Animation scale optimization for power saving

### ⚡ Performance Recommendations
- Hardware UI rendering optimization
- Background process limiting
- Animation scale tuning for responsiveness
- GPU rendering force enablement

### 🌐 Network Optimization
- WiFi sleep policy optimization
- Data roaming management
- Network-based location optimization
- Connectivity stability improvements

### 💾 Backup & Restore System
- Complete settings backup with checksum verification
- Selective namespace restoration (system, secure, global)
- Automatic cleanup of old backups
- Metadata tracking and size optimization

### 🎯 Optimization Profiles
- **Battery Saver**: Maximum battery life with reduced performance
- **Performance**: Maximum responsiveness and speed
- **Balanced**: Optimal balance between battery life and performance
- **Gaming**: Optimized for gaming performance
- **Custom**: User-defined optimization parameters

## Architecture

```
SettingsService
├── System Settings Reader (ADB Integration)
├── Recommendation Engine
│   ├── Battery Optimizer
│   ├── Performance Analyzer
│   └── Network Configuration
├── Backup & Restore Manager
├── Optimization Profile Manager
└── Cache Management System
```

## API Endpoints

### Optimization Profiles

#### List Profiles
```http
GET /api/v1/settings/profiles
```

Query Parameters:
- `profile_type`: Filter by type (battery, performance, balanced, gaming, custom)
- `active_only`: Show only active profiles
- `system_only`: Show only system-defined profiles

#### Create Custom Profile
```http
POST /api/v1/settings/profiles
```

#### Apply Profile to Device
```http
POST /api/v1/settings/profiles/{profile_id}/apply
```

### Recommendations

#### Get Device Recommendations
```http
GET /api/v1/settings/recommendations/{device_id}
```

Query Parameters:
- `category`: Filter by category (battery, performance, network)

#### Apply Recommendations
```http
POST /api/v1/settings/recommendations/apply
```

### Settings Backup & Restore

#### Create Backup
```http
POST /api/v1/settings/settings/backup
```

#### List Backups
```http
GET /api/v1/settings/settings/backups
```

#### Restore Settings
```http
POST /api/v1/settings/settings/restore
```

#### Delete Backup
```http
DELETE /api/v1/settings/settings/backups/{backup_id}
```

## Usage Examples

### Creating a Settings Service Instance

```python
from backend.core.adb_manager import AdbManager
from backend.services.settings_service import SettingsService
from backend.core.database import get_db

# Initialize ADB manager and database session
adb_manager = AdbManager(auto_connect=True)
db_session = next(get_db())

# Create settings service
settings_service = SettingsService(adb_manager, db_session)
```

### Reading System Settings

```python
# Read all system settings safely
settings = await settings_service.read_system_settings(device_id)

# Read specific namespace
system_settings = await settings_service.read_system_settings(
    device_id, namespace="system"
)

# Read specific settings keys
brightness_settings = await settings_service.read_system_settings(
    device_id, 
    namespace="system",
    keys=["screen_brightness", "screen_off_timeout"]
)
```

### Generating Optimization Recommendations

```python
# Generate battery recommendations
battery_recs = await settings_service.generate_battery_recommendations(device_id)

# Generate performance recommendations
perf_recs = await settings_service.generate_performance_recommendations(device_id)

# Get all recommendations
all_recs = await settings_service.get_comprehensive_recommendations(device_id)

# Apply specific recommendations
results = await settings_service.apply_recommendations(
    device_id, 
    ["battery_0", "performance_1", "network_0"]
)
```

### Working with Optimization Profiles

```python
# Get available profiles
profiles = settings_service.get_optimization_profiles()

# Create custom profile
custom_profile = settings_service.create_custom_profile(
    name="Gaming Performance",
    description="Optimized for mobile gaming",
    brightness_level=200,
    animation_scale=0.5,
    force_gpu_rendering=True,
    advanced_settings={
        "location_mode": "high_accuracy",
        "force_msaa": True
    }
)

# Apply profile to device
success = await settings_service.apply_optimization_profile(
    device_id, profile.id, applied_by="user"
)
```

### Settings Backup and Restore

```python
# Create backup
backup = await settings_service.create_settings_backup(
    device_id, "Pre-optimization Backup"
)

# List available backups
backups = settings_service.get_backup_list(device_id)

# Restore from backup (only safe settings)
success = await settings_service.restore_settings_backup(
    device_id, backup.backup_id
)

# Restore specific namespaces
success = await settings_service.restore_settings_backup(
    device_id, backup.backup_id, namespace_filter=["system"]
)
```

## Safety Features

### Safe Settings Whitelist

The service maintains a comprehensive whitelist of Android settings that are safe to modify without root access:

#### System Settings
- `window_animation_scale`
- `transition_animation_scale`
- `animator_duration_scale`
- `screen_brightness`
- `screen_off_timeout`
- `accelerometer_rotation`
- `haptic_feedback_enabled`

#### Secure Settings
- `android_id` (read-only)
- `bluetooth_name`
- `default_input_method`
- `location_providers_allowed`

#### Global Settings
- `airplane_mode_on`
- `auto_time`
- `auto_time_zone`
- `development_settings_enabled`
- `wifi_sleep_policy`

### Root Requirement Detection

Settings that require root access are automatically flagged and handled appropriately:

```python
setting = SystemSetting(
    namespace="system",
    key="cpu_governor",
    value="performance",
    value_type="string",
    safe_to_modify=False,
    requires_root=True
)
```

### Validation and Error Handling

- **Value Type Validation**: Automatic detection of boolean, integer, float, and string values
- **Setting Existence Check**: Verification that settings exist before modification
- **ADB Connection Status**: Ensures device connectivity before operations
- **Transaction Safety**: Database rollback on service operation failures

## Performance Optimizations

### Caching System
- **5-minute TTL**: Settings cache expires after 5 minutes
- **Per-device Caching**: Separate cache keys for each device
- **Selective Invalidation**: Cache cleared only for modified devices
- **Namespace-aware**: Separate caching for system, secure, and global settings

### Batch Operations
- **Bulk Settings Read**: Single ADB command for multiple settings
- **Optimized Parsing**: Efficient line-by-line settings parsing
- **Connection Pooling**: Reused ADB connections for multiple operations

### Memory Management
- **Lazy Loading**: Settings loaded only when requested
- **Automatic Cleanup**: Old cache entries automatically expired
- **Minimal Memory Footprint**: Efficient data structures

## Configuration

### Environment Variables

```bash
# Backup storage directory
SETTINGS_BACKUP_DIR=/path/to/backups

# Cache timeout (in seconds)
SETTINGS_CACHE_TTL=300

# ADB command timeout
ADB_COMMAND_TIMEOUT=30

# Maximum retry attempts
MAX_RETRY_ATTEMPTS=3
```

### Initialization Options

```python
settings_service = SettingsService(
    adb_manager=adb_manager,
    db_session=db_session,
    backup_dir="data/backups"  # Custom backup directory
)
```

## Error Handling

### Common Error Scenarios

1. **Device Not Connected**
   ```python
   if not adb_manager.is_device_connected(device_id):
       raise DeviceNotConnectedException(f"Device {device_id} not connected")
   ```

2. **Permission Denied**
   ```python
   if not setting.safe_to_modify:
       logger.warning(f"Setting {setting.key} requires root access")
       return False
   ```

3. **Invalid Setting Value**
   ```python
   try:
       validated_value = validate_setting_value(key, value, value_type)
   except ValueError as e:
       logger.error(f"Invalid value for {key}: {e}")
       return False
   ```

### Logging and Monitoring

```python
# Comprehensive logging at all levels
logger.info(f"Applied profile {profile.name} to device {device_id}")
logger.warning(f"Setting {key} may not be safe to modify")
logger.error(f"Failed to execute command: {command}")
logger.debug(f"Cache hit for device {device_id}")
```

## Testing

### Unit Tests

Run unit tests for the settings service:

```bash
python -m pytest backend/tests/test_settings_service.py -v
```

### Integration Tests

Test with real Android devices:

```bash
python -m pytest backend/tests/integration/test_settings_integration.py -v
```

### Load Testing

Performance testing with multiple devices:

```bash
python -m pytest backend/tests/performance/test_settings_performance.py -v
```

## Security Considerations

### Data Protection
- **Settings Encryption**: Sensitive settings encrypted at rest
- **Checksum Verification**: Backup integrity verification
- **Access Control**: User-based access restrictions
- **Audit Logging**: Complete operation audit trail

### Safe Operations
- **Whitelist Validation**: Only approved settings modification
- **Rollback Capability**: Quick settings restoration
- **Sandbox Testing**: Safe testing environment
- **Permission Verification**: Runtime permission checks

## Monitoring and Analytics

### Performance Metrics
- Settings read/write latency
- Cache hit/miss ratios
- Profile application success rates
- Backup creation times

### Usage Analytics
- Most applied optimization profiles
- Common recommendation categories
- Device-specific optimization patterns
- User preference trends

## Troubleshooting

### Common Issues

1. **ADB Connection Failures**
   - Verify device USB debugging enabled
   - Check ADB server status
   - Restart ADB daemon if necessary

2. **Settings Not Applied**
   - Confirm device is not in read-only mode
   - Check if setting requires root access
   - Verify setting key is in whitelist

3. **Backup Failures**
   - Ensure sufficient disk space
   - Check backup directory permissions
   - Verify device connectivity

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger('backend.services.settings_service').setLevel(logging.DEBUG)
```

## Contributing

### Development Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

3. Run tests:
   ```bash
   python -m pytest
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Add comprehensive docstrings
- Include error handling for all operations

## License

This Settings Enhancement Hub is part of AndroidZen Pro and is subject to the project's license terms.

## Support

For support and questions:
- Create an issue in the project repository
- Contact the development team
- Review the troubleshooting documentation
