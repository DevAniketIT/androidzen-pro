#!/usr/bin/env python3
"""Test Alembic migration system."""

import sys
import os
import subprocess
sys.path.insert(0, '.')

def test_alembic():
    """Test Alembic migration system."""
    try:
        os.chdir('backend')
        
        # Set environment variable for Python path
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.getcwd())
        
        print("Testing Alembic current version...")
        result = subprocess.run(['alembic', 'current'], 
                              capture_output=True, text=True, env=env)
        print(f"Current version stdout: {result.stdout}")
        print(f"Current version stderr: {result.stderr}")
        print(f"Return code: {result.returncode}")
        
        if result.returncode != 0:
            print("Alembic current failed, trying to create initial migration...")
            
            # Try to create an initial migration
            result2 = subprocess.run(['alembic', 'revision', '--autogenerate', '-m', 'Initial migration'], 
                                   capture_output=True, text=True, env=env)
            print(f"Create migration stdout: {result2.stdout}")
            print(f"Create migration stderr: {result2.stderr}")
            print(f"Create migration return code: {result2.returncode}")
            
            if result2.returncode == 0:
                print("Testing upgrade head...")
                result3 = subprocess.run(['alembic', 'upgrade', 'head'], 
                                       capture_output=True, text=True, env=env)
                print(f"Upgrade head stdout: {result3.stdout}")
                print(f"Upgrade head stderr: {result3.stderr}")
                print(f"Upgrade head return code: {result3.returncode}")
        
        os.chdir('..')
        
    except Exception as e:
        print(f"Error testing Alembic: {e}")
        os.chdir('..')

if __name__ == "__main__":
    test_alembic()
