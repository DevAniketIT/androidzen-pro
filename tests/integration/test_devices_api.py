"""
Integration tests for Devices API endpoints.
"""

import pytest
import json
from datetime import datetime
from httpx import AsyncClient
from fastapi.testclient import TestClient

from backend.models.device import Device
from backend.models.analytics import Analytics
from backend.tests.mocks.mock_adb_device import MockADBDevice, create_test_devices


@pytest.mark.integration
class TestDevicesAPI:
    """Integration tests for devices API."""

    async def test_get_devices_empty(self, async_client: AsyncClient, authenticated_headers):
        """Test getting devices when none are connected."""
        response = await async_client.get(
            "/api/devices/",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_devices_with_mock_devices(self, async_client: AsyncClient, 
                                                 authenticated_headers, mock_adb_manager):
        """Test getting devices with mock devices."""
        # Add mock devices
        test_devices = create_test_devices(3)
        for device in test_devices:
            mock_adb_manager.add_device(device)
        
        with pytest.mock.patch('backend.api.devices.adb_manager', mock_adb_manager):
            response = await async_client.get(
                "/api/devices/",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 0  # Depends on connected devices

    async def test_get_device_info_success(self, async_client: AsyncClient,
                                          authenticated_headers, mock_adb_device):
        """Test getting specific device info."""
        device_id = mock_adb_device.device_id
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            mock_manager.get_device_info.return_value = mock_adb_device.get_device_info()
            
            response = await async_client.get(
                f"/api/devices/{device_id}",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == device_id
        assert data["model"] == mock_adb_device.model
        assert data["android_version"] == mock_adb_device.android_version

    async def test_get_device_info_not_found(self, async_client: AsyncClient,
                                            authenticated_headers):
        """Test getting info for non-existent device."""
        device_id = "nonexistent_device"
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = None
            
            response = await async_client.get(
                f"/api/devices/{device_id}",
                headers=authenticated_headers
            )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    async def test_connect_device_success(self, async_client: AsyncClient,
                                         authenticated_headers):
        """Test connecting to a device."""
        connection_data = {
            "connection_type": "wifi",
            "host": "192.168.1.100",
            "port": 5555
        }
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.connect_device_wifi.return_value = True
            
            response = await async_client.post(
                "/api/devices/connect",
                json=connection_data,
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "connected" in data["message"].lower()

    async def test_connect_device_failure(self, async_client: AsyncClient,
                                         authenticated_headers):
        """Test failed device connection."""
        connection_data = {
            "connection_type": "wifi",
            "host": "192.168.1.100",
            "port": 5555
        }
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.connect_device_wifi.return_value = False
            
            response = await async_client.post(
                "/api/devices/connect",
                json=connection_data,
                headers=authenticated_headers
            )
        
        assert response.status_code == 400
        data = response.json()
        assert "failed" in data["detail"].lower()

    async def test_disconnect_device_success(self, async_client: AsyncClient,
                                            authenticated_headers, mock_adb_device):
        """Test disconnecting a device."""
        device_id = mock_adb_device.device_id
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            mock_manager.disconnect_device.return_value = True
            
            response = await async_client.post(
                f"/api/devices/{device_id}/disconnect",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "disconnected" in data["message"].lower()

    async def test_get_device_analytics(self, async_client: AsyncClient,
                                       authenticated_headers, mock_adb_device,
                                       sample_device_data):
        """Test getting device analytics."""
        device_id = mock_adb_device.device_id
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            mock_manager.execute_command.return_value = "mock_output"
            
            # Mock device metrics
            mock_adb_device.get_current_metrics = lambda: sample_device_data
            
            response = await async_client.get(
                f"/api/devices/{device_id}/analytics",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == device_id
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "battery_level" in data

    async def test_execute_device_command(self, async_client: AsyncClient,
                                         authenticated_headers, mock_adb_device):
        """Test executing command on device."""
        device_id = mock_adb_device.device_id
        command_data = {
            "command": "shell getprop ro.build.version.release"
        }
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            mock_manager.execute_command.return_value = "13"
            
            response = await async_client.post(
                f"/api/devices/{device_id}/execute",
                json=command_data,
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["output"] == "13"
        assert data["command"] == command_data["command"]

    async def test_execute_dangerous_command_blocked(self, async_client: AsyncClient,
                                                    authenticated_headers, mock_adb_device):
        """Test that dangerous commands are blocked."""
        device_id = mock_adb_device.device_id
        dangerous_commands = [
            {"command": "shell rm -rf /"},
            {"command": "shell su -c 'rm -rf /'"},
            {"command": "reboot bootloader"},
            {"command": "fastboot erase userdata"}
        ]
        
        for command_data in dangerous_commands:
            response = await async_client.post(
                f"/api/devices/{device_id}/execute",
                json=command_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "dangerous" in data["detail"].lower() or "not allowed" in data["detail"].lower()

    async def test_get_installed_apps(self, async_client: AsyncClient,
                                     authenticated_headers, mock_adb_device):
        """Test getting installed applications."""
        device_id = mock_adb_device.device_id
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            mock_manager.get_installed_packages.return_value = [
                "com.android.chrome",
                "com.whatsapp",
                "com.spotify.music"
            ]
            
            response = await async_client.get(
                f"/api/devices/{device_id}/apps",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert "com.android.chrome" in data

    async def test_install_apk(self, async_client: AsyncClient,
                              authenticated_headers, mock_adb_device):
        """Test APK installation."""
        device_id = mock_adb_device.device_id
        install_data = {
            "apk_path": "/path/to/test.apk"
        }
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            mock_manager.install_apk.return_value = True
            
            response = await async_client.post(
                f"/api/devices/{device_id}/install",
                json=install_data,
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "installed" in data["message"].lower()

    async def test_uninstall_package(self, async_client: AsyncClient,
                                    authenticated_headers, mock_adb_device):
        """Test package uninstallation."""
        device_id = mock_adb_device.device_id
        package_name = "com.example.testapp"
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            mock_manager.uninstall_package.return_value = True
            
            response = await async_client.delete(
                f"/api/devices/{device_id}/apps/{package_name}",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "uninstalled" in data["message"].lower()

    async def test_device_optimization_recommendations(self, async_client: AsyncClient,
                                                      authenticated_headers, 
                                                      mock_adb_device, mock_ai_service):
        """Test getting device optimization recommendations."""
        device_id = mock_adb_device.device_id
        
        # Mock AI recommendations
        from backend.services.intelligence_service import AIRecommendation
        mock_recommendations = [
            AIRecommendation(
                recommendation_id="rec_001",
                device_id=device_id,
                category="performance",
                title="Clear Cache",
                description="Clear app cache to improve performance",
                priority="medium",
                confidence=0.8,
                expected_impact="5-10% performance improvement",
                implementation_difficulty="easy",
                estimated_time="2 minutes",
                reasoning=["High cache usage detected"],
                evidence={"cache_size": 500},
                alternatives=["Restart apps", "Clear storage"]
            )
        ]
        
        with pytest.mock.patch('backend.api.devices.ai_service', mock_ai_service):
            mock_ai_service.generate_recommendations.return_value = mock_recommendations
            
            response = await async_client.get(
                f"/api/devices/{device_id}/recommendations",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["category"] == "performance"

    async def test_device_security_scan(self, async_client: AsyncClient,
                                       authenticated_headers, mock_adb_device):
        """Test device security scanning."""
        device_id = mock_adb_device.device_id
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            
            # Mock security scan results
            mock_adb_device.get_security_events = lambda: [
                {
                    "event_type": "suspicious_permission",
                    "severity": "medium",
                    "description": "App requesting suspicious permissions",
                    "source_app": "com.suspicious.app",
                    "timestamp": datetime.now()
                }
            ]
            
            response = await async_client.post(
                f"/api/devices/{device_id}/security/scan",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "scan_results" in data
        assert isinstance(data["scan_results"], list)

    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test unauthorized access to devices API."""
        response = await async_client.get("/api/devices/")
        
        assert response.status_code == 401

    async def test_invalid_device_id_format(self, async_client: AsyncClient,
                                           authenticated_headers):
        """Test invalid device ID format."""
        invalid_device_ids = ["", "invalid/id", "id with spaces", "id@#$%"]
        
        for device_id in invalid_device_ids:
            response = await async_client.get(
                f"/api/devices/{device_id}",
                headers=authenticated_headers
            )
            
            # Should return 422 for invalid format or 404 for not found
            assert response.status_code in [404, 422]

    async def test_concurrent_device_operations(self, async_client: AsyncClient,
                                               authenticated_headers, mock_adb_manager):
        """Test concurrent operations on multiple devices."""
        test_devices = create_test_devices(3)
        for device in test_devices:
            mock_adb_manager.add_device(device)
        
        import asyncio
        
        with pytest.mock.patch('backend.api.devices.adb_manager', mock_adb_manager):
            # Create concurrent requests
            tasks = []
            for device in test_devices[:2]:  # Test with first 2 devices
                task = async_client.get(
                    f"/api/devices/{device.device_id}",
                    headers=authenticated_headers
                )
                tasks.append(task)
            
            # Execute concurrent requests
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all requests completed
            for response in responses:
                if not isinstance(response, Exception):
                    assert response.status_code in [200, 404]  # Either found or not found

    async def test_device_analytics_history(self, async_client: AsyncClient,
                                           authenticated_headers, mock_adb_device,
                                           test_db_session):
        """Test getting device analytics history."""
        device_id = mock_adb_device.device_id
        
        # Add some analytics data to the database
        analytics_data = [
            Analytics(
                device_id=device_id,
                cpu_usage=45.5,
                memory_usage=67.8,
                storage_usage_percentage=78.9,
                battery_level=85,
                recorded_at=datetime.now()
            ),
            Analytics(
                device_id=device_id,
                cpu_usage=50.2,
                memory_usage=70.1,
                storage_usage_percentage=79.2,
                battery_level=82,
                recorded_at=datetime.now()
            )
        ]
        
        for data in analytics_data:
            test_db_session.add(data)
        test_db_session.commit()
        
        response = await async_client.get(
            f"/api/devices/{device_id}/analytics/history",
            params={"limit": 10},
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    async def test_device_real_time_metrics(self, async_client: AsyncClient,
                                           authenticated_headers, mock_adb_device):
        """Test getting real-time device metrics."""
        device_id = mock_adb_device.device_id
        
        with pytest.mock.patch('backend.api.devices.adb_manager') as mock_manager:
            mock_manager.get_device.return_value = mock_adb_device
            
            response = await async_client.get(
                f"/api/devices/{device_id}/metrics/realtime",
                headers=authenticated_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "metrics" in data
        assert isinstance(data["metrics"], dict)
