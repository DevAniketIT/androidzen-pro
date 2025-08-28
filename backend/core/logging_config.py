"""
Comprehensive logging configuration for AndroidZen Pro.
Provides structured logging, performance monitoring, error tracking, and debug capabilities.
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


@dataclass
class LogEntry:
    """Structured log entry with contextual information."""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    execution_time: Optional[float] = None
    extra_data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    error_type: Optional[str] = None


@dataclass
class PerformanceMetric:
    """Performance monitoring metric."""
    metric_name: str
    value: float
    unit: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get contextual information
        context = getattr(record, 'context', {})
        
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
            request_id=context.get('request_id'),
            user_id=context.get('user_id'),
            device_id=context.get('device_id'),
            session_id=context.get('session_id'),
            execution_time=context.get('execution_time'),
            extra_data=context.get('extra_data'),
            stack_trace=self.format_exception(record.exc_info) if record.exc_info else None,
            error_type=record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else None
        )
        
        return json.dumps(asdict(log_entry), default=str, ensure_ascii=False)
    
    def format_exception(self, exc_info) -> str:
        """Format exception information."""
        if exc_info:
            return ''.join(traceback.format_exception(*exc_info))
        return None


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        context = getattr(record, 'context', {})
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format basic log message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_parts = [
            f"{color}[{record.levelname}]{reset}",
            f"{timestamp}",
            f"{record.name}",
            f"{record.funcName}:{record.lineno}",
        ]
        
        # Add contextual information if available
        if context.get('request_id'):
            log_parts.append(f"req:{context['request_id'][:8]}")
        if context.get('user_id'):
            log_parts.append(f"user:{context['user_id']}")
        if context.get('device_id'):
            log_parts.append(f"device:{context['device_id']}")
        if context.get('execution_time'):
            log_parts.append(f"time:{context['execution_time']:.3f}s")
        
        header = " | ".join(log_parts)
        message = record.getMessage()
        
        result = f"{header} - {message}"
        
        # Add exception information
        if record.exc_info:
            result += f"\n{self.formatException(record.exc_info)}"
        
        return result


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self):
        self.metrics_queue = Queue(maxsize=10000)
        self.metrics_storage: List[PerformanceMetric] = []
        self.lock = threading.Lock()
        
    def record_metric(self, metric_name: str, value: float, unit: str = "ms", 
                     context: Optional[Dict[str, Any]] = None,
                     tags: Optional[Dict[str, str]] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.now(timezone.utc).isoformat(),
            context=context,
            tags=tags
        )
        
        try:
            self.metrics_queue.put_nowait(metric)
        except:
            # Queue is full, drop oldest metric
            try:
                self.metrics_queue.get_nowait()
                self.metrics_queue.put_nowait(metric)
            except Empty:
                pass
    
    def get_metrics(self, limit: int = 100) -> List[PerformanceMetric]:
        """Get recent performance metrics."""
        metrics = []
        count = 0
        
        while count < limit:
            try:
                metric = self.metrics_queue.get_nowait()
                metrics.append(metric)
                count += 1
            except Empty:
                break
        
        return metrics
    
    def get_average_metric(self, metric_name: str, minutes: int = 5) -> Optional[float]:
        """Get average value for a metric over the specified time period."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (minutes * 60)
        values = []
        
        # This is a simplified implementation
        # In production, you might want to use a proper time-series database
        for metric in list(self.metrics_queue.queue):
            if (metric.metric_name == metric_name and 
                datetime.fromisoformat(metric.timestamp.replace('Z', '+00:00')).timestamp() > cutoff_time):
                values.append(metric.value)
        
        return sum(values) / len(values) if values else None


