# API Documentation

AndroidZen Pro provides a comprehensive REST API with WebSocket support for real-time features. This document covers authentication, endpoints, request/response formats, and examples.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [System](#system-endpoints)
  - [Authentication](#authentication-endpoints)
  - [Devices](#device-management)
  - [Storage](#storage-analysis)
  - [AI Analytics](#ai-analytics)
  - [Security](#security-monitoring)
  - [Admin](#admin-endpoints)
  - [WebSocket](#websocket-endpoints)
- [Rate Limiting](#rate-limiting)
- [SDKs and Libraries](#sdks-and-libraries)

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.yourdomain.com`

All API endpoints are prefixed with `/api` unless otherwise specified.

## Authentication

AndroidZen Pro uses JWT (JSON Web Token) authentication with Bearer token authorization.

### Getting a Token

```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123",
    "username": "your_username",
    "email": "user@example.com",
    "is_admin": false
  }
}
```

### Using the Token

Include the token in the Authorization header:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Refresh

```bash
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "your_refresh_token"
}
```

## Response Format

All API responses follow a consistent format:

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Detailed error message",
    "details": {
      // Additional error context
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Error Handling

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

### Common Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | Valid authentication token required |
| `INVALID_CREDENTIALS` | Username or password incorrect |
| `TOKEN_EXPIRED` | Authentication token has expired |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | Requested resource does not exist |
| `VALIDATION_ERROR` | Request data validation failed |
| `RATE_LIMIT_EXCEEDED` | API rate limit exceeded |

## Endpoints

## System Endpoints

### Health Check

Check API health and status.

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "AndroidZen Pro Backend",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### API Information

Get API version and available endpoints.

```bash
GET /
```

**Response:**
```json
{
  "message": "AndroidZen Pro Backend API",
  "version": "1.0.0",
  "docs_url": "/docs",
  "health_check": "/health",
  "websocket_endpoint": "/ws"
}
```

## Authentication Endpoints

### Register User

Create a new user account.

```bash
POST /api/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "securepassword123",
  "full_name": "New User"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "456",
    "username": "newuser",
    "email": "newuser@example.com",
    "is_active": true
  }
}
```

### Login

Authenticate and receive access tokens.

```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

### Get Current User

Get current authenticated user information.

```bash
GET /api/auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user": {
    "id": "123",
    "username": "user",
    "email": "user@example.com",
    "full_name": "User Name",
    "is_admin": false,
    "permissions": ["read_devices", "manage_own_devices"],
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

### Logout

Invalidate current session.

```bash
POST /api/auth/logout
Authorization: Bearer <token>
```

## Device Management

### List Devices

Get all devices for authenticated user.

```bash
GET /api/devices/
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20)
- `status` (string): Filter by status (`connected`, `disconnected`)
- `search` (string): Search by device name or model

**Response:**
```json
{
  "devices": [
    {
      "id": "device_123",
      "name": "Samsung Galaxy S21",
      "model": "SM-G991B",
      "android_version": "13",
      "is_connected": true,
      "battery_level": 85,
      "storage_used": 45.2,
      "storage_total": 128.0,
      "last_seen": "2024-01-01T12:00:00Z",
      "status": "healthy"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

### Get Device Details

Get detailed information for a specific device.

```bash
GET /api/devices/{device_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "device": {
    "id": "device_123",
    "name": "Samsung Galaxy S21",
    "model": "SM-G991B",
    "manufacturer": "Samsung",
    "android_version": "13",
    "api_level": 33,
    "is_connected": true,
    "battery_level": 85,
    "battery_health": "good",
    "storage": {
      "used": 45.2,
      "total": 128.0,
      "available": 82.8,
      "usage_by_category": {
        "apps": 20.5,
        "photos": 15.3,
        "videos": 5.8,
        "audio": 2.1,
        "other": 1.5
      }
    },
    "performance": {
      "cpu_usage": 25.5,
      "memory_usage": 60.2,
      "temperature": 32.5
    },
    "network": {
      "wifi_connected": true,
      "signal_strength": -45,
      "data_usage_today": 125.6
    },
    "last_seen": "2024-01-01T12:00:00Z",
    "enrolled_at": "2024-01-01T10:00:00Z"
  }
}
```

### Update Device

Update device settings or information.

```bash
PUT /api/devices/{device_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Samsung Phone",
  "settings": {
    "auto_backup": true,
    "notification_enabled": true
  }
}
```

### Device Actions

Perform actions on a device.

```bash
POST /api/devices/{device_id}/actions
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "restart_adb",
  "parameters": {}
}
```

**Available Actions:**
- `restart_adb` - Restart ADB connection
- `refresh_info` - Refresh device information
- `cleanup_storage` - Run storage cleanup
- `optimize_performance` - Run performance optimization

## Storage Analysis

### Storage Statistics

Get storage statistics across all devices.

```bash
GET /api/storage/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total_devices": 5,
  "total_storage": 640.0,
  "used_storage": 425.6,
  "available_storage": 214.4,
  "average_usage": 66.5,
  "trends": {
    "daily_change": -2.1,
    "weekly_change": 5.8,
    "monthly_change": 12.3
  },
  "categories": {
    "apps": 125.5,
    "photos": 98.2,
    "videos": 85.1,
    "audio": 15.8,
    "system": 45.2,
    "other": 55.8
  }
}
```

### Device Storage Details

Get detailed storage information for a specific device.

```bash
GET /api/storage/{device_id}
Authorization: Bearer <token>
```

### Storage Recommendations

Get AI-powered storage optimization recommendations.

```bash
GET /api/storage/{device_id}/recommendations
Authorization: Bearer <token>
```

**Response:**
```json
{
  "recommendations": [
    {
      "type": "cleanup",
      "category": "cache",
      "description": "Clear app cache to free up 2.1 GB",
      "potential_savings": 2.1,
      "impact": "low",
      "actions": ["clear_cache"]
    },
    {
      "type": "duplicate_files",
      "category": "photos",
      "description": "Remove 45 duplicate photos",
      "potential_savings": 0.8,
      "impact": "medium",
      "actions": ["remove_duplicates"]
    }
  ],
  "total_potential_savings": 2.9
}
```

## AI Analytics

### AI Service Health

Check AI service status and capabilities.

```bash
GET /api/ai/health
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": 3,
  "features_available": [
    "usage_pattern_analysis",
    "predictive_maintenance",
    "anomaly_detection",
    "user_behavior_clustering",
    "ai_recommendations"
  ]
}
```

### Usage Analytics

Get AI-powered usage analytics for a device.

```bash
GET /api/ai/analytics/{device_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "device_id": "device_123",
  "analysis_period": "30_days",
  "usage_patterns": {
    "peak_hours": ["09:00-11:00", "19:00-22:00"],
    "most_used_apps": [
      {"app": "Chrome", "usage_hours": 45.2},
      {"app": "WhatsApp", "usage_hours": 32.1}
    ],
    "screen_time_trend": "increasing"
  },
  "performance_insights": {
    "battery_health_trend": "stable",
    "storage_growth_rate": 2.1,
    "performance_score": 85
  },
  "recommendations": [
    {
      "type": "battery_optimization",
      "description": "Reduce background app refresh to improve battery life",
      "priority": "medium"
    }
  ]
}
```

### Predictive Maintenance

Get predictive maintenance alerts and recommendations.

```bash
GET /api/ai/maintenance/{device_id}
Authorization: Bearer <token>
```

### Anomaly Detection

Get anomaly detection results for a device.

```bash
GET /api/ai/anomalies/{device_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "device_id": "device_123",
  "scan_time": "2024-01-01T12:00:00Z",
  "anomalies": [
    {
      "type": "unusual_battery_drain",
      "severity": "medium",
      "description": "Battery draining 40% faster than normal",
      "detected_at": "2024-01-01T11:30:00Z",
      "suggested_actions": ["check_background_apps", "battery_calibration"]
    }
  ],
  "overall_health_score": 78
}
```

## Security Monitoring

### Security Events

Get security events and alerts.

```bash
GET /api/security/events
Authorization: Bearer <token>
```

**Query Parameters:**
- `severity` (string): Filter by severity (`low`, `medium`, `high`, `critical`)
- `event_type` (string): Filter by event type
- `start_date` (string): Start date (ISO 8601)
- `end_date` (string): End date (ISO 8601)

### Security Scan

Perform security scan on a device.

```bash
POST /api/security/scan/{device_id}
Authorization: Bearer <token>
```

### Security Dashboard

Get security overview dashboard data.

```bash
GET /api/security/dashboard
Authorization: Bearer <token>
```

## Admin Endpoints

**Note:** Admin endpoints require admin privileges.

### List All Users

```bash
GET /api/admin/users
Authorization: Bearer <admin_token>
```

**Query Parameters:**
- `page` (int): Page number
- `per_page` (int): Items per page
- `search` (string): Search users
- `active_only` (boolean): Filter active users only

### Create User

```bash
POST /api/admin/users
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User",
  "is_admin": false,
  "permissions": ["read_devices"]
}
```

### Update User

```bash
PUT /api/admin/users/{user_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "is_active": false,
  "permissions": ["read_devices", "write_devices"]
}
```

### Delete User

```bash
DELETE /api/admin/users/{user_id}
Authorization: Bearer <admin_token>
```

### System Statistics

```bash
GET /api/admin/system/stats
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_users": 150,
  "active_users": 142,
  "admin_users": 5,
  "active_sessions": 78,
  "total_devices": 300,
  "connected_devices": 245
}
```

### System Cleanup

```bash
POST /api/admin/system/cleanup
Authorization: Bearer <admin_token>
```

### Audit Logs

```bash
GET /api/admin/audit/logs
Authorization: Bearer <admin_token>
```

**Query Parameters:**
- `page` (int): Page number
- `per_page` (int): Items per page
- `level` (string): Log level filter
- `start_date` (string): Start date
- `end_date` (string): End date

## WebSocket Endpoints

### Connection

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=YOUR_JWT_TOKEN');
```

