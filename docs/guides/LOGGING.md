# AndroidZen Pro Comprehensive Logging System

This document describes the comprehensive logging, error tracking, and performance monitoring system implemented for AndroidZen Pro.

## Overview

The logging system provides:

- **Structured logging** with JSON output and contextual information
- **Performance monitoring** with automatic metrics collection
- **Error tracking** and reporting
- **Request/response logging** with FastAPI middleware
- **Security logging** for suspicious activities
- **Log rotation** and archiving
- **Debug mode** for development
- **Real-time monitoring** endpoints

## Quick Start

### Basic Usage

```python
from backend.core.logging_config import setup_logging, get_logger

# Setup logging (usually done once at application startup)
logger = setup_logging(
    app_name="my-app",
    log_level="INFO",
    log_format="console",  # or "structured" for JSON
    log_file="./logs/app.log"
)

# Use the logger
logger.info("Application started")
logger.error("Something went wrong", context={"user_id": "123"})
```

### Performance Monitoring

```python
from backend.core.logging_config import get_logger, performance_monitor

logger = get_logger(__name__)

# Using decorator
@performance_monitor("database_query")
async def query_database(sql: str):
    # Your code here
    pass

# Using context manager
async def some_operation():
    with logger.performance_context("complex_operation"):
        # Your code here
        pass
```

### Request Context

```python
from backend.core.logging_config import set_request_context, clear_request_context

# Set context for the current request
set_request_context(
    request_id="req-123",
    user_id="user-456",
    device_id="device-789"
)

# All logs will now include this context automatically
logger.info("Processing request")  # Will include request_id, user_id, device_id

# Clear context when done
clear_request_context()
```

## Configuration

### Environment Variables

Create a `.env` file based on `backend/config/logging.env.example`:

```bash
# Basic logging
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=console

# File logging
LOG_FILE=./logs/androidzen-pro.log
MAX_LOG_FILE_SIZE=10485760
LOG_BACKUP_COUNT=5

# Request logging
LOG_REQUESTS=true
LOG_RESPONSES=true
LOG_REQUEST_BODY=false
LOG_RESPONSE_BODY=false

# Performance monitoring
ENABLE_PERFORMANCE_MONITORING=true
SLOW_REQUEST_THRESHOLD=1000

# Error tracking
ENABLE_ERROR_TRACKING=true
MAX_ERROR_HISTORY=1000
```

### Programmatic Configuration

```python
from backend.core.logging_config import setup_logging

logger = setup_logging(
    app_name="androidzen-pro",
    log_level="DEBUG",
    log_format="structured",  # JSON output
    log_file="./logs/app.log",
    max_file_size=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    enable_performance_monitoring=True,
    enable_error_tracking=True
)
```

## Features

### 1. Structured Logging

The system provides structured JSON logging with rich contextual information:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger_name": "androidzen-pro",
  "message": "User request processed",
  "module": "api.devices",
  "function": "get_devices",
  "line_number": 45,
  "thread_id": 12345,
  "process_id": 1234,
  "request_id": "req-abc123",
  "user_id": "user-456",
  "device_id": "device-789",
  "execution_time": 0.234,
  "extra_data": {
    "operation": "list_devices",
    "count": 5
  }
}
```

### 2. Performance Monitoring

Automatic performance monitoring with metrics collection:

- **Request timing**: HTTP request/response times
- **Operation timing**: Database queries, API calls, etc.
- **Slow request detection**: Configurable threshold alerts
- **Metrics storage**: In-memory queue with configurable limits
- **Performance APIs**: RESTful endpoints for metrics access

#### Using Performance Decorators

```python
from backend.core.logging_config import performance_monitor, log_exceptions

@performance_monitor("user_authentication")
@log_exceptions()
async def authenticate_user(username: str, password: str):
    # Function automatically timed and exceptions logged
    pass
```

#### Using Performance Context

```python
logger = get_logger(__name__)

