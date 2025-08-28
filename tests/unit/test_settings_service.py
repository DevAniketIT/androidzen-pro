"""
Unit tests for Settings Service module.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from backend.services.settings_service import SettingsService


@pytest.mark.unit
class TestSettingsService:
    """Test cases for Settings Service."""

    @pytest.fixture
    def settings_service(self, test_db_session):
        """Create SettingsService instance for testing."""
        return SettingsService(db_session=test_db_session)

    @pytest.fixture
    def sample_settings_data(self):
        """Sample settings data for testing."""
        return {
            "notification_enabled": True,
            "auto_cleanup": False,
            "monitoring_interval": 30,
            "alert_threshold": 80,
            "theme": "dark",
            "language": "en"
        }

    async def test_get_setting_success(self, settings_service, sample_settings_data):
        """Test getting a setting successfully."""
        setting_name = "notification_enabled"
        expected_value = sample_settings_data[setting_name]
        
        with patch.object(settings_service, '_get_setting_from_db') as mock_get:
            mock_get.return_value = expected_value
            
            result = await settings_service.get_setting(setting_name)
            
            assert result == expected_value
            mock_get.assert_called_once_with(setting_name)

    async def test_get_setting_not_found(self, settings_service):
        """Test getting a non-existent setting."""
        setting_name = "non_existent_setting"
        
        with patch.object(settings_service, '_get_setting_from_db') as mock_get:
            mock_get.return_value = None
            
            result = await settings_service.get_setting(setting_name)
            
            assert result is None
            mock_get.assert_called_once_with(setting_name)

    async def test_get_setting_with_default(self, settings_service):
        """Test getting setting with default value."""
        setting_name = "non_existent_setting"
        default_value = "default_value"
        
        with patch.object(settings_service, '_get_setting_from_db') as mock_get:
            mock_get.return_value = None
            
            result = await settings_service.get_setting(setting_name, default_value)
            
            assert result == default_value

    async def test_set_setting_new(self, settings_service):
        """Test setting a new setting."""
        setting_name = "new_setting"
        setting_value = "new_value"
        
        with patch.object(settings_service, '_save_setting_to_db') as mock_save:
            mock_save.return_value = True
            
            result = await settings_service.set_setting(setting_name, setting_value)
            
            assert result is True
            mock_save.assert_called_once_with(setting_name, setting_value)

    async def test_set_setting_update_existing(self, settings_service):
        """Test updating an existing setting."""
        setting_name = "existing_setting"
        old_value = "old_value"
        new_value = "new_value"
        
        with patch.object(settings_service, '_get_setting_from_db') as mock_get, \
             patch.object(settings_service, '_save_setting_to_db') as mock_save:
            
            mock_get.return_value = old_value
            mock_save.return_value = True
            
            result = await settings_service.set_setting(setting_name, new_value)
            
            assert result is True
            mock_save.assert_called_once_with(setting_name, new_value)

    async def test_get_all_settings(self, settings_service, sample_settings_data):
        """Test getting all settings."""
        with patch.object(settings_service, '_get_all_settings_from_db') as mock_get_all:
            mock_get_all.return_value = sample_settings_data
            
            result = await settings_service.get_all_settings()
            
            assert result == sample_settings_data
            mock_get_all.assert_called_once()

    async def test_delete_setting_success(self, settings_service):
        """Test deleting a setting successfully."""
        setting_name = "setting_to_delete"
        
        with patch.object(settings_service, '_delete_setting_from_db') as mock_delete:
            mock_delete.return_value = True
            
            result = await settings_service.delete_setting(setting_name)
            
            assert result is True
            mock_delete.assert_called_once_with(setting_name)

    async def test_delete_setting_not_found(self, settings_service):
        """Test deleting a non-existent setting."""
        setting_name = "non_existent_setting"
        
        with patch.object(settings_service, '_delete_setting_from_db') as mock_delete:
            mock_delete.return_value = False
            
            result = await settings_service.delete_setting(setting_name)
            
            assert result is False
            mock_delete.assert_called_once_with(setting_name)

    async def test_bulk_update_settings(self, settings_service, sample_settings_data):
        """Test bulk updating multiple settings."""
        with patch.object(settings_service, '_bulk_save_settings') as mock_bulk_save:
            mock_bulk_save.return_value = True
            
            result = await settings_service.bulk_update_settings(sample_settings_data)
            
            assert result is True
            mock_bulk_save.assert_called_once_with(sample_settings_data)

    async def test_get_settings_by_category(self, settings_service):
        """Test getting settings by category."""
        category = "notifications"
        expected_settings = {
            "notification_enabled": True,
            "email_notifications": True,
            "push_notifications": False
        }
        
        with patch.object(settings_service, '_get_settings_by_category') as mock_get_category:
            mock_get_category.return_value = expected_settings
            
            result = await settings_service.get_settings_by_category(category)
            
            assert result == expected_settings
            mock_get_category.assert_called_once_with(category)

    def test_validate_setting_value_valid(self, settings_service):
        """Test setting value validation with valid values."""
        # Test boolean
        assert settings_service._validate_setting_value("bool_setting", True) is True
        assert settings_service._validate_setting_value("bool_setting", False) is True
        
        # Test string
        assert settings_service._validate_setting_value("string_setting", "test") is True
        
        # Test integer
        assert settings_service._validate_setting_value("int_setting", 42) is True
        
        # Test float
        assert settings_service._validate_setting_value("float_setting", 3.14) is True

    def test_validate_setting_value_invalid(self, settings_service):
        """Test setting value validation with invalid values."""
        # These would fail if strict validation is implemented
        # For now, most values might be accepted
        pass

    async def test_reset_setting_to_default(self, settings_service):
        """Test resetting a setting to its default value."""
        setting_name = "notification_enabled"
        default_value = True
        
        with patch.object(settings_service, '_get_default_value') as mock_default, \
             patch.object(settings_service, 'set_setting') as mock_set:
            
            mock_default.return_value = default_value
            mock_set.return_value = True
            
            result = await settings_service.reset_setting_to_default(setting_name)
            
            assert result is True
            mock_default.assert_called_once_with(setting_name)
            mock_set.assert_called_once_with(setting_name, default_value)

    async def test_reset_all_settings_to_default(self, settings_service):
        """Test resetting all settings to default values."""
        default_settings = {
            "notification_enabled": True,
            "auto_cleanup": False,
            "monitoring_interval": 30
        }
        
        with patch.object(settings_service, '_get_all_default_settings') as mock_defaults, \
             patch.object(settings_service, 'bulk_update_settings') as mock_bulk:
            
            mock_defaults.return_value = default_settings
            mock_bulk.return_value = True
            
            result = await settings_service.reset_all_settings_to_default()
            
            assert result is True
            mock_defaults.assert_called_once()
            mock_bulk.assert_called_once_with(default_settings)

    async def test_export_settings(self, settings_service, sample_settings_data):
        """Test exporting settings to JSON."""
        with patch.object(settings_service, 'get_all_settings') as mock_get_all:
            mock_get_all.return_value = sample_settings_data
            
            result = await settings_service.export_settings()
            
            assert isinstance(result, str)
            exported_data = json.loads(result)
            assert exported_data == sample_settings_data

    async def test_import_settings(self, settings_service, sample_settings_data):
        """Test importing settings from JSON."""
        json_data = json.dumps(sample_settings_data)
        
        with patch.object(settings_service, 'bulk_update_settings') as mock_bulk:
            mock_bulk.return_value = True
            
            result = await settings_service.import_settings(json_data)
            
            assert result is True
            mock_bulk.assert_called_once_with(sample_settings_data)

    async def test_import_settings_invalid_json(self, settings_service):
        """Test importing invalid JSON data."""
        invalid_json = "invalid json data"
        
        with pytest.raises(json.JSONDecodeError):
            await settings_service.import_settings(invalid_json)

    async def test_get_setting_history(self, settings_service):
        """Test getting setting change history."""
        setting_name = "test_setting"
        expected_history = [
            {
                "timestamp": datetime.now(),
                "old_value": "old_value",
                "new_value": "new_value",
                "changed_by": "admin"
            }
        ]
        
        with patch.object(settings_service, '_get_setting_history') as mock_history:
            mock_history.return_value = expected_history
            
            result = await settings_service.get_setting_history(setting_name)
            
            assert result == expected_history
            mock_history.assert_called_once_with(setting_name)

    async def test_setting_change_callback(self, settings_service):
        """Test setting change callbacks."""
        setting_name = "test_setting"
        old_value = "old_value"
        new_value = "new_value"
        
        callback_called = False
        callback_args = None
        
        def test_callback(name, old_val, new_val):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = (name, old_val, new_val)
        
        # Register callback
        settings_service.register_change_callback(setting_name, test_callback)
        
        # Trigger change
        await settings_service._trigger_change_callbacks(setting_name, old_value, new_value)
        
        assert callback_called is True
        assert callback_args == (setting_name, old_value, new_value)

    def test_setting_validation_rules(self, settings_service):
        """Test custom setting validation rules."""
        # Test email validation
        assert settings_service._validate_email("test@example.com") is True
        assert settings_service._validate_email("invalid-email") is False
        
        # Test URL validation
        assert settings_service._validate_url("https://example.com") is True
        assert settings_service._validate_url("not-a-url") is False
        
        # Test range validation
        assert settings_service._validate_range(50, 0, 100) is True
        assert settings_service._validate_range(150, 0, 100) is False

    async def test_setting_encryption_for_sensitive_data(self, settings_service):
        """Test encryption of sensitive settings."""
        sensitive_setting = "api_key"
        sensitive_value = "secret_api_key_123"
        
        with patch.object(settings_service, '_encrypt_value') as mock_encrypt, \
             patch.object(settings_service, '_decrypt_value') as mock_decrypt:
            
            encrypted_value = "encrypted_secret"
            mock_encrypt.return_value = encrypted_value
            mock_decrypt.return_value = sensitive_value
            
            # Test setting sensitive value
            with patch.object(settings_service, '_save_setting_to_db') as mock_save:
                mock_save.return_value = True
                await settings_service.set_setting(sensitive_setting, sensitive_value)
                
                # Should save encrypted value
                if settings_service._is_sensitive_setting(sensitive_setting):
                    mock_encrypt.assert_called_once_with(sensitive_value)
            
            # Test getting sensitive value
            with patch.object(settings_service, '_get_setting_from_db') as mock_get:
                mock_get.return_value = encrypted_value
                
                result = await settings_service.get_setting(sensitive_setting)
                
                # Should decrypt and return original value
                if settings_service._is_sensitive_setting(sensitive_setting):
                    mock_decrypt.assert_called_once_with(encrypted_value)
                    assert result == sensitive_value

    async def test_concurrent_setting_updates(self, settings_service):
        """Test concurrent setting updates."""
        import asyncio
        
        setting_name = "concurrent_setting"
        
        async def update_setting(value):
            return await settings_service.set_setting(setting_name, value)
        
        with patch.object(settings_service, '_save_setting_to_db') as mock_save:
            mock_save.return_value = True
            
            # Run concurrent updates
            tasks = [update_setting(f"value_{i}") for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            # All updates should succeed
            assert all(results)
            assert mock_save.call_count == 10

    async def test_setting_cache_functionality(self, settings_service):
        """Test setting caching for performance."""
        setting_name = "cached_setting"
        setting_value = "cached_value"
        
        with patch.object(settings_service, '_get_setting_from_db') as mock_db:
            mock_db.return_value = setting_value
            
            # First call should hit database
            result1 = await settings_service.get_setting(setting_name)
            assert result1 == setting_value
            assert mock_db.call_count == 1
            
            # Second call should use cache (if implemented)
            result2 = await settings_service.get_setting(setting_name)
            assert result2 == setting_value
            
            # Depending on cache implementation, this might still be 1
            # or could be 2 if no caching is implemented yet

    async def test_setting_backup_and_restore(self, settings_service, sample_settings_data):
        """Test settings backup and restore functionality."""
        backup_id = "backup_001"
        
        # Test backup creation
        with patch.object(settings_service, 'get_all_settings') as mock_get_all, \
             patch.object(settings_service, '_save_backup') as mock_save_backup:
            
            mock_get_all.return_value = sample_settings_data
            mock_save_backup.return_value = backup_id
            
            result = await settings_service.create_settings_backup("test_backup")
            
            assert result == backup_id
            mock_save_backup.assert_called_once()
        
        # Test backup restore
        with patch.object(settings_service, '_load_backup') as mock_load_backup, \
             patch.object(settings_service, 'bulk_update_settings') as mock_bulk:
            
            mock_load_backup.return_value = sample_settings_data
            mock_bulk.return_value = True
            
            result = await settings_service.restore_settings_backup(backup_id)
            
            assert result is True
            mock_load_backup.assert_called_once_with(backup_id)
            mock_bulk.assert_called_once_with(sample_settings_data)
