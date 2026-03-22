# Assessor MCP Server Skill

## Overview
This skill implements a fake Santa Clara County Assessor API exposed as an MCP (Model Context Protocol) Server. It runs as a standalone Python microservice and communicates with the AI agent using Server-Sent Events (SSE).

## Tools Provided
- `lookup_parcel(apn: str) -> dict`: Looks up property details by Assessor's Parcel Number (APN).
- `get_zoning_classification(address: str) -> str`: Retrieves the zoning classification code for a given address.
- `get_setback_requirements(zoning_code: str) -> dict`: Returns setback requirements, lot coverage limits, and height limits for a given zoning code.

## Integration
The AI Agent (`plan_analyzer` in `agent/services.py`) includes these tools in its context by instantiating an `McpToolset` connected to this server's SSE endpoint (`http://0.0.0.0:8002/sse`).

## Execution
```bash
cd assessor-mcp-server
uv sync
make start
```
