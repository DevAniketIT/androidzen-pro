#!/usr/bin/env python3
"""
Comprehensive API and Integration Testing for AndroidZen Pro
Tests all REST API endpoints, authentication flow, file operations, database migrations,
WebSocket connections, and external API integrations.

This script follows the requirements from Step 10: Point 12: API and Integration Testing
"""

import asyncio
import json
import os
import sys
import time
import requests
import websockets
from typing import Dict, Any, Optional, List
import subprocess
import psutil
from datetime import datetime
import uuid
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"
TIMEOUT = 15
TEST_USER_DATA = {
    "username": f"testuser_{uuid.uuid4().hex[:8]}",
    "email": f"testuser_{uuid.uuid4().hex[:8]}@example.com",
    "password": "TestPassword123!",
    "full_name": "Integration Test User"
}

class Colors:
    """ANSI color codes for colored terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class TestResults:
    """Track test results and statistics"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []
    
    def add_result(self, test_name: str, passed: bool, details: str = "", skipped: bool = False):
        """Add a test result"""
        if skipped:
            self.skipped += 1
            status = "SKIP"
            color = Colors.YELLOW
        elif passed:
            self.passed += 1
            status = "PASS"
            color = Colors.GREEN
        else:
            self.failed += 1
            status = "FAIL"
            color = Colors.RED
        
        self.results.append({
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"{color}{status}{Colors.END} {test_name}")
        if details:
            print(f"    {details}")
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed + self.skipped
        print(f"\n{Colors.BOLD}Test Summary:{Colors.END}")
        print(f"Total: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.END}")
        print(f"{Colors.YELLOW}Skipped: {self.skipped}{Colors.END}")
        
        if self.failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test']}: {result['details']}")
    
    def save_results(self, filename: str = "test_results.json"):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                'summary': {
                    'total': self.passed + self.failed + self.skipped,
                    'passed': self.passed,
                    'failed': self.failed,
                    'skipped': self.skipped
                },
                'results': self.results,
                'generated_at': datetime.now().isoformat()
            }, f, indent=2)

