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

## Write Tools
- `add_parcel(apn: str, address: str, lot_size_sqft: int, owner: str, assessed_value: int) -> dict`: Add a new property to the assessor's database.
- `rezone_address(address: str, new_zoning_code: str) -> dict`: Update the zoning classification code for a specific address.
- `add_zoning_rule(zoning_code: str, description: str, max_height_ft: int, max_lot_coverage_percent: int, front_setback_ft: int, rear_setback_ft: int, side_setback_ft: int) -> dict`: Add or update the setback requirements and lot coverage limits for a zoning code.
