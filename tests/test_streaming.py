"""Tests for the SSE streaming endpoint (/events)."""
from fastapi.testclient import TestClient

from main import app


def test_sse_events_basic_response():
    client = TestClient(app, base_url="http://testserver")
    # Use a fast interval and small limit so the test completes quickly
    r = client.get("/events", params={"interval": 0.01, "limit": 3})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")

    text = r.text
    # Should contain at least 3 tick events and corresponding data lines
    assert text.count("event: tick") >= 3
    assert text.count("data: ") >= 3


def test_sse_events_stream_interface():
    client = TestClient(app, base_url="http://testserver")
    # Verify streaming consumption using TestClient.stream
    collected = []
    with client.stream("GET", "/events", params={"interval": 0.005, "limit": 5}) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line:
                continue
            # Normalize to str for assertions
            if isinstance(line, (bytes, bytearray)):
                line = line.decode("utf-8", errors="ignore")
            collected.append(line)

    # Confirm multiple SSE lines were received
    assert any(l.startswith("event: tick") for l in collected)
    assert sum(1 for l in collected if l.startswith("data: ")) >= 5


def test_sse_events_auth(monkeypatch):
    # Require auth and ensure 401 without token, 200 with
    monkeypatch.setenv("EVENTS_AUTH_REQUIRED", "true")
    monkeypatch.setenv("EVENTS_AUTH_TOKEN", "secret")

    client = TestClient(app, base_url="http://testserver")

    # No token -> 401
    r = client.get("/events", params={"interval": 0.01, "limit": 1})
    assert r.status_code == 401

    # With Authorization header -> 200 and 1 event
    r = client.get(
        "/events",
        params={"interval": 0.01, "limit": 1},
        headers={"Authorization": "Bearer secret"},
    )
    assert r.status_code == 200
    assert "event: tick" in r.text
