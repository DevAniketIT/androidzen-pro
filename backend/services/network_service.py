"""
Network Optimization Center for AndroidZen Pro

This service provides comprehensive network monitoring, optimization, and analysis:
- Network diagnostics (ping, traceroute, DNS tests)
- WiFi signal strength analyzer and optimization
- Mobile data usage tracker with intelligent alerts
- Connection troubleshooting automation
- Network speed testing with historical tracking
- Optimization recommendations with performance impact analysis
- Network history and analytics with trend detection
- Real-time network monitoring and alerting
"""

import asyncio
import hashlib
import ipaddress
import json
import logging
import re
import statistics
import subprocess
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, NamedTuple

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .core.adb_manager import AdbManager
from .core.websocket_manager import WebSocketManager
from .models.device import Device
from .models.analytics import Analytics


class NetworkType(Enum):
    """Network connection types"""
    WIFI = "wifi"
    MOBILE = "mobile"
    ETHERNET = "ethernet"
    VPN = "vpn"
    UNKNOWN = "unknown"


class ConnectionStatus(Enum):
    """Network connection status"""
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    LIMITED = "limited"
    FAILED = "failed"


class OptimizationType(Enum):
    """Network optimization types"""
    DNS = "dns"
    TCP = "tcp"
    WIFI = "wifi"
    MOBILE_DATA = "mobile_data"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


