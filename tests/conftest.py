"""
AndroidZen Pro Test Configuration

This file contains shared fixtures and configuration for all test types:
- Unit tests
- Integration tests  
- End-to-end tests
- Performance tests
"""

import asyncio
import os
import sys
import pytest
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import application and core modules (with error handling)
try:
    from backend.main import app
    from backend.core.database import Base, get_db
    from backend.core.auth import AuthManager
    from backend.core.websocket_manager import WebSocketManager
    from backend.services.intelligence_service import AIService
    from tests.mocks.mock_adb_device import MockADBDevice, MockADBManager
except ImportError as e:
    # Handle import errors gracefully during test discovery
    print(f"Warning: Could not import some backend modules: {e}")
    app = None
    Base = None
    get_db = None
    AuthManager = None
    WebSocketManager = None
    AIService = None
    MockADBDevice = None
    MockADBManager = None


# Test database setup
@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    if Base is not None:
        Base.metadata.create_all(bind=engine)
    yield engine
    if Base is not None:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def override_get_db(test_db_session):
    """Override database dependency."""
    def _override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    return _override_get_db


# FastAPI test client
@pytest.fixture
def client(override_get_db):
    """FastAPI test client."""
    if app is None or get_db is None:
        pytest.skip("FastAPI app not available")
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db):
    """Async FastAPI test client."""
    if app is None or get_db is None:
        pytest.skip("FastAPI app not available")
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# Authentication fixtures
@pytest.fixture
def mock_auth_manager():
    """Mock authentication manager."""
    if AuthManager is None:
        mock_auth = Mock()
    else:
        mock_auth = Mock(spec=AuthManager)
    mock_auth.create_access_token.return_value = "test_token"
    mock_auth.verify_token.return_value = {"user_id": "test_user", "username": "testuser"}
    mock_auth.hash_password.return_value = "hashed_password"
    mock_auth.verify_password.return_value = True
    return mock_auth


@pytest.fixture
def authenticated_headers():
    """Headers with valid authentication token."""
    return {"Authorization": "Bearer test_token"}


# Mock ADB fixtures
@pytest.fixture
def mock_adb_device():
    """Mock ADB device for testing."""
    if MockADBDevice is None:
        return {
            "device_id": "test_device_001",
            "model": "TestPhone Pro",
            "android_version": "13",
            "is_connected": True
        }
    return MockADBDevice(
        device_id="test_device_001",
        model="TestPhone Pro",
        android_version="13",
        is_connected=True
    )


@pytest.fixture
def mock_adb_manager(mock_adb_device):
    """Mock ADB manager with test devices."""
    if MockADBManager is None:
        return Mock()
    manager = MockADBManager()
    if hasattr(manager, 'add_device'):
        manager.add_device(mock_adb_device)
    return manager


@pytest.fixture
def mock_multiple_adb_devices():
    """Multiple mock ADB devices for testing."""
    if MockADBDevice is None:
        return [
            {"device_id": "device_001", "model": "Samsung Galaxy S21", "android_version": "13", "is_connected": True},
            {"device_id": "device_002", "model": "Google Pixel 7", "android_version": "14", "is_connected": True},
            {"device_id": "device_003", "model": "OnePlus 10", "android_version": "12", "is_connected": False},
        ]
    devices = [
        MockADBDevice("device_001", "Samsung Galaxy S21", "13", True),
        MockADBDevice("device_002", "Google Pixel 7", "14", True),
        MockADBDevice("device_003", "OnePlus 10", "12", False),
    ]
    return devices


# WebSocket fixtures
@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager."""
    if WebSocketManager is None:
        mock_ws = Mock()
    else:
        mock_ws = Mock(spec=WebSocketManager)
    mock_ws.connect = MagicMock()
    mock_ws.disconnect = MagicMock()
    mock_ws.broadcast_message = MagicMock()
    mock_ws.broadcast_device_status = MagicMock()
    return mock_ws


# AI Service fixtures
@pytest.fixture
def mock_ai_service():
    """Mock AI service."""
    if AIService is None:
        mock_ai = Mock()
    else:
        mock_ai = Mock(spec=AIService)
    mock_ai.initialize_models = MagicMock()
    mock_ai.detect_anomalies = MagicMock()
    mock_ai.predict_maintenance = MagicMock()
    mock_ai.analyze_user_behavior = MagicMock()
    mock_ai.generate_recommendations = MagicMock()
    return mock_ai


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration settings."""
    return {
        "test_database_url": "sqlite:///test_androidzen.db",
        "test_server_url": "http://localhost:8000",
        "test_timeout": 30,
        "mock_adb_devices": True,
        "enable_logging": True
    }


@pytest.fixture
def mock_device_data():
    """Provide mock device data for tests."""
    return {
        "device_id": "test_device_001",
        "serial_number": "TEST123456789",
        "device_name": "Test Android Device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "android_version": "11.0",
        "is_connected": True,
        "is_active": True,
        "battery_level": 85,
        "cpu_usage": 35.5,
        "memory_usage": 60.2,
        "storage_usage": 45.8
    }


# Sample data fixtures
@pytest.fixture
def sample_device_data():
    """Sample device analytics data."""
    return {
        "device_id": "test_device_001",
        "cpu_usage": 45.6,
        "memory_usage": 67.8,
        "storage_usage_percentage": 78.9,
        "battery_level": 85,
        "battery_temperature": 32.5,
        "cpu_temperature": 42.3,
        "running_processes": 125,
        "network_strength": -65
    }


@pytest.fixture
def sample_security_event():
    """Sample security event data."""
    return {
        "device_id": "test_device_001",
        "event_type": "malware_detected",
        "severity": "high",
        "description": "Suspicious app detected",
        "source_app": "com.suspicious.app",
        "mitigation_action": "app_quarantined"
    }


# Temporary file fixtures
@pytest.fixture
def temp_file():
    """Temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_dir():
    """Temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# Environment fixtures
@pytest.fixture
def test_env_vars():
    """Set test environment variables."""
    test_vars = {
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "sqlite:///./test.db",
        "SECRET_KEY": "test_secret_key",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    }
    
    # Store original values
    original_vars = {}
    for key, value in test_vars.items():
        original_vars[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_vars
    
    # Restore original values
    for key, value in original_vars.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Set testing environment variable
    os.environ["TESTING"] = "true"
    
    yield
    
    # Clean up after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


# Performance testing fixtures
@pytest.fixture
def benchmark_config():
    """Configuration for performance benchmarks."""
    return {
        "rounds": 10,
        "warmup_rounds": 2,
        "timeout": 60,
        "max_time": 1.0,  # Maximum acceptable time in seconds
        "min_rounds": 5
    }


# Security testing fixtures
@pytest.fixture
def security_test_config():
    """Configuration for security tests."""
    return {
        "max_password_attempts": 3,
        "token_expiry": 1800,  # 30 minutes
        "rate_limit_requests": 100,
        "rate_limit_window": 3600,  # 1 hour
        "allowed_origins": ["http://localhost:3000", "http://127.0.0.1:3000"]
    }


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_adb: marks tests that require ADB connection"
    )
    config.addinivalue_line(
        "markers", "requires_db: marks tests that require database"
    )
    config.addinivalue_line(
        "markers", "mock_adb: marks tests using mock ADB devices"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        test_file_path = str(item.fspath)
        
        # Add markers based on directory structure
        if "/unit/" in test_file_path or "\\unit\\" in test_file_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_file_path or "\\integration\\" in test_file_path:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in test_file_path or "\\e2e\\" in test_file_path:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
        elif "/performance/" in test_file_path or "\\performance\\" in test_file_path:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
