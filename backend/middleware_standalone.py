"""
Main middleware module for AndroidZen Pro backend.

This module provides stub implementations of middleware classes for:
- Request/response logging
- Performance monitoring
- Error tracking
- Security logging
"""

import time
import uuid
import logging
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    
    This is a minimal stub implementation.
    """
    
    def __init__(self, app, logger_name: str = "request"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log basic information."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Log incoming request
        self.logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )
        
        try:
            response = await call_next(request)
            execution_time = (time.time() - start_time) * 1000
            
            # Log response
            self.logger.info(
                f"Response: {request.method} {request.url.path} - {response.status_code} ({execution_time:.2f}ms)",
                extra={"request_id": request_id, "execution_time": execution_time}
            )
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(
                f"Error: {request.method} {request.url.path} - {str(e)} ({execution_time:.2f}ms)",
                extra={"request_id": request_id, "execution_time": execution_time}
            )
            raise


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for performance monitoring.
    
    This is a minimal stub implementation.
    """
    
    def __init__(self, app, slow_request_threshold: float = 1000.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold  # milliseconds
        self.logger = logging.getLogger("performance")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request performance."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            execution_time = (time.time() - start_time) * 1000
            
            # Log slow requests
            if execution_time > self.slow_request_threshold:
                self.logger.warning(
                    f"Slow request: {request.method} {request.url.path} took {execution_time:.2f}ms"
                )
            
            # Add performance header
            response.headers["X-Response-Time"] = f"{execution_time:.2f}ms"
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(
                f"Request failed after {execution_time:.2f}ms: {request.method} {request.url.path}"
            )
            raise


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for error tracking and reporting.
    
    This is a minimal stub implementation.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("error_tracker")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track errors and exceptions."""
        try:
            response = await call_next(request)
            
            # Track 4xx and 5xx errors
            if response.status_code >= 400:
                self.logger.error(
                    f"HTTP {response.status_code}: {request.method} {request.url.path}",
                    extra={
                        "status_code": response.status_code,
                        "method": request.method,
                        "path": request.url.path,
                        "client_ip": request.client.host if request.client else None
                    }
                )
            
            return response
            
        except HTTPException as e:
            self.logger.warning(
                f"HTTP Exception {e.status_code}: {request.method} {request.url.path} - {e.detail}"
            )
            raise
            
        except Exception as e:
            self.logger.exception(
                f"Unhandled exception: {request.method} {request.url.path} - {str(e)}"
            )
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security monitoring and logging.
    
    This is a minimal stub implementation.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("security")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor for security-related events."""
        # Log authentication attempts
        if "authorization" in request.headers or request.url.path.startswith("/api/auth"):
            self.logger.info(
                f"Authentication attempt: {request.method} {request.url.path}",
                extra={
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )
        
        try:
            response = await call_next(request)
            
            # Log failed authentication
            if response.status_code == 401:
                self.logger.warning(
                    f"Authentication failed: {request.method} {request.url.path}",
                    extra={"client_ip": request.client.host if request.client else None}
                )
            
            return response
            
        except Exception as e:
            self.logger.error(
                f"Security-related error: {request.method} {request.url.path} - {str(e)}"
            )
            raise


class CORSMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling CORS (Cross-Origin Resource Sharing).
    
    This is a minimal stub implementation.
    """
    
    def __init__(self, app, allow_origins: Optional[list] = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.logger = logging.getLogger("cors")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS headers."""
        if request.method == "OPTIONS":
            # Handle preflight requests
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response
        
        response = await call_next(request)
        
        # Add CORS headers to response
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


# Utility function to get all middleware classes
def get_all_middleware():
    """Return all available middleware classes."""
    return [
        LoggingMiddleware,
        PerformanceMiddleware,
        ErrorTrackingMiddleware,
        SecurityMiddleware,
        CORSMiddleware
    ]


# Export all middleware classes
__all__ = [
    "LoggingMiddleware",
    "PerformanceMiddleware", 
    "ErrorTrackingMiddleware",
    "SecurityMiddleware",
    "CORSMiddleware",
    "get_all_middleware"
]
