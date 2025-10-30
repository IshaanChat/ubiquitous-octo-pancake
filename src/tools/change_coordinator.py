"""
Change Coordinator tools for ServiceNow MCP integration.
Handles change request lifecycle and approval management.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

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
    if isinstance(obj, dict) and "result" in obj:
        inner = obj["result"]
        if isinstance(inner, list):
            return inner[0] if inner else {}
        if isinstance(inner, dict):
            return inner
    return obj

class ListChangeRequestsParams(BaseModel):
    """Parameters for listing change requests."""
    
    limit: int = Field(10, description="Maximum number of change requests to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for change requests")
    state: Optional[str] = Field(None, description="Filter by change request state")
    type: Optional[str] = Field(None, description="Filter by change type")
    assignment_group: Optional[str] = Field(None, description="Filter by assignment group")


class GetChangeRequestParams(BaseModel):
    """Parameters for getting a specific change request."""
    
    change_number: str = Field(..., description="Change request number")


class CreateChangeRequestParams(BaseModel):
    """Parameters for creating a new change request."""
    
    short_description: str = Field(..., description="Short description of the change")
    type: Optional[str] = Field(None, description="Type of change")
    risk: Optional[str] = Field(None, description="Risk level")
    impact: Optional[str] = Field(None, description="Impact level")
    assignment_group: Optional[str] = Field(None, description="Assignment group")
    start_date: Optional[datetime] = Field(None, description="Planned start date")
    end_date: Optional[datetime] = Field(None, description="Planned end date")


class UpdateChangeRequestParams(BaseModel):
    """Parameters for updating an existing change request."""
    
    change_number: str = Field(..., description="Change request number to update")
    short_description: Optional[str] = Field(None, description="Short description of the change")
    type: Optional[str] = Field(None, description="Type of change")
    risk: Optional[str] = Field(None, description="Risk level")
    impact: Optional[str] = Field(None, description="Impact level")
    state: Optional[str] = Field(None, description="Change request state")


class ApproveChangeParams(BaseModel):
    """Parameters for approving a change request."""
    
    change_number: str = Field(..., description="Change request number to approve")
    comments: Optional[str] = Field(None, description="Approval comments")


class RejectChangeParams(BaseModel):
    """Parameters for rejecting a change request."""
    
    change_number: str = Field(..., description="Change request number to reject")
    reason: str = Field(..., description="Reason for rejection")


class ChangeResponse(BaseModel):
    """Response from change request operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if any")


async def list_change_requests(
    config: ServerConfig,
    auth_manager: Any,
    params: ListChangeRequestsParams,
) -> Dict[str, Any]:
    """
    List change requests from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing change requests

    Returns:
        Dictionary containing change requests and metadata
    """
    logger.info("Listing change requests")
    client = auth_manager
    query_params = {"sysparm_limit": params.limit, "sysparm_offset": params.offset}
    qp = []
    if params.query:
        qp.append(params.query)
    if params.state:
        qp.append(f"state={params.state}")
    if params.type:
        qp.append(f"type={params.type}")
    if params.assignment_group:
        qp.append(f"assignment_group={params.assignment_group}")
    if qp:
        query_params["sysparm_query"] = "^".join(qp)
    try:
        response = await client.get(f"{getattr(config, 'api_url', '')}/table/change_request", params=query_params)
        data = await _maybe_await(response.json)
        raw = data.get("changes", data.get("result", []))
        items = []
        for c in raw:
            items.append(_unwrap_result(c))
        return {"changes": items, "count": len(items)}
    except Exception:
        raise