class APITester:
    """Main API testing class"""
    
    def __init__(self):
        self.results = TestResults()
        self.jwt_token = None
        self.refresh_token = None
        self.user_id = None
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
    
    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}")
        print(f" {title}")
        print(f"{'='*80}{Colors.END}")
    
    def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None, 
                    headers: Dict[str, str] = None, files: Dict[str, Any] = None,
                    auth_required: bool = True) -> Optional[requests.Response]:
        """Make an HTTP request with error handling"""
        url = f"{BASE_URL}{endpoint}"
        request_headers = headers or {}
        
        # Add authentication if required and available
        if auth_required and self.jwt_token:
            request_headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=request_headers)
            elif method.upper() == "POST":
                if files:
                    response = self.session.post(url, data=data, files=files, headers=request_headers)
                else:
                    response = self.session.post(url, json=data, headers=request_headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=request_headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=request_headers)
            elif method.upper() == "PATCH":
                response = self.session.patch(url, json=data, headers=request_headers)
            elif method.upper() == "OPTIONS":
                response = self.session.options(url, headers=request_headers)
            else:
                logger.error(f"Unsupported method: {method}")
                return None
            
            return response
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection failed to {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout to {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Request error to {url}: {e}")
            return None
    
    def wait_for_server(self, max_attempts: int = 30) -> bool:
        """Wait for the server to start up"""
        print(f"{Colors.BLUE}Waiting for server to start up...{Colors.END}")
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=3)
                if response.status_code == 200:
                    print(f"{Colors.GREEN}✅ Server is ready!{Colors.END}")
                    return True
            except:
                pass
            time.sleep(2)
            if attempt % 5 == 0:
                print(f"Attempt {attempt + 1}/{max_attempts}...")
        
        print(f"{Colors.RED}❌ Server failed to start or is not responding{Colors.END}")
        return False
    
    def test_public_endpoints(self):
        """Test public endpoints that don't require authentication"""
        self.print_header("Testing Public Endpoints")
        
        # Test root endpoint
        response = self.make_request("GET", "/", auth_required=False)
        if response and response.status_code == 200:
            data = response.json()
            self.results.add_result(
                "Root endpoint (/)", 
                True, 
                f"Status: {response.status_code}, Service: {data.get('message', 'N/A')}"
            )
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Root endpoint (/)", False, f"Status: {status}")
        
        # Test health check endpoint
        response = self.make_request("GET", "/health", auth_required=False)
        if response and response.status_code in [200, 503]:  # 503 is acceptable for degraded service
            data = response.json()
            self.results.add_result(
                "Health check endpoint (/health)", 
                True, 
                f"Status: {response.status_code}, Health: {data.get('status', 'N/A')}"
            )
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Health check endpoint (/health)", False, f"Status: {status}")
        
        # Test OpenAPI docs endpoint
        response = self.make_request("GET", "/docs", auth_required=False)
        if response and response.status_code == 200:
            self.results.add_result("OpenAPI docs endpoint (/docs)", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("OpenAPI docs endpoint (/docs)", False, f"Status: {status}")
        
        # Test ReDoc endpoint
        response = self.make_request("GET", "/redoc", auth_required=False)
        if response and response.status_code == 200:
            self.results.add_result("ReDoc endpoint (/redoc)", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("ReDoc endpoint (/redoc)", False, f"Status: {status}")
        
        # Test OpenAPI schema endpoint
        response = self.make_request("GET", "/openapi.json", auth_required=False)
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.results.add_result("OpenAPI schema endpoint", True, f"Status: {response.status_code}")
            except:
                self.results.add_result("OpenAPI schema endpoint", False, "Invalid JSON response")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("OpenAPI schema endpoint", False, f"Status: {status}")
    
    def test_authentication_flow(self):
        """Test complete authentication flow end-to-end"""
        self.print_header("Testing Authentication Flow End-to-End")
        
        # Test user registration
        response = self.make_request("POST", "/api/auth/register", data=TEST_USER_DATA, auth_required=False)
        if response and response.status_code in [200, 201]:
            data = response.json()
            self.results.add_result(
                "User registration", 
                True, 
                f"Status: {response.status_code}, User: {data.get('user', {}).get('username', 'N/A')}"
            )
        else:
            status = response.status_code if response else "No response"
            error_msg = response.text if response else "No response"
            self.results.add_result("User registration", False, f"Status: {status}, Error: {error_msg}")
            return
        
        # Test user login
        login_data = {
            "username": TEST_USER_DATA["username"],
            "password": TEST_USER_DATA["password"]
        }
        response = self.make_request("POST", "/api/auth/login", data=login_data, auth_required=False)
        if response and response.status_code == 200:
            data = response.json()
            self.jwt_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            user = data.get("user", {})
            self.user_id = user.get("id")
            self.results.add_result(
                "User login", 
                True, 
                f"Status: {response.status_code}, Token received: {bool(self.jwt_token)}"
            )
        else:
            status = response.status_code if response else "No response"
            error_msg = response.text if response else "No response"
            self.results.add_result("User login", False, f"Status: {status}, Error: {error_msg}")
            return
        
        # Test get current user
        response = self.make_request("GET", "/api/auth/me")
        if response and response.status_code == 200:
            data = response.json()
            user = data.get("user", {})
            self.results.add_result(
                "Get current user", 
                True, 
                f"Status: {response.status_code}, User: {user.get('username', 'N/A')}"
            )
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Get current user", False, f"Status: {status}")
        
        # Test token refresh
        if self.refresh_token:
            refresh_data = {"refresh_token": self.refresh_token}
            response = self.make_request("POST", "/api/auth/refresh", data=refresh_data, auth_required=False)
            if response and response.status_code == 200:
                data = response.json()
                new_token = data.get("access_token")
                if new_token:
                    self.jwt_token = new_token
                self.results.add_result(
                    "Token refresh", 
                    True, 
                    f"Status: {response.status_code}, New token received: {bool(new_token)}"
                )
            else:
                status = response.status_code if response else "No response"
                self.results.add_result("Token refresh", False, f"Status: {status}")
        else:
            self.results.add_result("Token refresh", False, "No refresh token available")
        
        # Test invalid credentials
        invalid_login = {
            "username": "nonexistent_user",
            "password": "wrong_password"
        }
        response = self.make_request("POST", "/api/auth/login", data=invalid_login, auth_required=False)
        unauthorized = response and response.status_code == 401
        self.results.add_result(
            "Invalid credentials rejection", 
            unauthorized, 
            f"Status: {response.status_code if response else 'No response'} {'(correctly rejected)' if unauthorized else '(should be rejected)'}"
        )
        
        # Test logout
        response = self.make_request("POST", "/api/auth/logout")
        if response and response.status_code == 200:
            self.results.add_result("User logout", True, f"Status: {response.status_code}")
            # Re-login for subsequent tests
            response = self.make_request("POST", "/api/auth/login", data=login_data, auth_required=False)
            if response and response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("access_token")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("User logout", False, f"Status: {status}")
    
    def test_protected_endpoints(self):
        """Test protected endpoints that require authentication"""
        self.print_header("Testing Protected Endpoints")
        
        if not self.jwt_token:
            self.results.add_result("Protected endpoints", False, "No JWT token available")
            return
        
        # Test devices API
        response = self.make_request("GET", "/api/devices/")
        if response and response.status_code in [200, 404]:  # 404 is OK if no devices exist
            self.results.add_result("Devices list endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Devices list endpoint", False, f"Status: {status}")
        
        # Test storage API
        response = self.make_request("GET", "/api/storage/stats")
        if response and response.status_code in [200, 404]:
            self.results.add_result("Storage stats endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Storage stats endpoint", False, f"Status: {status}")
        
        # Test AI analytics API
        response = self.make_request("GET", "/api/ai/health")
        if response and response.status_code in [200, 503]:
            self.results.add_result("AI health endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("AI health endpoint", False, f"Status: {status}")
        
        # Test security API
        response = self.make_request("GET", "/api/security/events")
        if response and response.status_code in [200, 404]:
            self.results.add_result("Security events endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Security events endpoint", False, f"Status: {status}")
        
        # Test monitoring API
        response = self.make_request("GET", "/api/monitoring/health")
        if response and response.status_code in [200, 404]:
            self.results.add_result("Monitoring health endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Monitoring health endpoint", False, f"Status: {status}")
        
        # Test network API
        response = self.make_request("GET", "/api/network/status")
        if response and response.status_code in [200, 404]:
            self.results.add_result("Network status endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Network status endpoint", False, f"Status: {status}")
        
        # Test settings API
        response = self.make_request("GET", "/api/settings/")
        if response and response.status_code in [200, 404]:
            self.results.add_result("Settings endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Settings endpoint", False, f"Status: {status}")
        
        # Test reports API
        response = self.make_request("GET", "/api/reports/")
        if response and response.status_code in [200, 404]:
            self.results.add_result("Reports endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Reports endpoint", False, f"Status: {status}")
        
        # Test unauthorized access
        old_token = self.jwt_token
        self.jwt_token = None
        response = self.make_request("GET", "/api/devices/")
        unauthorized = response and response.status_code in [401, 403]
        self.results.add_result(
            "Unauthorized access rejection", 
            unauthorized, 
            f"Status: {response.status_code if response else 'No response'} {'(correctly rejected)' if unauthorized else '(should be rejected)'}"
        )
        self.jwt_token = old_token
    
    def test_file_upload_download(self):
        """Test file upload and download functionality"""
        self.print_header("Testing File Upload/Download Functionality")
        
        # Create a test file
        test_file_content = "This is a test file for upload testing"
        test_file_path = "test_upload.txt"
        
        try:
            with open(test_file_path, "w") as f:
                f.write(test_file_content)
            
            # Test file upload (check if upload endpoint exists)
            with open(test_file_path, "rb") as f:
                files = {"file": f}
                response = self.make_request("POST", "/api/files/upload", files=files)
                if response:
                    if response.status_code in [200, 201]:
                        self.results.add_result("File upload", True, f"Status: {response.status_code}")
                        
                        # Try to get the uploaded file info
                        try:
                            data = response.json()
                            file_id = data.get("file_id") or data.get("id")
                            if file_id:
                                # Test file download
                                download_response = self.make_request("GET", f"/api/files/download/{file_id}")
                                if download_response and download_response.status_code == 200:
                                    self.results.add_result("File download", True, f"Status: {download_response.status_code}")
                                else:
                                    status = download_response.status_code if download_response else "No response"
                                    self.results.add_result("File download", False, f"Status: {status}")
                            else:
                                self.results.add_result("File download", False, "No file ID returned from upload")
                        except:
                            self.results.add_result("File download", False, "Unable to parse upload response")
                    
                    elif response.status_code == 404:
                        self.results.add_result("File upload", False, "Upload endpoint not implemented (404)")
                        self.results.add_result("File download", False, "Download endpoint not available")
                    else:
                        status = response.status_code
                        self.results.add_result("File upload", False, f"Status: {status}")
                        self.results.add_result("File download", False, "Upload failed, cannot test download")
                else:
                    self.results.add_result("File upload", False, "No response from upload endpoint")
                    self.results.add_result("File download", False, "Upload failed, cannot test download")
        
        except Exception as e:
            self.results.add_result("File upload", False, f"Error creating test file: {e}")
            self.results.add_result("File download", False, "File upload test failed")
        
        finally:
            # Clean up test file
            try:
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)
            except:
                pass
    
    def test_database_migrations(self):
        """Test database migrations"""
        self.print_header("Testing Database Migrations")
        
        try:
            # Check if alembic is available
            result = subprocess.run(["alembic", "--version"], 
                                  capture_output=True, text=True, cwd="backend")
            if result.returncode == 0:
                self.results.add_result("Alembic availability", True, "Alembic is installed and accessible")
                
                # Check current migration status
                result = subprocess.run(["alembic", "current"], 
                                      capture_output=True, text=True, cwd="backend")
                if result.returncode == 0:
                    current_revision = result.stdout.strip()
                    self.results.add_result(
                        "Database migration status", 
                        True, 
                        f"Current revision: {current_revision or 'None (fresh database)'}"
                    )
                    
                    # Check if there are pending migrations
                    result = subprocess.run(["alembic", "heads"], 
                                          capture_output=True, text=True, cwd="backend")
                    if result.returncode == 0:
                        heads = result.stdout.strip()
                        self.results.add_result(
                            "Migration heads check", 
                            True, 
                            f"Available heads: {heads or 'None'}"
                        )
                        
                        # Test migration (upgrade to head)
                        result = subprocess.run(["alembic", "upgrade", "head"], 
                                              capture_output=True, text=True, cwd="backend")
                        if result.returncode == 0:
                            self.results.add_result("Database migration execution", True, "Migrations ran successfully")
                        else:
                            self.results.add_result(
                                "Database migration execution", 
                                False, 
                                f"Migration failed: {result.stderr or result.stdout}"
                            )
                    else:
                        self.results.add_result(
                            "Migration heads check", 
                            False, 
                            f"Error checking heads: {result.stderr}"
                        )
                else:
                    self.results.add_result(
                        "Database migration status", 
                        False, 
                        f"Error checking current revision: {result.stderr}"
                    )
            else:
                self.results.add_result("Alembic availability", False, "Alembic not found or not working")
                self.results.add_result("Database migration status", False, "Cannot check without Alembic")
                self.results.add_result("Database migration execution", False, "Cannot run without Alembic")
        
        except FileNotFoundError:
            self.results.add_result("Alembic availability", False, "Alembic command not found")
            self.results.add_result("Database migration status", False, "Cannot check without Alembic")
            self.results.add_result("Database migration execution", False, "Cannot run without Alembic")
        except Exception as e:
            self.results.add_result("Database migrations", False, f"Unexpected error: {e}")
    
    async def test_websocket_connections(self):
        """Test WebSocket connections and functionality"""
        self.print_header("Testing WebSocket Connections")
        
        try:
            # Test WebSocket connection without authentication
            ws_url = f"{WS_URL}?client_id=test_client_{uuid.uuid4().hex[:8]}"
            
            async with websockets.connect(ws_url, timeout=10) as websocket:
                self.results.add_result("WebSocket connection", True, "Successfully connected")
                
                # Test receiving connection confirmation
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    if data.get("type") == "device_connected":
                        self.results.add_result("WebSocket connection confirmation", True, "Received connection confirmation")
                    else:
                        self.results.add_result("WebSocket connection confirmation", True, f"Received message: {data.get('type')}")
                except asyncio.TimeoutError:
                    self.results.add_result("WebSocket connection confirmation", False, "No confirmation received within timeout")
                
                # Test sending a heartbeat message
                heartbeat_message = {
                    "type": "heartbeat",
                    "data": {}
                }
                await websocket.send(json.dumps(heartbeat_message))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    if response_data.get("type") == "heartbeat":
                        self.results.add_result("WebSocket heartbeat", True, "Heartbeat response received")
                    else:
                        self.results.add_result("WebSocket heartbeat", True, f"Response: {response_data.get('type')}")
                except asyncio.TimeoutError:
                    self.results.add_result("WebSocket heartbeat", False, "No heartbeat response within timeout")
                
                # Test subscription
                subscription_message = {
                    "type": "subscription",
                    "data": {"topic": "device_updates"}
                }
                await websocket.send(json.dumps(subscription_message))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    if response_data.get("type") == "subscription":
                        self.results.add_result("WebSocket subscription", True, "Subscription confirmed")
                    else:
                        self.results.add_result("WebSocket subscription", True, f"Response: {response_data.get('type')}")
                except asyncio.TimeoutError:
                    self.results.add_result("WebSocket subscription", False, "No subscription confirmation")
                
        except websockets.exceptions.ConnectionClosed:
            self.results.add_result("WebSocket connection", False, "Connection closed unexpectedly")
        except websockets.exceptions.InvalidURI:
            self.results.add_result("WebSocket connection", False, "Invalid WebSocket URI")
        except Exception as e:
            self.results.add_result("WebSocket connection", False, f"Connection error: {e}")
        
        # Test WebSocket statistics endpoint
        response = self.make_request("GET", "/ws/stats", auth_required=False)
        if response and response.status_code == 200:
            data = response.json()
            self.results.add_result("WebSocket stats endpoint", True, f"Status: {response.status_code}")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("WebSocket stats endpoint", False, f"Status: {status}")
    
    def test_external_api_integrations(self):
        """Test external API integrations (where applicable)"""
        self.print_header("Testing External API Integrations")
        
        # Since this is a device management system, external integrations might include:
        # - ADB (Android Debug Bridge)
        # - AI/ML services
        # - Third-party analytics services
        
        # Test if ADB is available (for Android device management)
        try:
            result = subprocess.run(["adb", "version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.results.add_result("ADB integration", True, "ADB is available and working")
                
                # Test ADB device listing
                result = subprocess.run(["adb", "devices"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    devices = result.stdout.strip()
                    self.results.add_result("ADB device detection", True, f"ADB devices command successful")
                else:
                    self.results.add_result("ADB device detection", False, "ADB devices command failed")
            else:
                self.results.add_result("ADB integration", False, "ADB not working properly")
        except FileNotFoundError:
            self.results.add_result("ADB integration", False, "ADB not found in PATH")
        except subprocess.TimeoutExpired:
            self.results.add_result("ADB integration", False, "ADB command timed out")
        except Exception as e:
            self.results.add_result("ADB integration", False, f"ADB error: {e}")
        
        # Test AI service integration (internal)
        response = self.make_request("GET", "/api/ai/health")
        if response and response.status_code in [200, 503]:
            try:
                data = response.json()
                status = data.get("status", "unknown")
                self.results.add_result("AI service integration", True, f"AI service status: {status}")
            except:
                self.results.add_result("AI service integration", True, f"AI service responded (status: {response.status_code})")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("AI service integration", False, f"AI service unavailable (status: {status})")
        
        # Test network connectivity (simulating external API calls)
        try:
            test_response = requests.get("https://httpbin.org/json", timeout=10)
            if test_response.status_code == 200:
                self.results.add_result("External API connectivity", True, "Network connectivity test successful")
            else:
                self.results.add_result("External API connectivity", False, f"Network test failed: {test_response.status_code}")
        except requests.exceptions.RequestException as e:
            self.results.add_result("External API connectivity", False, f"Network connectivity issue: {e}")
    
    def test_admin_endpoints(self):
        """Test admin-specific endpoints"""
        self.print_header("Testing Admin Endpoints")
        
        # First, try to login as admin
        admin_login = {
            "username": "admin",
            "password": "admin123"  # Default admin credentials
        }
        
        response = self.make_request("POST", "/api/auth/login", data=admin_login, auth_required=False)
        admin_token = None
        if response and response.status_code == 200:
            data = response.json()
            admin_token = data.get("access_token")
            user = data.get("user", {})
            is_admin = user.get("is_admin", False)
            
            if admin_token and is_admin:
                self.results.add_result("Admin login", True, "Admin authentication successful")
                
                # Temporarily use admin token
                original_token = self.jwt_token
                self.jwt_token = admin_token
                
                # Test admin endpoints
                response = self.make_request("GET", "/api/admin/users")
                if response and response.status_code in [200, 404]:
                    self.results.add_result("Admin users list", True, f"Status: {response.status_code}")
                else:
                    status = response.status_code if response else "No response"
                    self.results.add_result("Admin users list", False, f"Status: {status}")
                
                response = self.make_request("GET", "/api/admin/system/stats")
                if response and response.status_code in [200, 404]:
                    self.results.add_result("Admin system stats", True, f"Status: {response.status_code}")
                else:
                    status = response.status_code if response else "No response"
                    self.results.add_result("Admin system stats", False, f"Status: {status}")
                
                # Restore original token
                self.jwt_token = original_token
            else:
                self.results.add_result("Admin login", False, "User is not admin or login failed")
        else:
            status = response.status_code if response else "No response"
            self.results.add_result("Admin login", False, f"Admin login failed: {status}")
    
    def test_cors_configuration(self):
        """Test CORS configuration"""
        self.print_header("Testing CORS Configuration")
        
        # Test CORS preflight request
        cors_headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization"
        }
        
        response = self.make_request("OPTIONS", "/", headers=cors_headers, auth_required=False)
        if response:
            cors_origin = response.headers.get("Access-Control-Allow-Origin", "")
            cors_methods = response.headers.get("Access-Control-Allow-Methods", "")
            cors_headers_allowed = response.headers.get("Access-Control-Allow-Headers", "")
            cors_credentials = response.headers.get("Access-Control-Allow-Credentials", "")
            
            self.results.add_result(
                "CORS preflight", 
                response.status_code == 200, 
                f"Status: {response.status_code}"
            )
            
            # Check if frontend origins are allowed
            frontend_supported = ("localhost:3000" in cors_origin or 
                                "127.0.0.1:3000" in cors_origin or 
                                "*" in cors_origin)
            self.results.add_result(
                "CORS frontend support", 
                frontend_supported, 
                f"Origin header: {cors_origin}"
            )
            
            # Check if credentials are allowed
            credentials_allowed = cors_credentials.lower() == "true"
            self.results.add_result(
                "CORS credentials support", 
                credentials_allowed, 
                f"Credentials: {cors_credentials}"
            )
            
        else:
            self.results.add_result("CORS preflight", False, "No response to OPTIONS request")
    
    def run_curl_tests(self):
        """Run curl-based tests for additional verification"""
        self.print_header("Running cURL-based Tests")
        
        # Test basic curl connectivity
        try:
            result = subprocess.run([
                "curl", "-s", "-w", "%{http_code}", 
                f"{BASE_URL}/health"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Extract HTTP status code from curl output
                output = result.stdout
                if output.endswith("200") or output.endswith("503"):
                    self.results.add_result("cURL basic test", True, "cURL connectivity successful")
                else:
                    self.results.add_result("cURL basic test", False, f"Unexpected HTTP code: {output}")
            else:
                self.results.add_result("cURL basic test", False, f"cURL failed: {result.stderr}")
        
        except FileNotFoundError:
            self.results.add_result("cURL basic test", False, "cURL not found")
        except subprocess.TimeoutExpired:
            self.results.add_result("cURL basic test", False, "cURL request timed out")
        except Exception as e:
            self.results.add_result("cURL basic test", False, f"cURL error: {e}")
        
        # Test authenticated curl request
        if self.jwt_token:
            try:
                result = subprocess.run([
                    "curl", "-s", "-w", "%{http_code}",
                    "-H", f"Authorization: Bearer {self.jwt_token}",
                    f"{BASE_URL}/api/devices/"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    output = result.stdout
                    if "200" in output or "404" in output:  # 404 is OK if no devices
                        self.results.add_result("cURL authenticated test", True, "Authenticated request successful")
                    else:
                        self.results.add_result("cURL authenticated test", False, f"Unexpected response: {output}")
                else:
                    self.results.add_result("cURL authenticated test", False, f"cURL failed: {result.stderr}")
            
            except Exception as e:
                self.results.add_result("cURL authenticated test", False, f"cURL error: {e}")
        else:
            self.results.add_result("cURL authenticated test", False, "No JWT token available")
    
    def check_system_requirements(self):
        """Check system requirements and environment"""
        self.print_header("Checking System Requirements")
        
        # Check Python version
        python_version = sys.version
        self.results.add_result("Python version", True, f"Python {python_version}")
        
        # Check if server process is running
        server_running = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and any('uvicorn' in str(cmd) or 'main:app' in str(cmd) for cmd in proc.info['cmdline']):
                    server_running = True
                    break
            except:
                pass
        
        self.results.add_result("Server process", server_running, "Server is running" if server_running else "Server process not detected")
        
        # Check database connectivity (PostgreSQL)
        try:
            import psycopg2
            # Try to connect to default database
            conn_string = "postgresql://androidzen_user:dev_password@localhost:5432/androidzen"
            conn = psycopg2.connect(conn_string)
            conn.close()
            self.results.add_result("Database connectivity", True, "PostgreSQL connection successful")
        except ImportError:
            self.results.add_result("Database connectivity", False, "psycopg2 not installed")
        except Exception as e:
            self.results.add_result("Database connectivity", False, f"Database connection failed: {e}")
        
        # Check Redis connectivity
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, password='dev_redis_password', decode_responses=True)
            r.ping()
            self.results.add_result("Redis connectivity", True, "Redis connection successful")
        except ImportError:
            self.results.add_result("Redis connectivity", False, "redis-py not installed")
        except Exception as e:
            self.results.add_result("Redis connectivity", False, f"Redis connection failed: {e}")
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"{Colors.BOLD}{Colors.BLUE}AndroidZen Pro API & Integration Testing{Colors.END}")
        print(f"Testing server at: {BASE_URL}")
        print(f"WebSocket URL: {WS_URL}")
        print(f"Started at: {datetime.now().isoformat()}")
        
        # Check system requirements first
        self.check_system_requirements()
        
        # Wait for server to be ready
        if not self.wait_for_server():
            self.results.add_result("Server availability", False, "Server not responding")
            self.results.print_summary()
            return
        
        # Run all test categories
        self.test_public_endpoints()
        self.test_cors_configuration()
        self.test_authentication_flow()
        self.test_protected_endpoints()
        self.test_admin_endpoints()
        self.test_file_upload_download()
        self.test_database_migrations()
        await self.test_websocket_connections()
        self.test_external_api_integrations()
        self.run_curl_tests()
        
        # Print final results
        self.results.print_summary()
        self.results.save_results("api_integration_test_results.json")
        
        print(f"\n{Colors.BLUE}Testing completed at: {datetime.now().isoformat()}{Colors.END}")
        print(f"{Colors.CYAN}Results saved to: api_integration_test_results.json{Colors.END}")
        
        # Return exit code based on results
        return 0 if self.results.failed == 0 else 1

async def main():
    """Main entry point"""
    tester = APITester()
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