class ErrorTracker:
    """Error tracking and reporting system."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        
    def track_error(self, error_type: str, error_message: str, 
                   context: Optional[Dict[str, Any]] = None,
                   stack_trace: Optional[str] = None):
        """Track an error occurrence."""
        with self.lock:
            # Increment error count
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # Add to error history
            error_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': error_type,
                'message': error_message,
                'context': context or {},
                'stack_trace': stack_trace,
                'count': self.error_counts[error_type]
            }
            
            self.error_history.append(error_entry)
            
            # Keep only last 1000 errors
            if len(self.error_history) > 1000:
                self.error_history = self.error_history[-1000:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics."""
        with self.lock:
            return {
                'total_errors': sum(self.error_counts.values()),
                'error_types': len(self.error_counts),
                'error_counts': self.error_counts.copy(),
                'recent_errors': self.error_history[-10:]  # Last 10 errors
            }


class LogContext:
    """Thread-local context for structured logging."""
    
    _context = threading.local()
    
    @classmethod
    def set(cls, **kwargs):
        """Set context values."""
        if not hasattr(cls._context, 'data'):
            cls._context.data = {}
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


class AndroidZenLogger:
    """Main logger class with enhanced functionality."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.performance_monitor = PerformanceMonitor()
        self.error_tracker = ErrorTracker()
    
    def _log_with_context(self, level: int, message: str, *args, 
                         context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log message with contextual information."""
        # Merge context with thread-local context
        full_context = LogContext.get()
        if context:
            full_context.update(context)
        
        # Create log record with context
        extra = kwargs.copy()
        extra['context'] = full_context
        
        self.logger.log(level, message, *args, extra=extra)
        
        # Track errors
        if level >= logging.ERROR:
            error_type = kwargs.get('exc_info', [None])[0]
            if error_type:
                error_type = error_type.__name__
            else:
                error_type = 'UnknownError'
            
            self.error_tracker.track_error(
                error_type=error_type,
                error_message=message % args if args else message,
                context=full_context,
                stack_trace=traceback.format_stack() if not kwargs.get('exc_info') else None
            )
    
    def debug(self, message: str, *args, context: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.DEBUG, message, *args, context=context, **kwargs)
    
    def info(self, message: str, *args, context: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.INFO, message, *args, context=context, **kwargs)
    
    def warning(self, message: str, *args, context: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.WARNING, message, *args, context=context, **kwargs)
    
    def error(self, message: str, *args, context: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.ERROR, message, *args, context=context, **kwargs)
    
    def critical(self, message: str, *args, context: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.CRITICAL, message, *args, context=context, **kwargs)
    
    def exception(self, message: str, *args, context: Optional[Dict[str, Any]] = None, **kwargs):
        kwargs['exc_info'] = True
        self.error(message, *args, context=context, **kwargs)
    
    @contextmanager
    def performance_context(self, operation_name: str, 
                           context: Optional[Dict[str, Any]] = None,
                           tags: Optional[Dict[str, str]] = None):
        """Context manager for performance monitoring."""
        start_time = time.time()
        operation_id = str(uuid.uuid4())[:8]
        
        # Set operation context
        LogContext.set(operation_id=operation_id, operation=operation_name)
        
        self.info(f"Starting operation: {operation_name}", 
                 context={'operation_id': operation_id})
        
        try:
            yield
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Record performance metric
            self.performance_monitor.record_metric(
                metric_name=f"operation.{operation_name}",
                value=execution_time,
                unit="ms",
                context=context,
                tags=tags
            )
            
            self.info(f"Completed operation: {operation_name}", 
                     context={
                         'operation_id': operation_id,
                         'execution_time': execution_time / 1000  # Convert back to seconds for logging
                     })
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            self.exception(f"Failed operation: {operation_name} - {str(e)}", 
                          context={
                              'operation_id': operation_id,
                              'execution_time': execution_time / 1000,
                              'error': str(e)
                          })
            raise
        finally:
            LogContext.remove('operation_id')
            LogContext.remove('operation')


