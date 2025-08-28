#!/usr/bin/env python3
"""
Automated test runner for AndroidZen Pro testing pipeline.
"""

import os
import sys
import subprocess
import time
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional
import tempfile


class TestRunner:
    """Automated test runner for the testing pipeline."""

    def __init__(self):
        """Initialize the test runner."""
        self.project_root = Path(__file__).parent.parent.parent
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Test categories
        self.test_categories = {
            "unit": "tests/unit/",
            "integration": "tests/integration/",
            "performance": "tests/performance/",
            "security": "tests/security/"
        }
        
        # Results storage
        self.results = {
            "timestamp": time.time(),
            "categories": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "duration": 0
            }
        }

    def run_tests(self, categories: List[str] = None, 
                 parallel: bool = True,
                 coverage: bool = True,
                 verbose: bool = False,
                 fail_fast: bool = False) -> Dict:
        """
        Run tests for specified categories.
        
        Args:
            categories: List of test categories to run
            parallel: Run tests in parallel
            coverage: Generate coverage report
            verbose: Verbose output
            fail_fast: Stop on first failure
            
        Returns:
            Dictionary with test results
        """
        if categories is None:
            categories = list(self.test_categories.keys())
        
        print(f"🚀 Starting AndroidZen Pro Test Pipeline")
        print(f"Categories: {', '.join(categories)}")
        print(f"Parallel: {parallel}, Coverage: {coverage}")
        print("-" * 60)
        
        start_time = time.time()
        
        # Setup environment
        self._setup_test_environment()
        
        # Run tests by category
        for category in categories:
            if category not in self.test_categories:
                print(f"❌ Unknown category: {category}")
                continue
                
            print(f"\n📋 Running {category} tests...")
            result = self._run_category_tests(
                category, parallel, coverage, verbose, fail_fast
            )
            self.results["categories"][category] = result
            
            # Update summary
            self.results["summary"]["total_tests"] += result.get("total", 0)
            self.results["summary"]["passed"] += result.get("passed", 0)
            self.results["summary"]["failed"] += result.get("failed", 0)
            self.results["summary"]["skipped"] += result.get("skipped", 0)
            self.results["summary"]["errors"] += result.get("errors", 0)
            
            if fail_fast and result.get("failed", 0) > 0:
                print(f"🛑 Stopping on first failure in {category} tests")
                break
        
        self.results["summary"]["duration"] = time.time() - start_time
        
        # Generate reports
        self._generate_reports()
        
        # Print summary
        self._print_summary()
        
        return self.results

    def _setup_test_environment(self):
        """Setup test environment."""
        print("🔧 Setting up test environment...")
        
        # Set test environment variables
        os.environ["TESTING"] = "true"
        os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise during testing
        
        # Create test directories
        test_dirs = ["reports", "htmlcov", "logs"]
        for dir_name in test_dirs:
            (self.project_root / dir_name).mkdir(exist_ok=True)
        
        # Install test dependencies if needed
        self._ensure_test_dependencies()

    def _ensure_test_dependencies(self):
        """Ensure test dependencies are installed."""
        try:
            import pytest
            import coverage
        except ImportError:
            print("📦 Installing test dependencies...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
            ], check=True, cwd=self.project_root)

    def _run_category_tests(self, category: str, parallel: bool, 
                           coverage: bool, verbose: bool, fail_fast: bool) -> Dict:
        """Run tests for a specific category."""
        test_path = self.test_categories[category]
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        # Add test path and markers
        cmd.extend([test_path, "-m", category])
        
        # Add options
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        if fail_fast:
            cmd.append("--tb=short")
            cmd.append("--maxfail=1")
        
        # Parallel execution
        if parallel and category != "security":  # Security tests run sequentially
            cmd.extend(["-n", "auto"])
        
        # Coverage for unit and integration tests
        if coverage and category in ["unit", "integration"]:
            cmd.extend([
                "--cov=backend",
                f"--cov-report=html:htmlcov/{category}",
                f"--cov-report=xml:reports/{category}_coverage.xml"
            ])
        
        # Output formats
        cmd.extend([
            "--html=reports/{}_report.html".format(category),
            "--self-contained-html",
            "--json-report",
            "--json-report-file=reports/{}_report.json".format(category)
        ])
        
        # Timeout for performance tests
        if category == "performance":
            cmd.extend(["--timeout=600"])  # 10 minutes
        
        print(f"Running: {' '.join(cmd)}")
        
        # Execute tests
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour max
            )
            duration = time.time() - start_time
            
            # Parse results
            test_result = self._parse_test_output(result, category, duration)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            return {
                "category": category,
                "status": "timeout",
                "duration": time.time() - start_time,
                "total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 1
            }
        except Exception as e:
            print(f"❌ Error running {category} tests: {e}")
            return {
                "category": category,
                "status": "error",
                "error": str(e),
                "duration": time.time() - start_time,
                "total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 1
            }

    def _parse_test_output(self, result: subprocess.CompletedProcess, 
                          category: str, duration: float) -> Dict:
        """Parse pytest output to extract results."""
        # Try to read JSON report first
        json_report_path = self.project_root / f"reports/{category}_report.json"
        if json_report_path.exists():
            try:
                with open(json_report_path, 'r') as f:
                    json_data = json.load(f)
                
                summary = json_data.get("summary", {})
                return {
                    "category": category,
                    "status": "success" if result.returncode == 0 else "failed",
                    "duration": duration,
                    "total": summary.get("total", 0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "skipped": summary.get("skipped", 0),
                    "errors": summary.get("error", 0),
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            except Exception as e:
                print(f"Warning: Could not parse JSON report: {e}")
        
        # Fallback to parsing stdout
        lines = result.stdout.split('\n')
        test_result = {
            "category": category,
            "status": "success" if result.returncode == 0 else "failed",
            "duration": duration,
            "total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
        # Parse summary line (e.g., "5 passed, 2 failed, 1 skipped in 10.5s")
        for line in lines:
            if "passed" in line or "failed" in line or "error" in line:
                # Simple regex-free parsing
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        test_result["passed"] = int(parts[i-1])
                    elif part == "failed" and i > 0:
                        test_result["failed"] = int(parts[i-1])
                    elif part == "skipped" and i > 0:
                        test_result["skipped"] = int(parts[i-1])
                    elif part == "error" and i > 0:
                        test_result["errors"] = int(parts[i-1])
        
        test_result["total"] = (test_result["passed"] + test_result["failed"] + 
                              test_result["skipped"] + test_result["errors"])
        
        return test_result

    def _generate_reports(self):
        """Generate consolidated test reports."""
        print("\n📊 Generating reports...")
        
        # Generate consolidated HTML report
        self._generate_html_report()
        
        # Generate JUnit XML for CI/CD
        self._generate_junit_xml()
        
        # Generate coverage summary
        self._generate_coverage_summary()

    def _generate_html_report(self):
        """Generate consolidated HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AndroidZen Pro Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .category {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
        .summary {{ font-size: 18px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AndroidZen Pro Test Results</h1>
        <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Duration: {self.results['summary']['duration']:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: {self.results['summary']['total_tests']}</p>
        <p class="passed">✅ Passed: {self.results['summary']['passed']}</p>
        <p class="failed">❌ Failed: {self.results['summary']['failed']}</p>
        <p class="skipped">⏭️ Skipped: {self.results['summary']['skipped']}</p>
        <p>❗ Errors: {self.results['summary']['errors']}</p>
    </div>
    
    <h2>Categories</h2>
    <table>
        <tr>
            <th>Category</th>
            <th>Status</th>
            <th>Total</th>
            <th>Passed</th>
            <th>Failed</th>
            <th>Skipped</th>
            <th>Duration</th>
        </tr>
"""
        
        for category, result in self.results["categories"].items():
            status_class = "passed" if result["status"] == "success" else "failed"
            html_content += f"""
        <tr>
            <td>{category.title()}</td>
            <td class="{status_class}">{result["status"].title()}</td>
            <td>{result["total"]}</td>
            <td class="passed">{result["passed"]}</td>
            <td class="failed">{result["failed"]}</td>
            <td class="skipped">{result["skipped"]}</td>
            <td>{result["duration"]:.2f}s</td>
        </tr>
"""
        
        html_content += """
    </table>
</body>
</html>
"""
        
        with open(self.project_root / "reports/consolidated_report.html", "w") as f:
            f.write(html_content)

    def _generate_junit_xml(self):
        """Generate JUnit XML for CI/CD integration."""
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += f'<testsuites name="AndroidZen Pro Tests" tests="{self.results["summary"]["total_tests"]}" failures="{self.results["summary"]["failed"]}" time="{self.results["summary"]["duration"]:.2f}">\n'
        
        for category, result in self.results["categories"].items():
            xml_content += f'  <testsuite name="{category}" tests="{result["total"]}" failures="{result["failed"]}" time="{result["duration"]:.2f}">\n'
            
            # Add test cases (simplified)
            for i in range(result["passed"]):
                xml_content += f'    <testcase name="{category}_test_{i}" classname="{category}" time="0.1"/>\n'
            
            for i in range(result["failed"]):
                xml_content += f'    <testcase name="{category}_test_fail_{i}" classname="{category}" time="0.1">\n'
                xml_content += f'      <failure message="Test failed">Test failure in {category}</failure>\n'
                xml_content += f'    </testcase>\n'
            
            xml_content += f'  </testsuite>\n'
        
        xml_content += '</testsuites>\n'
        
        with open(self.project_root / "reports/junit.xml", "w") as f:
            f.write(xml_content)

    def _generate_coverage_summary(self):
        """Generate coverage summary."""
        coverage_files = list((self.project_root / "reports").glob("*_coverage.xml"))
        
        if coverage_files:
            print("📈 Coverage reports generated:")
            for coverage_file in coverage_files:
                print(f"  - {coverage_file}")

    def _print_summary(self):
        """Print test execution summary."""
        print("\n" + "="*60)
        print("🎯 TEST EXECUTION SUMMARY")
        print("="*60)
        
        summary = self.results["summary"]
        total = summary["total_tests"]
        passed = summary["passed"]
        failed = summary["failed"]
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed} ({success_rate:.1f}%)")
        print(f"❌ Failed: {failed}")
        print(f"⏭️ Skipped: {summary['skipped']}")
        print(f"❗ Errors: {summary['errors']}")
        print(f"⏱️ Duration: {summary['duration']:.2f}s")
        
        print("\nCategory Results:")
        for category, result in self.results["categories"].items():
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"  {status_icon} {category.title()}: {result['passed']}/{result['total']} passed")
        
        # Overall result
        overall_status = "✅ SUCCESS" if failed == 0 else "❌ FAILED"
        print(f"\nOverall Result: {overall_status}")
        
        # Generate reports info
        print(f"\n📊 Reports generated in: {self.project_root}/reports/")
        print("  - consolidated_report.html")
        print("  - junit.xml")
        
        if failed > 0:
            print("\n🔍 Check detailed reports for failure information.")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="AndroidZen Pro Test Runner")
    parser.add_argument(
        "--categories", 
        nargs="+", 
        choices=["unit", "integration", "performance", "security", "all"],
        default=["all"],
        help="Test categories to run"
    )
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel execution")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    
    args = parser.parse_args()
    
    # Handle 'all' category
    if "all" in args.categories:
        categories = ["unit", "integration", "performance", "security"]
    else:
        categories = args.categories
    
    # Create and run tests
    runner = TestRunner()
    results = runner.run_tests(
        categories=categories,
        parallel=not args.no_parallel,
        coverage=not args.no_coverage,
        verbose=args.verbose,
        fail_fast=args.fail_fast
    )
    
    # Exit with appropriate code
    exit_code = 0 if results["summary"]["failed"] == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
