"""
Main FastAPI application for AndroidZen Pro backend.
Includes REST API endpoints, WebSocket real-time monitoring, authentication, and CORS middleware.
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

# Import core modules
from .core.database import create_tables, get_db
from .core.auth import AuthManager, get_current_user
from .core.websocket_manager import WebSocketManager
from .core.logging_config import setup_logging, get_logger, performance_monitor, log_exceptions

# Import API routers
from .api.devices import router as devices_router
from .api.storage import router as storage_router
from .api.settings import router as settings_router
from .api.security import router as security_router
from .api.network import router as network_router
from .api.auth import router as auth_router
from .api.websocket import router as websocket_router
from .api.analytics_service import router as ai_analytics_router
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
    SecurityLoggingMiddleware
)

# Setup comprehensive logging
logger = setup_logging(
    app_name="androidzen-pro",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_format=os.getenv("LOG_FORMAT", "console"),
    log_file=os.getenv("LOG_FILE"),
    max_file_size=int(os.getenv("MAX_LOG_FILE_SIZE", str(10 * 1024 * 1024))),
    backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
)

# Global managers
websocket_manager = WebSocketManager()
auth_manager = AuthManager()
ai_service = AIService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting AndroidZen Pro Backend...")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Start background tasks
    monitoring_task = asyncio.create_task(start_monitoring_tasks())
    
    # Initialize AI service
    try:
        await ai_service.initialize_models()
        logger.info("AI service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI service: {e}")
    
    logger.info("Backend startup complete")
    
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
    description="Backend API for AndroidZen Pro device optimization platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add comprehensive logging and monitoring middleware
if os.getenv("ENABLE_SECURITY_LOGGING", "true").lower() == "true":
    app.add_middleware(SecurityLoggingMiddleware)

if os.getenv("ENABLE_ERROR_TRACKING", "true").lower() == "true":
    app.add_middleware(ErrorTrackingMiddleware)

if os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true":
    app.add_middleware(
        PerformanceMiddleware,
        slow_request_threshold=float(os.getenv("SLOW_REQUEST_THRESHOLD", "1000"))
    )

# Add request/response logging middleware
if os.getenv("LOG_REQUESTS", "true").lower() == "true":
    app.add_middleware(
        LoggingMiddleware,
        log_requests=True,
        log_responses=os.getenv("LOG_RESPONSES", "true").lower() == "true",
        log_request_body=os.getenv("LOG_REQUEST_BODY", "false").lower() == "true",
        log_response_body=os.getenv("LOG_RESPONSE_BODY", "false").lower() == "true"
    )

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development
        "http://localhost:5173",  # Vite development
        "http://localhost:8080",  # Vue development
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        # Add production domains when deployed
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "An unexpected error occurred"
        }
    )

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {
        "status": "healthy",
        "service": "AndroidZen Pro Backend",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"  # This would be dynamic in production
    }

# Root endpoint
@app.get("/", tags=["System"])
async def read_root():
    """Root endpoint providing API information."""
    return {
        "message": "AndroidZen Pro Backend API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/health",
        "websocket_endpoint": "/ws"
    }

# Include API routers
app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    devices_router,
    prefix="/api/devices",
    tags=["Devices"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    storage_router,
    prefix="/api/storage",
    tags=["Storage"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    settings_router,
    prefix="/api/settings",
    tags=["Settings"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    security_router,
    prefix="/api/security",
    tags=["Security"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    network_router,
    prefix="/api/network",
    tags=["Network"],
    dependencies=[Depends(get_current_user)]
)

# WebSocket router (no auth dependency for WebSocket connections - handled internally)
app.include_router(
    websocket_router,
    tags=["WebSocket"]
)

# AI Analytics router
app.include_router(
    ai_analytics_router,
    tags=["AI Analytics"],
    dependencies=[Depends(get_current_user)]
)

# Monitoring router
app.include_router(
    monitoring_router,
    prefix="/api/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(get_current_user)]
)

# Admin router (requires admin privileges)
app.include_router(
    admin_router,
    prefix="/api/admin",
    tags=["Administration"]
)

# Reports router
app.include_router(
    reports_router,
    prefix="/api/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)]
)

@performance_monitor("background_monitoring")
@log_exceptions("background_monitoring")
async def start_monitoring_tasks():
    """Start background monitoring tasks."""
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
                                logger.info(f"Detected {len(anomalies)} anomalies for device {device.device_id}")
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
                            logger.error(f"Error detecting anomalies for device {device.device_id}: {inner_e}")
            
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in monitoring task: {e}")
            await asyncio.sleep(30)

# Note: Request logging is now handled by LoggingMiddleware
# The old logging middleware has been replaced with the comprehensive logging system

if __name__ == "__main__":
    import uvicorn
    
    # Configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )
