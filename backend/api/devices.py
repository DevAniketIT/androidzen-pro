"""
Device management API endpoints for AndroidZen Pro.
Handles device registration, monitoring, connection management, and basic operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import subprocess
import os
import platform
import json

from .core.database import get_db
from .models.device import Device, DeviceConnectionHistory
from .models.analytics import Analytics
from .core.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class DeviceCreate(BaseModel):
    device_id: str
    serial_number: Optional[str] = None
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    brand: Optional[str] = None
    android_version: Optional[str] = None
    api_level: Optional[int] = None
    connection_type: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None

class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    is_active: Optional[bool] = None
    connection_type: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None

class DeviceResponse(BaseModel):
    id: int
    device_id: str
    serial_number: Optional[str]
    device_name: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    brand: Optional[str]
    android_version: Optional[str]
    api_level: Optional[int]
    connection_type: Optional[str]
    is_connected: bool
    is_rooted: bool
    last_seen: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class DeviceStats(BaseModel):
    total_devices: int
    connected_devices: int
    active_devices: int
    device_types: Dict[str, int]
    connection_types: Dict[str, int]

class ConnectionHistoryResponse(BaseModel):
    id: int
    device_id: int
    connection_type: str
    event_type: str
    ip_address: Optional[str]
    timestamp: datetime

@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    connected_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get a list of all registered devices with optional filtering.
    """
    query = db.query(Device)
    
    if active_only:
        query = query.filter(Device.is_active == True)
    
    if connected_only:
        query = query.filter(Device.is_connected == True)
    
    devices = query.offset(skip).limit(limit).all()
    
    return [DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        serial_number=device.serial_number,
        device_name=device.device_name,
        manufacturer=device.manufacturer,
        model=device.model,
        brand=device.brand,
        android_version=device.android_version,
        api_level=device.api_level,
        connection_type=device.connection_type,
        is_connected=device.is_connected,
        is_rooted=device.is_rooted,
        last_seen=device.last_seen,
        created_at=device.created_at,
        updated_at=device.updated_at
    ) for device in devices]

