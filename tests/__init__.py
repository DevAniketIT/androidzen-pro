"""
AndroidZen Pro Test Suite

This package contains all tests for the AndroidZen Pro application,
organized by test type:

- unit/: Unit tests for individual components
- integration/: Integration tests for component interactions
- e2e/: End-to-end tests for full application workflows
- performance/: Performance and load tests

Run tests using pytest from the project root:
    pytest tests/                    # Run all tests
    pytest tests/unit/               # Run only unit tests
    pytest tests/integration/        # Run only integration tests
    pytest tests/e2e/                # Run only e2e tests
    pytest tests/performance/        # Run only performance tests
    
    pytest -m unit                   # Run tests marked as unit
    pytest -m "not slow"             # Skip slow tests
    pytest -m "integration and not requires_adb"  # Integration tests without ADB
"""