async def complex_operation():
    with logger.performance_context(
        "data_processing",
        context={"batch_size": 1000},
        tags={"operation_type": "batch"}
    ):
        # Code is automatically timed
        # Metrics are recorded with context and tags
        pass
```

### 3. Error Tracking

Comprehensive error tracking and reporting:

- **Automatic error counting**: Track error frequency by type
- **Error history**: Keep detailed history of errors
- **Context preservation**: Maintain request/user context in errors
- **Stack trace capture**: Full stack traces for debugging
- **Error APIs**: RESTful endpoints for error analysis

```python
# Errors are automatically tracked when using the logger
logger.error("Database connection failed", context={
    "database": "primary",
    "retry_count": 3,
    "last_error": "Connection timeout"
})

# Get error summary
error_summary = logger.error_tracker.get_error_summary()
print(f"Total errors: {error_summary['total_errors']}")
```

### 4. Request/Response Middleware

FastAPI middleware for automatic request/response logging:

```python
from backend.middleware import LoggingMiddleware

app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True,
    log_request_body=False,  # Enable with caution
    log_response_body=False
)
```

Features:
- **Request logging**: Method, URL, headers, body (optional)
- **Response logging**: Status code, headers, body (optional)
- **Performance tracking**: Automatic request timing
- **Context extraction**: User and session information
- **Security filtering**: Sensitive header redaction

### 5. Security Logging

Security-focused logging middleware:

```python
from backend.middleware import SecurityLoggingMiddleware

app.add_middleware(SecurityLoggingMiddleware)
```

Features:
- **Suspicious pattern detection**: SQL injection, XSS attempts
- **Authentication logging**: Login attempts and failures
- **Rate limiting**: Unusual request patterns
- **IP tracking**: Client IP addresses for security events

### 6. Log Rotation and Archiving

Automatic log file management:

- **Size-based rotation**: Rotate when files exceed configured size
- **Backup retention**: Keep specified number of backup files
- **Compression**: Optional gzip compression for archives
- **Date-based naming**: Timestamped backup files

## Monitoring APIs

### Health Check

```bash
GET /api/monitoring/health
```

Returns system health information including CPU, memory, and disk usage.

### Performance Metrics

```bash
GET /api/monitoring/metrics/summary
GET /api/monitoring/metrics/performance?limit=100&metric_type=database
```

Access performance metrics and summaries.

### Error Tracking

```bash
GET /api/monitoring/errors/summary
```

Get error statistics and recent error history (admin only).

### System Information

```bash
GET /api/monitoring/system/info
POST /api/monitoring/logs/level?level=DEBUG
```

System information and dynamic log level changes (admin only).

### Alerts

```bash
GET /api/monitoring/alerts
```

Get system alerts based on resource usage and error rates.

## Development vs Production

### Development Configuration

```bash
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=console
LOG_REQUESTS=true
LOG_RESPONSES=true
```

Features:
- Colored console output
- Detailed debug information
- Request/response logging
- Auto-reload on changes

### Production Configuration

```bash
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=structured
LOG_FILE=/var/log/androidzen/app.log
LOG_REQUESTS=false
LOG_REQUEST_BODY=false
LOG_RESPONSE_BODY=false
```

Features:
- JSON structured logging
- File-based logging with rotation
- Reduced verbosity
- Security-conscious (no body logging)

## Integration Examples

### Database Operations

```python
from backend.core.logging_config import get_logger, performance_monitor

logger = get_logger(__name__)

@performance_monitor("database.query")
async def get_user_devices(user_id: str):
    with logger.performance_context("database_query", context={"user_id": user_id}):
        logger.info("Fetching user devices", context={"user_id": user_id})
        
        try:
            # Database query here
            devices = await db.query(Device).filter_by(user_id=user_id).all()
            
            logger.info("Devices retrieved successfully", context={
                "user_id": user_id,
                "device_count": len(devices)
            })
            
            return devices
            
        except Exception as e:
            logger.exception("Failed to retrieve devices", context={
                "user_id": user_id,
                "error": str(e)
            })
            raise
