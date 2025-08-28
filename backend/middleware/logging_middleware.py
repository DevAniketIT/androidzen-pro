"""
FastAPI middleware for request logging and performance monitoring.
Integrates with the comprehensive logging system.
"""

import time
import uuid
import asyncio
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException
import json

from .core.logging_config import get_logger, set_request_context, clear_request_context, LogContext
from .logging_config import get_prometheus_metrics


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log HTTP requests and responses with contextual information.
    """
    
    def __init__(self, app, logger_name: str = "request", log_requests: bool = True, 
                 log_responses: bool = True, log_request_body: bool = False,
                 log_response_body: bool = False, sensitive_headers: Optional[list] = None):
        super().__init__(app)
        self.logger = get_logger(logger_name)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.sensitive_headers = sensitive_headers or ['authorization', 'cookie', 'x-api-key']
    
    def _filter_headers(self, headers: dict) -> dict:
        """Filter out sensitive headers from logging."""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "[REDACTED]"
            else:
                filtered[key] = value
        return filtered
    
    async def _read_body(self, request: Request) -> Optional[str]:
        """Safely read request body."""
        try:
            body = await request.body()
            if len(body) > 10000:  # Limit body size to log
                return f"[BODY TOO LARGE: {len(body)} bytes]"
            return body.decode('utf-8', errors='ignore')
        except Exception:
            return "[ERROR READING BODY]"
    
    def _extract_user_info(self, request: Request) -> tuple:
        """Extract user information from request."""
        user_id = None
        session_id = None
        
        # Try to get user info from headers or state
        if hasattr(request.state, 'user'):
            user = request.state.user
            user_id = user.get('id') if isinstance(user, dict) else getattr(user, 'id', None)
        
        # Try to get session info from cookies or headers
        session_id = request.cookies.get('session_id') or request.headers.get('x-session-id')
        
        return user_id, session_id
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Extract user information
        user_id, session_id = self._extract_user_info(request)
        
        # Set request context for structured logging
        set_request_context(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id
        )
        
        # Log incoming request
        if self.log_requests:
            request_data = {
                'method': request.method,
                'url': str(request.url),
                'path': request.url.path,
                'query_params': dict(request.query_params),
                'headers': self._filter_headers(dict(request.headers)),
                'client_ip': client_ip,
                'user_agent': user_agent,
                'content_type': request.headers.get('content-type'),
                'content_length': request.headers.get('content-length')
            }
            
            # Log request body if enabled
            if self.log_request_body and request.method in ['POST', 'PUT', 'PATCH']:
                # Store original body
                body = await request.body()
                request._body = body
                
                if body:
                    try:
                        # Try to parse as JSON for better logging
                        if 'application/json' in request.headers.get('content-type', ''):
                            request_data['body'] = json.loads(body.decode('utf-8'))
                        else:
                            request_data['body'] = body.decode('utf-8', errors='ignore')[:1000]
                    except Exception:
                        request_data['body'] = f"[BINARY DATA: {len(body)} bytes]"
            
            self.logger.info(
                f"Incoming request: {request.method} {request.url.path}",
                context={'request_data': request_data}
            )
        
        # Process request and measure execution time
        response = None
        error_occurred = False
        error_details = None
        
        try:
            response = await call_next(request)
            
        except HTTPException as e:
            error_occurred = True
            error_details = {
                'type': 'HTTPException',
                'status_code': e.status_code,
                'detail': e.detail
            }
            
            self.logger.warning(
                f"HTTP exception in {request.method} {request.url.path}: {e.detail}",
                context={
                    'status_code': e.status_code,
                    'error_detail': e.detail
                }
            )
            raise
            
        except Exception as e:
            error_occurred = True
            error_details = {
                'type': type(e).__name__,
                'message': str(e)
            }
            
            self.logger.exception(
                f"Unhandled exception in {request.method} {request.url.path}: {str(e)}"
            )
            raise
            
        finally:
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log response
            if self.log_responses and response:
                response_data = {
                    'status_code': response.status_code,
                    'headers': self._filter_headers(dict(response.headers)),
                    'execution_time_ms': execution_time
                }
                
                # Log response body if enabled and not too large
                if self.log_response_body and hasattr(response, 'body'):
                    try:
                        if len(response.body) < 1000:  # Only log small responses
                            response_data['body'] = response.body.decode('utf-8', errors='ignore')
                    except Exception:
                        response_data['body'] = "[ERROR READING RESPONSE BODY]"
                
                log_level = 'info'
                if response.status_code >= 400:
                    log_level = 'error' if response.status_code >= 500 else 'warning'
                
                getattr(self.logger, log_level)(
                    f"Response: {request.method} {request.url.path} - {response.status_code}",
                    context={
                        'response_data': response_data,
                        'execution_time': execution_time / 1000  # seconds for context
                    }
                )
            
            # Record performance metrics
            self.logger.performance_monitor.record_metric(
                metric_name=f"http.{request.method.lower()}.{request.url.path}",
                value=execution_time,
                unit="ms",
                context={
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': response.status_code if response else None,
                    'error': error_occurred
                },
                tags={
                    'method': request.method,
                    'endpoint': request.url.path,
                    'status_family': f"{response.status_code // 100}xx" if response else "error"
                }
            )
            
            # Clear request context
            clear_request_context()
        
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware specifically for performance monitoring and slow request detection.
    """
    
    def __init__(self, app, slow_request_threshold: float = 1000.0, logger_name: str = "performance"):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold  # milliseconds
        self.logger = get_logger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Add performance context
        LogContext.set(performance_monitoring=True)
        
        try:
            response = await call_next(request)
            execution_time = (time.time() - start_time) * 1000
            
            # Log slow requests
            if execution_time > self.slow_request_threshold:
                self.logger.warning(
                    f"Slow request detected: {request.method} {request.url.path}",
                    context={
                        'execution_time': execution_time / 1000,
                        'threshold': self.slow_request_threshold / 1000,
                        'method': request.method,
                        'path': request.url.path
                    }
                )
            
            # Add performance header
            response.headers["X-Response-Time"] = f"{execution_time:.2f}ms"
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            self.logger.error(
                f"Request failed after {execution_time:.2f}ms: {request.method} {request.url.path}",
                context={
                    'execution_time': execution_time / 1000,
                    'error': str(e),
                    'method': request.method,
                    'path': request.url.path
                }
            )
            raise
        
        finally:
            LogContext.remove('performance_monitoring')


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enhanced error tracking and reporting.
    """
    
    def __init__(self, app, logger_name: str = "error_tracker"):
        super().__init__(app)
        self.logger = get_logger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            
            # Track 4xx errors
            if 400 <= response.status_code < 500:
                self.logger.error_tracker.track_error(
                    error_type=f"HTTP{response.status_code}",
                    error_message=f"{request.method} {request.url.path} returned {response.status_code}",
                    context={
                        'method': request.method,
                        'path': request.url.path,
                        'status_code': response.status_code,
                        'user_agent': request.headers.get('user-agent'),
                        'client_ip': request.client.host if request.client else None
                    }
                )
            
            return response
            
        except Exception as e:
            # Track unhandled exceptions
            self.logger.error_tracker.track_error(
                error_type=type(e).__name__,
                error_message=str(e),
                context={
                    'method': request.method,
                    'path': request.url.path,
                    'user_agent': request.headers.get('user-agent'),
                    'client_ip': request.client.host if request.client else None
                },
                stack_trace=self.logger.logger.findCaller()
            )
            
            # Re-raise the exception
            raise


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security-related logging.
    """
    
    def __init__(self, app, logger_name: str = "security", suspicious_patterns: Optional[list] = None):
        super().__init__(app)
        self.logger = get_logger(logger_name)
        self.suspicious_patterns = suspicious_patterns or [
            'script', 'javascript:', 'onerror=', 'onload=', '<script>',
            'union select', 'drop table', 'delete from',
            '../', '..\\', '/etc/passwd', '/etc/hosts'
        ]
    
    def _check_suspicious_content(self, content: str) -> list:
        """Check for suspicious patterns in content."""
        if not content:
            return []
        
        content_lower = content.lower()
        found_patterns = []
        
        for pattern in self.suspicious_patterns:
            if pattern in content_lower:
                found_patterns.append(pattern)
        
        return found_patterns
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for suspicious patterns in URL
        suspicious_url = self._check_suspicious_content(str(request.url))
        
        # Check for suspicious patterns in headers
        suspicious_headers = []
        for header_name, header_value in request.headers.items():
            if header_name.lower() not in ['authorization', 'cookie']:
                patterns = self._check_suspicious_content(header_value)
                if patterns:
                    suspicious_headers.extend(patterns)
        
        # Check request body for POST/PUT requests
        suspicious_body = []
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    suspicious_body = self._check_suspicious_content(body_str)
                    # Restore body for further processing
                    request._body = body
            except Exception:
                pass
        
        # Log suspicious activity
        if suspicious_url or suspicious_headers or suspicious_body:
            self.logger.warning(
                f"Suspicious request detected: {request.method} {request.url.path}",
                context={
                    'client_ip': request.client.host if request.client else None,
                    'user_agent': request.headers.get('user-agent'),
                    'suspicious_url_patterns': suspicious_url,
                    'suspicious_header_patterns': suspicious_headers,
                    'suspicious_body_patterns': suspicious_body,
                    'full_url': str(request.url)
                }
            )
        
        # Log authentication attempts
        if 'authorization' in request.headers or request.url.path.startswith('/api/auth'):
            self.logger.info(
                f"Authentication attempt: {request.method} {request.url.path}",
                context={
                    'client_ip': request.client.host if request.client else None,
                    'user_agent': request.headers.get('user-agent'),
                    'has_auth_header': 'authorization' in request.headers
                }
            )
        
        try:
            response = await call_next(request)
            
            # Log failed authentication
            if response.status_code == 401:
                self.logger.warning(
                    f"Authentication failed: {request.method} {request.url.path}",
                    context={
                        'client_ip': request.client.host if request.client else None,
                        'user_agent': request.headers.get('user-agent')
                    }
                )
            
            return response
            
        except Exception as e:
            self.logger.error(
                f"Security-related error in {request.method} {request.url.path}: {str(e)}",
                context={
                    'client_ip': request.client.host if request.client else None,
                    'user_agent': request.headers.get('user-agent'),
                    'error': str(e)
                }
            )
            raise


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics for HTTP requests.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.prometheus_metrics = get_prometheus_metrics()
    
    def _get_endpoint_pattern(self, path: str) -> str:
        """Convert path to a pattern suitable for metrics (reduce cardinality)."""
        # Replace UUIDs and IDs with placeholders to reduce cardinality
        import re
        
        # Replace UUIDs
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path, flags=re.IGNORECASE)
        # Replace numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        # Replace other long identifiers
        path = re.sub(r'/[a-zA-Z0-9_-]{20,}(?=/|$)', '/{id}', path)
        
        return path
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.prometheus_metrics.enabled:
            return await call_next(request)
        
        start_time = time.time()
        status_code = 500  # Default to 500 in case of unhandled exception
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
            
        except HTTPException as e:
            status_code = e.status_code
            # Record error metrics
            self.prometheus_metrics.record_error(
                error_type="HTTPException",
                severity="warning" if status_code < 500 else "error"
            )
            raise
            
        except Exception as e:
            status_code = 500
            # Record error metrics
            self.prometheus_metrics.record_error(
                error_type=type(e).__name__,
                severity="error"
            )
            raise
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Get normalized endpoint pattern
            endpoint_pattern = self._get_endpoint_pattern(request.url.path)
            
            # Record HTTP request metrics
            self.prometheus_metrics.record_http_request(
                method=request.method,
                endpoint=endpoint_pattern,
                status_code=status_code,
                duration=duration
            )

