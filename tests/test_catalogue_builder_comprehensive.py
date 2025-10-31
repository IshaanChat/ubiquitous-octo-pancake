"""Comprehensive test suite for ServiceNow catalog management functionality."""
import logging
import os
import sys
import tracemalloc
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Start tracemalloc for debugging async/await issues
tracemalloc.start()

# Mark all tests in this module as async tests
pytestmark = pytest.mark.asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from auth.auth_manager import AuthManager
from config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig

from tools.catalogue_builder import (
    ListCatalogItemsParams,
    GetCatalogItemParams,
    CreateCatalogItemParams,
    UpdateCatalogItemParams,
    ListCatalogCategoriesParams,
    CreateCatalogCategoryParams,
    UpdateCatalogCategoryParams,
    list_catalog_items,
    get_catalog_item,
    create_catalog_item,
    update_catalog_item,
    list_catalog_categories,
    create_catalog_category,
    update_catalog_category,
)

logging.basicConfig(level=logging.DEBUG)

# Test Data
MOCK_CATALOG_ITEM = {
    "sys_id": "test_item_001",
    "name": "Test Item",
    "short_description": "Test Description",
    "category": "test_category",
    "active": True,
    "sys_created_on": "2025-10-29 10:00:00",
    "sys_updated_on": "2025-10-29 10:00:00"
}

MOCK_CATALOG_CATEGORY = {
    "sys_id": "test_cat_001",
    "title": "Test Category",
    "description": "Test Category Description",
    "active": True,
    "parent_category": None
}

# Common HTTP Headers for Security
SECURITY_HEADERS = {
    "Date": "Wed, 29 Oct 2025 12:00:00 GMT",
    "X-Request-ID": "test-request-id",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block"
}

@pytest.fixture
def config():
    """Create a test server configuration."""
    return ServerConfig(
        instance_url="https://test.service-now.com",
        auth=AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(
                username="test-user",
                password="test-pass"
            )
        ),
        timeout=30
    )

@pytest.fixture
def auth_manager():
    """Create a mock authentication manager."""
    mock_auth = MagicMock(spec=AuthManager)
    async def get_headers():
        return {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json"
        }
    mock_auth.get_headers = get_headers
    return mock_auth

