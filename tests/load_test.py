"""
Load Testing Suite using Locust

This module provides comprehensive load testing scenarios for the application,
including user behavior simulation, stress testing, and performance benchmarking.

Usage:
    # Basic load test
    locust -f tests/load_test.py --host=http://localhost:8000

    # Web UI mode
    locust -f tests/load_test.py --host=http://localhost:8000 --web-host=127.0.0.1 --web-port=8089

    # Headless mode with specific parameters
    locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=300s --headless

    # Distributed testing
    # Master node:
    locust -f tests/load_test.py --master --host=http://localhost:8000
    # Worker nodes:
    locust -f tests/load_test.py --worker --master-host=192.168.1.100
"""

import json
import random
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

from locust import HttpUser, TaskSet, task, between, events
from locust.runners import MasterRunner, WorkerRunner


# Configuration
class LoadTestConfig:
    """Configuration class for load testing parameters"""
    
    # API Endpoints
    ENDPOINTS = {
        'health': '/health',
        'api_health': '/api/health',
        'login': '/api/auth/login',
        'register': '/api/auth/register',
        'profile': '/api/users/profile',
        'products': '/api/products',
        'product_detail': '/api/products/{product_id}',
        'cart': '/api/cart',
        'cart_add': '/api/cart/add',
        'orders': '/api/orders',
        'order_create': '/api/orders',
        'search': '/api/search',
        'categories': '/api/categories',
        'static_css': '/static/css/main.css',
        'static_js': '/static/js/bundle.js',
        'static_images': '/static/images/logo.png'
    }
    
    # Test Data
    TEST_USERS = [
        {'email': f'user{i}@test.com', 'password': 'testpass123'} 
        for i in range(1, 101)
    ]
    
    PRODUCT_IDS = list(range(1, 201))  # Assuming products with IDs 1-200
    SEARCH_TERMS = [
        'laptop', 'phone', 'headphones', 'camera', 'tablet',
        'keyboard', 'mouse', 'monitor', 'speaker', 'charger'
    ]
    
    # Performance thresholds (in milliseconds)
    THRESHOLDS = {
        'api_fast': 200,      # Fast API responses (search, health checks)
        'api_normal': 500,    # Normal API responses (CRUD operations)
        'api_slow': 1000,     # Slow API responses (complex operations)
        'static': 100,        # Static file serving
        'auth': 800,          # Authentication operations
    }


