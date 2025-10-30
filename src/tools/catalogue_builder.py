"""
Catalog Builder tools for ServiceNow MCP integration.
Handles service catalog and category management.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx
import inspect
from pydantic import BaseModel, Field

from auth.auth_manager import AuthManager
from config import ServerConfig

# Field length limits
FIELD_LENGTHS = {
    "sys_id": 32,
    "name": 255,
    "short_description": 1000,
    "description": 4000,
    "title": 255
}


logger = logging.getLogger(__name__)


async def _maybe_await(callable_or_awaitable, *args, **kwargs):
    """Call a function and await the result if it is awaitable.

    Supports both sync and async httpx Response methods so tests using
    AsyncMock and real httpx behave consistently.
    """
    try:
        result = callable_or_awaitable(*args, **kwargs)
    except Exception:
        # Propagate exceptions from the underlying call (e.g., raise_for_status)
        raise
    if inspect.isawaitable(result):
        return await result
    return result


async def _get_auth_headers(auth_manager: AuthManager) -> Dict[str, str]:
    """Get auth headers supporting both async and sync getters.

    Tries `aget_headers` then `get_headers`, awaiting as needed.
    Ensures a dict is returned.
    """
    headers: Any = {}
    getter = None
    if hasattr(auth_manager, "aget_headers"):
        getter = getattr(auth_manager, "aget_headers")
    elif hasattr(auth_manager, "get_headers"):
        getter = getattr(auth_manager, "get_headers")
    if getter:
        try:
            headers = await _maybe_await(getter)
        except Exception:
            headers = {}
    if not isinstance(headers, dict):
        headers = {}
    return headers


class ListCatalogItemsParams(BaseModel):
    """Parameters for listing service catalog items."""
    
    limit: int = Field(10, description="Maximum number of catalog items to return")
    offset: int = Field(0, description="Offset for pagination")
    category: Optional[str] = Field(None, description="Filter by category")
    query: Optional[str] = Field(None, description="Search query for catalog items")
    active: bool = Field(True, description="Whether to only return active catalog items")


class GetCatalogItemParams(BaseModel):
    """Parameters for getting a specific service catalog item."""
    
    item_id: str = Field(..., description="Catalog item ID or sys_id")


class CreateCatalogItemParams(BaseModel):
    """Parameters for creating a new service catalog item."""
    
    name: str = Field(..., description="Name of the catalog item")
    description: str = Field(..., description="Description of the catalog item")
    category: Optional[str] = Field(None, description="Category ID for the item")
    template: Optional[str] = Field(None, description="Template for the catalog item")
    workflow: Optional[str] = Field(None, description="Workflow for the catalog item")
    active: bool = Field(True, description="Whether the item is active")


class UpdateCatalogItemParams(BaseModel):
    """Parameters for updating an existing catalog item."""
    
    item_id: str = Field(..., description="Catalog item ID to update")
    name: Optional[str] = Field(None, description="Name of the catalog item")
    description: Optional[str] = Field(None, description="Description of the catalog item")
    category: Optional[str] = Field(None, description="Category ID for the item")
    active: Optional[bool] = Field(None, description="Whether the item is active")


class ListCatalogCategoriesParams(BaseModel):
    """Parameters for listing service catalog categories."""
    
    limit: int = Field(10, description="Maximum number of categories to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for categories")
    active: bool = Field(True, description="Whether to only return active categories")


class CreateCatalogCategoryParams(BaseModel):
    """Parameters for creating a new catalog category."""
    
    name: str = Field(..., description="Name of the category")
    description: str = Field(..., description="Description of the category")
    parent_category: Optional[str] = Field(None, description="Parent category ID")


class UpdateCatalogCategoryParams(BaseModel):
    """Parameters for updating a catalog category."""
    
    category_id: str = Field(..., description="Category ID to update")
    name: Optional[str] = Field(None, description="Name of the category")
    description: Optional[str] = Field(None, description="Description of the category")
    parent_category: Optional[str] = Field(None, description="Parent category ID")


class CatalogResponse(BaseModel):
    """Response from catalog operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