### WebSocket Statistics

Get WebSocket connection statistics:

```bash
GET /ws/stats
```

**Response:**
```json
{
  "websocket_stats": {
    "total_connections": 25,
    "active_connections": 23,
    "total_users": 18,
    "subscription_counts": {
      "device_updates": 15,
      "system_alerts": 8,
      "performance_metrics": 12
    }
  },
  "status": "active"
}
```

### Message Types

WebSocket messages follow this format:

```json
{
  "type": "device_update",
  "data": {
    "device_id": "device_123",
    "battery_level": 75,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

**Message Types:**
- `device_update` - Device status updates
- `system_alert` - System-wide alerts
- `performance_metrics` - Real-time performance data
- `security_event` - Security alerts
- `user_notification` - User-specific notifications

### Subscriptions

Subscribe to specific event types:

```json
{
  "action": "subscribe",
  "events": ["device_updates", "system_alerts"]
}
```

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Default**: 100 requests per minute per user
- **Admin endpoints**: 200 requests per minute
- **Authentication endpoints**: 10 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

## SDKs and Libraries

### JavaScript/TypeScript

```javascript
// Using the built-in API service
import { apiService } from './services/api';

// Get devices
const devices = await apiService.get('/api/devices/');

// Create device
const newDevice = await apiService.post('/api/devices/', deviceData);
```

### Python

```python
import requests

# Authentication
response = requests.post('http://localhost:8000/api/auth/login', json={
    'username': 'user',
    'password': 'password'
})
token = response.json()['access_token']

# API calls with authentication
headers = {'Authorization': f'Bearer {token}'}
devices = requests.get('http://localhost:8000/api/devices/', headers=headers)
```

### cURL Examples

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Get devices
curl -X GET http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create device action
curl -X POST http://localhost:8000/api/devices/device_123/actions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "refresh_info"}'
```

## Interactive Documentation

AndroidZen Pro provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Support

For API support:
1. Check the interactive documentation
2. Review this API documentation
3. Check GitHub Issues
4. Contact the development team

## Changelog

### Version 1.0.0
- Initial API release
- Authentication endpoints
- Device management
- Storage analysis
- AI analytics
- WebSocket support
- Admin endpoints
