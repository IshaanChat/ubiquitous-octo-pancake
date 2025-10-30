"""
ServiceNow MCP protocol implementation and request/response models.
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional, Literal

class MCPRequest(BaseModel):
    """MCP Request model following the protocol specification"""
    version: str
    type: Literal["request"]
    id: str
    tool: str
    parameters: Dict[str, Any]

class MCPResponse(BaseModel):
    """MCP Response model following the protocol specification"""
    version: str
    type: Literal["response", "error"]
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ServiceNowOperation(BaseModel):
    """Base model for ServiceNow operations"""
    operation: str
    table: Optional[str] = None
    sys_id: Optional[str] = None
    query: Optional[str] = None
    fields: Optional[list[str]] = None