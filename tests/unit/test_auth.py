"""
Unit tests for Authentication module.
"""

import pytest
import jwt
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from backend.core.auth import AuthManager


@pytest.mark.unit
class TestAuth:
    """Test cases for Authentication module."""

    @pytest.fixture
    def auth_manager(self):
        """Create AuthManager instance for testing."""
        return AuthManager()

    def test_auth_manager_initialization(self, auth_manager):
        """Test AuthManager initialization."""
        assert auth_manager.algorithm == "HS256"
        assert auth_manager.expire_minutes == 60 * 24  # 24 hours default
        assert auth_manager.secret_key is not None

    def test_hash_password(self, auth_manager):
        """Test password hashing."""
        password = "test_password123"
        hashed = auth_manager.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 10
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self, auth_manager):
        """Test password verification with correct password."""
        password = "test_password123"
        hashed = auth_manager.hash_password(password)
        
        assert auth_manager.verify_password(password, hashed) == True

    def test_verify_password_incorrect(self, auth_manager):
        """Test password verification with incorrect password."""
        password = "test_password123"
        wrong_password = "wrong_password"
        hashed = auth_manager.hash_password(password)
        
        assert auth_manager.verify_password(wrong_password, hashed) == False

    def test_create_access_token(self, auth_manager):
        """Test access token creation."""
        user_data = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "admin"
        }
        
        token = auth_manager.create_access_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        assert token.count('.') == 2  # JWT has 3 parts separated by dots

    def test_verify_token_valid(self, auth_manager):
        """Test token verification with valid token."""
        user_data = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "admin"
        }
        
        token = auth_manager.create_access_token(user_data)
        decoded_data = auth_manager.verify_token(token)
        
        assert decoded_data["user_id"] == user_data["user_id"]
        assert decoded_data["username"] == user_data["username"]
        assert decoded_data["role"] == user_data["role"]
        assert "exp" in decoded_data
        assert "iat" in decoded_data

    def test_verify_token_invalid(self, auth_manager):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(jwt.InvalidTokenError):
            auth_manager.verify_token(invalid_token)

    def test_verify_token_expired(self, auth_manager):
        """Test token verification with expired token."""
        user_data = {"user_id": "test_user", "username": "testuser"}
        
        # Create token with very short expiration
        with patch('backend.core.auth.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow()
            mock_datetime.timedelta.return_value = timedelta(seconds=-1)  # Already expired
            
            expired_token = auth_manager.create_access_token(user_data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(jwt.ExpiredSignatureError):
            auth_manager.verify_token(expired_token)

    def test_verify_token_tampered(self, auth_manager):
        """Test token verification with tampered token."""
        user_data = {"user_id": "test_user", "username": "testuser"}
        token = auth_manager.create_access_token(user_data)
        
        # Tamper with the token
        tampered_token = token[:-5] + "XXXXX"  # Change last 5 characters
        
        with pytest.raises(jwt.InvalidSignatureError):
            auth_manager.verify_token(tampered_token)

    def test_create_token_custom_expiration(self, auth_manager):
        """Test token creation with custom expiration."""
        user_data = {"user_id": "test_user", "username": "testuser"}
        custom_expiration = timedelta(hours=2)
        
        token = auth_manager.create_access_token(user_data, expires_delta=custom_expiration)
        decoded_data = auth_manager.verify_token(token)
        
        # Check that expiration is approximately 2 hours from now
        exp_time = datetime.fromtimestamp(decoded_data["exp"])
        expected_exp = datetime.utcnow() + custom_expiration
        time_diff = abs((exp_time - expected_exp).total_seconds())
        
        assert time_diff < 60  # Within 1 minute tolerance

    def test_token_contains_required_claims(self, auth_manager):
        """Test that token contains required claims."""
        user_data = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "admin",
            "email": "test@example.com"
        }
        
        token = auth_manager.create_access_token(user_data)
        decoded_data = auth_manager.verify_token(token)
        
        # Check all user data is preserved
        for key, value in user_data.items():
            assert decoded_data[key] == value
        
        # Check standard JWT claims
        assert "exp" in decoded_data  # Expiration time
        assert "iat" in decoded_data  # Issued at time

    def test_password_hash_uniqueness(self, auth_manager):
        """Test that password hashing produces unique hashes."""
        password = "test_password"
        
        hash1 = auth_manager.hash_password(password)
        hash2 = auth_manager.hash_password(password)
        
        # Same password should produce different hashes due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert auth_manager.verify_password(password, hash1)
        assert auth_manager.verify_password(password, hash2)

    def test_empty_password_handling(self, auth_manager):
        """Test handling of empty password."""
        empty_password = ""
        
        hashed = auth_manager.hash_password(empty_password)
        assert auth_manager.verify_password(empty_password, hashed)

    def test_unicode_password_handling(self, auth_manager):
        """Test handling of unicode passwords."""
        unicode_password = "пароль123!@#"
        
        hashed = auth_manager.hash_password(unicode_password)
        assert auth_manager.verify_password(unicode_password, hashed)

    def test_long_password_handling(self, auth_manager):
        """Test handling of very long passwords."""
        long_password = "a" * 1000  # Very long password
        
        hashed = auth_manager.hash_password(long_password)
        assert auth_manager.verify_password(long_password, hashed)

    def test_token_algorithm_consistency(self, auth_manager):
        """Test that token uses consistent algorithm."""
        user_data = {"user_id": "test_user"}
        token = auth_manager.create_access_token(user_data)
        
        # Decode header to check algorithm
        header = jwt.get_unverified_header(token)
        assert header["alg"] == auth_manager.algorithm

    def test_concurrent_token_operations(self, auth_manager):
        """Test concurrent token creation and verification."""
        import threading
        import queue
        
        results = queue.Queue()
        user_data = {"user_id": "test_user", "username": "testuser"}
        
        def create_and_verify():
            try:
                token = auth_manager.create_access_token(user_data)
                decoded = auth_manager.verify_token(token)
                results.put(("success", decoded["user_id"]))
            except Exception as e:
                results.put(("error", str(e)))
        
        # Create multiple threads
        threads = [threading.Thread(target=create_and_verify) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            status, value = results.get()
            if status == "success":
                assert value == user_data["user_id"]
                success_count += 1
        
        assert success_count == 10

    @patch.dict('os.environ', {'SECRET_KEY': 'test_secret_key_123'})
    def test_secret_key_from_environment(self):
        """Test that secret key is loaded from environment."""
        auth_manager = AuthManager()
        assert auth_manager.secret_key == 'test_secret_key_123'

    def test_token_blacklist_functionality(self, auth_manager):
        """Test token blacklisting (if implemented)."""
        # This would test token invalidation/blacklisting
        # Currently not implemented in basic version
        pass

    def test_refresh_token_functionality(self, auth_manager):
        """Test refresh token functionality (if implemented)."""
        # This would test refresh token generation and validation
        # Currently not implemented in basic version
        pass
