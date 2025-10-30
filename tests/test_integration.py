"""
Integration tests for the ServiceNow MCP server.
"""
import json
import logging
import os
from typing import AsyncGenerator, Dict, Any

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig
from main import app
from mcp_core.protocol import MCPRequest, MCPResponse
from test_utils import TestDebugger
from tests.test_utils.mock_data import (
    MOCK_CATALOG_ITEMS,
    MOCK_CATALOG_CATEGORIES,
    MOCK_MCP_SUCCESS
)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Load test environment
load_dotenv("tests/.env.test")


@pytest.fixture
def test_config() -> ServerConfig:
    """Create test server configuration."""
    return ServerConfig(
        instance_url=f"https://{os.getenv('SERVICENOW_INSTANCE')}",
        auth=AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(
                username=os.getenv("SERVICENOW_USERNAME"),
                password=os.getenv("SERVICENOW_PASSWORD")
            )
        ),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        timeout=int(os.getenv("REQUEST_TIMEOUT", "5"))
    )


@pytest.fixture
def debug_api(test_config: ServerConfig) -> TestDebugger:
    """Create test debug client."""
    return TestDebugger(app)
@pytest.fixture
def client(test_config: ServerConfig) -> TestClient:
    """Create test client."""
    app.state.config = test_config
    return TestClient(app, base_url="http://testserver")

def test_health_check(client: TestClient, debug_api: TestDebugger):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    
    # Print debug info if needed
    debug_api.debug_last_interaction()


def test_list_tools(client: TestClient, debug_api: TestDebugger):
    """Test listing available tools."""
    response = client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    
    # Print debug info if needed
    debug_api.debug_last_interaction()
    assert isinstance(data["tools"], dict)


def test_list_incidents(client: TestClient, debug_api: TestDebugger):
    """Test listing incidents through MCP."""
    request = MCPRequest(
        version="1.0",
        type="request",
        id="test-1",
        tool="service_desk.list_incidents",
        parameters={"limit": 5}
    )
    response = client.post("/mcp", json=request.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["type"] in ["response", "error"]
    assert data["id"] == "test-1"
    
    # Print debug info if needed
    debug_api.debug_last_interaction()


def test_get_incident(client: TestClient, debug_api: TestDebugger):
    """Test getting a specific incident through MCP."""
    # First list incidents to get a valid incident number
    list_request = MCPRequest(
        version="1.0",
        type="request",
        id="test-list",
        tool="service_desk.list_incidents",
        parameters={"limit": 1}
    )
    list_response = client.post("/mcp", json=list_request.model_dump())
    assert list_response.status_code == 200
    list_data = list_response.json()
    
    # Print debug info for list request
    debug_api.debug_last_interaction()
    
    if list_data["type"] == "response" and list_data.get("result", {}).get("incidents"):
        incident = list_data["result"]["incidents"][0]
        incident_number = incident["number"]
        
        # Now test getting this specific incident
        get_request = MCPRequest(
            version="1.0",
            type="request",
            id="test-get",
            tool="service_desk.get_incident",
            parameters={"incident_number": incident_number}
        )
        get_response = client.post("/mcp", json=get_request.model_dump())
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["type"] in ["response", "error"]
        assert get_data["id"] == "test-get"
        
        # Print debug info for get request
        debug_api.debug_last_interaction()
        
        if get_data["type"] == "response":
            result = get_data["result"]
            assert "incident" in result
            assert result["incident"]["number"] == incident_number
