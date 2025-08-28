#!/usr/bin/env python3
"""
Test runner script for AndroidZen Pro

This script provides easy commands to run different types of tests:
- All tests
- Unit tests only
- Integration tests only
- End-to-end tests only
- Performance tests only
- Tests with coverage reports

Usage:
    python run_tests.py [all|unit|integration|e2e|performance|coverage|help]
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd: list, description: str = ""):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    if description:
        print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description or 'Command'} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description or 'Command'} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Command not found. Make sure pytest is installed: pip install pytest")
        return False


def run_all_tests():
    """Run all tests."""
    cmd = ["pytest", "tests/", "-v"]
    return run_command(cmd, "All Tests")


def run_unit_tests():
    """Run unit tests only."""
    cmd = ["pytest", "tests/unit/", "-v"]
    return run_command(cmd, "Unit Tests")


def run_integration_tests():
    """Run integration tests only."""
    cmd = ["pytest", "tests/integration/", "-v"]
    return run_command(cmd, "Integration Tests")


def run_e2e_tests():
    """Run end-to-end tests only."""
    cmd = ["pytest", "tests/e2e/", "-v"]
    return run_command(cmd, "End-to-End Tests")


def run_performance_tests():
    """Run performance tests only."""
    cmd = ["pytest", "tests/performance/", "-v"]
    return run_command(cmd, "Performance Tests")


def run_security_tests():
    """Run security tests only."""
    cmd = ["pytest", "tests/security/", "-v"]
    return run_command(cmd, "Security Tests")


def run_with_coverage():
    """Run all tests with coverage report."""
    cmd = ["pytest", "tests/", "-v", "--cov=backend", "--cov-report=term-missing", "--cov-report=html"]
    return run_command(cmd, "All Tests with Coverage")


def run_fast_tests():
    """Run only fast tests (exclude slow tests)."""
    cmd = ["pytest", "tests/", "-v", "-m", "not slow"]
    return run_command(cmd, "Fast Tests Only")


def run_marked_tests(marker: str):
    """Run tests with specific marker."""
    cmd = ["pytest", "tests/", "-v", "-m", marker]
    return run_command(cmd, f"Tests marked with '{marker}'")


def show_help():
    """Show help information."""
    print("\nAndroidZen Pro Test Runner")
    print("=" * 60)
    print("Available commands:")
    print("  all           - Run all tests")
    print("  unit          - Run unit tests only")
    print("  integration   - Run integration tests only")
    print("  e2e           - Run end-to-end tests only")
    print("  performance   - Run performance tests only")
    print("  security      - Run security tests only")
    print("  coverage      - Run all tests with coverage report")
    print("  fast          - Run only fast tests (exclude slow)")
    print("  marker <name> - Run tests with specific marker")
    print("  help          - Show this help message")
    print("\nExamples:")
    print("  python run_tests.py all")
    print("  python run_tests.py unit")
    print("  python run_tests.py coverage")
    print("  python run_tests.py marker requires_db")
    print("\nTest Structure:")
    print("  tests/unit/         - Unit tests")
    print("  tests/integration/  - Integration tests")
    print("  tests/e2e/          - End-to-end tests")
    print("  tests/performance/  - Performance tests")
    print("  tests/security/     - Security tests")
    print("  tests/mocks/        - Mock objects")
    print("  tests/pipeline/     - CI/CD tests")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test runner for AndroidZen Pro",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "e2e", "performance", "security", 
                "coverage", "fast", "marker", "help"],
        help="Test command to run"
    )
    parser.add_argument(
        "marker_name",
        nargs="?",
        help="Marker name when using 'marker' command"
    )

    args = parser.parse_args()

    # Change to project root directory
    project_root = Path(__file__).parent
    if project_root != Path.cwd():
        print(f"Changing directory to: {project_root}")
        import os
        os.chdir(project_root)

    # Check if tests directory exists
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("❌ Tests directory not found. Make sure you're in the project root.")
        sys.exit(1)

    # Run the requested command
    success = True
    
    if args.command == "help":
        show_help()
    elif args.command == "all":
        success = run_all_tests()
    elif args.command == "unit":
        success = run_unit_tests()
    elif args.command == "integration":
        success = run_integration_tests()
    elif args.command == "e2e":
        success = run_e2e_tests()
    elif args.command == "performance":
        success = run_performance_tests()
    elif args.command == "security":
        success = run_security_tests()
    elif args.command == "coverage":
        success = run_with_coverage()
    elif args.command == "fast":
        success = run_fast_tests()
    elif args.command == "marker":
        if not args.marker_name:
            print("❌ Please specify a marker name. Example: python run_tests.py marker requires_db")
            sys.exit(1)
        success = run_marked_tests(args.marker_name)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