@router.post("/", response_model=DeviceResponse)
async def create_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Register a new device in the system.
    """
    # Check if device already exists
    existing_device = db.query(Device).filter(Device.device_id == device_data.device_id).first()
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device with this ID already exists"
        )
    
    # Create new device
    device = Device(
        device_id=device_data.device_id,
        serial_number=device_data.serial_number,
        device_name=device_data.device_name,
        manufacturer=device_data.manufacturer,
        model=device_data.model,
        brand=device_data.brand,
        android_version=device_data.android_version,
        api_level=device_data.api_level,
        connection_type=device_data.connection_type,
        ip_address=device_data.ip_address,
        port=device_data.port,
        is_connected=True,
        is_active=True
    )
    
    db.add(device)
    db.commit()
    db.refresh(device)
    
    # Create initial connection history record
    connection_history = DeviceConnectionHistory(
        device_id=device.id,
        connection_type=device_data.connection_type or "unknown",
        event_type="connected",
        ip_address=device_data.ip_address
    )
    db.add(connection_history)
    db.commit()
    
    logger.info(f"New device registered: {device.device_id} by user {current_user['username']}")
    
    return DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        serial_number=device.serial_number,
        device_name=device.device_name,
        manufacturer=device.manufacturer,
        model=device.model,
        brand=device.brand,
        android_version=device.android_version,
        api_level=device.api_level,
        connection_type=device.connection_type,
        is_connected=device.is_connected,
        is_rooted=device.is_rooted,
        last_seen=device.last_seen,
        created_at=device.created_at,
        updated_at=device.updated_at
    )

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed information about a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        serial_number=device.serial_number,
        device_name=device.device_name,
        manufacturer=device.manufacturer,
        model=device.model,
        brand=device.brand,
        android_version=device.android_version,
        api_level=device.api_level,
        connection_type=device.connection_type,
        is_connected=device.is_connected,
        is_rooted=device.is_rooted,
        last_seen=device.last_seen,
        created_at=device.created_at,
        updated_at=device.updated_at
    )

@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update device information.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Update device fields
    update_data = device_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(device, field):
            setattr(device, field, value)
    
    # Update timestamp
    device.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(device)
    
    logger.info(f"Device updated: {device.device_id} by user {current_user['username']}")
    
    return DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        serial_number=device.serial_number,
        device_name=device.device_name,
        manufacturer=device.manufacturer,
        model=device.model,
        brand=device.brand,
        android_version=device.android_version,
        api_level=device.api_level,
        connection_type=device.connection_type,
        is_connected=device.is_connected,
        is_rooted=device.is_rooted,
        last_seen=device.last_seen,
        created_at=device.created_at,
        updated_at=device.updated_at
    )

@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Delete a device from the system (soft delete by marking as inactive).
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Soft delete - mark as inactive
    device.is_active = False
    device.is_connected = False
    device.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Device deleted: {device.device_id} by user {current_user['username']}")
    
    return {"message": "Device deleted successfully"}

@router.post("/{device_id}/connect")
async def connect_device(
    device_id: str,
    connection_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Mark a device as connected and update connection information.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Update connection status
    device.update_connection_status(True)
    
    # Update connection info if provided
    if connection_data:
        if "ip_address" in connection_data:
            device.ip_address = connection_data["ip_address"]
        if "port" in connection_data:
            device.port = connection_data["port"]
        if "connection_type" in connection_data:
            device.connection_type = connection_data["connection_type"]
    
    db.commit()
    
    # Create connection history record
    connection_history = DeviceConnectionHistory(
        device_id=device.id,
        connection_type=device.connection_type or "unknown",
        event_type="connected",
        ip_address=device.ip_address
    )
    db.add(connection_history)
    db.commit()
    
    logger.info(f"Device connected: {device.device_id}")
    
    return {"message": "Device connected successfully", "device_id": device_id}

@router.post("/{device_id}/disconnect")
async def disconnect_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Mark a device as disconnected.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Update connection status
    device.update_connection_status(False)
    db.commit()
    
    # Create connection history record
    connection_history = DeviceConnectionHistory(
        device_id=device.id,
        connection_type=device.connection_type or "unknown",
        event_type="disconnected",
        ip_address=device.ip_address
    )
    db.add(connection_history)
    db.commit()
    
    logger.info(f"Device disconnected: {device.device_id}")
    
    return {"message": "Device disconnected successfully", "device_id": device_id}

@router.get("/{device_id}/history", response_model=List[ConnectionHistoryResponse])
async def get_device_connection_history(
    device_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get connection history for a specific device.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    history = (db.query(DeviceConnectionHistory)
              .filter(DeviceConnectionHistory.device_id == device.id)
              .order_by(DeviceConnectionHistory.timestamp.desc())
              .offset(skip)
              .limit(limit)
              .all())
    
    return [ConnectionHistoryResponse(
        id=h.id,
        device_id=h.device_id,
        connection_type=h.connection_type,
        event_type=h.event_type,
        ip_address=h.ip_address,
        timestamp=h.timestamp
    ) for h in history]

@router.get("/{device_id}/status")
async def get_device_status(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get real-time status information for a device.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get latest analytics data
    latest_analytics = (db.query(Analytics)
                       .filter(Analytics.device_id == device.id)
                       .order_by(Analytics.recorded_at.desc())
                       .first())
    
    status_data = {
        "device_id": device.device_id,
        "device_name": device.device_name,
        "is_connected": device.is_connected,
        "is_active": device.is_active,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "connection_type": device.connection_type,
        "ip_address": device.ip_address,
        "basic_info": {
            "manufacturer": device.manufacturer,
            "model": device.model,
            "android_version": device.android_version,
            "api_level": device.api_level,
        }
    }
    
    # Add latest metrics if available
    if latest_analytics:
        status_data["metrics"] = {
            "cpu_usage": latest_analytics.cpu_usage,
            "memory_usage": latest_analytics.memory_usage,
            "battery_level": latest_analytics.battery_level,
            "storage_usage_percentage": latest_analytics.storage_usage_percentage,
            "performance_score": latest_analytics.performance_score,
            "last_updated": latest_analytics.recorded_at.isoformat()
        }
    
    return status_data

@router.get("/{device_id}/properties")
async def get_device_properties(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get custom properties for a device.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return {"device_id": device_id, "properties": device.properties or {}}

@router.put("/{device_id}/properties")
async def update_device_properties(
    device_id: str,
    properties: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update custom properties for a device.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Merge with existing properties
    if device.properties:
        device.properties.update(properties)
    else:
        device.properties = properties
    
    device.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Device properties updated: {device.device_id} by user {current_user['username']}")
    
    return {"message": "Properties updated successfully", "properties": device.properties}

def find_adb_executable():
    """Find the ADB executable on the system."""
    # Check common ADB locations
    adb_paths = [
        "adb",  # If ADB is in PATH
        "C:\\platform-tools\\adb.exe",  # Windows custom install
        "C:\\android-sdk\\platform-tools\\adb.exe",  # Windows SDK
        "/usr/local/bin/adb",  # macOS/Linux
        "/usr/bin/adb",  # Linux
        os.path.expanduser("~/Android/Sdk/platform-tools/adb"),  # User SDK
        os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),  # macOS SDK
    ]
    
    for adb_path in adb_paths:
        try:
            result = subprocess.run([adb_path, "version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return adb_path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    return None

def get_device_info_via_adb(serial_number, adb_path):
    """Get detailed device information via ADB."""
    device_info = {
        "serial_number": serial_number,
        "status": "online"
    }
    
    # Get device properties
    properties_to_get = {
        "ro.product.manufacturer": "manufacturer",
        "ro.product.model": "model", 
        "ro.product.brand": "brand",
        "ro.build.version.release": "android_version",
        "ro.build.version.sdk": "api_level",
        "ro.product.name": "device_name"
    }
    
    for prop, key in properties_to_get.items():
        try:
            result = subprocess.run(
                [adb_path, "-s", serial_number, "shell", "getprop", prop],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                value = result.stdout.strip()
                if key == "api_level":
                    try:
                        device_info[key] = int(value)
                    except ValueError:
                        device_info[key] = None
                else:
                    device_info[key] = value if value else None
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"Failed to get {prop} for device {serial_number}: {e}")
            device_info[key] = None
    
    # Get battery information
    try:
        result = subprocess.run(
            [adb_path, "-s", serial_number, "shell", "dumpsys", "battery"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if "level:" in line:
                    try:
                        battery_level = int(line.split(":")[1].strip())
                        device_info["battery_level"] = battery_level
                        break
                    except (ValueError, IndexError):
                        pass
    except Exception as e:
        logger.warning(f"Failed to get battery info for {serial_number}: {e}")
    
    # Get storage information
    try:
        result = subprocess.run(
            [adb_path, "-s", serial_number, "shell", "df", "/data"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines[1:]:  # Skip header
                if '/data' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            total_kb = int(parts[1])
                            used_kb = int(parts[2])
                            device_info["storage_total"] = round(total_kb / 1024 / 1024, 1)  # Convert to GB
                            device_info["storage_used"] = round(used_kb / 1024 / 1024, 1)   # Convert to GB
                            break
                        except (ValueError, IndexError):
                            pass
    except Exception as e:
        logger.warning(f"Failed to get storage info for {serial_number}: {e}")
    
    return device_info

@router.post("/scan")
async def scan_adb_devices(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Scan for connected Android devices using ADB.
    """
    # Find ADB executable
    adb_path = find_adb_executable()
    if not adb_path:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADB not found. Please install Android Platform Tools and ensure ADB is in your PATH."
        )
    
    logger.info(f"Using ADB at: {adb_path}")
    
    try:
        # Run adb devices command
        result = subprocess.run([adb_path, "devices"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ADB command failed: {result.stderr}"
            )
        
        # Parse ADB output
        lines = result.stdout.strip().split('\n')[1:]  # Skip header line
        detected_devices = []
        
        for line in lines:
            if line.strip() and '\t' in line:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    serial_number = parts[0]
                    status = parts[1]
                    
                    if status == "device":  # Only process authorized devices
                        # Get detailed device information
                        device_info = get_device_info_via_adb(serial_number, adb_path)
                        device_info["id"] = f"adb-{serial_number}"
                        device_info["connection_type"] = "usb"
                        device_info["last_seen"] = datetime.utcnow().isoformat()
                        detected_devices.append(device_info)
                    elif status == "unauthorized":
                        # Device connected but not authorized
                        detected_devices.append({
                            "id": f"adb-{serial_number}",
                            "serial_number": serial_number,
                            "status": "unauthorized",
                            "device_name": "Unauthorized Device",
                            "connection_type": "usb",
                            "message": "Please authorize this computer on your Android device"
                        })
        
        logger.info(f"Found {len(detected_devices)} Android devices via ADB")
        
        # Auto-register new devices in database
        registered_count = 0
        for device_info in detected_devices:
            if device_info.get("status") == "online":
                existing = db.query(Device).filter(
                    Device.device_id == device_info["id"]
                ).first()
                
                if not existing:
                    # Register new device
                    new_device = Device(
                        device_id=device_info["id"],
                        serial_number=device_info["serial_number"],
                        device_name=device_info.get("device_name", "Android Device"),
                        manufacturer=device_info.get("manufacturer"),
                        model=device_info.get("model"),
                        brand=device_info.get("brand"),
                        android_version=device_info.get("android_version"),
                        api_level=device_info.get("api_level"),
                        connection_type="usb",
                        is_connected=True,
                        is_active=True
                    )
                    db.add(new_device)
                    registered_count += 1
                else:
                    # Update existing device
                    existing.is_connected = True
                    existing.last_seen = datetime.utcnow()
        
        if registered_count > 0:
            db.commit()
            logger.info(f"Registered {registered_count} new devices")
        
        return {
            "success": True,
            "adb_path": adb_path,
            "devices_found": len(detected_devices),
            "devices_registered": registered_count,
            "devices": detected_devices
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="ADB scan timed out. Please check your device connections."
        )
    except Exception as e:
        logger.error(f"ADB scan error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan devices: {str(e)}"
        )

@router.get("/adb/status")
async def check_adb_status(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Check if ADB is available and working.
    """
    adb_path = find_adb_executable()
    
    if not adb_path:
        return {
            "adb_available": False,
            "message": "ADB not found. Please install Android Platform Tools.",
            "install_url": "https://developer.android.com/studio/releases/platform-tools"
        }
    
    try:
        result = subprocess.run([adb_path, "version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_info = result.stdout.strip()
            return {
                "adb_available": True,
                "adb_path": adb_path,
                "version": version_info,
                "message": "ADB is ready to use"
            }
        else:
            return {
                "adb_available": False,
                "adb_path": adb_path,
                "error": result.stderr,
                "message": "ADB found but not working properly"
            }
    except Exception as e:
        return {
            "adb_available": False,
            "adb_path": adb_path,
            "error": str(e),
            "message": "ADB found but failed to execute"
        }

@router.get("/stats/overview", response_model=DeviceStats)
async def get_device_stats(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get overview statistics for all devices.
    """
    total_devices = db.query(Device).count()
    connected_devices = db.query(Device).filter(Device.is_connected == True).count()
    active_devices = db.query(Device).filter(Device.is_active == True).count()
    
    # Get device type distribution
    device_types = {}
    devices = db.query(Device.manufacturer, Device.model).filter(Device.is_active == True).all()
    for manufacturer, model in devices:
        device_type = f"{manufacturer} {model}" if manufacturer and model else "Unknown"
        device_types[device_type] = device_types.get(device_type, 0) + 1
    
    # Get connection type distribution
    connection_types = {}
    connections = db.query(Device.connection_type).filter(Device.is_active == True).all()
    for (conn_type,) in connections:
        conn_type = conn_type or "Unknown"
        connection_types[conn_type] = connection_types.get(conn_type, 0) + 1
    
    return DeviceStats(
        total_devices=total_devices,
        connected_devices=connected_devices,
        active_devices=active_devices,
        device_types=device_types,
        connection_types=connection_types
    )

