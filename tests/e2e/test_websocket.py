#!/usr/bin/env python3
"""
Test script for AndroidZen Pro WebSocket functionality.
Demonstrates sending various types of real-time updates.
"""

import asyncio
import json
import logging
from datetime import datetime
from backend.core.websocket_manager import WebSocketManager, MessageType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_functionality():
    """Test various WebSocket manager functions."""
    
    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()
    
    print("=== AndroidZen Pro WebSocket Test ===\n")
    
    # Test 1: Send device status update
    print("Test 1: Broadcasting device status...")
    device_data = [
        {
            "id": "test_device_1",
            "name": "Test Android Device",
            "status": "connected",
            "battery_level": 75,
            "cpu_usage": 25.5,
            "memory_usage": 58.2,
            "storage_usage": 68.9,
            "last_seen": datetime.utcnow().isoformat()
        }
    ]
    await websocket_manager.broadcast_device_status(device_data)
    print("✓ Device status broadcast sent\n")
    
    # Test 2: Send live metrics
    print("Test 2: Sending live performance metrics...")
    metrics = {
        "cpu_usage": 35.8,
        "memory_usage": 62.4,
        "disk_io": 12.3,
        "network_rx": 1024,
        "network_tx": 2048,
        "battery_temp": 32.5
    }
    await websocket_manager.send_live_metrics("test_device_1", metrics)
    print("✓ Live metrics sent\n")
    
    # Test 3: Send security alert
    print("Test 3: Sending security alert...")
    alert_details = {
        "type": "malware_detected",
        "severity": "high",
        "threat_name": "Android.Trojan.TestVirus",
        "file_path": "/system/test/malicious.apk",
        "action_taken": "quarantined"
    }
    await websocket_manager.send_security_alert("test_device_1", alert_details)
    print("✓ Security alert sent\n")
    
    # Test 4: Send notification
    print("Test 4: Sending notification...")
    await websocket_manager.send_notification(
        "system",
        "Test Notification",
        "This is a test notification from the WebSocket system",
        "info",
        device_id="test_device_1"
    )
    print("✓ Notification sent\n")
    
    # Test 5: Send device action status
    print("Test 5: Sending device action status...")
    await websocket_manager.send_device_action_status(
        "action_123",
        "test_device_1",
        "security_scan",
        "completed",
        {"threats_found": 0, "scan_duration": "2.5s"}
    )
    print("✓ Device action status sent\n")
    
    # Test 6: Broadcast performance data
    print("Test 6: Broadcasting performance data...")
    performance_data = {
        "overall_cpu": 28.7,
        "overall_memory": 55.2,
        "active_devices": 3,
        "network_throughput": 15.8,
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.broadcast_performance_data(performance_data)
    print("✓ Performance data broadcast sent\n")
    
    # Test 7: Start real-time monitoring
    print("Test 7: Starting real-time monitoring...")
    await websocket_manager.start_real_time_monitoring(
        "test_device_1",
        "performance",
        10  # 10 second intervals
    )
    print("✓ Real-time monitoring started\n")
    
    # Test 8: Get connection statistics
    print("Test 8: Getting connection statistics...")
    stats = websocket_manager.get_connection_stats()
    print(f"Connection Stats: {json.dumps(stats, indent=2)}\n")
    
    print("=== All WebSocket tests completed successfully! ===")

async def simulate_real_time_updates():
    """Simulate continuous real-time updates."""
    
    websocket_manager = WebSocketManager()
    
    print("Starting real-time update simulation...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Simulate changing metrics
            import random
            
            # Update device status
            device_data = {
                "id": "simulated_device",
                "name": "Simulated Android Device",
                "status": "connected",
                "battery_level": random.randint(20, 100),
                "cpu_usage": round(random.uniform(10, 80), 1),
                "memory_usage": round(random.uniform(30, 90), 1),
                "storage_usage": round(random.uniform(40, 95), 1),
                "last_seen": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.broadcast_device_status([device_data])
            
            # Send live metrics
            metrics = {
                "cpu_usage": round(random.uniform(10, 80), 1),
                "memory_usage": round(random.uniform(30, 90), 1),
                "disk_io": round(random.uniform(0, 100), 1),
                "network_rx": random.randint(100, 5000),
                "network_tx": random.randint(100, 5000),
                "battery_temp": round(random.uniform(25, 45), 1)
            }
            
            await websocket_manager.send_live_metrics("simulated_device", metrics)
            
            # Occasionally send alerts
            if random.random() < 0.1:  # 10% chance
                severity = random.choice(["low", "medium", "high"])
                await websocket_manager.send_notification(
                    "performance",
                    f"Performance Alert",
                    f"Device metrics showing {severity} priority issues",
                    severity,
                    device_id="simulated_device"
                )
            
            print(f"Sent update at {datetime.now().strftime('%H:%M:%S')} - "
                  f"CPU: {metrics['cpu_usage']}%, "
                  f"Memory: {metrics['memory_usage']}%, "
                  f"Battery: {device_data['battery_level']}%")
            
            await asyncio.sleep(2)  # Update every 2 seconds
            
    except KeyboardInterrupt:
        print("\nReal-time simulation stopped.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simulate":
        # Run continuous simulation
        asyncio.run(simulate_real_time_updates())
    else:
        # Run test suite
        asyncio.run(test_websocket_functionality())
