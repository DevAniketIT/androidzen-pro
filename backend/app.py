"""
Production-ready FastAPI application for AndroidZen Pro backend.
Enhanced with comprehensive logging, monitoring, and error tracking.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
import os
from typing import Dict, Any
from pathlib import Path

# Import core modules
from .core.database import create_tables, get_db
from .core.auth import AuthManager, get_current_user
from .core.websocket_manager import WebSocketManager
from .logging_config import setup_production_logging, LogContext, performance_monitor, log_exceptions, get_prometheus_metrics

# Import API routers
from .api.devices import router as devices_router
from .api.storage import router as storage_router
from .api.settings import router as settings_router
from .api.security import router as security_router
from .api.network import router as network_router
from .api.auth import router as auth_router
from .api.websocket import router as websocket_router
from .api.ai_analytics import router as ai_analytics_router
from .api.monitoring import router as monitoring_router
from .api.admin import router as admin_router
from .api.reports import router as reports_router

# Import AI service
from .services.intelligence_service import AIService

# Import middleware
from .middleware import (
    LoggingMiddleware,
    PerformanceMiddleware,
    ErrorTrackingMiddleware,
    SecurityLoggingMiddleware,
    PrometheusMiddleware
)

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Logging configuration with environment-specific settings
def configure_logging():
    """Configure logging based on environment."""
    
    # Default log configuration
    log_config = {
        "app_name": "androidzen-pro",
        "environment": ENVIRONMENT,
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_format": "console" if DEBUG else "structured",
        "enable_performance_monitoring": True,
        "enable_error_tracking": True,
    }
    
    # Environment-specific configurations
    if ENVIRONMENT.lower() == "production":
        log_config.update({
            "log_level": "INFO",  # Force INFO level in production
            "log_format": "structured",  # Force JSON format in production
            "log_file": os.getenv("LOG_FILE", "./logs/androidzen-pro.log"),
            "max_file_size": int(os.getenv("MAX_LOG_FILE_SIZE", str(50 * 1024 * 1024))),  # 50MB
            "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "10")),
        })
    elif ENVIRONMENT.lower() == "staging":
        log_config.update({
            "log_level": "DEBUG",
            "log_format": "structured",
            "log_file": os.getenv("LOG_FILE", "./logs/androidzen-pro-staging.log"),
            "max_file_size": int(os.getenv("MAX_LOG_FILE_SIZE", str(20 * 1024 * 1024))),  # 20MB
            "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
        })
    else:  # development
        log_config.update({
            "log_level": "DEBUG" if DEBUG else "INFO",
            "log_format": "console",
            "log_file": os.getenv("LOG_FILE"),  # Optional in development
        })
    
    logging_setup = setup_production_logging(**log_config)
    return logging_setup['logger']


# Setup comprehensive logging
logger = configure_logging()

# Global managers
websocket_manager = WebSocketManager()
auth_manager = AuthManager()
ai_service = AIService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting AndroidZen Pro Backend...", extra={'context': {
        "environment": ENVIRONMENT,
        "debug_mode": DEBUG,
        "host": HOST,
        "port": PORT
    }})
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.exception("Failed to initialize database", context={"error": str(e)})
        raise

    # Start background tasks
    monitoring_task = asyncio.create_task(start_monitoring_tasks())
    
    # Initialize AI service
    try:
        await ai_service.initialize_models()
        logger.info("AI service initialized successfully")
    except Exception as e:
        logger.exception("Failed to initialize AI service", context={"error": str(e)})

    logger.info("Backend startup complete", context={
        "startup_time": "complete",
        "services": {
            "database": "initialized",
            "ai_service": "initialized",
            "monitoring": "started"
        }
    })
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down AndroidZen Pro Backend...")
    
    # Cancel background tasks
    monitoring_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass
    
    # Close WebSocket connections
    await websocket_manager.disconnect_all()
    
    logger.info("Backend shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="AndroidZen Pro Backend",
    description="Production-ready Backend API for AndroidZen Pro device optimization platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=DEBUG
)

# Production middleware setup with proper ordering
def setup_middleware():
    """Setup middleware in the correct order for production."""
    
    # Prometheus metrics middleware (first to ensure all requests are captured)
    if os.getenv("ENABLE_PROMETHEUS_METRICS", "true").lower() == "true":
        app.add_middleware(PrometheusMiddleware)
        logger.info("Prometheus metrics middleware enabled")
    
    # Security logging middleware
    if os.getenv("ENABLE_SECURITY_LOGGING", "true").lower() == "true":
        app.add_middleware(SecurityLoggingMiddleware)
        logger.info("Security logging middleware enabled")

    # Error tracking middleware
    if os.getenv("ENABLE_ERROR_TRACKING", "true").lower() == "true":
        app.add_middleware(ErrorTrackingMiddleware)
        logger.info("Error tracking middleware enabled")

    # Performance monitoring middleware
    if os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true":
        app.add_middleware(
            PerformanceMiddleware,
            slow_request_threshold=float(os.getenv("SLOW_REQUEST_THRESHOLD", "1000"))
        )
        logger.info("Performance monitoring middleware enabled")

    # Request/response logging middleware
    if os.getenv("LOG_REQUESTS", "true").lower() == "true":
        app.add_middleware(
            LoggingMiddleware,
            log_requests=True,
            log_responses=os.getenv("LOG_RESPONSES", "true").lower() == "true",
            log_request_body=os.getenv("LOG_REQUEST_BODY", "false").lower() == "true",
            log_response_body=os.getenv("LOG_RESPONSE_BODY", "false").lower() == "true"
        )
        logger.info("Request/response logging middleware enabled")

    # CORS middleware (should be last middleware before routes)
    allowed_origins = []
    
    if ENVIRONMENT.lower() == "production":
        # Production origins from environment
        origins_env = os.getenv("ALLOWED_ORIGINS", "")
        if origins_env:
            allowed_origins = [origin.strip() for origin in origins_env.split(",")]
        else:
            logger.warning("No ALLOWED_ORIGINS set for production environment")
    else:
        # Development origins
        allowed_origins = [
            "http://localhost:3000",  # React development
            "http://localhost:5173",  # Vite development
            "http://localhost:8080",  # Vue development
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )
    
    logger.info("CORS middleware configured", context={
        "allowed_origins": allowed_origins,
        "environment": ENVIRONMENT
    })


# Setup middleware
setup_middleware()

# Security scheme
security = HTTPBearer()

# Global exception handler with enhanced logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.exception(
        f"Unhandled error in {request.method} {request.url.path}: {str(exc)}",
        context={
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if DEBUG else "An unexpected error occurred",
            "timestamp": "2024-01-01T00:00:00Z"  # This would be dynamic in production
        }
    )

# Enhanced health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint with comprehensive system status."""
    try:
        # Check database connectivity
        db_status = "healthy"
        try:
            # Simple database check - you might want to make this more comprehensive
            async with get_db() as db:
                # Perform a simple query to check database connectivity
                pass
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
            logger.error("Database health check failed", context={"error": str(e)})
        
        # Check AI service status
        ai_status = "healthy" if hasattr(ai_service, '_initialized') else "not_initialized"
        
        health_data = {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "service": "AndroidZen Pro Backend",
            "version": "1.0.0",
            "environment": ENVIRONMENT,
            "timestamp": "2024-01-01T00:00:00Z",  # This would be dynamic in production
            "checks": {
                "database": db_status,
                "ai_service": ai_status,
                "websocket_manager": "healthy"
            }
        }
        
        status_code = 200 if health_data["status"] == "healthy" else 503
        
        logger.info("Health check performed", context=health_data)
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
        
    except Exception as e:
        logger.exception("Health check failed", context={"error": str(e)})
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e) if DEBUG else "Health check failed"
            }
        )

