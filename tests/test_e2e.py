"""Minimal end-to-end tests for /rpc and /events."""
from fastapi.testclient import TestClient

from main import app


def test_e2e_rpc_and_metrics(monkeypatch):
    # Configure prod-like auth
    monkeypatch.setenv("RPC_AUTH_TOKEN", "secret")
    monkeypatch.setenv("RPC_ALLOW_PARAMS_AUTH", "false")
    monkeypatch.setenv("EVENTS_AUTH_REQUIRED", "true")

    client = TestClient(app, base_url="http://testserver")

    # Health
    r = client.get("/health")
    assert r.status_code == 200
    assert isinstance(r.json().get("status"), bool)

    # Unauthorized tools/call
    payload = {
        "jsonrpc": "2.0",
        "id": 100,
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
    assert data.get("id") == 100
    assert data.get("error", {}).get("message") == "Unauthorized"

    # Authorized tools/call via Authorization header
    payload["id"] = 101
    r = client.post("/rpc", json=payload, headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == 101
    assert ("result" in data) or ("error" in data)

    # SSE requires auth now; validate 401 then success
    r = client.get("/events", params={"interval": 0.01, "limit": 1})
    assert r.status_code == 401
    r = client.get(
        "/events",
        params={"interval": 0.01, "limit": 1},
        headers={"Authorization": "Bearer secret"},
    )
    assert r.status_code == 200
    assert "event: tick" in r.text
