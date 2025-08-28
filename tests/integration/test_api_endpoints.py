#!/usr/bin/env python3
"""
Test script for AndroidZen Pro API endpoints
Tests public endpoints, authentication, and CORS configuration
"""

import requests
import json
import time
from typing import Dict, Any, Optional
import sys

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 10

def print_header(title: str):
    """Print a formatted header for test sections"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_test_result(test_name: str, success: bool, details: str = ""):
    """Print formatted test results"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")

def make_request(method: str, url: str, data: Dict[Any, Any] = None, 
                headers: Dict[str, str] = None, timeout: int = TIMEOUT) -> Optional[requests.Response]:
    """Make an HTTP request with error handling"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
        elif method.upper() == "OPTIONS":
            response = requests.options(url, headers=headers, timeout=timeout)
        else:
            print(f"Unsupported method: {method}")
            return None
        
        return response
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed to {url}")
        return None
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout to {url}")
        return None
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None

def test_public_endpoints():
    """Test public endpoints that don't require authentication"""
    print_header("Testing Public Endpoints")
    
    # Test root endpoint
    print("\n1. Testing Root Endpoint (GET /)")
    response = make_request("GET", f"{BASE_URL}/")
    if response and response.status_code == 200:
        data = response.json()
        print_test_result(
            "Root endpoint", 
            True, 
            f"Status: {response.status_code}, Message: {data.get('message', 'N/A')}"
        )
        print(f"    Response: {json.dumps(data, indent=2)}")
    else:
        status_code = response.status_code if response else "No response"
        print_test_result("Root endpoint", False, f"Status: {status_code}")
    
    # Test health check endpoint
    print("\n2. Testing Health Check Endpoint (GET /health)")
    response = make_request("GET", f"{BASE_URL}/health")
    if response and response.status_code == 200:
        data = response.json()
        print_test_result(
            "Health check endpoint", 
            True, 
            f"Status: {response.status_code}, Service: {data.get('service', 'N/A')}"
        )
        print(f"    Response: {json.dumps(data, indent=2)}")
    else:
        status_code = response.status_code if response else "No response"
        print_test_result("Health check endpoint", False, f"Status: {status_code}")

def test_cors_configuration():
    """Test CORS configuration"""
    print_header("Testing CORS Configuration")
    
    # Test CORS preflight request
    print("\n1. Testing CORS Preflight (OPTIONS /)")
    cors_headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization"
    }
    
    response = make_request("OPTIONS", f"{BASE_URL}/", headers=cors_headers)
    if response:
        cors_origin = response.headers.get("Access-Control-Allow-Origin", "")
        cors_methods = response.headers.get("Access-Control-Allow-Methods", "")
        cors_headers_allowed = response.headers.get("Access-Control-Allow-Headers", "")
        cors_credentials = response.headers.get("Access-Control-Allow-Credentials", "")
        
        print_test_result(
            "CORS preflight", 
            response.status_code == 200, 
            f"Status: {response.status_code}"
        )
        print(f"    Access-Control-Allow-Origin: {cors_origin}")
        print(f"    Access-Control-Allow-Methods: {cors_methods}")
        print(f"    Access-Control-Allow-Headers: {cors_headers_allowed}")
        print(f"    Access-Control-Allow-Credentials: {cors_credentials}")
        
        # Check if frontend origins are allowed
        if "localhost:3000" in cors_origin or "*" in cors_origin:
            print_test_result("Frontend origin allowed", True, "React dev server supported")
        else:
            print_test_result("Frontend origin allowed", False, f"Origin: {cors_origin}")
    else:
        print_test_result("CORS preflight", False, "No response")

