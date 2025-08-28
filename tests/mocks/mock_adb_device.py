"""
Mock ADB Device implementation for testing AndroidZen Pro without physical devices.
"""

import asyncio
import random
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from enum import Enum

from backend.core.adb_manager import DeviceStatus, ConnectionType, DeviceInfo


class MockDeviceState(Enum):
    """Mock device states for simulation"""
    NORMAL = "normal"
    HIGH_CPU = "high_cpu"
    LOW_BATTERY = "low_battery"
    HIGH_TEMPERATURE = "high_temperature"
    LOW_STORAGE = "low_storage"
    NETWORK_ISSUES = "network_issues"


@dataclass
class MockAppInfo:
    """Mock app information"""
    package_name: str
    app_name: str
    version: str
    is_system: bool = False
    permissions: List[str] = field(default_factory=list)
    data_usage: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


class MockADBDevice:
    """
    Mock ADB device that simulates Android device behavior for testing.
    """
    
    def __init__(self, 
                 device_id: str,
                 model: str = "TestDevice",
                 android_version: str = "13",
                 is_connected: bool = True,
                 simulate_issues: bool = False):
        """
        Initialize mock ADB device.
        
        Args:
            device_id: Unique device identifier
            model: Device model name
            android_version: Android version
            is_connected: Initial connection status
            simulate_issues: Whether to simulate device issues
        """
        self.device_id = device_id
        self.model = model
        self.android_version = android_version
        self.is_connected = is_connected
        self.simulate_issues = simulate_issues
        
        # Device state
        self.state = MockDeviceState.NORMAL
        self.last_update = time.time()
        
        # Device specs
        self.total_storage = random.randint(32000, 512000)  # MB
        self.total_memory = random.randint(4096, 16384)  # MB
        self.cpu_cores = random.randint(4, 8)
        
        # Current metrics (will be updated dynamically)
        self._init_metrics()
        
        # Apps
        self.installed_apps: Dict[str, MockAppInfo] = {}
        self._init_sample_apps()
        
        # Security
        self.security_events: List[Dict] = []
        self.permissions: List[str] = []
        
        # Background simulation
        self._simulation_thread = None
        self._stop_simulation = threading.Event()
        
        if simulate_issues:
            self.start_simulation()
    
    def _init_metrics(self):
        """Initialize device metrics."""
        self.cpu_usage = random.uniform(10, 30)
        self.memory_usage = random.uniform(40, 70)
        self.storage_used = random.uniform(30, 80)
        self.battery_level = random.randint(20, 100)
        self.battery_temperature = random.uniform(25, 35)
        self.cpu_temperature = random.uniform(35, 45)
        self.network_strength = random.randint(-80, -30)
        self.running_processes = random.randint(80, 150)
    
    def _init_sample_apps(self):
        """Initialize sample applications."""
        sample_apps = [
            MockAppInfo("com.android.chrome", "Chrome", "108.0.5359", False, 
                       ["INTERNET", "CAMERA", "MICROPHONE"]),
            MockAppInfo("com.whatsapp", "WhatsApp", "2.23.1", False,
                       ["INTERNET", "CAMERA", "MICROPHONE", "CONTACTS"]),
            MockAppInfo("com.android.settings", "Settings", "13.0", True, 
                       ["MODIFY_AUDIO_SETTINGS", "WRITE_SETTINGS"]),
            MockAppInfo("com.google.android.gms", "Google Play Services", "22.45.14", True,
                       ["INTERNET", "ACCESS_FINE_LOCATION", "READ_CONTACTS"]),
            MockAppInfo("com.spotify.music", "Spotify", "8.7.76", False,
                       ["INTERNET", "WRITE_EXTERNAL_STORAGE", "RECORD_AUDIO"])
        ]
        
        for app in sample_apps:
            app.data_usage = random.uniform(10, 500)  # MB
            app.cpu_usage = random.uniform(0.1, 5.0)  # %
            app.memory_usage = random.uniform(50, 300)  # MB
            self.installed_apps[app.package_name] = app
    
    def start_simulation(self):
        """Start background simulation of device behavior."""
        if self._simulation_thread and self._simulation_thread.is_alive():
            return
        
        self._stop_simulation.clear()
        self._simulation_thread = threading.Thread(
            target=self._simulate_device_behavior,
            daemon=True
        )
        self._simulation_thread.start()
    
    def stop_simulation(self):
        """Stop background simulation."""
        self._stop_simulation.set()
        if self._simulation_thread:
            self._simulation_thread.join(timeout=1)
    
    def _simulate_device_behavior(self):
        """Simulate dynamic device behavior."""
        while not self._stop_simulation.is_set():
            try:
                self._update_metrics()
                self._simulate_state_changes()
                self._simulate_security_events()
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                print(f"Error in device simulation: {e}")
                time.sleep(1)
    
    def _update_metrics(self):
        """Update device metrics based on current state."""
        # Base fluctuation
        self.cpu_usage += random.uniform(-5, 5)
        self.memory_usage += random.uniform(-2, 2)
        self.network_strength += random.randint(-5, 5)
        self.running_processes += random.randint(-5, 5)
        
        # State-based modifications
        if self.state == MockDeviceState.HIGH_CPU:
            self.cpu_usage = max(80, self.cpu_usage + 20)
            self.cpu_temperature += random.uniform(2, 5)
        elif self.state == MockDeviceState.LOW_BATTERY:
            self.battery_level = max(5, self.battery_level - 1)
        elif self.state == MockDeviceState.HIGH_TEMPERATURE:
            self.cpu_temperature = max(60, self.cpu_temperature + 5)
            self.battery_temperature = max(40, self.battery_temperature + 3)
        elif self.state == MockDeviceState.LOW_STORAGE:
            self.storage_used = min(95, self.storage_used + 1)
        elif self.state == MockDeviceState.NETWORK_ISSUES:
            self.network_strength = min(-75, self.network_strength - 10)
        
        # Clamp values
        self.cpu_usage = max(0, min(100, self.cpu_usage))
        self.memory_usage = max(0, min(100, self.memory_usage))
        self.battery_level = max(0, min(100, self.battery_level))
        self.network_strength = max(-100, min(-20, self.network_strength))
        self.running_processes = max(50, min(200, self.running_processes))
        self.cpu_temperature = max(25, min(80, self.cpu_temperature))
        self.battery_temperature = max(20, min(50, self.battery_temperature))
        
        self.last_update = time.time()
    
    def _simulate_state_changes(self):
        """Simulate device state changes."""
        if random.random() < 0.1:  # 10% chance of state change
            states = list(MockDeviceState)
            self.state = random.choice(states)
    
    def _simulate_security_events(self):
        """Simulate security events."""
        if random.random() < 0.05:  # 5% chance of security event
            event_types = [
                "malware_detected", "suspicious_permission", "root_access_attempt",
                "unauthorized_app_install", "security_patch_needed"
            ]
            
            event = {
                "timestamp": datetime.now(),
                "event_type": random.choice(event_types),
                "severity": random.choice(["low", "medium", "high", "critical"]),
                "description": f"Simulated security event: {random.choice(event_types)}",
                "source_app": random.choice(list(self.installed_apps.keys())),
                "resolved": False
            }
            
            self.security_events.append(event)
    
    # Mock ADB command implementations
    async def shell(self, command: str, timeout: int = 30) -> str:
        """Mock shell command execution."""
        await asyncio.sleep(0.1)  # Simulate command execution time
        
        if not self.is_connected:
            raise Exception("Device not connected")
        
        # Simulate common ADB shell commands
        if command == "getprop ro.build.version.release":
            return self.android_version
        elif command == "getprop ro.product.model":
            return self.model
        elif command.startswith("dumpsys battery"):
            return f"level: {self.battery_level}\ntemperature: {int(self.battery_temperature * 10)}"
        elif command.startswith("dumpsys cpuinfo"):
            return f"Total CPU usage: {self.cpu_usage:.1f}%"
        elif command.startswith("dumpsys meminfo"):
            used_memory = (self.memory_usage / 100) * self.total_memory
            return f"Total RAM: {self.total_memory}MB\nUsed: {used_memory:.0f}MB"
        elif command == "df /data":
            used_storage = (self.storage_used / 100) * self.total_storage
            available = self.total_storage - used_storage
            return f"/data {self.total_storage}M {used_storage:.0f}M {available:.0f}M"
        elif command == "ps":
            processes = []
            for i in range(self.running_processes):
                processes.append(f"user {1000 + i} 0.0 0.1 process{i}")
            return "\n".join(processes)
        elif command.startswith("pm list packages"):
            return "\n".join([f"package:{pkg}" for pkg in self.installed_apps.keys()])
        elif command.startswith("dumpsys wifi"):
            return f"Wi-Fi is enabled\nRSSI: {self.network_strength} dBm"
        else:
            return f"Mock response for: {command}"
    
    def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            device_id=self.device_id,
            connection_type=ConnectionType.USB,
            status=DeviceStatus.CONNECTED if self.is_connected else DeviceStatus.DISCONNECTED,
            model=self.model,
            android_version=self.android_version,
            last_seen=self.last_update
        )
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current device metrics."""
        return {
            "device_id": self.device_id,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "storage_usage_percentage": self.storage_used,
            "battery_level": self.battery_level,
            "battery_temperature": self.battery_temperature,
            "cpu_temperature": self.cpu_temperature,
            "network_strength": self.network_strength,
            "running_processes": self.running_processes,
            "timestamp": self.last_update
        }
    
    def get_installed_apps(self) -> List[MockAppInfo]:
        """Get list of installed applications."""
        return list(self.installed_apps.values())
    
    def get_security_events(self) -> List[Dict]:
        """Get security events."""
        return self.security_events.copy()
    
    def connect(self) -> bool:
        """Simulate device connection."""
        self.is_connected = True
        return True
    
    def disconnect(self):
        """Simulate device disconnection."""
        self.is_connected = False
        self.stop_simulation()


class MockADBManager:
    """
    Mock ADB Manager that manages multiple mock devices.
    """
    
    def __init__(self):
        """Initialize mock ADB manager."""
        self.devices: Dict[str, MockADBDevice] = {}
        self.callbacks: Dict[str, List[Callable]] = {
            "device_connected": [],
            "device_disconnected": []
        }
    
    def add_device(self, device: MockADBDevice):
        """Add a mock device to the manager."""
        self.devices[device.device_id] = device
        if device.is_connected:
            self._trigger_callback("device_connected", device.device_id)
    
    def remove_device(self, device_id: str):
        """Remove a device from the manager."""
        if device_id in self.devices:
            device = self.devices[device_id]
            device.stop_simulation()
            self._trigger_callback("device_disconnected", device_id)
            del self.devices[device_id]
    
    def get_device(self, device_id: str) -> Optional[MockADBDevice]:
        """Get a specific device."""
        return self.devices.get(device_id)
    
    def get_connected_devices(self) -> List[MockADBDevice]:
        """Get all connected devices."""
        return [device for device in self.devices.values() if device.is_connected]
    
    def get_all_devices(self) -> List[MockADBDevice]:
        """Get all devices (connected and disconnected)."""
        return list(self.devices.values())
    
    async def execute_command(self, device_id: str, command: str, timeout: int = 30) -> str:
        """Execute command on specific device."""
        device = self.get_device(device_id)
        if not device:
            raise Exception(f"Device {device_id} not found")
        
        return await device.shell(command, timeout)
    
    def add_callback(self, event: str, callback: Callable):
        """Add callback for device events."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def _trigger_callback(self, event: str, device_id: str):
        """Trigger callbacks for device events."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(device_id)
            except Exception as e:
                print(f"Error in callback for {event}: {e}")
    
    def simulate_device_connection(self, device_id: str):
        """Simulate device connection."""
        device = self.get_device(device_id)
        if device:
            device.connect()
            self._trigger_callback("device_connected", device_id)
    
    def simulate_device_disconnection(self, device_id: str):
        """Simulate device disconnection."""
        device = self.get_device(device_id)
        if device:
            device.disconnect()
            self._trigger_callback("device_disconnected", device_id)
    
    def cleanup(self):
        """Cleanup all devices and stop simulations."""
        for device in self.devices.values():
            device.stop_simulation()
        self.devices.clear()


def create_test_devices(count: int = 3, simulate_issues: bool = True) -> List[MockADBDevice]:
    """
    Create multiple test devices for testing.
    
    Args:
        count: Number of devices to create
        simulate_issues: Whether devices should simulate issues
        
    Returns:
        List of mock ADB devices
    """
    devices = []
    models = ["Samsung Galaxy S21", "Google Pixel 7", "OnePlus 10", "Xiaomi 12", "iPhone 14"]
    android_versions = ["11", "12", "13", "14"]
    
    for i in range(count):
        device_id = f"test_device_{i:03d}"
        model = random.choice(models)
        android_version = random.choice(android_versions)
        is_connected = random.choice([True, True, True, False])  # 75% connected
        
        device = MockADBDevice(
            device_id=device_id,
            model=model,
            android_version=android_version,
            is_connected=is_connected,
            simulate_issues=simulate_issues
        )
        
        devices.append(device)
    
    return devices
