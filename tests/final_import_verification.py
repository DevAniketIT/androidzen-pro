#!/usr/bin/env python3
"""
Final import verification for AndroidZen Pro
Tests all critical imports and provides comprehensive dependency report
"""

import sys
import os
import importlib
import traceback
from pathlib import Path

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def test_external_dependencies():
    """Test all external dependencies"""
    print("🔍 Testing External Dependencies")
    print("=" * 50)
    
    dependencies = [
        ('fastapi', 'FastAPI web framework'),
        ('uvicorn', 'ASGI server'),
        ('sqlalchemy', 'SQL ORM'),
        ('pydantic', 'Data validation'),
        ('pandas', 'Data analysis'),
        ('numpy', 'Numerical computing'),
        ('adb_shell', 'ADB shell interface'),
        ('websockets', 'WebSocket communication'),
        ('psutil', 'System monitoring'),
        ('dotenv', 'Environment variables (python-dotenv)'),
        ('passlib', 'Password hashing'),
        ('pytest', 'Testing framework'),
        ('alembic', 'Database migrations'),
        ('schedule', 'Task scheduling'),
    ]
    
    success = 0
    failures = 0
    
    for module_name, description in dependencies:
        try:
            importlib.import_module(module_name)
            print(f"✅ {module_name:<15} - {description}")
            success += 1
        except ImportError:
            print(f"❌ {module_name:<15} - {description} (MISSING)")
            failures += 1
    
    print(f"\nExternal Dependencies: {success} successful, {failures} failed")
    return failures == 0

def test_core_modules():
    """Test core module imports"""
    print("\n🔧 Testing Core Modules")
    print("=" * 50)
    
    core_modules = [
        ('backend.core.logging_config', 'Logging configuration'),
        ('backend.core.database', 'Database setup'),
        ('backend.core.auth', 'Authentication core'),
    ]
    
    success = 0
    failures = 0
    
    for module_name, description in core_modules:
        try:
            importlib.import_module(module_name)
            print(f"✅ {description}")
            success += 1
        except Exception as e:
            print(f"❌ {description} - {str(e)[:80]}...")
            failures += 1
    
    print(f"\nCore Modules: {success} successful, {failures} failed")
    return failures == 0

def test_models():
    """Test model imports individually to avoid conflicts"""
    print("\n📊 Testing Models")
    print("=" * 50)
    
    models = [
        ('backend.models.analytics', 'Analytics', 'Analytics model'),
    ]
    
    success = 0
    failures = 0
    
    for module_name, class_name, description in models:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                print(f"✅ {description} ({class_name})")
                success += 1
            else:
                print(f"⚠️  {description} - class {class_name} not found")
                failures += 1
        except Exception as e:
            print(f"❌ {description} - {str(e)[:80]}...")
            failures += 1
    
    print(f"\nModels: {success} successful, {failures} failed/warnings")
    return failures == 0

def test_services():
    """Test service imports"""
    print("\n🛠️  Testing Services")
    print("=" * 50)
    
    services = [
        ('backend.services.ai_service', 'AIService', 'AI Service'),
        ('backend.services.network_service', 'NetworkService', 'Network Service'),
        ('backend.services.security_service', 'SecurityService', 'Security Service'),
        ('backend.services.settings_service', 'SettingsService', 'Settings Service'),
        ('backend.services.storage_service', 'StorageService', 'Storage Service'),
    ]
    
    success = 0
    failures = 0
    
    for module_name, class_name, description in services:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                print(f"✅ {description} ({class_name})")
                success += 1
            else:
                print(f"⚠️  {description} - class {class_name} not found")
                failures += 1
        except Exception as e:
            print(f"❌ {description} - {str(e)[:80]}...")
            failures += 1
    
    print(f"\nServices: {success} successful, {failures} failed/warnings")
    return failures == 0

