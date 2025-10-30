"""
Tests for the authentication manager.
"""
import pytest
from datetime import datetime, timedelta
import httpx
from unittest.mock import patch, Mock

from auth.auth_manager import AuthManager, AuthConfig, TokenInfo

# Mock successful token response
MOCK_TOKEN_RESPONSE = {
    "access_token": "mock_access_token",
    "refresh_token": "mock_refresh_token",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "useraccount"
}

@pytest.fixture
def auth_config():
    """Create test auth configuration"""
    return AuthConfig(
        instance_url="test.service-now.com",
        username="test_user",
        password="test_pass",
        client_id="test_client_id",
        client_secret="test_client_secret"
    )

@pytest.fixture
def mock_httpx_client():
    """Create mock HTTP client"""
    with patch("httpx.AsyncClient") as mock_client:
        # Setup mock response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = MOCK_TOKEN_RESPONSE
        
        # Setup mock client
        client_instance = Mock()
        client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = client_instance
        
        yield mock_client

@pytest.mark.asyncio
async def test_oauth_authentication_success(auth_config, mock_httpx_client):
    """Test successful OAuth authentication"""
    auth_manager = AuthManager(auth_config)
    
    # Attempt authentication
    success = await auth_manager.authenticate()
    
    assert success is True
    assert auth_manager._token_info is not None
    assert auth_manager._token_info.access_token == "mock_access_token"
    assert auth_manager._token_info.refresh_token == "mock_refresh_token"
    
    # Verify headers
    headers = auth_manager.get_headers()
    assert headers["Authorization"] == "Bearer mock_access_token"

@pytest.mark.asyncio
async def test_token_refresh(auth_config, mock_httpx_client):
    """Test token refresh flow"""
    auth_manager = AuthManager(auth_config)
    
    # First authenticate
    await auth_manager.authenticate()
    
    # Set token to expire soon
    auth_manager._token_expiry = datetime.now() - timedelta(minutes=5)
    
    # Mock new token response
    new_token = MOCK_TOKEN_RESPONSE.copy()
    new_token["access_token"] = "new_access_token"
    mock_httpx_client.return_value.__aenter__.return_value.post.return_value.json.return_value = new_token
    
    # Attempt refresh
    success = await auth_manager.refresh()
    
    assert success is True
    assert auth_manager._token_info.access_token == "new_access_token"
    
    # Verify headers updated
    headers = auth_manager.get_headers()
    assert headers["Authorization"] == "Bearer new_access_token"

@pytest.mark.asyncio
async def test_authentication_failure(auth_config, mock_httpx_client):
    """Test authentication failure handling"""
    # Setup mock to raise an error
    mock_httpx_client.return_value.__aenter__.return_value.post.side_effect = httpx.HTTPError("Auth failed")
    
    auth_manager = AuthManager(auth_config)
    success = await auth_manager.authenticate()
    
    assert success is False
    assert auth_manager._token_info is None
    
    # Should fall back to basic auth
    headers = auth_manager.get_headers()
    assert "Basic" in headers["Authorization"]

@pytest.mark.asyncio
async def test_refresh_failure_fallback(auth_config, mock_httpx_client):
    """Test refresh failure falls back to full authentication"""
    auth_manager = AuthManager(auth_config)
    
    # First authenticate
    await auth_manager.authenticate()
    original_token = auth_manager._token_info.access_token
    
    # Make refresh fail but new auth succeed
    mock_response = mock_httpx_client.return_value.__aenter__.return_value.post
    mock_response.side_effect = [
        httpx.HTTPError("Refresh failed"),  # First call fails (refresh)
        Mock(
            raise_for_status=Mock(),
            json=Mock(return_value=MOCK_TOKEN_RESPONSE)
        )  # Second call succeeds (new auth)
    ]
    
    # Attempt refresh
    success = await auth_manager.refresh()
    
    assert success is True
    assert auth_manager._token_info is not None
    assert auth_manager._token_info.access_token != original_token
