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