async def get_change_request(
    config: ServerConfig,
    auth_manager: Any,
    params: GetChangeRequestParams,
) -> ChangeResponse:
    """
    Get a specific change request from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for getting a change request

    Returns:
        Response containing the change request details
    """
    logger.info(f"Getting change request: {params.change_number}")
    client = auth_manager
    try:
        response = await client.get(f"{getattr(config, 'api_url', '')}/table/change_request/{params.change_number}")
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        return ChangeResponse(success=True, message="Change retrieved", data=result)
    except Exception as e:
        logger.exception("Error getting change request")
        return ChangeResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def create_change_request(
    config: ServerConfig,
    auth_manager: Any,
    params: CreateChangeRequestParams,
) -> ChangeResponse:
    """
    Create a new change request in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating a change request

    Returns:
        Response containing the created change request details
    """
    logger.info(f"Creating new change request: {params.short_description}")
    client = auth_manager
    payload = {
        "short_description": params.short_description,
        "type": params.type,
        "risk": params.risk,
        "impact": params.impact,
        "assignment_group": params.assignment_group,
        "start_date": params.start_date.isoformat() if params.start_date else None,
        "end_date": params.end_date.isoformat() if params.end_date else None,
    }
    try:
        response = await client.post(f"{getattr(config, 'api_url', '')}/table/change_request", json=payload)
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        return ChangeResponse(success=True, message="Change created", data=result)
    except Exception as e:
        logger.exception("Error creating change request")
        return ChangeResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def update_change_request(
    config: ServerConfig,
    auth_manager: Any,
    params: UpdateChangeRequestParams,
) -> ChangeResponse:
    """
    Update an existing change request in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating a change request

    Returns:
        Response containing the updated change request details
    """
    logger.info(f"Updating change request: {params.change_number}")
    client = auth_manager
    payload = {}
    for field in ["short_description", "type", "risk", "impact", "state"]:
        value = getattr(params, field)
        if value is not None:
            payload[field] = value
    try:
        response = await client.put(f"{getattr(config, 'api_url', '')}/table/change_request/{params.change_number}", json=payload)
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        return ChangeResponse(success=True, message="Change updated", data=result)
    except Exception as e:
        logger.exception("Error updating change request")
        return ChangeResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def approve_change(
    config: ServerConfig,
    auth_manager: Any,
    params: ApproveChangeParams,
) -> ChangeResponse:
    """
    Approve a change request in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for approving a change request

    Returns:
        Response containing the approval result
    """
    logger.info(f"Approving change request: {params.change_number}")
    client = auth_manager
    payload = {"approval": "approved", "comments": params.comments}
    try:
        response = await client.put(f"{getattr(config, 'api_url', '')}/table/change_request/{params.change_number}", json=payload)
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        return ChangeResponse(success=True, message="Change approved", data=result)
    except Exception as e:
        logger.exception("Error approving change request")
        return ChangeResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def reject_change(
    config: ServerConfig,
    auth_manager: Any,
    params: RejectChangeParams,
) -> ChangeResponse:
    """
    Reject a change request in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for rejecting a change request

    Returns:
        Response containing the rejection result
    """
    logger.info(f"Rejecting change request: {params.change_number}")
    client = auth_manager
    payload = {"approval": "rejected", "comments": params.reason}
    try:
        response = await client.put(f"{getattr(config, 'api_url', '')}/table/change_request/{params.change_number}", json=payload)
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        return ChangeResponse(success=True, message="Change rejected", data=result)
    except Exception as e:
        logger.exception("Error rejecting change request")
        return ChangeResponse(success=False, message=str(e), data=None, error={"message": str(e)})


# Tool metadata
TOOL_ID = "change_coordinator"
TOOL_NAME = "Change Coordinator Tools"
TOOL_DESCRIPTION = "ServiceNow tools for change management and approval workflows"

OPERATIONS = {
    "list_change_requests": {
        "description": "List change requests matching query parameters",
        "required_params": [],
        "optional_params": ["query", "state", "type", "assignment_group", "limit", "offset"]
    },
    "get_change_request": {
        "description": "Get detailed information about a change request",
        "required_params": ["change_number"]
    },
    "create_change_request": {
        "description": "Create a new change request",
        "required_params": ["short_description"],
        "optional_params": ["type", "risk", "impact", "assignment_group", "start_date", "end_date"]
    },
    "update_change_request": {
        "description": "Update an existing change request",
        "required_params": ["change_number"],
        "optional_params": ["short_description", "type", "risk", "impact", "state"]
    },
    "approve_change": {
        "description": "Approve a change request",
        "required_params": ["change_number"],
        "optional_params": ["comments"]
    },
    "reject_change": {
        "description": "Reject a change request",
        "required_params": ["change_number", "reason"]
    }
}