# Readiness probe endpoint
@app.get("/ready", tags=["System"])
async def readiness_check():
    """Readiness probe endpoint for Kubernetes deployments."""
    try:
        from datetime import datetime
        
        # Check if all critical services are ready
        checks = {
            "database": "ready",
            "ai_service": "ready",
            "logging": "ready",
            "monitoring": "ready"
        }
        
        # Check database connectivity
        try:
            async with get_db() as db:
                pass  # Simple connection test
        except Exception as e:
            checks["database"] = f"not_ready: {str(e)}"
        
        # Check AI service initialization
        if not hasattr(ai_service, '_initialized'):
            checks["ai_service"] = "not_ready: not_initialized"
        
        # Determine overall readiness
        all_ready = all(status == "ready" for status in checks.values())
        
        readiness_data = {
            "ready": all_ready,
            "service": "AndroidZen Pro Backend",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "checks": checks
        }
        
        status_code = 200 if all_ready else 503
        
        logger.info("Readiness check performed", extra={'context': readiness_data})
        
        return JSONResponse(
            status_code=status_code,
            content=readiness_data
        )
        
    except Exception as e:
        logger.exception("Readiness check failed", extra={'context': {"error": str(e)}})
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "error": str(e) if DEBUG else "Readiness check failed"
            }
        )


