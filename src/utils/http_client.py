"""HTTP client utilities for ServiceNow API interactions."""
import asyncio
import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import httpx
from config import ServerConfig
from auth.auth_manager import AuthManager

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API requests."""
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self._cleanup_threshold = 1000  # Cleanup history when this many requests accumulate
        self.logger = logging.getLogger(__name__ + ".RateLimiter")
        self.logger.info(
            f"Initialized rate limiter with {requests_per_minute} requests per minute"
        )

    async def acquire(self):
        """Acquire permission to make a request."""
        now = datetime.now()
        self._cleanup_old_requests(now)
        
        # Check if we're at the rate limit
        minute_ago = now - timedelta(minutes=1)
        recent_requests = len([r for r in self.requests if r > minute_ago])
        
        self.logger.debug(
            f"Rate limit check: {recent_requests}/{self.requests_per_minute} "
            f"requests in last minute"
        )
        
        if recent_requests >= self.requests_per_minute:
            # Calculate delay needed
            oldest_recent = min([r for r in self.requests if r > minute_ago])
            delay = (oldest_recent + timedelta(minutes=1) - now).total_seconds()
            if delay > 0:
                self.logger.warning(
                    f"Rate limit reached ({recent_requests} requests in last minute). "
                    f"Waiting {delay:.2f} seconds"
                )
                await asyncio.sleep(delay)
        
        self.requests.append(now)
        self.logger.debug("Request permitted")

    def _cleanup_old_requests(self, now: datetime):
        """Remove old requests from history."""
        if len(self.requests) > self._cleanup_threshold:
            minute_ago = now - timedelta(minutes=1)
            self.requests = [r for r in self.requests if r > minute_ago]

def get_secure_client(timeout: int) -> httpx.AsyncClient:
    """
    Create an HTTPX client with secure defaults.
    
    Args:
        timeout: Request timeout in seconds
    
    Returns:
        Configured HTTPX client
    """
    client_logger = logging.getLogger(__name__ + ".HttpClient")
    
    # Log client creation
    client_logger.info(
        f"Creating HTTP client with timeout={timeout}s, "
        "SSL verification=True, HTTP/2=True"
    )
    
    limits = httpx.Limits(
        max_keepalive_connections=5,
        max_connections=10,
        keepalive_expiry=5.0
    )
    
    client_logger.debug(
        f"Connection limits: max_keepalive={limits.max_keepalive_connections}, "
        f"max_connections={limits.max_connections}, "
        f"keepalive_expiry={limits.keepalive_expiry}s"
    )
    
    return httpx.AsyncClient(
        timeout=timeout,
        verify=True,  # Enforce SSL verification
        http2=False,  # Disable HTTP/2 to avoid requiring h2 package
        limits=limits,
        # Enable request/response logging
        event_hooks={
            'request': [
                lambda r: client_logger.debug(
                    f"Starting request: {r.method} {r.url} - "
                    f"Headers: {dict(r.headers)}"
                )
            ],
            'response': [
                lambda r: client_logger.debug(
                    f"Received response: {r.status_code} - "
                    f"Headers: {dict(r.headers)}"
                )
            ]
        }
    )

def get_secure_headers(auth_headers: Dict[str, str]) -> Dict[str, str]:
    """
    Enhance headers with security defaults.
    
    Args:
        auth_headers: Authentication headers
    
    Returns:
        Enhanced headers with security defaults
    """
    headers = auth_headers.copy()
    headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block"
    })
    return headers

def sanitize_query_param(value: str, max_length: int = 100) -> str:
    """
    Sanitize a query parameter value.
    
    Args:
        value: Value to sanitize
        max_length: Maximum length allowed
    
    Returns:
        Sanitized value
    """
    # Remove potential injection characters
    safe_value = value.replace('^', '').replace('=', '')
    # Limit length
    return safe_value[:max_length]

def build_sysparm_query(filters: Dict[str, Any]) -> Optional[str]:
    """
    Build a ServiceNow sysparm_query from filters.
    
    Args:
        filters: Dictionary of filter conditions
    
    Returns:
        Query string or None if no filters
    """
    query_parts = []
    
    for field, value in filters.items():
        if value is not None:
            if isinstance(value, bool):
                query_parts.append(f"{field}={str(value).lower()}")
            else:
                safe_value = sanitize_query_param(str(value))
                query_parts.append(f"{field}={safe_value}")
    
    return "^".join(query_parts) if query_parts else None

async def make_request(
    method: str,
    url: str,
    config: ServerConfig,
    auth_manager: AuthManager,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Make a secure HTTP request to ServiceNow with retries and rate limiting.
    
    Args:
        method: HTTP method
        url: Request URL
        config: Server configuration
        auth_manager: Authentication manager
        params: Query parameters
        json_data: JSON request body
        max_retries: Maximum number of retries
    
    Returns:
        Response data
    
    Raises:
        httpx.HTTPStatusError: For unrecoverable HTTP errors
        httpx.NetworkError: For network-related errors
        ValueError: For validation errors
    """
    request_id = f"{method}_{int(time.time() * 1000)}"
    request_logger = logging.getLogger(__name__ + f".request.{request_id}")
    
    request_logger.info(
        f"Initiating {method} request to {url}\n"
        f"Configuration:\n"
        f"- Timeout: {config.timeout}s\n"
        f"- Max retries: {max_retries}\n"
        f"- Rate limit: {config.rate_limit} requests/minute"
    )
    
    if params:
        request_logger.debug(f"Query parameters: {params}")
    if json_data:
        request_logger.debug(f"Request body: {json_data}")
    
    headers = get_secure_headers(await auth_manager.aget_headers())
    request_logger.debug(f"Request headers: {headers}")
    
    rate_limiter = RateLimiter(requests_per_minute=config.rate_limit or 100)
    retry_count = 0
    last_error = None
    
    request_logger.info("Starting request execution")
    
    while retry_count < max_retries:
        try:
            # Wait for rate limiter
            await rate_limiter.acquire()
            
            # Log request details at debug level
            logger.debug(f"Making {method} request to {url}")
            logger.debug(f"Params: {params}")
            logger.debug(f"Headers: {headers}")
            if json_data:
                logger.debug(f"Request body: {json_data}")
            
            async with get_secure_client(config.timeout) as client:
                start_time = time.time()
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers
                )
                duration = time.time() - start_time
                
                # Log response timing
                logger.info(f"{method} {url} completed in {duration:.2f}s with status {response.status_code}")
                
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [401, 403]:
                        # Auth errors - try to refresh token and retry
                        if await auth_manager.refresh():
                            headers = get_secure_headers(await auth_manager.aget_headers())
                            retry_count += 1
                            continue
                        raise  # Re-raise if refresh failed
                    elif e.response.status_code == 429:
                        # Rate limit hit - wait and retry
                        retry_after = int(e.response.headers.get('Retry-After', '60'))
                        logger.warning(f"Rate limit hit, waiting {retry_after}s before retry")
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                    elif e.response.status_code >= 500:
                        # Server errors - retry with backoff
                        if retry_count < max_retries - 1:
                            wait_time = 2 ** retry_count
                            logger.warning(f"Server error, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            retry_count += 1
                            continue
                        raise  # Re-raise if max retries reached
                    else:
                        raise  # Re-raise other status errors
                
                # Parse response
                try:
                    data = await response.json()
                    logger.debug(f"Response data: {data}")
                    return data
                except ValueError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    raise ValueError(f"Invalid JSON response: {str(e)}")
                
        except httpx.TransportError as e:
            logger.error(f"Network error occurred: {str(e)}")
            last_error = e
            if retry_count < max_retries - 1:
                wait_time = 2 ** retry_count
                logger.warning(f"Network error, retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
                retry_count += 1
                continue
            raise  # Re-raise if max retries reached
            
    # If we get here, we've exhausted retries
    if last_error:
        raise last_error
    raise RuntimeError("Max retries exceeded")
