#!/usr/bin/env python3
"""
Comprehensive import testing script for AndroidZen Pro
Tests all Python modules for import errors, missing dependencies, and circular imports
"""

import sys
import os
import importlib
import traceback
import ast
from pathlib import Path
import inspect
from typing import List, Dict, Set, Tuple

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

class ImportTester:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.results = {
            'success': [],
            'failures': [],
            'warnings': [],
            'circular_imports': [],
            'missing_deps': []
        }
        self.imported_modules = set()
        self.import_stack = []
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project"""
        python_files = []
        for root, dirs, files in os.walk(self.base_path):
            # Skip __pycache__ and .git directories
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__') and d != '.git']
            
            for file in files:
                if file.endswith('.py') and not file.startswith('.'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name"""
        try:
            relative_path = file_path.relative_to(self.base_path)
        except ValueError:
            # File is outside base path, use absolute module name
            return str(file_path.stem)
        
        parts = list(relative_path.parts[:-1])  # Remove filename
        if relative_path.stem != '__init__':
            parts.append(relative_path.stem)
        
        return '.'.join(parts) if parts else relative_path.stem
    
    def parse_imports(self, file_path: Path) -> List[str]:
        """Parse imports from a Python file"""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
        except Exception as e:
            self.results['warnings'].append(f"Could not parse imports from {file_path}: {e}")
        
        return imports
    
    def test_import(self, module_name: str, file_path: Path) -> bool:
        """Test importing a specific module"""
        if module_name in self.import_stack:
            self.results['circular_imports'].append(f"Circular import detected: {' -> '.join(self.import_stack)} -> {module_name}")
            return False
        
        self.import_stack.append(module_name)
        
        try:
            # Try to import the module
            if module_name in sys.modules:
                # Module already imported, reload to test fresh import
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
            
            self.results['success'].append(f"✓ {module_name}")
            self.imported_modules.add(module_name)
            return True
            
        except ImportError as e:
            error_msg = str(e)
            if "No module named" in error_msg:
                self.results['missing_deps'].append(f"✗ {module_name}: Missing dependency - {error_msg}")
            else:
                self.results['failures'].append(f"✗ {module_name}: Import error - {error_msg}")
            return False
            
        except Exception as e:
            self.results['failures'].append(f"✗ {module_name}: Unexpected error - {str(e)}\n{traceback.format_exc()}")
            return False
            
        finally:
            if module_name in self.import_stack:
                self.import_stack.remove(module_name)
    
    def test_all_modules(self):
        """Test importing all Python modules in the project"""
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files to test")
        print("=" * 60)
        
        # Group files by module type
        api_modules = []
        core_modules = []
        service_modules = []
        model_modules = []
        other_modules = []
        
        for file_path in python_files:
            module_name = self.get_module_name(file_path)
            
            if 'api' in str(file_path):
                api_modules.append((module_name, file_path))
            elif 'core' in str(file_path):
                core_modules.append((module_name, file_path))
            elif 'services' in str(file_path):
                service_modules.append((module_name, file_path))
            elif 'models' in str(file_path):
                model_modules.append((module_name, file_path))
            else:
                other_modules.append((module_name, file_path))
        
        # Test modules in order of dependency (core first, then models, services, api)
        module_groups = [
            ("Core modules", core_modules),
            ("Model modules", model_modules),
            ("Service modules", service_modules),
            ("API modules", api_modules),
            ("Other modules", other_modules)
        ]
        
        for group_name, modules in module_groups:
            if modules:
                print(f"\n{group_name}:")
                print("-" * 40)
                for module_name, file_path in modules:
                    self.test_import(module_name, file_path)
    
    def check_external_dependencies(self):
        """Check if all external dependencies are available"""
        print("\nChecking external dependencies...")
        print("-" * 40)
        
        # Common dependencies to check
        dependencies = [
            'fastapi', 'uvicorn', 'sqlalchemy', 'alembic', 'pydantic',
            'pandas', 'numpy', 'scikit-learn', 'websockets', 'adb_shell',
            'pure_python_adb', 'python_dotenv', 'passlib', 'python_jose',
            'python_multipart', 'psutil'
        ]
        
        for dep in dependencies:
            try:
                importlib.import_module(dep)
                self.results['success'].append(f"✓ External dependency: {dep}")
            except ImportError:
                self.results['missing_deps'].append(f"✗ Missing external dependency: {dep}")
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("IMPORT TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Success count
        print(f"\n✓ Successfully imported: {len(self.results['success'])} modules")
        
        # Failures
        if self.results['failures']:
            print(f"\n✗ Import failures: {len(self.results['failures'])}")
            for failure in self.results['failures']:
                print(f"  {failure}")
        
        # Missing dependencies
        if self.results['missing_deps']:
            print(f"\n⚠ Missing dependencies: {len(self.results['missing_deps'])}")
            for missing in self.results['missing_deps']:
                print(f"  {missing}")
        
        # Circular imports
        if self.results['circular_imports']:
            print(f"\n⚠ Circular imports detected: {len(self.results['circular_imports'])}")
            for circular in self.results['circular_imports']:
                print(f"  {circular}")
        
        # Warnings
        if self.results['warnings']:
            print(f"\n⚠ Warnings: {len(self.results['warnings'])}")
            for warning in self.results['warnings']:
                print(f"  {warning}")
        
        # Overall status
        total_issues = len(self.results['failures']) + len(self.results['missing_deps']) + len(self.results['circular_imports'])
        
        print("\n" + "=" * 60)
        if total_issues == 0:
            print("🎉 ALL IMPORTS SUCCESSFUL! No issues detected.")
        else:
            print(f"⚠ {total_issues} issues detected that need attention.")
        print("=" * 60)

def main():
    """Main function to run import tests"""
    print("AndroidZen Pro - Import Testing Suite")
    print("=" * 60)
    print("Testing all module imports and dependencies...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create and run the import tester
    tester = ImportTester(project_root)
    
    # Test external dependencies first
    tester.check_external_dependencies()
    
    # Test all project modules
    tester.test_all_modules()
    
    # Print results
    tester.print_results()
    
    # Return exit code based on results
    total_issues = len(tester.results['failures']) + len(tester.results['missing_deps'])
    return 0 if total_issues == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
