# AndroidZen Pro Test Suite

This directory contains all tests for the AndroidZen Pro application, organized by test type for better maintainability and execution control.

## Directory Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py             # Shared test configuration and fixtures
├── pytest.ini             # Pytest configuration
├── README.md              # This file
├── unit/                  # Unit tests
│   ├── __init__.py
│   ├── focused_import_test.py
│   ├── test_imports.py
│   ├── test_main_imports.py
│   ├── test_stub_modules.py
│   ├── test_adb_manager.py
│   ├── test_ai_service.py
│   ├── test_auth.py
│   └── test_settings_service.py
├── integration/           # Integration tests
│   ├── __init__.py
│   ├── test_alembic.py
│   ├── test_api_endpoints.py
│   └── test_devices_api.py
├── e2e/                   # End-to-end tests
│   ├── __init__.py
│   ├── test_server.py
│   ├── test_websocket.py
│   ├── test_device_enrollment_flows.py
│   └── test_policy_enforcement.py
├── performance/           # Performance tests
│   ├── __init__.py
│   └── test_performance_benchmarks.py
├── security/              # Security tests
│   ├── __init__.py
│   └── test_security.py
├── mocks/                 # Mock objects and utilities
│   ├── __init__.py
│   └── mock_adb_device.py
└── pipeline/              # CI/CD pipeline tests
    ├── __init__.py
    └── test_runner.py
```

## Test Types

### Unit Tests (`unit/`)
Tests individual components in isolation:
- **focused_import_test.py**: Tests for focused import functionality
- **test_imports.py**: Comprehensive import testing
- **test_main_imports.py**: Main application import tests
- **test_stub_modules.py**: Tests for stub service modules

### Integration Tests (`integration/`)
Tests component interactions and API integrations:
- **test_alembic.py**: Database migration testing
- **test_api_endpoints.py**: API endpoint integration tests

### End-to-End Tests (`e2e/`)
Tests complete application workflows:
- **test_server.py**: Full server functionality testing
- **test_websocket.py**: WebSocket functionality testing

### Performance Tests (`performance/`)
Tests for performance benchmarks and load testing (to be added).

## Running Tests

### Prerequisites
Ensure you have pytest and required dependencies installed:
```bash
pip install pytest pytest-cov pytest-asyncio pytest-html pytest-json-report pytest-timeout
```

### Basic Test Execution

From the project root directory:

```bash
# Run all tests
pytest tests/

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest tests/performance/

# Run tests by markers
pytest -m unit                    # Only unit tests
pytest -m integration             # Only integration tests
pytest -m e2e                     # Only end-to-end tests
pytest -m performance             # Only performance tests
pytest -m "not slow"              # Skip slow-running tests
pytest -m "integration and not requires_adb"  # Integration tests without ADB
```

### Test Configuration

Tests can be configured using markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_adb` - Tests requiring ADB connection
- `@pytest.mark.requires_db` - Tests requiring database
- `@pytest.mark.mock_adb` - Tests using mock ADB devices

### Coverage Reports

Tests generate coverage reports:
```bash
# HTML coverage report (opens in browser)
pytest tests/ --cov=backend --cov-report=html

# Terminal coverage report
pytest tests/ --cov=backend --cov-report=term-missing

# XML coverage report (for CI/CD)
pytest tests/ --cov=backend --cov-report=xml
```

### Test Reports

HTML and JSON reports are generated:
- HTML Report: `../reports/report.html`
- JSON Report: `../reports/report.json`
- Coverage HTML: `../htmlcov/index.html`

## Writing Tests

### Test Structure
Follow the naming convention:
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Using Fixtures
Common fixtures are available in `conftest.py`:
- `test_config`: Test configuration settings
- `mock_device_data`: Mock device data for tests
- `setup_test_environment`: Test environment setup

### Example Test
```python
import pytest

@pytest.mark.unit
def test_example_function(mock_device_data):
    """Test example function with mock data."""
    # Test implementation
    assert mock_device_data["device_id"] == "test_device_001"

@pytest.mark.integration
@pytest.mark.requires_db
async def test_database_integration():
    """Test database integration."""
    # Test implementation
    pass
```

## Continuous Integration

Tests are configured to run in CI/CD pipelines with:
- Automatic test discovery
- Coverage reporting
- HTML and JSON reports
- Timeout protection (300 seconds default)
- Parallel execution support

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure backend path is correctly added to PYTHONPATH
2. **Database Tests**: Make sure test database is configured
3. **ADB Tests**: Use `mock_adb` marker for tests without physical devices
4. **Async Tests**: Use `pytest-asyncio` for async test functions

### Debug Mode
Run tests with verbose output:
```bash
pytest tests/ -v --tb=long
```

For debugging specific tests:
```bash
pytest tests/unit/test_specific.py::test_function -v -s
```
