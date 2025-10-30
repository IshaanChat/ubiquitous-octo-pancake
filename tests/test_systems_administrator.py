"""
Tests for Systems Administrator tool implementation.
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from test_utils import (
    MOCK_USER_DATA,
    mock_snow_client,
    mock_server_config,
    mock_auth_config
)

from tools.systems_administrator import (
    list_users,
    get_user,
    create_user,
    update_user,
    list_groups,
    create_group,
    update_group,
    ListUsersParams,
    GetUserParams,
    CreateUserParams,
    UpdateUserParams,
    ListGroupsParams,
    CreateGroupParams,
    UpdateGroupParams
)

@pytest.mark.asyncio
async def test_list_users(mock_snow_client, mock_server_config):
    """Test listing users"""
    params = ListUsersParams(
        limit=10,
        offset=0,
        roles=["admin"],
        department="IT"
    )
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": {"users": [MOCK_USER_DATA]}}
    mock_snow_client.get.return_value = mock_response
    
    result = await list_users(mock_server_config, mock_snow_client, params)
    
    assert result is not None
    assert "users" in result
    assert len(result["users"]) > 0
    assert result["users"][0]["user_name"] == MOCK_USER_DATA["user_name"]

@pytest.mark.asyncio
async def test_get_user(mock_snow_client, mock_server_config):
    """Test getting a specific user"""
    params = GetUserParams(user_id="usr123456")
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": MOCK_USER_DATA}
    mock_snow_client.get.return_value = mock_response
    
    result = await get_user(mock_server_config, mock_snow_client, params)
    
    assert result.success is True
    assert result.data["sys_id"] == MOCK_USER_DATA["sys_id"]

@pytest.mark.asyncio
async def test_create_user(mock_snow_client, mock_server_config):
    """Test creating a user"""
    params = CreateUserParams(
        username="new.user",
        email="new.user@example.com",
        first_name="New",
        last_name="User",
        roles=["itil"]
    )
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": MOCK_USER_DATA}
    mock_snow_client.post.return_value = mock_response
    
    result = await create_user(mock_server_config, mock_snow_client, params)
    
    assert result.success is True
    assert result.data["sys_id"] == MOCK_USER_DATA["sys_id"]

@pytest.mark.asyncio
async def test_update_user(mock_snow_client, mock_server_config):
    """Test updating a user"""
    params = UpdateUserParams(
        user_id="usr123456",
        email="updated.email@example.com",
        active=True
    )
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": MOCK_USER_DATA}
    mock_snow_client.put.return_value = mock_response
    
    result = await update_user(mock_server_config, mock_snow_client, params)
    
    assert result.success is True
    assert result.data["sys_id"] == MOCK_USER_DATA["sys_id"]

@pytest.mark.asyncio
async def test_list_groups(mock_snow_client, mock_server_config):
    """Test listing groups"""
    params = ListGroupsParams(
        limit=10,
        offset=0,
        type="it",
        active=True
    )
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": {"groups": [{"name": "IT Support", "sys_id": "grp123"}]}}
    mock_snow_client.get.return_value = mock_response
    
    result = await list_groups(mock_server_config, mock_snow_client, params)
    
    assert result is not None
    assert "groups" in result
    assert len(result["groups"]) > 0

@pytest.mark.asyncio
async def test_create_group(mock_snow_client, mock_server_config):
    """Test creating a group"""
    params = CreateGroupParams(
        name="New Group",
        description="Test group",
        type="it"
    )
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": {"name": "New Group", "sys_id": "grp123"}}
    mock_snow_client.post.return_value = mock_response
    
    result = await create_group(mock_server_config, mock_snow_client, params)
    
    assert result.success is True
    assert result.data["name"] == "New Group"

@pytest.mark.asyncio
async def test_update_group(mock_snow_client, mock_server_config):
    """Test updating a group"""
    params = UpdateGroupParams(
        group_id="grp123",
        name="Updated Group",
        active=True
    )
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": {"name": "Updated Group", "sys_id": "grp123"}}
    mock_snow_client.put.return_value = mock_response
    
    result = await update_group(mock_server_config, mock_snow_client, params)
    
    assert result.success is True
    assert result.data["name"] == "Updated Group"

@pytest.mark.asyncio
async def test_error_handling(mock_snow_client, mock_server_config):
    """Test error handling in user/group operations"""
    params = GetUserParams(user_id="nonexistent")
    
    # Set up mock to raise an error
    mock_snow_client.get.side_effect = Exception("Not found")
    
    result = await get_user(mock_server_config, mock_snow_client, params)
    
    assert result.success is False
    assert result.error is not None