@pytest.fixture
def mock_client():
    """Create a mock httpx client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    
    # Set up async context manager
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    
    return client

def create_mock_response(status_code=200, data=None, headers=None):
    """Create a mock HTTP response."""
    async def async_response():
        # Create a response object with async methods
        response = AsyncMock()
        response.status_code = status_code
        response.headers = {**SECURITY_HEADERS, **(headers or {})}
        response.text = str(data)
        
        if status_code >= 400:
            err = httpx.HTTPStatusError(
                f"HTTP {status_code}",
                request=AsyncMock(),
                response=response
            )
            err.response = response
            response.raise_for_status.side_effect = err
        
        response.json.return_value = data
        return response
    
    return async_response()

# List Catalog Items Tests
@pytest.mark.asyncio
async def test_list_catalog_items_success(config, auth_manager, mock_client):
    """Test successful listing of catalog items."""
    response_data = {
        "result": [MOCK_CATALOG_ITEM, MOCK_CATALOG_ITEM]
    }
    mock_response = create_mock_response(
        data=response_data,
        headers={"X-Total-Count": "2"}
    )
    mock_client.get.return_value = mock_response
    
    params = ListCatalogItemsParams(
        limit=10,
        offset=0,
        category="test_category",
        active=True
    )
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await list_catalog_items(config, auth_manager, params)
        
        assert len(result["items"]) == 2
        assert result["count"] == 2
        assert result["total"] == 2
        assert result["hasMore"] is False
        assert "timestamp" in result
        assert "request_id" in result
        
        for item in result["items"]:
            assert len(item["sys_id"]) <= 32
            assert len(item["name"]) <= 255
            assert len(item["short_description"]) <= 1000
            assert isinstance(item["active"], bool)

@pytest.mark.asyncio
async def test_list_catalog_items_with_filters(config, auth_manager, mock_client):
    """Test listing catalog items with various filters."""
    mock_response = create_mock_response(
        data={"result": [MOCK_CATALOG_ITEM]},
        headers={"X-Total-Count": "1"}
    )
    mock_client.get.return_value = mock_response
    
    params = ListCatalogItemsParams(
        limit=10,
        offset=0,
        category="test_category",
        query="test query",
        active=True
    )
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await list_catalog_items(config, auth_manager, params)
        
        call_args = mock_client.get.call_args
        query_params = call_args[1]["params"]
        assert query_params["sysparm_limit"] == 10
        assert query_params["sysparm_offset"] == 0
        assert "sysparm_query" in query_params
        assert "cat_item.category" in query_params["sysparm_query"]
        assert "active=true" in query_params["sysparm_query"]
        assert "test query" in query_params["sysparm_query"]

# Get Catalog Item Tests
@pytest.mark.asyncio
async def test_get_catalog_item_success(config, auth_manager, mock_client):
    """Test successful retrieval of a catalog item."""
    item_data = {"result": MOCK_CATALOG_ITEM}
    variables_data = {
        "result": [
            {"name": "var1", "type": "string"},
            {"name": "var2", "type": "integer"}
        ]
    }
    
    mock_item_response = create_mock_response(data=item_data)
    mock_vars_response = create_mock_response(data=variables_data)
    mock_client.get.side_effect = [mock_item_response, mock_vars_response]
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await get_catalog_item(
            config,
            auth_manager,
            GetCatalogItemParams(item_id="test_item_001")
        )
        
        assert response.success is True
        assert response.data["item"]["sys_id"] == "test_item_001"
        assert "variables" in response.data["item"]
        assert len(response.data["item"]["variables"]) == 2

@pytest.mark.asyncio
async def test_get_catalog_item_not_found(config, auth_manager, mock_client):
    """Test getting a non-existent catalog item."""
    mock_response = create_mock_response(status_code=404, data={"error": "Not found"})
    mock_client.get.return_value = mock_response
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await get_catalog_item(
            config,
            auth_manager,
            GetCatalogItemParams(item_id="nonexistent")
        )
        
        assert response.success is False
        assert "not found" in response.message.lower()

# Create Catalog Item Tests
@pytest.mark.asyncio
async def test_create_catalog_item_success(config, auth_manager, mock_client):
    """Test successful creation of a catalog item."""
    mock_response = create_mock_response(data={"result": MOCK_CATALOG_ITEM})
    mock_client.post.return_value = mock_response
    
    params = CreateCatalogItemParams(
        name="Test Item",
        description="Test Description",
        category="test_category",
        template="test_template",
        workflow="test_workflow",
        active=True
    )
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await create_catalog_item(config, auth_manager, params)
        
        assert response.success is True
        assert response.data["item"]["sys_id"] == "test_item_001"
        assert response.data["item"]["name"] == "Test Item"
        
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["name"] == "Test Item"
        assert payload["short_description"] == "Test Description"
        assert payload["category"] == "test_category"
        assert payload["template"] == "test_template"
        assert payload["workflow"] == "test_workflow"
        assert payload["active"] is True

# Update Catalog Item Tests
@pytest.mark.asyncio
async def test_update_catalog_item_success(config, auth_manager, mock_client):
    """Test successful update of a catalog item."""
    updated_item = {**MOCK_CATALOG_ITEM, "name": "Updated Item"}
    mock_response = create_mock_response(data={"result": updated_item})
    mock_client.patch.return_value = mock_response
    
    params = UpdateCatalogItemParams(
        item_id="test_item_001",
        name="Updated Item",
        description="Updated Description",
        category="updated_category",
        active=True
    )
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await update_catalog_item(config, auth_manager, params)
        
        assert response.success is True
        assert response.data["item"]["name"] == "Updated Item"
        
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json"]
        assert payload["name"] == "Updated Item"
        assert payload["short_description"] == "Updated Description"
        assert payload["category"] == "updated_category"
        assert payload["active"] is True

# List Categories Tests
@pytest.mark.asyncio
async def test_list_catalog_categories_success(config, auth_manager, mock_client):
    """Test successful listing of catalog categories."""
    response_data = {
        "result": [MOCK_CATALOG_CATEGORY, MOCK_CATALOG_CATEGORY]
    }
    mock_response = create_mock_response(
        data=response_data,
        headers={"X-Total-Count": "2"}
    )
    mock_client.get.return_value = mock_response
    
    params = ListCatalogCategoriesParams(
        limit=10,
        offset=0,
        query="test",
        active=True
    )
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await list_catalog_categories(config, auth_manager, params)
        
        assert len(result["categories"]) == 2
        assert result["count"] == 2
        assert result["total"] == 2
        assert result["hasMore"] is False

# Create Category Tests
@pytest.mark.asyncio
async def test_create_catalog_category_success(config, auth_manager, mock_client):
    """Test successful creation of a catalog category."""
    mock_response = create_mock_response(data={"result": MOCK_CATALOG_CATEGORY})
    mock_client.post.return_value = mock_response
    
    params = CreateCatalogCategoryParams(
        name="Test Category",
        description="Test Category Description",
        parent_category="parent_cat_001"
    )
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await create_catalog_category(config, auth_manager, params)
        
        assert response.success is True
        assert response.data["category"]["sys_id"] == "test_cat_001"
        assert response.data["category"]["title"] == "Test Category"
        
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["title"] == "Test Category"
        assert payload["description"] == "Test Category Description"
        assert payload["parent_category"] == "parent_cat_001"

# Update Category Tests
@pytest.mark.asyncio
async def test_update_catalog_category_success(config, auth_manager, mock_client):
    """Test successful update of a catalog category."""
    updated_category = {**MOCK_CATALOG_CATEGORY, "title": "Updated Category"}
    mock_response = create_mock_response(data={"result": updated_category})
    mock_client.patch.return_value = mock_response
    
    params = UpdateCatalogCategoryParams(
        category_id="test_cat_001",
        name="Updated Category",
        description="Updated Description",
        parent_category="new_parent_001"
    )
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await update_catalog_category(config, auth_manager, params)
        
        assert response.success is True
        assert response.data["category"]["title"] == "Updated Category"
        
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json"]
        assert payload["title"] == "Updated Category"
        assert payload["description"] == "Updated Description"
        assert payload["parent_category"] == "new_parent_001"

# Error Handling Tests
@pytest.mark.asyncio
async def test_network_error_handling(config, auth_manager, mock_client):
    """Test handling of network errors."""
    
    # Set up network error
    async def raise_network_error(*args, **kwargs):
        raise httpx.NetworkError("Connection failed")
    mock_client.get.side_effect = raise_network_error
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        try:
            await list_catalog_items(
                config,
                auth_manager,
                ListCatalogItemsParams(limit=10, offset=0)
            )
            pytest.fail("Expected ValueError to be raised")
        except ValueError as e:
            assert "Network error" in str(e)
            assert "Connection failed" in str(e)
        
        # Reset side effect for get_catalog_item test
        mock_client.get.side_effect = raise_network_error
        response = await get_catalog_item(
            config,
            auth_manager,
            GetCatalogItemParams(item_id="test_item_001")
        )
        assert response.success is False
        assert "Network error" in response.message
        assert "Connection failed" in response.message
async def test_authentication_error_handling(config, auth_manager, mock_client):
    """Test handling of authentication errors."""
    mock_response = create_mock_response(status_code=401, data={"error": "Unauthorized"})
    mock_client.get.side_effect = [
        mock_response,
        create_mock_response(status_code=401, data={"error": "Unauthorized"}),
    ]

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Test list_catalog_items
        try:
            await list_catalog_items(
                config,
                auth_manager,
                ListCatalogItemsParams(limit=10, offset=0)
            )
            pytest.fail("Expected ValueError to be raised")
        except ValueError as e:
            assert "401" in str(e)

        # Test get_catalog_item
        response = await get_catalog_item(
            config,
            auth_manager,
            GetCatalogItemParams(item_id="test_item_001")
        )
        assert response.success is False
        assert "401" in response.message

async def test_permission_error_handling(config, auth_manager, mock_client):
    """Test handling of permission errors."""
    mock_response = create_mock_response(status_code=403, data={"error": "Forbidden"})
    mock_client.get.side_effect = [
        mock_response,
        create_mock_response(status_code=403, data={"error": "Forbidden"}),
    ]

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Test list_catalog_items
        with pytest.raises(ValueError) as exc_info:
            await list_catalog_items(
                config,
                auth_manager,
                ListCatalogItemsParams(limit=10, offset=0)
            )
        assert "Not authorized" in str(exc_info.value)

        # Test get_catalog_item
        response = await get_catalog_item(
            config,
            auth_manager,
            GetCatalogItemParams(item_id="test_item_001")
        )
        assert response.success is False
        assert "Not authorized" in response.message

