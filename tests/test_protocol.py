"""
Tests for the MCP protocol implementation.
"""
import pytest
from src.mcp_core.protocol import MCPRequest, MCPResponse

def test_mcp_request_validation():
    """Test MCP request model validation"""
    # Valid request
    request = MCPRequest(
        version="0.1",
        type="request",
        id="test-1",
        tool="servicenow.incident",
        parameters={"operation": "get", "sys_id": "123"}
    )
    assert request.version == "0.1"
    assert request.type == "request"
    assert request.tool == "servicenow.incident"

    # Invalid request (wrong type)
    with pytest.raises(ValueError):
        MCPRequest(
            version="0.1",
            type="invalid",
            id="test-2",
            tool="servicenow.incident",
            parameters={}
        )

def test_mcp_response_validation():
    """Test MCP response model validation"""
    # Valid response
    response = MCPResponse(
        version="0.1",
        type="response",
        id="test-1",
        result={"status": "success"}
    )
    assert response.version == "0.1"
    assert response.type == "response"
    assert response.result == {"status": "success"}

    # Valid error response
    error_response = MCPResponse(
        version="0.1",
        type="error",
        id="test-2",
        error="Something went wrong"
    )
    assert error_response.type == "error"
    assert error_response.error == "Something went wrong"

    # Invalid response (wrong type)
    with pytest.raises(ValueError):
        MCPResponse(
            version="0.1",
            type="invalid",
            id="test-3"
        )