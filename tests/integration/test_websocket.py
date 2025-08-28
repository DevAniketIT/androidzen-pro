#!/usr/bin/env python3
"""
WebSocket Connection Testing for AndroidZen Pro
Tests WebSocket functionality, real-time monitoring, and bidirectional communication.

This script specifically tests WebSocket connections as part of Step 10: Point 12.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
WS_URL = "ws://localhost:8000/ws"
TEST_TIMEOUT = 10

class Colors:
    """ANSI color codes for colored terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class WebSocketTester:
    """WebSocket testing class"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}")
        print(f" {title}")
        print(f"{'='*60}{Colors.END}")
    
    def print_result(self, test_name: str, success: bool, details: str = ""):
        """Print test result with color coding"""
        if success:
            print(f"{Colors.GREEN}✅ PASS{Colors.END} {test_name}")
            self.passed_tests += 1
        else:
            print(f"{Colors.RED}❌ FAIL{Colors.END} {test_name}")
            self.failed_tests += 1
        
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    async def test_basic_connection(self):
        """Test basic WebSocket connection"""
        self.print_header("Testing Basic WebSocket Connection")
        
        try:
            async with websockets.connect(WS_URL, timeout=TEST_TIMEOUT) as websocket:
                self.print_result("WebSocket connection", True, "Successfully connected to WebSocket")
                
                # Test receiving welcome/connection message
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    
                    if data.get("type") == "device_connected":
                        self.print_result(
                            "Connection confirmation message", 
                            True, 
                            f"Received: {data.get('type')} - {data.get('data', {}).get('message', 'N/A')}"
                        )
                    else:
                        self.print_result(
                            "Connection confirmation message", 
                            True, 
                            f"Received message type: {data.get('type')}"
                        )
                
                except asyncio.TimeoutError:
                    self.print_result(
                        "Connection confirmation message", 
                        False, 
                        "No welcome message received within timeout"
                    )
                except json.JSONDecodeError:
                    self.print_result(
                        "Connection confirmation message", 
                        False, 
                        "Invalid JSON in welcome message"
                    )
                
        except websockets.exceptions.ConnectionClosed:
            self.print_result("WebSocket connection", False, "Connection closed unexpectedly")
        except websockets.exceptions.InvalidURI:
            self.print_result("WebSocket connection", False, "Invalid WebSocket URI")
        except asyncio.TimeoutError:
            self.print_result("WebSocket connection", False, "Connection timeout")
        except Exception as e:
            self.print_result("WebSocket connection", False, f"Connection error: {e}")
    
    async def test_authenticated_connection(self):
        """Test WebSocket connection with authentication token"""
        self.print_header("Testing Authenticated WebSocket Connection")
        
        # For this test, we'll use a mock token since we don't have real authentication here
        # In a real scenario, you'd get this from the login API
        test_token = "test_jwt_token_123"
        auth_ws_url = f"{WS_URL}?token={test_token}&client_id=test_client_auth"
        
        try:
            async with websockets.connect(auth_ws_url, timeout=TEST_TIMEOUT) as websocket:
                self.print_result(
                    "Authenticated WebSocket connection", 
                    True, 
                    "Successfully connected with token parameter"
                )
                
                # Wait for authentication response
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    
                    self.print_result(
                        "Authentication response", 
                        True, 
                        f"Received: {data.get('type')} message"
                    )
                
                except asyncio.TimeoutError:
                    self.print_result(
                        "Authentication response", 
                        False, 
                        "No authentication response received"
                    )
        
        except Exception as e:
            self.print_result("Authenticated WebSocket connection", False, f"Error: {e}")
    
    async def test_heartbeat_mechanism(self):
        """Test WebSocket heartbeat functionality"""
        self.print_header("Testing WebSocket Heartbeat")
        
        try:
            async with websockets.connect(WS_URL, timeout=TEST_TIMEOUT) as websocket:
                
                # Skip initial connection message
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2)
                except:
                    pass
                
                # Send heartbeat message
                heartbeat_msg = {
                    "type": "heartbeat",
                    "data": {"timestamp": datetime.now().isoformat()}
                }
                
                await websocket.send(json.dumps(heartbeat_msg))
                self.print_result("Heartbeat message sent", True, "Sent heartbeat to server")
                
                # Wait for heartbeat response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "heartbeat":
                        self.print_result(
                            "Heartbeat response", 
                            True, 
                            f"Received heartbeat response: {response_data.get('data', {}).get('status', 'unknown')}"
                        )
                    else:
                        self.print_result(
                            "Heartbeat response", 
                            False, 
                            f"Unexpected response type: {response_data.get('type')}"
                        )
                
                except asyncio.TimeoutError:
                    self.print_result("Heartbeat response", False, "No heartbeat response received")
                except json.JSONDecodeError:
                    self.print_result("Heartbeat response", False, "Invalid JSON in response")
        
        except Exception as e:
            self.print_result("Heartbeat mechanism", False, f"Error: {e}")
    
    async def test_subscription_mechanism(self):
        """Test WebSocket subscription functionality"""
        self.print_header("Testing WebSocket Subscriptions")
        
        try:
            async with websockets.connect(WS_URL, timeout=TEST_TIMEOUT) as websocket:
                
                # Skip initial connection message
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2)
                except:
                    pass
                
                # Test subscription to device updates
                subscription_msg = {
                    "type": "subscription",
                    "data": {"topic": "device_updates"}
                }
                
                await websocket.send(json.dumps(subscription_msg))
                self.print_result("Subscription request sent", True, "Sent subscription for device_updates")
                
                # Wait for subscription confirmation
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "subscription":
                        topic = response_data.get("data", {}).get("topic")
                        status = response_data.get("data", {}).get("status")
                        
                        self.print_result(
                            "Subscription confirmation", 
                            status == "subscribed", 
                            f"Topic: {topic}, Status: {status}"
                        )
                    else:
                        self.print_result(
                            "Subscription confirmation", 
                            False, 
                            f"Unexpected response: {response_data.get('type')}"
                        )
                
                except asyncio.TimeoutError:
                    self.print_result("Subscription confirmation", False, "No subscription confirmation received")
                
                # Test unsubscription
                unsubscription_msg = {
                    "type": "unsubscription", 
                    "data": {"topic": "device_updates"}
                }
                
                await websocket.send(json.dumps(unsubscription_msg))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "unsubscription":
                        status = response_data.get("data", {}).get("status")
                        self.print_result(
                            "Unsubscription confirmation", 
                            status == "unsubscribed", 
                            f"Status: {status}"
                        )
                    else:
                        self.print_result("Unsubscription confirmation", False, "No unsubscription response")
                
                except asyncio.TimeoutError:
                    self.print_result("Unsubscription confirmation", False, "No unsubscription response")
        
        except Exception as e:
            self.print_result("Subscription mechanism", False, f"Error: {e}")
    
    async def test_message_handling(self):
        """Test various WebSocket message types"""
        self.print_header("Testing Message Handling")
        
        try:
            async with websockets.connect(WS_URL, timeout=TEST_TIMEOUT) as websocket:
                
                # Skip initial connection message
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2)
                except:
                    pass
                
                # Test sending invalid JSON
                try:
                    await websocket.send("invalid json message")
                    
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "error":
                        self.print_result(
                            "Invalid JSON handling", 
                            True, 
                            f"Server correctly handled invalid JSON: {response_data.get('data', {}).get('message', 'N/A')}"
                        )
                    else:
                        self.print_result("Invalid JSON handling", False, "Server did not send error for invalid JSON")
                
                except asyncio.TimeoutError:
                    self.print_result("Invalid JSON handling", False, "No error response for invalid JSON")
                except:
                    self.print_result("Invalid JSON handling", False, "Error testing invalid JSON")
                
                # Test sending unknown message type
                unknown_msg = {
                    "type": "unknown_message_type",
                    "data": {"test": "data"}
                }
                
                try:
                    await websocket.send(json.dumps(unknown_msg))
                    
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "error":
                        self.print_result(
                            "Unknown message type handling", 
                            True, 
                            "Server correctly handled unknown message type"
                        )
                    else:
                        self.print_result(
                            "Unknown message type handling", 
                            False, 
                            f"Unexpected response: {response_data.get('type')}"
                        )
                
                except asyncio.TimeoutError:
                    self.print_result("Unknown message type handling", False, "No response to unknown message")
        
        except Exception as e:
            self.print_result("Message handling", False, f"Error: {e}")
    
    async def test_multiple_connections(self):
        """Test multiple simultaneous WebSocket connections"""
        self.print_header("Testing Multiple Connections")
        
        try:
            # Create multiple connections
            connections = []
            client_ids = []
            
            for i in range(3):
                client_id = f"test_client_{i}"
                client_ids.append(client_id)
                ws_url = f"{WS_URL}?client_id={client_id}"
                
                try:
                    websocket = await websockets.connect(ws_url, timeout=TEST_TIMEOUT)
                    connections.append(websocket)
                except Exception as e:
                    self.print_result(f"Connection {i+1}", False, f"Failed to connect: {e}")
                    continue
            
            if len(connections) > 0:
                self.print_result(
                    "Multiple connections", 
                    len(connections) == 3, 
                    f"Successfully established {len(connections)}/3 connections"
                )
                
                # Test that all connections can receive their welcome messages
                welcome_count = 0
                for i, ws in enumerate(connections):
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=3)
                        data = json.loads(message)
                        if data.get("type") == "device_connected":
                            welcome_count += 1
                    except:
                        pass
                
                self.print_result(
                    "Multiple connection messages", 
                    welcome_count == len(connections), 
                    f"Received welcome messages from {welcome_count}/{len(connections)} connections"
                )
                
                # Close all connections
                for ws in connections:
                    await ws.close()
                
                self.print_result("Connection cleanup", True, "All connections closed successfully")
            else:
                self.print_result("Multiple connections", False, "Could not establish any connections")
        
        except Exception as e:
            self.print_result("Multiple connections", False, f"Error: {e}")
    
    async def test_connection_persistence(self):
        """Test WebSocket connection persistence and reconnection"""
        self.print_header("Testing Connection Persistence")
        
        try:
            # Test normal connection duration
            async with websockets.connect(WS_URL, timeout=TEST_TIMEOUT) as websocket:
                
                # Skip initial message
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2)
                except:
                    pass
                
                # Send periodic heartbeats to keep connection alive
                heartbeat_count = 0
                for i in range(3):
                    heartbeat_msg = {
                        "type": "heartbeat",
                        "data": {"sequence": i + 1}
                    }
                    
                    await websocket.send(json.dumps(heartbeat_msg))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3)
                        response_data = json.loads(response)
                        if response_data.get("type") == "heartbeat":
                            heartbeat_count += 1
                    except:
                        pass
                    
                    # Wait between heartbeats
                    await asyncio.sleep(1)
                
                self.print_result(
                    "Connection persistence", 
                    heartbeat_count >= 2, 
                    f"Maintained connection through {heartbeat_count}/3 heartbeats"
                )
        
        except Exception as e:
            self.print_result("Connection persistence", False, f"Error: {e}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = self.passed_tests + self.failed_tests
        
        print(f"\n{Colors.BOLD}WebSocket Test Summary:{Colors.END}")
        print(f"Total tests: {total_tests}")
        print(f"{Colors.GREEN}Passed: {self.passed_tests}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed_tests}{Colors.END}")
        
        if self.failed_tests > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return self.failed_tests == 0
    
    async def run_all_tests(self):
        """Run all WebSocket tests"""
        print(f"{Colors.BLUE}{Colors.BOLD}AndroidZen Pro WebSocket Testing{Colors.END}")
        print(f"WebSocket URL: {WS_URL}")
        print(f"Started at: {datetime.now().isoformat()}")
        
        # Run all test categories
        await self.test_basic_connection()
        await self.test_authenticated_connection()
        await self.test_heartbeat_mechanism()
        await self.test_subscription_mechanism()
        await self.test_message_handling()
        await self.test_multiple_connections()
        await self.test_connection_persistence()
        
        # Print final results
        success = self.print_summary()
        
        print(f"\n{Colors.BLUE}WebSocket testing completed at: {datetime.now().isoformat()}{Colors.END}")
        
        return 0 if success else 1

async def main():
    """Main entry point"""
    tester = WebSocketTester()
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
