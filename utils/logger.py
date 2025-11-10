"""
Comprehensive logging framework for SnipVault.

Provides structured logging with multiple handlers, log rotation,
and configurable log levels.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        """Format log record with colors."""
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"

        return super().format(record)


def get_log_dir() -> Path:
    """
    Get or create log directory.

    Returns:
        Path to log directory
    """
    log_dir = Path.home() / '.snipvault' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logger(
    name: str = 'snipvault',
    level: str = 'INFO',
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper()))

    # File handler with rotation
    if log_to_file:
        log_dir = get_log_dir()
        log_file = log_dir / f'{name}.log'

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Console handler with colors
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (defaults to 'snipvault')

    Returns:
        Logger instance
    """
    logger_name = name or 'snipvault'

    # If logger doesn't exist, set it up
    if logger_name not in logging.Logger.manager.loggerDict:
        return setup_logger(logger_name)

    return logging.getLogger(logger_name)


def log_function_call(func):
    """
    Decorator to log function calls with arguments and execution time.

    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            ...
    """
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_time = datetime.now()

        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.debug(f"{func.__name__} completed in {execution_time:.2f}ms")

            return result

        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}", exc_info=True)
            raise

    return wrapper


def log_error(error: Exception, context: Optional[str] = None):
    """
    Log an error with context.

    Args:
        error: Exception to log
        context: Additional context about where the error occurred
    """
    logger = get_logger()

    error_msg = f"{type(error).__name__}: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"

    logger.error(error_msg, exc_info=True)


def log_api_call(api_name: str, endpoint: str, status: str, duration_ms: float):
    """
    Log an API call for monitoring.

    Args:
        api_name: Name of the API (e.g., 'Gemini', 'Pinecone')
        endpoint: API endpoint or operation
        status: Success/failure status
        duration_ms: Duration in milliseconds
    """
    logger = get_logger()

    logger.info(
        f"API Call - {api_name}.{endpoint} - Status: {status} - Duration: {duration_ms:.2f}ms"
    )


def log_db_query(query_type: str, table: str, duration_ms: float, rows_affected: Optional[int] = None):
    """
    Log a database query for monitoring.

    Args:
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        duration_ms: Duration in milliseconds
        rows_affected: Number of rows affected
    """
    logger = get_logger()

    msg = f"DB Query - {query_type} on {table} - Duration: {duration_ms:.2f}ms"
    if rows_affected is not None:
        msg += f" - Rows: {rows_affected}"

    logger.debug(msg)


# Default logger instance
default_logger = get_logger()
