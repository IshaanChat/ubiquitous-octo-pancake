"""
CMDB Reader tools: read-only access to configuration items and relationships.
"""
import logging
from typing import Any, Dict, Optional, List

import inspect
from pydantic import BaseModel, Field

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


def _unwrap(obj: Any) -> Any:
    if isinstance(obj, dict) and "result" in obj:
        inner = obj["result"]
        if isinstance(inner, list):
            return inner[0] if inner else {}
        if isinstance(inner, dict):
            return inner
    return obj


class ListCIsParams(BaseModel):
    limit: int = Field(10, description="Max records")
    offset: int = Field(0, description="Offset")
    query: Optional[str] = Field(None, description="sysparm_query filter")
    class_name: Optional[str] = Field(None, description="CMDB class (table) name override")


class GetCIParams(BaseModel):
    sys_id: str = Field(..., description="CI sys_id")
    class_name: Optional[str] = Field(None, description="CMDB class (table) name override")


class ListCIRelationshipsParams(BaseModel):
    sys_id: str = Field(..., description="CI sys_id")
    direction: Optional[str] = Field(
        None, description="parent|child|both (default both)")


async def list_cis(config: ServerConfig, auth_manager: Any, params: ListCIsParams) -> Dict[str, Any]:
    """List configuration items (read-only)."""
    table = params.class_name or "cmdb_ci"
    qp: Dict[str, Any] = {"sysparm_limit": params.limit, "sysparm_offset": params.offset}
    if params.query:
        qp["sysparm_query"] = params.query
    resp = await auth_manager.get(f"{getattr(config, 'api_url', '')}/table/{table}", params=qp)
    data = await _maybe_await(resp.json)
    raw = data.get("cis", data.get("result", []))
    items: List[Dict[str, Any]] = []
    for r in raw:
        items.append(_unwrap(r))
    return {"items": items, "count": len(items)}


async def get_ci(config: ServerConfig, auth_manager: Any, params: GetCIParams) -> Dict[str, Any]:
    """Get a specific CI by sys_id."""
    table = params.class_name or "cmdb_ci"
    resp = await auth_manager.get(f"{getattr(config, 'api_url', '')}/table/{table}/{params.sys_id}")
    data = await _maybe_await(resp.json)
    return _unwrap(data)


async def list_ci_relationships(config: ServerConfig, auth_manager: Any, params: ListCIRelationshipsParams) -> Dict[str, Any]:
    """List relationships for a CI (parent/child/both)."""
    direction = (params.direction or "both").lower()
    filters: List[str] = []
    if direction in ("both", "parent"):
        filters.append(f"parent={params.sys_id}")
    if direction in ("both", "child"):
        filters.append(f"child={params.sys_id}")
    query = "^OR".join(filters) if len(filters) > 1 else (filters[0] if filters else "")
    qp = {"sysparm_query": query} if query else {}
    resp = await auth_manager.get(f"{getattr(config, 'api_url', '')}/table/cmdb_rel_ci", params=qp)
    data = await _maybe_await(resp.json)
    raw = data.get("relationships", data.get("result", []))
    items: List[Dict[str, Any]] = []
    for r in raw:
        items.append(_unwrap(r))
    return {"relationships": items, "count": len(items)}


TOOL_ID = "cmdb"
TOOL_NAME = "CMDB Reader"
TOOL_DESCRIPTION = "Read-only CMDB access: CIs and relationships"

OPERATIONS = {
    "list_cis": {
        "description": "List configuration items (read-only)",
        "required_params": [],
        "optional_params": ["limit", "offset", "query", "class_name"],
    },
    "get_ci": {
        "description": "Get CI by sys_id",
        "required_params": ["sys_id"],
        "optional_params": ["class_name"],
    },
    "list_ci_relationships": {
        "description": "List relationships for a CI",
        "required_params": ["sys_id"],
        "optional_params": ["direction"],
    },
}

