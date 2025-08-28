"""
WebSocket manager for real-time monitoring and bidirectional communication.
Handles device status updates, security alerts, and live analytics.
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import weakref
from enum import Enum

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """WebSocket message types."""
    DEVICE_STATUS = "device_status"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    ANALYTICS_UPDATE = "analytics_update"
    SECURITY_ALERT = "security_alert"
    OPTIMIZATION_COMPLETE = "optimization_complete"
    STORAGE_ALERT = "storage_alert"
    NETWORK_STATUS = "network_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    SUBSCRIPTION = "subscription"
    UNSUBSCRIPTION = "unsubscription"
    LIVE_METRICS = "live_metrics"
    NOTIFICATION = "notification"
    DEVICE_ACTION = "device_action"
    SYSTEM_MESSAGE = "system_message"
    PERFORMANCE_DATA = "performance_data"

class WebSocketConnection:
    """Represents a WebSocket connection with metadata."""
    
    def __init__(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None):
        self.websocket = websocket
        self.client_id = client_id
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.subscriptions: Set[str] = set()
        self.is_active = True
        
    async def send_message(self, message_type: MessageType, data: Dict[str, Any]):
        """Send a message to this WebSocket connection."""
        try:
            message = {
                "type": message_type.value,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            await self.websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message to client {self.client_id}: {e}")
            self.is_active = False
    
    async def send_error(self, error_message: str, error_code: Optional[str] = None):
        """Send an error message to this WebSocket connection."""
        await self.send_message(MessageType.ERROR, {
            "message": error_message,
            "code": error_code
        })
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()
    
    def add_subscription(self, subscription: str):
        """Add a subscription topic."""
        self.subscriptions.add(subscription)
        logger.info(f"Client {self.client_id} subscribed to {subscription}")
    
    def remove_subscription(self, subscription: str):
        """Remove a subscription topic."""
        self.subscriptions.discard(subscription)
        logger.info(f"Client {self.client_id} unsubscribed from {subscription}")
    
    def has_subscription(self, subscription: str) -> bool:
        """Check if client is subscribed to a topic."""
        return subscription in self.subscriptions

class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, List[str]] = {}  # user_id -> list of client_ids
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None) -> WebSocketConnection:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            connection = WebSocketConnection(websocket, client_id, user_id)
            self.connections[client_id] = connection
            
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = []
                self.user_connections[user_id].append(client_id)
            
            logger.info(f"WebSocket connected: client_id={client_id}, user_id={user_id}")
            return connection
    
    async def disconnect(self, client_id: str):
        """Disconnect a WebSocket connection."""
        async with self._lock:
            connection = self.connections.get(client_id)
            if connection:
                connection.is_active = False
                
                # Remove from user connections
                if connection.user_id and connection.user_id in self.user_connections:
                    if client_id in self.user_connections[connection.user_id]:
                        self.user_connections[connection.user_id].remove(client_id)
                    
                    # Clean up empty user connection list
                    if not self.user_connections[connection.user_id]:
                        del self.user_connections[connection.user_id]
                
                # Remove from main connections
                del self.connections[client_id]
                logger.info(f"WebSocket disconnected: client_id={client_id}")
    
    async def disconnect_all(self):
        """Disconnect all WebSocket connections."""
        async with self._lock:
            for connection in list(self.connections.values()):
                try:
                    await connection.websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket connection: {e}")
            
            self.connections.clear()
            self.user_connections.clear()
            logger.info("All WebSocket connections disconnected")
    
    async def send_to_client(self, client_id: str, message_type: MessageType, data: Dict[str, Any]) -> bool:
        """Send a message to a specific client."""
        connection = self.connections.get(client_id)
        if connection and connection.is_active:
            await connection.send_message(message_type, data)
            return True
        return False
    
    async def send_to_user(self, user_id: str, message_type: MessageType, data: Dict[str, Any]) -> int:
        """Send a message to all connections for a specific user."""
        sent_count = 0
        client_ids = self.user_connections.get(user_id, [])
        
        for client_id in client_ids.copy():  # Copy to avoid modification during iteration
            if await self.send_to_client(client_id, message_type, data):
                sent_count += 1
        
        return sent_count
    
    async def broadcast(self, message_type: MessageType, data: Dict[str, Any], subscription_filter: Optional[str] = None):
        """Broadcast a message to all connected clients or filtered by subscription."""
        sent_count = 0
        
        for connection in list(self.connections.values()):
            if not connection.is_active:
                continue
                
            # Filter by subscription if specified
            if subscription_filter and not connection.has_subscription(subscription_filter):
                continue
            
            try:
                await connection.send_message(message_type, data)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to client {connection.client_id}: {e}")
                connection.is_active = False
        
        logger.debug(f"Broadcast sent to {sent_count} clients")
        return sent_count
    
    async def handle_client_message(self, client_id: str, message: str):
        """Handle incoming message from a client."""
        connection = self.connections.get(client_id)
        if not connection:
            return
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            payload = data.get("data", {})
            
            if message_type == MessageType.HEARTBEAT.value:
                connection.update_heartbeat()
                await connection.send_message(MessageType.HEARTBEAT, {"status": "alive"})
            
            elif message_type == MessageType.SUBSCRIPTION.value:
                subscription = payload.get("topic")
                if subscription:
                    connection.add_subscription(subscription)
                    await connection.send_message(MessageType.SUBSCRIPTION, {
                        "topic": subscription,
                        "status": "subscribed"
                    })
            
            elif message_type == MessageType.UNSUBSCRIPTION.value:
                subscription = payload.get("topic")
                if subscription:
                    connection.remove_subscription(subscription)
                    await connection.send_message(MessageType.UNSUBSCRIPTION, {
                        "topic": subscription,
                        "status": "unsubscribed"
                    })
            
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
                await connection.send_error(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError:
            await connection.send_error("Invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
            await connection.send_error("Internal server error")
    
    async def cleanup_inactive_connections(self):
        """Clean up inactive connections (call periodically)."""
        inactive_clients = []
        current_time = datetime.utcnow()
        
        for client_id, connection in self.connections.items():
            # Consider connection inactive if no heartbeat for 5 minutes
            if (current_time - connection.last_heartbeat).total_seconds() > 300:
                inactive_clients.append(client_id)
                logger.warning(f"Connection {client_id} appears inactive, marking for cleanup")
        
        for client_id in inactive_clients:
            await self.disconnect(client_id)
        
        return len(inactive_clients)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about WebSocket connections."""
        active_connections = sum(1 for conn in self.connections.values() if conn.is_active)
        total_users = len(self.user_connections)
        
        # Count subscriptions
        subscription_counts = {}
        for connection in self.connections.values():
            for subscription in connection.subscriptions:
                subscription_counts[subscription] = subscription_counts.get(subscription, 0) + 1
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "total_users": total_users,
            "subscription_counts": subscription_counts,
            "average_subscriptions_per_client": (
                sum(len(conn.subscriptions) for conn in self.connections.values()) / 
                len(self.connections) if self.connections else 0
            )
        }
    
    # Device-specific broadcast methods
    async def broadcast_device_status(self, device_data=None):
        """Broadcast device status updates to subscribed clients.
        
        Args:
            device_data (dict, optional): Actual device data to broadcast. If None, mock data will be used.
        """
        if device_data is None:
            # In a real implementation, this would fetch actual device data from a database or service
            # For now, we'll send mock data
            device_status = {
                "devices": [
                    {
                        "id": "device_1",
                        "name": "Samsung Galaxy S21",
                        "status": "connected",
                        "battery_level": 85,
                        "cpu_usage": 23.5,
                        "memory_usage": 67.2,
                        "storage_usage": 78.9
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            device_status = {
                "devices": device_data if isinstance(device_data, list) else [device_data],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        await self.broadcast(
            MessageType.DEVICE_STATUS,
            device_status,
            subscription_filter="device_status"
        )
    
    async def send_device_alert(self, device_id: str, alert_type: str, message: str, severity: str = "medium"):
        """Send a device-specific alert."""
        alert_data = {
            "device_id": device_id,
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(
            MessageType.SECURITY_ALERT if alert_type == "security" else MessageType.ANALYTICS_UPDATE,
            alert_data,
            subscription_filter=f"device_{device_id}"
        )
    
    async def send_analytics_update(self, device_id: str, metrics: Dict[str, Any]):
        """Send real-time analytics update for a device."""
        analytics_data = {
            "device_id": device_id,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(
            MessageType.ANALYTICS_UPDATE,
            analytics_data,
            subscription_filter="analytics"
        )
    
    async def send_security_alert(self, device_id: str, alert_details: Dict[str, Any]):
        """Send a security alert for a device."""
        security_data = {
            "device_id": device_id,
            "alert_details": alert_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(
            MessageType.SECURITY_ALERT,
            security_data,
            subscription_filter="security"
        )
    
    async def send_optimization_complete(self, device_id: str, optimization_results: Dict[str, Any]):
        """Send optimization completion notification."""
        optimization_data = {
            "device_id": device_id,
            "results": optimization_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(
            MessageType.OPTIMIZATION_COMPLETE,
            optimization_data,
            subscription_filter=f"device_{device_id}"
        )
    
    async def send_live_metrics(self, device_id: str, metrics_data: Dict[str, Any]):
        """Send live performance metrics for a device.
        
        Args:
            device_id (str): The ID of the device
            metrics_data (Dict[str, Any]): Live metrics data including CPU, memory, network, etc.
        """
        live_data = {
            "device_id": device_id,
            "metrics": metrics_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to device-specific subscribers and to metrics subscribers
        await self.broadcast(
            MessageType.LIVE_METRICS,
            live_data,
            subscription_filter=f"metrics_{device_id}"
        )
    
    async def send_notification(self, notification_type: str, title: str, message: str, 
                               severity: str = "info", user_id: Optional[str] = None, 
                               device_id: Optional[str] = None, extra_data: Optional[Dict[str, Any]] = None):
        """Send a notification to specific users or broadcast to all.
        
        Args:
            notification_type (str): Type of notification (e.g., 'security', 'performance', 'system')
            title (str): Notification title
            message (str): Notification message body
            severity (str): Severity level ('info', 'warning', 'error', 'critical')
            user_id (Optional[str]): If specified, send only to this user
            device_id (Optional[str]): If specified, related device ID
            extra_data (Optional[Dict[str, Any]]): Any additional data to include
        """
        notification_data = {
            "id": f"notification_{int(datetime.utcnow().timestamp() * 1000)}",
            "type": notification_type,
            "title": title,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "read": False
        }
        
        if device_id:
            notification_data["device_id"] = device_id
        
        if extra_data:
            notification_data["data"] = extra_data
        
        if user_id:
            # Send to specific user
            await self.send_to_user(user_id, MessageType.NOTIFICATION, notification_data)
        else:
            # Broadcast to all subscribers
            await self.broadcast(
                MessageType.NOTIFICATION,
                notification_data,
                subscription_filter="notifications"
            )
    
    async def broadcast_performance_data(self, performance_data: Dict[str, Any]):
        """Broadcast performance data to all subscribers.
        
        Args:
            performance_data (Dict[str, Any]): Performance metrics to broadcast
        """
        data = {
            "performance": performance_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(
            MessageType.PERFORMANCE_DATA,
            data,
            subscription_filter="performance"
        )
        
    async def send_device_action_status(self, action_id: str, device_id: str, action_type: str, 
                                      status: str, result: Optional[Dict[str, Any]] = None):
        """Send status update for a device action.
        
        Args:
            action_id (str): Unique ID for the action
            device_id (str): The device ID
            action_type (str): Type of action (e.g., 'scan', 'optimize', 'update')
            status (str): Status of the action ('queued', 'in_progress', 'completed', 'failed')
            result (Optional[Dict[str, Any]]): Optional result data if the action is complete
        """
        action_data = {
            "action_id": action_id,
            "device_id": device_id,
            "action_type": action_type,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if result is not None:
            action_data["result"] = result
        
        # Send to specific device subscribers
        await self.broadcast(
            MessageType.DEVICE_ACTION,
            action_data,
            subscription_filter=f"device_{device_id}"
        )
        
    async def start_real_time_monitoring(self, device_id: str, monitoring_type: str = "all", 
                                       interval: int = 5):
        """Start real-time monitoring for a specific device.
        This is a placeholder implementation that would be connected to actual device monitoring.
        
        Args:
            device_id (str): The ID of the device to monitor
            monitoring_type (str): Type of monitoring ('all', 'performance', 'network', etc.)
            interval (int): Interval in seconds between updates
        """
        # In a real implementation, this would connect to a real monitoring service
        # and establish a data stream. For now, we'll just log it.
        logger.info(f"Started real-time monitoring for device {device_id}, type: {monitoring_type}, interval: {interval}s")
        
        # Return a response to subscribers that monitoring has started
        await self.broadcast(
            MessageType.SYSTEM_MESSAGE,
            {
                "message": f"Real-time monitoring started for device {device_id}",
                "device_id": device_id,
                "monitoring_type": monitoring_type,
                "interval": interval,
                "timestamp": datetime.utcnow().isoformat()
            },
            subscription_filter=f"device_{device_id}"
        )
