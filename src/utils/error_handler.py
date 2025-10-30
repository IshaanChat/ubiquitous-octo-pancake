"""Common error handling utilities."""
import logging
from typing import Any, Dict, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class ServiceNowError(Exception):
    """Base error for ServiceNow API interactions."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

def handle_http_error(
    e: httpx.HTTPStatusError,
    response_class: Type[T],
    item_type: str
) -> T:
    """
    Handle HTTP errors and return appropriate responses.
    
    Args:
        e: HTTP error
        response_class: Response model class
        item_type: Type of item being handled (e.g., "catalog item", "category")
    
    Returns:
        Error response
    """
    logger.error(f"HTTP error for {item_type}: %s", str(e))
    status_code = e.response.status_code
    
    if status_code == 401:
        return response_class(
            success=False,
            message="Authentication failed",
            data=None
        )
    elif status_code == 403:
        return response_class(
            success=False,
            message=f"Not authorized to access this {item_type}",
            data=None
        )
    elif status_code == 404:
        return response_class(
            success=False,
            message=f"{item_type.title()} not found",
            data=None
        )
    else:
        return response_class(
            success=False,
            message=f"Failed to access {item_type}: {e.response.text}",
            data=None
        )

def handle_network_error(
    e: Exception,
    response_class: Type[T],
    item_type: str
) -> T:
    """
    Handle network errors and return appropriate responses.
    
    Args:
        e: Network error
        response_class: Response model class
        item_type: Type of item being handled
    
    Returns:
        Error response
    """
    logger.error(f"Network error for {item_type}: %s", str(e))
    return response_class(
        success=False,
        message=f"Network error while accessing {item_type}: {str(e)}",
        data=None
    )

def handle_unexpected_error(
    e: Exception,
    response_class: Type[T],
    item_type: str
) -> T:
    """
    Handle unexpected errors and return appropriate responses.
    
    Args:
        e: Unexpected error
        response_class: Response model class
        item_type: Type of item being handled
    
    Returns:
        Error response
    """
    logger.exception(f"Unexpected error for {item_type}")
    return response_class(
        success=False,
        message=f"Unexpected error while accessing {item_type}: {str(e)}",
        data=None
    )