"""Test utilities for the ServiceNow MCP server."""

from .debug_client import debug_client, _TestDebugger as TestDebugger
from .snow_client import mock_snow_client, make_mock_snow_client
from .config import mock_auth_config
from .config import mock_server_config
from .mock_data import (
    MOCK_CATALOG_ITEMS,
    MOCK_CATALOG_CATEGORIES,
    MOCK_AUTH_ERROR,
    MOCK_NOT_FOUND,
    MOCK_VALIDATION_ERROR,
    MOCK_MCP_ERROR,
    MOCK_MCP_SUCCESS,
    MOCK_SERVICENOW_RESPONSES
)
from . import mock_data_extra as _extra
from .mock_data_extra import (
    MOCK_SERVICENOW_RESPONSES,  # keep side effects/updates
)

__all__ = [
    'TestDebugger',
    'mock_snow_client',
    'make_mock_snow_client',
    'mock_server_config',
    'mock_auth_config',
    'MOCK_CATALOG_ITEMS',
    'MOCK_CATALOG_CATEGORIES',
    'MOCK_AUTH_ERROR',
    'MOCK_NOT_FOUND',
    'MOCK_VALIDATION_ERROR',
    'MOCK_MCP_ERROR',
    'MOCK_MCP_SUCCESS',
    'MOCK_SERVICENOW_RESPONSES',
    'MOCK_CHANGE_REQUEST_DATA',
    'MOCK_ARTICLE_DATA',
    'MOCK_INCIDENT_DATA',
    'MOCK_USER_DATA'
]

# Export flattened records expected by tests
MOCK_CHANGE_REQUEST_DATA = (_extra.MOCK_CHANGE_REQUEST_DATA.get('result') or [_extra.MOCK_CHANGE_REQUEST_DATA])[0]
MOCK_ARTICLE_DATA = (_extra.MOCK_ARTICLE_DATA.get('result') or [_extra.MOCK_ARTICLE_DATA])[0]
MOCK_INCIDENT_DATA = (_extra.MOCK_INCIDENT_DATA.get('result') or [_extra.MOCK_INCIDENT_DATA])[0]
MOCK_USER_DATA = (_extra.MOCK_USER_DATA.get('result') or [_extra.MOCK_USER_DATA])[0]

# Add friendly aliases for tests that expect these fields
if isinstance(MOCK_ARTICLE_DATA, dict):
    if 'title' not in MOCK_ARTICLE_DATA and 'short_description' in MOCK_ARTICLE_DATA:
        MOCK_ARTICLE_DATA['title'] = MOCK_ARTICLE_DATA['short_description']
    if 'content' not in MOCK_ARTICLE_DATA and 'text' in MOCK_ARTICLE_DATA:
        MOCK_ARTICLE_DATA['content'] = MOCK_ARTICLE_DATA['text']
