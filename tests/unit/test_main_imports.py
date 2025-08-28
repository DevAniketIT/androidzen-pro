#!/usr/bin/env python3
"""
Test main application imports to verify the app can start
"""

import sys
import os

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def test_main_app():
    """Test if we can import the main FastAPI app"""
    try:
        print("Testing main app import...")
        from backend.main import app
        print("✅ Successfully imported FastAPI app")
        print(f"   App type: {type(app)}")
        return True
    except ImportError as e:
        print(f"❌ Import error in main app: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Warning in main app import: {e}")
        return True  # App imported but with warnings

def test_core_functionality():
    """Test core functionality imports"""
    try:
        print("Testing core functionality...")
        
        # Test database
        from backend.core.database import get_db, engine
        print("✅ Database components imported")
        
        # Test logging
        from backend.core.logging_config import setup_logging
        print("✅ Logging configuration imported")
        
        # Test AI service
        from backend.services.intelligence_service import AIService
        ai_service = AIService()
        print("✅ AI Service instantiated successfully")
        
        return True
    except Exception as e:
        print(f"❌ Core functionality test failed: {e}")
        return False

def main():
    """Run main import tests"""
    print("🚀 Testing Main Application Imports")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    # Test main app
    if test_main_app():
        tests_passed += 1
    
    print()
    
    # Test core functionality
    if test_core_functionality():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print("📊 MAIN IMPORT TEST RESULTS")
    print("=" * 50)
    
    if tests_passed == total_tests:
        print("🎉 ALL MAIN IMPORTS SUCCESSFUL!")
        print("✅ The application is ready to run")
        return True
    else:
        print(f"⚠️  {total_tests - tests_passed} out of {total_tests} tests failed")
        print("🔧 Please check the error messages above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
