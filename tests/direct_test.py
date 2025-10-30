"""
Direct test of auth manager functionality.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from auth.auth_manager import AuthManager, AuthConfig, TokenInfo

async def test_auth_flow():
    """Test the basic authentication flow"""
    # Create config
    config = AuthConfig(
        instance_url="test.service-now.com",
        username="test_user",
        password="test_pass",
        client_id="test_client",
        client_secret="test_secret"
    )
    
    # Create auth manager
    auth_manager = AuthManager(config)
    
    # Get headers (should use basic auth initially)
    headers = auth_manager.get_headers()
    print("Initial headers:", headers)
    assert "Basic" in headers["Authorization"]
    
    print("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())