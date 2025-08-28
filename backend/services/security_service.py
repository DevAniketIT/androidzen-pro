"""
Security Monitoring Dashboard Service for AndroidZen Pro

This service provides comprehensive security monitoring and threat detection:
- App permission analysis and suspicious app detection
- Network traffic monitoring within ADB limitations
- Suspicious activity detection algorithms
- Real-time alert system with WebSocket notifications
- Security scoring system based on device state
- Security recommendations engine
- Comprehensive logging for security events
"""

import asyncio
import hashlib
import json
import logging
import re
import statistics
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, NamedTuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import ipaddress
from collections import defaultdict, deque

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from .core.adb_manager import AdbManager
from .core.websocket_manager import WebSocketManager, MessageType
from .models.device import Device
from .models.security import (
    SecurityEvent, SecurityAlert, ThreatIntelligence,
    SeverityLevel, EventStatus
)
from .core.database import get_db


@dataclass
class AppPermission:
    """Application permission information"""
    package_name: str
    app_name: str
    permission: str
    is_dangerous: bool
    description: str
    granted: bool
    requested_at: Optional[datetime] = None


@dataclass
class SuspiciousApp:
    """Suspicious application information"""
    package_name: str
    app_name: str
    version: str
    install_source: str
    risk_score: float
    reasons: List[str]
    permissions: List[str]
    file_hash: Optional[str] = None
    last_activity: Optional[datetime] = None


@dataclass
class NetworkConnection:
    """Network connection information"""
    protocol: str
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    state: str
    process_name: Optional[str] = None
    package_name: Optional[str] = None
    data_sent: int = 0
    data_received: int = 0
    connection_time: Optional[datetime] = None


@dataclass
class SecurityScore:
    """Security scoring information"""
    overall_score: float  # 0-100
    permission_score: float
    app_security_score: float
    network_security_score: float
    system_security_score: float
    threat_level: str  # "low", "medium", "high", "critical"
    recommendations: List[str]
    last_updated: datetime


@dataclass
class ThreatDetection:
    """Threat detection result"""
    threat_type: str
    severity: SeverityLevel
    confidence: float
    description: str
    indicators: List[str]
    affected_components: List[str]
    recommended_actions: List[str]
    detection_time: datetime


