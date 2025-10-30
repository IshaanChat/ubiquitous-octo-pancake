"""
Systems Administrator tools for ServiceNow MCP integration.
Handles user and group management operations.
"""
import logging
from typing import Any, Dict, List, Optional

import inspect
import requests
from pydantic import BaseModel, Field

from auth.auth_manager import AuthManager
from config import ServerConfig


logger = logging.getLogger(__name__)


async def _maybe_await(callable_or_awaitable, *args, **kwargs):
    try:
        result = callable_or_awaitable(*args, **kwargs)
    except Exception:
        raise
    if inspect.isawaitable(result):
        return await result
    return result


def _unwrap_result(obj: Any) -> Any:
    """Unwrap nested ServiceNow-style results.

    - If obj is a dict with a "result" that is a list, return the first element (or {}).
    - If obj is a dict with a "result" that is a dict, return that dict.
    - Otherwise, return obj unchanged.
    """
    if isinstance(obj, dict) and "result" in obj:
        inner = obj["result"]
        if isinstance(inner, list):
            return inner[0] if inner else {}
        if isinstance(inner, dict):
            return inner
    return obj

class ListUsersParams(BaseModel):
    """Parameters for listing users."""
    
    limit: int = Field(10, description="Maximum number of users to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for users")
    roles: Optional[List[str]] = Field(None, description="Filter by roles")
    department: Optional[str] = Field(None, description="Filter by department")
    active: Optional[bool] = Field(None, description="Filter by active status")


class GetUserParams(BaseModel):
    """Parameters for getting a specific user."""
    
    user_id: str = Field(..., description="User ID or sys_id")


class CreateUserParams(BaseModel):
    """Parameters for creating a new user."""
    
    username: str = Field(..., description="Username for the user")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    roles: Optional[List[str]] = Field(None, description="Roles to assign")
    department: Optional[str] = Field(None, description="Department")
    title: Optional[str] = Field(None, description="Job title")


