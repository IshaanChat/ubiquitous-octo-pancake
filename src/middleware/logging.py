"""Middleware for request logging and error handling."""
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request/response details."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request, log details, and return response."""
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(time.time()))
        
        # Log request
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")
        logger.debug(f"Request {request_id} headers: {dict(request.headers)}")
        
        # Record timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response {request_id}: {response.status_code} "
                f"completed in {duration:.2f}s"
            )
            
            # Add timing header
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                f"Request {request_id} failed after {time.time() - start_time:.2f}s: "
                f"{str(e)}"
            )
            raise  # Re-raise the exception for FastAPI's error handlers

class ResponseSizeMiddleware(BaseHTTPMiddleware):
    """Middleware for logging response size."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log response size."""
        response = await call_next(request)
        
        try:
            # Get response size if available
            size = len(response.body) if hasattr(response, "body") else 0
            logger.debug(f"Response size: {size} bytes")
            
            # Add size header for non-streaming responses
            if size > 0:
                response.headers["Content-Length"] = str(size)
            
        except Exception as e:
            logger.warning(f"Failed to calculate response size: {str(e)}")
            
        return response