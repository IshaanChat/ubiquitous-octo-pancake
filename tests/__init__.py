"""
Test utilities initialization module.
This module provides common test fixtures and utilities used across test cases.
"""
import pytest
from fastapi.testclient import TestClient
from tests.test_utils.debug_client import _TestDebugger as TestDebugger

# Re-export commonly used test utilities
__all__ = ['TestDebugger', 'TestClient']

# Global test configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers",
        "api: mark test as an API test"
    )

# Common test fixtures
@pytest.fixture(scope="session")
def test_env():
    """Provide test environment configuration."""
    return {
        "debug": True,
        "test_mode": True
    }

@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """Set up logging for all tests."""
    import logging
    caplog.set_level(logging.INFO)
