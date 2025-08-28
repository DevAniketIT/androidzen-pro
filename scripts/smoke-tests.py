#!/usr/bin/env python3
"""
Smoke tests for AndroidZen Pro deployment validation.
"""

import argparse
import json
import os
import sys
import time
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SmokeTestRunner:
    """Run smoke tests against deployed application."""
    
    def __init__(self, environment, comprehensive=False):
        self.environment = environment
        self.comprehensive = comprehensive
        self.session = self._create_session()
        
        # Environment-specific URLs
        if environment == "staging":
            self.api_base = "https://api-staging.androidzen.dev"
            self.frontend_base = "https://staging.androidzen.dev"
        elif environment == "production":
            self.api_base = "https://api.androidzen.dev"
            self.frontend_base = "https://androidzen.dev"
        else:
            raise ValueError(f"Unsupported environment: {environment}")
    
    def _create_session(self):
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def test_backend_health(self):
        """Test backend health endpoint."""
        print("🔍 Testing backend health...")
        
        try:
            response = self.session.get(
                urljoin(self.api_base, "/health"),
                timeout=10
            )
            response.raise_for_status()
            
            health_data = response.json()
            assert health_data.get("status") == "healthy"
            
            print("✅ Backend health check passed")
            return True
            
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")
            return False
    
    def test_frontend_accessibility(self):
        """Test frontend accessibility."""
        print("🔍 Testing frontend accessibility...")
        
        try:
            response = self.session.get(self.frontend_base, timeout=10)
            response.raise_for_status()
            
            # Check for basic HTML structure
            html_content = response.text.lower()
            assert "<html" in html_content
            assert "<body" in html_content
            assert "androidzen" in html_content
            
            print("✅ Frontend accessibility check passed")
            return True
            
        except Exception as e:
            print(f"❌ Frontend accessibility check failed: {e}")
            return False
    
    def test_api_authentication(self):
        """Test API authentication endpoints."""
        print("🔍 Testing API authentication...")
        
        try:
            # Test login endpoint accessibility
            response = self.session.post(
                urljoin(self.api_base, "/api/auth/login"),
                json={"email": "test@example.com", "password": "invalid"},
                timeout=10
            )
            
            # We expect this to fail with 401/422, not 500
            assert response.status_code in [401, 422]
            
            print("✅ API authentication endpoint accessible")
            return True
            
        except Exception as e:
            print(f"❌ API authentication test failed: {e}")
            return False
    
    def test_database_connectivity(self):
        """Test database connectivity through API."""
        print("🔍 Testing database connectivity...")
        
        try:
            # Test an endpoint that requires database access
            response = self.session.get(
                urljoin(self.api_base, "/api/devices"),
                timeout=10
            )
            
            # We expect 401 (unauthorized) not 500 (database error)
            assert response.status_code == 401
            
            print("✅ Database connectivity check passed")
            return True
            
        except Exception as e:
            print(f"❌ Database connectivity test failed: {e}")
            return False
    
    def test_comprehensive_apis(self):
        """Run comprehensive API tests."""
        if not self.comprehensive:
            return True
            
        print("🔍 Running comprehensive API tests...")
        
        endpoints_to_test = [
            "/api/devices",
            "/api/analytics",
            "/api/reports",
            "/api/settings",
            "/api/monitoring",
        ]
        
        passed = 0
        total = len(endpoints_to_test)
        
        for endpoint in endpoints_to_test:
            try:
                response = self.session.get(
                    urljoin(self.api_base, endpoint),
                    timeout=10
                )
                
                # Accept 401 (unauthorized) as success - endpoint is accessible
                if response.status_code in [200, 401]:
                    passed += 1
                    print(f"✅ {endpoint} - accessible")
                else:
                    print(f"❌ {endpoint} - status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {endpoint} - error: {e}")
        
        success_rate = passed / total
        if success_rate >= 0.8:  # 80% success rate required
            print(f"✅ Comprehensive API tests passed ({passed}/{total})")
            return True
        else:
            print(f"❌ Comprehensive API tests failed ({passed}/{total})")
            return False
    
    def test_performance_basic(self):
        """Basic performance tests."""
        print("🔍 Testing basic performance...")
        
        try:
            # Test response times
            start_time = time.time()
            response = self.session.get(
                urljoin(self.api_base, "/health"),
                timeout=10
            )
            response_time = time.time() - start_time
            
            response.raise_for_status()
            
            # Response time should be under 2 seconds
            if response_time < 2.0:
                print(f"✅ Response time acceptable: {response_time:.2f}s")
                return True
            else:
                print(f"❌ Response time too slow: {response_time:.2f}s")
                return False
                
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all smoke tests."""
        print(f"🚀 Running smoke tests for {self.environment} environment")
        print(f"📊 Comprehensive mode: {'enabled' if self.comprehensive else 'disabled'}")
        print("-" * 50)
        
        tests = [
            self.test_backend_health,
            self.test_frontend_accessibility,
            self.test_api_authentication,
            self.test_database_connectivity,
            self.test_comprehensive_apis,
            self.test_performance_basic,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
            
            print()  # Add spacing between tests
        
        print("-" * 50)
        print(f"📋 Test Results: {passed}/{total} passed")
        
        if passed == total:
            print("🎉 All smoke tests passed!")
            return True
        else:
            print("💥 Some smoke tests failed!")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run AndroidZen Pro smoke tests")
    parser.add_argument(
        "--env",
        choices=["staging", "production"],
        required=True,
        help="Target environment"
    )
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive test suite"
    )
    
    args = parser.parse_args()
    
    runner = SmokeTestRunner(args.env, args.comprehensive)
    
    try:
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