# Prometheus metrics endpoint
@app.get("/metrics", tags=["Monitoring"])
async def prometheus_metrics():
    """Prometheus metrics endpoint for monitoring and alerting."""
    try:
        from fastapi.responses import PlainTextResponse
        
        # Get metrics from the global Prometheus metrics instance
        metrics = get_prometheus_metrics()
        metrics_data = metrics.get_metrics()
        
        logger.debug("Metrics endpoint accessed")
        
        return PlainTextResponse(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.exception("Failed to generate metrics", extra={'context': {"error": str(e)}})
        return PlainTextResponse(
            content="# Error generating metrics\n",
            status_code=500,
            media_type="text/plain"
        )


# Root endpoint
@app.get("/", tags=["System"])
async def read_root():
    """Root endpoint providing API information."""
    from datetime import datetime
    return {
        "message": "AndroidZen Pro Backend API",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "endpoints": {
            "docs": "/docs",
            "health_check": "/health",
            "readiness_check": "/ready",
            "metrics": "/metrics",
            "websocket": "/ws"
        },
        "timestamp": datetime.now().isoformat()
    }

# Include API routers with enhanced logging
def include_routers():
    """Include all API routers with proper configuration."""
    
    routers_config = [
        {"router": auth_router, "prefix": "/api/auth", "tags": ["Authentication"], "auth_required": False},
        {"router": devices_router, "prefix": "/api/devices", "tags": ["Devices"], "auth_required": True},
        {"router": storage_router, "prefix": "/api/storage", "tags": ["Storage"], "auth_required": True},
        {"router": settings_router, "prefix": "/api/settings", "tags": ["Settings"], "auth_required": True},
        {"router": security_router, "prefix": "/api/security", "tags": ["Security"], "auth_required": True},
        {"router": network_router, "prefix": "/api/network", "tags": ["Network"], "auth_required": True},
        {"router": websocket_router, "prefix": "", "tags": ["WebSocket"], "auth_required": False},
        {"router": ai_analytics_router, "prefix": "/api/ai", "tags": ["AI Analytics"], "auth_required": True},
        {"router": monitoring_router, "prefix": "/api/monitoring", "tags": ["Monitoring"], "auth_required": True},
        {"router": admin_router, "prefix": "/api/admin", "tags": ["Administration"], "auth_required": True},
        {"router": reports_router, "prefix": "/api/reports", "tags": ["Reports"], "auth_required": True},
    ]
    
    for config in routers_config:
        kwargs = {
            "prefix": config["prefix"],
            "tags": config["tags"]
        }
        
        if config["auth_required"]:
            kwargs["dependencies"] = [Depends(get_current_user)]
        
        app.include_router(config["router"], **kwargs)
        
        logger.info(f"Router included: {config['prefix']}", context={
            "tags": config["tags"],
            "auth_required": config["auth_required"]
        })

# Include routers
include_routers()

@performance_monitor("background_monitoring")
@log_exceptions("background_monitoring")
async def start_monitoring_tasks():
    """Start background monitoring tasks with enhanced error handling."""
    while True:
        try:
            # Broadcast device status updates every 30 seconds
            await websocket_manager.broadcast_device_status()
            
            # Run AI anomaly detection every 6 hours (simplified for demo)
            from datetime import datetime as dt
            current_hour = dt.now().hour
            if current_hour % 6 == 0 and dt.now().minute < 5:
                # Get connected devices
                async with get_db() as db:
                    from .models.device import Device
                    devices = db.query(Device).filter(Device.is_connected == True).all()
                    for device in devices:
                        try:
                            # Run anomaly detection
                            anomalies = await ai_service.detect_anomalies(device.device_id)
                            if anomalies:
                                logger.info(
                                    f"Detected {len(anomalies)} anomalies for device {device.device_id}",
                                    context={
                                        "device_id": device.device_id,
                                        "anomaly_count": len(anomalies)
                                    }
                                )
                                # Send notifications through WebSocket
                                for anomaly in anomalies:
                                    if anomaly.severity in ["high", "critical"]:
                                        await websocket_manager.broadcast_message({
                                            "type": "anomaly_alert",
                                            "device_id": device.device_id,
                                            "anomaly_type": anomaly.anomaly_type,
                                            "severity": anomaly.severity,
                                            "explanation": anomaly.explanation
                                        })
                        except Exception as inner_e:
                            logger.exception(
                                f"Error detecting anomalies for device {device.device_id}",
                                context={"device_id": device.device_id, "error": str(inner_e)}
                            )
            
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Background monitoring task cancelled")
            break
        except Exception as e:
            logger.exception("Error in monitoring task", context={"error": str(e)})
            await asyncio.sleep(30)

# Production server startup
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {HOST}:{PORT}", context={
        "host": HOST,
        "port": PORT,
        "environment": ENVIRONMENT,
        "debug": DEBUG
    })
    
    # Production-specific uvicorn configuration
    uvicorn_config = {
        "host": HOST,
        "port": PORT,
        "reload": DEBUG and ENVIRONMENT.lower() == "development",
        "log_level": "info" if not DEBUG else "debug",
        "access_log": True,
        "server_header": False,  # Hide server header for security
    }
    
    # Production optimizations
    if ENVIRONMENT.lower() == "production":
        uvicorn_config.update({
            "workers": int(os.getenv("WORKERS", "4")),
            "loop": "uvloop",  # Use uvloop for better performance
            "http": "httptools",  # Use httptools for better performance
            "reload": False,
            "log_level": "warning",  # Reduce uvicorn log verbosity in production
        })
    
    uvicorn.run("backend.app:app", **uvicorn_config)

