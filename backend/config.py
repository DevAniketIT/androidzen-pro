"""
Security Configuration for AndroidZen Pro Backend
Comprehensive configuration including rate limiting, CORS, security headers,
JWT settings, database pooling, and SSL/TLS settings.
"""

import os
from datetime import timedelta
from typing import Dict, List, Any


class Config:
    """Base configuration class with common settings."""
    
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///androidzen.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database Connection Pooling Settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', '10')),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '3600')),  # 1 hour
        'pool_pre_ping': True,
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', '20')),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '20'))
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get('JWT_ACCESS_TOKEN_HOURS', '1'))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get('JWT_REFRESH_TOKEN_DAYS', '30'))
    )
    JWT_ALGORITHM = 'HS256'
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Rate Limiting Configuration (Flask-Limiter)
    RATELIMIT_STORAGE_URI = os.environ.get('REDIS_URL') or 'memory://'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '1000 per hour')
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_SWALLOW_ERRORS = True
    
    # Custom Rate Limits for Different Endpoints
    RATE_LIMITS = {
        'auth_login': '5 per minute',
        'auth_register': '3 per minute', 
        'api_general': '100 per minute',
        'api_upload': '10 per minute',
        'websocket': '50 per minute'
    }
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
    CORS_ALLOW_HEADERS = [
        'Content-Type',
        'Authorization',
        'Access-Control-Allow-Credentials',
        'Access-Control-Allow-Origin',
        'Access-Control-Allow-Headers',
        'Access-Control-Allow-Methods',
        'X-Requested-With',
        'X-API-Key'
    ]
    CORS_EXPOSE_HEADERS = [
        'X-RateLimit-Limit',
        'X-RateLimit-Remaining',
        'X-RateLimit-Reset'
    ]
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_MAX_AGE = 86400  # 24 hours
    
    # Security Headers Configuration
    SECURITY_HEADERS = {
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        ),
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'accelerometer=(), '
            'gyroscope=()'
        )
    }
    
    # SSL/TLS Configuration
    SSL_DISABLE = os.environ.get('SSL_DISABLE', 'False').lower() == 'true'
    SSL_REDIRECT = os.environ.get('SSL_REDIRECT', 'True').lower() == 'true'
    SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH')
    SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # File Upload Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_EXTENSIONS = ['.apk', '.jpg', '.jpeg', '.png', '.pdf', '.txt', '.log']
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # WebSocket Configuration
    WEBSOCKET_PING_INTERVAL = 25
    WEBSOCKET_PING_TIMEOUT = 5
    WEBSOCKET_MAX_SIZE = 2**20  # 1MB
    
    # API Configuration
    API_PREFIX = '/api/v1'
    PAGINATION_PER_PAGE = 20
    PAGINATION_MAX_PER_PAGE = 100


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    TESTING = False
    
    # Relaxed CORS for development
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:8080']
    
    # More permissive CSP for development
    SECURITY_HEADERS = Config.SECURITY_HEADERS.copy()
    SECURITY_HEADERS['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https: http:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss: http: https:; "
        "frame-ancestors 'self';"
    )
    
    # Relaxed rate limiting for development
    RATELIMIT_DEFAULT = '10000 per hour'
    RATE_LIMITS = {
        'auth_login': '100 per minute',
        'auth_register': '50 per minute',
        'api_general': '1000 per minute',
        'api_upload': '100 per minute',
        'websocket': '500 per minute'
    }
    
    # SSL disabled for development
    SSL_DISABLE = True
    SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    
    # Development database with smaller pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'pool_timeout': 10,
        'max_overflow': 10
    }


