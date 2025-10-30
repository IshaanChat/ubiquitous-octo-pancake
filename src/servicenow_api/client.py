"""
ServiceNow API client implementation for handling operations.
"""
import httpx
from typing import Dict, Any, Optional
from ..mcp_core.protocol import ServiceNowOperation

class ServiceNowClient:
    """Client for interacting with ServiceNow REST API"""
    
    def __init__(self, instance: str, username: str, password: str):
        self.base_url = f"https://{instance}.service-now.com/api/now"
        self.auth = (username, password)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def handle_operation(self, tool: str, operation: str, **params) -> Dict[str, Any]:
        """Handle different ServiceNow operations based on tool and operation type"""
        op = ServiceNowOperation(operation=operation, **params)
        
        if tool == "servicenow.incident":
            return await self._handle_incident_operation(op)
        elif tool == "servicenow.catalog":
            return await self._handle_catalog_operation(op)
        elif tool == "servicenow.change":
            return await self._handle_change_operation(op)
        else:
            raise ValueError(f"Unsupported tool: {tool}")

    async def _handle_incident_operation(self, op: ServiceNowOperation) -> Dict[str, Any]:
        """Handle incident-related operations"""
        if op.operation == "get":
            return await self._get_record("incident", op.sys_id, op.fields)
        elif op.operation == "create":
            return await self._create_record("incident", op.parameters)
        elif op.operation == "update":
            return await self._update_record("incident", op.sys_id, op.parameters)
        else:
            raise ValueError(f"Unsupported incident operation: {op.operation}")

    async def _handle_catalog_operation(self, op: ServiceNowOperation) -> Dict[str, Any]:
        """Handle service catalog operations"""
        # Implement catalog operations
        pass

    async def _handle_change_operation(self, op: ServiceNowOperation) -> Dict[str, Any]:
        """Handle change request operations"""
        # Implement change operations
        pass

    async def _get_record(self, table: str, sys_id: str, fields: Optional[list[str]] = None) -> Dict[str, Any]:
        """Get a record from ServiceNow"""
        async with httpx.AsyncClient() as client:
            params = {}
            if fields:
                params["sysparm_fields"] = ",".join(fields)
            
            response = await client.get(
                f"{self.base_url}/table/{table}/{sys_id}",
                auth=self.auth,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json().get("result", {})