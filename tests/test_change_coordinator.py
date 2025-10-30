"""
Tests for Change Coordinator tool implementation.
"""
import pytest
from unittest.mock import patch, Mock
from test_utils import (
    MOCK_CHANGE_REQUEST_DATA,
    make_mock_snow_client,
    mock_server_config,
    mock_auth_config
)

from tools.change_coordinator import (
    list_change_requests,
    get_change_request,
    create_change_request,
    update_change_request,
    approve_change,
    reject_change,
    ListChangeRequestsParams,
    GetChangeRequestParams,
    CreateChangeRequestParams,
    UpdateChangeRequestParams,
    ApproveChangeParams,
    RejectChangeParams
)

@pytest.mark.asyncio
async def test_list_change_requests():
    """Test listing change requests"""
    params = ListChangeRequestsParams(
        limit=10,
        offset=0,
        state="pending",
        type="normal"
    )
    
    mock_client = make_mock_snow_client({"changes": [MOCK_CHANGE_REQUEST_DATA]})
    
    result = await list_change_requests(mock_server_config, mock_client, params)
    
    assert result is not None
    assert "changes" in result
    assert len(result["changes"]) > 0
    assert result["changes"][0]["number"] == MOCK_CHANGE_REQUEST_DATA["number"]

@pytest.mark.asyncio
async def test_get_change_request():
    """Test getting a specific change request"""
    params = GetChangeRequestParams(change_number="CHG0010001")
    
    mock_client = make_mock_snow_client(MOCK_CHANGE_REQUEST_DATA)
    
    result = await get_change_request(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_CHANGE_REQUEST_DATA["number"]

@pytest.mark.asyncio
async def test_create_change_request():
    """Test creating a change request"""
    params = CreateChangeRequestParams(
        short_description="Test change",
        type="normal",
        risk="3",
        impact="2"
    )
    
    mock_client = make_mock_snow_client(MOCK_CHANGE_REQUEST_DATA)
    
    result = await create_change_request(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_CHANGE_REQUEST_DATA["number"]

@pytest.mark.asyncio
async def test_update_change_request():
    """Test updating a change request"""
    params = UpdateChangeRequestParams(
        change_number="CHG0010001",
        short_description="Updated change",
        state="scheduled"
    )
    
    mock_client = make_mock_snow_client(MOCK_CHANGE_REQUEST_DATA)
    
    result = await update_change_request(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_CHANGE_REQUEST_DATA["number"]

@pytest.mark.asyncio
async def test_approve_change():
    """Test approving a change request"""
    params = ApproveChangeParams(
        change_number="CHG0010001",
        comments="Approved after review"
    )
    
    mock_client = make_mock_snow_client(MOCK_CHANGE_REQUEST_DATA)
    
    result = await approve_change(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_CHANGE_REQUEST_DATA["number"]

@pytest.mark.asyncio
async def test_reject_change():
    """Test rejecting a change request"""
    params = RejectChangeParams(
        change_number="CHG0010001",
        reason="Risk too high"
    )
    
    mock_client = make_mock_snow_client(MOCK_CHANGE_REQUEST_DATA)
    
    result = await reject_change(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_CHANGE_REQUEST_DATA["number"]

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in change operations"""
    params = GetChangeRequestParams(change_number="nonexistent")
    
    # Mock client that raises an error
    error_client = make_mock_snow_client(None)
    error_client.get.side_effect = Exception("Not found")
    
    result = await get_change_request(mock_server_config, error_client, params)
    
    assert result.success is False
    assert result.error is not None
