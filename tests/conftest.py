"""
Test configuration and fixtures.
"""
import os
import sys
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock
from tests.test_utils.debug_client import DebugClientHelper as TestDebugger
# Add src and tests directories to Python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
tests_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.extend([src_dir, tests_dir])

from config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig

@pytest.fixture(scope="session")
def test_config() -> ServerConfig:
    """Create test server configuration."""
    return ServerConfig(
        instance_url=f"https://{os.getenv('SERVICENOW_INSTANCE')}",
        auth=AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(
                username=os.getenv("SERVICENOW_USERNAME", "test_user"),
                password=os.getenv("SERVICENOW_PASSWORD", "test_pass")
            )
        ),
        debug=True,
        timeout=5
    )

@pytest.fixture
def test_app(test_config: ServerConfig) -> FastAPI:
    """Create a test FastAPI application."""
    from main import app
    app.state.config = test_config
    return app

@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)

@pytest.fixture
def debug_api(test_app: FastAPI) -> TestDebugger:
    """Create a test client with debugging capabilities."""
    return TestDebugger(test_app)

@pytest.fixture
def mock_snow_client():
    """Create a mock ServiceNow client"""
    return Mock()

def pytest_collection_modifyitems(items):
    """Add markers based on test location and name."""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        if "api" in item.nodeid:
            item.add_marker(pytest.mark.api)