def setup_logging(
    app_name: str = "androidzen-pro",
    log_level: str = "INFO",
    log_format: str = "structured",  # "structured" or "console"
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_performance_monitoring: bool = True,
    enable_error_tracking: bool = True,
    environment: str = "development"
) -> AndroidZenLogger:
    """
    Setup comprehensive logging configuration.
    
    Args:
        app_name: Application name for log identification
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format type ("structured" for JSON, "console" for human-readable)
        log_file: Optional log file path
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
        enable_performance_monitoring: Enable performance monitoring
        enable_error_tracking: Enable error tracking
    
    Returns:
        AndroidZenLogger instance
    """
    
    # Create logs directory if logging to file
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "structured":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(ColoredConsoleFormatter())
    
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(StructuredFormatter())
        file_handler.setLevel(logging.DEBUG)  # File gets all logs
        root_logger.addHandler(file_handler)
        
        # Separate error file
        error_log_file = str(log_path.with_suffix('.error.log'))
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setFormatter(StructuredFormatter())
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
    
    # Create main application logger
    main_logger = AndroidZenLogger(app_name)
    
    # Set debug mode for development
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    if debug_mode:
        root_logger.setLevel(logging.DEBUG)
        console_handler.setLevel(logging.DEBUG)
        main_logger.info("Debug mode enabled")
    
    # Production-specific configurations
    if environment.lower() == "production":
        # Force structured logging in production
        if console_handler.formatter.__class__.__name__ != "StructuredFormatter":
            console_handler.setFormatter(StructuredFormatter())
        
        # Ensure INFO level minimum in production
        if root_logger.level < logging.INFO:
            root_logger.setLevel(logging.INFO)
            console_handler.setLevel(logging.INFO)
        
        # Add JSON audit log handler for production
        if log_file:
            audit_log_file = str(log_path.with_suffix('.audit.log'))
            audit_handler = logging.handlers.RotatingFileHandler(
                filename=audit_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            audit_handler.setFormatter(StructuredFormatter())
            audit_handler.setLevel(logging.INFO)
            
            # Create audit logger for security and business events
            audit_logger = logging.getLogger('audit')
            audit_logger.addHandler(audit_handler)
            audit_logger.setLevel(logging.INFO)
            audit_logger.propagate = False  # Don't propagate to root logger
    
    # Setup external error tracking if configured
    sentry_dsn = os.getenv('SENTRY_DSN')
    if sentry_dsn and environment.lower() == "production":
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            
            sentry_logging = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[sentry_logging],
                traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
                environment=environment
            )
            main_logger.info("Sentry error tracking initialized")
        except ImportError:
            main_logger.warning("Sentry SDK not installed, skipping error tracking setup")
        except Exception as e:
            main_logger.error(f"Failed to initialize Sentry: {e}")
    
    main_logger.info(f"Logging initialized for {app_name}", 
                    context={
                        'environment': environment,
                        'log_level': log_level,
                        'log_format': log_format,
                        'log_file': log_file,
                        'debug_mode': debug_mode,
                        'performance_monitoring': enable_performance_monitoring,
                        'error_tracking': enable_error_tracking,
                        'sentry_enabled': bool(sentry_dsn)
                    })
    
    return main_logger


def performance_monitor(operation_name: Optional[str] = None):
    """Decorator for automatic performance monitoring."""
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = AndroidZenLogger(func.__module__)
            with logger.performance_context(operation_name):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = AndroidZenLogger(func.__module__)
            with logger.performance_context(operation_name):
                return await func(*args, **kwargs)
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    
    return decorator


def log_exceptions(logger_name: Optional[str] = None):
    """Decorator for automatic exception logging."""
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = AndroidZenLogger(logger_name or func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = AndroidZenLogger(logger_name or func.__module__)
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    
    return decorator


# Convenience functions
def get_logger(name: str) -> AndroidZenLogger:
    """Get an AndroidZen logger instance."""
    return AndroidZenLogger(name)


def set_request_context(request_id: str, user_id: Optional[str] = None, 
                       device_id: Optional[str] = None, session_id: Optional[str] = None):
    """Set request context for structured logging."""
    LogContext.set(
        request_id=request_id,
        user_id=user_id,
        device_id=device_id,
        session_id=session_id
    )


def clear_request_context():
    """Clear request context."""
    LogContext.clear()
