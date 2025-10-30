"""
Tests for Service Desk tool implementation.
"""
import pytest
from unittest.mock import patch, Mock
from test_utils import (
    MOCK_INCIDENT_DATA,
    MOCK_USER_DATA,
    make_mock_snow_client,
    mock_server_config,
    mock_auth_config
)

from tools.service_desk import (
    list_incidents,
    get_incident,
    create_incident,
    update_incident,
    add_comment,
    resolve_incident,
    ListIncidentsParams,
    GetIncidentParams,
    CreateIncidentParams,
    UpdateIncidentParams,
    AddCommentParams,
    ResolveIncidentParams
)

@pytest.mark.asyncio
async def test_list_incidents():
    """Test listing incidents"""
    params = ListIncidentsParams(
        limit=10,
        offset=0,
        query="priority=1",
        state="new"
    )
    
    mock_client = make_mock_snow_client({"incidents": [MOCK_INCIDENT_DATA]})
    
    result = await list_incidents(mock_server_config, mock_client, params)
    
    assert result is not None
    assert "incidents" in result
    assert len(result["incidents"]) > 0
    assert result["incidents"][0]["number"] == MOCK_INCIDENT_DATA["number"]

@pytest.mark.asyncio
async def test_get_incident():
    """Test getting a specific incident"""
    params = GetIncidentParams(incident_number="INC0010001")
    
    mock_client = make_mock_snow_client(MOCK_INCIDENT_DATA)
    
    result = await get_incident(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_INCIDENT_DATA["number"]

@pytest.mark.asyncio
async def test_create_incident():
    """Test creating an incident"""
    params = CreateIncidentParams(
        description="Test incident",
        urgency="2",
        impact="2",
        priority="2"
    )
    
    mock_client = make_mock_snow_client(MOCK_INCIDENT_DATA)
    
    result = await create_incident(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_INCIDENT_DATA["number"]

@pytest.mark.asyncio
async def test_update_incident():
    """Test updating an incident"""
    params = UpdateIncidentParams(
        incident_number="INC0010001",
        description="Updated description",
        state="2"
    )
    
    mock_client = make_mock_snow_client(MOCK_INCIDENT_DATA)
    
    result = await update_incident(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_INCIDENT_DATA["number"]

@pytest.mark.asyncio
async def test_add_comment():
    """Test adding a comment to an incident"""
    params = AddCommentParams(
        incident_number="INC0010001",
        comment="Test comment"
    )
    
    mock_client = make_mock_snow_client(MOCK_INCIDENT_DATA)
    
    result = await add_comment(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_INCIDENT_DATA["number"]

@pytest.mark.asyncio
async def test_resolve_incident():
    """Test resolving an incident"""
    params = ResolveIncidentParams(
        incident_number="INC0010001",
        resolution_notes="Issue resolved"
    )
    
    mock_client = make_mock_snow_client(MOCK_INCIDENT_DATA)
    
    result = await resolve_incident(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_INCIDENT_DATA["number"]

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in incident operations"""
    params = GetIncidentParams(incident_number="nonexistent")
    
    # Mock client that raises an error
    error_client = make_mock_snow_client(None)
    error_client.get.side_effect = Exception("Not found")
    
    result = await get_incident(mock_server_config, error_client, params)
    
    assert result.success is False
    assert result.error is not None