```

### API Endpoints

```python
from fastapi import APIRouter, Depends
from backend.core.logging_config import get_logger, set_request_context

router = APIRouter()
logger = get_logger(__name__)

@router.get("/devices")
async def list_devices(current_user: dict = Depends(get_current_user)):
    # Context is automatically set by middleware, but you can add more
    logger.info("Listing user devices", context={
        "user_id": current_user["id"],
        "endpoint": "list_devices"
    })
    
    # Your business logic here
    pass
```

## Best Practices

### 1. Use Appropriate Log Levels

- **DEBUG**: Detailed information for troubleshooting
- **INFO**: General application flow
- **WARNING**: Unusual conditions that might need attention
- **ERROR**: Serious problems that need immediate attention
- **CRITICAL**: System failure conditions

### 2. Include Context

Always include relevant context information:

```python
logger.info("User action completed", context={
    "user_id": user.id,
    "action": "device_scan",
    "duration": elapsed_time,
    "devices_found": len(devices)
})
```

### 3. Performance Monitoring

Use performance monitoring for important operations:

```python
# For functions/methods
@performance_monitor("critical_operation")
async def critical_operation():
    pass

# For code blocks
with logger.performance_context("batch_processing"):
    # Process large batch
    pass
```

### 4. Error Handling

Always provide context for errors:

```python
try:
    result = await risky_operation()
except SpecificException as e:
    logger.error("Operation failed", context={
        "operation": "risky_operation",
        "parameters": {"param1": value1},
        "error_details": str(e)
    })
    raise
```

### 5. Security Considerations

- Never log sensitive data (passwords, tokens, personal info)
- Use context to include non-sensitive identifiers
- Enable body logging only in development
- Regularly rotate and archive logs

### 6. Testing Logging

```python
import pytest
from backend.core.logging_config import get_logger

def test_logging():
    logger = get_logger("test")
    
    # Test different scenarios
    logger.info("Test message", context={"test": True})
    
    # Check performance monitoring
    with logger.performance_context("test_operation"):
        # Test code
        pass
    
    # Verify metrics were recorded
    metrics = logger.performance_monitor.get_metrics(limit=1)
    assert len(metrics) > 0
    assert "test_operation" in metrics[0].metric_name
```

## Troubleshooting

### Common Issues

1. **Logs not appearing**: Check log level configuration
2. **File permissions**: Ensure write access to log directory
3. **Disk space**: Monitor disk usage for log files
4. **Performance impact**: Adjust logging levels in production

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### Log Analysis

For structured JSON logs, use tools like:
- **jq** for command-line JSON processing
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Fluentd** for log collection
- **Grafana** for visualization

Example jq usage:
```bash
# Filter error logs
jq 'select(.level == "ERROR")' app.log

# Get performance metrics
jq 'select(.execution_time != null) | {timestamp, execution_time, message}' app.log
```

## Demo

Run the logging demo to see all features in action:

```bash
cd backend
python -m examples.logging_demo
```

This will demonstrate:
- Different log levels and contexts
- Performance monitoring
- Error tracking
- Request context management
- Metrics collection

Check the generated log files in `./logs/` for examples of structured JSON output.

## API Documentation

The monitoring endpoints are automatically documented in the FastAPI docs at `/docs` when the application is running.

Key endpoints:
- `GET /api/monitoring/health` - System health check
- `GET /api/monitoring/metrics/summary` - Performance metrics
- `GET /api/monitoring/errors/summary` - Error tracking (admin)
- `GET /api/monitoring/alerts` - System alerts
- `POST /api/monitoring/logs/level` - Change log level (admin)

## Support

For questions or issues with the logging system:

1. Check this documentation
2. Run the demo script for examples
3. Review the configuration in `backend/config/logging.env.example`
4. Check the source code in `backend/core/logging_config.py`