def test_api_modules():
    """Test API module imports"""
    print("\n🌐 Testing API Modules")
    print("=" * 50)
    
    api_modules = [
        ('backend.api.auth', 'Authentication API'),
        ('backend.api.devices', 'Devices API'),
        ('backend.api.monitoring', 'Monitoring API'),
        ('backend.api.network', 'Network API'),
        ('backend.api.security', 'Security API'),
        ('backend.api.settings', 'Settings API'),
        ('backend.api.storage', 'Storage API'),
        ('backend.api.websocket', 'WebSocket API'),
    ]
    
    success = 0
    failures = 0
    
    for module_name, description in api_modules:
        try:
            importlib.import_module(module_name)
            print(f"✅ {description}")
            success += 1
        except Exception as e:
            print(f"❌ {description} - {str(e)[:80]}...")
            failures += 1
    
    print(f"\nAPI Modules: {success} successful, {failures} failed")
    return failures == 0

def test_critical_classes():
    """Test specific critical class imports"""
    print("\n🎯 Testing Critical Classes")
    print("=" * 50)
    
    critical_imports = [
        ('backend.core.adb_manager', 'AdbManager', 'ADB Manager (correct name)'),
        ('backend.core.websocket_manager', 'WebSocketManager', 'WebSocket Manager'),
        ('backend.services.ai_service', 'AIService', 'AI Service class'),
        ('backend.models.analytics', 'Analytics', 'Analytics model'),
    ]
    
    success = 0
    failures = 0
    
    for module_name, class_name, description in critical_imports:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                print(f"✅ {description}")
                success += 1
            else:
                available_classes = [name for name in dir(module) if not name.startswith('_') and name[0].isupper()]
                print(f"❌ {description} - Available classes: {available_classes}")
                failures += 1
        except Exception as e:
            print(f"❌ {description} - {str(e)[:80]}...")
            failures += 1
    
    print(f"\nCritical Classes: {success} successful, {failures} failed")
    return failures == 0

def test_utilities():
    """Test utility imports"""
    print("\n🔧 Testing Utilities")
    print("=" * 50)
    
    utilities = [
        ('backend.utils.database_utils', 'Database Utilities'),
        ('backend.middleware.logging_middleware', 'Logging Middleware'),
    ]
    
    success = 0
    failures = 0
    
    for module_name, description in utilities:
        try:
            importlib.import_module(module_name)
            print(f"✅ {description}")
            success += 1
        except Exception as e:
            print(f"❌ {description} - {str(e)[:80]}...")
            failures += 1
    
    print(f"\nUtilities: {success} successful, {failures} failed")
    return failures == 0

def check_package_versions():
    """Check versions of critical packages"""
    print("\n📋 Package Version Report")
    print("=" * 50)
    
    packages_to_check = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic', 
        'pandas', 'numpy', 'adb_shell', 'websockets'
    ]
    
    for package in packages_to_check:
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', 'Unknown')
            print(f"📦 {package:<15} v{version}")
        except ImportError:
            print(f"❌ {package:<15} Not installed")

def main():
    """Run complete import verification"""
    print("AndroidZen Pro - Import Verification Suite")
    print("=" * 60)
    print("🚀 Starting comprehensive import verification...\n")
    
    # Run all tests
    results = []
    results.append(test_external_dependencies())
    results.append(test_core_modules())
    results.append(test_models())
    results.append(test_services())
    results.append(test_api_modules())
    results.append(test_critical_classes())
    results.append(test_utilities())
    
    # Show package versions
    check_package_versions()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 FINAL VERIFICATION RESULTS")
    print("=" * 60)
    
    successful_categories = sum(results)
    total_categories = len(results)
    
    if successful_categories == total_categories:
        print("🎉 ALL IMPORT CATEGORIES PASSED!")
        print("✅ The project is ready for development and deployment.")
        print("✅ No missing dependencies or import issues detected.")
    else:
        failed_categories = total_categories - successful_categories
        print(f"⚠️  {failed_categories} out of {total_categories} categories have issues.")
        print("🔧 Please address the failed imports before proceeding.")
        
        print("\n🛠️  RECOMMENDED ACTIONS:")
        print("   1. Install missing external dependencies")
        print("   2. Check class names and module structure")
        print("   3. Verify database model definitions")
        print("   4. Review circular import patterns")
    
    print("\n" + "=" * 60)
    
    return successful_categories == total_categories

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
