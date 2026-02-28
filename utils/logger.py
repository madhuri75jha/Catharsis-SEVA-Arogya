"""Logging Configuration for CloudWatch Integration"""
import logging
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, 'service'):
            log_data['service'] = record.service
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'error_code'):
            log_data['error_code'] = record.error_code
        if hasattr(record, 'status'):
            log_data['status'] = record.status
        
        # Add any other extra attributes
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'message', 'pathname', 'process', 'processName', 
                          'relativeCreated', 'thread', 'threadName', 'exc_info', 
                          'exc_text', 'stack_info', 'service', 'operation', 
                          'request_id', 'duration_ms', 'error_code', 'status']:
                if not key.startswith('_'):
                    log_data[key] = value
        
        return json.dumps(log_data)


def setup_logging(log_level: str = 'INFO', json_format: bool = True):
    """
    Configure application logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting (True for CloudWatch)
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional file handler (for temporary debug access)
    log_file_path = os.getenv('LOG_FILE_PATH', 'logs/app.log')
    if log_file_path:
        try:
            log_dir = os.path.dirname(log_file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding='utf-8'
            )
            file_handler.setLevel(numeric_level)

            # Keep file logs human-readable even if console is JSON
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            logging.info(f"File logging enabled at {log_file_path}")
        except Exception as e:
            logging.warning(f"Failed to enable file logging at {log_file_path}: {e}")
    
    # Suppress noisy third-party loggers
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level={log_level}, json_format={json_format}")


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance (wrapper for logging.getLogger).

    Args:
        name: Optional logger name
    """
    return logging.getLogger(name)


class RequestIDContext:
    """Context manager for adding AWS request ID to log records"""
    
    def __init__(self, request_id: str):
        """
        Initialize context with request ID
        
        Args:
            request_id: AWS request ID to add to logs
        """
        self.request_id = request_id
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and modify log record factory"""
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.request_id = self.request_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original log record factory"""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log message with additional context fields
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields to include in log
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=context)
