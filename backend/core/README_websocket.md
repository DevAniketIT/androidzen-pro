# WebSocket Real-Time Communication System

This document describes the WebSocket implementation for AndroidZen Pro's real-time monitoring and communication features.

## Overview

The WebSocket system provides bidirectional real-time communication between the backend server and frontend clients. It supports:

- Real-time device status broadcasting
- Live monitoring data streams  
- Notification system for alerts
- Connection state management
- Automatic reconnection logic
- Message queuing during disconnections
- Subscription-based message filtering

## Architecture

### Backend Components

1. **WebSocketManager** (`websocket_manager.py`)
   - Manages all WebSocket connections
   - Handles message routing and broadcasting
   - Provides subscription management
   - Implements connection cleanup and heartbeat monitoring

2. **WebSocketConnection** 
   - Represents individual client connections
   - Tracks connection metadata and subscriptions
   - Handles message sending with error handling

3. **MessageType Enum**
   - Defines all supported message types
   - Ensures type safety for message routing

### Frontend Components

1. **WebSocketClient** (`websocket.js`)
   - Manages client-side WebSocket connection
   - Implements automatic reconnection with exponential backoff
   - Provides message queuing during disconnections
   - Handles subscription management and heartbeat

## Message Types

### Real-Time Data
- `device_status` - Device connection and status updates
- `live_metrics` - Real-time performance metrics
- `performance_data` - Performance analytics data
- `analytics_update` - General analytics updates

### Notifications
- `notification` - General notifications to users
- `security_alert` - Security-related alerts
- `device_action` - Device action status updates
- `system_message` - System-level messages

### Connection Management
- `heartbeat` - Keep-alive messages
- `device_connected`/`device_disconnected` - Connection events
- `subscription`/`unsubscription` - Topic management

## API Endpoints

### WebSocket Connection
- `ws://localhost:8000/ws` - Main WebSocket endpoint
- Query parameters: `client_id`, `token` (optional authentication)

### REST API Endpoints
- `GET /ws/stats` - Get connection statistics
- `POST /ws/broadcast` - Broadcast message to all clients
- `POST /ws/send-to-user/{user_id}` - Send message to specific user
- `POST /ws/device-alert` - Send device-specific alert
- `POST /ws/live-metrics` - Send live performance metrics
- `POST /ws/notification` - Send notification
- `POST /ws/performance-data` - Broadcast performance data
- `POST /ws/device-action/{device_id}` - Send device action status
- `POST /ws/start-monitoring/{device_id}` - Start real-time monitoring

## Usage Examples

### Frontend Usage

```javascript
// Initialize WebSocket client
const wsClient = new WebSocketClient('ws://localhost:8000/ws', {
    maxReconnectAttempts: 10,
    reconnectDelay: 1000,
    heartbeatInterval: 30000,
    enableHeartbeat: true,
    messageQueueEnabled: true
});

// Subscribe to device updates
wsClient.subscribe('device_status');
wsClient.subscribe('notifications');

// Listen for specific message types
wsClient.on('device_status', (data) => {
    console.log('Device status update:', data);
    // Update UI with device data
});

wsClient.on('notification', (data) => {
    console.log('New notification:', data);
    // Show notification to user
});

// Send messages
wsClient.send({
    type: 'subscription',
    data: { topic: 'device_device1' }
});
```

### Backend Usage

```python
# Send real-time metrics
await websocket_manager.send_live_metrics('device_1', {
    'cpu_usage': 45.2,
    'memory_usage': 67.8,
    'battery_level': 85
})

# Send notification
await websocket_manager.send_notification(
    'security', 
    'Security Alert', 
    'Suspicious activity detected',
    'high',
    device_id='device_1'
)

# Broadcast to all subscribers
await websocket_manager.broadcast(
    MessageType.DEVICE_STATUS,
    {'devices': device_list},
    subscription_filter='device_status'
)
```

## Subscription System

Clients can subscribe to specific topics to receive filtered messages:

- `device_status` - All device status updates
- `device_{device_id}` - Updates for specific device
- `metrics_{device_id}` - Live metrics for specific device
- `notifications` - All notifications
- `security` - Security alerts
- `performance` - Performance data
- `analytics` - Analytics updates

## Connection Management

### Heartbeat System
- Server sends heartbeat every 30 seconds (configurable)
- Clients respond to maintain connection
- Inactive connections cleaned up after 5 minutes

### Automatic Reconnection
- Exponential backoff strategy
- Maximum retry attempts configurable
- Message queuing during reconnection
- Automatic re-subscription to topics

### Connection States
- `CONNECTING` - Establishing connection
- `OPEN` - Connected and ready
- `CLOSING` - Closing connection
- `CLOSED` - Connection closed
- `RECONNECTING` - Attempting to reconnect
- `FAILED` - Connection failed permanently

## Security

- Optional authentication via JWT tokens
- Connection-level user identification
- Subscription-based message filtering
- Admin-only management endpoints

## Configuration

### Backend Configuration
```python
# WebSocket manager settings
websocket_manager = WebSocketManager()

# Connection cleanup interval
cleanup_interval = 300  # 5 minutes

# Heartbeat settings
heartbeat_interval = 30  # 30 seconds
```

### Frontend Configuration
```javascript
const options = {
    maxReconnectAttempts: 10,     // Maximum reconnection attempts
    reconnectDelay: 1000,         // Base delay between attempts (ms)
    heartbeatInterval: 30000,     // Heartbeat interval (ms)
    enableHeartbeat: true,        // Enable heartbeat
    autoConnect: true,            // Auto-connect on instantiation
    messageQueueEnabled: true     // Queue messages during disconnection
};
```

## Monitoring and Debugging

### Connection Statistics
The `/ws/stats` endpoint provides:
- Total connections
- Active connections
- Total users
- Subscription counts
- Average subscriptions per client

### Logging
- Connection events logged at INFO level
- Message routing logged at DEBUG level
- Errors logged at ERROR level
- Heartbeat responses logged at DEBUG level

## Best Practices

1. **Client-side**:
   - Always handle connection state changes
   - Implement proper error handling
   - Use subscriptions to filter relevant messages
   - Queue non-critical messages during disconnections

2. **Server-side**:
   - Use subscription filters for targeted broadcasting
   - Implement proper error handling in message handlers
   - Monitor connection health with heartbeats
   - Clean up inactive connections regularly

3. **Message Design**:
   - Include timestamps in all messages
   - Use consistent message structure
   - Keep messages lightweight
   - Implement message versioning for future compatibility
