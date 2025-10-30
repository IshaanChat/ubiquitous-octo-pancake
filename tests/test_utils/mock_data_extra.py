"""
Mock data for ServiceNow change coordinator tests.
"""
from .mock_data import MOCK_SERVICENOW_RESPONSES

MOCK_CHANGE_REQUEST_DATA = {
    "result": [
        {
            "sys_id": "chg001",
            "number": "CHG0010001",
            "short_description": "Test change request",
            "description": "A test change request",
            "state": "draft",
            "risk": "low",
            "type": "normal",
            "assigned_to": "user001",
            "approval": "not requested"
        }
    ]
}

MOCK_ARTICLE_DATA = {
    "result": [
        {
            "sys_id": "kb001",
            "number": "KB0010001",
            "short_description": "Test knowledge article",
            "text": "A test knowledge article",
            "workflow_state": "draft",
            "author": "user001",
            "category": "how-to"
        }
    ]
}

MOCK_INCIDENT_DATA = {
    "result": [
        {
            "sys_id": "inc001",
            "number": "INC0010001",
            "short_description": "Test incident",
            "description": "A test incident",
            "state": "new",
            "impact": "low",
            "urgency": "low",
            "priority": "3",
            "assigned_to": "user001"
        }
    ]
}

MOCK_USER_DATA = {
    "result": [
        {
            "sys_id": "user001",
            "user_name": "test.user",
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
            "active": True,
            "roles": ["admin", "user"]
        }
    ]
}

# Update mock ServiceNow responses
MOCK_SERVICENOW_RESPONSES.update({
    "GET/api/now/table/change_request": MOCK_CHANGE_REQUEST_DATA,
    "GET/api/now/table/kb_knowledge": MOCK_ARTICLE_DATA,
    "GET/api/now/table/incident": MOCK_INCIDENT_DATA,
    "GET/api/now/table/sys_user": MOCK_USER_DATA,
    "GET/api/now/table/change_request/chg001": {"result": MOCK_CHANGE_REQUEST_DATA["result"][0]},
    "GET/api/now/table/kb_knowledge/kb001": {"result": MOCK_ARTICLE_DATA["result"][0]},
    "GET/api/now/table/incident/inc001": {"result": MOCK_INCIDENT_DATA["result"][0]},
    "GET/api/now/table/sys_user/user001": {"result": MOCK_USER_DATA["result"][0]},
})