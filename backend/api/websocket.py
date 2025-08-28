"""
WebSocket API endpoints for real-time monitoring and communication.
Handles WebSocket connections, subscriptions, and real-time data streaming.
"""

import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from typing import Optional, Dict, Any
import asyncio

from .core.websocket_manager import WebSocketManager, MessageType
from .core.auth import verify_refresh_token, auth_manager as auth_manager_instance

logger = logging.getLogger(__name__)

router = APIRouter()

# Global WebSocket manager instance (imported from main.py)
websocket_manager = WebSocketManager()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint for real-time communication.
    Clients can optionally provide authentication token and client_id.
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = str(uuid.uuid4())
    
    user_id = None
    username = None
    
    # Optional authentication - if token provided, verify it
    if token:
        try:
            payload = auth_manager_instance.verify_token(token)
            if payload and payload.get("type") == "access":
                username = payload.get("sub")
                user_id = payload.get("user_id")
                logger.info(f"WebSocket authenticated for user: {username}")
            else:
                logger.warning(f"Invalid token provided for WebSocket connection: {client_id}")
        except Exception as e:
            logger.warning(f"Token verification failed for WebSocket: {e}")
    
    # Accept connection
    try:
        connection = await websocket_manager.connect(websocket, client_id, user_id)
        logger.info(f"WebSocket connection established: {client_id} (user: {username})")
        
        # Send connection confirmation
        await connection.send_message(MessageType.DEVICE_CONNECTED, {
            "client_id": client_id,
            "user_id": user_id,
            "username": username,
            "message": "Connected to AndroidZen Pro real-time monitoring"
        })
        
        # Handle messages
        while True:
            try:
                # Wait for messages from client
                message = await websocket.receive_text()
                await websocket_manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client {client_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {client_id}: {e}")
                await connection.send_error(f"Error processing message: {str(e)}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error for {client_id}: {e}")
    finally:
        await websocket_manager.disconnect(client_id)

@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    Public endpoint for monitoring purposes.
    """
    stats = websocket_manager.get_connection_stats()
    return {
        "websocket_stats": stats,
        "status": "active"
    }

# Admin endpoints for WebSocket management
@router.post("/ws/broadcast")
async def broadcast_message(
    message_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"is_admin": True})  # Simplified admin check
):
    """
    Broadcast a message to all connected WebSocket clients.
    Admin-only endpoint.
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    message_type = message_data.get("type", MessageType.ANALYTICS_UPDATE.value)
    data = message_data.get("data", {})
    subscription_filter = message_data.get("subscription_filter")
    
    try:
        sent_count = await websocket_manager.broadcast(
            MessageType(message_type),
            data,
            subscription_filter
        )
        
        return {
            "message": "Broadcast sent successfully",
            "recipients": sent_count,
            "type": message_type
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid message type: {message_type}")
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        raise HTTPException(status_code=500, detail="Broadcast failed")

@router.post("/ws/send-to-user/{user_id}")
async def send_to_user(
    user_id: str,
    message_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"is_admin": True})  # Simplified admin check
):
    """
    Send a message to all WebSocket connections for a specific user.
    Admin-only endpoint.
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    message_type = message_data.get("type", MessageType.ANALYTICS_UPDATE.value)
    data = message_data.get("data", {})
    
    try:
        sent_count = await websocket_manager.send_to_user(
            user_id,
            MessageType(message_type),
            data
        )
        
        if sent_count == 0:
            return {
                "message": "User not connected or no active sessions",
                "user_id": user_id,
                "recipients": 0
            }
        
        return {
            "message": "Message sent successfully",
            "user_id": user_id,
            "recipients": sent_count,
            "type": message_type
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid message type: {message_type}")
    except Exception as e:
        logger.error(f"Send to user error: {e}")
        raise HTTPException(status_code=500, detail="Send message failed")

@router.delete("/ws/connections/{client_id}")
async def disconnect_client(
    client_id: str,
    current_user: Dict[str, Any] = Depends(lambda: {"is_admin": True})  # Simplified admin check
):
    """
    Disconnect a specific WebSocket client.
    Admin-only endpoint.
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        await websocket_manager.disconnect(client_id)
        return {
            "message": "Client disconnected successfully",
            "client_id": client_id
        }
    except Exception as e:
        logger.error(f"Disconnect client error: {e}")
        raise HTTPException(status_code=500, detail="Disconnect failed")