class PerformanceMetrics:
    """Custom metrics collection for performance analysis"""
    
    def __init__(self):
        self.custom_metrics = {}
        self.response_times = []
        self.error_counts = {}
        
    def record_response(self, name: str, response_time: float, success: bool):
        """Record response time and success rate"""
        if name not in self.custom_metrics:
            self.custom_metrics[name] = {
                'response_times': [],
                'success_count': 0,
                'error_count': 0
            }
        
        self.custom_metrics[name]['response_times'].append(response_time)
        if success:
            self.custom_metrics[name]['success_count'] += 1
        else:
            self.custom_metrics[name]['error_count'] += 1
    
    def get_percentile(self, response_times: List[float], percentile: float) -> float:
        """Calculate response time percentile"""
        if not response_times:
            return 0
        sorted_times = sorted(response_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        stats = {}
        for name, metrics in self.custom_metrics.items():
            response_times = metrics['response_times']
            if response_times:
                stats[name] = {
                    'count': len(response_times),
                    'avg': sum(response_times) / len(response_times),
                    'min': min(response_times),
                    'max': max(response_times),
                    'p50': self.get_percentile(response_times, 50),
                    'p95': self.get_percentile(response_times, 95),
                    'p99': self.get_percentile(response_times, 99),
                    'success_rate': metrics['success_count'] / (metrics['success_count'] + metrics['error_count']) * 100
                }
        return stats


# Global metrics instance
performance_metrics = PerformanceMetrics()


class BaseBehavior(TaskSet):
    """Base behavior class with common utilities"""
    
    def on_start(self):
        """Initialize user session"""
        self.user_data = random.choice(LoadTestConfig.TEST_USERS)
        self.auth_token = None
        self.user_id = None
        
    def authenticate(self) -> bool:
        """Authenticate user and store token"""
        with self.client.post(
            LoadTestConfig.ENDPOINTS['login'],
            json=self.user_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token')
                self.user_id = data.get('user_id')
                return True
            else:
                response.failure(f"Login failed: {response.text}")
                return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if self.auth_token:
            return {'Authorization': f'Bearer {self.auth_token}'}
        return {}
    
    def make_authenticated_request(self, method: str, url: str, **kwargs):
        """Make authenticated API request"""
        headers = kwargs.get('headers', {})
        headers.update(self.get_auth_headers())
        kwargs['headers'] = headers
        return getattr(self.client, method.lower())(url, **kwargs)


class HealthCheckBehavior(BaseBehavior):
    """Health check and monitoring endpoints behavior"""
    
    @task(10)
    def health_check(self):
        """Test application health endpoint"""
        start_time = time.time()
        with self.client.get(LoadTestConfig.ENDPOINTS['health'], catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
            
            performance_metrics.record_response('health_check', response_time, success)
    
    @task(5)
    def api_health_check(self):
        """Test API health endpoint"""
        start_time = time.time()
        with self.client.get(LoadTestConfig.ENDPOINTS['api_health'], catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success and response_time < LoadTestConfig.THRESHOLDS['api_fast']:
                response.success()
            else:
                response.failure(f"API health check slow or failed: {response_time}ms")
            
            performance_metrics.record_response('api_health_check', response_time, success)


class StaticAssetBehavior(BaseBehavior):
    """Static asset loading behavior"""
    
    @task(20)
    def load_css(self):
        """Load CSS assets"""
        self._load_static_asset('css', LoadTestConfig.ENDPOINTS['static_css'])
    
    @task(15)
    def load_js(self):
        """Load JavaScript assets"""
        self._load_static_asset('js', LoadTestConfig.ENDPOINTS['static_js'])
    
    @task(10)
    def load_images(self):
        """Load image assets"""
        self._load_static_asset('images', LoadTestConfig.ENDPOINTS['static_images'])
    
    def _load_static_asset(self, asset_type: str, url: str):
        """Load static asset and check performance"""
        start_time = time.time()
        with self.client.get(url, catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success and response_time < LoadTestConfig.THRESHOLDS['static']:
                response.success()
            else:
                response.failure(f"Static asset {asset_type} slow or failed: {response_time}ms")
            
            performance_metrics.record_response(f'static_{asset_type}', response_time, success)


class AuthenticationBehavior(BaseBehavior):
    """User authentication behavior"""
    
    def on_start(self):
        super().on_start()
        # 70% of users authenticate
        if random.random() < 0.7:
            self.authenticate()
    
    @task(5)
    def login(self):
        """Test user login"""
        if self.auth_token:
            return  # Already authenticated
        
        start_time = time.time()
        with self.client.post(
            LoadTestConfig.ENDPOINTS['login'],
            json=self.user_data,
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success and response_time < LoadTestConfig.THRESHOLDS['auth']:
                self.auth_token = response.json().get('token')
                self.user_id = response.json().get('user_id')
                response.success()
            else:
                response.failure(f"Login slow or failed: {response_time}ms")
            
            performance_metrics.record_response('login', response_time, success)
    
    @task(2)
    def register(self):
        """Test user registration with random data"""
        random_user = {
            'email': f'test{random.randint(10000, 99999)}@example.com',
            'password': 'testpass123',
            'first_name': f'Test{random.randint(1, 1000)}',
            'last_name': 'User'
        }
        
        start_time = time.time()
        with self.client.post(
            LoadTestConfig.ENDPOINTS['register'],
            json=random_user,
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code in [200, 201]
            
            if success and response_time < LoadTestConfig.THRESHOLDS['auth']:
                response.success()
            else:
                response.failure(f"Registration slow or failed: {response_time}ms")
            
            performance_metrics.record_response('register', response_time, success)


class EcommerceBehavior(BaseBehavior):
    """E-commerce specific user behavior"""
    
    def on_start(self):
        super().on_start()
        if not self.auth_token and random.random() < 0.6:
            self.authenticate()
    
    @task(30)
    def browse_products(self):
        """Browse product listings"""
        start_time = time.time()
        params = {
            'page': random.randint(1, 10),
            'limit': random.choice([10, 20, 50])
        }
        
        with self.client.get(
            LoadTestConfig.ENDPOINTS['products'],
            params=params,
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success and response_time < LoadTestConfig.THRESHOLDS['api_normal']:
                response.success()
            else:
                response.failure(f"Product browsing slow or failed: {response_time}ms")
            
            performance_metrics.record_response('browse_products', response_time, success)
    
    @task(25)
    def view_product_detail(self):
        """View individual product details"""
        product_id = random.choice(LoadTestConfig.PRODUCT_IDS)
        url = LoadTestConfig.ENDPOINTS['product_detail'].format(product_id=product_id)
        
        start_time = time.time()
        with self.client.get(url, catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success and response_time < LoadTestConfig.THRESHOLDS['api_normal']:
                response.success()
            else:
                response.failure(f"Product detail slow or failed: {response_time}ms")
            
            performance_metrics.record_response('product_detail', response_time, success)
    
    @task(20)
    def search_products(self):
        """Search for products"""
        search_term = random.choice(LoadTestConfig.SEARCH_TERMS)
        params = {'q': search_term}
        
        start_time = time.time()
        with self.client.get(
            LoadTestConfig.ENDPOINTS['search'],
            params=params,
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success and response_time < LoadTestConfig.THRESHOLDS['api_fast']:
                response.success()
            else:
                response.failure(f"Search slow or failed: {response_time}ms")
            
            performance_metrics.record_response('search', response_time, success)
    
    @task(10)
    def add_to_cart(self):
        """Add items to shopping cart"""
        if not self.auth_token:
            return
        
        product_id = random.choice(LoadTestConfig.PRODUCT_IDS)
        cart_data = {
            'product_id': product_id,
            'quantity': random.randint(1, 3)
        }
        
        start_time = time.time()
        with self.make_authenticated_request(
            'POST',
            LoadTestConfig.ENDPOINTS['cart_add'],
            json=cart_data,
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code in [200, 201]
            
            if success and response_time < LoadTestConfig.THRESHOLDS['api_normal']:
                response.success()
            else:
                response.failure(f"Add to cart slow or failed: {response_time}ms")
            
            performance_metrics.record_response('add_to_cart', response_time, success)
    
    @task(8)
    def view_cart(self):
        """View shopping cart"""
        if not self.auth_token:
            return
        
        start_time = time.time()
        with self.make_authenticated_request(
            'GET',
            LoadTestConfig.ENDPOINTS['cart'],
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code == 200
            
            if success and response_time < LoadTestConfig.THRESHOLDS['api_fast']:
                response.success()
            else:
                response.failure(f"View cart slow or failed: {response_time}ms")
            
            performance_metrics.record_response('view_cart', response_time, success)
    
    @task(5)
    def create_order(self):
        """Create a new order"""
        if not self.auth_token:
            return
        
        order_data = {
            'items': [
                {
                    'product_id': random.choice(LoadTestConfig.PRODUCT_IDS),
                    'quantity': random.randint(1, 2),
                    'price': random.uniform(10.0, 100.0)
                }
                for _ in range(random.randint(1, 3))
            ],
            'shipping_address': {
                'street': '123 Test St',
                'city': 'Test City',
                'zip_code': '12345'
            }
        }
        
        start_time = time.time()
        with self.make_authenticated_request(
            'POST',
            LoadTestConfig.ENDPOINTS['order_create'],
            json=order_data,
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            success = response.status_code in [200, 201]
            
            if success and response_time < LoadTestConfig.THRESHOLDS['api_slow']:
                response.success()
            else:
                response.failure(f"Create order slow or failed: {response_time}ms")
            
            performance_metrics.record_response('create_order', response_time, success)


class RegularUser(HttpUser):
    """Regular user with mixed behavior patterns"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    weight = 3
    
    tasks = {
        HealthCheckBehavior: 1,
        StaticAssetBehavior: 2,
        AuthenticationBehavior: 1,
        EcommerceBehavior: 6
    }


class HeavyUser(HttpUser):
    """Heavy user with intensive browsing behavior"""
    
    wait_time = between(0.5, 2)  # Faster interactions
    weight = 1
    
    tasks = {
        EcommerceBehavior: 8,
        StaticAssetBehavior: 2
    }


class APIUser(HttpUser):
    """API-focused user for backend testing"""
    
    wait_time = between(0.1, 1)  # Very fast API calls
    weight = 1
    
    tasks = {
        HealthCheckBehavior: 2,
        AuthenticationBehavior: 1,
        EcommerceBehavior: 7
    }


class StressTestUser(HttpUser):
    """Stress test user with minimal wait time"""
    
    wait_time = between(0, 0.5)  # Aggressive load
    weight = 0  # Only used in stress tests
    
    tasks = {
        EcommerceBehavior: 10
    }


# Event handlers for custom metrics and reporting
@events.request.add_listener
def request_handler(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Custom request handler for detailed metrics"""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate performance report at test end"""
    stats = performance_metrics.get_stats()
    
    print("\n" + "="*80)
    print("PERFORMANCE REPORT")
    print("="*80)
    
    for endpoint, metrics in stats.items():
        print(f"\n{endpoint.upper()}:")
        print(f"  Count: {metrics['count']}")
        print(f"  Average: {metrics['avg']:.2f}ms")
        print(f"  Min/Max: {metrics['min']:.2f}ms / {metrics['max']:.2f}ms")
        print(f"  P50/P95/P99: {metrics['p50']:.2f}ms / {metrics['p95']:.2f}ms / {metrics['p99']:.2f}ms")
        print(f"  Success Rate: {metrics['success_rate']:.2f}%")
        
        # Performance threshold validation
        if endpoint in ['health_check', 'api_health_check', 'search']:
            threshold = LoadTestConfig.THRESHOLDS['api_fast']
        elif endpoint.startswith('static_'):
            threshold = LoadTestConfig.THRESHOLDS['static']
        elif endpoint in ['login', 'register']:
            threshold = LoadTestConfig.THRESHOLDS['auth']
        elif endpoint == 'create_order':
            threshold = LoadTestConfig.THRESHOLDS['api_slow']
        else:
            threshold = LoadTestConfig.THRESHOLDS['api_normal']
        
        if metrics['p95'] > threshold:
            print(f"  ⚠️  P95 exceeds threshold ({threshold}ms)")
        else:
            print(f"  ✅ P95 within threshold ({threshold}ms)")
    
    print("\n" + "="*80)
    
    # Save detailed report
    report_data = {
        'timestamp': time.time(),
        'test_duration': getattr(environment, 'test_duration', 0),
        'total_users': getattr(environment, 'user_count', 0),
        'performance_metrics': stats,
        'thresholds': LoadTestConfig.THRESHOLDS
    }
    
    with open('load_test_report.json', 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print("Detailed report saved to: load_test_report.json")


# Performance test scenarios
class PerformanceTestScenarios:
    """Collection of predefined test scenarios"""
    
    @staticmethod
    def smoke_test():
        """
        Smoke test scenario - minimal load to verify basic functionality
        
        Usage:
            locust -f tests/load_test.py --users=10 --spawn-rate=2 --run-time=60s --headless
        """
        pass
    
    @staticmethod
    def load_test():
        """
        Standard load test - expected production load
        
        Usage:
            locust -f tests/load_test.py --users=100 --spawn-rate=10 --run-time=300s --headless
        """
        pass
    
    @staticmethod
    def stress_test():
        """
        Stress test - beyond expected capacity
        
        Usage:
            locust -f tests/load_test.py --users=500 --spawn-rate=25 --run-time=600s --headless
        """
        pass
    
    @staticmethod
    def spike_test():
        """
        Spike test - sudden load increase
        
        Usage:
            locust -f tests/load_test.py --users=200 --spawn-rate=100 --run-time=180s --headless
        """
        pass
    
    @staticmethod
    def endurance_test():
        """
        Endurance test - sustained load over time
        
        Usage:
            locust -f tests/load_test.py --users=150 --spawn-rate=5 --run-time=3600s --headless
        """
        pass


# Example custom test runner
def run_performance_suite():
    """
    Run complete performance test suite
    
    This function demonstrates how to run multiple test scenarios programmatically.
    In practice, you would use CI/CD pipelines to orchestrate these tests.
    """
    import subprocess
    import sys
    
    scenarios = [
        {
            'name': 'Smoke Test',
            'users': 10,
            'spawn_rate': 2,
            'run_time': '60s'
        },
        {
            'name': 'Load Test',
            'users': 100,
            'spawn_rate': 10,
            'run_time': '300s'
        },
        {
            'name': 'Stress Test',
            'users': 300,
            'spawn_rate': 20,
            'run_time': '600s'
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🚀 Running {scenario['name']}...")
        cmd = [
            'locust',
            '-f', 'tests/load_test.py',
            '--host=http://localhost:8000',
            f'--users={scenario["users"]}',
            f'--spawn-rate={scenario["spawn_rate"]}',
            f'--run-time={scenario["run_time"]}',
            '--headless',
            '--html', f'{scenario["name"].lower().replace(" ", "_")}_report.html'
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ {scenario['name']} completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ {scenario['name']} failed: {e}")
            print(f"Error output: {e.stderr}")


if __name__ == '__main__':
    """
    Direct script execution for custom test scenarios
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Run performance tests')
    parser.add_argument('--suite', action='store_true', help='Run complete test suite')
    parser.add_argument('--scenario', choices=['smoke', 'load', 'stress', 'spike', 'endurance'],
                       help='Run specific scenario')
    
    args = parser.parse_args()
    
    if args.suite:
        run_performance_suite()
    elif args.scenario:
        print(f"Run the following command for {args.scenario} test:")
        scenarios = {
            'smoke': '--users=10 --spawn-rate=2 --run-time=60s',
            'load': '--users=100 --spawn-rate=10 --run-time=300s',
            'stress': '--users=500 --spawn-rate=25 --run-time=600s',
            'spike': '--users=200 --spawn-rate=100 --run-time=180s',
            'endurance': '--users=150 --spawn-rate=5 --run-time=3600s'
        }
        print(f"locust -f tests/load_test.py --host=http://localhost:8000 {scenarios[args.scenario]} --headless")
    else:
        print("Use --suite to run all tests or --scenario <name> for specific test")
        print("For interactive mode: locust -f tests/load_test.py --host=http://localhost:8000")
