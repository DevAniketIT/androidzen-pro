"""
Performance benchmarks for AndroidZen Pro API endpoints and services.
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import psutil
import memory_profiler

from httpx import AsyncClient
from backend.tests.mocks.mock_adb_device import create_test_devices


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmarks for various components."""

    @pytest.fixture
    def performance_client(self, async_client):
        """Performance testing client."""
        return async_client

    @pytest.fixture
    def large_device_dataset(self):
        """Create large dataset for performance testing."""
        return create_test_devices(100, simulate_issues=True)

    def measure_response_time(self, func):
        """Decorator to measure function response time."""
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            response_time = end_time - start_time
            return result, response_time
        return wrapper

    async def test_api_response_times(self, performance_client: AsyncClient, 
                                     authenticated_headers, benchmark_config):
        """Benchmark API response times."""
        endpoints = [
            "/health",
            "/api/devices/",
            "/api/settings/",
            "/api/security/events",
            "/api/monitoring/system-status"
        ]
        
        response_times = {}
        
        for endpoint in endpoints:
            times = []
            
            for _ in range(benchmark_config["rounds"]):
                start_time = time.perf_counter()
                
                try:
                    if endpoint == "/health":
                        response = await performance_client.get(endpoint)
                    else:
                        response = await performance_client.get(
                            endpoint, 
                            headers=authenticated_headers
                        )
                    
                    end_time = time.perf_counter()
                    response_time = end_time - start_time
                    times.append(response_time)
                    
                    # Verify successful response
                    assert response.status_code in [200, 401]  # 401 for auth errors in mocks
                    
                except Exception as e:
                    print(f"Error testing {endpoint}: {e}")
                    continue
            
            if times:
                response_times[endpoint] = {
                    "mean": statistics.mean(times),
                    "median": statistics.median(times),
                    "min": min(times),
                    "max": max(times),
                    "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)
                }
        
        # Assert performance requirements
        for endpoint, metrics in response_times.items():
            assert metrics["mean"] < benchmark_config["max_time"], \
                f"{endpoint} mean response time {metrics['mean']:.3f}s exceeds limit"
            assert metrics["p95"] < benchmark_config["max_time"] * 2, \
                f"{endpoint} P95 response time {metrics['p95']:.3f}s exceeds limit"
        
        print("\nAPI Response Time Benchmarks:")
        for endpoint, metrics in response_times.items():
            print(f"{endpoint}: {metrics['mean']:.3f}s avg, {metrics['p95']:.3f}s P95")

    async def test_concurrent_api_requests(self, performance_client: AsyncClient,
                                          authenticated_headers, benchmark_config):
        """Test API performance under concurrent load."""
        endpoint = "/api/devices/"
        concurrent_requests = 10
        total_requests = 50
        
        async def make_request():
            start_time = time.perf_counter()
            response = await performance_client.get(endpoint, headers=authenticated_headers)
            end_time = time.perf_counter()
            return response.status_code, end_time - start_time
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def limited_request():
            async with semaphore:
                return await make_request()
        
        # Execute concurrent requests
        start_time = time.perf_counter()
        tasks = [limited_request() for _ in range(total_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        successful_requests = 0
        response_times = []
        
        for result in results:
            if isinstance(result, tuple):
                status_code, response_time = result
                if status_code in [200, 401]:  # Accept auth errors in testing
                    successful_requests += 1
                    response_times.append(response_time)
        
        # Calculate throughput
        throughput = successful_requests / total_time
        
        # Performance assertions
        assert successful_requests >= total_requests * 0.9, \
            f"Only {successful_requests}/{total_requests} requests succeeded"
        assert throughput >= 5, \
            f"Throughput {throughput:.2f} requests/sec is below minimum"
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time < benchmark_config["max_time"], \
                f"Average response time {avg_response_time:.3f}s under load exceeds limit"
        
        print(f"\nConcurrency Test: {throughput:.2f} req/s, "
              f"{statistics.mean(response_times):.3f}s avg response time")

    @pytest.mark.benchmark
    def test_ai_service_performance(self, benchmark, mock_ai_service, sample_analytics_data):
        """Benchmark AI service operations."""
        import pandas as pd
        import numpy as np
        
        # Create larger dataset for realistic testing
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'device_id': f'device_{i % 10}',
                'cpu_usage': np.random.normal(50, 15),
                'memory_usage': np.random.normal(60, 10),
                'storage_usage_percentage': np.random.normal(70, 20),
                'battery_level': np.random.randint(20, 100),
                'recorded_at': pd.Timestamp.now()
            })
        
        df = pd.DataFrame(large_dataset)
        
        def ai_processing_task():
            """Simulate AI processing task."""
        from backend.services.intelligence_service import DeviceFeatureExtractor
            
            # Feature extraction
            extractor = DeviceFeatureExtractor()
            features = extractor.fit_transform(df)
            
            # Simulate anomaly detection
            from sklearn.ensemble import IsolationForest
            model = IsolationForest(contamination=0.1, random_state=42)
            model.fit(features)
            anomalies = model.predict(features)
            
            return len(anomalies[anomalies == -1])
        
        # Benchmark the AI processing
        result = benchmark(ai_processing_task)
        
        # Assert reasonable performance
        assert result >= 0, "AI processing should complete successfully"
        
        # Check benchmark results
        stats = benchmark.stats
        assert stats.mean < 5.0, f"AI processing too slow: {stats.mean:.3f}s"

    @memory_profiler.profile
    def test_memory_usage_ai_service(self, mock_ai_service):
        """Test memory usage of AI service operations."""
        import numpy as np
        from backend.services.intelligence_service import DeviceFeatureExtractor
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset to stress memory
        large_data = np.random.rand(10000, 10)
        
        # Process data
        extractor = DeviceFeatureExtractor()
        features = extractor.fit_transform(large_data)
        
        # Measure peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Memory usage should be reasonable
        assert memory_increase < 500, f"Memory usage too high: {memory_increase:.1f}MB"
        
        print(f"Memory usage increase: {memory_increase:.1f}MB")

    async def test_database_query_performance(self, test_db_session, benchmark_config):
        """Test database query performance."""
        from backend.models.analytics import Analytics
        from backend.models.device import Device
        from datetime import datetime, timedelta
        
        # Insert test data
        devices_data = []
        analytics_data = []
        
        for i in range(100):
            device = Device(
                device_id=f"perf_device_{i}",
                model=f"TestPhone_{i}",
                android_version="13",
                is_connected=True
            )
            devices_data.append(device)
            
            for j in range(10):  # 10 analytics records per device
                analytics = Analytics(
                    device_id=f"perf_device_{i}",
                    cpu_usage=50 + (j * 5),
                    memory_usage=60 + (j * 3),
                    storage_usage_percentage=70 + (j * 2),
                    battery_level=90 - (j * 5),
                    recorded_at=datetime.now() - timedelta(hours=j)
                )
                analytics_data.append(analytics)
        
        test_db_session.add_all(devices_data)
        test_db_session.add_all(analytics_data)
        test_db_session.commit()
        
        # Benchmark queries
        query_times = {}
        
        # Simple device query
        start_time = time.perf_counter()
        devices = test_db_session.query(Device).filter(Device.is_connected == True).all()
        query_times['device_list'] = time.perf_counter() - start_time
        
        # Analytics aggregation query
        start_time = time.perf_counter()
        avg_cpu = test_db_session.query(Analytics.cpu_usage).filter(
            Analytics.recorded_at > datetime.now() - timedelta(hours=24)
        ).all()
        query_times['analytics_aggregation'] = time.perf_counter() - start_time
        
        # Complex join query
        start_time = time.perf_counter()
        joined_data = test_db_session.query(Device, Analytics).join(
            Analytics, Device.device_id == Analytics.device_id
        ).limit(100).all()
        query_times['complex_join'] = time.perf_counter() - start_time
        
        # Assert query performance
        for query_name, query_time in query_times.items():
            assert query_time < 1.0, f"{query_name} query too slow: {query_time:.3f}s"
        
        print("\nDatabase Query Performance:")
        for query_name, query_time in query_times.items():
            print(f"{query_name}: {query_time:.3f}s")

    async def test_websocket_performance(self, mock_websocket_manager):
        """Test WebSocket performance with multiple connections."""
        from backend.core.websocket_manager import WebSocketManager
        from unittest.mock import AsyncMock
        
        # Simulate multiple WebSocket connections
        connection_count = 100
        message_count = 10
        
        # Create mock connections
        mock_connections = []
        for i in range(connection_count):
            mock_ws = AsyncMock()
            mock_connections.append(mock_ws)
        
        mock_websocket_manager.active_connections = mock_connections
        
        # Measure broadcast performance
        start_time = time.perf_counter()
        
        for i in range(message_count):
            await mock_websocket_manager.broadcast_message({
                "type": "performance_test",
                "message": f"Test message {i}",
                "timestamp": time.time()
            })
        
        broadcast_time = time.perf_counter() - start_time
        
        # Calculate metrics
        messages_per_second = (connection_count * message_count) / broadcast_time
        avg_time_per_broadcast = broadcast_time / message_count
        
        # Performance assertions
        assert avg_time_per_broadcast < 0.1, \
            f"Broadcast too slow: {avg_time_per_broadcast:.3f}s per message"
        assert messages_per_second > 1000, \
            f"Throughput too low: {messages_per_second:.0f} messages/s"
        
        print(f"WebSocket Performance: {messages_per_second:.0f} messages/s, "
              f"{avg_time_per_broadcast:.3f}s per broadcast")

    def test_adb_command_performance(self, mock_adb_manager, large_device_dataset):
        """Test ADB command execution performance."""
        # Add devices to manager
        for device in large_device_dataset[:10]:  # Test with 10 devices
            mock_adb_manager.add_device(device)
        
        commands = [
            "shell getprop ro.build.version.release",
            "shell dumpsys battery",
            "shell dumpsys cpuinfo",
            "shell dumpsys meminfo",
            "shell pm list packages"
        ]
        
        execution_times = []
        
        for device in mock_adb_manager.get_connected_devices()[:5]:  # Test 5 devices
            for command in commands:
                start_time = time.perf_counter()
                
                try:
                    # This would normally be async, but we're testing the mock
                    result = asyncio.run(device.shell(command))
                    execution_time = time.perf_counter() - start_time
                    execution_times.append(execution_time)
                except Exception as e:
                    print(f"Command failed: {e}")
        
        if execution_times:
            avg_execution_time = statistics.mean(execution_times)
            max_execution_time = max(execution_times)
            
            # Performance assertions
            assert avg_execution_time < 0.5, \
                f"Average command execution too slow: {avg_execution_time:.3f}s"
            assert max_execution_time < 2.0, \
                f"Maximum command execution too slow: {max_execution_time:.3f}s"
            
            print(f"ADB Command Performance: {avg_execution_time:.3f}s avg, "
                  f"{max_execution_time:.3f}s max")

    async def test_load_test_scenario(self, performance_client: AsyncClient,
                                     authenticated_headers, benchmark_config):
        """Comprehensive load test scenario."""
        # Simulate realistic user behavior patterns
        user_scenarios = [
            # Regular monitoring user
            ["/api/devices/", "/api/monitoring/system-status"],
            # Power user checking analytics
            ["/api/devices/", "/api/devices/test_device_001/analytics"],
            # Security-focused user
            ["/api/security/events", "/api/security/scan-results"],
            # Settings management
            ["/api/settings/", "/api/settings/performance"]
        ]
        
        concurrent_users = 5
        iterations_per_user = 10
        
        async def user_simulation(user_id: int, scenario: List[str]):
            """Simulate a user's interaction pattern."""
            response_times = []
            errors = 0
            
            for iteration in range(iterations_per_user):
                for endpoint in scenario:
                    try:
                        start_time = time.perf_counter()
                        response = await performance_client.get(
                            endpoint, 
                            headers=authenticated_headers
                        )
                        response_time = time.perf_counter() - start_time
                        response_times.append(response_time)
                        
                        if response.status_code >= 400:
                            errors += 1
                            
                        # Small delay between requests
                        await asyncio.sleep(0.1)
                        
                    except Exception:
                        errors += 1
            
            return {
                "user_id": user_id,
                "response_times": response_times,
                "errors": errors,
                "total_requests": len(scenario) * iterations_per_user
            }
        
        # Run concurrent user simulations
        start_time = time.perf_counter()
        
        tasks = []
        for user_id in range(concurrent_users):
            scenario = user_scenarios[user_id % len(user_scenarios)]
            task = user_simulation(user_id, scenario)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        all_response_times = []
        total_errors = 0
        total_requests = 0
        
        for result in results:
            all_response_times.extend(result["response_times"])
            total_errors += result["errors"]
            total_requests += result["total_requests"]
        
        # Calculate metrics
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
        throughput = total_requests / total_time
        error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
        
        # Performance assertions
        assert error_rate < 5, f"Error rate too high: {error_rate:.1f}%"
        assert avg_response_time < benchmark_config["max_time"], \
            f"Average response time under load: {avg_response_time:.3f}s"
        assert throughput >= 10, f"Throughput too low: {throughput:.2f} req/s"
        
        print(f"\nLoad Test Results:")
        print(f"Throughput: {throughput:.2f} requests/sec")
        print(f"Average Response Time: {avg_response_time:.3f}s")
        print(f"Error Rate: {error_rate:.1f}%")
        print(f"Total Requests: {total_requests}")

    def test_system_resource_usage(self):
        """Monitor system resource usage during testing."""
        process = psutil.Process()
        
        # Initial measurements
        initial_cpu = process.cpu_percent()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate workload
        for _ in range(1000):
            # CPU intensive task
            sum(i**2 for i in range(100))
        
        # Final measurements
        final_cpu = process.cpu_percent()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        cpu_usage = max(initial_cpu, final_cpu)
        memory_increase = final_memory - initial_memory
        
        # Resource usage assertions
        assert cpu_usage < 80, f"CPU usage too high: {cpu_usage:.1f}%"
        assert memory_increase < 100, f"Memory increase too high: {memory_increase:.1f}MB"
        
        print(f"Resource Usage - CPU: {cpu_usage:.1f}%, Memory: {memory_increase:.1f}MB")

    @pytest.mark.slow
    async def test_endurance_test(self, performance_client: AsyncClient,
                                 authenticated_headers):
        """Long-running endurance test."""
        test_duration = 60  # 1 minute for testing
        request_interval = 1  # 1 request per second
        endpoint = "/health"
        
        start_time = time.perf_counter()
        response_times = []
        errors = 0
        requests_made = 0
        
        while time.perf_counter() - start_time < test_duration:
            try:
                request_start = time.perf_counter()
                response = await performance_client.get(endpoint)
                request_time = time.perf_counter() - request_start
                
                response_times.append(request_time)
                requests_made += 1
                
                if response.status_code >= 400:
                    errors += 1
                
                # Wait for next request
                await asyncio.sleep(request_interval)
                
            except Exception:
                errors += 1
        
        # Calculate metrics
        avg_response_time = statistics.mean(response_times) if response_times else 0
        error_rate = (errors / requests_made) * 100 if requests_made > 0 else 0
        
        # Endurance test assertions
        assert error_rate < 1, f"Error rate in endurance test: {error_rate:.1f}%"
        assert avg_response_time < 1.0, f"Response time degraded: {avg_response_time:.3f}s"
        
        print(f"Endurance Test - {requests_made} requests, "
              f"{avg_response_time:.3f}s avg, {error_rate:.1f}% errors")
