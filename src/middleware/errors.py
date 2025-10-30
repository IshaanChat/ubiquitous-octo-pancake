"""Error handling middleware and utilities."""
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class ApiError(HTTPException):
    """Custom API error that includes error details."""
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the API error.
        
        Args:
            status_code: HTTP status code
            message: Human readable error message
            error_code: Machine readable error code
            details: Additional error context
        """
        super().__init__(status_code=status_code)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling."""
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Handle the request and catch errors."""
        try:
            return await call_next(request)
            
        except ApiError as e:
            # Handle our custom API errors
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details
                    }
                }
            )
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": f"HTTP_{e.status_code}",
                        "message": str(e.detail),
                        "details": {}
                    }
                }
            )
            
        except Exception as e:
            # Handle unexpected errors
            logger.exception("Unhandled error processing request")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {
                            "type": e.__class__.__name__
                        }
                    }
                }
            )

# Common error codes
class ErrorCodes:
    """Common error codes used across the API."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    BAD_REQUEST = "BAD_REQUEST"
    SERVICENOW_ERROR = "SERVICENOW_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"