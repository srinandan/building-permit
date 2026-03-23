# Assessor MCP Server

The **Assessor MCP Server** provides a simulated API for the San Paloma County Assessor's office. It is implemented using the **Model Context Protocol (MCP)**, allowing AI models to interact with real-world property data as a set of structured tools.

## Features
- **Parcel Lookup:** Retrieve detailed information about a property based on its Assessor's Parcel Number (APN).
- **Zoning Classification:** Determine the zoning code for a given property address.
- **Setback & Compliance Specs:** Fetch precise requirements (setbacks, height limits, lot coverage) for specific zoning codes.
- **SSE Communication:** Exposes an MCP server over Server-Sent Events (SSE) for easy integration with web-based AI agents.

## Tools Provided
- `lookup_parcel`: Returns APN-based property details.
- `get_zoning_classification`: Returns zoning codes for addresses.
- `get_setback_requirements`: Returns technical compliance data for zoning codes.

## Integration

The **Compliance Agent** uses these tools to contextually analyze building plans. It connects to the Assessor MCP server's SSE endpoint (`http://localhost:8002/sse`) to retrieve the local constraints for the property being analyzed.

## Tech Stack
- **Framework:** FastAPI + `mcp.server.fastmcp`
- **Dependency Management:** `uv`
- **Protocol:** MCP (via SSE)

## Local Development

### Prerequisites
- Python 3.12+
- `uv` installed.

### Setup and Execution
1.  **Install dependencies:**
    ```bash
    make install
    ```
2.  **Start the MCP server:**
    ```bash
    make start
    ```
    The server will be available at `http://localhost:8002`.

## Deployment

The Assessor MCP Server is containerized and ready for deployment to **Google Cloud Run** using Cloud Build.

```bash
gcloud builds submit --config .cloudbuild/deploy.yaml .
```