async def list_catalog_items(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCatalogItemsParams,
) -> Dict[str, Any]:
    """
    List service catalog items from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing catalog items

    Returns:
        Dictionary containing catalog items and metadata
    """
    logger.info("Listing service catalog items with params: %s", params)
    
    try:
        logger.debug("Building query parameters...")
        # Build base query parameters with security defaults
        query_params = {
            "sysparm_limit": max(1, min(params.limit, 1000)),  # Limit between 1-1000
            "sysparm_offset": max(0, params.offset),  # No negative offsets
            "sysparm_display_value": "true",  # Get human-readable values
            "sysparm_exclude_reference_link": "true"  # Prevent reference exposure
        }
        logger.debug("Base query params: %s", query_params)
        
        # Build secure query filters
        filters = []
        
        # Add sanitized category filter if specified
        if params.category:
            # Remove potential injection characters
            safe_category = params.category.replace('^', '').replace('=', '')
            filters.append(f"cat_item.category={safe_category}")
            logger.debug("Added sanitized category filter: %s", safe_category)
            
        # Add sanitized search query if specified
        if params.query:
            # Escape special characters and limit query length
            safe_query = params.query.replace('^', '').replace('=', '')[:100]
            filters.append(f"nameLIKE{safe_query}^ORshort_descriptionLIKE{safe_query}")
            logger.debug("Added sanitized search filter: %s", safe_query)

        # Add active filter with explicit boolean conversion
        if params.active is not None:
            filters.append(f"active={str(bool(params.active)).lower()}")

        # Combine filters securely
        if filters:
            query_params["sysparm_query"] = "^".join(filters)

        # Get and enhance authentication headers (support async/sync)
        headers = await _get_auth_headers(auth_manager)
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            # Add security headers
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block"
        })
        
        logger.debug("Making API request...")
        # Configure HTTP client with security settings
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=True,  # Enforce SSL verification
            http2=False,  # Disable HTTP/2 to avoid h2 dependency
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=5.0
            )
        ) as client:
            logger.debug("Sending GET request...")
            response = await client.get(
                f"{config.instance_url}/api/now/v1/servicecatalog/items",
                params=query_params,
                headers=headers
            )
            # Some mocks may return an awaitable that yields the response
            if inspect.isawaitable(response):
                response = await response
            logger.debug("Got response, checking status...")
            await _maybe_await(response.raise_for_status)
            
            logger.debug("Getting response JSON...")
            json_data = await _maybe_await(response.json)
            if not isinstance(json_data, dict):
                logger.error("Invalid response format - not a dict: %s", type(json_data))
                raise ValueError("Invalid response format: not a dictionary")
                
            result = json_data.get("result", [])
            if not isinstance(result, list):
                logger.error("Invalid result format - not a list: %s", type(result))
                raise ValueError("Invalid result format: not a list")
            
            # Sanitize and validate each item
            sanitized_items = []
            for item in result:
                if isinstance(item, dict):
                    # Sanitize and type-check each field
                    sanitized_item = {
                        "sys_id": str(item.get("sys_id", ""))[:32],  # Limit sys_id length
                        "name": str(item.get("name", ""))[:255],  # Limit name length
                        "short_description": str(item.get("short_description", ""))[:1000],
                        "category": str(item.get("category", "")),
                        "active": bool(item.get("active", False)),
                        "created": str(item.get("sys_created_on", "")),
                        "updated": str(item.get("sys_updated_on", ""))
                    }
                    sanitized_items.append(sanitized_item)
            
            response_data = {
                "items": sanitized_items,
                "count": len(sanitized_items),
                "total": max(0, int(response.headers.get("X-Total-Count", "0"))),  # Ensure non-negative
                "hasMore": len(sanitized_items) >= params.limit if params.limit > 0 else False,
                "timestamp": str(response.headers.get("Date", "")),
                "request_id": str(response.headers.get("X-Request-ID", ""))
            }
            logger.debug("Returning sanitized response data")
            return response_data
            
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error listing catalog items: %s", str(e))
        if e.response.status_code == 401:
            raise ValueError("Authentication failed (401)")
        elif e.response.status_code == 403:
            raise ValueError("Not authorized to list catalog items")
        else:
            raise ValueError(f"Failed to list catalog items: {e.response.text}")
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error("Network error listing catalog items: %s", str(e))
        raise ValueError(f"Network error while listing catalog items: {str(e)}")
        
    except Exception as e:
        logger.exception("Unexpected error listing catalog items")
        raise ValueError(f"Unexpected error while listing catalog items: {str(e)}")


