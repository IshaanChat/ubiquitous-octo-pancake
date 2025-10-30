# Supported operations in the MCP server
SUPPORTED_OPERATIONS = {
    "servicenow.incident": [
        "get",
        "create", 
        "update",
        "list"
    ],
    "servicenow.catalog": [
        "get_item",
        "list_items",
        "create_item",
        "update_item"
    ],
    "servicenow.change": [
        "get_request",
        "create_request",
        "update_request",
        "list_requests"
    ]
}

# Operation descriptions for documentation
OPERATION_DESCRIPTIONS = {
    "servicenow.incident.get": "Get incident details by sys_id or number",
    "servicenow.incident.create": "Create a new incident",
    "servicenow.incident.update": "Update an existing incident",
    "servicenow.incident.list": "List incidents matching query parameters",
    "servicenow.catalog.get_item": "Get service catalog item details",
    "servicenow.catalog.list_items": "List service catalog items",
    "servicenow.catalog.create_item": "Create a new service catalog item",
    "servicenow.catalog.update_item": "Update an existing service catalog item",
    "servicenow.change.get_request": "Get change request details",
    "servicenow.change.create_request": "Create a new change request",
    "servicenow.change.update_request": "Update an existing change request",
    "servicenow.change.list_requests": "List change requests matching query parameters"
}