"""
Production-ready logging configuration for AndroidZen Pro.
Consolidated logging setup with environment-specific configurations, 
error tracking integration, and performance monitoring.
"""

import os
import sys
import json
import time
import logging
import logging.handlers
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import threading
from queue import Queue, Empty
from contextlib import contextmanager
from functools import wraps
from dataclasses import dataclass, asdict
import uuid
import asyncio


# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


@dataclass
class LogEntry:
    """Enhanced structured log entry with comprehensive contextual information."""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    environment: str
    service: str = "androidzen-pro"
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    execution_time: Optional[float] = None
    extra_data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    error_type: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


@dataclass
class PerformanceMetric:
    """Enhanced performance monitoring metric with additional metadata."""
    metric_name: str
    value: float
    unit: str
    timestamp: str
    environment: str
    service: str = "androidzen-pro"
    context: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None
    threshold_exceeded: Optional[bool] = None


@dataclass
class SecurityEvent:
    """Security event logging structure."""
    event_type: str
    severity: str
    timestamp: str
    user_id: Optional[str]
    client_ip: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    details: Dict[str, Any]
    environment: str
    service: str = "androidzen-pro"


class ProductionJSONFormatter(logging.Formatter):
    """Production-ready JSON formatter with enhanced security and compliance features."""
    
    def __init__(self, include_sensitive_data: bool = False):
        super().__init__()
        self.include_sensitive_data = include_sensitive_data
        self.sensitive_fields = {'password', 'token', 'api_key', 'secret', 'authorization'}
    
    def format(self, record: logging.LogRecord) -> str:
        # Get contextual information
        context = getattr(record, 'context', {})
        
        # Sanitize sensitive data in production
        if not self.include_sensitive_data and ENVIRONMENT == "production":
            context = self._sanitize_context(context)
        
        log_entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line_number=record.lineno,
            thread_id=record.thread,
            process_id=record.process,
            environment=ENVIRONMENT,
            service="androidzen-pro",
            request_id=context.get('request_id'),
            user_id=context.get('user_id'),
            device_id=context.get('device_id'),
            session_id=context.get('session_id'),
            correlation_id=context.get('correlation_id'),
            execution_time=context.get('execution_time'),
            extra_data=context.get('extra_data'),
            stack_trace=self._format_exception(record.exc_info) if record.exc_info else None,
            error_type=record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else None,
            tags=context.get('tags')
        )
        
        return json.dumps(asdict(log_entry), default=str, ensure_ascii=False)
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive information from log context."""
        sanitized = {}
        
        for key, value in context.items():
            if isinstance(key, str) and any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_context(value)
            elif isinstance(value, str) and len(value) > 50:
                # Truncate very long strings that might contain sensitive data
                sanitized[key] = value[:50] + "... [TRUNCATED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _format_exception(self, exc_info) -> str:
        """Format exception information with production considerations."""
        if exc_info:
            if ENVIRONMENT == "production":
                # In production, limit stack trace depth for security
                return ''.join(traceback.format_exception(*exc_info)[-10:])  # Last 10 frames
            else:
                return ''.join(traceback.format_exception(*exc_info))
        return None


class DevelopmentFormatter(logging.Formatter):
    """Enhanced colored console formatter for development with better readability."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    ICONS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '💀'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        context = getattr(record, 'context', {})
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        icon = self.ICONS.get(record.levelname, '📝')
        
        # Format timestamp
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Build log components
        log_parts = [
            f"{color}{icon} [{record.levelname}]{reset}",
            f"{timestamp}",
            f"[{record.name}]",
            f"{record.funcName}:{record.lineno}",
        ]
        
        # Add contextual information with colors
        if context.get('request_id'):
            log_parts.append(f"🔗 {context['request_id'][:8]}")
        if context.get('user_id'):
            log_parts.append(f"👤 {context['user_id']}")
        if context.get('device_id'):
            log_parts.append(f"📱 {context['device_id']}")
        if context.get('execution_time'):
            time_color = '\033[93m' if context['execution_time'] > 1.0 else '\033[92m'
            log_parts.append(f"{time_color}⏱️ {context['execution_time']:.3f}s{reset}")
        
        header = " │ ".join(log_parts)
        message = record.getMessage()
        
        result = f"{header}\n   └─ {message}"
        
        # Add exception information with formatting
        if record.exc_info:
            exc_lines = self.formatException(record.exc_info).split('\n')
            formatted_exc = '\n'.join(f"      {line}" for line in exc_lines)
            result += f"\n{self.COLORS['ERROR']}{formatted_exc}{reset}"
        
        return result


