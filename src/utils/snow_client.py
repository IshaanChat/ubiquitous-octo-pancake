"""
Thin ServiceNow HTTP client used by the MCP server.

Provides async get/post/put/delete methods that:
- Attach auth + default headers via AuthManager
- Use httpx.AsyncClient with secure defaults
- Raise for HTTP errors so callers can handle via existing try/except
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from config import ServerConfig
from auth.auth_manager import AuthManager


logger = logging.getLogger(__name__)


def _secure_headers(base: Dict[str, str]) -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        **(base or {}),
    }
    return headers


class ServiceNowClient:
    def __init__(self, config: ServerConfig, auth_manager: AuthManager):
        self.config = config
        self.auth_manager = auth_manager

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.config.timeout,
            verify=True,
            http2=False,  # Disable HTTP/2 to avoid h2 dependency
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        auth_headers = await self.auth_manager.aget_headers()
        all_headers = _secure_headers(auth_headers)
        if headers:
            all_headers.update(headers)

        async with await self._client() as client:
            resp = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=all_headers,
            )
            # Raise for non-2xx so tool-level error handling kicks in
            resp.raise_for_status()
            return resp

    # Public HTTP helpers used by tool functions
    async def get(self, url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        return await self._request("GET", url, params=params, headers=headers)

    async def post(self, url: str, *, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        return await self._request("POST", url, json=json, headers=headers)

    async def put(self, url: str, *, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        return await self._request("PUT", url, json=json, headers=headers)

    async def delete(self, url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        return await self._request("DELETE", url, params=params, headers=headers)
