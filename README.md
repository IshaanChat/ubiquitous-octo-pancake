# ServiceNow MCP Server

A Model Context Protocol (MCP) server implementation for ServiceNow integration, enabling AI-powered automation and interactions with ServiceNow instances.

## Features

- Basic MCP protocol implementation
- ServiceNow REST API integration
- Support for common ServiceNow operations
- Configurable authentication and endpoints

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
# Create a .env file with:
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

3. Run the server:
```bash
python src/main.py
```

## Replicating On Another Device

- Commit and push (do not commit `.env` or virtual envs):
  1. Initialize git and set remote
     ```bash
     git init
     git add .
     git commit -m "Initial commit"
     git branch -M main
     git remote add origin <your-remote-url>
     git push -u origin main
     ```
  2. On the new device:
     ```bash
     git clone <your-remote-url> mcp
     cd mcp
     # Windows PowerShell quick start
     scripts/setup.ps1
     ```
     The script creates a virtual environment, installs dependencies, and copies `.env.example` to `.env` if missing.

### Notes
- Secrets: keep `.env` out of git. Update `.env.example` when new keys are required.
- Environments: `.venv/` and `venv/` are ignored by `.gitignore` and should not be committed.
- Dependencies: this repo includes a `requirements.txt`. If you change packages, update and commit it.

## Usage

The server implements the MCP protocol for ServiceNow operations. Example requests:

```python
# Example MCP request
{
    "version": "0.1",
    "type": "request",
    "id": "unique-request-id",
    "tool": "servicenow",
    "parameters": {
        "operation": "get_incident",
        "incident_number": "INC0010001"
    }
}
```

## Project Structure

```
.
├── src/
│   ├── main.py              # Server entry point
│   ├── config.py            # Configuration management
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── protocol.py      # MCP protocol implementation
│   │   └── handlers.py      # Request handlers
│   └── servicenow/
│       ├── __init__.py
│       ├── client.py        # ServiceNow API client
│       └── operations.py    # ServiceNow operations
├── tests/
│   └── test_mcp.py         # Tests for MCP implementation
├── requirements.txt
└── README.md
```

## Development

1. Install development dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
python -m pytest tests/
```

## License

MIT
