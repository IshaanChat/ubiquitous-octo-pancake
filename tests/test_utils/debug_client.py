"""
Diagnostic test helpers for debugging MCP server tests.
"""
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests import Response

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class _TestDebugger:
    """Helper class for debugging test requests and responses. Internal implementation."""
    
    def __init__(self, app: FastAPI, base_url: str = "http://testserver"):
        """Initialize the debugger.
        
        Args:
            app: FastAPI application instance
            base_url: Base URL for requests
        """
        self.client = TestClient(app)
        self.base_url = base_url
        self.last_response: Optional[Response] = None
        self.last_request_info: Dict[str, Any] = {}
    
    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details."""
        self.last_request_info = {
            "method": method,
            "url": url,
            **kwargs
        }
        
        logger.info(f"\n=== Making {method} request to {url} ===")
        if "json" in kwargs:
            logger.info(f"Request body: {json.dumps(kwargs['json'], indent=2)}")
        if "params" in kwargs:
            logger.info(f"Query params: {kwargs['params']}")
        if "headers" in kwargs:
            logger.info(f"Headers: {kwargs['headers']}")
    
    def _log_response(self, response: Response):
        """Log response details."""
        self.last_response = response
        
        logger.info(f"\n=== Response Status: {response.status_code} ===")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        try:
            json_data = response.json()
            logger.info(f"Response body: {json.dumps(json_data, indent=2)}")
        except json.JSONDecodeError:
            logger.warning("Response is not valid JSON")
            logger.info(f"Raw response: {response.content}")
    
    def get(self, path: str, **kwargs) -> Response:
        """Make a GET request with detailed logging."""
        url = urljoin(self.base_url, path)
        self._log_request("GET", url, **kwargs)
        response = self.client.get(url, **kwargs)
        self._log_response(response)
        return response
    
    def post(self, path: str, **kwargs) -> Response:
        """Make a POST request with detailed logging."""
        url = urljoin(self.base_url, path)
        self._log_request("POST", url, **kwargs)
        response = self.client.post(url, **kwargs)
        self._log_response(response)
        return response
    
    def debug_last_interaction(self):
        """Print debug information about the last request/response."""
        if not self.last_request_info or not self.last_response:
            logger.warning("No previous request/response to debug")
            return
        
        logger.info("\n=== Last Request/Response Debug Information ===")
        logger.info("REQUEST:")
        logger.info(json.dumps(self.last_request_info, indent=2))
        
        logger.info("\nRESPONSE:")
        logger.info(f"Status: {self.last_response.status_code}")
        logger.info(f"Headers: {dict(self.last_response.headers)}")
        try:
            body = self.last_response.json()
            logger.info(f"Body: {json.dumps(body, indent=2)}")
        except json.JSONDecodeError:
            logger.info(f"Raw body: {self.last_response.content}")

@pytest.fixture
def debug_client(app: FastAPI) -> _TestDebugger:
    """Create a test client with debugging capabilities."""
    return _TestDebugger(app)