class EnhancedPerformanceMonitor:
    """Enhanced performance monitoring with alerting and trend analysis."""
    
    def __init__(self, alert_thresholds: Optional[Dict[str, float]] = None):
        self.metrics_queue = Queue(maxsize=50000)  # Increased capacity
        self.alert_thresholds = alert_thresholds or {
            'http_request': 5000,  # 5 seconds
            'database_query': 2000,  # 2 seconds
            'ai_processing': 10000,  # 10 seconds
        }
        self.lock = threading.Lock()
        
    def record_metric(self, metric_name: str, value: float, unit: str = "ms", 
                     context: Optional[Dict[str, Any]] = None,
                     tags: Optional[Dict[str, str]] = None):
        """Record a performance metric with threshold checking."""
        
        # Check if threshold is exceeded
        threshold_exceeded = False
        for threshold_key, threshold_value in self.alert_thresholds.items():
            if threshold_key in metric_name.lower() and value > threshold_value:
                threshold_exceeded = True
                break
        
        metric = PerformanceMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment=ENVIRONMENT,
            service="androidzen-pro",
            context=context,
            tags=tags,
            threshold_exceeded=threshold_exceeded
        )
        
        try:
            self.metrics_queue.put_nowait(metric)
            
            # Log performance alerts
            if threshold_exceeded:
                logger = logging.getLogger('performance.alerts')
                logger.warning(
                    f"Performance threshold exceeded: {metric_name}",
                    extra={'context': {
                        'metric_name': metric_name,
                        'value': value,
                        'unit': unit,
                        'threshold_exceeded': threshold_exceeded,
                        'tags': tags
                    }}
                )
        except:
            # Queue is full, implement circular buffer behavior
            try:
                self.metrics_queue.get_nowait()
                self.metrics_queue.put_nowait(metric)
            except Empty:
                pass
    
    def get_metrics(self, limit: int = 1000, 
                   metric_name_filter: Optional[str] = None) -> List[PerformanceMetric]:
        """Get recent performance metrics with optional filtering."""
        metrics = []
        temp_storage = []
        count = 0
        
        while count < limit:
            try:
                metric = self.metrics_queue.get_nowait()
                temp_storage.append(metric)
                
                if metric_name_filter is None or metric_name_filter in metric.metric_name:
                    metrics.append(metric)
                    count += 1
            except Empty:
                break
        
        # Put metrics back in queue
        for metric in temp_storage:
            try:
                self.metrics_queue.put_nowait(metric)
            except:
                break
        
        return metrics
    
    def get_performance_summary(self, minutes: int = 15) -> Dict[str, Any]:
        """Get performance summary for the specified time period."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (minutes * 60)
        metrics_by_name = {}
        threshold_violations = 0
        
        for metric in list(self.metrics_queue.queue):
            try:
                metric_time = datetime.fromisoformat(
                    metric.timestamp.replace('Z', '+00:00')
                ).timestamp()
                
                if metric_time > cutoff_time:
                    if metric.metric_name not in metrics_by_name:
                        metrics_by_name[metric.metric_name] = {
                            'values': [],
                            'count': 0,
                            'threshold_violations': 0
                        }
                    
                    metrics_by_name[metric.metric_name]['values'].append(metric.value)
                    metrics_by_name[metric.metric_name]['count'] += 1
                    
                    if metric.threshold_exceeded:
                        metrics_by_name[metric.metric_name]['threshold_violations'] += 1
                        threshold_violations += 1
            except Exception:
                continue
        
        # Calculate statistics
        summary = {
            'period_minutes': minutes,
            'total_metrics': sum(data['count'] for data in metrics_by_name.values()),
            'unique_metrics': len(metrics_by_name),
            'threshold_violations': threshold_violations,
            'metrics': {}
        }
        
        for name, data in metrics_by_name.items():
            if data['values']:
                summary['metrics'][name] = {
                    'count': data['count'],
                    'avg': sum(data['values']) / len(data['values']),
                    'min': min(data['values']),
                    'max': max(data['values']),
                    'threshold_violations': data['threshold_violations']
                }
        
        return summary


class SecurityLogger:
    """Dedicated security event logger with compliance features."""
    
    def __init__(self):
        self.security_logger = logging.getLogger('security.events')
        self.events_queue = Queue(maxsize=10000)
        
    def log_security_event(self, event_type: str, severity: str = "info",
                          user_id: Optional[str] = None, 
                          client_ip: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          endpoint: Optional[str] = None,
                          **details):
        """Log a security event with structured data."""
        
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            client_ip=client_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            details=details,
            environment=ENVIRONMENT,
            service="androidzen-pro"
        )
        
        # Queue event for analysis
        try:
            self.events_queue.put_nowait(event)
        except:
            pass
        
        # Log event
        log_level = getattr(logging, severity.upper(), logging.INFO)
        self.security_logger.log(
            log_level,
            f"Security event: {event_type}",
            extra={'context': {
                'security_event': asdict(event),
                'tags': {'type': 'security', 'event': event_type}
            }}
        )
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security events summary."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        events_by_type = {}
        high_severity_events = 0
        
        for event in list(self.events_queue.queue):
            try:
                event_time = datetime.fromisoformat(
                    event.timestamp.replace('Z', '+00:00')
                ).timestamp()
                
                if event_time > cutoff_time:
                    if event.event_type not in events_by_type:
                        events_by_type[event.event_type] = {'count': 0, 'severities': {}}
                    
                    events_by_type[event.event_type]['count'] += 1
                    
                    if event.severity not in events_by_type[event.event_type]['severities']:
                        events_by_type[event.event_type]['severities'][event.severity] = 0
                    events_by_type[event.event_type]['severities'][event.severity] += 1
                    
                    if event.severity in ['error', 'critical']:
                        high_severity_events += 1
            except Exception:
                continue
        
        return {
            'period_hours': hours,
            'total_events': sum(data['count'] for data in events_by_type.values()),
            'event_types': len(events_by_type),
            'high_severity_events': high_severity_events,
            'events_by_type': events_by_type
        }


class LogContext:
    """Enhanced thread-local context for structured logging with correlation support."""
    
    _context = threading.local()
    
    @classmethod
    def set(cls, **kwargs):
        """Set context values with automatic correlation ID generation."""
        if not hasattr(cls._context, 'data'):
            cls._context.data = {}
        
        # Auto-generate correlation ID if not provided
        if 'correlation_id' not in kwargs and 'request_id' in kwargs:
            kwargs['correlation_id'] = kwargs['request_id']
        
        cls._context.data.update(kwargs)
    
    @classmethod
    def get(cls, key: str = None):
        """Get context value(s)."""
        if not hasattr(cls._context, 'data'):
            return {} if key is None else None
        
        if key is None:
            return cls._context.data.copy()
        return cls._context.data.get(key)
    
    @classmethod
    def clear(cls):
        """Clear all context."""
        if hasattr(cls._context, 'data'):
            cls._context.data.clear()
    
    @classmethod
    def remove(cls, key: str):
        """Remove a specific context key."""
        if hasattr(cls._context, 'data') and key in cls._context.data:
            del cls._context.data[key]
    
    @classmethod
    def with_correlation(cls, correlation_id: str = None):
        """Context manager for correlation tracking."""
        @contextmanager
        def correlation_context():
            old_correlation = cls.get('correlation_id')
            new_correlation = correlation_id or str(uuid.uuid4())
            cls.set(correlation_id=new_correlation)
            try:
                yield new_correlation
            finally:
                if old_correlation:
                    cls.set(correlation_id=old_correlation)
                else:
                    cls.remove('correlation_id')
        
        return correlation_context()


def setup_production_logging(
    app_name: str = "androidzen-pro",
    log_level: str = None,
    log_format: str = None,
    log_file: str = None,
    max_file_size: int = None,
    backup_count: int = None,
    enable_audit_logging: bool = True,
    enable_security_logging: bool = True,
    enable_performance_monitoring: bool = True
) -> Dict[str, Any]:
    """
    Setup production-ready logging configuration with environment-specific defaults.
    
    Returns:
        Dict containing logger instances and monitoring objects
    """
    
    # Environment-specific defaults
    if ENVIRONMENT == "production":
        defaults = {
            "log_level": log_level or "INFO",
            "log_format": log_format or "structured",
            "log_file": log_file or "./logs/androidzen-pro.log",
            "max_file_size": max_file_size or (100 * 1024 * 1024),  # 100MB
            "backup_count": backup_count or 10,
        }
    elif ENVIRONMENT == "staging":
        defaults = {
            "log_level": log_level or "DEBUG",
            "log_format": log_format or "structured",
            "log_file": log_file or "./logs/androidzen-pro-staging.log",
            "max_file_size": max_file_size or (50 * 1024 * 1024),  # 50MB
            "backup_count": backup_count or 5,
        }
    else:  # development
        defaults = {
            "log_level": log_level or ("DEBUG" if DEBUG else "INFO"),
            "log_format": log_format or "console",
            "log_file": log_file,  # Optional in development
            "max_file_size": max_file_size or (10 * 1024 * 1024),  # 10MB
            "backup_count": backup_count or 3,
        }
    
    # Create logs directory
    if defaults["log_file"]:
        log_path = Path(defaults["log_file"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, defaults["log_level"].upper(), logging.INFO))
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if defaults["log_format"] == "structured":
        console_handler.setFormatter(ProductionJSONFormatter(
            include_sensitive_data=(ENVIRONMENT == "development")
        ))
    else:
        console_handler.setFormatter(DevelopmentFormatter())
    
    console_handler.setLevel(getattr(logging, defaults["log_level"].upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    
    # File handlers
    if defaults["log_file"]:
        # Main application log
        file_handler = logging.handlers.RotatingFileHandler(
            filename=defaults["log_file"],
            maxBytes=defaults["max_file_size"],
            backupCount=defaults["backup_count"],
            encoding='utf-8'
        )
        file_handler.setFormatter(ProductionJSONFormatter())
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        
        # Error log
        error_log_file = str(log_path.with_suffix('.error.log'))
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_file,
            maxBytes=defaults["max_file_size"],
            backupCount=defaults["backup_count"],
            encoding='utf-8'
        )
        error_handler.setFormatter(ProductionJSONFormatter())
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # Audit log (for compliance and security events)
        if enable_audit_logging:
            audit_log_file = str(log_path.with_suffix('.audit.log'))
            audit_handler = logging.handlers.RotatingFileHandler(
                filename=audit_log_file,
                maxBytes=defaults["max_file_size"],
                backupCount=defaults["backup_count"] * 2,  # Keep more audit logs
                encoding='utf-8'
            )
            audit_handler.setFormatter(ProductionJSONFormatter())
            audit_handler.setLevel(logging.INFO)
            
            audit_logger = logging.getLogger('audit')
            audit_logger.addHandler(audit_handler)
            audit_logger.setLevel(logging.INFO)
            audit_logger.propagate = False
    
    # Initialize monitoring components
    performance_monitor = EnhancedPerformanceMonitor() if enable_performance_monitoring else None
    security_logger = SecurityLogger() if enable_security_logging else None
    
    # Setup external error tracking
    if ENVIRONMENT == "production":
        setup_external_error_tracking()
    
    # Log initialization
    main_logger = logging.getLogger(app_name)
    main_logger.info(f"Logging system initialized", extra={'context': {
        'environment': ENVIRONMENT,
        'log_level': defaults["log_level"],
        'log_format': defaults["log_format"],
        'log_file': defaults["log_file"],
        'debug_mode': DEBUG,
        'audit_logging': enable_audit_logging,
        'security_logging': enable_security_logging,
        'performance_monitoring': enable_performance_monitoring,
    }})
    
    return {
        'logger': main_logger,
        'performance_monitor': performance_monitor,
        'security_logger': security_logger,
        'log_context': LogContext,
        'config': defaults
    }


def setup_external_error_tracking():
    """Setup external error tracking services for production."""
    sentry_dsn = os.getenv('SENTRY_DSN')
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            
            sentry_logging = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=ENVIRONMENT,
                integrations=[
                    sentry_logging,
                    SqlalchemyIntegration(),
                    FastApiIntegration(auto_enable=True),
                ],
                traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
                profiles_sample_rate=float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1')),
                attach_stacktrace=True,
                send_default_pii=False,  # Don't send PII for privacy
            )
            
            logging.getLogger('sentry').info("Sentry error tracking initialized")
        except ImportError:
            logging.getLogger('sentry').warning("Sentry SDK not available")
        except Exception as e:
            logging.getLogger('sentry').error(f"Failed to initialize Sentry: {e}")


# Convenience decorators
def performance_monitor(operation_name: Optional[str] = None, 
                       threshold: Optional[float] = None):
    """Decorator for automatic performance monitoring."""
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            with LogContext.with_correlation():
                try:
                    result = func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Record metric if performance monitor is available
                    if hasattr(logging.getLogger(), '_performance_monitor'):
                        logging.getLogger()._performance_monitor.record_metric(
                            metric_name=operation_name,
                            value=execution_time,
                            unit="ms",
                            context={'function': func.__name__, 'module': func.__module__}
                        )
                    
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    logging.getLogger(func.__module__).exception(
                        f"Operation failed: {operation_name}",
                        extra={'context': {
                            'operation': operation_name,
                            'execution_time': execution_time / 1000,
                            'error': str(e)
                        }}
                    )
                    raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            with LogContext.with_correlation():
                try:
                    result = await func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000
                    
                    if hasattr(logging.getLogger(), '_performance_monitor'):
                        logging.getLogger()._performance_monitor.record_metric(
                            metric_name=operation_name,
                            value=execution_time,
                            unit="ms",
                            context={'function': func.__name__, 'module': func.__module__}
                        )
                    
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    logging.getLogger(func.__module__).exception(
                        f"Operation failed: {operation_name}",
                        extra={'context': {
                            'operation': operation_name,
                            'execution_time': execution_time / 1000,
                            'error': str(e)
                        }}
                    )
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_exceptions(logger_name: Optional[str] = None):
    """Decorator for automatic exception logging with context preservation."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(
                    f"Exception in {func.__name__}",
                    extra={'context': {
                        'function': func.__name__,
                        'module': func.__module__,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'correlation_id': LogContext.get('correlation_id')
                    }}
                )
                raise
        
        return wrapper
    
    return decorator