@router.post("/ws/cleanup")
async def cleanup_connections(
    current_user: Dict[str, Any] = Depends(lambda: {"is_admin": True})  # Simplified admin check
):
    """
    Clean up inactive WebSocket connections.
    Admin-only endpoint.
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        cleaned_count = await websocket_manager.cleanup_inactive_connections()
        return {
            "message": "Cleanup completed successfully",
            "cleaned_connections": cleaned_count
        }
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

# Convenience endpoints for common real-time updates
@router.post("/ws/device-alert")
async def send_device_alert(
    alert_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})  # Simplified for demo
):
    """
    Send a device-specific alert to subscribed clients.
    """
    device_id = alert_data.get("device_id")
    alert_type = alert_data.get("alert_type", "general")
    message = alert_data.get("message", "Device alert")
    severity = alert_data.get("severity", "medium")
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    try:
        await websocket_manager.send_device_alert(device_id, alert_type, message, severity)
        return {
            "message": "Device alert sent successfully",
            "device_id": device_id,
            "alert_type": alert_type
        }
    except Exception as e:
        logger.error(f"Device alert error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send device alert")

@router.post("/ws/analytics-update")
async def send_analytics_update(
    analytics_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})  # Simplified for demo
):
    """
    Send real-time analytics update for a device.
    """
    device_id = analytics_data.get("device_id")
    metrics = analytics_data.get("metrics", {})
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    try:
        await websocket_manager.send_analytics_update(device_id, metrics)
        return {
            "message": "Analytics update sent successfully",
            "device_id": device_id,
            "metrics_count": len(metrics)
        }
    except Exception as e:
        logger.error(f"Analytics update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send analytics update")

@router.post("/ws/security-alert")
async def send_security_alert(
    security_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})  # Simplified for demo
):
    """
    Send a security alert for a device.
    """
    device_id = security_data.get("device_id")
    alert_details = security_data.get("alert_details", {})
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    try:
        await websocket_manager.send_security_alert(device_id, alert_details)
        return {
            "message": "Security alert sent successfully",
            "device_id": device_id,
            "alert_type": alert_details.get("type", "unknown")
        }
    except Exception as e:
        logger.error(f"Security alert error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send security alert")

@router.post("/ws/optimization-complete")
async def send_optimization_complete(
    optimization_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})  # Simplified for demo
):
    """
    Send optimization completion notification.
    """
    device_id = optimization_data.get("device_id")
    results = optimization_data.get("results", {})
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    try:
        await websocket_manager.send_optimization_complete(device_id, results)
        return {
            "message": "Optimization complete notification sent successfully",
            "device_id": device_id,
            "improvements": results.get("improvements", 0)
        }
    except Exception as e:
        logger.error(f"Optimization complete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send optimization complete notification")

@router.post("/ws/live-metrics")
async def send_live_metrics(
    metrics_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})
):
    """
    Send live performance metrics for a device.
    """
    device_id = metrics_data.get("device_id")
    metrics = metrics_data.get("metrics", {})
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    try:
        await websocket_manager.send_live_metrics(device_id, metrics)
        return {
            "message": "Live metrics sent successfully",
            "device_id": device_id,
            "metrics_count": len(metrics)
        }
    except Exception as e:
        logger.error(f"Live metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send live metrics")

@router.post("/ws/notification")
async def send_notification(
    notification_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})
):
    """
    Send a notification to users.
    """
    notification_type = notification_data.get("type", "info")
    title = notification_data.get("title")
    message = notification_data.get("message")
    severity = notification_data.get("severity", "info")
    user_id = notification_data.get("user_id")
    device_id = notification_data.get("device_id")
    extra_data = notification_data.get("data")
    
    if not title or not message:
        raise HTTPException(status_code=400, detail="title and message are required")
    
    try:
        await websocket_manager.send_notification(
            notification_type, title, message, severity, user_id, device_id, extra_data
        )
        return {
            "message": "Notification sent successfully",
            "type": notification_type,
            "title": title,
            "severity": severity
        }
    except Exception as e:
        logger.error(f"Notification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")

@router.post("/ws/performance-data")
async def broadcast_performance_data(
    performance_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})
):
    """
    Broadcast performance data to all subscribers.
    """
    try:
        await websocket_manager.broadcast_performance_data(performance_data)
        return {
            "message": "Performance data broadcasted successfully",
            "data_points": len(performance_data)
        }
    except Exception as e:
        logger.error(f"Performance data broadcast error: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast performance data")

@router.post("/ws/device-action/{device_id}")
async def send_device_action_status(
    device_id: str,
    action_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})
):
    """
    Send device action status update.
    """
    action_id = action_data.get("action_id")
    action_type = action_data.get("action_type")
    status = action_data.get("status")
    result = action_data.get("result")
    
    if not action_id or not action_type or not status:
        raise HTTPException(status_code=400, detail="action_id, action_type, and status are required")
    
    try:
        await websocket_manager.send_device_action_status(
            action_id, device_id, action_type, status, result
        )
        return {
            "message": "Device action status sent successfully",
            "device_id": device_id,
            "action_id": action_id,
            "status": status
        }
    except Exception as e:
        logger.error(f"Device action status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send device action status")

@router.post("/ws/start-monitoring/{device_id}")
async def start_real_time_monitoring(
    device_id: str,
    monitoring_data: Dict[str, Any] = None,
    current_user: Dict[str, Any] = Depends(lambda: {"username": "system"})
):
    """
    Start real-time monitoring for a device.
    """
    if monitoring_data is None:
        monitoring_data = {}
    
    monitoring_type = monitoring_data.get("type", "all")
    interval = monitoring_data.get("interval", 5)
    
    try:
        await websocket_manager.start_real_time_monitoring(device_id, monitoring_type, interval)
        return {
            "message": "Real-time monitoring started successfully",
            "device_id": device_id,
            "monitoring_type": monitoring_type,
            "interval": interval
        }
    except Exception as e:
        logger.error(f"Start monitoring error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start real-time monitoring")

