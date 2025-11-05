"""
ServiceNow MCP Server entry point.
"""
import logging
import os
from typing import Dict, Any, AsyncIterator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
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
from utils.logging import setup_logging

# Load environment variables
load_dotenv()

# Configure logging (env-driven)
log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE") or None
log_json = (os.getenv("LOG_JSON", "false").lower() in {"1", "true", "yes"})
setup_logging(log_level=log_level, log_file=log_file, log_json=log_json)
logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _resolve_host(default: str = "0.0.0.0") -> str:
    return (
        os.getenv("UVICORN_HOST")
        or os.getenv("HOST")
        or os.getenv("APP_HOST")
        or os.getenv("BIND_HOST")
        or default
    )


def _resolve_port(default: int = 8000) -> int:
    for key in ("UVICORN_PORT", "PORT", "APP_PORT", "BIND_PORT"):
        value = os.getenv(key)
        if value:
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError(f"Invalid integer for {key}={value!r}") from exc
    return default

# Initialize FastAPI app
app = FastAPI(title="ServiceNow MCP Server")

# Configure CORS (configurable via env CORS_ALLOW_ORIGINS)
def _parse_cors_origins(env_value: Optional[str]) -> list:
    if not env_value or env_value.strip() == "*":
        return ["*"]
    parts = [p.strip() for p in env_value.split(",") if p.strip()]
    return parts or ["*"]

# Determine environment (prod vs dev)
_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").lower()
_is_prod = _env in {"prod", "production"} or (os.getenv("PRODUCTION", "").lower() in {"1", "true", "yes"})

cors_origins = _parse_cors_origins(os.getenv("CORS_ALLOW_ORIGINS", "*"))
# Lock CORS in production if wildcard
if _is_prod and cors_origins == ["*"]:
    cors_origins = []  # No cross-origin unless explicitly configured
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import uuid
        # Allow client-provided request id; otherwise generate
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        # Proceed
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


app.add_middleware(RequestIdMiddleware)




# --- Streaming (SSE) endpoint -------------------------------------------------
async def _sse_event_stream(
    request: Request,
    interval: float = 1.0,
    max_events: Optional[int] = None,
) -> AsyncIterator[bytes]:
    """Async generator that yields Server-Sent Events (SSE).

    - Sends periodic tick events with a timestamp to keep the connection alive.
    - Stops when the client disconnects or the optional max_events is reached.
    """
    import asyncio
    import json
    from datetime import datetime, timezone

    count = 0
    while True:
        # Stop if client disconnected
        try:
            if await request.is_disconnected():
                break
        except Exception:
            # If detection fails, proceed conservatively
            pass

        payload = {
            "type": "tick",
            "ts": datetime.now(timezone.utc).isoformat(),
            "count": count,
        }
        data = f"id: {count}\nevent: tick\ndata: {json.dumps(payload)}\n\n"
        yield data.encode("utf-8")

        count += 1
        if max_events is not None and count >= max_events:
            break

        try:
            await asyncio.sleep(max(0.05, float(interval)))
        except Exception:
            # If sleep fails due to cancellation, exit
            break


@app.get("/events")
async def events(
    request: Request,
    interval: float = 1.0,
    limit: Optional[int] = None,
):
    """Simple SSE endpoint for real-time, streamable HTTP.

    Query params:
    - interval: seconds between events (default 1.0)
    - limit: optional maximum number of events to send
    """
    # Optional auth for events when EVENTS_AUTH_REQUIRED=true
    # Default to requiring auth in production unless explicitly disabled
    env_val = os.getenv("EVENTS_AUTH_REQUIRED")
    if env_val is None:
        auth_required = _is_prod
    else:
        auth_required = env_val.lower() in {"1", "true", "yes"}
    if auth_required:
        expected = os.getenv("EVENTS_AUTH_TOKEN") or os.getenv("RPC_AUTH_TOKEN")
        provided = request.headers.get("Authorization") or request.query_params.get("auth")
        if isinstance(provided, str) and provided.lower().startswith("bearer "):
            provided = provided.split(" ", 1)[1]
        if not expected or provided != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # Disable buffering on some proxies
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        _sse_event_stream(request, interval=interval, max_events=limit),
        media_type="text/event-stream",
        headers=headers,
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
async def handle_jsonrpc(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
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
                provided = request.headers.get("Authorization")
                if isinstance(provided, str) and provided.lower().startswith("bearer "):
                    provided = provided.split(" ", 1)[1]
                # Back-compat: allow token via params.auth/Authorization, configurable
                # Default disabled in production
                allow_params_env = os.getenv("RPC_ALLOW_PARAMS_AUTH")
                if allow_params_env is None:
                    allow_params = not _is_prod
                else:
                    allow_params = allow_params_env.lower() in {"1", "true", "yes"}
                if not provided and allow_params and isinstance(params, dict):
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
    uvicorn.run(
        app,
        host=_resolve_host(),
        port=_resolve_port(),
        reload=_env_flag("UVICORN_RELOAD", default=True),
    )