def test_authentication_endpoints():
    """Test authentication endpoints"""
    print_header("Testing Authentication Endpoints")
    
    # Test login with existing demo user first
    print("\n1. Testing User Login with Demo User (POST /api/auth/login)")
    login_data = {
        "username": "demo",
        "password": "demo123"
    }
    
    response = make_request("POST", f"{BASE_URL}/api/auth/login", data=login_data)
    jwt_token = None
    
    if response:
        print_test_result(
            "Demo user login", 
            response.status_code == 200, 
            f"Status: {response.status_code}"
        )
        if response.status_code == 200:
            try:
                data = response.json()
                jwt_token = data.get("access_token")
                token_type = data.get("token_type", "bearer")
                print(f"    Login successful!")
                print(f"    Token type: {token_type}")
                print(f"    Token (first 50 chars): {jwt_token[:50] if jwt_token else 'None'}...")
                print(f"    User: {data.get('user', {}).get('username', 'N/A')}")
            except:
                print(f"    Response text: {response.text}")
        else:
            print(f"    Error response: {response.text}")
    else:
        print_test_result("Demo user login", False, "No response")
    
    # Test admin user login
    print("\n2. Testing Admin User Login (POST /api/auth/login)")
    admin_login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = make_request("POST", f"{BASE_URL}/api/auth/login", data=admin_login_data)
    if response:
        print_test_result(
            "Admin user login", 
            response.status_code == 200, 
            f"Status: {response.status_code}"
        )
        if response.status_code == 200:
            try:
                data = response.json()
                admin_user = data.get('user', {})
                print(f"    Admin login successful!")
                print(f"    Admin status: {admin_user.get('is_admin', False)}")
                print(f"    Permissions: {admin_user.get('permissions', [])}")
            except:
                print(f"    Response text: {response.text}")
        else:
            print(f"    Error response: {response.text}")
    else:
        print_test_result("Admin user login", False, "No response")
    
    # Test user registration
    print("\n3. Testing User Registration (POST /api/auth/register)")
    register_data = {
        "username": "testuser123",
        "email": "testuser123@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    response = make_request("POST", f"{BASE_URL}/api/auth/register", data=register_data)
    if response:
        print_test_result(
            "User registration", 
            response.status_code in [200, 201], 
            f"Status: {response.status_code}"
        )
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                print(f"    Registration response: {json.dumps(data, indent=2)}")
            except:
                print(f"    Response text: {response.text}")
        else:
            print(f"    Error response: {response.text}")
    else:
        print_test_result("User registration", False, "No response")
    
    # Test login with newly registered user
    print("\n4. Testing Login with Newly Registered User")
    new_user_login = {
        "username": "testuser123",
        "password": "testpassword123"
    }
    
    response = make_request("POST", f"{BASE_URL}/api/auth/login", data=new_user_login)
    if response:
        print_test_result(
            "New user login", 
            response.status_code == 200, 
            f"Status: {response.status_code}"
        )
        if response.status_code == 200:
            try:
                data = response.json()
                new_jwt_token = data.get("access_token")
                if new_jwt_token:
                    jwt_token = new_jwt_token  # Use the new token for further tests
                print(f"    New user login successful!")
                print(f"    Token obtained: {bool(new_jwt_token)}")
            except:
                print(f"    Response text: {response.text}")
        else:
            print(f"    Error response: {response.text}")
    else:
        print_test_result("New user login", False, "No response")
    
    # Test invalid login credentials
    print("\n5. Testing Invalid Login Credentials")
    invalid_login = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    
    response = make_request("POST", f"{BASE_URL}/api/auth/login", data=invalid_login)
    if response:
        unauthorized = response.status_code == 401
        print_test_result(
            "Invalid login rejection", 
            unauthorized, 
            f"Status: {response.status_code} {'(correctly unauthorized)' if unauthorized else '(should be unauthorized)'}"
        )
    else:
        print_test_result("Invalid login rejection", False, "No response")
    
    return jwt_token

def test_jwt_token_validation(token: str):
    """Test JWT token validation"""
    print_header("Testing JWT Token Validation")
    
    if not token:
        print_test_result("JWT token validation", False, "No token available from login")
        return
    
    # Test protected endpoint with token
    print("\n1. Testing Protected Endpoint Access with JWT Token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Try to access a protected endpoint (devices API)
    response = make_request("GET", f"{BASE_URL}/api/devices/", headers=headers)
    if response:
        print_test_result(
            "Protected endpoint with valid token", 
            response.status_code in [200, 404],  # 404 is OK if no devices exist
            f"Status: {response.status_code}"
        )
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"    Devices response: {json.dumps(data, indent=2)}")
            except:
                print(f"    Response text: {response.text}")
        elif response.status_code == 404:
            print("    No devices found (expected for new user)")
        else:
            print(f"    Error response: {response.text}")
    else:
        print_test_result("Protected endpoint with valid token", False, "No response")
    
    # Test protected endpoint without token
    print("\n2. Testing Protected Endpoint Access without JWT Token")
    response = make_request("GET", f"{BASE_URL}/api/devices/")
    if response:
        unauthorized = response.status_code == 401 or response.status_code == 403
        print_test_result(
            "Protected endpoint without token", 
            unauthorized, 
            f"Status: {response.status_code} {'(correctly unauthorized)' if unauthorized else '(should be unauthorized)'}"
        )
        if not unauthorized:
            print(f"    Unexpected response: {response.text}")
    else:
        print_test_result("Protected endpoint without token", False, "No response")
    
    # Test protected endpoint with invalid token
    print("\n3. Testing Protected Endpoint Access with Invalid JWT Token")
    invalid_headers = {
        "Authorization": "Bearer invalid_token_12345",
        "Content-Type": "application/json"
    }
    
    response = make_request("GET", f"{BASE_URL}/api/devices/", headers=invalid_headers)
    if response:
        unauthorized = response.status_code == 401 or response.status_code == 403
        print_test_result(
            "Protected endpoint with invalid token", 
            unauthorized, 
            f"Status: {response.status_code} {'(correctly unauthorized)' if unauthorized else '(should be unauthorized)'}"
        )
        if not unauthorized:
            print(f"    Unexpected response: {response.text}")
    else:
        print_test_result("Protected endpoint with invalid token", False, "No response")

def wait_for_server():
    """Wait for the server to start up"""
    print("Waiting for server to start up...")
    max_attempts = 20
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except:
            pass
        time.sleep(1)
        print(f"Attempt {attempt + 1}/{max_attempts}...")
    
    print("❌ Server failed to start or is not responding")
    return False

def main():
    """Main test execution"""
    print("🚀 AndroidZen Pro API Endpoint Testing")
    print(f"Testing server at: {BASE_URL}")
    
    # Wait for server to be ready
    if not wait_for_server():
        sys.exit(1)
    
    # Run tests
    test_public_endpoints()
    test_cors_configuration()
    jwt_token = test_authentication_endpoints()
    test_jwt_token_validation(jwt_token)
    
    # Summary
    print_header("Testing Complete")
    print("✅ All endpoint tests have been executed!")
    print("📝 Review the results above for any failures or issues.")
    print("\nNext steps:")
    print("- Check server logs for any errors")
    print("- Verify database connections are working")
    print("- Test WebSocket connections if needed")
    print("- Run integration tests with frontend")

if __name__ == "__main__":
    main()
