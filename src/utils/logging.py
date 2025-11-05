"""Logging configuration and utilities."""
import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Optional

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "lineno": record.lineno,
            "message": record.getMessage(),
        }
        # Include extras when present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
    log_json: bool = False,
) -> None:
    """Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs to stdout only.
        log_format: Optional custom log format. Uses default if None.
        max_bytes: Maximum size of each log file before rotation.
        backup_count: Number of backup log files to keep.
    """
    # Default format includes timestamp, level, logger name, and message
    if log_format is None:
        log_format = (
            "%(asctime)s - %(levelname)-8s - [%(name)s:%(lineno)d] - "
            "%(message)s - {%(pathname)s}"
        )
    
    # Create formatter (optionally JSON)
    if log_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())
    
    # Remove any existing handlers
    root_logger.handlers = []
    
    # Always add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if log file specified
    if log_file:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Create module loggers with appropriate levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Name for the logger, typically __name__
        
    Returns:
        Logger instance configured with standard formatting
    """
    return logging.getLogger(name)
