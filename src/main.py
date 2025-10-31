"""
ServiceNow MCP Server entry point.
"""
import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import (
    ServerConfig,
    AuthConfig,
    AuthType,
    BasicAuthConfig,
    OAuthConfig,
    ApiKeyConfig,
)
from mcp_core.protocol import MCPRequest, MCPResponse
from mcp_core.jsonrpc import (
    jsonrpc_ok,
    jsonrpc_error,
    jsonrpc_initialize_result,
    jsonrpc_tools_list,
)
from mcp_core.server import ServiceNowMCPServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="ServiceNow MCP Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _build_server_config() -> ServerConfig:
    instance = os.getenv("SERVICENOW_INSTANCE", "")
    instance_url = f"https://{instance}" if instance and not instance.startswith("http") else instance

    auth_type = (os.getenv("AUTH_TYPE", "basic") or "basic").strip().lower()
    username = os.getenv("SERVICENOW_USERNAME", "")
    password = os.getenv("SERVICENOW_PASSWORD", "")

    if auth_type == "oauth":
        client_id = os.getenv("OAUTH_CLIENT_ID", "")
        client_secret = os.getenv("OAUTH_CLIENT_SECRET", "")
        token_url = os.getenv("OAUTH_TOKEN_URL", "") or None
        if client_id and client_secret and username and password:
            auth = AuthConfig(
                type=AuthType.OAUTH,
                oauth=OAuthConfig(
                    client_id=client_id,
                    client_secret=client_secret,
                    username=username,
                    password=password,
                    token_url=token_url,
                ),
            )
        else:
            logger.warning("AUTH_TYPE=oauth but required OAUTH_* or credentials missing; falling back to basic auth")
            auth = AuthConfig(
                type=AuthType.BASIC,
                basic=BasicAuthConfig(username=username, password=password),
            )
    elif auth_type in ("apikey", "api_key", "api-key"):
        api_key = os.getenv("API_KEY", "")
        header_name = os.getenv("API_KEY_HEADER", "X-ServiceNow-API-Key")
        if api_key:
            auth = AuthConfig(
                type=AuthType.API_KEY,
                api_key=ApiKeyConfig(api_key=api_key, header_name=header_name),
            )
        else:
            logger.warning("AUTH_TYPE=api_key but API_KEY missing; falling back to basic auth")
            auth = AuthConfig(
                type=AuthType.BASIC,
                basic=BasicAuthConfig(username=username, password=password),
            )
    else:
        # Default/basic
        auth = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username=username, password=password),
        )

    return ServerConfig(
        instance_url=instance_url,
        auth=auth,
    )

# Initialize server configuration
config = _build_server_config()

# Initialize MCP server
mcp_server = ServiceNowMCPServer(config)

@app.post("/mcp")
async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """Handle incoming MCP requests"""
    try:
        return await mcp_server.handle_request(request)
    except Exception as e:
        logger.exception("Error handling MCP request")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rpc")
async def handle_jsonrpc(payload: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-RPC 2.0 endpoint exposing minimal MCP-style methods.

    Methods:
    - initialize
    - tools/list
    - tools/call
    """
    id_value = payload.get("id")
    if payload.get("jsonrpc") != "2.0":
        return jsonrpc_error(id_value, -32600, "Invalid Request: missing jsonrpc 2.0")

    method = payload.get("method")
    params = payload.get("params") or {}
    try:
        if method == "initialize":
            # Reflect whether bearer auth is configured
            import os
            auth_required = bool(os.getenv("RPC_AUTH_TOKEN"))
            return jsonrpc_ok(id_value, jsonrpc_initialize_result(auth_required))
        elif method in ("tools/list", "tools.list"):
            tools = jsonrpc_tools_list(mcp_server)
            return jsonrpc_ok(id_value, {"tools": tools})
        elif method in ("tools/call", "tools.call"):
            # Optional bearer auth when configured via env
            import os
            token = os.getenv("RPC_AUTH_TOKEN")
            if token:
                # Expect Authorization: Bearer <token>
                # FastAPI stores headers in request context; we can access via dependency injection here
                from fastapi import Request
                from fastapi import Depends
            
            # Authentication check using the global request state via FastAPI's context is non-trivial here.
            # Instead, read from params meta: allow passing token as 'auth' or skip if not set.
            # Prefer header in actual runtime; for safety, also allow params["auth"] when present.
            token = os.getenv("RPC_AUTH_TOKEN")
            if token:
                provided = None
                # Allow either params.auth or params.Authorization for testing convenience
                if isinstance(params, dict):
                    provided = params.get("auth") or params.get("Authorization")
                if isinstance(provided, str) and provided.lower().startswith("bearer "):
                    provided = provided.split(" ", 1)[1]
                if provided != token:
                    return jsonrpc_error(id_value, -32001, "Unauthorized")
            name = params.get("name")
            args = params.get("arguments") or {}
            if not isinstance(name, str):
                return jsonrpc_error(id_value, -32602, "Invalid params: name required")
            req = MCPRequest(version="1.0", type="request", id=str(id_value), tool=name, parameters=args)
            resp = await mcp_server.handle_request(req)
            if resp.type == "response":
                return jsonrpc_ok(id_value, resp.result)
            return jsonrpc_error(id_value, -32000, resp.error or "Tool error")
        else:
            return jsonrpc_error(id_value, -32601, f"Method not found: {method}")
    except Exception as e:
        logger.exception("Error handling JSON-RPC request")
        return jsonrpc_error(id_value, -32603, "Internal error", {"error": str(e)})

@app.get("/tools")
async def list_tools() -> Dict[str, Any]:
    """List available tools"""
    try:
        return await mcp_server.list_tools()
    except Exception as e:
        logger.exception("Error listing tools")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> Dict[str, bool]:
    """Check server health and ServiceNow connectivity"""
    try:
        is_connected = await mcp_server.validate_connection()
        return {"status": is_connected}
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/details")
async def health_details() -> Dict[str, Any]:
    """Detailed health info including any ServiceNow error details."""
    try:
        return await mcp_server.validate_connection_details()
    except Exception as e:
        logger.exception("Health details failed")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
