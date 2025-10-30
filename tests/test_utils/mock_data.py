"""
Mock data and responses for tests.
"""
from typing import Dict, Any

# Mock ServiceNow data
MOCK_CATALOG_ITEMS = {
    "result": [
        {
            "sys_id": "item001",
            "name": "Test Item 1",
            "description": "A test catalog item",
            "category": "hardware",
            "price": 100.00,
            "active": True
        },
        {
            "sys_id": "item002",
            "name": "Test Item 2",
            "description": "Another test catalog item",
            "category": "software",
            "price": 50.00,
            "active": True
        }
    ]
}

MOCK_CATALOG_CATEGORIES = {
    "result": [
        {
            "sys_id": "cat001",
            "name": "Hardware",
            "description": "Hardware items",
            "active": True
        },
        {
            "sys_id": "cat002",
            "name": "Software",
            "description": "Software items",
            "active": True
        }
    ]
}

MOCK_SERVICENOW_RESPONSES: Dict[str, Dict[str, Any]] = {
    "GET/api/now/table/sc_cat_item": MOCK_CATALOG_ITEMS,
    "GET/api/now/table/sc_cat_item/item001": {"result": MOCK_CATALOG_ITEMS["result"][0]},
    "GET/api/now/table/sc_category": MOCK_CATALOG_CATEGORIES,
    "GET/api/now/table/sc_category/cat001": {"result": MOCK_CATALOG_CATEGORIES["result"][0]}
}

# Mock error responses
MOCK_AUTH_ERROR = {
    "error": {
        "message": "User Not Authenticated",
        "detail": {
            "type": "authentication_error",
            "status": 401
        }
    }
}

MOCK_NOT_FOUND = {
    "error": {
        "message": "Record not found",
        "detail": {
            "type": "not_found",
            "status": 404
        }
    }
}

MOCK_VALIDATION_ERROR = {
    "error": {
        "message": "Invalid input",
        "detail": {
            "type": "validation_error",
            "status": 400,
            "fields": ["name", "category"]
        }
    }
}

# Mock MCP responses
MOCK_MCP_ERROR = {
    "version": "1.0",
    "type": "error",
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters",
        "details": {
            "fields": ["tool", "parameters"]
        }
    }
}

MOCK_MCP_SUCCESS = {
    "version": "1.0",
    "type": "response",
    "result": {
        "status": "success",
        "data": {}  # To be filled with actual data
    }
}