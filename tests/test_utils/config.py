"""Test configuration fixtures."""
import pytest
import os
import sys

# Add src directory to Python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.append(src_dir)

from config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig

@pytest.fixture
def mock_auth_config():
    """Create a mock authentication configuration."""
    return AuthConfig(
        type=AuthType.BASIC,
        basic=BasicAuthConfig(
            username="test_user",
            password="test_pass"
        )
    )

@pytest.fixture
def mock_server_config():
    """Create a mock server configuration."""
    return ServerConfig(
        instance_url="https://dev.service-now.com",
        auth=AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(
                username="test_user",
                password="test_pass"
            )
        ),
        debug=True,
        timeout=5
    )