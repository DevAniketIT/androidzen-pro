#!/usr/bin/env python3
"""
Test script to verify FastAPI backend server functionality
"""
import subprocess
import time
import requests
import sys
import threading
import os
import signal

def start_server():
    """Start the FastAPI server"""
    try:
        # Start server process
        cmd = ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give server time to start
        time.sleep(8)
        
        return process
    except Exception as e:
        print(f"Failed to start server: {e}")
        return None

def test_endpoints():
    """Test various API endpoints"""
    base_url = "http://localhost:8000"
    
    tests = [
        {
            "name": "Health Check",
            "endpoint": "/health",
            "expected_status": 200
        },
        {
            "name": "Root Endpoint",
            "endpoint": "/",
            "expected_status": 200
        },
        {
            "name": "API Documentation",
            "endpoint": "/docs",
            "expected_status": 200
        }
    ]
    
    print("🚀 Testing FastAPI Backend Server")
    print("=" * 50)
    
    for test in tests:
        try:
            url = f"{base_url}{test['endpoint']}"
            print(f"Testing {test['name']}: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == test['expected_status']:
                print(f"✅ {test['name']} - Status: {response.status_code}")
                
                if test['endpoint'] in ['/health', '/']:
                    try:
                        data = response.json()
                        print(f"   Response: {data}")
                    except:
                        print(f"   Response (text): {response.text[:100]}...")
                else:
                    print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
            else:
                print(f"❌ {test['name']} - Expected: {test['expected_status']}, Got: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {test['name']} - Connection refused (server not running)")
        except requests.exceptions.Timeout:
            print(f"❌ {test['name']} - Request timeout")
        except Exception as e:
            print(f"❌ {test['name']} - Error: {e}")
        
        print()
    
    # Test API routes (these may require auth, so we just check if they're registered)
    api_routes = [
        "/api/devices",
        "/api/storage", 
        "/api/settings",
        "/api/security",
        "/api/network"
    ]
    
    print("🔗 Testing API Route Registration")
    print("=" * 50)
    
    for route in api_routes:
        try:
            url = f"{base_url}{route}"
            response = requests.get(url, timeout=5)
            
            # For protected routes, we expect 401 (unauthorized) or 422 (validation error)
            # not 404 (not found), which would indicate the route isn't registered
            if response.status_code in [200, 401, 422, 403]:
                print(f"✅ {route} - Route is registered (Status: {response.status_code})")
            elif response.status_code == 404:
                print(f"❌ {route} - Route not found")
            else:
                print(f"⚠️  {route} - Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {route} - Error: {e}")
    
    print()
    
    # Test WebSocket endpoint availability
    print("🔌 Testing WebSocket Endpoint")
    print("=" * 50)
    try:
        # Just check if the WebSocket endpoint returns a proper error for HTTP request
        url = f"{base_url}/ws"
        response = requests.get(url, timeout=5)
        
        # WebSocket endpoints typically return 426 (Upgrade Required) for HTTP requests
        if response.status_code in [426, 400]:
            print(f"✅ /ws - WebSocket endpoint is available (Status: {response.status_code})")
        else:
            print(f"⚠️  /ws - Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ /ws - Error: {e}")

def main():
    print("Starting FastAPI Backend Server Test")
    print("=" * 50)
    
    # Start server
    print("Starting server...")
    server_process = start_server()
    
    if server_process is None:
        print("❌ Failed to start server")
        return
    
    try:
        # Test endpoints
        test_endpoints()
        
        print("\n🎉 Server testing completed!")
        print("📊 Server is running on http://localhost:8000")
        print("📖 API Documentation: http://localhost:8000/docs")
        
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    
    finally:
        # Cleanup - stop server
        if server_process:
            print("\n🛑 Stopping server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("✅ Server stopped")

if __name__ == "__main__":
    main()
