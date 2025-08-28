#!/usr/bin/env python3
"""
Focused import testing script for AndroidZen Pro project modules only
Tests only project modules, avoids virtual environment conflicts
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

class FocusedImportTester:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.results = {
            'success': [],
            'failures': [],
            'warnings': []
        }
    
    def test_external_dependencies(self):
        """Test critical external dependencies"""
        print("Testing external dependencies...")
        print("-" * 50)
        
        critical_deps = [
            ('fastapi', 'FastAPI framework'),
            ('uvicorn', 'ASGI server'),
            ('sqlalchemy', 'Database ORM'),
            ('pydantic', 'Data validation'),
            ('pandas', 'Data analysis'),
            ('numpy', 'Numerical computing'),
            ('adb_shell', 'ADB shell interface'),
            ('websockets', 'WebSocket support'),
            ('psutil', 'System monitoring'),
            ('python_dotenv', 'Environment variables'),
            ('passlib', 'Password hashing'),
            ('pytest', 'Testing framework')
        ]
        
        for module_name, description in critical_deps:
            try:
                importlib.import_module(module_name)
                print(f"✓ {module_name} ({description})")
                self.results['success'].append(f"{module_name} - {description}")
            except ImportError as e:
                print(f"✗ {module_name} ({description}) - {e}")
                self.results['failures'].append(f"{module_name} - {e}")
    
    def test_project_modules(self):
        """Test project modules systematically"""
        print("\nTesting project modules...")
        print("-" * 50)
        
        # Test in dependency order
        module_tests = [
            # Core modules first
            ('backend.core.logging_config', 'Logging configuration'),
            ('backend.core.database', 'Database connection'),
            
            # Models (test individual models to avoid conflicts)
            ('backend.models.analytics', 'Analytics models'),
            
            # Services
            ('backend.services.intelligence_service', 'AI service'),
            ('backend.services.network_service', 'Network service'),
            ('backend.services.security_service', 'Security service'),
            ('backend.services.settings_service', 'Settings service'),
            ('backend.services.storage_service', 'Storage service'),
            
            # API modules
            ('backend.api.auth', 'Authentication API'),
            ('backend.api.devices', 'Devices API'),
            ('backend.api.monitoring', 'Monitoring API'),
            ('backend.api.network', 'Network API'),
            ('backend.api.security', 'Security API'),
            ('backend.api.settings', 'Settings API'),
            ('backend.api.storage', 'Storage API'),
            ('backend.api.websocket', 'WebSocket API'),
            
            # Utilities
            ('backend.utils.database_utils', 'Database utilities'),
            
            # Middleware
            ('backend.middleware.logging_middleware', 'Logging middleware'),
        ]
        
        for module_name, description in module_tests:
            self.test_single_module(module_name, description)
    
    def test_single_module(self, module_name: str, description: str):
        """Test importing a single module"""
        try:
            # Clear module from cache if it exists to test fresh import
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            importlib.import_module(module_name)
            print(f"✓ {module_name} ({description})")
            self.results['success'].append(f"{module_name} - {description}")
            return True
            
        except ImportError as e:
            print(f"✗ {module_name} ({description}) - Import Error: {e}")
            self.results['failures'].append(f"{module_name} - Import Error: {e}")
            return False
            
        except Exception as e:
            print(f"⚠ {module_name} ({description}) - Warning: {e}")
            self.results['warnings'].append(f"{module_name} - {e}")
            return False
    
    def test_specific_imports(self):
        """Test specific import statements that are known to cause issues"""
        print("\nTesting specific import statements...")
        print("-" * 50)
        
        specific_tests = [
            # Test AI service imports
            ("from backend.services.intelligence_service import AIService", "AIService class"),
            ("from backend.core.adb_manager import ADBManager", "ADBManager class"),
            ("from backend.core.websocket_manager import WebSocketManager", "WebSocketManager class"),
            ("from backend.models.analytics import AnalyticsRecord", "AnalyticsRecord model"),
        ]
        
        for import_statement, description in specific_tests:
            try:
                exec(import_statement)
                print(f"✓ {description}")
                self.results['success'].append(f"Import: {description}")
            except Exception as e:
                print(f"✗ {description} - {e}")
                self.results['failures'].append(f"Import {description} - {e}")
    
    def check_circular_imports(self):
        """Basic check for potential circular import issues"""
        print("\nChecking for potential circular import issues...")
        print("-" * 50)
        
        # Test imports that might have circular dependencies
        circular_tests = [
            ('backend.api.devices', 'backend.services.ai_service'),
            ('backend.core.adb_manager', 'backend.models.device'),
            ('backend.api.ai_analytics', 'backend.services.ai_service'),
        ]
        
        for module1, module2 in circular_tests:
            try:
                # Clear modules from cache
                if module1 in sys.modules:
                    del sys.modules[module1]
                if module2 in sys.modules:
                    del sys.modules[module2]
                
                # Try importing both
                importlib.import_module(module1)
                importlib.import_module(module2)
                print(f"✓ No circular import between {module1} and {module2}")
            except Exception as e:
                print(f"⚠ Potential issue between {module1} and {module2}: {e}")
                self.results['warnings'].append(f"Circular import check: {module1} <-> {module2} - {e}")
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("FOCUSED IMPORT TEST RESULTS")
        print("=" * 60)
        
        print(f"\n✓ Successful imports: {len(self.results['success'])}")
        
        if self.results['failures']:
            print(f"\n✗ Failed imports ({len(self.results['failures'])}):")
            for failure in self.results['failures']:
                print(f"  • {failure}")
        
        if self.results['warnings']:
            print(f"\n⚠ Warnings ({len(self.results['warnings'])}):")
            for warning in self.results['warnings']:
                print(f"  • {warning}")
        
        # Overall assessment
        total_issues = len(self.results['failures'])
        total_warnings = len(self.results['warnings'])
        
        print("\n" + "=" * 60)
        if total_issues == 0:
            if total_warnings == 0:
                print("🎉 ALL CRITICAL IMPORTS SUCCESSFUL! No issues detected.")
            else:
                print(f"✅ All critical imports successful, but {total_warnings} warnings need attention.")
        else:
            print(f"⚠ {total_issues} critical import failures detected.")
        print("=" * 60)
        
        return total_issues == 0

def main():
    """Main function to run focused import tests"""
    print("AndroidZen Pro - Focused Import Testing")
    print("=" * 60)
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create and run the import tester
    tester = FocusedImportTester(project_root)
    
    # Run tests in order
    tester.test_external_dependencies()
    tester.test_project_modules()
    tester.test_specific_imports()
    tester.check_circular_imports()
    
    # Print summary
    success = tester.print_summary()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
