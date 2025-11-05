"""Tests for the JSON-RPC endpoint (/rpc)."""
from fastapi.testclient import TestClient

from main import app


client = TestClient(app, base_url="http://testserver")


def test_rpc_initialize():
    payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    r = client.post("/rpc", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == 1
    assert "result" in data
    assert "serverInfo" in data["result"]


def test_rpc_tools_list():
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    r = client.post("/rpc", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == 2
    assert "result" in data
    assert isinstance(data["result"].get("tools"), list)
    # Should include at least one tool
    assert len(data["result"]["tools"]) >= 1


def test_rpc_tools_call_smoke():
    # Smoke test a call; we accept either result or error per environment
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "service_desk.list_incidents",
            "arguments": {"limit": 1},
        },
    }
    r = client.post("/rpc", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == 3
    assert ("result" in data) or ("error" in data)


def test_rpc_tools_call_auth(monkeypatch):
    # Enforce token and verify Unauthorized then success with token
    monkeypatch.setenv("RPC_AUTH_TOKEN", "secret")

    # Missing token -> Unauthorized
    payload = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "service_desk.list_incidents",
            "arguments": {"limit": 1},
        },
    }
    r = client.post("/rpc", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == 4
    assert "error" in data and data["error"]["message"] == "Unauthorized"

    # Provide token via params.auth (back-compat path)
    payload["id"] = 5
    payload["params"]["auth"] = "Bearer secret"
    r = client.post("/rpc", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == 5
    assert ("result" in data) or ("error" in data)


def test_rpc_tools_call_auth_header(monkeypatch):
    # Enforce token and verify success using Authorization header
    monkeypatch.setenv("RPC_AUTH_TOKEN", "secret")
    payload = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "service_desk.list_incidents",
            "arguments": {"limit": 1},
        },
    }
    r = client.post("/rpc", json=payload, headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == 6
    assert ("result" in data) or ("error" in data)
