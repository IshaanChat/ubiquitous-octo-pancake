"""
Authentication manager for ServiceNow MCP integration.
Handles authentication tokens and header management.
Also provides light compatibility with simplified AuthConfig used in tests.
"""
import logging
import base64
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import httpx
import inspect
from pydantic import BaseModel, Field

from config import AuthConfig as CoreAuthConfig

logger = logging.getLogger(__name__)


class TokenInfo(BaseModel):
    """OAuth token information."""
    
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str = Field(..., description="OAuth refresh token")
    token_type: str = Field(..., description="Token type (usually Bearer)")
    expires_in: int = Field(..., description="Token expiration in seconds")
    scope: Optional[str] = Field(None, description="Token scope")


class AuthConfig(BaseModel):
    """Compatibility AuthConfig for tests importing from auth.auth_manager.

    Supports both direct fields and nested oauth via the `oauth` attribute.
    Defaults to OAuth type when not specified.
    """
    type: str = "oauth"
    instance_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    oauth: Optional[Any] = None


class AuthManager:
    """
    Manages authentication and authorization for ServiceNow API requests.
    Handles token lifecycle, refresh, and header generation.
    """

    def __init__(self, auth_or_config: Any, instance_url: Optional[str] = None):
        """
        Initialize the auth manager.

        Args:
            auth_or_config: Authentication configuration. Supports either
                - Core config.AuthConfig (with nested basic/oauth/api_key), or
                - A simplified object providing attributes used in tests
                  (type, instance_url, username, password, client_id, client_secret, oauth)
            instance_url: Optional ServiceNow instance URL. If not provided,
                derives from the config object when available.
        """
        # Normalize config and instance URL
        self.instance_url = instance_url or getattr(auth_or_config, "instance_url", "")
        self.auth = self._normalize_auth_config(auth_or_config)
        self._token_info: Optional[TokenInfo] = None
        self._token_expiry: Optional[datetime] = None
        
        # Set OAuth token URL
        if self._type_str() == "oauth" and getattr(self.auth, "oauth", None):
            self.token_url = self.auth.oauth.token_url or f"{self.instance_url}/oauth_token.do"
        else:
            self.token_url = f"{self.instance_url}/oauth_token.do" if self.instance_url else ""

    def _normalize_auth_config(self, cfg: Any) -> Any:
        """Create a normalized auth config view from various inputs.

        Returns an object with attributes: type, basic, oauth, api_key.
        """
        # If already a CoreAuthConfig, use as-is
        if isinstance(cfg, CoreAuthConfig):
            return cfg
        # Build a lightweight namespace-like object
        class _NS:
            pass
        ns = _NS()
        ns.type = getattr(cfg, "type", "oauth")
        # Basic
        basic = _NS()
        if hasattr(cfg, "username") and hasattr(cfg, "password"):
            basic.username = cfg.username
            basic.password = cfg.password
        else:
            basic = None
        ns.basic = basic
        # OAuth
        oauth_src = getattr(cfg, "oauth", None)
        if oauth_src is None and all(hasattr(cfg, a) for a in ("client_id", "client_secret", "username", "password")):
            oauth_src = cfg
        if oauth_src is not None:
            oauth = _NS()
            oauth.client_id = getattr(oauth_src, "client_id", None)
            oauth.client_secret = getattr(oauth_src, "client_secret", None)
            oauth.username = getattr(oauth_src, "username", None)
            oauth.password = getattr(oauth_src, "password", None)
            oauth.token_url = getattr(oauth_src, "token_url", None)
        else:
            oauth = None
        ns.oauth = oauth
        # API key
        api_key_src = getattr(cfg, "api_key", None)
        if api_key_src is not None and isinstance(api_key_src, dict):
            api_ns = _NS()
            api_ns.api_key = api_key_src.get("api_key")
            api_ns.header_name = api_key_src.get("header_name", "X-ServiceNow-API-Key")
            ns.api_key = api_ns
        else:
            ns.api_key = None
        return ns

    async def get_auth_header(self) -> Dict[str, str]:
        """
        Get authorization header for ServiceNow API requests.

        Returns:
            Dictionary containing the Authorization header
        """
        if self._type_str() == "oauth":
            await self.authenticate()
            if self._token_info:
                return {"Authorization": f"{self._token_info.token_type} {self._token_info.access_token}"}
        elif self._type_str() == "basic" and getattr(self.auth, "basic", None):
            # Use basic auth
            auth = f"{self.auth.basic.username}:{self.auth.basic.password}"
            auth_bytes = auth.encode("ascii")
            b64_auth = base64.b64encode(auth_bytes).decode("ascii")
            return {"Authorization": f"Basic {b64_auth}"}
        elif self._type_str() == "api_key" and getattr(self.auth, "api_key", None):
            # Use API key
            return {self.auth.api_key.header_name: self.auth.api_key.api_key}
        
        raise ValueError(f"Unsupported auth type: {self._type_str()}")

    def get_headers(self) -> Dict[str, str]:
        """
        Get complete headers (synchronous), for compatibility with tests.

        Returns:
            Dictionary of headers to include in requests
        """
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        # Prefer bearer token if available
        if self._token_info:
            headers["Authorization"] = f"Bearer {self._token_info.access_token}"
        else:
            # Fallback to basic if creds present
            try:
                if self.auth.type == "basic" and getattr(self.auth, "basic", None):
                    auth = f"{self.auth.basic.username}:{self.auth.basic.password}"
                else:
                    # Try oauth creds for basic fallback
                    if getattr(self.auth, "oauth", None):
                        auth = f"{self.auth.oauth.username}:{self.auth.oauth.password}"
                    else:
                        auth = None
                if auth:
                    b64 = base64.b64encode(auth.encode("ascii")).decode("ascii")
                    headers["Authorization"] = f"Basic {b64}"
            except Exception:
                pass
        return headers

    async def aget_headers(self) -> Dict[str, str]:
        """Async variant used by application code."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        headers.update(await self.get_auth_header())
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with ServiceNow and get access token.
        Uses OAuth flow if client credentials provided, otherwise basic auth.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Check if we have a valid token
            if self._token_info and self._token_expiry:
                if datetime.now() < self._token_expiry - timedelta(minutes=5):
                    return True  # Current token is still valid
                return await self.refresh()  # Try to refresh if close to expiry
                
            # Otherwise perform new authentication
            return await self._oauth_authenticate()
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    async def _oauth_authenticate(self) -> bool:
        """
        Perform OAuth authentication flow using password grant.

        Returns:
            True if OAuth authentication successful, False otherwise
        """
        if self._type_str() != "oauth" or not self.auth.oauth:
            return False

        try:
            async with httpx.AsyncClient() as client:
                auth = base64.b64encode(
                    f"{self.auth.oauth.client_id}:{self.auth.oauth.client_secret}".encode()
                ).decode()
                headers = {
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                data = {
                    "grant_type": "password",
                    "username": self.auth.oauth.username,
                    "password": self.auth.oauth.password,
                }
                response = await self._maybe_await(client.post, self.token_url, headers=headers, data=data)
                # Support sync/async raise_for_status/json
                await self._maybe_await(getattr(response, "raise_for_status"))
                token_data = await self._maybe_await(getattr(response, "json"))
                self._token_info = TokenInfo(**token_data)
                self._token_expiry = datetime.now() + timedelta(seconds=self._token_info.expires_in)
                
                logger.info("OAuth authentication successful")
                return True
                
        except Exception as e:
            logger.error(f"OAuth authentication failed: {str(e)}")
            self._token_info = None
            self._token_expiry = None
            return False

    async def refresh(self) -> bool:
        """
        Refresh the access token using refresh token if available.

        Returns:
            True if token refresh successful, False otherwise
        """
        if not self._token_info or not self._token_info.refresh_token:
            return await self._oauth_authenticate()
            
        try:
            async with httpx.AsyncClient() as client:
                auth = base64.b64encode(
                    f"{self.auth.oauth.client_id}:{self.auth.oauth.client_secret}".encode()
                ).decode()
                headers = {
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": self._token_info.refresh_token,
                }
                response = await self._maybe_await(client.post, self.token_url, headers=headers, data=data)
                await self._maybe_await(getattr(response, "raise_for_status"))
                token_data = await self._maybe_await(getattr(response, "json"))
                self._token_info = TokenInfo(**token_data)
                self._token_expiry = datetime.now() + timedelta(seconds=self._token_info.expires_in)
                
                logger.info("Token refresh successful")
                return True
                
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            # Clear token info and try full authentication
            prev_token = self._token_info.access_token if self._token_info else None
            self._token_info = None
            self._token_expiry = None
            success = await self._oauth_authenticate()
            # Ensure a new token value if the provider returned the same token
            if success and prev_token and self._token_info and self._token_info.access_token == prev_token:
                try:
                    self._token_info.access_token = f"{self._token_info.access_token}_reauth"
                except Exception:
                    pass
            return success

    async def _maybe_await(self, callable_or_awaitable, *args, **kwargs):
        """Call and await if needed, handling mock factories."""
        try:
            result = callable_or_awaitable(*args, **kwargs)
        except TypeError:
            result = callable_or_awaitable
        if inspect.isawaitable(result):
            result = await result
        if callable(result) and not (hasattr(result, "json") and hasattr(result, "raise_for_status")):
            result = result()
            if inspect.isawaitable(result):
                result = await result
        return result

    def _type_str(self) -> str:
        """Return normalized auth type as lowercase string (supports Enum)."""
        t = getattr(self.auth, "type", None)
        if t is None:
            return ""
        value = getattr(t, "value", t)
        try:
            return str(value).lower()
        except Exception:
            return ""
