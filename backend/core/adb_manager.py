"""
ADB Connection Manager for Android Device Communication

This module provides comprehensive ADB connection handling including:
- USB and WiFi connection methods
- Device discovery and auto-reconnection logic
- Device status monitoring with heartbeat checks
- Safe ADB command execution wrapper
- Error handling and logging for connection issues
"""

import asyncio
import logging
import threading
import time
import subprocess
import socket
import re
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from adb_shell.adb_device import AdbDeviceTcp, AdbDeviceUsb
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_cryptography import CryptographySigner
from adb_shell.exceptions import (
    AdbConnectionError,
    AdbTimeoutError,
    AdbCommandFailureException
)


class ConnectionType(Enum):
    """ADB connection types"""
    USB = "usb"
    WIFI = "wifi"
    UNKNOWN = "unknown"


class DeviceStatus(Enum):
    """Device connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    BOOTLOADER = "bootloader"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """Device information container"""
    device_id: str
    connection_type: ConnectionType
    host: Optional[str] = None
    port: Optional[int] = None
    status: DeviceStatus = DeviceStatus.UNKNOWN
    model: Optional[str] = None
    android_version: Optional[str] = None
    last_seen: Optional[float] = None


@dataclass
class AdbCommand:
    """ADB command container"""
    command: str
    timeout: int = 30
    check_return_code: bool = True
    retries: int = 3


class AdbManager:
    """
    Comprehensive ADB connection manager for Android device communication
    """
    
    def __init__(self, 
                 heartbeat_interval: int = 30,
                 reconnection_interval: int = 5,
                 command_timeout: int = 30,
                 max_retries: int = 3,
                 auto_connect: bool = True):
        """
        Initialize ADB Manager
        
        Args:
            heartbeat_interval: Seconds between heartbeat checks
            reconnection_interval: Seconds between reconnection attempts
            command_timeout: Default command timeout in seconds
            max_retries: Maximum command retry attempts
            auto_connect: Enable automatic device connection
        """
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Configuration
        self.heartbeat_interval = heartbeat_interval
        self.reconnection_interval = reconnection_interval
        self.command_timeout = command_timeout
        self.max_retries = max_retries
        self.auto_connect = auto_connect
        
        # Device management
        self.devices: Dict[str, DeviceInfo] = {}
        self.connections: Dict[str, Any] = {}  # AdbDevice instances
        self.device_locks: Dict[str, threading.Lock] = {}
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ADB")
        self._shutdown_event = threading.Event()
        self._monitor_thread = None
        
        # Callbacks
        self.device_connected_callbacks: List[Callable[[str], None]] = []
        self.device_disconnected_callbacks: List[Callable[[str], None]] = []
        
        # Authentication
        self._setup_auth()
        
        if self.auto_connect:
            self.start_monitoring()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _setup_auth(self):
        """Setup ADB authentication"""
        try:
            # Generate RSA key pair for ADB authentication
            self.private_key, self.public_key = keygen()
            self.signer = CryptographySigner(self.private_key)
            self.logger.info("ADB authentication setup completed")
        except Exception as e:
            self.logger.error(f"Failed to setup ADB authentication: {e}")
            self.signer = None
    
    def start_monitoring(self):
        """Start device monitoring and heartbeat checking"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self.logger.warning("Monitoring already started")
            return
        
        self._shutdown_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_devices,
            daemon=True,
            name="ADB-Monitor"
        )
        self._monitor_thread.start()
        self.logger.info("Started ADB device monitoring")
    
    def stop_monitoring(self):
        """Stop device monitoring"""
        self._shutdown_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Stopped ADB device monitoring")
    
    def _monitor_devices(self):
        """Main monitoring loop for device discovery and heartbeat"""
        last_discovery = 0
        discovery_interval = 10  # Discover devices every 10 seconds
        
        while not self._shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # Periodic device discovery
                if current_time - last_discovery >= discovery_interval:
                    self._discover_devices()
                    last_discovery = current_time
                
                # Heartbeat check for connected devices
                self._check_device_heartbeats()
                
                # Attempt reconnection for disconnected devices
                self._attempt_reconnections()
                
                time.sleep(min(self.heartbeat_interval, self.reconnection_interval))
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def _discover_devices(self):
        """Discover available ADB devices"""
        try:
            # Get devices from adb command
            result = subprocess.run(
                ['adb', 'devices', '-l'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.logger.warning(f"ADB devices command failed: {result.stderr}")
                return
            
            current_devices = set()
            
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                device_id = parts[0]
                status_str = parts[1]
                current_devices.add(device_id)
                
                # Parse device status
                status = self._parse_device_status(status_str)
                
                # Determine connection type and details
                conn_type, host, port = self._parse_device_connection(device_id, line)
                
                # Update or create device info
                if device_id not in self.devices:
                    device_info = DeviceInfo(
                        device_id=device_id,
                        connection_type=conn_type,
                        host=host,
                        port=port,
                        status=status,
                        last_seen=time.time()
                    )
                    self.devices[device_id] = device_info
                    self.device_locks[device_id] = threading.Lock()
                    self.logger.info(f"Discovered new device: {device_id} ({conn_type.value})")
                else:
                    self.devices[device_id].status = status
                    self.devices[device_id].last_seen = time.time()
                
                # Auto-connect if enabled and device is ready
                if (self.auto_connect and 
                    status == DeviceStatus.CONNECTED and 
                    device_id not in self.connections):
                    asyncio.create_task(self._connect_device(device_id))
            
            # Handle disconnected devices
            for device_id in list(self.devices.keys()):
                if device_id not in current_devices:
                    self._handle_device_disconnection(device_id)
                    
        except subprocess.TimeoutExpired:
            self.logger.warning("ADB devices discovery timed out")
        except Exception as e:
            self.logger.error(f"Error discovering devices: {e}")
    
    def _parse_device_status(self, status_str: str) -> DeviceStatus:
        """Parse device status from adb output"""
        status_map = {
            'device': DeviceStatus.CONNECTED,
            'unauthorized': DeviceStatus.UNAUTHORIZED,
            'offline': DeviceStatus.OFFLINE,
            'bootloader': DeviceStatus.BOOTLOADER,
            'recovery': DeviceStatus.RECOVERY,
        }
        return status_map.get(status_str.lower(), DeviceStatus.UNKNOWN)
    
    def _parse_device_connection(self, device_id: str, line: str) -> Tuple[ConnectionType, Optional[str], Optional[int]]:
        """Parse connection type and details from device line"""
        if ':' in device_id and not device_id.startswith('emulator'):
            # WiFi connection (IP:PORT format)
            try:
                host, port_str = device_id.split(':')
                port = int(port_str)
                return ConnectionType.WIFI, host, port
            except ValueError:
                pass
        
        # Check for transport info in the line
        if 'transport:' in line:
            if 'transport:usb' in line:
                return ConnectionType.USB, None, None
            elif 'transport:tcp' in line:
                return ConnectionType.WIFI, None, None
        
        # Default based on device_id format
        if ':' in device_id:
            return ConnectionType.WIFI, None, None
        else:
            return ConnectionType.USB, None, None
    
    def _check_device_heartbeats(self):
        """Check heartbeat status of connected devices"""
        for device_id, connection in list(self.connections.items()):
            try:
                with self.device_locks[device_id]:
                    # Simple heartbeat: check if device is still responsive
                    result = connection.shell("echo 'heartbeat'", timeout_s=5)
                    if result and 'heartbeat' in result:
                        self.devices[device_id].last_seen = time.time()
                    else:
                        raise AdbConnectionError("Heartbeat failed")
                        
            except Exception as e:
                self.logger.warning(f"Heartbeat failed for device {device_id}: {e}")
                self._handle_device_disconnection(device_id)
    
    def _attempt_reconnections(self):
        """Attempt to reconnect to disconnected devices"""
        for device_id, device_info in self.devices.items():
            if (device_info.status == DeviceStatus.CONNECTED and 
                device_id not in self.connections):
                try:
                    asyncio.create_task(self._connect_device(device_id))
                except Exception as e:
                    self.logger.debug(f"Reconnection attempt failed for {device_id}: {e}")
    
    async def _connect_device(self, device_id: str) -> bool:
        """Connect to a specific device"""
        if device_id not in self.devices:
            self.logger.error(f"Device {device_id} not found")
            return False
        
        device_info = self.devices[device_id]
        
        try:
            with self.device_locks[device_id]:
                if device_id in self.connections:
                    self.logger.debug(f"Device {device_id} already connected")
                    return True
                
                # Create appropriate connection
                if device_info.connection_type == ConnectionType.USB:
                    connection = AdbDeviceUsb()
                elif device_info.connection_type == ConnectionType.WIFI:
                    if device_info.host and device_info.port:
                        host, port = device_info.host, device_info.port
                    else:
                        # Parse from device_id
                        host, port = device_id.split(':')
                        port = int(port)
                    
                    connection = AdbDeviceTcp(host, port, default_timeout_s=self.command_timeout)
                else:
                    self.logger.error(f"Unknown connection type for device {device_id}")
                    return False
                
                # Connect with authentication
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: connection.connect(rsa_keys=[self.signer] if self.signer else None)
                )
                
                self.connections[device_id] = connection
                
                # Get device properties
                await self._update_device_properties(device_id)
                
                self.logger.info(f"Successfully connected to device {device_id}")
                
                # Notify callbacks
                for callback in self.device_connected_callbacks:
                    try:
                        callback(device_id)
                    except Exception as e:
                        self.logger.error(f"Error in device connected callback: {e}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to connect to device {device_id}: {e}")
            return False
    
    async def _update_device_properties(self, device_id: str):
        """Update device properties after connection"""
        if device_id not in self.connections:
            return
        
        try:
            connection = self.connections[device_id]
            
            # Get device model
            model_result = await self.execute_command(
                device_id, 
                "getprop ro.product.model",
                timeout=10
            )
            if model_result.success:
                self.devices[device_id].model = model_result.output.strip()
            
            # Get Android version
            version_result = await self.execute_command(
                device_id,
                "getprop ro.build.version.release",
                timeout=10
            )
            if version_result.success:
                self.devices[device_id].android_version = version_result.output.strip()
                
        except Exception as e:
            self.logger.debug(f"Failed to update properties for device {device_id}: {e}")
    
    def _handle_device_disconnection(self, device_id: str):
        """Handle device disconnection"""
        if device_id in self.connections:
            try:
                with self.device_locks[device_id]:
                    connection = self.connections.pop(device_id)
                    connection.close()
            except Exception as e:
                self.logger.error(f"Error closing connection for device {device_id}: {e}")
            
            self.logger.info(f"Device {device_id} disconnected")
            
            # Notify callbacks
            for callback in self.device_disconnected_callbacks:
                try:
                    callback(device_id)
                except Exception as e:
                    self.logger.error(f"Error in device disconnected callback: {e}")
    
    # Public API Methods
    
    def get_connected_devices(self) -> List[str]:
        """Get list of connected device IDs"""
        return list(self.connections.keys())
    
    def get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device information"""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> Dict[str, DeviceInfo]:
        """Get all discovered devices"""
        return self.devices.copy()
    
    def is_device_connected(self, device_id: str) -> bool:
        """Check if device is connected"""
        return device_id in self.connections
    
    async def connect_device_wifi(self, host: str, port: int = 5555) -> Optional[str]:
        """
        Connect to device via WiFi
        
        Args:
            host: Device IP address
            port: ADB port (default 5555)
            
        Returns:
            Device ID if successful, None otherwise
        """
        device_id = f"{host}:{port}"
        
        try:
            # First, try to connect via adb connect command
            result = subprocess.run(
                ['adb', 'connect', device_id],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and 'connected' in result.stdout.lower():
                # Wait a moment for the device to appear
                await asyncio.sleep(2)
                
                # Trigger device discovery
                self._discover_devices()
                
                # Attempt direct connection
                if await self._connect_device(device_id):
                    return device_id
            else:
                self.logger.warning(f"ADB connect failed: {result.stdout} {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"WiFi connection to {device_id} timed out")
        except Exception as e:
            self.logger.error(f"WiFi connection error: {e}")
        
        return None
    
    async def disconnect_device(self, device_id: str) -> bool:
        """
        Disconnect from a specific device
        
        Args:
            device_id: Device to disconnect
            
        Returns:
            True if successful
        """
        if device_id not in self.connections:
            return True
        
        try:
            self._handle_device_disconnection(device_id)
            
            # For WiFi connections, also run adb disconnect
            if device_id in self.devices:
                device_info = self.devices[device_id]
                if device_info.connection_type == ConnectionType.WIFI:
                    subprocess.run(['adb', 'disconnect', device_id], timeout=10)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting device {device_id}: {e}")
            return False
    
    @dataclass
    class CommandResult:
        """Command execution result"""
        success: bool
        output: str = ""
        error: str = ""
        return_code: int = 0
        execution_time: float = 0.0
    
    async def execute_command(self, 
                            device_id: str, 
                            command: str,
                            timeout: Optional[int] = None,
                            retries: Optional[int] = None,
                            check_return_code: bool = True) -> 'AdbManager.CommandResult':
        """
        Safely execute ADB command on device
        
        Args:
            device_id: Target device ID
            command: Command to execute
            timeout: Command timeout in seconds
            retries: Number of retry attempts
            check_return_code: Whether to check command return code
            
        Returns:
            CommandResult with execution details
        """
        if device_id not in self.connections:
            return self.CommandResult(
                success=False,
                error=f"Device {device_id} not connected"
            )
        
        timeout = timeout or self.command_timeout
        retries = retries if retries is not None else self.max_retries
        
        connection = self.connections[device_id]
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                start_time = time.time()
                
                with self.device_locks[device_id]:
                    # Execute command
                    output = await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        lambda: connection.shell(command, timeout_s=timeout)
                    )
                
                execution_time = time.time() - start_time
                
                if output is None:
                    output = ""
                
                # Check return code if requested
                return_code = 0
                if check_return_code and output:
                    # Get return code
                    try:
                        rc_output = await asyncio.get_event_loop().run_in_executor(
                            self.executor,
                            lambda: connection.shell("echo $?", timeout_s=5)
                        )
                        if rc_output and rc_output.strip().isdigit():
                            return_code = int(rc_output.strip())
                    except:
                        pass  # Return code check failed, continue anyway
                
                success = not check_return_code or return_code == 0
                
                if success or attempt == retries:
                    return self.CommandResult(
                        success=success,
                        output=output,
                        return_code=return_code,
                        execution_time=execution_time
                    )
                
            except (AdbTimeoutError, asyncio.TimeoutError) as e:
                last_error = f"Command timed out: {e}"
                self.logger.warning(f"Command timeout on device {device_id} (attempt {attempt + 1}): {command}")
                
            except (AdbConnectionError, AdbCommandFailureException) as e:
                last_error = f"ADB error: {e}"
                self.logger.error(f"ADB command failed on device {device_id}: {e}")
                # Connection might be lost, trigger reconnection
                self._handle_device_disconnection(device_id)
                break
                
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                self.logger.error(f"Unexpected error executing command on device {device_id}: {e}")
            
            # Wait before retry
            if attempt < retries:
                await asyncio.sleep(1)
        
        return self.CommandResult(
            success=False,
            error=last_error or "Command failed after all retries"
        )
    
    async def execute_shell_command(self, device_id: str, command: str, **kwargs) -> 'AdbManager.CommandResult':
        """Alias for execute_command for shell commands"""
        return await self.execute_command(device_id, command, **kwargs)
    
    async def push_file(self, device_id: str, local_path: str, remote_path: str) -> bool:
        """
        Push file to device
        
        Args:
            device_id: Target device ID
            local_path: Local file path
            remote_path: Remote file path on device
            
        Returns:
            True if successful
        """
        if device_id not in self.connections:
            self.logger.error(f"Device {device_id} not connected")
            return False
        
        try:
            connection = self.connections[device_id]
            
            with self.device_locks[device_id]:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: connection.push(local_path, remote_path)
                )
            
            self.logger.info(f"Successfully pushed {local_path} to {device_id}:{remote_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to push file to device {device_id}: {e}")
            return False
    
    async def pull_file(self, device_id: str, remote_path: str, local_path: str) -> bool:
        """
        Pull file from device
        
        Args:
            device_id: Target device ID
            remote_path: Remote file path on device
            local_path: Local file path
            
        Returns:
            True if successful
        """
        if device_id not in self.connections:
            self.logger.error(f"Device {device_id} not connected")
            return False
        
        try:
            connection = self.connections[device_id]
            
            with self.device_locks[device_id]:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: connection.pull(remote_path, local_path)
                )
            
            self.logger.info(f"Successfully pulled {device_id}:{remote_path} to {local_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pull file from device {device_id}: {e}")
            return False
    
    def add_device_connected_callback(self, callback: Callable[[str], None]):
        """Add callback for device connection events"""
        self.device_connected_callbacks.append(callback)
    
    def add_device_disconnected_callback(self, callback: Callable[[str], None]):
        """Add callback for device disconnection events"""
        self.device_disconnected_callbacks.append(callback)
    
    def remove_device_connected_callback(self, callback: Callable[[str], None]):
        """Remove device connection callback"""
        if callback in self.device_connected_callbacks:
            self.device_connected_callbacks.remove(callback)
    
    def remove_device_disconnected_callback(self, callback: Callable[[str], None]):
        """Remove device disconnection callback"""
        if callback in self.device_disconnected_callbacks:
            self.device_disconnected_callbacks.remove(callback)
    
    @asynccontextmanager
    async def device_context(self, device_id: str):
        """Context manager for device operations"""
        if device_id not in self.connections:
            raise AdbConnectionError(f"Device {device_id} not connected")
        
        try:
            yield self.connections[device_id]
        except Exception as e:
            self.logger.error(f"Error in device context for {device_id}: {e}")
            raise
    
    def shutdown(self):
        """Shutdown the ADB manager"""
        self.logger.info("Shutting down ADB manager...")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Disconnect all devices
        for device_id in list(self.connections.keys()):
            try:
                self._handle_device_disconnection(device_id)
            except Exception as e:
                self.logger.error(f"Error disconnecting device {device_id} during shutdown: {e}")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        self.logger.info("ADB manager shutdown complete")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# Convenience functions

def create_adb_manager(**kwargs) -> AdbManager:
    """Create ADB manager with default settings"""
    return AdbManager(**kwargs)


async def get_device_property(adb_manager: AdbManager, device_id: str, property_name: str) -> Optional[str]:
    """Get Android system property from device"""
    result = await adb_manager.execute_command(device_id, f"getprop {property_name}")
    return result.output.strip() if result.success else None


async def install_apk(adb_manager: AdbManager, device_id: str, apk_path: str) -> bool:
    """Install APK on device"""
    result = await adb_manager.execute_command(device_id, f"pm install '{apk_path}'", timeout=120)
    return result.success and "Success" in result.output


async def uninstall_package(adb_manager: AdbManager, device_id: str, package_name: str) -> bool:
    """Uninstall package from device"""
    result = await adb_manager.execute_command(device_id, f"pm uninstall {package_name}")
    return result.success and "Success" in result.output


async def is_screen_on(adb_manager: AdbManager, device_id: str) -> bool:
    """Check if device screen is on"""
    result = await adb_manager.execute_command(device_id, "dumpsys power | grep 'mHoldingDisplaySuspendBlocker'")
    return result.success and "true" in result.output.lower()


async def get_current_activity(adb_manager: AdbManager, device_id: str) -> Optional[str]:
    """Get current activity name"""
    result = await adb_manager.execute_command(
        device_id, 
        "dumpsys activity activities | grep 'mResumedActivity'"
    )
    if result.success and result.output:
        # Extract activity name from output
        import re
        match = re.search(r'ActivityRecord{[^}]+ ([^/]+/[^}]+)', result.output)
        return match.group(1) if match else None
    return None