async def get_catalog_item(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCatalogItemParams,
) -> CatalogResponse:
    """
    Get a specific service catalog item from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for getting a catalog item

    Returns:
        Response containing the catalog item details
    """
    logger.info(f"Getting service catalog item: {params.item_id}")
    
    try:
        # Get authentication headers (support async/sync)
        headers = await _get_auth_headers(auth_manager)
        
        # Make the API request for the item details
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.get(
                f"{config.instance_url}/api/now/v1/servicecatalog/items/{params.item_id}",
                params={"sysparm_display_value": "true"},
                headers=headers
            )
            if inspect.isawaitable(response):
                response = await response
            await _maybe_await(response.raise_for_status)
            
            data = await _maybe_await(response.json)
            item = data.get("result")
            
            if not item:
                return CatalogResponse(
                    success=False,
                    message=f"Catalog item {params.item_id} not found",
                    data=None
                )
            
            # Get variables/fields for the catalog item
            fields_response = await client.get(
                f"{config.instance_url}/api/now/v1/servicecatalog/items/{params.item_id}/variables",
                headers=headers
            )
            if inspect.isawaitable(fields_response):
                fields_response = await fields_response
            await _maybe_await(fields_response.raise_for_status)
            
            fields_data = await _maybe_await(fields_response.json)
            item["variables"] = fields_data.get("result", [])
                
            return CatalogResponse(
                success=True,
                message=f"Successfully retrieved catalog item {params.item_id}",
                data={"item": item}
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error getting catalog item: %s", str(e))
        if e.response.status_code == 401:
            return CatalogResponse(
                success=False,
                message="Authentication failed (401)",
                data=None
            )
        elif e.response.status_code == 403:
            return CatalogResponse(
                success=False,
                message="Not authorized to view this catalog item",
                data=None
            )
        elif e.response.status_code == 404:
            return CatalogResponse(
                success=False,
                message=f"Catalog item {params.item_id} not found",
                data=None
            )
        else:
            return CatalogResponse(
                success=False,
                message=f"Failed to get catalog item: {e.response.text}",
                data=None
            )
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error("Network error getting catalog item: %s", str(e))
        return CatalogResponse(
            success=False,
            message=f"Network error while getting catalog item: {str(e)}",
            data=None
        )
        
    except Exception as e:
        logger.exception("Unexpected error getting catalog item")
        return CatalogResponse(
            success=False,
            message=f"Unexpected error while getting catalog item: {str(e)}",
            data=None
        )


async def create_catalog_item(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateCatalogItemParams,
) -> CatalogResponse:
    """
    Create a new service catalog item in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating a catalog item

    Returns:
        Response containing the created item details
    """
    logger.info(f"Creating new service catalog item: {params.name}")
    
    try:
        # Prepare the request payload
        payload = {
            "name": params.name,
            "short_description": params.description,
            "active": params.active
        }
        
        if params.category:
            payload["category"] = params.category
        if params.template:
            payload["template"] = params.template
        if params.workflow:
            payload["workflow"] = params.workflow
            
        # Get authentication headers (support async/sync)
        headers = await _get_auth_headers(auth_manager)
        
        # Make the API request
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.post(
                f"{config.instance_url}/api/now/v1/servicecatalog/items",
                json=payload,
                headers=headers
            )
            if inspect.isawaitable(response):
                response = await response
            await _maybe_await(response.raise_for_status)
            
            data = await _maybe_await(response.json)
            item = data.get("result")
            
            if not item:
                return CatalogResponse(
                    success=False,
                    message="Failed to create catalog item - no response data",
                    data=None
                )
                
            return CatalogResponse(
                success=True,
                message=f"Successfully created catalog item: {item.get('sys_id')}",
                data={"item": item}
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error creating catalog item: %s", str(e))
        if e.response.status_code == 401:
            return CatalogResponse(
                success=False,
                message="Authentication failed",
                data=None
            )
        elif e.response.status_code == 403:
            return CatalogResponse(
                success=False,
                message="Not authorized to create catalog items",
                data=None
            )
        else:
            return CatalogResponse(
                success=False,
                message=f"Failed to create catalog item: {e.response.text}",
                data=None
            )
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error("Network error creating catalog item: %s", str(e))
        return CatalogResponse(
            success=False,
            message=f"Network error while creating catalog item: {str(e)}",
            data=None
        )
        
    except Exception as e:
        logger.exception("Unexpected error creating catalog item")
        return CatalogResponse(
            success=False,
            message=f"Unexpected error while creating catalog item: {str(e)}",
            data=None
        )


async def update_catalog_item(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateCatalogItemParams,
) -> CatalogResponse:
    """
    Update an existing service catalog item in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating a catalog item

    Returns:
        Response containing the updated item details
    """
    logger.info(f"Updating service catalog item: {params.item_id}")
    
    try:
        # Prepare the update payload with only provided fields
        payload = {}
        if params.name is not None:
            payload["name"] = params.name
        if params.description is not None:
            payload["short_description"] = params.description
        if params.category is not None:
            payload["category"] = params.category
        if params.active is not None:
            payload["active"] = params.active
            
        if not payload:
            return CatalogResponse(
                success=False,
                message="No update parameters provided",
                data=None
            )
            
        # Get authentication headers (support async/sync)
        headers = await _get_auth_headers(auth_manager)
        
        # Make the API request
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.patch(
                f"{config.instance_url}/api/now/v1/servicecatalog/items/{params.item_id}",
                json=payload,
                headers=headers
            )
            if inspect.isawaitable(response):
                response = await response
            await _maybe_await(response.raise_for_status)
            
            data = await _maybe_await(response.json)
            item = data.get("result")
            
            if not item:
                return CatalogResponse(
                    success=False,
                    message="Failed to update catalog item - no response data",
                    data=None
                )
                
            return CatalogResponse(
                success=True,
                message=f"Successfully updated catalog item: {params.item_id}",
                data={"item": item}
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error updating catalog item: %s", str(e))
        if e.response.status_code == 401:
            return CatalogResponse(
                success=False,
                message="Authentication failed",
                data=None
            )
        elif e.response.status_code == 403:
            return CatalogResponse(
                success=False,
                message="Not authorized to update this catalog item",
                data=None
            )
        elif e.response.status_code == 404:
            return CatalogResponse(
                success=False,
                message=f"Catalog item {params.item_id} not found",
                data=None
            )
        else:
            return CatalogResponse(
                success=False,
                message=f"Failed to update catalog item: {e.response.text}",
                data=None
            )
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error("Network error updating catalog item: %s", str(e))
        return CatalogResponse(
            success=False,
            message=f"Network error while updating catalog item: {str(e)}",
            data=None
        )
        
    except Exception as e:
        logger.exception("Unexpected error updating catalog item")
        return CatalogResponse(
            success=False,
            message=f"Unexpected error while updating catalog item: {str(e)}",
            data=None
        )


async def list_catalog_categories(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCatalogCategoriesParams,
) -> Dict[str, Any]:
    """
    List service catalog categories from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing catalog categories

    Returns:
        Dictionary containing catalog categories and metadata
    """
    logger.info("Listing service catalog categories with params: %s", params)
    
    try:
        # Build query parameters
        query_params = {
            "sysparm_limit": params.limit,
            "sysparm_offset": params.offset,
            "sysparm_display_value": "true"
        }
        
        # Add search query if specified
        if params.query:
            query_params["sysparm_query"] = f"titleLIKE{params.query}^ORdescriptionLIKE{params.query}"
            
        # Add active filter
        if params.active is not None:
            active_query = f"active={str(params.active).lower()}"
            query_params["sysparm_query"] = f"{query_params.get('sysparm_query', '')}{'^' if 'sysparm_query' in query_params else ''}{active_query}"
            
        # Get authentication headers (support async/sync)
        headers = await _get_auth_headers(auth_manager)
        
        # Make the API request
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.get(
                f"{config.instance_url}/api/now/v1/servicecatalog/categories",
                params=query_params,
                headers=headers
            )
            if inspect.isawaitable(response):
                response = await response
            await _maybe_await(response.raise_for_status)
            
            data = await _maybe_await(response.json)
            result = data.get("result", [])
            
            return {
                "categories": result,
                "count": len(result),
                "total": int(response.headers.get("X-Total-Count", "0")),
                "hasMore": len(result) >= params.limit if params.limit > 0 else False
            }
            
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error listing catalog categories: %s", str(e))
        if e.response.status_code == 401:
            raise ValueError("Authentication failed")
        elif e.response.status_code == 403:
            raise ValueError("Not authorized to list catalog categories")
        else:
            raise ValueError(f"Failed to list catalog categories: {e.response.text}")
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error("Network error listing catalog categories: %s", str(e))
        raise ValueError(f"Network error while listing catalog categories: {str(e)}")
        
    except Exception as e:
        logger.exception("Unexpected error listing catalog categories")
        raise ValueError(f"Unexpected error while listing catalog categories: {str(e)}")


async def create_catalog_category(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateCatalogCategoryParams,
) -> CatalogResponse:
    """
    Create a new service catalog category in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating a catalog category

    Returns:
        Response containing the created category details
    """
    logger.info(f"Creating new service catalog category: {params.name}")
    
    try:
        # Prepare the request payload
        payload = {
            "title": params.name,
            "description": params.description,
        }
        
        if params.parent_category:
            payload["parent_category"] = params.parent_category
            
        # Get authentication headers (support async/sync)
        headers = await _get_auth_headers(auth_manager)
        
        # Make the API request
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.post(
                f"{config.instance_url}/api/now/v1/servicecatalog/categories",
                json=payload,
                headers=headers
            )
            if inspect.isawaitable(response):
                response = await response
            await _maybe_await(response.raise_for_status)
            
            data = await _maybe_await(response.json)
            category = data.get("result")
            
            if not category:
                return CatalogResponse(
                    success=False,
                    message="Failed to create catalog category - no response data",
                    data=None
                )
                
            return CatalogResponse(
                success=True,
                message=f"Successfully created catalog category: {category.get('sys_id')}",
                data={"category": category}
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error creating catalog category: %s", str(e))
        if e.response.status_code == 401:
            return CatalogResponse(
                success=False,
                message="Authentication failed",
                data=None
            )
        elif e.response.status_code == 403:
            return CatalogResponse(
                success=False,
                message="Not authorized to create catalog categories",
                data=None
            )
        else:
            return CatalogResponse(
                success=False,
                message=f"Failed to create catalog category: {e.response.text}",
                data=None
            )
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error("Network error creating catalog category: %s", str(e))
        return CatalogResponse(
            success=False,
            message=f"Network error while creating catalog category: {str(e)}",
            data=None
        )
        
    except Exception as e:
        logger.exception("Unexpected error creating catalog category")
        return CatalogResponse(
            success=False,
            message=f"Unexpected error while creating catalog category: {str(e)}",
            data=None
        )


async def update_catalog_category(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateCatalogCategoryParams,
) -> CatalogResponse:
    """
    Update an existing service catalog category in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating a catalog category

    Returns:
        Response containing the updated category details
    """
    logger.info(f"Updating service catalog category: {params.category_id}")
    
    try:
        # Prepare the update payload with only provided fields
        payload = {}
        if params.name is not None:
            payload["title"] = params.name
        if params.description is not None:
            payload["description"] = params.description
        if params.parent_category is not None:
            payload["parent_category"] = params.parent_category
            
        if not payload:
            return CatalogResponse(
                success=False,
                message="No update parameters provided",
                data=None
            )
            
        # Get authentication headers (support async/sync)
        headers = await _get_auth_headers(auth_manager)
        
        # Make the API request
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.patch(
                f"{config.instance_url}/api/now/v1/servicecatalog/categories/{params.category_id}",
                json=payload,
                headers=headers
            )
            if inspect.isawaitable(response):
                response = await response
            await _maybe_await(response.raise_for_status)
            
            data = await _maybe_await(response.json)
            category = data.get("result")
            
            if not category:
                return CatalogResponse(
                    success=False,
                    message="Failed to update catalog category - no response data",
                    data=None
                )
                
            return CatalogResponse(
                success=True,
                message=f"Successfully updated catalog category: {params.category_id}",
                data={"category": category}
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error updating catalog category: %s", str(e))
        if e.response.status_code == 401:
            return CatalogResponse(
                success=False,
                message="Authentication failed",
                data=None
            )
        elif e.response.status_code == 403:
            return CatalogResponse(
                success=False,
                message="Not authorized to update this catalog category",
                data=None
            )
        elif e.response.status_code == 404:
            return CatalogResponse(
                success=False,
                message=f"Catalog category {params.category_id} not found",
                data=None
            )
        else:
            return CatalogResponse(
                success=False,
                message=f"Failed to update catalog category: {e.response.text}",
                data=None
            )
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error("Network error updating catalog category: %s", str(e))
        return CatalogResponse(
            success=False,
            message=f"Network error while updating catalog category: {str(e)}",
            data=None
        )
        
    except Exception as e:
        logger.exception("Unexpected error updating catalog category")
        return CatalogResponse(
            success=False,
            message=f"Unexpected error while updating catalog category: {str(e)}",
            data=None
        )