# Main setup function for backward compatibility
def setup_logging(*args, **kwargs):
    """Backward compatibility wrapper for setup_production_logging."""
    return setup_production_logging(*args, **kwargs)['logger']


# Prometheus metrics integration
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = None
    start_http_server = generate_latest = None
    CollectorRegistry = None


class PrometheusMetrics:
    """Prometheus metrics collector for application monitoring."""
    
    def __init__(self, registry=None):
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return
            
        self.enabled = True
        self.registry = registry or CollectorRegistry()
        
        # Define application metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.database_queries_total = Counter(
            'database_queries_total',
            'Total number of database queries',
            ['operation', 'table'],
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['operation', 'table'],
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'active_connections',
            'Number of active connections',
            registry=self.registry
        )
        
        self.errors_total = Counter(
            'errors_total',
            'Total number of errors',
            ['error_type', 'severity'],
            registry=self.registry
        )
        
        self.ai_processing_duration = Histogram(
            'ai_processing_duration_seconds',
            'AI processing duration in seconds',
            ['operation', 'model_type'],
            registry=self.registry
        )
        
        self.device_operations_total = Counter(
            'device_operations_total',
            'Total number of device operations',
            ['operation_type', 'device_type', 'status'],
            registry=self.registry
        )
        
        self.websocket_connections = Gauge(
            'websocket_connections',
            'Number of active WebSocket connections',
            registry=self.registry
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.registry
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        if not self.enabled:
            return
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_database_query(self, operation: str, table: str, duration: float):
        """Record database query metrics."""
        if not self.enabled:
            return
        
        self.database_queries_total.labels(
            operation=operation,
            table=table
        ).inc()
        
        self.database_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def record_error(self, error_type: str, severity: str):
        """Record error metrics."""
        if not self.enabled:
            return
        
        self.errors_total.labels(
            error_type=error_type,
            severity=severity
        ).inc()
    
    def record_ai_processing(self, operation: str, model_type: str, duration: float):
        """Record AI processing metrics."""
        if not self.enabled:
            return
        
        self.ai_processing_duration.labels(
            operation=operation,
            model_type=model_type
        ).observe(duration)
    
    def record_device_operation(self, operation_type: str, device_type: str, status: str):
        """Record device operation metrics."""
        if not self.enabled:
            return
        
        self.device_operations_total.labels(
            operation_type=operation_type,
            device_type=device_type,
            status=status
        ).inc()
    
    def update_system_metrics(self):
        """Update system metrics using psutil."""
        if not self.enabled:
            return
        
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.system_disk_usage.set(disk.percent)
            
            # Active connections
            try:
                connections = len(psutil.net_connections())
                self.active_connections.set(connections)
            except (psutil.AccessDenied, OSError):
                pass  # Skip if access is denied
                
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            logging.getLogger('metrics').warning(f"Failed to update system metrics: {e}")
    
    def get_metrics(self):
        """Get current metrics in Prometheus format."""
        if not self.enabled:
            return "# Prometheus metrics not available\n"
        
        # Update system metrics before returning
        self.update_system_metrics()
        
        return generate_latest(self.registry).decode('utf-8')


# Global Prometheus metrics instance
_prometheus_metrics = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """Get the global Prometheus metrics instance."""
    global _prometheus_metrics
    if _prometheus_metrics is None:
        _prometheus_metrics = PrometheusMetrics()
    return _prometheus_metrics


# Export commonly used functions
__all__ = [
    'setup_production_logging',
    'setup_logging',
    'LogContext',
    'performance_monitor',
    'log_exceptions',
    'ProductionJSONFormatter',
    'DevelopmentFormatter',
    'EnhancedPerformanceMonitor',
    'SecurityLogger',
    'PrometheusMetrics',
    'get_prometheus_metrics'
]
