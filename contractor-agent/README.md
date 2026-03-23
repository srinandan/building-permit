# Contractor Agent

The **Contractor Agent** is an AI agent that simulates a building contractor. It interacts with the **Compliance Agent** and end-users to discuss building plans, clarify violations, and propose structural remediation based on regulatory feedback.

## Features
- **A2A Integration:** Complies with the **Agent-to-Agent (A2A)** protocol for seamless communication with other AI agents.
- **Contractor Discovery:** Capable of finding licensed contractors based on specific job needs and locations.
- **Remediation Planning:** Proposes specific structural fixes to resolve non-compliance issues found by the Compliance Agent.
- **Tool Use:** Uses **Google Search** to find real-world contractor data and license information.

## Tech Stack
- **Framework:** FastAPI + `a2a-sdk`
- **AI Stack:** Vertex AI (Gemini 2.5 Flash)
- **Dependency Management:** `uv`

## Local Development

### Prerequisites
- Python 3.12+
- `uv` installed.

### Setup and Execution
1.  **Install dependencies:**
    ```bash
    make install
    ```
2.  **Start the agent:**
    ```bash
    make start
    ```
    The agent will be available at `http://localhost:8001`.

## Integration
The agent exposes an A2A-compliant interface via its `.well-known/agent-card.json` endpoint. It is designed to be discovered and called by the API Gateway or other compliant agents in the San Paloma County ecosystem.