class SecurityAnalysisService:
    """Comprehensive security analysis and monitoring service"""
    
    def __init__(self, adb_manager: AdbManager, websocket_manager: WebSocketManager):
        self.adb_manager = adb_manager
        self.websocket_manager = websocket_manager
        self.logger = logging.getLogger(__name__)
        
        # Security monitoring state
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._device_baselines: Dict[str, Dict] = {}
        self._activity_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._network_baselines: Dict[str, Dict] = {}
        
        # Dangerous permissions (high-risk)
        self.dangerous_permissions = {
            "android.permission.CAMERA": "Access camera for photos/videos",
            "android.permission.RECORD_AUDIO": "Record audio and conversations",
            "android.permission.ACCESS_FINE_LOCATION": "Access precise location",
            "android.permission.ACCESS_COARSE_LOCATION": "Access approximate location",
            "android.permission.READ_CONTACTS": "Read contacts and contact info",
            "android.permission.WRITE_CONTACTS": "Modify contacts",
            "android.permission.READ_SMS": "Read SMS messages",
            "android.permission.SEND_SMS": "Send SMS messages",
            "android.permission.READ_PHONE_STATE": "Read phone status and identity",
            "android.permission.CALL_PHONE": "Make phone calls",
            "android.permission.READ_CALL_LOG": "Read call history",
            "android.permission.WRITE_CALL_LOG": "Modify call history",
            "android.permission.READ_EXTERNAL_STORAGE": "Read external storage",
            "android.permission.WRITE_EXTERNAL_STORAGE": "Write to external storage",
            "android.permission.ACCESS_WIFI_STATE": "Access Wi-Fi information",
            "android.permission.CHANGE_WIFI_STATE": "Change Wi-Fi configuration",
            "android.permission.BLUETOOTH": "Connect to Bluetooth devices",
            "android.permission.BLUETOOTH_ADMIN": "Manage Bluetooth settings",
            "android.permission.SYSTEM_ALERT_WINDOW": "Display system alert windows",
            "android.permission.WRITE_SETTINGS": "Modify system settings",
            "android.permission.DEVICE_ADMIN": "Device administrator privileges",
            "android.permission.BIND_DEVICE_ADMIN": "Bind as device admin",
            "android.permission.MANAGE_ACCOUNTS": "Manage device accounts",
            "android.permission.USE_FINGERPRINT": "Use fingerprint hardware",
            "android.permission.BODY_SENSORS": "Access body sensors",
            "android.permission.ACCESS_NOTIFICATION_POLICY": "Access notification policy"
        }
        
        # Suspicious app indicators
        self.suspicious_indicators = {
            "permissions": ["DEVICE_ADMIN", "SYSTEM_ALERT_WINDOW", "BIND_DEVICE_ADMIN"],
            "package_patterns": [r".*\.fake\..*", r".*\.malware\..*", r".*\.trojan\..*"],
            "install_sources": ["unknown", "sideload", "adb"],
            "behavioral_patterns": ["excessive_network", "hidden_activities", "root_access"]
        }
        
        # Network monitoring patterns
        self.suspicious_network_patterns = {
            "tor_exit_nodes": [],  # Would be populated from threat intel
            "known_malicious_ips": [],  # Would be populated from threat intel
            "suspicious_ports": [6667, 6697, 1337, 31337, 4444, 5554, 9999],
            "crypto_mining_ports": [4444, 8333, 18333, 9332, 9333]
        }

    async def start_monitoring(self, device_id: str) -> bool:
        """Start continuous security monitoring for a device"""
        try:
            if device_id in self._monitoring_tasks:
                self.logger.info(f"Security monitoring already active for device {device_id}")
                return True
            
            # Create monitoring task
            task = asyncio.create_task(self._continuous_monitoring_loop(device_id))
            self._monitoring_tasks[device_id] = task
            
            # Initialize device baseline
            await self._initialize_device_baseline(device_id)
            
            self.logger.info(f"Started security monitoring for device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start security monitoring for device {device_id}: {e}")
            return False

    async def stop_monitoring(self, device_id: str) -> bool:
        """Stop security monitoring for a device"""
        try:
            if device_id in self._monitoring_tasks:
                self._monitoring_tasks[device_id].cancel()
                del self._monitoring_tasks[device_id]
                self.logger.info(f"Stopped security monitoring for device {device_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop security monitoring for device {device_id}: {e}")
            return False

    async def _continuous_monitoring_loop(self, device_id: str):
        """Main continuous monitoring loop"""
        monitoring_interval = 30  # 30 seconds between checks
        
        try:
            while True:
                try:
                    # Perform security checks
                    await self._perform_security_scan(device_id)
                    
                    # Network monitoring
                    await self._monitor_network_activity(device_id)
                    
                    # Behavioral analysis
                    await self._analyze_behavioral_patterns(device_id)
                    
                    # Update security score
                    await self._update_security_score(device_id)
                    
                    await asyncio.sleep(monitoring_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop for device {device_id}: {e}")
                    await asyncio.sleep(monitoring_interval)
                    
        except asyncio.CancelledError:
            self.logger.info(f"Monitoring loop cancelled for device {device_id}")
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring loop for device {device_id}: {e}")

    async def _initialize_device_baseline(self, device_id: str):
        """Initialize security baseline for a device"""
        try:
            baseline = {
                "installed_apps": await self._get_installed_apps(device_id),
                "network_connections": await self._get_network_connections(device_id),
                "system_processes": await self._get_running_processes(device_id),
                "initialization_time": datetime.utcnow(),
                "total_apps": 0,
                "system_apps": 0,
                "user_apps": 0
            }
            
            # Analyze baseline apps
            if baseline["installed_apps"]:
                baseline["total_apps"] = len(baseline["installed_apps"])
                baseline["system_apps"] = len([app for app in baseline["installed_apps"] 
                                             if app.get("is_system", False)])
                baseline["user_apps"] = baseline["total_apps"] - baseline["system_apps"]
            
            self._device_baselines[device_id] = baseline
            
        except Exception as e:
            self.logger.error(f"Failed to initialize baseline for device {device_id}: {e}")

    async def _perform_security_scan(self, device_id: str):
        """Perform comprehensive security scan"""
        try:
            # App permission analysis
            await self._analyze_app_permissions(device_id)
            
            # Detect suspicious apps
            await self._detect_suspicious_apps(device_id)
            
            # Check system integrity
            await self._check_system_integrity(device_id)
            
            # Analyze file system changes
            await self._analyze_filesystem_changes(device_id)
            
        except Exception as e:
            self.logger.error(f"Error in security scan for device {device_id}: {e}")

    async def _analyze_app_permissions(self, device_id: str) -> List[AppPermission]:
        """Analyze application permissions and detect suspicious grants"""
        permissions = []
        
        try:
            # Get list of installed packages
            packages_result = await self.adb_manager.execute_command(
                device_id, "pm list packages -3"  # User-installed only
            )
            
            if not packages_result.success:
                return permissions
            
            packages = []
            for line in packages_result.output.strip().split('\n'):
                if line.startswith('package:'):
                    packages.append(line.replace('package:', '').strip())
            
            # Analyze permissions for each package
            for package in packages[:20]:  # Limit to avoid timeout
                try:
                    package_permissions = await self._get_package_permissions(device_id, package)
                    permissions.extend(package_permissions)
                    
                    # Check for suspicious permission combinations
                    await self._check_suspicious_permission_patterns(device_id, package, package_permissions)
                    
                except Exception as e:
                    self.logger.debug(f"Error analyzing permissions for {package}: {e}")
                    continue
            
            # Log summary
            dangerous_count = sum(1 for p in permissions if p.is_dangerous and p.granted)
            self.logger.info(f"Analyzed {len(permissions)} permissions, {dangerous_count} dangerous")
            
            return permissions
            
        except Exception as e:
            self.logger.error(f"Error analyzing app permissions for device {device_id}: {e}")
            return []

    async def _get_package_permissions(self, device_id: str, package_name: str) -> List[AppPermission]:
        """Get permissions for a specific package"""
        permissions = []
        
        try:
            # Get package permissions
            perm_result = await self.adb_manager.execute_command(
                device_id, f"dumpsys package {package_name} | grep -E '(permission|granted)'"
            )
            
            if not perm_result.success:
                return permissions
            
            # Get app name
            app_name = await self._get_app_name(device_id, package_name)
            
            # Parse permissions
            lines = perm_result.output.strip().split('\n')
            for line in lines:
                line = line.strip()
                
                # Look for permission grants
                if 'android.permission' in line and 'granted=true' in line:
                    perm_match = re.search(r'(android\.permission\.[A-Z_]+)', line)
                    if perm_match:
                        perm_name = perm_match.group(1)
                        is_dangerous = perm_name in self.dangerous_permissions
                        description = self.dangerous_permissions.get(perm_name, "Unknown permission")
                        
                        permissions.append(AppPermission(
                            package_name=package_name,
                            app_name=app_name,
                            permission=perm_name,
                            is_dangerous=is_dangerous,
                            description=description,
                            granted=True
                        ))
            
            return permissions
            
        except Exception as e:
            self.logger.debug(f"Error getting permissions for {package_name}: {e}")
            return []

    async def _get_app_name(self, device_id: str, package_name: str) -> str:
        """Get human-readable app name"""
        try:
            name_result = await self.adb_manager.execute_command(
                device_id, f"dumpsys package {package_name} | grep -E 'applicationInfo'"
            )
            
            if name_result.success and name_result.output:
                # Try to extract app name from output
                lines = name_result.output.split('\n')
                for line in lines:
                    if 'name=' in line and package_name in line:
                        name_match = re.search(r'name=([^,\s]+)', line)
                        if name_match:
                            return name_match.group(1)
            
            return package_name  # Fallback to package name
            
        except Exception:
            return package_name

    async def _check_suspicious_permission_patterns(self, device_id: str, package_name: str, 
                                                   permissions: List[AppPermission]):
        """Check for suspicious permission patterns and create alerts"""
        try:
            dangerous_perms = [p for p in permissions if p.is_dangerous and p.granted]
            
            # High-risk permission combinations
            high_risk_patterns = [
                {"permissions": ["DEVICE_ADMIN", "SYSTEM_ALERT_WINDOW"], "risk": "Device takeover potential"},
                {"permissions": ["CAMERA", "RECORD_AUDIO", "ACCESS_FINE_LOCATION"], "risk": "Surveillance capabilities"},
                {"permissions": ["READ_SMS", "SEND_SMS", "READ_CONTACTS"], "risk": "SMS/Contact access"},
                {"permissions": ["READ_CALL_LOG", "CALL_PHONE"], "risk": "Call manipulation"},
                {"permissions": ["WRITE_EXTERNAL_STORAGE", "SYSTEM_ALERT_WINDOW"], "risk": "File system manipulation"}
            ]
            
            perm_names = [p.permission.split('.')[-1] for p in dangerous_perms]
            
            for pattern in high_risk_patterns:
                if all(perm in perm_names for perm in pattern["permissions"]):
                    await self._create_security_event(
                        device_id=device_id,
                        event_type="suspicious_permissions",
                        severity=SeverityLevel.HIGH,
                        title=f"Suspicious permission pattern in {package_name}",
                        description=f"App has dangerous permission combination: {pattern['risk']}",
                        app_package_name=package_name,
                        app_permissions=[p.permission for p in dangerous_perms],
                        risk_score=85.0
                    )
                    break
            
            # Check for excessive dangerous permissions
            if len(dangerous_perms) >= 5:
                await self._create_security_event(
                    device_id=device_id,
                    event_type="excessive_permissions",
                    severity=SeverityLevel.MEDIUM,
                    title=f"Excessive permissions granted to {package_name}",
                    description=f"App has {len(dangerous_perms)} dangerous permissions granted",
                    app_package_name=package_name,
                    app_permissions=[p.permission for p in dangerous_perms],
                    risk_score=60.0
                )
                
        except Exception as e:
            self.logger.error(f"Error checking permission patterns: {e}")

    async def _detect_suspicious_apps(self, device_id: str) -> List[SuspiciousApp]:
        """Detect potentially malicious or suspicious applications"""
        suspicious_apps = []
        
        try:
            apps = await self._get_installed_apps(device_id)
            
            for app in apps:
                suspicion_reasons = []
                risk_score = 0.0
                
                # Check package name patterns
                package_name = app.get("package_name", "")
                for pattern in self.suspicious_indicators["package_patterns"]:
                    if re.match(pattern, package_name, re.IGNORECASE):
                        suspicion_reasons.append(f"Suspicious package name pattern: {pattern}")
                        risk_score += 30.0
                
                # Check install source
                install_source = app.get("install_source", "")
                if install_source in self.suspicious_indicators["install_sources"]:
                    suspicion_reasons.append(f"Suspicious install source: {install_source}")
                    risk_score += 25.0
                
                # Check permissions
                permissions = await self._get_package_permissions(device_id, package_name)
                dangerous_perms = [p for p in permissions if p.is_dangerous and p.granted]
                
                if len(dangerous_perms) >= 6:
                    suspicion_reasons.append(f"Excessive dangerous permissions: {len(dangerous_perms)}")
                    risk_score += 20.0
                
                # Check for admin permissions
                admin_perms = [p for p in permissions if "ADMIN" in p.permission]
                if admin_perms:
                    suspicion_reasons.append("Has device admin permissions")
                    risk_score += 40.0
                
                # Check app behavior (simplified)
                if app.get("has_hidden_icon", False):
                    suspicion_reasons.append("App hides its icon")
                    risk_score += 35.0
                
                # Create suspicious app record if risk score is high enough
                if risk_score >= 50.0 or len(suspicion_reasons) >= 2:
                    suspicious_app = SuspiciousApp(
                        package_name=package_name,
                        app_name=app.get("app_name", package_name),
                        version=app.get("version", "unknown"),
                        install_source=install_source,
                        risk_score=min(risk_score, 100.0),
                        reasons=suspicion_reasons,
                        permissions=[p.permission for p in dangerous_perms],
                        last_activity=datetime.utcnow()
                    )
                    
                    suspicious_apps.append(suspicious_app)
                    
                    # Create security event
                    severity = SeverityLevel.CRITICAL if risk_score >= 80 else \
                              SeverityLevel.HIGH if risk_score >= 65 else SeverityLevel.MEDIUM
                    
                    await self._create_security_event(
                        device_id=device_id,
                        event_type="suspicious_app",
                        severity=severity,
                        title=f"Suspicious app detected: {app.get('app_name', package_name)}",
                        description=f"App flagged for: {', '.join(suspicion_reasons)}",
                        app_package_name=package_name,
                        app_name=app.get("app_name"),
                        risk_score=risk_score,
                        threat_indicators={"reasons": suspicion_reasons, "permissions": [p.permission for p in dangerous_perms]}
                    )
            
            return suspicious_apps
            
        except Exception as e:
            self.logger.error(f"Error detecting suspicious apps for device {device_id}: {e}")
            return []

    async def _get_installed_apps(self, device_id: str) -> List[Dict[str, Any]]:
        """Get list of installed applications with metadata"""
        apps = []
        
        try:
            # Get user-installed packages
            packages_result = await self.adb_manager.execute_command(
                device_id, "pm list packages -3"
            )
            
            if not packages_result.success:
                return apps
            
            for line in packages_result.output.strip().split('\n'):
                if line.startswith('package:'):
                    package_name = line.replace('package:', '').strip()
                    
                    try:
                        # Get app info
                        app_info = await self._get_app_info(device_id, package_name)
                        if app_info:
                            apps.append(app_info)
                    except Exception as e:
                        self.logger.debug(f"Error getting info for {package_name}: {e}")
                        continue
            
            return apps
            
        except Exception as e:
            self.logger.error(f"Error getting installed apps: {e}")
            return []

    async def _get_app_info(self, device_id: str, package_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an app"""
        try:
            # Get package info
            info_result = await self.adb_manager.execute_command(
                device_id, f"dumpsys package {package_name}"
            )
            
            if not info_result.success:
                return None
            
            app_info = {
                "package_name": package_name,
                "app_name": package_name,  # Will be updated if found
                "version": "unknown",
                "install_source": "unknown",
                "is_system": False,
                "has_hidden_icon": False,
                "install_time": None
            }
            
            # Parse dumpsys output
            lines = info_result.output.split('\n')
            for line in lines:
                line = line.strip()
                
                # Version info
                if 'versionName=' in line:
                    version_match = re.search(r'versionName=([^\s]+)', line)
                    if version_match:
                        app_info["version"] = version_match.group(1)
                
                # Install source
                if 'installerPackageName=' in line:
                    installer_match = re.search(r'installerPackageName=([^\s]+)', line)
                    if installer_match:
                        installer = installer_match.group(1)
                        if installer == "null":
                            app_info["install_source"] = "sideload"
                        elif "com.android.vending" in installer:
                            app_info["install_source"] = "play_store"
                        else:
                            app_info["install_source"] = installer
                
                # System app check
                if 'system=true' in line:
                    app_info["is_system"] = True
                
                # Install time
                if 'firstInstallTime=' in line:
                    time_match = re.search(r'firstInstallTime=([^\s]+)', line)
                    if time_match:
                        try:
                            app_info["install_time"] = datetime.fromisoformat(time_match.group(1))
                        except:
                            pass
            
            # Get app name from activity manager
            name_result = await self.adb_manager.execute_command(
                device_id, f"pm dump {package_name} | grep 'applicationInfo'"
            )
            
            if name_result.success and name_result.output:
                # Try to extract readable name
                for line in name_result.output.split('\n'):
                    if 'name=' in line:
                        name_match = re.search(r'name=([^,\s]+)', line)
                        if name_match:
                            app_info["app_name"] = name_match.group(1)
                            break
            
            return app_info
            
        except Exception as e:
            self.logger.debug(f"Error getting app info for {package_name}: {e}")
            return None

    async def _monitor_network_activity(self, device_id: str):
        """Monitor network activity and detect suspicious connections"""
        try:
            connections = await self._get_network_connections(device_id)
            
            for conn in connections:
                await self._analyze_network_connection(device_id, conn)
            
            # Update network baseline
            if device_id in self._device_baselines:
                self._device_baselines[device_id]["last_network_scan"] = datetime.utcnow()
                self._device_baselines[device_id]["active_connections"] = len(connections)
            
        except Exception as e:
            self.logger.error(f"Error monitoring network activity for device {device_id}: {e}")

    async def _get_network_connections(self, device_id: str) -> List[NetworkConnection]:
        """Get active network connections"""
        connections = []
        
        try:
            # Get network connections using netstat
            netstat_result = await self.adb_manager.execute_command(
                device_id, "netstat -tuln 2>/dev/null || ss -tuln 2>/dev/null"
            )
            
            if not netstat_result.success:
                return connections
            
            # Parse netstat/ss output
            for line in netstat_result.output.strip().split('\n'):
                if not line or 'Proto' in line or 'Local' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        protocol = parts[0].lower()
                        local_addr = parts[3]
                        
                        # Parse address:port
                        if ':' in local_addr:
                            addr_parts = local_addr.rsplit(':', 1)
                            local_ip = addr_parts[0]
                            local_port = int(addr_parts[1]) if addr_parts[1].isdigit() else 0
                        else:
                            continue
                        
                        # For TCP connections, get remote address
                        remote_addr = ""
                        remote_port = 0
                        state = "LISTEN"
                        
                        if len(parts) >= 5 and protocol == 'tcp':
                            remote_addr_str = parts[4]
                            if ':' in remote_addr_str and remote_addr_str != '0.0.0.0:*':
                                remote_parts = remote_addr_str.rsplit(':', 1)
                                remote_addr = remote_parts[0]
                                remote_port = int(remote_parts[1]) if remote_parts[1].isdigit() else 0
                            
                            if len(parts) >= 6:
                                state = parts[5]
                        
                        connection = NetworkConnection(
                            protocol=protocol,
                            local_address=local_ip,
                            local_port=local_port,
                            remote_address=remote_addr,
                            remote_port=remote_port,
                            state=state,
                            connection_time=datetime.utcnow()
                        )
                        
                        connections.append(connection)
                        
                    except (ValueError, IndexError) as e:
                        self.logger.debug(f"Error parsing netstat line '{line}': {e}")
                        continue
            
            return connections
            
        except Exception as e:
            self.logger.error(f"Error getting network connections: {e}")
            return []

    async def _analyze_network_connection(self, device_id: str, connection: NetworkConnection):
        """Analyze individual network connection for threats"""
        try:
            risk_score = 0.0
            threat_indicators = []
            
            # Check for suspicious ports
            if connection.remote_port in self.suspicious_network_patterns["suspicious_ports"]:
                risk_score += 30.0
                threat_indicators.append(f"Connection to suspicious port {connection.remote_port}")
            
            # Check for crypto mining ports
            if connection.remote_port in self.suspicious_network_patterns["crypto_mining_ports"]:
                risk_score += 40.0
                threat_indicators.append(f"Connection to crypto mining port {connection.remote_port}")
            
            # Check for connections to private IP ranges from outside
            try:
                if connection.remote_address and connection.remote_address != "0.0.0.0":
                    remote_ip = ipaddress.ip_address(connection.remote_address)
                    if not remote_ip.is_private and connection.local_port < 1024:
                        risk_score += 20.0
                        threat_indicators.append("Privileged port connection to external IP")
            except (ValueError, ipaddress.AddressValueError):
                pass
            
            # Check for unusual connection patterns
            if connection.state == "ESTABLISHED" and connection.remote_port == 0:
                risk_score += 25.0
                threat_indicators.append("Unusual connection state")
            
            # Create security event if risk is high
            if risk_score >= 40.0:
                await self._create_security_event(
                    device_id=device_id,
                    event_type="suspicious_network",
                    severity=SeverityLevel.MEDIUM if risk_score < 60 else SeverityLevel.HIGH,
                    title=f"Suspicious network connection detected",
                    description=f"Connection to {connection.remote_address}:{connection.remote_port}",
                    network_address=connection.remote_address,
                    network_port=connection.remote_port,
                    network_protocol=connection.protocol,
                    risk_score=risk_score,
                    threat_indicators={"indicators": threat_indicators, "connection": connection.__dict__}
                )
            
        except Exception as e:
            self.logger.error(f"Error analyzing network connection: {e}")

    async def _analyze_behavioral_patterns(self, device_id: str):
        """Analyze device behavior patterns for anomalies"""
        try:
            # Get current activity
            current_activity = await self._get_current_system_state(device_id)
            
            # Add to activity history
            self._activity_history[device_id].append({
                "timestamp": datetime.utcnow(),
                "activity": current_activity
            })
            
            # Analyze patterns if we have enough history
            if len(self._activity_history[device_id]) >= 10:
                await self._detect_behavioral_anomalies(device_id)
            
        except Exception as e:
            self.logger.error(f"Error analyzing behavioral patterns for device {device_id}: {e}")

    async def _get_current_system_state(self, device_id: str) -> Dict[str, Any]:
        """Get current system state snapshot"""
        try:
            state = {
                "timestamp": datetime.utcnow(),
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "active_processes": 0,
                "network_connections": 0,
                "battery_level": 0
            }
            
            # Get CPU usage
            cpu_result = await self.adb_manager.execute_command(
                device_id, "dumpsys cpuinfo | head -20"
            )
            if cpu_result.success:
                # Parse CPU usage (simplified)
                for line in cpu_result.output.split('\n'):
                    if 'TOTAL:' in line and '%cpu' in line:
                        cpu_match = re.search(r'(\d+(?:\.\d+)?)%cpu', line)
                        if cpu_match:
                            state["cpu_usage"] = float(cpu_match.group(1))
                        break
            
            # Get memory info
            mem_result = await self.adb_manager.execute_command(
                device_id, "dumpsys meminfo | grep 'Total RAM'"
            )
            if mem_result.success and mem_result.output:
                # Parse memory usage (simplified)
                mem_match = re.search(r'Total RAM:\s*(\d+(?:,\d+)*)', mem_result.output)
                if mem_match:
                    total_mem = int(mem_match.group(1).replace(',', ''))
                    state["memory_usage"] = total_mem
            
            # Get battery level
            battery_result = await self.adb_manager.execute_command(
                device_id, "dumpsys battery | grep level"
            )
            if battery_result.success:
                battery_match = re.search(r'level:\s*(\d+)', battery_result.output)
                if battery_match:
                    state["battery_level"] = int(battery_match.group(1))
            
            return state
            
        except Exception as e:
            self.logger.debug(f"Error getting system state: {e}")
            return {"timestamp": datetime.utcnow(), "error": str(e)}

    async def _detect_behavioral_anomalies(self, device_id: str):
        """Detect anomalies in device behavior patterns"""
        try:
            history = list(self._activity_history[device_id])
            if len(history) < 10:
                return
            
            # Analyze CPU usage patterns
            cpu_values = [h["activity"].get("cpu_usage", 0) for h in history[-20:]]
            cpu_values = [v for v in cpu_values if v > 0]  # Filter valid values
            
            if len(cpu_values) >= 5:
                avg_cpu = statistics.mean(cpu_values)
                cpu_stddev = statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
                
                # Check for sustained high CPU usage
                recent_cpu = cpu_values[-5:]
                if all(cpu > 80 for cpu in recent_cpu):
                    await self._create_security_event(
                        device_id=device_id,
                        event_type="behavioral_anomaly",
                        severity=SeverityLevel.MEDIUM,
                        title="Sustained high CPU usage detected",
                        description=f"CPU usage has been consistently high (avg: {avg_cpu:.1f}%)",
                        risk_score=50.0,
                        behavioral_patterns={"cpu_pattern": recent_cpu, "average": avg_cpu}
                    )
                
                # Check for CPU usage spikes
                for cpu in recent_cpu:
                    if cpu > avg_cpu + (3 * cpu_stddev) and cpu > 90:
                        await self._create_security_event(
                            device_id=device_id,
                            event_type="behavioral_anomaly",
                            severity=SeverityLevel.LOW,
                            title="CPU usage spike detected",
                            description=f"Unusual CPU spike: {cpu:.1f}% (avg: {avg_cpu:.1f}%)",
                            risk_score=30.0,
                            behavioral_patterns={"spike_value": cpu, "baseline": avg_cpu}
                        )
            
        except Exception as e:
            self.logger.error(f"Error detecting behavioral anomalies: {e}")

    async def _check_system_integrity(self, device_id: str):
        """Check system integrity and detect tampering"""
        try:
            integrity_issues = []
            
            # Check for root access
            root_check = await self.adb_manager.execute_command(
                device_id, "which su 2>/dev/null && echo 'rooted' || echo 'not_rooted'"
            )
            
            if root_check.success and "rooted" in root_check.output:
                integrity_issues.append("Device appears to be rooted")
                
                await self._create_security_event(
                    device_id=device_id,
                    event_type="root_detection",
                    severity=SeverityLevel.HIGH,
                    title="Rooted device detected",
                    description="Device has root access which poses security risks",
                    risk_score=70.0,
                    system_command="su",
                    detection_method="adb"
                )
            
            # Check for development settings
            dev_settings = await self.adb_manager.execute_command(
                device_id, "settings get global development_settings_enabled"
            )
            
            if dev_settings.success and "1" in dev_settings.output:
                integrity_issues.append("Developer options enabled")
            
            # Check for ADB debugging
            adb_debug = await self.adb_manager.execute_command(
                device_id, "settings get global adb_enabled"
            )
            
            if adb_debug.success and "1" in adb_debug.output:
                integrity_issues.append("ADB debugging enabled")
            
            # Check for unknown sources
            unknown_sources = await self.adb_manager.execute_command(
                device_id, "settings get global install_non_market_apps"
            )
            
            if unknown_sources.success and "1" in unknown_sources.output:
                integrity_issues.append("Installation from unknown sources enabled")
            
            # Log integrity status
            if integrity_issues:
                self.logger.info(f"System integrity issues for device {device_id}: {integrity_issues}")
            else:
                self.logger.debug(f"System integrity check passed for device {device_id}")
                
        except Exception as e:
            self.logger.error(f"Error checking system integrity: {e}")

    async def _analyze_filesystem_changes(self, device_id: str):
        """Analyze filesystem for suspicious changes"""
        try:
            # Check for new files in sensitive directories
            sensitive_paths = [
                "/system/bin/",
                "/system/xbin/", 
                "/data/local/tmp/",
                "/sdcard/.android_secure/",
                "/cache/"
            ]
            
            for path in sensitive_paths:
                try:
                    # Check if path exists and get listing
                    files_result = await self.adb_manager.execute_command(
                        device_id, f"test -d '{path}' && ls -la '{path}' | head -20"
                    )
                    
                    if files_result.success and files_result.output:
                        await self._check_suspicious_files(device_id, path, files_result.output)
                        
                except Exception as e:
                    self.logger.debug(f"Error checking {path}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error analyzing filesystem changes: {e}")

    async def _check_suspicious_files(self, device_id: str, path: str, file_listing: str):
        """Check for suspicious files in directory listing"""
        try:
            suspicious_patterns = [
                r".*\.dex$",  # Dalvik executables
                r".*su$",     # Su binaries
                r".*busybox.*",  # BusyBox
                r".*\.so$",   # Native libraries in wrong places
                r".*tmp.*\.sh$"  # Temporary shell scripts
            ]
            
            for line in file_listing.split('\n'):
                if not line.strip():
                    continue
                    
                # Parse file listing (simplified)
                parts = line.split()
                if len(parts) >= 9:
                    filename = parts[-1]
                    
                    for pattern in suspicious_patterns:
                        if re.match(pattern, filename, re.IGNORECASE):
                            await self._create_security_event(
                                device_id=device_id,
                                event_type="suspicious_file",
                                severity=SeverityLevel.MEDIUM,
                                title=f"Suspicious file detected: {filename}",
                                description=f"Found suspicious file in {path}",
                                file_path=f"{path}/{filename}",
                                risk_score=45.0,
                                detection_method="filesystem_scan"
                            )
                            break
                            
        except Exception as e:
            self.logger.debug(f"Error checking suspicious files: {e}")

    async def _get_running_processes(self, device_id: str) -> List[Dict[str, Any]]:
        """Get list of running processes"""
        processes = []
        
        try:
            ps_result = await self.adb_manager.execute_command(
                device_id, "ps -A 2>/dev/null || ps"
            )
            
            if not ps_result.success:
                return processes
            
            lines = ps_result.output.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        processes.append({
                            "pid": int(parts[1]),
                            "name": parts[-1],
                            "user": parts[0] if len(parts) > 0 else "unknown"
                        })
                    except (ValueError, IndexError):
                        continue
            
            return processes
            
        except Exception as e:
            self.logger.error(f"Error getting running processes: {e}")
            return []

    async def _calculate_security_score(self, device_id: str) -> SecurityScore:
        """Calculate comprehensive security score for device"""
        try:
            # Initialize scores
            permission_score = 100.0
            app_security_score = 100.0
            network_security_score = 100.0
            system_security_score = 100.0
            
            recommendations = []
            
            # Get recent security events
            # In a real implementation, this would query the database
            # For now, we'll calculate based on current state
            
            # Permission analysis
            apps = await self._get_installed_apps(device_id)
            total_dangerous_perms = 0
            
            for app in apps[:10]:  # Limit for performance
                perms = await self._get_package_permissions(device_id, app["package_name"])
                dangerous_perms = [p for p in perms if p.is_dangerous and p.granted]
                total_dangerous_perms += len(dangerous_perms)
            
            # Adjust permission score
            if total_dangerous_perms > 20:
                permission_score -= 30
                recommendations.append("Review and revoke unnecessary dangerous permissions")
            elif total_dangerous_perms > 10:
                permission_score -= 15
            
            # System integrity score
            root_check = await self.adb_manager.execute_command(
                device_id, "which su 2>/dev/null && echo 'rooted'"
            )
            
            if root_check.success and "rooted" in root_check.output:
                system_security_score -= 40
                recommendations.append("Device is rooted - consider security implications")
            
            # Development settings check
            dev_enabled = await self.adb_manager.execute_command(
                device_id, "settings get global development_settings_enabled"
            )
            
            if dev_enabled.success and "1" in dev_enabled.output:
                system_security_score -= 10
                recommendations.append("Disable developer options when not needed")
            
            # Network security (simplified)
            connections = await self._get_network_connections(device_id)
            suspicious_connections = 0
            
            for conn in connections:
                if (conn.remote_port in self.suspicious_network_patterns["suspicious_ports"] or
                    conn.remote_port in self.suspicious_network_patterns["crypto_mining_ports"]):
                    suspicious_connections += 1
            
            if suspicious_connections > 0:
                network_security_score -= (suspicious_connections * 15)
                recommendations.append(f"Review {suspicious_connections} suspicious network connections")
            
            # App security score based on suspicious apps
            suspicious_apps = await self._detect_suspicious_apps(device_id)
            if suspicious_apps:
                high_risk_apps = [app for app in suspicious_apps if app.risk_score >= 70]
                if high_risk_apps:
                    app_security_score -= (len(high_risk_apps) * 20)
                    recommendations.append(f"Review {len(high_risk_apps)} high-risk applications")
                
                medium_risk_apps = [app for app in suspicious_apps if 50 <= app.risk_score < 70]
                if medium_risk_apps:
                    app_security_score -= (len(medium_risk_apps) * 10)
            
            # Calculate overall score
            scores = [permission_score, app_security_score, network_security_score, system_security_score]
            overall_score = max(0, min(100, statistics.mean(scores)))
            
            # Determine threat level
            if overall_score >= 90:
                threat_level = "low"
            elif overall_score >= 70:
                threat_level = "medium"
            elif overall_score >= 50:
                threat_level = "high"
            else:
                threat_level = "critical"
            
            # Add general recommendations based on score
            if overall_score < 70:
                recommendations.append("Immediate security review recommended")
            if overall_score < 50:
                recommendations.append("Critical security issues require immediate attention")
            
            if not recommendations:
                recommendations.append("Security posture looks good - continue monitoring")
            
            return SecurityScore(
                overall_score=round(overall_score, 1),
                permission_score=max(0, round(permission_score, 1)),
                app_security_score=max(0, round(app_security_score, 1)),
                network_security_score=max(0, round(network_security_score, 1)),
                system_security_score=max(0, round(system_security_score, 1)),
                threat_level=threat_level,
                recommendations=recommendations,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating security score: {e}")
            return SecurityScore(
                overall_score=0.0,
                permission_score=0.0,
                app_security_score=0.0,
                network_security_score=0.0,
                system_security_score=0.0,
                threat_level="unknown",
                recommendations=["Error calculating security score"],
                last_updated=datetime.utcnow()
            )

    async def _update_security_score(self, device_id: str):
        """Update and broadcast security score"""
        try:
            score = await self._calculate_security_score(device_id)
            
            # Send real-time update via WebSocket
            await self.websocket_manager.send_security_alert(
                device_id=device_id,
                alert_details={
                    "type": "security_score_update",
                    "score": score.__dict__,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Log score update
            self.logger.info(f"Security score updated for device {device_id}: {score.overall_score:.1f} ({score.threat_level})")
            
        except Exception as e:
            self.logger.error(f"Error updating security score: {e}")

    async def _create_security_event(self, device_id: str, event_type: str, severity: SeverityLevel,
                                   title: str, description: str, **kwargs) -> Optional[int]:
        """Create a security event and send real-time alerts"""
        try:
            # Get database session
            db = next(get_db())
            
            try:
                # Get device from database
                device = db.query(Device).filter(Device.device_id == device_id).first()
                if not device:
                    self.logger.error(f"Device {device_id} not found in database")
                    return None
                
                # Create security event
                event = SecurityEvent(
                    device_id=device.id,
                    event_type=event_type,
                    event_title=title,
                    event_description=description,
                    severity=severity,
                    detection_method="adb",
                    source_component="security_service",
                    **kwargs
                )
                
                # Calculate risk score if not provided
                if not hasattr(event, 'risk_score') or event.risk_score is None:
                    event.calculate_risk_score()
                
                db.add(event)
                db.commit()
                db.refresh(event)
                
                # Send real-time alert
                await self._send_security_alert(device_id, event)
                
                # Log the event
                self.logger.warning(f"Security event created: {title} (severity: {severity.value})")
                
                return event.id
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error creating security event: {e}")
            return None

    async def _send_security_alert(self, device_id: str, event: SecurityEvent):
        """Send real-time security alert via WebSocket"""
        try:
            alert_data = {
                "event_id": event.id,
                "device_id": device_id,
                "event_type": event.event_type,
                "title": event.event_title,
                "description": event.event_description,
                "severity": event.severity.value,
                "risk_score": event.risk_score,
                "timestamp": event.detected_at.isoformat(),
                "requires_action": event.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
            }
            
            # Send alert via WebSocket
            await self.websocket_manager.send_security_alert(device_id, alert_data)
            
            # Log alert sent
            self.logger.info(f"Security alert sent for device {device_id}: {event.event_title}")
            
        except Exception as e:
            self.logger.error(f"Error sending security alert: {e}")

    # Public API Methods
    
    async def get_security_dashboard(self, device_id: str) -> Dict[str, Any]:
        """Get comprehensive security dashboard data"""
        try:
            # Calculate security score
            security_score = await self._calculate_security_score(device_id)
            
            # Get recent security events (mock - would query database)
            recent_events = []
            
            # Get suspicious apps
            suspicious_apps = await self._detect_suspicious_apps(device_id)
            
            # Get network status
            connections = await self._get_network_connections(device_id)
            active_connections = len([c for c in connections if c.state == "ESTABLISHED"])
            
            # Compile dashboard
            dashboard = {
                "device_id": device_id,
                "security_score": security_score.__dict__,
                "threat_summary": {
                    "active_threats": len(recent_events),
                    "suspicious_apps": len(suspicious_apps),
                    "network_connections": active_connections,
                    "last_scan": datetime.utcnow().isoformat()
                },
                "recent_events": recent_events,
                "suspicious_apps": [app.__dict__ for app in suspicious_apps[:5]],
                "recommendations": security_score.recommendations,
                "monitoring_status": device_id in self._monitoring_tasks
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error getting security dashboard for device {device_id}: {e}")
            raise

    async def perform_security_scan(self, device_id: str, scan_type: str = "full") -> Dict[str, Any]:
        """Perform on-demand security scan"""
        try:
            self.logger.info(f"Starting {scan_type} security scan for device {device_id}")
            
            scan_results = {
                "scan_type": scan_type,
                "device_id": device_id,
                "start_time": datetime.utcnow().isoformat(),
                "results": {},
                "threats_found": 0,
                "recommendations": []
            }
            
            if scan_type in ["full", "apps"]:
                # App permission analysis
                permissions = await self._analyze_app_permissions(device_id)
                suspicious_apps = await self._detect_suspicious_apps(device_id)
                
                scan_results["results"]["permissions"] = {
                    "total_permissions": len(permissions),
                    "dangerous_permissions": len([p for p in permissions if p.is_dangerous and p.granted]),
                    "suspicious_apps": len(suspicious_apps)
                }
                
                scan_results["threats_found"] += len(suspicious_apps)
            
            if scan_type in ["full", "network"]:
                # Network analysis
                await self._monitor_network_activity(device_id)
                connections = await self._get_network_connections(device_id)
                
                scan_results["results"]["network"] = {
                    "active_connections": len(connections),
                    "established_connections": len([c for c in connections if c.state == "ESTABLISHED"]),
                    "listening_ports": len([c for c in connections if c.state == "LISTEN"])
                }
            
            if scan_type in ["full", "system"]:
                # System integrity check
                await self._check_system_integrity(device_id)
                
                # Check for root
                root_check = await self.adb_manager.execute_command(
                    device_id, "which su 2>/dev/null && echo 'rooted'"
                )
                
                scan_results["results"]["system"] = {
                    "is_rooted": "rooted" in root_check.output if root_check.success else False,
                    "developer_options_enabled": False,  # Would be checked properly
                    "adb_enabled": True  # Obviously true since we're using ADB
                }
            
            # Calculate security score
            security_score = await self._calculate_security_score(device_id)
            scan_results["security_score"] = security_score.overall_score
            scan_results["threat_level"] = security_score.threat_level
            scan_results["recommendations"] = security_score.recommendations
            
            scan_results["end_time"] = datetime.utcnow().isoformat()
            scan_results["duration_seconds"] = (datetime.fromisoformat(scan_results["end_time"]) - 
                                               datetime.fromisoformat(scan_results["start_time"])).total_seconds()
            
            self.logger.info(f"Security scan completed for device {device_id}: {scan_results['threats_found']} threats found")
            
            return scan_results
            
        except Exception as e:
            self.logger.error(f"Error performing security scan for device {device_id}: {e}")
            raise

    async def get_security_recommendations(self, device_id: str) -> List[Dict[str, Any]]:
        """Get security recommendations based on device analysis"""
        try:
            recommendations = []
            
            # Get security score with recommendations
            security_score = await self._calculate_security_score(device_id)
            
            # Convert recommendations to detailed format
            for i, rec in enumerate(security_score.recommendations):
                recommendations.append({
                    "id": f"rec_{i}",
                    "title": rec,
                    "description": rec,
                    "priority": "high" if security_score.overall_score < 60 else "medium",
                    "category": "general",
                    "estimated_impact": "medium",
                    "difficulty": "easy",
                    "automated": False
                })
            
            # Add specific recommendations based on findings
            suspicious_apps = await self._detect_suspicious_apps(device_id)
            if suspicious_apps:
                for app in suspicious_apps[:3]:  # Top 3
                    recommendations.append({
                        "id": f"app_{app.package_name}",
                        "title": f"Review {app.app_name}",
                        "description": f"App flagged for: {', '.join(app.reasons)}",
                        "priority": "high" if app.risk_score >= 70 else "medium",
                        "category": "application_security",
                        "estimated_impact": "high",
                        "difficulty": "easy",
                        "automated": False,
                        "action_required": "Review and potentially uninstall this app"
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting security recommendations: {e}")
            raise

    async def acknowledge_security_event(self, event_id: int, user_id: str, notes: str = None) -> bool:
        """Acknowledge a security event"""
        try:
            db = next(get_db())
            
            try:
                event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
                if not event:
                    return False
                
                event.status = EventStatus.INVESTIGATING
                event.investigated_by = user_id
                event.investigation_notes = notes
                event.investigation_started_at = datetime.utcnow()
                
                db.commit()
                
                self.logger.info(f"Security event {event_id} acknowledged by {user_id}")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error acknowledging security event {event_id}: {e}")
            return False

    def get_monitoring_status(self, device_id: str) -> Dict[str, Any]:
        """Get monitoring status for a device"""
        is_monitoring = device_id in self._monitoring_tasks
        task = self._monitoring_tasks.get(device_id)
        
        status = {
            "device_id": device_id,
            "is_monitoring": is_monitoring,
            "task_status": "running" if task and not task.done() else "stopped",
            "baseline_initialized": device_id in self._device_baselines,
            "activity_history_count": len(self._activity_history[device_id]) if device_id in self._activity_history else 0
        }
        
        if device_id in self._device_baselines:
            baseline = self._device_baselines[device_id]
            status["baseline_info"] = {
                "initialization_time": baseline["initialization_time"].isoformat(),
                "total_apps": baseline.get("total_apps", 0),
                "last_scan": baseline.get("last_network_scan", baseline["initialization_time"]).isoformat()
            }
        
        return status

    async def shutdown(self):
        """Shutdown security service and cleanup resources"""
        try:
            self.logger.info("Shutting down security service...")
            
            # Stop all monitoring tasks
            for device_id in list(self._monitoring_tasks.keys()):
                await self.stop_monitoring(device_id)
            
            # Clear state
            self._device_baselines.clear()
            self._activity_history.clear()
            self._network_baselines.clear()
            
            self.logger.info("Security service shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during security service shutdown: {e}")


# Factory function for creating security service
def create_security_service(adb_manager: AdbManager, websocket_manager: WebSocketManager) -> SecurityAnalysisService:
    """Create security analysis service with proper dependencies"""
    return SecurityAnalysisService(adb_manager, websocket_manager)

