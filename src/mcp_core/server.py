"""
ServiceNow MCP Server implementation for handling requests and tools.
"""
import json
import logging
import os
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Type

import yaml
from pydantic import ValidationError, BaseModel

from auth.auth_manager import AuthManager
from config import ServerConfig
from mcp_core.protocol import MCPRequest, MCPResponse, ServiceNowOperation
from utils.snow_client import ServiceNowClient
from tools import (
    service_desk,
    catalogue_builder,
    change_coordinator,
    knowledge_author,
    systems_administrator,
)

logger = logging.getLogger(__name__)


class ServiceNowMCPServer:
    """
    ServiceNow MCP Server implementation.

    This class provides a Model Context Protocol (MCP) server for ServiceNow,
    allowing LLMs to interact with ServiceNow data and functionality.
    """

    def __init__(self, config: ServerConfig):
        """
        Initialize the ServiceNow MCP server.

        Args:
            config: Server configuration.
        """
        self.config = config
        self.auth_manager = AuthManager(self.config.auth, self.config.instance_url)
        # Real HTTP client that tools can call (compatible with tests where a mock client is passed)
        self.http_client = ServiceNowClient(self.config, self.auth_manager)
        
        # Initialize tool modules
        self.tools = {
            "service_desk": service_desk,
            "catalogue": catalogue_builder,
            "change": change_coordinator,
            "knowledge": knowledge_author,
            "system": systems_administrator
        }

        # Load tool metadata
        self.tool_metadata = self._load_tool_metadata()
        logger.info(f"Loaded {len(self.tool_metadata)} tools")

    def _load_tool_metadata(self) -> Dict[str, Dict]:
        """
        Load metadata for all available tools.
        
        Returns:
            Dictionary mapping tool names to their metadata.
        """
        metadata = {}
        for module_name, module in self.tools.items():
            if hasattr(module, "OPERATIONS"):
                for op_name, op_meta in module.OPERATIONS.items():
                    tool_name = f"{module_name}.{op_name}"
                    metadata[tool_name] = {
                        "module": module_name,
                        "operation": op_name,
                        **op_meta
                    }
        return metadata

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle an incoming MCP request.

        Args:
            request: The MCP request to handle.

        Returns:
            The MCP response.
        """
        try:
            # Parse tool name and operation
            if "." not in request.tool:
                return MCPResponse(
                    version=request.version,
                    type="error",
                    id=request.id,
                    error="Invalid tool name format. Expected: module.operation"
                )

            module_name, operation = request.tool.split(".", 1)
            
            # Check if module exists
            if module_name not in self.tools:
                return MCPResponse(
                    version=request.version,
                    type="error",
                    id=request.id,
                    error=f"Unknown module: {module_name}"
                )

            # Check if operation exists
            module = self.tools[module_name]
            if not hasattr(module, operation):
                return MCPResponse(
                    version=request.version,
                    type="error",
                    id=request.id,
                    error=f"Unknown operation: {operation} in module {module_name}"
                )

            # Get operation metadata
            tool_name = f"{module_name}.{operation}"
            metadata = self.tool_metadata.get(tool_name)
            if not metadata:
                return MCPResponse(
                    version=request.version,
                    type="error",
                    id=request.id,
                    error=f"No metadata found for tool: {tool_name}"
                )

            # Validate required parameters
            required_params = metadata.get("required_params", [])
            for param in required_params:
                if param not in request.parameters:
                    return MCPResponse(
                        version=request.version,
                        type="error",
                        id=request.id,
                        error=f"Missing required parameter: {param}"
                    )

            # Execute operation
            operation_func = getattr(module, operation)

            # Build a params model instance if the function expects one
            bound_params: Dict[str, Any] = {
                "config": self.config,
                "auth_manager": self.http_client,
            }
            try:
                sig = inspect.signature(operation_func)
                params_param = None
                for name, param in list(sig.parameters.items())[2:3]:  # third parameter
                    params_param = param
                    break
                if params_param is not None and params_param.annotation is not inspect._empty:
                    ann = params_param.annotation
                    model_cls: Optional[Type[BaseModel]] = None
                    try:
                        # Pydantic BaseModel subclass?
                        if isinstance(ann, type) and issubclass(ann, BaseModel):
                            model_cls = ann
                    except Exception:
                        model_cls = None
                    if model_cls:
                        bound_params[params_param.name] = model_cls(**request.parameters)
                    else:
                        # Fall back to passing raw parameters dict under expected name
                        bound_params[params_param.name] = request.parameters
                else:
                    # No typed params; pass through kwargs
                    bound_params.update(request.parameters)
            except Exception as e:
                return MCPResponse(
                    version=request.version,
                    type="error",
                    id=request.id,
                    error=f"Parameter binding failed: {str(e)}"
                )

            result = await operation_func(**bound_params)

            return MCPResponse(
                version=request.version,
                type="response",
                id=request.id,
                result=result
            )

        except ValidationError as e:
            return MCPResponse(
                version=request.version,
                type="error",
                id=request.id,
                error=f"Invalid parameters: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error handling request: {e}")
            return MCPResponse(
                version=request.version,
                type="error",
                id=request.id,
                error=f"Internal server error: {str(e)}"
            )

    async def list_tools(self) -> Dict[str, Any]:
        """
        Get a list of all available tools and their metadata.

        Returns:
            Dictionary containing tool information.
        """
        return {
            "tools": self.tool_metadata,
            "modules": list(self.tools.keys())
        }

    async def validate_connection(self) -> bool:
        """
        Validate the connection to ServiceNow.

        Returns:
            True if connection is valid, False otherwise.
        """
        try:
            # Perform a lightweight request to validate connectivity and auth
            try:
                resp = await self.http_client.get(
                    f"{self.config.api_url}/table/sys_user", params={"sysparm_limit": 1}
                )
                # If request succeeded (2xx), consider healthy. JSON parse not required.
                _ = resp.status_code  # ensure response object
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False

    async def validate_connection_details(self) -> Dict[str, Any]:
        """Detailed connectivity check including error information."""
        url = f"{self.config.api_url}/table/sys_user"
        details: Dict[str, Any] = {"status": False, "url": url}
        try:
            resp = await self.http_client.get(url, params={"sysparm_limit": 1})
            details.update({
                "status": True,
                "http_status": getattr(resp, "status_code", None),
            })
            try:
                body = resp.json()
                details["sample"] = body
            except Exception:
                details["sample"] = None
            return details
        except Exception as e:
            # Try to extract status code/message if available
            http_status = getattr(getattr(e, "response", None), "status_code", None)
            err_text = None
            try:
                if getattr(e, "response", None) is not None:
                    err_text = e.response.text
            except Exception:
                err_text = str(e)
            details.update({
                "status": False,
                "http_status": http_status,
                "error": str(e),
                "error_text": err_text,
            })
            return details