class AlertSeverity(Enum):
    """Network alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NetworkInterface:
    """Network interface information"""
    name: str
    type: NetworkType
    is_active: bool
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    mac_address: Optional[str] = None
    mtu: Optional[int] = None
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WiFiNetwork:
    """WiFi network information"""
    ssid: str
    bssid: str
    frequency: int
    signal_strength: int  # dBm
    security_type: str
    channel: int
    bandwidth: str
    is_connected: bool = False
    is_saved: bool = False
    quality_score: Optional[float] = None
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MobileNetwork:
    """Mobile network information"""
    carrier: str
    network_type: str  # LTE, 5G, 3G, etc.
    signal_strength: int  # dBm
    signal_quality: Optional[float]
    cell_id: Optional[str]
    lac: Optional[str]
    mcc: Optional[str]  # Mobile Country Code
    mnc: Optional[str]  # Mobile Network Code
    is_roaming: bool = False
    data_state: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkSpeedTestResult:
    """Network speed test results"""
    test_id: str
    device_id: str
    test_type: str  # download, upload, ping
    server_id: str
    server_name: str
    server_location: str
    start_time: datetime
    end_time: datetime
    download_speed: float  # Mbps
    upload_speed: float  # Mbps
    latency: float  # milliseconds
    jitter: float  # milliseconds
    packet_loss: float  # percentage
    network_type: NetworkType
    signal_strength: Optional[int] = None
    test_duration: float = 0.0
    bytes_sent: int = 0
    bytes_received: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        data['network_type'] = self.network_type.value
        return data


@dataclass
class NetworkDiagnosticResult:
    """Network diagnostic test result"""
    test_type: str  # ping, traceroute, dns_lookup, port_scan
    target: str
    status: str  # success, failed, timeout
    response_time: Optional[float] = None
    hops: Optional[List[Dict[str, Any]]] = None
    resolved_ip: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class DataUsageStats:
    """Data usage statistics"""
    interface: str
    period_start: datetime
    period_end: datetime
    rx_bytes: int
    tx_bytes: int
    total_bytes: int
    app_usage: Dict[str, int] = field(default_factory=dict)
    daily_average: float = 0.0
    weekly_trend: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['period_start'] = self.period_start.isoformat()
        data['period_end'] = self.period_end.isoformat()
        return data


@dataclass
class NetworkOptimization:
    """Network optimization recommendation"""
    optimization_type: OptimizationType
    title: str
    description: str
    current_value: Any
    recommended_value: Any
    expected_improvement: float  # percentage
    impact_level: str  # low, medium, high
    safety_level: str  # safe, moderate, risky
    commands: List[str]
    prerequisites: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['optimization_type'] = self.optimization_type.value
        return data


@dataclass
class NetworkAlert:
    """Network monitoring alert"""
    alert_id: str
    device_id: str
    alert_type: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    threshold_value: float
    current_value: float
    timestamp: datetime
    is_resolved: bool = False
    resolution_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolution_time:
            data['resolution_time'] = self.resolution_time.isoformat()
        return data


class NetworkOptimizationService:
    """Comprehensive Network Optimization Center"""
    
    def __init__(self, adb_manager: AdbManager, websocket_manager: WebSocketManager):
        self.adb_manager = adb_manager
        self.websocket_manager = websocket_manager
        self.logger = logging.getLogger(__name__)
        
        # Network monitoring state
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._network_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._speed_test_history: Dict[str, List[NetworkSpeedTestResult]] = defaultdict(list)
        self._active_alerts: Dict[str, List[NetworkAlert]] = defaultdict(list)
        
        # Network optimization cache
        self._optimization_cache: Dict[str, List[NetworkOptimization]] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        
        # Speed test servers (public servers for testing)
        self.speed_test_servers = [
            {"id": "speedtest_net", "name": "Speedtest.net", "location": "Auto", "host": "speedtest.net"},
            {"id": "fast_com", "name": "Fast.com", "location": "Netflix", "host": "fast.com"},
            {"id": "google", "name": "Google", "location": "Global", "host": "gstatic.com"}
        ]
        
        # DNS servers for optimization
        self.public_dns_servers = {
            "google": {"primary": "8.8.8.8", "secondary": "8.8.4.4", "name": "Google DNS"},
            "cloudflare": {"primary": "1.1.1.1", "secondary": "1.0.0.1", "name": "Cloudflare DNS"},
            "opendns": {"primary": "208.67.222.222", "secondary": "208.67.220.220", "name": "OpenDNS"},
            "quad9": {"primary": "9.9.9.9", "secondary": "149.112.112.112", "name": "Quad9 DNS"}
        }
        
        # Network monitoring thresholds
        self.alert_thresholds = {
            "signal_strength_wifi": -70,  # dBm
            "signal_strength_mobile": -90,  # dBm
            "latency": 100,  # milliseconds
            "packet_loss": 5,  # percentage
            "download_speed_min": 5,  # Mbps
            "upload_speed_min": 1,  # Mbps
            "data_usage_daily": 1024,  # MB
            "connection_drops": 5  # per hour
        }

    # Network Interface Management
    
    async def get_network_interfaces(self, device_id: str) -> List[NetworkInterface]:
        """Get all network interfaces on the device"""
        interfaces = []
        
        try:
            # Get network interfaces
            result = await self.adb_manager.execute_command(
                device_id, "ip addr show 2>/dev/null || ifconfig -a 2>/dev/null"
            )
            
            if not result.success:
                self.logger.warning(f"Failed to get network interfaces for device {device_id}")
                return interfaces
            
            current_interface = None
            
            for line in result.output.split('\n'):
                line = line.strip()
                
                # Parse ip addr output format
                if re.match(r'^\d+:', line):
                    if current_interface:
                        interfaces.append(current_interface)
                    
                    # Extract interface name
                    match = re.search(r'^\d+:\s*([^:@]+)', line)
                    if match:
                        interface_name = match.group(1).strip()
                        
                        # Determine interface type
                        if 'wlan' in interface_name or 'wifi' in interface_name:
                            net_type = NetworkType.WIFI
                        elif 'rmnet' in interface_name or 'mobile' in interface_name:
                            net_type = NetworkType.MOBILE
                        elif 'eth' in interface_name:
                            net_type = NetworkType.ETHERNET
                        elif 'tun' in interface_name or 'ppp' in interface_name:
                            net_type = NetworkType.VPN
                        else:
                            net_type = NetworkType.UNKNOWN
                        
                        current_interface = NetworkInterface(
                            name=interface_name,
                            type=net_type,
                            is_active='UP' in line and 'LOWER_UP' in line
                        )
                
                elif current_interface:
                    # Parse IP address
                    ip_match = re.search(r'inet ([0-9.]+)/(\d+)', line)
                    if ip_match:
                        current_interface.ip_address = ip_match.group(1)
                        # Calculate subnet mask from CIDR
                        cidr = int(ip_match.group(2))
                        current_interface.subnet_mask = self._cidr_to_netmask(cidr)
                    
                    # Parse MAC address
                    mac_match = re.search(r'(?:link/ether|HWaddr)\s+([0-9a-fA-F:]{17})', line)
                    if mac_match:
                        current_interface.mac_address = mac_match.group(1)
                    
                    # Parse MTU
                    mtu_match = re.search(r'mtu\s+(\d+)', line)
                    if mtu_match:
                        current_interface.mtu = int(mtu_match.group(1))
            
            # Add the last interface
            if current_interface:
                interfaces.append(current_interface)
            
            # Get traffic statistics
            for interface in interfaces:
                await self._update_interface_stats(device_id, interface)
            
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Error getting network interfaces for device {device_id}: {e}")
            return interfaces

    def _cidr_to_netmask(self, cidr: int) -> str:
        """Convert CIDR notation to subnet mask"""
        try:
            network = ipaddress.IPv4Network(f"0.0.0.0/{cidr}", strict=False)
            return str(network.netmask)
        except:
            return "255.255.255.0"  # Default

    async def _update_interface_stats(self, device_id: str, interface: NetworkInterface):
        """Update network interface statistics"""
        try:
            # Get interface statistics
            stats_result = await self.adb_manager.execute_command(
                device_id, f"cat /sys/class/net/{interface.name}/statistics/* 2>/dev/null"
            )
            
            if stats_result.success:
                # This is a simplified approach; real implementation would parse specific stat files
                # For now, we'll use mock data
                import random
                interface.rx_bytes = random.randint(1000000, 100000000)
                interface.tx_bytes = random.randint(500000, 50000000)
                interface.rx_packets = random.randint(1000, 100000)
                interface.tx_packets = random.randint(500, 50000)
                interface.rx_errors = random.randint(0, 10)
                interface.tx_errors = random.randint(0, 5)
            
        except Exception as e:
            self.logger.debug(f"Error updating interface stats for {interface.name}: {e}")

    # WiFi Analysis
    
    async def get_wifi_networks(self, device_id: str, include_scan: bool = True) -> List[WiFiNetwork]:
        """Get available WiFi networks"""
        networks = []
        
        try:
            if include_scan:
                # Trigger WiFi scan
                scan_result = await self.adb_manager.execute_command(
                    device_id, "dumpsys wifi | grep -A 1000 'Latest scan results:'"
                )
            
            # Get WiFi scan results
            result = await self.adb_manager.execute_command(
                device_id, "dumpsys wifi | grep -E '(SSID|BSSID|freq|level|capabilities)'"
            )
            
            if not result.success:
                return networks
            
            current_network = {}
            
            for line in result.output.split('\n'):
                line = line.strip()
                
                if 'SSID:' in line:
                    if current_network and current_network.get('ssid'):
                        networks.append(self._create_wifi_network(current_network))
                    current_network = {'ssid': line.split('SSID: ')[-1].strip('"')}
                
                elif 'BSSID:' in line:
                    current_network['bssid'] = line.split('BSSID: ')[-1].strip()
                
                elif 'freq:' in line:
                    freq_match = re.search(r'freq: (\d+)', line)
                    if freq_match:
                        current_network['frequency'] = int(freq_match.group(1))
                
                elif 'level:' in line:
                    level_match = re.search(r'level: (-?\d+)', line)
                    if level_match:
                        current_network['signal_strength'] = int(level_match.group(1))
                
                elif 'capabilities:' in line:
                    caps_match = re.search(r'capabilities: \[(.*?)\]', line)
                    if caps_match:
                        current_network['capabilities'] = caps_match.group(1).split(', ')
            
            # Add the last network
            if current_network and current_network.get('ssid'):
                networks.append(self._create_wifi_network(current_network))
            
            # Get connected network info
            await self._update_connected_wifi_status(device_id, networks)
            
            return networks
            
        except Exception as e:
            self.logger.error(f"Error getting WiFi networks for device {device_id}: {e}")
            return networks

    def _create_wifi_network(self, network_data: Dict) -> WiFiNetwork:
        """Create WiFiNetwork object from parsed data"""
        # Determine security type
        capabilities = network_data.get('capabilities', [])
        if 'WPA3' in capabilities:
            security_type = 'WPA3'
        elif 'WPA2' in capabilities or 'WPA-PSK' in capabilities:
            security_type = 'WPA2'
        elif 'WEP' in capabilities:
            security_type = 'WEP'
        elif any('OPEN' in cap for cap in capabilities):
            security_type = 'Open'
        else:
            security_type = 'Unknown'
        
        # Calculate channel from frequency
        frequency = network_data.get('frequency', 2412)
        if frequency >= 5000:
            # 5GHz band
            channel = (frequency - 5000) // 5
        else:
            # 2.4GHz band
            if frequency == 2484:
                channel = 14
            else:
                channel = (frequency - 2412) // 5 + 1
        
        # Calculate quality score
        signal_strength = network_data.get('signal_strength', -100)
        quality_score = max(0, min(100, (signal_strength + 100) * 2))
        
        return WiFiNetwork(
            ssid=network_data.get('ssid', 'Unknown'),
            bssid=network_data.get('bssid', ''),
            frequency=frequency,
            signal_strength=signal_strength,
            security_type=security_type,
            channel=channel,
            bandwidth='20MHz',  # Default, would need more detailed parsing
            quality_score=quality_score,
            capabilities=capabilities
        )

    async def _update_connected_wifi_status(self, device_id: str, networks: List[WiFiNetwork]):
        """Update connection status for WiFi networks"""
        try:
            # Get connected WiFi info
            result = await self.adb_manager.execute_command(
                device_id, "dumpsys wifi | grep -E '(mWifiInfo|mNetworkInfo)'"
            )
            
            if result.success:
                connected_ssid = None
                connected_bssid = None
                
                for line in result.output.split('\n'):
                    if 'SSID:' in line:
                        ssid_match = re.search(r'SSID: "([^"]*)"', line)
                        if ssid_match:
                            connected_ssid = ssid_match.group(1)
                    
                    if 'BSSID:' in line:
                        bssid_match = re.search(r'BSSID: ([0-9a-fA-F:]{17})', line)
                        if bssid_match:
                            connected_bssid = bssid_match.group(1)
                
                # Mark connected network
                for network in networks:
                    if (network.ssid == connected_ssid and 
                        network.bssid == connected_bssid):
                        network.is_connected = True
                        break
            
        except Exception as e:
            self.logger.debug(f"Error updating WiFi connection status: {e}")

    async def analyze_wifi_signal_strength(self, device_id: str) -> Dict[str, Any]:
        """Analyze WiFi signal strength and provide recommendations"""
        try:
            networks = await self.get_wifi_networks(device_id, include_scan=True)
            connected_network = next((n for n in networks if n.is_connected), None)
            
            analysis = {
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "connected_network": None,
                "signal_analysis": {},
                "recommendations": [],
                "optimization_suggestions": []
            }
            
            if not connected_network:
                analysis["recommendations"].append("No active WiFi connection detected")
                return analysis
            
            analysis["connected_network"] = connected_network.to_dict()
            
            # Analyze signal strength
            signal_strength = connected_network.signal_strength
            
            if signal_strength >= -30:
                signal_quality = "Excellent"
                quality_color = "green"
            elif signal_strength >= -67:
                signal_quality = "Good"
                quality_color = "yellow"
            elif signal_strength >= -70:
                signal_quality = "Fair"
                quality_color = "orange"
            else:
                signal_quality = "Poor"
                quality_color = "red"
            
            analysis["signal_analysis"] = {
                "strength_dbm": signal_strength,
                "quality": signal_quality,
                "quality_color": quality_color,
                "quality_percentage": max(0, min(100, (signal_strength + 100) * 2)),
                "frequency_band": "5GHz" if connected_network.frequency >= 5000 else "2.4GHz",
                "channel": connected_network.channel,
                "security": connected_network.security_type
            }
            
            # Generate recommendations
            if signal_strength < -70:
                analysis["recommendations"].extend([
                    "Move closer to the WiFi router",
                    "Check for physical obstructions between device and router",
                    "Consider using a WiFi extender or mesh network"
                ])
            
            if connected_network.frequency < 5000:
                analysis["recommendations"].append("Consider switching to 5GHz band if available")
            
            # Channel congestion analysis
            nearby_networks = [n for n in networks if abs(n.channel - connected_network.channel) <= 2]
            if len(nearby_networks) > 3:
                analysis["recommendations"].append(f"Channel {connected_network.channel} appears congested. Consider changing WiFi channel.")
            
            # Optimization suggestions
            analysis["optimization_suggestions"] = await self._generate_wifi_optimizations(device_id, connected_network)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing WiFi signal strength for device {device_id}: {e}")
            return {"error": str(e), "device_id": device_id}

    async def _generate_wifi_optimizations(self, device_id: str, network: WiFiNetwork) -> List[Dict[str, Any]]:
        """Generate WiFi optimization suggestions"""
        optimizations = []
        
        try:
            # Check WiFi power saving mode
            power_result = await self.adb_manager.execute_command(
                device_id, "dumpsys wifi | grep -i 'power save'"
            )
            
            if power_result.success and 'enabled' in power_result.output.lower():
                optimizations.append({
                    "type": "wifi_power_save",
                    "title": "Disable WiFi Power Saving",
                    "description": "WiFi power saving mode can reduce performance",
                    "impact": "medium",
                    "command": "settings put global wifi_power_save_mode 0"
                })
            
            # Frequency band optimization
            if network.frequency < 5000:
                optimizations.append({
                    "type": "frequency_band",
                    "title": "Use 5GHz Band",
                    "description": "5GHz typically offers better performance and less congestion",
                    "impact": "high",
                    "manual_action": "Switch to 5GHz network in WiFi settings"
                })
            
            # Channel optimization
            if network.channel in [1, 6, 11]:  # Common congested channels
                optimizations.append({
                    "type": "channel_optimization",
                    "title": "Optimize WiFi Channel",
                    "description": f"Channel {network.channel} may be congested",
                    "impact": "medium",
                    "manual_action": "Change router channel to less congested option"
                })
            
            return optimizations
            
        except Exception as e:
            self.logger.debug(f"Error generating WiFi optimizations: {e}")
            return optimizations

    # Mobile Network Analysis
    
    async def get_mobile_network_info(self, device_id: str) -> Optional[MobileNetwork]:
        """Get mobile network information"""
        try:
            # Get mobile network info
            result = await self.adb_manager.execute_command(
                device_id, "dumpsys telephony.registry | grep -E '(mSignalStrength|mDataConnectionState|mServiceState)'"
            )
            
            if not result.success:
                return None
            
            mobile_info = {
                "signal_strength": -100,
                "network_type": "Unknown",
                "carrier": "Unknown",
                "is_roaming": False,
                "data_state": "unknown"
            }
            
            # Parse mobile network information
            for line in result.output.split('\n'):
                line = line.strip()
                
                # Signal strength
                if 'mSignalStrength' in line:
                    strength_match = re.search(r'rssi=(-?\d+)', line)
                    if strength_match:
                        mobile_info["signal_strength"] = int(strength_match.group(1))
                
                # Network type
                if 'mDataNetworkType' in line:
                    type_match = re.search(r'mDataNetworkType=(\d+)', line)
                    if type_match:
                        network_type_id = int(type_match.group(1))
                        mobile_info["network_type"] = self._get_network_type_name(network_type_id)
                
                # Data connection state
                if 'mDataConnectionState' in line:
                    state_match = re.search(r'mDataConnectionState=(\d+)', line)
                    if state_match:
                        state_id = int(state_match.group(1))
                        mobile_info["data_state"] = "connected" if state_id == 2 else "disconnected"
                
                # Roaming status
                if 'mServiceState' in line and 'roaming' in line.lower():
                    mobile_info["is_roaming"] = 'true' in line.lower()
            
            # Get carrier information
            carrier_result = await self.adb_manager.execute_command(
                device_id, "getprop gsm.operator.alpha"
            )
            if carrier_result.success and carrier_result.output.strip():
                mobile_info["carrier"] = carrier_result.output.strip()
            
            # Calculate signal quality
            signal_strength = mobile_info["signal_strength"]
            signal_quality = max(0, min(100, (signal_strength + 113) * 2))
            
            return MobileNetwork(
                carrier=mobile_info["carrier"],
                network_type=mobile_info["network_type"],
                signal_strength=signal_strength,
                signal_quality=signal_quality,
                is_roaming=mobile_info["is_roaming"],
                data_state=mobile_info["data_state"]
            )
            
        except Exception as e:
            self.logger.error(f"Error getting mobile network info for device {device_id}: {e}")
            return None

    def _get_network_type_name(self, type_id: int) -> str:
        """Convert network type ID to human-readable name"""
        network_types = {
            0: "Unknown",
            1: "GPRS",
            2: "EDGE",
            3: "UMTS",
            4: "CDMA",
            5: "EVDO_0",
            6: "EVDO_A",
            7: "1xRTT",
            8: "HSDPA",
            9: "HSUPA",
            10: "HSPA",
            11: "iDEN",
            12: "EVDO_B",
            13: "LTE",
            14: "eHRPD",
            15: "HSPA+",
            16: "GSM",
            17: "TD_SCDMA",
            18: "IWLAN",
            19: "LTE_CA",
            20: "NR"  # 5G
        }
        return network_types.get(type_id, "Unknown")

    # Data Usage Tracking
    
    async def get_data_usage_stats(self, device_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Get comprehensive data usage statistics"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=period_days)
            
            # Get network usage data
            usage_result = await self.adb_manager.execute_command(
                device_id, "dumpsys netstats summary"
            )
            
            stats = {
                "device_id": device_id,
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "total_usage": {"rx_bytes": 0, "tx_bytes": 0, "total_bytes": 0},
                "wifi_usage": {"rx_bytes": 0, "tx_bytes": 0, "total_bytes": 0},
                "mobile_usage": {"rx_bytes": 0, "tx_bytes": 0, "total_bytes": 0},
                "app_usage": {},
                "daily_breakdown": [],
                "alerts": []
            }
            
            if usage_result.success:
                # Parse network usage (simplified)
                import random
                
                # Mock data usage stats
                wifi_rx = random.randint(500_000_000, 5_000_000_000)  # 500MB - 5GB
                wifi_tx = random.randint(100_000_000, 1_000_000_000)  # 100MB - 1GB
                mobile_rx = random.randint(100_000_000, 2_000_000_000)  # 100MB - 2GB
                mobile_tx = random.randint(50_000_000, 500_000_000)  # 50MB - 500MB
                
                stats["wifi_usage"] = {
                    "rx_bytes": wifi_rx,
                    "tx_bytes": wifi_tx,
                    "total_bytes": wifi_rx + wifi_tx
                }
                
                stats["mobile_usage"] = {
                    "rx_bytes": mobile_rx,
                    "tx_bytes": mobile_tx,
                    "total_bytes": mobile_rx + mobile_tx
                }
                
                stats["total_usage"] = {
                    "rx_bytes": wifi_rx + mobile_rx,
                    "tx_bytes": wifi_tx + mobile_tx,
                    "total_bytes": wifi_rx + wifi_tx + mobile_rx + mobile_tx
                }
                
                # Mock app usage breakdown
                apps = ["com.android.chrome", "com.youtube.android", "com.spotify.music", 
                       "com.whatsapp", "com.facebook.android"]
                for app in apps:
                    usage = random.randint(10_000_000, 500_000_000)  # 10MB - 500MB
                    stats["app_usage"][app] = usage
                
                # Generate daily breakdown
                for i in range(min(period_days, 7)):  # Last 7 days
                    day_date = end_time - timedelta(days=i)
                    daily_usage = random.randint(50_000_000, 500_000_000)  # 50MB - 500MB
                    stats["daily_breakdown"].append({
                        "date": day_date.strftime("%Y-%m-%d"),
                        "usage_bytes": daily_usage,
                        "usage_mb": round(daily_usage / (1024 * 1024), 2)
                    })
                
                # Check for usage alerts
                daily_avg = stats["total_usage"]["total_bytes"] / period_days
                if daily_avg > self.alert_thresholds["data_usage_daily"] * 1024 * 1024:
                    stats["alerts"].append({
                        "type": "high_daily_usage",
                        "message": f"Daily average exceeds {self.alert_thresholds['data_usage_daily']}MB",
                        "value": round(daily_avg / (1024 * 1024), 2)
                    })
                
                # Mobile vs WiFi ratio alert
                if stats["mobile_usage"]["total_bytes"] > stats["wifi_usage"]["total_bytes"]:
                    stats["alerts"].append({
                        "type": "mobile_heavy_usage",
                        "message": "Mobile data usage exceeds WiFi usage",
                        "recommendation": "Consider using WiFi more often to save mobile data"
                    })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting data usage stats for device {device_id}: {e}")
            return {"error": str(e), "device_id": device_id}

    async def track_app_data_usage(self, device_id: str) -> Dict[str, Any]:
        """Track per-application data usage"""
        try:
            # Get per-app network usage
            result = await self.adb_manager.execute_command(
                device_id, "dumpsys package | grep -E '(Package|dataDir)' | head -50"
            )
            
            app_usage = {}
            
            if result.success:
                # This would require more sophisticated parsing in a real implementation
                # For now, we'll generate mock data for demonstration
                
                # Get list of installed packages
                packages_result = await self.adb_manager.execute_command(
                    device_id, "pm list packages | head -20"
                )
                
                if packages_result.success:
                    packages = []
                    for line in packages_result.output.split('\n'):
                        if line.startswith('package:'):
                            packages.append(line.replace('package:', '').strip())
                    
                    # Generate mock usage data
                    import random
                    for package in packages[:10]:  # Top 10 apps
                        app_usage[package] = {
                            "package_name": package,
                            "wifi_rx": random.randint(1_000_000, 100_000_000),
                            "wifi_tx": random.randint(500_000, 50_000_000),
                            "mobile_rx": random.randint(500_000, 50_000_000),
                            "mobile_tx": random.randint(100_000, 10_000_000),
                            "last_activity": (datetime.utcnow() - timedelta(
                                hours=random.randint(1, 24))).isoformat()
                        }
                        
                        # Calculate total
                        total = (app_usage[package]["wifi_rx"] + 
                                app_usage[package]["wifi_tx"] +
                                app_usage[package]["mobile_rx"] + 
                                app_usage[package]["mobile_tx"])
                        app_usage[package]["total_bytes"] = total
            
            # Sort by total usage
            sorted_apps = sorted(app_usage.items(), 
                               key=lambda x: x[1]["total_bytes"], 
                               reverse=True)
            
            return {
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_apps": len(app_usage),
                "app_usage": dict(sorted_apps),
                "top_consumers": [{"package": k, **v} for k, v in sorted_apps[:5]]
            }
            
        except Exception as e:
            self.logger.error(f"Error tracking app data usage for device {device_id}: {e}")
            return {"error": str(e), "device_id": device_id}

    # Network Diagnostics
    
    async def run_ping_test(self, device_id: str, target: str = "8.8.8.8", count: int = 4) -> NetworkDiagnosticResult:
        """Run ping diagnostic test"""
        try:
            start_time = datetime.utcnow()
            
            # Run ping command
            result = await self.adb_manager.execute_command(
                device_id, f"ping -c {count} {target} 2>&1"
            )
            
            if result.success:
                output = result.output
                
                # Parse ping results
                packet_loss = 0.0
                avg_time = None
                
                for line in output.split('\n'):
                    # Parse packet loss
                    if '% packet loss' in line:
                        loss_match = re.search(r'(\d+)% packet loss', line)
                        if loss_match:
                            packet_loss = float(loss_match.group(1))
                    
                    # Parse average time
                    elif 'min/avg/max' in line or 'avg' in line:
                        time_match = re.search(r'avg[=:]?\s*(\d+(?:\.\d+)?)', line)
                        if time_match:
                            avg_time = float(time_match.group(1))
                
                status = "success" if packet_loss < 100 else "failed"
                
                return NetworkDiagnosticResult(
                    test_type="ping",
                    target=target,
                    status=status,
                    response_time=avg_time,
                    error_message=None if status == "success" else "High packet loss",
                    timestamp=start_time
                )
            else:
                return NetworkDiagnosticResult(
                    test_type="ping",
                    target=target,
                    status="failed",
                    error_message=result.error or "Ping command failed",
                    timestamp=start_time
                )
                
        except Exception as e:
            self.logger.error(f"Error running ping test: {e}")
            return NetworkDiagnosticResult(
                test_type="ping",
                target=target,
                status="failed",
                error_message=str(e),
                timestamp=datetime.utcnow()
            )

    async def run_traceroute_test(self, device_id: str, target: str = "8.8.8.8") -> NetworkDiagnosticResult:
        """Run traceroute diagnostic test"""
        try:
            start_time = datetime.utcnow()
            
            # Run traceroute command
            result = await self.adb_manager.execute_command(
                device_id, f"traceroute {target} 2>&1 || ping -R -c 1 {target} 2>&1"
            )
            
            hops = []
            
            if result.success:
                for line_num, line in enumerate(result.output.split('\n'), 1):
                    # Parse traceroute output
                    hop_match = re.search(r'(\d+)\s+([0-9.]+)\s+.*?(\d+(?:\.\d+)?)\s*ms', line)
                    if hop_match:
                        hops.append({
                            "hop": int(hop_match.group(1)),
                            "ip": hop_match.group(2),
                            "response_time": float(hop_match.group(3))
                        })
                    elif line_num <= 10:  # Limit parsing
                        # Try alternative parsing for different formats
                        ip_match = re.search(r'([0-9.]+)', line)
                        time_match = re.search(r'(\d+(?:\.\d+)?)\s*ms', line)
                        if ip_match:
                            hops.append({
                                "hop": line_num,
                                "ip": ip_match.group(1),
                                "response_time": float(time_match.group(1)) if time_match else None
                            })
                
                return NetworkDiagnosticResult(
                    test_type="traceroute",
                    target=target,
                    status="success" if hops else "failed",
                    hops=hops,
                    error_message=None if hops else "No route information found",
                    timestamp=start_time
                )
            else:
                return NetworkDiagnosticResult(
                    test_type="traceroute",
                    target=target,
                    status="failed",
                    error_message=result.error or "Traceroute command failed",
                    timestamp=start_time
                )
                
        except Exception as e:
            self.logger.error(f"Error running traceroute test: {e}")
            return NetworkDiagnosticResult(
                test_type="traceroute",
                target=target,
                status="failed",
                error_message=str(e),
                timestamp=datetime.utcnow()
            )

    async def run_dns_test(self, device_id: str, domain: str = "google.com") -> NetworkDiagnosticResult:
        """Run DNS lookup test"""
        try:
            start_time = datetime.utcnow()
            
            # Run DNS lookup
            result = await self.adb_manager.execute_command(
                device_id, f"nslookup {domain} 2>&1 || getent hosts {domain} 2>&1"
            )
            
            if result.success:
                resolved_ip = None
                response_time = None
                
                for line in result.output.split('\n'):
                    # Look for IP address resolution
                    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match and not resolved_ip:
                        resolved_ip = ip_match.group(1)
                    
                    # Try to extract timing information
                    if 'time' in line.lower():
                        time_match = re.search(r'(\d+(?:\.\d+)?)\s*ms', line)
                        if time_match:
                            response_time = float(time_match.group(1))
                
                # Calculate response time if not found
                if not response_time:
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds() * 1000
                
                return NetworkDiagnosticResult(
                    test_type="dns_lookup",
                    target=domain,
                    status="success" if resolved_ip else "failed",
                    resolved_ip=resolved_ip,
                    response_time=response_time,
                    error_message=None if resolved_ip else "DNS resolution failed",
                    timestamp=start_time
                )
            else:
                return NetworkDiagnosticResult(
                    test_type="dns_lookup",
                    target=domain,
                    status="failed",
                    error_message=result.error or "DNS lookup command failed",
                    timestamp=start_time
                )
                
        except Exception as e:
            self.logger.error(f"Error running DNS test: {e}")
            return NetworkDiagnosticResult(
                test_type="dns_lookup",
                target=domain,
                status="failed",
                error_message=str(e),
                timestamp=datetime.utcnow()
            )

    async def run_comprehensive_diagnostics(self, device_id: str) -> Dict[str, Any]:
        """Run comprehensive network diagnostics"""
        try:
            self.logger.info(f"Starting comprehensive network diagnostics for device {device_id}")
            
            diagnostics = {
                "device_id": device_id,
                "start_time": datetime.utcnow().isoformat(),
                "tests": {},
                "summary": {},
                "recommendations": []
            }
            
            # Run ping test
            ping_result = await self.run_ping_test(device_id)
            diagnostics["tests"]["ping"] = ping_result.to_dict()
            
            # Run DNS test
            dns_result = await self.run_dns_test(device_id)
            diagnostics["tests"]["dns"] = dns_result.to_dict()
            
            # Run traceroute test
            traceroute_result = await self.run_traceroute_test(device_id)
            diagnostics["tests"]["traceroute"] = traceroute_result.to_dict()
            
            # Analyze results and generate summary
            passed_tests = 0
            failed_tests = 0
            
            for test_name, test_result in diagnostics["tests"].items():
                if test_result["status"] == "success":
                    passed_tests += 1
                else:
                    failed_tests += 1
            
            diagnostics["summary"] = {
                "total_tests": passed_tests + failed_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": round((passed_tests / (passed_tests + failed_tests)) * 100, 1)
            }
            
            # Generate recommendations
            if ping_result.status == "failed":
                diagnostics["recommendations"].append("Internet connectivity issues detected. Check network settings.")
            elif ping_result.response_time and ping_result.response_time > 100:
                diagnostics["recommendations"].append("High latency detected. Consider optimizing network connection.")
            
            if dns_result.status == "failed":
                diagnostics["recommendations"].append("DNS resolution issues detected. Consider changing DNS servers.")
            elif dns_result.response_time and dns_result.response_time > 50:
                diagnostics["recommendations"].append("Slow DNS resolution. Consider using faster DNS servers.")
            
            if traceroute_result.status == "failed":
                diagnostics["recommendations"].append("Network routing issues detected. Contact network administrator.")
            
            diagnostics["end_time"] = datetime.utcnow().isoformat()
            
            return diagnostics
            
        except Exception as e:
            self.logger.error(f"Error running comprehensive diagnostics for device {device_id}: {e}")
            return {"error": str(e), "device_id": device_id}

    # Speed Testing
    
    async def run_speed_test(self, device_id: str, server_id: str = None, test_duration: int = 30) -> NetworkSpeedTestResult:
        """Run network speed test"""
        try:
            test_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            # Select test server
            if server_id:
                server = next((s for s in self.speed_test_servers if s["id"] == server_id), self.speed_test_servers[0])
            else:
                server = self.speed_test_servers[0]
            
            self.logger.info(f"Starting speed test for device {device_id} using server {server['name']}")
            
            # Get current network type
            network_type = await self._detect_network_type(device_id)
            signal_strength = await self._get_current_signal_strength(device_id, network_type)
            
            # Simulate speed test (in real implementation, this would use speedtest-cli or similar)
            # For demonstration, we'll generate realistic values based on network type
            await asyncio.sleep(min(test_duration, 5))  # Simulate test duration
            
            if network_type == NetworkType.WIFI:
                download_speed = random.uniform(20, 150)
                upload_speed = random.uniform(5, 75)
                latency = random.uniform(8, 50)
                jitter = random.uniform(0.5, 5)
                packet_loss = random.uniform(0, 2)
            elif network_type == NetworkType.MOBILE:
                download_speed = random.uniform(5, 100)
                upload_speed = random.uniform(1, 50)
                latency = random.uniform(15, 100)
                jitter = random.uniform(1, 15)
                packet_loss = random.uniform(0, 5)
            else:
                download_speed = random.uniform(1, 50)
                upload_speed = random.uniform(0.5, 25)
                latency = random.uniform(20, 200)
                jitter = random.uniform(2, 20)
                packet_loss = random.uniform(0, 10)
            
            end_time = datetime.utcnow()
            test_duration_actual = (end_time - start_time).total_seconds()
            
            # Estimate bytes transferred
            bytes_received = int(download_speed * 1024 * 1024 / 8 * test_duration_actual)
            bytes_sent = int(upload_speed * 1024 * 1024 / 8 * test_duration_actual)
            
            result = NetworkSpeedTestResult(
                test_id=test_id,
                device_id=device_id,
                test_type="comprehensive",
                server_id=server["id"],
                server_name=server["name"],
                server_location=server["location"],
                start_time=start_time,
                end_time=end_time,
                download_speed=round(download_speed, 2),
                upload_speed=round(upload_speed, 2),
                latency=round(latency, 2),
                jitter=round(jitter, 2),
                packet_loss=round(packet_loss, 2),
                network_type=network_type,
                signal_strength=signal_strength,
                test_duration=test_duration_actual,
                bytes_sent=bytes_sent,
                bytes_received=bytes_received
            )
            
            # Store result in history
            self._speed_test_history[device_id].append(result)
            
            # Keep only last 50 results per device
            if len(self._speed_test_history[device_id]) > 50:
                self._speed_test_history[device_id] = self._speed_test_history[device_id][-50:]
            
            self.logger.info(f"Speed test completed for device {device_id}: {download_speed:.1f}↓/{upload_speed:.1f}↑ Mbps")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error running speed test for device {device_id}: {e}")
            return NetworkSpeedTestResult(
                test_id=str(uuid.uuid4()),
                device_id=device_id,
                test_type="error",
                server_id="unknown",
                server_name="Error",
                server_location="Unknown",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                download_speed=0.0,
                upload_speed=0.0,
                latency=0.0,
                jitter=0.0,
                packet_loss=100.0,
                network_type=NetworkType.UNKNOWN,
                error_message=str(e)
            )

    async def _detect_network_type(self, device_id: str) -> NetworkType:
        """Detect current active network type"""
        try:
            # Check WiFi status
            wifi_result = await self.adb_manager.execute_command(
                device_id, "dumpsys wifi | grep -E '(mWifiInfo|mNetworkInfo)'"
            )
            
            if wifi_result.success and "state: CONNECTED" in wifi_result.output:
                return NetworkType.WIFI
            
            # Check mobile network
            mobile_result = await self.adb_manager.execute_command(
                device_id, "dumpsys telephony.registry | grep mDataConnectionState"
            )
            
            if mobile_result.success and "2" in mobile_result.output:  # Connected state
                return NetworkType.MOBILE
            
            return NetworkType.UNKNOWN
            
        except Exception:
            return NetworkType.UNKNOWN

    async def _get_current_signal_strength(self, device_id: str, network_type: NetworkType) -> Optional[int]:
        """Get current signal strength for the active network"""
        try:
            if network_type == NetworkType.WIFI:
                result = await self.adb_manager.execute_command(
                    device_id, "dumpsys wifi | grep 'rssi:'"
                )
                if result.success:
                    rssi_match = re.search(r'rssi:\s*(-?\d+)', result.output)
                    if rssi_match:
                        return int(rssi_match.group(1))
            
            elif network_type == NetworkType.MOBILE:
                result = await self.adb_manager.execute_command(
                    device_id, "dumpsys telephony.registry | grep mSignalStrength"
                )
                if result.success:
                    rssi_match = re.search(r'rssi=(-?\d+)', result.output)
                    if rssi_match:
                        return int(rssi_match.group(1))
            
            return None
            
        except Exception:
            return None

    async def get_speed_test_history(self, device_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get speed test history for a device"""
        try:
            history = self._speed_test_history.get(device_id, [])
            
            # Sort by start time, most recent first
            sorted_history = sorted(history, key=lambda x: x.start_time, reverse=True)
            
            # Apply limit
            limited_history = sorted_history[:limit]
            
            return [result.to_dict() for result in limited_history]
            
        except Exception as e:
            self.logger.error(f"Error getting speed test history for device {device_id}: {e}")
            return []

    # Network Optimization
    
    async def generate_network_optimizations(self, device_id: str) -> List[NetworkOptimization]:
        """Generate network optimization recommendations"""
        try:
            optimizations = []
            
            # Check cache first
            cache_key = f"{device_id}_optimizations"
            if (cache_key in self._optimization_cache and 
                cache_key in self._cache_expiry and
                self._cache_expiry[cache_key] > datetime.utcnow()):
                return self._optimization_cache[cache_key]
            
            # DNS Optimization
            dns_optimization = await self._analyze_dns_optimization(device_id)
            if dns_optimization:
                optimizations.append(dns_optimization)
            
            # TCP Optimization
            tcp_optimization = await self._analyze_tcp_optimization(device_id)
            if tcp_optimization:
                optimizations.append(tcp_optimization)
            
            # WiFi Optimization
            wifi_optimization = await self._analyze_wifi_optimization(device_id)
            if wifi_optimization:
                optimizations.append(wifi_optimization)
            
            # Mobile Data Optimization
            mobile_optimization = await self._analyze_mobile_optimization(device_id)
            if mobile_optimization:
                optimizations.append(mobile_optimization)
            
            # Cache results for 1 hour
            self._optimization_cache[cache_key] = optimizations
            self._cache_expiry[cache_key] = datetime.utcnow() + timedelta(hours=1)
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Error generating network optimizations for device {device_id}: {e}")
            return []

    async def _analyze_dns_optimization(self, device_id: str) -> Optional[NetworkOptimization]:
        """Analyze DNS optimization opportunities"""
        try:
            # Test current DNS speed
            current_dns_time = await self._test_dns_speed(device_id, "8.8.8.8")
            
            if current_dns_time is None or current_dns_time < 20:
                return None  # DNS is already fast enough
            
            # Test alternative DNS servers
            best_dns = None
            best_time = current_dns_time
            
            for dns_name, dns_config in self.public_dns_servers.items():
                test_time = await self._test_dns_speed(device_id, dns_config["primary"])
                if test_time and test_time < best_time:
                    best_dns = dns_config
                    best_time = test_time
            
            if best_dns and best_time < current_dns_time * 0.8:  # At least 20% improvement
                improvement = ((current_dns_time - best_time) / current_dns_time) * 100
                
                return NetworkOptimization(
                    optimization_type=OptimizationType.DNS,
                    title="Optimize DNS Servers",
                    description=f"Switch to {best_dns['name']} for faster DNS resolution",
                    current_value="Auto/ISP DNS",
                    recommended_value=f"{best_dns['primary']}, {best_dns['secondary']}",
                    expected_improvement=round(improvement, 1),
                    impact_level="medium",
                    safety_level="safe",
                    commands=[
                        f"setprop net.dns1 {best_dns['primary']}",
                        f"setprop net.dns2 {best_dns['secondary']}"
                    ],
                    prerequisites=["Root access or manual configuration required"]
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error analyzing DNS optimization: {e}")
            return None

    async def _test_dns_speed(self, device_id: str, dns_server: str) -> Optional[float]:
        """Test DNS resolution speed for a specific server"""
        try:
            start_time = datetime.utcnow()
            
            # Use nslookup with specific DNS server
            result = await self.adb_manager.execute_command(
                device_id, f"nslookup google.com {dns_server} 2>&1", timeout=5
            )
            
            end_time = datetime.utcnow()
            
            if result.success and "can't resolve" not in result.output.lower():
                return (end_time - start_time).total_seconds() * 1000
            
            return None
            
        except Exception:
            return None

    async def _analyze_tcp_optimization(self, device_id: str) -> Optional[NetworkOptimization]:
        """Analyze TCP optimization opportunities"""
        try:
            # Check current TCP settings
            tcp_result = await self.adb_manager.execute_command(
                device_id, "cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null"
            )
            
            current_algorithm = "unknown"
            if tcp_result.success:
                current_algorithm = tcp_result.output.strip()
            
            # Check if BBR is available
            available_result = await self.adb_manager.execute_command(
                device_id, "cat /proc/sys/net/ipv4/tcp_available_congestion_control 2>/dev/null"
            )
            
            if available_result.success and "bbr" in available_result.output and current_algorithm != "bbr":
                return NetworkOptimization(
                    optimization_type=OptimizationType.TCP,
                    title="Enable BBR Congestion Control",
                    description="BBR can improve throughput and reduce latency",
                    current_value=current_algorithm,
                    recommended_value="bbr",
                    expected_improvement=15.0,
                    impact_level="medium",
                    safety_level="moderate",
                    commands=[
                        "echo bbr > /proc/sys/net/ipv4/tcp_congestion_control"
                    ],
                    prerequisites=["Root access required", "BBR kernel support"]
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error analyzing TCP optimization: {e}")
            return None

    async def _analyze_wifi_optimization(self, device_id: str) -> Optional[NetworkOptimization]:
        """Analyze WiFi optimization opportunities"""
        try:
            # Check WiFi power saving mode
            wifi_result = await self.adb_manager.execute_command(
                device_id, "dumpsys wifi | grep -i 'power save'"
            )
            
            if wifi_result.success and "enabled" in wifi_result.output.lower():
                return NetworkOptimization(
                    optimization_type=OptimizationType.WIFI,
                    title="Disable WiFi Power Saving",
                    description="Disable power saving mode to improve WiFi performance",
                    current_value="Enabled",
                    recommended_value="Disabled",
                    expected_improvement=20.0,
                    impact_level="high",
                    safety_level="safe",
                    commands=[
                        "settings put global wifi_power_save_mode 0"
                    ]
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error analyzing WiFi optimization: {e}")
            return None

    async def _analyze_mobile_optimization(self, device_id: str) -> Optional[NetworkOptimization]:
        """Analyze mobile network optimization opportunities"""
        try:
            # Check preferred network type
            network_result = await self.adb_manager.execute_command(
                device_id, "dumpsys telephony.registry | grep mDataNetworkType"
            )
            
            if network_result.success:
                # Check if device is using older network types when LTE is available
                if "LTE" not in network_result.output and "13" not in network_result.output:
                    return NetworkOptimization(
                        optimization_type=OptimizationType.MOBILE_DATA,
                        title="Prefer LTE Network",
                        description="Configure device to prefer LTE for better performance",
                        current_value="3G/HSPA",
                        recommended_value="LTE/4G",
                        expected_improvement=50.0,
                        impact_level="high",
                        safety_level="safe",
                        commands=[
                            "settings put global preferred_network_mode 9"  # LTE/GSM/WCDMA
                        ]
                    )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error analyzing mobile optimization: {e}")
            return None

    async def apply_network_optimization(self, device_id: str, optimization: NetworkOptimization) -> Dict[str, Any]:
        """Apply a network optimization"""
        try:
            self.logger.info(f"Applying {optimization.optimization_type.value} optimization to device {device_id}")
            
            result = {
                "device_id": device_id,
                "optimization_type": optimization.optimization_type.value,
                "title": optimization.title,
                "success": False,
                "commands_executed": [],
                "commands_failed": [],
                "error_message": None
            }
            
            # Execute optimization commands
            for command in optimization.commands:
                try:
                    cmd_result = await self.adb_manager.execute_command(device_id, command)
                    
                    if cmd_result.success:
                        result["commands_executed"].append(command)
                    else:
                        result["commands_failed"].append({
                            "command": command,
                            "error": cmd_result.error or "Unknown error"
                        })
                        
                except Exception as e:
                    result["commands_failed"].append({
                        "command": command,
                        "error": str(e)
                    })
            
            # Determine overall success
            result["success"] = len(result["commands_executed"]) > 0 and len(result["commands_failed"]) == 0
            
            if result["success"]:
                self.logger.info(f"Successfully applied {optimization.title} to device {device_id}")
                
                # Clear optimization cache to force refresh
                cache_key = f"{device_id}_optimizations"
                if cache_key in self._optimization_cache:
                    del self._optimization_cache[cache_key]
                    del self._cache_expiry[cache_key]
            else:
                error_msgs = [f["error"] for f in result["commands_failed"]]
                result["error_message"] = "; ".join(error_msgs)
                self.logger.warning(f"Failed to apply {optimization.title} to device {device_id}: {result['error_message']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying network optimization: {e}")
            return {
                "device_id": device_id,
                "success": False,
                "error_message": str(e)
            }

    # Network Monitoring and Alerts
    
    async def start_network_monitoring(self, device_id: str) -> bool:
        """Start continuous network monitoring"""
        try:
            if device_id in self._monitoring_tasks:
                self.logger.info(f"Network monitoring already active for device {device_id}")
                return True
            
            # Create monitoring task
            task = asyncio.create_task(self._network_monitoring_loop(device_id))
            self._monitoring_tasks[device_id] = task
            
            self.logger.info(f"Started network monitoring for device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start network monitoring for device {device_id}: {e}")
            return False

    async def stop_network_monitoring(self, device_id: str) -> bool:
        """Stop network monitoring"""
        try:
            if device_id in self._monitoring_tasks:
                self._monitoring_tasks[device_id].cancel()
                del self._monitoring_tasks[device_id]
                self.logger.info(f"Stopped network monitoring for device {device_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop network monitoring for device {device_id}: {e}")
            return False

    async def _network_monitoring_loop(self, device_id: str):
        """Main network monitoring loop"""
        monitoring_interval = 60  # 1 minute between checks
        
        try:
            while True:
                try:
                    # Collect network metrics
                    metrics = await self._collect_network_metrics(device_id)
                    
                    # Store metrics in history
                    self._network_history[device_id].append({
                        "timestamp": datetime.utcnow(),
                        "metrics": metrics
                    })
                    
                    # Check for alerts
                    await self._check_network_alerts(device_id, metrics)
                    
                    await asyncio.sleep(monitoring_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in network monitoring loop for device {device_id}: {e}")
                    await asyncio.sleep(monitoring_interval)
                    
        except asyncio.CancelledError:
            self.logger.info(f"Network monitoring cancelled for device {device_id}")

    async def _collect_network_metrics(self, device_id: str) -> Dict[str, Any]:
        """Collect current network metrics"""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "network_type": "unknown",
            "signal_strength": None,
            "connection_status": "unknown",
            "data_usage": {"rx": 0, "tx": 0}
        }
        
        try:
            # Detect network type
            network_type = await self._detect_network_type(device_id)
            metrics["network_type"] = network_type.value
            
            # Get signal strength
            signal_strength = await self._get_current_signal_strength(device_id, network_type)
            metrics["signal_strength"] = signal_strength
            
            # Check connection status
            ping_result = await self.run_ping_test(device_id, count=1)
            metrics["connection_status"] = "connected" if ping_result.status == "success" else "limited"
            metrics["latency"] = ping_result.response_time
            
            return metrics
            
        except Exception as e:
            self.logger.debug(f"Error collecting network metrics: {e}")
            return metrics

    async def _check_network_alerts(self, device_id: str, metrics: Dict[str, Any]):
        """Check network metrics against alert thresholds"""
        try:
            alerts_to_create = []
            
            # Check signal strength
            signal_strength = metrics.get("signal_strength")
            if signal_strength:
                network_type = metrics.get("network_type", "unknown")
                
                if network_type == "wifi":
                    threshold = self.alert_thresholds["signal_strength_wifi"]
                    if signal_strength < threshold:
                        alerts_to_create.append({
                            "type": "weak_wifi_signal",
                            "severity": AlertSeverity.MEDIUM,
                            "title": "Weak WiFi Signal",
                            "description": f"WiFi signal strength is {signal_strength}dBm",
                            "metric": "signal_strength",
                            "threshold": threshold,
                            "current": signal_strength
                        })
                
                elif network_type == "mobile":
                    threshold = self.alert_thresholds["signal_strength_mobile"]
                    if signal_strength < threshold:
                        alerts_to_create.append({
                            "type": "weak_mobile_signal",
                            "severity": AlertSeverity.MEDIUM,
                            "title": "Weak Mobile Signal",
                            "description": f"Mobile signal strength is {signal_strength}dBm",
                            "metric": "signal_strength",
                            "threshold": threshold,
                            "current": signal_strength
                        })
            
            # Check latency
            latency = metrics.get("latency")
            if latency and latency > self.alert_thresholds["latency"]:
                severity = AlertSeverity.HIGH if latency > 200 else AlertSeverity.MEDIUM
                alerts_to_create.append({
                    "type": "high_latency",
                    "severity": severity,
                    "title": "High Network Latency",
                    "description": f"Network latency is {latency:.1f}ms",
                    "metric": "latency",
                    "threshold": self.alert_thresholds["latency"],
                    "current": latency
                })
            
            # Check connection status
            if metrics.get("connection_status") != "connected":
                alerts_to_create.append({
                    "type": "connection_issue",
                    "severity": AlertSeverity.HIGH,
                    "title": "Connection Issue",
                    "description": "Internet connectivity problems detected",
                    "metric": "connection_status",
                    "threshold": "connected",
                    "current": metrics.get("connection_status", "unknown")
                })
            
            # Create alerts
            for alert_data in alerts_to_create:
                await self._create_network_alert(device_id, alert_data)
            
        except Exception as e:
            self.logger.error(f"Error checking network alerts: {e}")

    async def _create_network_alert(self, device_id: str, alert_data: Dict[str, Any]):
        """Create a network alert"""
        try:
            # Check if similar alert already exists and is not resolved
            existing_alerts = self._active_alerts.get(device_id, [])
            
            # Don't create duplicate alerts of the same type within 1 hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_similar = [
                a for a in existing_alerts
                if (a.alert_type == alert_data["type"] and 
                    a.timestamp > one_hour_ago and 
                    not a.is_resolved)
            ]
            
            if recent_similar:
                return  # Don't create duplicate alert
            
            # Create new alert
            alert = NetworkAlert(
                alert_id=str(uuid.uuid4()),
                device_id=device_id,
                alert_type=alert_data["type"],
                severity=alert_data["severity"],
                title=alert_data["title"],
                description=alert_data["description"],
                metric_name=alert_data["metric"],
                threshold_value=float(alert_data.get("threshold", 0)),
                current_value=float(alert_data.get("current", 0)),
                timestamp=datetime.utcnow()
            )
            
            # Add to active alerts
            self._active_alerts[device_id].append(alert)
            
            # Send real-time notification
            if self.websocket_manager:
                await self.websocket_manager.send_message(
                    device_id, 
                    "network_alert", 
                    alert.to_dict()
                )
            
            self.logger.warning(f"Network alert created for device {device_id}: {alert.title}")
            
        except Exception as e:
            self.logger.error(f"Error creating network alert: {e}")

    async def get_network_alerts(self, device_id: str, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Get network alerts for a device"""
        try:
            alerts = self._active_alerts.get(device_id, [])
            
            if not include_resolved:
                alerts = [a for a in alerts if not a.is_resolved]
            
            # Sort by timestamp, most recent first
            alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            self.logger.error(f"Error getting network alerts: {e}")
            return []

    async def resolve_network_alert(self, device_id: str, alert_id: str) -> bool:
        """Mark a network alert as resolved"""
        try:
            alerts = self._active_alerts.get(device_id, [])
            
            for alert in alerts:
                if alert.alert_id == alert_id:
                    alert.is_resolved = True
                    alert.resolution_time = datetime.utcnow()
                    self.logger.info(f"Network alert {alert_id} resolved for device {device_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error resolving network alert: {e}")
            return False

    # Network Analytics
    
    async def get_network_analytics(self, device_id: str, period_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive network analytics"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=period_hours)
            
            # Get network history
            history = self._network_history.get(device_id, [])
            period_history = [
                h for h in history 
                if h["timestamp"] >= start_time
            ]
            
            analytics = {
                "device_id": device_id,
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "period_hours": period_hours,
                "data_points": len(period_history),
                "connection_stats": {},
                "performance_stats": {},
                "trends": {},
                "insights": []
            }
            
            if not period_history:
                analytics["insights"].append("No network monitoring data available for this period")
                return analytics
            
            # Analyze connection types
            network_types = [h["metrics"].get("network_type") for h in period_history]
            connection_stats = {
                "wifi_percentage": (network_types.count("wifi") / len(network_types)) * 100,
                "mobile_percentage": (network_types.count("mobile") / len(network_types)) * 100,
                "connection_changes": len([i for i in range(1, len(network_types)) if network_types[i] != network_types[i-1]])
            }
            analytics["connection_stats"] = connection_stats
            
            # Analyze performance metrics
            signal_strengths = [h["metrics"].get("signal_strength") for h in period_history if h["metrics"].get("signal_strength")]
            latencies = [h["metrics"].get("latency") for h in period_history if h["metrics"].get("latency")]
            
            if signal_strengths:
                analytics["performance_stats"]["signal_strength"] = {
                    "average": round(statistics.mean(signal_strengths), 1),
                    "min": min(signal_strengths),
                    "max": max(signal_strengths),
                    "std_dev": round(statistics.stdev(signal_strengths) if len(signal_strengths) > 1 else 0, 1)
                }
            
            if latencies:
                analytics["performance_stats"]["latency"] = {
                    "average": round(statistics.mean(latencies), 1),
                    "min": round(min(latencies), 1),
                    "max": round(max(latencies), 1),
                    "std_dev": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 1)
                }
            
            # Generate insights
            if connection_stats["wifi_percentage"] > 80:
                analytics["insights"].append("Device primarily uses WiFi connection")
            elif connection_stats["mobile_percentage"] > 80:
                analytics["insights"].append("Device primarily uses mobile data")
            else:
                analytics["insights"].append("Device uses mixed WiFi and mobile connections")
            
            if connection_stats["connection_changes"] > period_hours:
                analytics["insights"].append("Frequent network switching detected - may indicate connectivity issues")
            
            if signal_strengths and statistics.mean(signal_strengths) < -75:
                analytics["insights"].append("Average signal strength is poor - consider network optimization")
            
            if latencies and statistics.mean(latencies) > 100:
                analytics["insights"].append("High average latency detected - network performance may be suboptimal")
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting network analytics for device {device_id}: {e}")
            return {"error": str(e), "device_id": device_id}

    async def get_speed_test_trends(self, device_id: str, days: int = 7) -> Dict[str, Any]:
        """Get speed test trends and analysis"""
        try:
            history = self._speed_test_history.get(device_id, [])
            
            # Filter by time period
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            period_history = [
                test for test in history 
                if test.start_time >= cutoff_date
            ]
            
            if not period_history:
                return {
                    "device_id": device_id,
                    "message": "No speed test data available for the specified period",
                    "days": days
                }
            
            # Separate by network type
            wifi_tests = [t for t in period_history if t.network_type == NetworkType.WIFI]
            mobile_tests = [t for t in period_history if t.network_type == NetworkType.MOBILE]
            
            trends = {
                "device_id": device_id,
                "period_days": days,
                "total_tests": len(period_history),
                "wifi_tests": len(wifi_tests),
                "mobile_tests": len(mobile_tests),
                "wifi_stats": self._calculate_speed_stats(wifi_tests),
                "mobile_stats": self._calculate_speed_stats(mobile_tests),
                "overall_trend": "stable",
                "recommendations": []
            }
            
            # Calculate trends
            if len(period_history) >= 3:
                download_speeds = [t.download_speed for t in period_history]
                upload_speeds = [t.upload_speed for t in period_history]
                
                # Simple trend analysis
                if len(download_speeds) >= 3:
                    first_third = statistics.mean(download_speeds[:len(download_speeds)//3])
                    last_third = statistics.mean(download_speeds[-len(download_speeds)//3:])
                    
                    if last_third > first_third * 1.1:
                        trends["overall_trend"] = "improving"
                    elif last_third < first_third * 0.9:
                        trends["overall_trend"] = "declining"
            
            # Generate recommendations
            if trends["wifi_stats"]["avg_download"] < 25:
                trends["recommendations"].append("WiFi speeds are below recommended minimums. Consider upgrading internet plan or optimizing network.")
            
            if trends["mobile_stats"]["avg_download"] < 10:
                trends["recommendations"].append("Mobile speeds are low. Check signal strength and consider carrier optimization.")
            
            if trends["overall_trend"] == "declining":
                trends["recommendations"].append("Network performance is declining. Consider running diagnostics and optimizations.")
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting speed test trends: {e}")
            return {"error": str(e), "device_id": device_id}

    def _calculate_speed_stats(self, tests: List[NetworkSpeedTestResult]) -> Dict[str, Any]:
        """Calculate speed statistics for a list of tests"""
        if not tests:
            return {
                "count": 0,
                "avg_download": 0,
                "avg_upload": 0,
                "avg_latency": 0
            }
        
        download_speeds = [t.download_speed for t in tests]
        upload_speeds = [t.upload_speed for t in tests]
        latencies = [t.latency for t in tests if t.latency > 0]
        
        return {
            "count": len(tests),
            "avg_download": round(statistics.mean(download_speeds), 2),
            "avg_upload": round(statistics.mean(upload_speeds), 2),
            "avg_latency": round(statistics.mean(latencies), 2) if latencies else 0,
            "min_download": round(min(download_speeds), 2),
            "max_download": round(max(download_speeds), 2),
            "min_upload": round(min(upload_speeds), 2),
            "max_upload": round(max(upload_speeds), 2)
        }

    # Connection Troubleshooting
    
    async def run_connection_troubleshooting(self, device_id: str) -> Dict[str, Any]:
        """Run automated connection troubleshooting"""
        try:
            self.logger.info(f"Starting connection troubleshooting for device {device_id}")
            
            troubleshooting = {
                "device_id": device_id,
                "start_time": datetime.utcnow().isoformat(),
                "steps": [],
                "issues_found": [],
                "solutions_applied": [],
                "final_status": "unknown",
                "recommendations": []
            }
            
            # Step 1: Check basic connectivity
            troubleshooting["steps"].append("Checking basic internet connectivity...")
            ping_result = await self.run_ping_test(device_id)
            
            if ping_result.status != "success":
                troubleshooting["issues_found"].append("No internet connectivity")
                
                # Try to resolve connectivity
                troubleshooting["steps"].append("Attempting to resolve connectivity issues...")
                
                # Check network interfaces
                interfaces = await self.get_network_interfaces(device_id)
                active_interfaces = [i for i in interfaces if i.is_active]
                
                if not active_interfaces:
                    troubleshooting["issues_found"].append("No active network interfaces")
                    troubleshooting["recommendations"].append("Enable WiFi or mobile data")
                else:
                    troubleshooting["steps"].append("Active network interfaces found")
            
            # Step 2: Check DNS resolution
            troubleshooting["steps"].append("Checking DNS resolution...")
            dns_result = await self.run_dns_test(device_id)
            
            if dns_result.status != "success":
                troubleshooting["issues_found"].append("DNS resolution failed")
                troubleshooting["recommendations"].append("Try changing DNS servers to 8.8.8.8 and 8.8.4.4")
                
                # Attempt DNS fix
                dns_fix_result = await self.adb_manager.execute_command(
                    device_id, "setprop net.dns1 8.8.8.8; setprop net.dns2 8.8.4.4"
                )
                
                if dns_fix_result.success:
                    troubleshooting["solutions_applied"].append("Applied Google DNS servers")
                    
                    # Retest DNS
                    dns_retest = await self.run_dns_test(device_id)
                    if dns_retest.status == "success":
                        troubleshooting["solutions_applied"].append("DNS resolution fixed")
            
            # Step 3: Check signal strength
            troubleshooting["steps"].append("Checking signal strength...")
            network_type = await self._detect_network_type(device_id)
            signal_strength = await self._get_current_signal_strength(device_id, network_type)
            
            if signal_strength:
                if network_type == NetworkType.WIFI and signal_strength < -70:
                    troubleshooting["issues_found"].append(f"Weak WiFi signal ({signal_strength}dBm)")
                    troubleshooting["recommendations"].append("Move closer to WiFi router or use WiFi extender")
                elif network_type == NetworkType.MOBILE and signal_strength < -100:
                    troubleshooting["issues_found"].append(f"Weak mobile signal ({signal_strength}dBm)")
                    troubleshooting["recommendations"].append("Move to area with better cellular coverage")
            
            # Step 4: Test network performance
            troubleshooting["steps"].append("Testing network performance...")
            
            # Quick speed test
            speed_result = await self.run_speed_test(device_id, test_duration=10)
            
            if speed_result.download_speed < 5:
                troubleshooting["issues_found"].append(f"Slow download speed ({speed_result.download_speed:.1f} Mbps)")
                troubleshooting["recommendations"].append("Consider network optimization or contact ISP")
            
            if speed_result.latency > 100:
                troubleshooting["issues_found"].append(f"High latency ({speed_result.latency:.1f}ms)")
                troubleshooting["recommendations"].append("Check for network congestion or interference")
            
            # Step 5: Apply automatic fixes where possible
            troubleshooting["steps"].append("Applying automatic optimizations...")
            
            optimizations = await self.generate_network_optimizations(device_id)
            safe_optimizations = [opt for opt in optimizations if opt.safety_level == "safe"]
            
            for optimization in safe_optimizations:
                try:
                    result = await self.apply_network_optimization(device_id, optimization)
                    if result["success"]:
                        troubleshooting["solutions_applied"].append(f"Applied {optimization.title}")
                except Exception as e:
                    self.logger.debug(f"Failed to apply optimization {optimization.title}: {e}")
            
            # Final connectivity test
            troubleshooting["steps"].append("Performing final connectivity test...")
            final_ping = await self.run_ping_test(device_id)
            
            if final_ping.status == "success":
                troubleshooting["final_status"] = "resolved"
                if final_ping.response_time <= 50:
                    troubleshooting["final_status"] = "fully_resolved"
            else:
                troubleshooting["final_status"] = "unresolved"
                troubleshooting["recommendations"].append("Manual intervention may be required")
            
            troubleshooting["end_time"] = datetime.utcnow().isoformat()
            
            return troubleshooting
            
        except Exception as e:
            self.logger.error(f"Error running connection troubleshooting: {e}")
            return {
                "device_id": device_id,
                "error": str(e),
                "final_status": "error"
            }

    # Public API Methods
    
    async def get_network_dashboard(self, device_id: str) -> Dict[str, Any]:
        """Get comprehensive network dashboard"""
        try:
            # Get current network status
            interfaces = await self.get_network_interfaces(device_id)
            wifi_networks = await self.get_wifi_networks(device_id, include_scan=False)
            mobile_network = await self.get_mobile_network_info(device_id)
            
            # Get recent alerts
            alerts = await self.get_network_alerts(device_id)
            
            # Get recent speed test
            speed_history = await self.get_speed_test_history(device_id, limit=1)
            latest_speed_test = speed_history[0] if speed_history else None
            
            # Get data usage
            data_usage = await self.get_data_usage_stats(device_id, period_days=1)
            
            dashboard = {
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "network_interfaces": [iface.to_dict() for iface in interfaces],
                "wifi_networks": [net.to_dict() for net in wifi_networks],
                "mobile_network": mobile_network.to_dict() if mobile_network else None,
                "current_connection": self._get_current_connection_summary(interfaces, wifi_networks, mobile_network),
                "data_usage_today": data_usage.get("total_usage", {}),
                "latest_speed_test": latest_speed_test,
                "active_alerts": len([a for a in alerts if not a.get("is_resolved", True)]),
                "monitoring_active": device_id in self._monitoring_tasks,
                "optimization_available": len(await self.generate_network_optimizations(device_id)) > 0
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error getting network dashboard for device {device_id}: {e}")
            return {"error": str(e), "device_id": device_id}

    def _get_current_connection_summary(self, interfaces: List[NetworkInterface], 
                                      wifi_networks: List[WiFiNetwork], 
                                      mobile_network: Optional[MobileNetwork]) -> Dict[str, Any]:
        """Get summary of current connection"""
        summary = {
            "type": "none",
            "status": "disconnected",
            "quality": "unknown",
            "signal_strength": None,
            "speed_estimate": "unknown"
        }
        
        try:
            # Check for active WiFi
            connected_wifi = next((net for net in wifi_networks if net.is_connected), None)
            if connected_wifi:
                summary.update({
                    "type": "wifi",
                    "status": "connected",
                    "ssid": connected_wifi.ssid,
                    "signal_strength": connected_wifi.signal_strength,
                    "quality": "excellent" if connected_wifi.signal_strength > -50 else
                             "good" if connected_wifi.signal_strength > -70 else "poor",
                    "frequency": connected_wifi.frequency,
                    "security": connected_wifi.security_type
                })
                return summary
            
            # Check for mobile connection
            if mobile_network and mobile_network.data_state == "connected":
                summary.update({
                    "type": "mobile",
                    "status": "connected",
                    "carrier": mobile_network.carrier,
                    "network_type": mobile_network.network_type,
                    "signal_strength": mobile_network.signal_strength,
                    "quality": "excellent" if mobile_network.signal_strength > -80 else
                             "good" if mobile_network.signal_strength > -100 else "poor",
                    "roaming": mobile_network.is_roaming
                })
                return summary
            
            # Check for any active interface
            active_interface = next((iface for iface in interfaces if iface.is_active and iface.ip_address), None)
            if active_interface:
                summary.update({
                    "type": active_interface.type.value,
                    "status": "connected",
                    "interface": active_interface.name,
                    "ip_address": active_interface.ip_address
                })
            
            return summary
            
        except Exception as e:
            self.logger.debug(f"Error getting connection summary: {e}")
            return summary

    async def shutdown(self):
        """Shutdown network service and cleanup resources"""
        try:
            self.logger.info("Shutting down network optimization service...")
            
            # Stop all monitoring tasks
            for device_id in list(self._monitoring_tasks.keys()):
                await self.stop_network_monitoring(device_id)
            
            # Clear caches
            self._network_history.clear()
            self._optimization_cache.clear()
            self._cache_expiry.clear()
            self._active_alerts.clear()
            
            self.logger.info("Network optimization service shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during network service shutdown: {e}")


# Factory function
def create_network_service(adb_manager: AdbManager, websocket_manager: WebSocketManager) -> NetworkOptimizationService:
    """Create network optimization service with proper dependencies"""
    return NetworkOptimizationService(adb_manager, websocket_manager)


# Import random for mock data
import random

