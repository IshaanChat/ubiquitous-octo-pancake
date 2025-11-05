 ServiceNow MCP Server

Comprehensive FastAPI service exposing Model Context Protocol (MCP) tools to automate and interact with ServiceNow. The server wraps ServiceNow REST APIs behind consistent tool interfaces, supports JSON‑RPC discovery/calls, and provides a minimal REST surface for health and introspection.

Core capabilities:
- MCP request handling and tool routing
- JSON‑RPC 2.0 endpoint for initialize, tool listing, and calling
- Modular tool suite: Service Desk, Catalogue, Change, Knowledge, and Systems Administration
- Configurable authentication (Basic, OAuth, API Key)
- Secure HTTP client patterns with retries and rate limiting

## Requirements
- Python 3.8+
- Access to a ServiceNow instance and credentials

## Quick Start
1) Install dependencies
```bash
pip install -r requirements.txt
```

2) Configure environment (create `.env` or export)
```bash
# Required
SERVICENOW_INSTANCE=your-instance.service-now.com
AUTH_TYPE=basic                   # basic | oauth | api_key
SERVICENOW_USERNAME=your-user
SERVICENOW_PASSWORD=your-pass

# Optional (OAuth)
OAUTH_CLIENT_ID=
OAUTH_CLIENT_SECRET=
OAUTH_TOKEN_URL=                  # defaults to https://<instance>/oauth_token.do

# Optional (API Key)
API_KEY=
API_KEY_HEADER=X-ServiceNow-API-Key

# Optional: protect /rpc tools.call
RPC_AUTH_TOKEN=
```

3) Run the server
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Windows setup helper:
```powershell
scripts/setup.ps1
```

## Endpoints
- `POST /mcp` — Accepts MCP requests and returns MCP responses
- `POST /rpc` — JSON‑RPC 2.0 methods: `initialize`, `tools/list`, `tools/call`
- `GET /tools` — Lists available tools from the server runtime
- `GET /health` — Health and ServiceNow connectivity check
- `GET /events` — Server-Sent Events (SSE) stream for real-time, streamable HTTP

If `RPC_AUTH_TOKEN` is set, `/rpc` requires `Bearer <token>` (via JSON params `auth` or `Authorization`).
For production, prefer the standard HTTP `Authorization: Bearer <token>` header.

## MCP Protocol
- Request model: `src/mcp_core/protocol.py: MCPRequest(version, type="request", id, tool, parameters)`
- Response model: `MCPResponse(version, type="response"|"error", id, result?, error?)`
- The server routes `tool` names in the form `<module>.<operation>` to functions in `src/tools/*`.

Example MCP requests:
```json
{"version":"1.0","type":"request","id":"1","tool":"service_desk.list_incidents","parameters":{"limit":5}}
```
```json
{"version":"1.0","type":"request","id":"2","tool":"catalogue.get_catalog_item","parameters":{"item_id":"1234567890abcdef"}}
```

## JSON‑RPC Helpers
Located in `src/mcp_core/jsonrpc.py` and wired in `src/main.py`.
- `initialize` returns `serverInfo` and capabilities with optional auth requirement.
- `tools/list` enumerates tools with JSON Schema of inputs where available.
- `tools/call` invokes a tool by name; arguments go under `params.arguments`.

## Authentication
Configured in `src/config.py` and normalized/handled by `src/auth/auth_manager.py`.
- Basic: `AUTH_TYPE=basic` + `SERVICENOW_USERNAME`/`SERVICENOW_PASSWORD`
- OAuth: `AUTH_TYPE=oauth` + `OAUTH_CLIENT_ID`/`OAUTH_CLIENT_SECRET`/user credentials
- API Key: `AUTH_TYPE=api_key` + `API_KEY` (and optional `API_KEY_HEADER`)

The server builds `ServerConfig` from env in `src/main.py` and passes it to the MCP core.

## HTTP Client, Retries, Rate Limiting
`src/utils/http_client.py` implements secure defaults:
- HTTPX async client with SSL verification and conservative connection limits
- Exponential backoff on server/network errors
- 429 handling with `Retry-After`
- Token refresh on 401/403 (delegated to `AuthManager`)
- Simple rate limiter (requests/minute)

### Streamable HTTP
- Server-side SSE: see `src/main.py:events` which returns `text/event-stream` and emits periodic events.
- Client-side streaming: use `src/utils/http_client.py:stream_request` to iterate bytes (or lines via `as_lines=True`) without buffering entire bodies.

