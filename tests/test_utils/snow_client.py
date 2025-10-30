"""Mock ServiceNow client utilities for tests."""
import pytest
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def mock_snow_client():
    """Pytest fixture: bare mock client with async HTTP methods."""
    client = Mock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


def make_mock_snow_client(payload=None, status_code: int = 200, headers: dict | None = None):
    """Factory that returns a configured mock ServiceNow client.

    - Each HTTP method returns an object with async .json() and .raise_for_status()
    - .json() yields the provided payload as-is (no wrapping)
    - .headers and .status_code are set for callers that inspect them
    """
    client = Mock()

    def _make_response():
        resp = AsyncMock()
        resp.status_code = status_code
        resp.headers = headers or {}
        # raise_for_status behaves like httpx: no-op if < 400, else raise
        if status_code >= 400:
            async def _raiser(*_a, **_k):
                raise Exception(f"HTTP {status_code}")
            resp.raise_for_status.side_effect = _raiser
        else:
            async def _ok(*_a, **_k):
                return None
            resp.raise_for_status.side_effect = None
            resp.raise_for_status.return_value = None
            resp.raise_for_status = AsyncMock(side_effect=_ok)

        async def _json():
            return payload
        resp.json = AsyncMock(side_effect=_json)
        return resp

    response = _make_response()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.put = AsyncMock(return_value=response)
    client.delete = AsyncMock(return_value=response)
    return client
