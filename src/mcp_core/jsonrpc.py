"""
Lightweight JSON-RPC 2.0 helpers to expose MCP-like methods without
impacting existing HTTP routes.

Provides:
- initialize: basic serverInfo + capabilities
- tools/list: enumerate tools with JSON Schema for parameters
- tools/call: invoke a tool by name using existing ServiceNowMCPServer
"""
from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel


JSONRPC_VERSION = "2.0"


def _param_model_from_func(func) -> Optional[Type[BaseModel]]:
    try:
        sig = inspect.signature(func)
        # We expect signature like (config, auth_manager, params_model)
        params = list(sig.parameters.values())
        if len(params) >= 3:
            p = params[2]
            ann = p.annotation
            try:
                if isinstance(ann, type) and issubclass(ann, BaseModel):
                    return ann
            except Exception:
                return None
    except Exception:
        return None
    return None


def _tool_schema_from_model(model_cls: Optional[Type[BaseModel]]) -> Dict[str, Any]:
    if not model_cls:
        return {"type": "object"}
    try:
        return model_cls.model_json_schema()  # Pydantic v2
    except Exception:
        # Fallback minimal schema
        return {"type": "object"}


def jsonrpc_initialize_result(auth_required: bool = False) -> Dict[str, Any]:
    return {
        "serverInfo": {"name": "ServiceNow MCP Server", "version": "1.0"},
        "capabilities": {
            "tools": {"list": True, "call": True},
            "authentication": {"scheme": "bearer", "required": bool(auth_required)},
        },
    }


def jsonrpc_tools_list(mcp_server) -> List[Dict[str, Any]]:
    """Build JSON-RPC style tool descriptors with input schema."""
    tools = []
    for tool_name, meta in mcp_server.tool_metadata.items():
        module = mcp_server.tools.get(meta.get("module"))
        if not module:
            continue
        operation = meta.get("operation")
        if not operation or not hasattr(module, operation):
            continue
        func = getattr(module, operation)
        model_cls = _param_model_from_func(func)
        schema = _tool_schema_from_model(model_cls)
        tools.append({
            "name": tool_name,
            "description": meta.get("description", f"{tool_name} operation"),
            "inputSchema": schema,
        })
    return tools


def jsonrpc_ok(id_value: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": id_value, "result": result}


def jsonrpc_error(id_value: Any, code: int, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": id_value, "error": err}