class UpdateUserParams(BaseModel):
    """Parameters for updating an existing user."""
    
    user_id: str = Field(..., description="User ID to update")
    email: Optional[str] = Field(None, description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    roles: Optional[List[str]] = Field(None, description="Roles to assign")
    active: Optional[bool] = Field(None, description="Active status")
    locked: Optional[bool] = Field(None, description="Locked status")


class ListGroupsParams(BaseModel):
    """Parameters for listing groups."""
    
    limit: int = Field(10, description="Maximum number of groups to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for groups")
    type: Optional[str] = Field(None, description="Filter by group type")
    active: Optional[bool] = Field(None, description="Filter by active status")


class CreateGroupParams(BaseModel):
    """Parameters for creating a new group."""
    
    name: str = Field(..., description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    parent_group: Optional[str] = Field(None, description="Parent group ID")
    roles: Optional[List[str]] = Field(None, description="Roles to assign")
    type: Optional[str] = Field(None, description="Group type")


class UpdateGroupParams(BaseModel):
    """Parameters for updating a group."""
    
    group_id: str = Field(..., description="Group ID to update")
    name: Optional[str] = Field(None, description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    parent_group: Optional[str] = Field(None, description="Parent group ID")
    roles: Optional[List[str]] = Field(None, description="Roles to assign")
    active: Optional[bool] = Field(None, description="Active status")


class AdminResponse(BaseModel):
    """Response from systems administrator operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if any")


async def list_users(
    config: ServerConfig,
    auth_manager: Any,
    params: ListUsersParams,
) -> Dict[str, Any]:
    """
    List users from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing users

    Returns:
        Dictionary containing users and metadata
    """
    logger.info("Listing users")
    client = auth_manager
    query_params = {"sysparm_limit": params.limit, "sysparm_offset": params.offset}
    if params.query:
        query_params["sysparm_query"] = params.query
    try:
        response = await client.get(f"{getattr(config, 'api_url', '')}/table/sys_user", params=query_params)
        data = await _maybe_await(response.json)
        users = data.get("result", {}).get("users", data.get("result", []))
        # Normalize any nested user objects
        normalized = []
        for u in users:
            normalized.append(_unwrap_result(u))
        return {"users": normalized, "count": len(normalized)}
    except Exception:
        raise


async def get_user(
    config: ServerConfig,
    auth_manager: Any,
    params: GetUserParams,
) -> AdminResponse:
    """
    Get a specific user from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for getting a user

    Returns:
        Response containing the user details
    """
    logger.info(f"Getting user: {params.user_id}")
    client = auth_manager
    try:
        response = await client.get(f"{getattr(config, 'api_url', '')}/table/sys_user/{params.user_id}")
        data = await _maybe_await(response.json)
        result = data.get("result", data)
        result = _unwrap_result(result)
        return AdminResponse(success=True, message="User retrieved", data=result)
    except Exception as e:
        logger.exception("Error getting user")
        return AdminResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def create_user(
    config: ServerConfig,
    auth_manager: Any,
    params: CreateUserParams,
) -> AdminResponse:
    """
    Create a new user in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating a user

    Returns:
        Response containing the created user details
    """
    logger.info(f"Creating new user: {params.username}")
    client = auth_manager
    payload = {
        "user_name": params.username,
        "email": params.email,
        "first_name": params.first_name,
        "last_name": params.last_name,
        "roles": params.roles,
        "department": params.department,
        "title": params.title,
    }
    try:
        response = await client.post(f"{getattr(config, 'api_url', '')}/table/sys_user", json=payload)
        data = await _maybe_await(response.json)
        result = data.get("result", data)
        return AdminResponse(success=True, message="User created", data=result)
    except Exception as e:
        logger.exception("Error creating user")
        return AdminResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def update_user(
    config: ServerConfig,
    auth_manager: Any,
    params: UpdateUserParams,
) -> AdminResponse:
    """
    Update an existing user in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating a user

    Returns:
        Response containing the updated user details
    """
    logger.info(f"Updating user: {params.user_id}")
    client = auth_manager
    payload = {}
    for field in ["email", "first_name", "last_name", "roles", "active", "locked"]:
        value = getattr(params, field)
        if value is not None:
            payload[field] = value
    try:
        response = await client.put(f"{getattr(config, 'api_url', '')}/table/sys_user/{params.user_id}", json=payload)
        data = await _maybe_await(response.json)
        result = data.get("result", data)
        return AdminResponse(success=True, message="User updated", data=result)
    except Exception as e:
        logger.exception("Error updating user")
        return AdminResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def list_groups(
    config: ServerConfig,
    auth_manager: Any,
    params: ListGroupsParams,
) -> Dict[str, Any]:
    """
    List groups from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing groups

    Returns:
        Dictionary containing groups and metadata
    """
    logger.info("Listing groups")
    client = auth_manager
    query_params = {"sysparm_limit": params.limit, "sysparm_offset": params.offset}
    if params.query:
        query_params["sysparm_query"] = params.query
    try:
        response = await client.get(f"{getattr(config, 'api_url', '')}/table/sys_user_group", params=query_params)
        data = await _maybe_await(response.json)
        groups = data.get("result", {}).get("groups", data.get("result", []))
        return {"groups": groups, "count": len(groups)}
    except Exception:
        raise


async def create_group(
    config: ServerConfig,
    auth_manager: Any,
    params: CreateGroupParams,
) -> AdminResponse:
    """
    Create a new group in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating a group

    Returns:
        Response containing the created group details
    """
    logger.info(f"Creating new group: {params.name}")
    client = auth_manager
    payload = {
        "name": params.name,
        "description": params.description,
        "parent": params.parent_group,
        "roles": params.roles,
        "type": params.type,
    }
    try:
        response = await client.post(f"{getattr(config, 'api_url', '')}/table/sys_user_group", json=payload)
        data = await _maybe_await(response.json)
        result = data.get("result", data)
        return AdminResponse(success=True, message="Group created", data=result)
    except Exception as e:
        logger.exception("Error creating group")
        return AdminResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def update_group(
    config: ServerConfig,
    auth_manager: Any,
    params: UpdateGroupParams,
) -> AdminResponse:
    """
    Update an existing group in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating a group

    Returns:
        Response containing the updated group details
    """
    logger.info(f"Updating group: {params.group_id}")
    client = auth_manager
    payload = {}
    for field in ["name", "description", "parent_group", "roles", "active"]:
        value = getattr(params, field)
        if value is not None:
            payload[field] = value
    try:
        response = await client.put(f"{getattr(config, 'api_url', '')}/table/sys_user_group/{params.group_id}", json=payload)
        data = await _maybe_await(response.json)
        result = data.get("result", data)
        return AdminResponse(success=True, message="Group updated", data=result)
    except Exception as e:
        logger.exception("Error updating group")
        return AdminResponse(success=False, message=str(e), data=None, error={"message": str(e)})


# Tool metadata
TOOL_ID = "systems_administrator"
TOOL_NAME = "Systems Administrator Tools"
TOOL_DESCRIPTION = "ServiceNow tools for user and group administration"

OPERATIONS = {
    "list_users": {
        "description": "List users matching query parameters",
        "required_params": [],
        "optional_params": ["query", "roles", "department", "active", "limit", "offset"]
    },
    "get_user": {
        "description": "Get user details",
        "required_params": ["user_id"]
    },
    "create_user": {
        "description": "Create a new user",
        "required_params": ["username", "email"],
        "optional_params": ["first_name", "last_name", "roles", "department", "title"]
    },
    "update_user": {
        "description": "Update an existing user",
        "required_params": ["user_id"],
        "optional_params": ["email", "first_name", "last_name", "roles", "active", "locked"]
    },
    "list_groups": {
        "description": "List groups matching query parameters",
        "required_params": [],
        "optional_params": ["query", "type", "active", "limit", "offset"]
    },
    "create_group": {
        "description": "Create a new group",
        "required_params": ["name"],
        "optional_params": ["description", "parent_group", "roles", "type"]
    },
    "update_group": {
        "description": "Update an existing group",
        "required_params": ["group_id"],
        "optional_params": ["name", "description", "parent_group", "roles", "active"]
    }
}