Example client usage:
```python
from utils.http_client import stream_request

async for chunk in stream_request("GET", "http://localhost:8000/events", config, auth_manager):
    print(chunk.decode().rstrip())
```

## Tools Overview
Each tool module exposes operations with Pydantic parameter models and metadata:
- `src/tools/service_desk.py` — Incidents and user lookups
  - list/get/create/update incidents; add comments; resolve incidents
  - list/get users
- `src/tools/catalogue_builder.py` — Service catalog and categories
  - list/get/create/update catalog items
  - list/create/update categories
- `src/tools/change_coordinator.py` — Change requests and approvals
  - list/get/create/update change requests; approve/reject
- `src/tools/knowledge_author.py` — Knowledge base articles
  - list/get/create/update articles
- `src/tools/systems_administrator.py` — Users and groups
  - list/get/create/update users and groups
 - `src/tools/cmdb_reader.py` — CMDB read-only access
   - list/get configuration items; list relationships

Tool names are `<module>.<operation>` (e.g., `service_desk.list_incidents`, `catalogue.get_catalog_item`). Use `/rpc` `tools/list` to see schemas.

## Configuration Reference
Environment variables read at startup (`.env` supported via dotenv):
- `SERVICENOW_INSTANCE` — domain or full URL; prefix added if missing (`https://`)
- `AUTH_TYPE` — `basic` | `oauth` | `api_key`
- `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD` — credentials
- `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OAUTH_TOKEN_URL` — OAuth settings
- `API_KEY`, `API_KEY_HEADER` — API key settings
- `RPC_AUTH_TOKEN` — enables bearer token check for `/rpc`
- `RPC_ALLOW_PARAMS_AUTH` — when truthy (default), allows token in JSON params for back-compat
- `CORS_ALLOW_ORIGINS` — comma-separated list of allowed origins (default `*`)
- `EVENTS_AUTH_REQUIRED` — when truthy (`true/1/yes`), `/events` requires bearer auth
- `EVENTS_AUTH_TOKEN` — optional token for `/events` (falls back to `RPC_AUTH_TOKEN`)
- `LOG_LEVEL` — `DEBUG|INFO|WARNING|ERROR|CRITICAL` (default `INFO`)
- `LOG_JSON` — when truthy, logs in JSON lines format
- `LOG_FILE` — optional log file path (rotating)
- `APP_ENV`/`ENVIRONMENT`/`PRODUCTION` — when set to production, defaults change:
  - CORS wildcard is disabled unless explicitly allowed
  - `/events` requires auth by default
  - `RPC_ALLOW_PARAMS_AUTH` defaults to false (header-only auth)


Additional runtime behavior (in code): timeouts, limited connection pooling, and headers hardened per call.

Note on `config/tool_packages.yaml`: this file documents a curated grouping of operations per tool for reference. It is not currently enforced at runtime.

## Development
- Run server: `uvicorn src.main:app --reload`
- Code layout:
  - `src/main.py` — FastAPI app, routes for `/mcp`, `/rpc`, `/tools`, `/health`
  - `src/mcp_core/` — protocol models, JSON‑RPC helpers, server router
  - `src/tools/` — tool implementations and operation metadata
  - `src/utils/` — HTTP client, logging, error utilities
  - `scripts/setup.ps1` — Windows bootstrap

## Testing
Run tests with pytest:
```bash
pytest -q
```
Highlights:
- `tests/test_rpc_endpoint.py` — JSON‑RPC smoke and auth behavior
- `tests/test_protocol.py` — MCP request/response model validation
- Tool tests under `tests/` for service_desk, catalogue, change, knowledge, system
- `tests/.env.test` — sample env values for local runs

## Replicate on Another Machine
```bash
git clone <your-remote-url> mcp
cd mcp
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # edit with real values
uvicorn src.main:app --reload
```

## Docker
- Build image:
```bash
docker build -t mcp-server .
```
- Run container (loads env from your local `.env`):
```bash
docker run --rm -p 8000:8000 --env-file .env mcp-server
```
- Test streamable HTTP (SSE):
```bash
curl -N "http://localhost:8000/events?interval=0.5&limit=5"
```

Notes:
- See `Dockerfile:1` for the base image and runtime command.
- `.dockerignore:1` is included to keep images small (excludes venvs, caches, tests, and local files).