class StagingConfig(Config):
    """Staging environment configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Moderate rate limiting for staging
    RATE_LIMITS = {
        'auth_login': '10 per minute',
        'auth_register': '5 per minute',
        'api_general': '500 per minute',
        'api_upload': '20 per minute',
        'websocket': '100 per minute'
    }
    
    # Staging-specific CORS origins
    CORS_ORIGINS = os.environ.get('STAGING_CORS_ORIGINS', 'https://staging.androidzen.com').split(',')
    
    # Medium database pool for staging
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 8,
        'pool_recycle': 2400,
        'pool_pre_ping': True,
        'pool_timeout': 15,
        'max_overflow': 15
    }


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Strict security headers for production
    SECURITY_HEADERS = Config.SECURITY_HEADERS.copy()
    SECURITY_HEADERS['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    # Strict rate limiting for production
    RATE_LIMITS = Config.RATE_LIMITS.copy()  # Use default strict limits
    
    # Production CORS origins (should be explicitly set)
    CORS_ORIGINS = os.environ.get('PROD_CORS_ORIGINS', '').split(',')
    if not CORS_ORIGINS or CORS_ORIGINS == ['']:
        raise ValueError("PROD_CORS_ORIGINS must be set in production")
    
    # Ensure SSL is enabled in production
    SSL_DISABLE = False
    SSL_REDIRECT = True
    
    # Strict session cookies
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Production database with larger pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 15,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'max_overflow': 30
    }
    
    # Shorter JWT expiration in production
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)


class TestingConfig(Config):
    """Testing environment configuration."""
    
    DEBUG = True
    TESTING = True
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Minimal database pool for testing
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,
        'pool_recycle': 300,
        'pool_pre_ping': False,
        'pool_timeout': 5,
        'max_overflow': 0
    }
    
    # Disable rate limiting for testing
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = 'memory://'
    
    # Relaxed security for testing
    SSL_DISABLE = True
    SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    
    # Fast JWT expiration for testing
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=300)  # 5 minutes
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Allow all origins for testing
    CORS_ORIGINS = ['*']


# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}


def get_config(config_name: str = None) -> Config:
    """
    Get configuration object based on environment name.
    
    Args:
        config_name: Name of configuration ('development', 'staging', 'production', 'testing')
                    If None, will use FLASK_ENV environment variable
    
    Returns:
        Configuration object
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config_map.get(config_name)
    if not config_class:
        raise ValueError(f"Invalid configuration name: {config_name}")
    
    return config_class()


# Security helper functions
def apply_security_headers(response):
    """Apply security headers to Flask response."""
    config = get_config()
    
    for header, value in config.SECURITY_HEADERS.items():
        response.headers[header] = value
    
    return response


def get_rate_limit(endpoint: str) -> str:
    """Get rate limit for specific endpoint."""
    config = get_config()
    return config.RATE_LIMITS.get(endpoint, config.RATELIMIT_DEFAULT)


def is_ssl_required() -> bool:
    """Check if SSL is required based on current configuration."""
    config = get_config()
    return not config.SSL_DISABLE and config.SSL_REDIRECT


def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration dictionary."""
    config = get_config()
    
    return {
        'origins': config.CORS_ORIGINS,
        'methods': config.CORS_METHODS,
        'allow_headers': config.CORS_ALLOW_HEADERS,
        'expose_headers': config.CORS_EXPOSE_HEADERS,
        'supports_credentials': config.CORS_SUPPORTS_CREDENTIALS,
        'max_age': config.CORS_MAX_AGE
    }


def get_jwt_config() -> Dict[str, Any]:
    """Get JWT configuration dictionary."""
    config = get_config()
    
    return {
        'JWT_SECRET_KEY': config.JWT_SECRET_KEY,
        'JWT_ACCESS_TOKEN_EXPIRES': config.JWT_ACCESS_TOKEN_EXPIRES,
        'JWT_REFRESH_TOKEN_EXPIRES': config.JWT_REFRESH_TOKEN_EXPIRES,
        'JWT_ALGORITHM': config.JWT_ALGORITHM,
        'JWT_BLACKLIST_ENABLED': config.JWT_BLACKLIST_ENABLED,
        'JWT_BLACKLIST_TOKEN_CHECKS': config.JWT_BLACKLIST_TOKEN_CHECKS
    }


def validate_production_config():
    """Validate that production configuration is secure."""
    config = get_config('production')
    errors = []
    
    # Check for default secret key
    if config.SECRET_KEY == 'your-secret-key-change-in-production':
        errors.append("SECRET_KEY must be changed in production")
    
    # Check for empty CORS origins
    if not config.CORS_ORIGINS or config.CORS_ORIGINS == ['']:
        errors.append("CORS_ORIGINS must be explicitly set in production")
    
    # Check SSL configuration
    if config.SSL_DISABLE:
        errors.append("SSL should not be disabled in production")
    
    # Check database URL
    if 'sqlite' in config.SQLALCHEMY_DATABASE_URI.lower():
        errors.append("SQLite should not be used in production")
    
    if errors:
        raise ValueError("Production configuration errors: " + "; ".join(errors))
    
    return True
