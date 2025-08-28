#!/usr/bin/env python3
"""
Test script to verify the functionality of stub service and middleware modules.

This script tests:
- AIService class and initialize_models method
- Middleware classes (LoggingMiddleware, PerformanceMiddleware, etc.)
- Device model class for database queries

Usage: python tests/unit/test_stub_modules.py
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ai_service():
    """Test AIService stub functionality."""
    try:
        logger.info("Testing AIService...")
        
        from services.ai_service import AIService
        
        # Initialize service
        ai_service = AIService()
        
        # Test initialization
        init_result = await ai_service.initialize_models()
        
        # Verify results
        assert isinstance(init_result, bool), "initialize_models should return boolean"
        logger.info(f"AI Service initialization result: {init_result}")
        
        # Test status check
        is_initialized = ai_service.is_initialized()
        logger.info(f"AI Service initialized status: {is_initialized}")
        
        # Test model info
        model_info = ai_service.get_model_info()
        logger.info(f"Model info: {model_info}")
        
        logger.info("✓ AIService tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ AIService test failed: {e}")
        return False


def test_middleware():
    """Test middleware stub functionality."""
    try:
        logger.info("Testing Middleware classes...")
        
        from middleware_standalone import (
            LoggingMiddleware, 
            PerformanceMiddleware, 
            ErrorTrackingMiddleware,
            SecurityMiddleware,
            CORSMiddleware,
            get_all_middleware
        )
        
        # Test that classes can be imported and instantiated
        class MockApp:
            pass
        
        mock_app = MockApp()
        
        # Test each middleware class
        middleware_classes = [
            LoggingMiddleware,
            PerformanceMiddleware,
            ErrorTrackingMiddleware,
            SecurityMiddleware,
            CORSMiddleware
        ]
        
        for middleware_class in middleware_classes:
            middleware = middleware_class(mock_app)
            logger.info(f"✓ {middleware_class.__name__} instantiated successfully")
        
        # Test utility function
        all_middleware = get_all_middleware()
        assert len(all_middleware) == 5, "Should return 5 middleware classes"
        logger.info(f"✓ get_all_middleware() returned {len(all_middleware)} classes")
        
        logger.info("✓ Middleware tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Middleware test failed: {e}")
        return False


def test_device_model():
    """Test Device model stub functionality."""
    try:
        logger.info("Testing Device model...")
        
        from models.device import Device
        
        # Test that class can be imported and basic attributes exist
        device_attrs = [
            'id', 'device_id', 'serial_number', 'device_name',
            'manufacturer', 'model', 'is_connected', 'is_active'
        ]
        
        for attr in device_attrs:
            assert hasattr(Device, attr), f"Device should have {attr} attribute"
        
        # Test class methods exist
        class_methods = [
            'get_by_device_id',
            'get_all_active', 
            'get_connected_devices',
            'create_device'
        ]
        
        for method in class_methods:
            assert hasattr(Device, method), f"Device should have {method} method"
            assert callable(getattr(Device, method)), f"{method} should be callable"
        
        # Test instance methods
        instance_methods = ['to_dict', 'update_status']
        for method in instance_methods:
            assert hasattr(Device, method), f"Device should have {method} method"
        
        logger.info("✓ Device model tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Device model test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting stub modules test...")
    
    results = []
    
    # Test AI Service
    results.append(await test_ai_service())
    
    # Test Middleware
    results.append(test_middleware())
    
    # Test Device Model
    results.append(test_device_model())
    
    # Summary
    passed_tests = sum(results)
    total_tests = len(results)
    
    logger.info(f"\nTest Summary:")
    logger.info(f"Passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        logger.info("✓ All stub module tests passed!")
        return True
    else:
        logger.error(f"✗ {total_tests - passed_tests} tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
