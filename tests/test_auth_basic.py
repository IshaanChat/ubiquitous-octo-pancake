"""
Basic test for auth manager functionality.
"""
import pytest
from datetime import datetime, timedelta
import httpx
from unittest.mock import patch, Mock

# Test directly with the classes to avoid import issues
from dataclasses import dataclass

@dataclass
class OAuthConfig:
    client_id: str
    client_secret: str
    username: str
    password: str
    token_url: str = None

@dataclass
class AuthConfig:
    type: str = "oauth"
    instance_url: str = None
    oauth: OAuthConfig = None
    
    @classmethod
    def create_oauth_config(cls, instance_url, username, password, client_id, client_secret):
        oauth = OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password
        )
        return cls(type="oauth", instance_url=instance_url, oauth=oauth)

@pytest.mark.asyncio
async def test_basic_auth_flow():
    """Test basic auth flow with mocked responses"""
    # Mock response data
    mock_token_data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    
    # Create mock response
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = mock_token_data
    
    # Create mock client
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    
    # Patch httpx.AsyncClient
    with patch('httpx.AsyncClient') as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        
        # Create auth config
        config = AuthConfig.create_oauth_config(
            instance_url="test.service-now.com",
            username="test_user",
            password="test_pass",
            client_id="test_client",
            client_secret="test_secret"
        )
        
        # Import here to use the patched client
        from auth.auth_manager import AuthManager
        auth_manager = AuthManager(config)
        
        # Test authentication
        success = await auth_manager.authenticate()
        assert success is True
        
        # Verify headers
        headers = auth_manager.get_headers()
        assert headers["Authorization"].startswith("Bearer ")
        assert "test_access_token" in headers["Authorization"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])