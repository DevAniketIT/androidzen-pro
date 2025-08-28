"""
End-to-end tests for device enrollment flows as per roadmap.
Testing: zero touch, QR code, NFC bump, and manual DPC enrollment with and without SSO.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch, Mock, AsyncMock

from backend.tests.mocks.mock_adb_device import MockADBDevice, create_test_devices


@pytest.mark.e2e
@pytest.mark.slow
class TestDeviceEnrollmentFlows:
    """End-to-end tests for device enrollment workflows."""

    @pytest.fixture
    def enrollment_data(self):
        """Sample enrollment data for testing."""
        return {
            "organization_id": "org_test_123",
            "enrollment_token": "token_abc123",
            "device_owner_mode": True,
            "policy_set": "standard_policy",
            "user_id": "test_admin",
            "device_info": {
                "model": "TestPhone Pro",
                "android_version": "13",
                "manufacturer": "TestCorp"
            }
        }

    @pytest.fixture
    def sso_config(self):
        """SSO configuration for testing."""
        return {
            "provider": "okta",
            "domain": "testcorp.okta.com",
            "client_id": "test_client_id",
            "redirect_uri": "https://androidzen.test/auth/callback"
        }

    async def test_zero_touch_enrollment_success(self, async_client: AsyncClient, 
                                               authenticated_headers, enrollment_data):
        """Test successful zero touch enrollment."""
        # Step 1: Device contacts zero touch service
        enrollment_data["enrollment_method"] = "zero_touch"
        
        with patch('backend.api.enrollment.validate_zero_touch_token') as mock_validate, \
             patch('backend.api.enrollment.create_device_profile') as mock_create_profile, \
             patch('backend.api.enrollment.apply_device_policies') as mock_apply_policies:
            
            mock_validate.return_value = True
            mock_create_profile.return_value = {"device_id": "zt_device_001", "profile_id": "profile_123"}
            mock_apply_policies.return_value = True
            
            # Initiate enrollment
            response = await async_client.post(
                "/api/enrollment/zero-touch/initiate",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "enrollment_initiated"
            assert "device_id" in data
            assert "enrollment_id" in data
            
            enrollment_id = data["enrollment_id"]
            
            # Step 2: Check enrollment status
            await asyncio.sleep(0.1)  # Simulate processing time
            
            status_response = await async_client.get(
                f"/api/enrollment/status/{enrollment_id}",
                headers=authenticated_headers
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] in ["in_progress", "completed"]
            
            # Step 3: Complete enrollment
            completion_data = {
                "enrollment_id": enrollment_id,
                "device_confirmation": True,
                "initial_setup_completed": True
            }
            
            complete_response = await async_client.post(
                "/api/enrollment/complete",
                json=completion_data,
                headers=authenticated_headers
            )
            
            assert complete_response.status_code == 200
            complete_data = complete_response.json()
            assert complete_data["status"] == "enrollment_completed"
            assert complete_data["device_enrolled"] == True

    async def test_qr_code_enrollment_success(self, async_client: AsyncClient,
                                            authenticated_headers, enrollment_data):
        """Test successful QR code enrollment."""
        enrollment_data["enrollment_method"] = "qr_code"
        
        # Step 1: Generate QR code
        qr_request = {
            "organization_id": enrollment_data["organization_id"],
            "policy_set": enrollment_data["policy_set"],
            "expires_in": 3600  # 1 hour
        }
        
        with patch('backend.api.enrollment.generate_qr_token') as mock_generate_qr:
            mock_generate_qr.return_value = {
                "qr_code_data": "androidzenqr://enroll?token=qr_token_123&org=org_test_123",
                "token": "qr_token_123",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
            }
            
            qr_response = await async_client.post(
                "/api/enrollment/qr-code/generate",
                json=qr_request,
                headers=authenticated_headers
            )
            
            assert qr_response.status_code == 200
            qr_data = qr_response.json()
            assert "qr_code_data" in qr_data
            assert "token" in qr_data
            
            qr_token = qr_data["token"]
        
        # Step 2: Device scans QR code and starts enrollment
        enrollment_data["qr_token"] = qr_token
        
        with patch('backend.api.enrollment.validate_qr_token') as mock_validate_qr, \
             patch('backend.api.enrollment.provision_device') as mock_provision:
            
            mock_validate_qr.return_value = True
            mock_provision.return_value = {"device_id": "qr_device_001", "status": "provisioned"}
            
            enroll_response = await async_client.post(
                "/api/enrollment/qr-code/enroll",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert enroll_response.status_code == 200
            enroll_data = enroll_response.json()
            assert enroll_data["status"] == "enrollment_completed"
            assert enroll_data["enrollment_method"] == "qr_code"

    async def test_nfc_bump_enrollment_success(self, async_client: AsyncClient,
                                             authenticated_headers, enrollment_data):
        """Test successful NFC bump enrollment."""
        enrollment_data["enrollment_method"] = "nfc_bump"
        
        # Step 1: Admin device prepares NFC enrollment data
        nfc_data = {
            "organization_id": enrollment_data["organization_id"],
            "enrollment_token": enrollment_data["enrollment_token"],
            "nfc_session_id": "nfc_session_123"
        }
        
        with patch('backend.api.enrollment.create_nfc_session') as mock_create_nfc:
            mock_create_nfc.return_value = {
                "session_id": "nfc_session_123",
                "nfc_payload": "nfc_encrypted_payload_data",
                "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            
            nfc_response = await async_client.post(
                "/api/enrollment/nfc/prepare",
                json=nfc_data,
                headers=authenticated_headers
            )
            
            assert nfc_response.status_code == 200
            nfc_session_data = nfc_response.json()
            assert "session_id" in nfc_session_data
            assert "nfc_payload" in nfc_session_data
        
        # Step 2: Device receives NFC data and enrolls
        enrollment_data["nfc_session_id"] = nfc_session_data["session_id"]
        enrollment_data["nfc_payload"] = nfc_session_data["nfc_payload"]
        
        with patch('backend.api.enrollment.validate_nfc_session') as mock_validate_nfc, \
             patch('backend.api.enrollment.process_nfc_enrollment') as mock_process_nfc:
            
            mock_validate_nfc.return_value = True
            mock_process_nfc.return_value = {
                "device_id": "nfc_device_001",
                "enrollment_status": "completed",
                "device_owner_granted": True
            }
            
            enroll_response = await async_client.post(
                "/api/enrollment/nfc/enroll",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert enroll_response.status_code == 200
            enroll_data = enroll_response.json()
            assert enroll_data["status"] == "enrollment_completed"
            assert enroll_data["enrollment_method"] == "nfc_bump"

    async def test_manual_dpc_enrollment_success(self, async_client: AsyncClient,
                                               authenticated_headers, enrollment_data):
        """Test successful manual DPC enrollment."""
        enrollment_data["enrollment_method"] = "manual_dpc"
        
        # Step 1: User manually installs DPC app
        dpc_install_data = {
            "package_name": "com.androidzen.dpc",
            "device_id": "manual_device_001",
            "installation_method": "manual_install"
        }
        
        with patch('backend.api.enrollment.verify_dpc_installation') as mock_verify_dpc:
            mock_verify_dpc.return_value = {
                "installed": True,
                "version": "1.0.0",
                "device_admin_enabled": False  # Not yet enabled
            }
            
            verify_response = await async_client.post(
                "/api/enrollment/manual-dpc/verify-installation",
                json=dpc_install_data,
                headers=authenticated_headers
            )
            
            assert verify_response.status_code == 200
            verify_data = verify_response.json()
            assert verify_data["installed"] == True
        
        # Step 2: Enable device admin and start enrollment
        enrollment_data["device_id"] = "manual_device_001"
        
        with patch('backend.api.enrollment.enable_device_admin') as mock_enable_admin, \
             patch('backend.api.enrollment.start_manual_enrollment') as mock_start_enrollment:
            
            mock_enable_admin.return_value = True
            mock_start_enrollment.return_value = {
                "enrollment_id": "manual_enroll_001",
                "status": "admin_enabled",
                "next_step": "organization_setup"
            }
            
            enroll_response = await async_client.post(
                "/api/enrollment/manual-dpc/start",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert enroll_response.status_code == 200
            enroll_data = enroll_response.json()
            assert enroll_data["status"] == "admin_enabled"
            assert "enrollment_id" in enroll_data

    async def test_sso_enrollment_flow(self, async_client: AsyncClient,
                                     authenticated_headers, enrollment_data, sso_config):
        """Test enrollment with SSO authentication."""
        enrollment_data["enrollment_method"] = "qr_code"
        enrollment_data["sso_required"] = True
        enrollment_data["sso_config"] = sso_config
        
        # Step 1: Generate QR code with SSO requirement
        qr_request = {
            "organization_id": enrollment_data["organization_id"],
            "policy_set": enrollment_data["policy_set"],
            "sso_required": True,
            "sso_provider": sso_config["provider"]
        }
        
        with patch('backend.api.enrollment.generate_sso_qr_token') as mock_generate_sso_qr:
            mock_generate_sso_qr.return_value = {
                "qr_code_data": "androidzenqr://enroll?token=sso_qr_token_123&sso=okta",
                "token": "sso_qr_token_123",
                "sso_auth_url": "https://testcorp.okta.com/oauth2/authorize?..."
            }
            
            qr_response = await async_client.post(
                "/api/enrollment/qr-code/generate",
                json=qr_request,
                headers=authenticated_headers
            )
            
            assert qr_response.status_code == 200
            qr_data = qr_response.json()
            assert "sso_auth_url" in qr_data
        
        # Step 2: User completes SSO authentication
        sso_callback_data = {
            "token": qr_data["token"],
            "auth_code": "sso_auth_code_123",
            "state": "sso_state_123"
        }
        
        with patch('backend.api.auth.validate_sso_callback') as mock_validate_sso:
            mock_validate_sso.return_value = {
                "user_id": "sso_user_123",
                "email": "user@testcorp.com",
                "organization_id": enrollment_data["organization_id"],
                "authenticated": True
            }
            
            sso_response = await async_client.post(
                "/api/auth/sso/callback",
                json=sso_callback_data,
                headers=authenticated_headers
            )
            
            assert sso_response.status_code == 200
            sso_auth_data = sso_response.json()
            assert sso_auth_data["authenticated"] == True
        
        # Step 3: Complete enrollment with authenticated user
        enrollment_data["sso_user_token"] = "sso_user_token_123"
        
        with patch('backend.api.enrollment.complete_sso_enrollment') as mock_complete_sso:
            mock_complete_sso.return_value = {
                "device_id": "sso_device_001",
                "enrollment_status": "completed",
                "user_assigned": True
            }
            
            complete_response = await async_client.post(
                "/api/enrollment/complete-sso",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert complete_response.status_code == 200
            complete_data = complete_response.json()
            assert complete_data["enrollment_status"] == "completed"
            assert complete_data["user_assigned"] == True

    async def test_enrollment_failure_network_issues(self, async_client: AsyncClient,
                                                   authenticated_headers, enrollment_data):
        """Test enrollment failure scenarios with network issues."""
        enrollment_data["enrollment_method"] = "zero_touch"
        
        # Simulate network timeout during enrollment
        with patch('backend.api.enrollment.validate_zero_touch_token', 
                  side_effect=asyncio.TimeoutError("Network timeout")):
            
            response = await async_client.post(
                "/api/enrollment/zero-touch/initiate",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 408  # Request Timeout
            data = response.json()
            assert "timeout" in data["detail"].lower()

    async def test_enrollment_failure_invalid_token(self, async_client: AsyncClient,
                                                  authenticated_headers, enrollment_data):
        """Test enrollment failure with invalid tokens."""
        enrollment_data["enrollment_method"] = "qr_code"
        enrollment_data["qr_token"] = "invalid_token_123"
        
        with patch('backend.api.enrollment.validate_qr_token') as mock_validate:
            mock_validate.return_value = False
            
            response = await async_client.post(
                "/api/enrollment/qr-code/enroll",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "invalid" in data["detail"].lower()

    async def test_enrollment_recovery_after_failure(self, async_client: AsyncClient,
                                                   authenticated_headers, enrollment_data):
        """Test enrollment recovery after partial failure."""
        enrollment_data["enrollment_method"] = "manual_dpc"
        device_id = "recovery_device_001"
        
        # Step 1: First enrollment attempt fails during policy application
        enrollment_data["device_id"] = device_id
        
        with patch('backend.api.enrollment.enable_device_admin') as mock_enable, \
             patch('backend.api.enrollment.apply_device_policies', 
                  side_effect=Exception("Policy application failed")):
            
            mock_enable.return_value = True
            
            response = await async_client.post(
                "/api/enrollment/manual-dpc/start",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 500
        
        # Step 2: Retry enrollment - should detect partial state and continue
        retry_data = enrollment_data.copy()
        retry_data["retry_enrollment"] = True
        
        with patch('backend.api.enrollment.detect_partial_enrollment') as mock_detect, \
             patch('backend.api.enrollment.resume_enrollment') as mock_resume:
            
            mock_detect.return_value = {
                "partial_enrollment_found": True,
                "completed_steps": ["device_admin_enabled"],
                "failed_step": "policy_application"
            }
            mock_resume.return_value = {
                "enrollment_id": "recovery_enroll_001",
                "status": "resumed",
                "next_step": "policy_application"
            }
            
            retry_response = await async_client.post(
                "/api/enrollment/retry",
                json=retry_data,
                headers=authenticated_headers
            )
            
            assert retry_response.status_code == 200
            retry_response_data = retry_response.json()
            assert retry_response_data["status"] == "resumed"

    async def test_work_profile_enrollment(self, async_client: AsyncClient,
                                         authenticated_headers, enrollment_data):
        """Test work profile creation during enrollment."""
        enrollment_data["enrollment_method"] = "manual_dpc"
        enrollment_data["device_owner_mode"] = False  # Work profile mode
        enrollment_data["work_profile_config"] = {
            "profile_name": "Work Profile",
            "allow_cross_profile_contacts": False,
            "allow_cross_profile_calendar": True
        }
        
        with patch('backend.api.enrollment.create_work_profile') as mock_create_profile, \
             patch('backend.api.enrollment.configure_work_profile') as mock_configure:
            
            mock_create_profile.return_value = {
                "profile_created": True,
                "profile_id": "work_profile_001",
                "managed_apps_installed": True
            }
            mock_configure.return_value = True
            
            response = await async_client.post(
                "/api/enrollment/work-profile/create",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["profile_created"] == True
            assert "profile_id" in data

    async def test_unenrollment_flow_with_cleanup(self, async_client: AsyncClient,
                                                authenticated_headers):
        """Test device unenrollment with proper cleanup."""
        device_id = "device_to_unenroll"
        unenroll_data = {
            "device_id": device_id,
            "unenroll_reason": "device_replacement",
            "wipe_device_data": True,
            "remove_work_profile": True
        }
        
        with patch('backend.api.enrollment.validate_device_ownership') as mock_validate, \
             patch('backend.api.enrollment.perform_device_wipe') as mock_wipe, \
             patch('backend.api.enrollment.remove_device_profiles') as mock_remove_profiles, \
             patch('backend.api.enrollment.cleanup_device_data') as mock_cleanup:
            
            mock_validate.return_value = True
            mock_wipe.return_value = {"wipe_initiated": True, "wipe_id": "wipe_001"}
            mock_remove_profiles.return_value = True
            mock_cleanup.return_value = True
            
            response = await async_client.post(
                "/api/enrollment/unenroll",
                json=unenroll_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["unenrollment_initiated"] == True
            assert "cleanup_completed" in data
            
            # Verify cleanup was performed
            mock_wipe.assert_called_once()
            mock_remove_profiles.assert_called_once()
            mock_cleanup.assert_called_once()

    async def test_enrollment_audit_logging(self, async_client: AsyncClient,
                                          authenticated_headers, enrollment_data):
        """Test that enrollment events are properly logged for audit."""
        enrollment_data["enrollment_method"] = "qr_code"
        
        with patch('backend.api.enrollment.log_enrollment_event') as mock_log, \
             patch('backend.api.enrollment.validate_qr_token') as mock_validate, \
             patch('backend.api.enrollment.complete_enrollment') as mock_complete:
            
            mock_validate.return_value = True
            mock_complete.return_value = {"device_id": "audit_device_001", "status": "completed"}
            
            response = await async_client.post(
                "/api/enrollment/qr-code/enroll",
                json=enrollment_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == 200
            
            # Verify audit events were logged
            assert mock_log.call_count >= 2  # Start and completion events
            
            # Check audit log entries
            log_calls = mock_log.call_args_list
            start_event = log_calls[0][0][0]  # First call, first argument
            assert start_event["event_type"] == "enrollment_started"
            assert start_event["enrollment_method"] == "qr_code"
            
            completion_event = log_calls[-1][0][0]  # Last call, first argument
            assert completion_event["event_type"] == "enrollment_completed"
            assert completion_event["device_id"] == "audit_device_001"
