"""
End-to-end tests for policy enforcement and device control as per roadmap.
Testing: password policies, restrictions, remote commands, geofencing, compliance rules.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch, Mock, AsyncMock

from backend.tests.mocks.mock_adb_device import MockADBDevice, create_test_devices


@pytest.mark.e2e
@pytest.mark.slow
class TestPolicyEnforcement:
    """End-to-end tests for policy enforcement and device control."""

    @pytest.fixture
    def test_device(self):
        """Create a test device for policy testing."""
        return MockADBDevice(
            device_id="policy_test_device_001",
            model="PolicyTestPhone",
            android_version="13",
            is_connected=True
        )

    @pytest.fixture
    def password_policy(self):
        """Sample password policy configuration."""
        return {
            "policy_id": "password_policy_001",
            "policy_type": "password_requirements",
            "settings": {
                "minimum_length": 8,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digits": True,
                "require_symbols": True,
                "prevent_common_passwords": True,
                "password_history_length": 5,
                "max_failed_attempts": 3,
                "lockout_duration_minutes": 15
            }
        }

    @pytest.fixture
    def restriction_policy(self):
        """Sample device restriction policy."""
        return {
            "policy_id": "restrictions_policy_001",
            "policy_type": "device_restrictions",
            "settings": {
                "camera_disabled": True,
                "bluetooth_disabled": False,
                "wifi_config_disabled": True,
                "usb_mass_storage_disabled": True,
                "microphone_disabled": False,
                "screen_capture_disabled": True,
                "developer_options_disabled": True,
                "install_unknown_sources_disabled": True,
                "safe_boot_disabled": True
            }
        }

    async def test_password_policy_enforcement(self, async_client: AsyncClient,
                                             authenticated_headers, test_device, password_policy):
        """Test password policy enforcement on device."""
        device_id = test_device.device_id
        
        # Step 1: Apply password policy to device
        policy_application = {
            "device_id": device_id,
            "policies": [password_policy],
            "enforce_immediately": True
        }
        
        with patch('backend.api.policies.apply_device_policy') as mock_apply, \
             patch('backend.api.devices.execute_command') as mock_execute:
            
            mock_apply.return_value = {"policy_applied": True, "policy_id": password_policy["policy_id"]}
            mock_execute.return_value = "Policy applied successfully"
            
            response = await async_client.post(
                f"/api/policies/apply",
                json=policy_application,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["policy_applied"] == True
        
        # Step 2: Verify policy is active on device
        verification_response = await async_client.get(
            f"/api/devices/{device_id}/policies/active",
            headers=authenticated_headers
        )
        
        assert verification_response.status_code == 200
        active_policies = verification_response.json()
        policy_ids = [p["policy_id"] for p in active_policies]
        assert password_policy["policy_id"] in policy_ids
        
        # Step 3: Test policy enforcement - simulate password violation
        violation_test = {
            "device_id": device_id,
            "test_scenario": "weak_password_attempt",
            "password": "123"  # Weak password
        }
        
        with patch('backend.api.policies.test_password_policy') as mock_test:
            mock_test.return_value = {
                "policy_violated": True,
                "violations": ["minimum_length", "require_uppercase", "require_lowercase", "require_symbols"],
                "action_taken": "password_rejected"
            }
            
            test_response = await async_client.post(
                f"/api/policies/test-enforcement",
                json=violation_test,
                headers=authenticated_headers
            )
            
            assert test_response.status_code == 200
            test_data = test_response.json()
            assert test_data["policy_violated"] == True
            assert "minimum_length" in test_data["violations"]

    async def test_device_restrictions_enforcement(self, async_client: AsyncClient,
                                                 authenticated_headers, test_device, restriction_policy):
        """Test device restriction policy enforcement."""
        device_id = test_device.device_id
        
        # Apply restriction policy
        policy_application = {
            "device_id": device_id,
            "policies": [restriction_policy],
            "enforce_immediately": True
        }
        
        with patch('backend.api.policies.apply_device_policy') as mock_apply:
            mock_apply.return_value = {"policy_applied": True}
            
            response = await async_client.post(
                f"/api/policies/apply",
                json=policy_application,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
        
        # Test individual restriction enforcement
        restrictions_to_test = [
            ("camera_disabled", "Camera access blocked"),
            ("usb_mass_storage_disabled", "USB mass storage disabled"),
            ("screen_capture_disabled", "Screen capture blocked"),
            ("developer_options_disabled", "Developer options disabled")
        ]
        
        for restriction, expected_message in restrictions_to_test:
            test_data = {
                "device_id": device_id,
                "restriction": restriction,
                "test_action": f"attempt_{restriction.replace('_disabled', '')}"
            }
            
            with patch('backend.api.policies.test_restriction') as mock_test:
                mock_test.return_value = {
                    "restriction_active": True,
                    "action_blocked": True,
                    "message": expected_message
                }
                
                test_response = await async_client.post(
                    f"/api/policies/test-restriction",
                    json=test_data,
                    headers=authenticated_headers
                )
                
                assert test_response.status_code == 200
                result = test_response.json()
                assert result["restriction_active"] == True
                assert result["action_blocked"] == True

    async def test_remote_lock_command(self, async_client: AsyncClient,
                                     authenticated_headers, test_device):
        """Test remote lock command execution and idempotency."""
        device_id = test_device.device_id
        
        # First lock command
        lock_command = {
            "device_id": device_id,
            "command": "lock",
            "message": "Device locked by administrator",
            "lock_duration": 3600,  # 1 hour
            "command_id": "lock_cmd_001"
        }
        
        with patch('backend.api.devices.execute_remote_command') as mock_execute, \
             patch('backend.api.audit.log_command_execution') as mock_audit:
            
            mock_execute.return_value = {
                "command_executed": True,
                "device_state": "locked",
                "execution_time": datetime.now().isoformat()
            }
            
            response = await async_client.post(
                f"/api/devices/{device_id}/commands/lock",
                json=lock_command,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["command_executed"] == True
            assert data["device_state"] == "locked"
            
            # Verify audit logging
            mock_audit.assert_called_once()
            audit_call = mock_audit.call_args[0][0]
            assert audit_call["command_type"] == "lock"
            assert audit_call["device_id"] == device_id
        
        # Test idempotency - sending same command again
        duplicate_response = await async_client.post(
            f"/api/devices/{device_id}/commands/lock",
            json=lock_command,
            headers=authenticated_headers
        )
        
        # Should return same result without re-executing
        assert duplicate_response.status_code == 200
        duplicate_data = duplicate_response.json()
        assert duplicate_data["command_executed"] == True
        assert "already_executed" in duplicate_data or duplicate_data["device_state"] == "locked"

    async def test_remote_wipe_command_with_authorization(self, async_client: AsyncClient,
                                                        authenticated_headers, test_device):
        """Test remote wipe command with proper authorization checks."""
        device_id = test_device.device_id
        
        # Wipe command requires elevated privileges
        wipe_command = {
            "device_id": device_id,
            "command": "wipe",
            "wipe_type": "factory_reset",
            "confirm_wipe": True,
            "authorization_code": "WIPE_CONFIRM_123",
            "reason": "Device compromised"
        }
        
        with patch('backend.api.devices.validate_wipe_authorization') as mock_validate, \
             patch('backend.api.devices.execute_factory_reset') as mock_wipe, \
             patch('backend.api.audit.log_critical_action') as mock_audit:
            
            mock_validate.return_value = {"authorized": True, "authorized_by": "admin_user"}
            mock_wipe.return_value = {
                "wipe_initiated": True,
                "wipe_id": "wipe_001",
                "estimated_completion": datetime.now() + timedelta(minutes=10)
            }
            
            response = await async_client.post(
                f"/api/devices/{device_id}/commands/wipe",
                json=wipe_command,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["wipe_initiated"] == True
            assert "wipe_id" in data
            
            # Verify authorization was checked
            mock_validate.assert_called_once()
            
            # Verify critical action was logged
            mock_audit.assert_called_once()
            audit_call = mock_audit.call_args[0][0]
            assert audit_call["action"] == "factory_reset"
            assert audit_call["device_id"] == device_id
            assert audit_call["severity"] == "critical"

    async def test_geofencing_policy_enforcement(self, async_client: AsyncClient,
                                               authenticated_headers, test_device):
        """Test geofencing policy enforcement."""
        device_id = test_device.device_id
        
        # Define geofence policy
        geofence_policy = {
            "policy_id": "geofence_policy_001",
            "policy_type": "geofencing",
            "settings": {
                "allowed_zones": [
                    {
                        "zone_id": "office_zone",
                        "name": "Office Building",
                        "center_lat": 37.7749,
                        "center_lng": -122.4194,
                        "radius_meters": 500,
                        "active_hours": "09:00-18:00"
                    }
                ],
                "violations_action": "alert_and_lock",
                "grace_period_minutes": 15
            }
        }
        
        # Apply geofencing policy
        with patch('backend.api.policies.apply_geofence_policy') as mock_apply_geo:
            mock_apply_geo.return_value = {"policy_applied": True, "zones_configured": 1}
            
            response = await async_client.post(
                f"/api/policies/geofencing/apply",
                json={"device_id": device_id, "policy": geofence_policy},
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
        
        # Simulate device location outside allowed zone
        location_update = {
            "device_id": device_id,
            "latitude": 40.7128,  # New York (outside zone)
            "longitude": -74.0060,
            "accuracy": 10,
            "timestamp": datetime.now().isoformat()
        }
        
        with patch('backend.api.policies.check_geofence_violation') as mock_check, \
             patch('backend.api.devices.trigger_compliance_action') as mock_action:
            
            mock_check.return_value = {
                "violation_detected": True,
                "violated_zones": ["office_zone"],
                "distance_from_zone": 2500,
                "action_required": "alert_and_lock"
            }
            mock_action.return_value = {"action_executed": True, "device_locked": True}
            
            violation_response = await async_client.post(
                f"/api/devices/{device_id}/location",
                json=location_update,
                headers=authenticated_headers
            )
            
            assert violation_response.status_code == 200
            violation_data = violation_response.json()
            assert violation_data["violation_detected"] == True
            
            # Verify compliance action was triggered
            mock_action.assert_called_once()

    async def test_compliance_rules_with_automatic_remediation(self, async_client: AsyncClient,
                                                             authenticated_headers, test_device):
        """Test compliance rules with automatic remediation actions."""
        device_id = test_device.device_id
        
        # Define compliance rule
        compliance_rule = {
            "rule_id": "security_compliance_001",
            "rule_type": "security_posture",
            "conditions": {
                "screen_lock_enabled": True,
                "encryption_enabled": True,
                "unknown_sources_disabled": True,
                "developer_options_disabled": True,
                "minimum_os_version": "12"
            },
            "remediation_actions": [
                "enforce_screen_lock",
                "disable_unknown_sources",
                "send_notification"
            ],
            "notification_message": "Your device does not meet security requirements"
        }
        
        # Apply compliance rule
        with patch('backend.api.policies.apply_compliance_rule') as mock_apply_rule:
            mock_apply_rule.return_value = {"rule_applied": True}
            
            response = await async_client.post(
                f"/api/policies/compliance/apply",
                json={"device_id": device_id, "rule": compliance_rule},
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
        
        # Simulate compliance check
        compliance_check = {
            "device_id": device_id,
            "check_type": "scheduled",
            "force_remediation": True
        }
        
        with patch('backend.api.policies.evaluate_device_compliance') as mock_evaluate, \
             patch('backend.api.policies.execute_remediation') as mock_remediate:
            
            # Simulate non-compliant device
            mock_evaluate.return_value = {
                "compliant": False,
                "violations": ["screen_lock_disabled", "unknown_sources_enabled"],
                "risk_level": "high"
            }
            mock_remediate.return_value = {
                "remediation_executed": True,
                "actions_taken": ["enforced_screen_lock", "disabled_unknown_sources"],
                "notification_sent": True
            }
            
            check_response = await async_client.post(
                f"/api/policies/compliance/check",
                json=compliance_check,
                headers=authenticated_headers
            )
            
            assert check_response.status_code == 200
            check_data = check_response.json()
            assert check_data["compliant"] == False
            assert check_data["remediation_executed"] == True
            assert "enforced_screen_lock" in check_data["actions_taken"]

    async def test_kiosk_mode_enforcement(self, async_client: AsyncClient,
                                        authenticated_headers, test_device):
        """Test kiosk mode and lock task mode enforcement."""
        device_id = test_device.device_id
        
        # Configure kiosk mode
        kiosk_config = {
            "device_id": device_id,
            "mode": "single_app_kiosk",
            "allowed_app": "com.company.kiosk_app",
            "restrictions": {
                "disable_home_button": True,
                "disable_recent_apps": True,
                "disable_notifications": True,
                "disable_status_bar": True,
                "prevent_escape": True
            },
            "exit_conditions": {
                "admin_password_required": True,
                "time_based_exit": False
            }
        }
        
        with patch('backend.api.devices.enable_kiosk_mode') as mock_kiosk, \
             patch('backend.api.devices.configure_lock_task') as mock_lock_task:
            
            mock_kiosk.return_value = {
                "kiosk_enabled": True,
                "locked_app": "com.company.kiosk_app",
                "escape_prevention": True
            }
            mock_lock_task.return_value = {"lock_task_configured": True}
            
            response = await async_client.post(
                f"/api/devices/{device_id}/kiosk/enable",
                json=kiosk_config,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["kiosk_enabled"] == True
            assert data["escape_prevention"] == True
        
        # Test escape prevention
        escape_attempt = {
            "device_id": device_id,
            "action": "home_button_press",
            "user_action": "attempt_exit"
        }
        
        with patch('backend.api.devices.handle_kiosk_escape_attempt') as mock_escape:
            mock_escape.return_value = {
                "escape_prevented": True,
                "action_blocked": True,
                "admin_notified": True
            }
            
            escape_response = await async_client.post(
                f"/api/devices/{device_id}/kiosk/test-escape",
                json=escape_attempt,
                headers=authenticated_headers
            )
            
            assert escape_response.status_code == 200
            escape_data = escape_response.json()
            assert escape_data["escape_prevented"] == True

    async def test_network_and_wifi_policy_enforcement(self, async_client: AsyncClient,
                                                     authenticated_headers, test_device):
        """Test network and WiFi policy enforcement."""
        device_id = test_device.device_id
        
        # Define network policy
        network_policy = {
            "policy_id": "network_policy_001",
            "policy_type": "network_configuration",
            "settings": {
                "allowed_wifi_networks": [
                    {"ssid": "CompanyWiFi", "security": "WPA2_Enterprise"},
                    {"ssid": "CompanyGuest", "security": "WPA2_Personal"}
                ],
                "blocked_wifi_networks": [
                    {"ssid": "PublicWiFi", "reason": "security_risk"}
                ],
                "wifi_configuration_disabled": True,
                "mobile_data_restrictions": {
                    "roaming_disabled": True,
                    "background_data_restricted": True
                }
            }
        }
        
        # Apply network policy
        with patch('backend.api.policies.apply_network_policy') as mock_apply_net:
            mock_apply_net.return_value = {"policy_applied": True, "wifi_configs_set": 2}
            
            response = await async_client.post(
                f"/api/policies/network/apply",
                json={"device_id": device_id, "policy": network_policy},
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
        
        # Test WiFi connection attempt to blocked network
        wifi_attempt = {
            "device_id": device_id,
            "ssid": "PublicWiFi",
            "action": "connect_attempt"
        }
        
        with patch('backend.api.policies.validate_wifi_connection') as mock_validate_wifi:
            mock_validate_wifi.return_value = {
                "connection_allowed": False,
                "block_reason": "network_blocked_by_policy",
                "policy_id": "network_policy_001"
            }
            
            wifi_response = await async_client.post(
                f"/api/devices/{device_id}/network/validate-connection",
                json=wifi_attempt,
                headers=authenticated_headers
            )
            
            assert wifi_response.status_code == 200
            wifi_data = wifi_response.json()
            assert wifi_data["connection_allowed"] == False
            assert "blocked_by_policy" in wifi_data["block_reason"]

    async def test_certificate_and_vpn_policy_enforcement(self, async_client: AsyncClient,
                                                        authenticated_headers, test_device):
        """Test certificate installation and VPN setup policies."""
        device_id = test_device.device_id
        
        # Certificate installation policy
        cert_policy = {
            "policy_id": "certificate_policy_001",
            "certificates": [
                {
                    "cert_id": "root_ca_cert",
                    "type": "ca_certificate",
                    "install_location": "system_store",
                    "certificate_data": "base64_encoded_cert_data"
                }
            ],
            "vpn_configuration": {
                "vpn_profile_id": "company_vpn",
                "server": "vpn.company.com",
                "type": "IPSec",
                "always_on": True,
                "allow_bypass": False
            }
        }
        
        with patch('backend.api.policies.install_certificates') as mock_install_certs, \
             patch('backend.api.policies.configure_vpn') as mock_configure_vpn:
            
            mock_install_certs.return_value = {
                "certificates_installed": 1,
                "installation_success": True,
                "cert_ids": ["root_ca_cert"]
            }
            mock_configure_vpn.return_value = {
                "vpn_configured": True,
                "profile_id": "company_vpn",
                "always_on_enabled": True
            }
            
            response = await async_client.post(
                f"/api/policies/certificates/apply",
                json={"device_id": device_id, "policy": cert_policy},
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["certificates_installed"] == 1
            assert data["vpn_configured"] == True

    async def test_os_update_policy_enforcement(self, async_client: AsyncClient,
                                              authenticated_headers, test_device):
        """Test OS update control policies."""
        device_id = test_device.device_id
        
        # OS update policy
        update_policy = {
            "policy_id": "update_policy_001",
            "policy_type": "system_updates",
            "settings": {
                "update_mode": "scheduled",
                "maintenance_window": {
                    "start_time": "02:00",
                    "end_time": "04:00",
                    "days": ["monday", "wednesday", "friday"]
                },
                "auto_update_enabled": True,
                "defer_updates_days": 7,
                "critical_updates_immediate": True
            }
        }
        
        with patch('backend.api.policies.apply_update_policy') as mock_update_policy:
            mock_update_policy.return_value = {
                "policy_applied": True,
                "maintenance_window_set": True,
                "auto_update_configured": True
            }
            
            response = await async_client.post(
                f"/api/policies/updates/apply",
                json={"device_id": device_id, "policy": update_policy},
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["policy_applied"] == True
            assert data["maintenance_window_set"] == True
        
        # Test update enforcement during maintenance window
        update_check = {
            "device_id": device_id,
            "current_time": "02:30",  # Within maintenance window
            "updates_available": [
                {"type": "security", "severity": "critical"},
                {"type": "system", "severity": "normal"}
            ]
        }
        
        with patch('backend.api.policies.check_update_window') as mock_check_window, \
             patch('backend.api.devices.trigger_system_update') as mock_trigger_update:
            
            mock_check_window.return_value = {"in_maintenance_window": True}
            mock_trigger_update.return_value = {
                "update_initiated": True,
                "updates_to_install": ["critical_security_update"],
                "estimated_duration": "30 minutes"
            }
            
            update_response = await async_client.post(
                f"/api/devices/{device_id}/updates/check",
                json=update_check,
                headers=authenticated_headers
            )
            
            assert update_response.status_code == 200
            update_data = update_response.json()
            assert update_data["update_initiated"] == True
