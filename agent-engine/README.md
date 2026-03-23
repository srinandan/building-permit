# Agent Engine Deployment Tool

This directory contains utilities and configuration for deploying AI agents to the **Vertex AI Agent Engine**. It is a specialized toolset for packaging Python-based agents (like those using Google ADK) into scalable, managed environments on Google Cloud.

## Features
- **Managed Deployment:** Automates the creation and updating of Agent Engines on Vertex AI.
- **Agent Identity:** Supports per-agent IAM access control via Agent Identity (Preview).
- **Environment & Secrets:** Handles injection of environment variables and Secret Manager secrets into the agent's runtime.
- **Resource Management:** Configures CPU, memory, and instance scaling (min/max instances).
- **Telemetry Integration:** Automatically enables OpenTelemetry for distributed tracing and monitoring.

## Tech Stack
- **Language:** Python
- **SDK:** `vertexai` (Google Cloud Vertex AI SDK)
- **Framework:** Google ADK (Agent Development Kit) compatible.

## Usage

This tool is primarily invoked via the `Makefile` or directly as a Python module to deploy an agent.

### Prerequisites
- Python 3.10+
- `uv` installed.
- Google Cloud project with Vertex AI API enabled.

### Deployment
To deploy the default agent engine application:
```bash
make deploy
```

This runs the `app.app_utils.deploy` module, which performs the following:
1.  Imports the agent entrypoint.
2.  Generates the class method specifications for the agent's operations.
3.  Uploads source packages and requirements.
4.  Configures the Vertex AI Agent Engine resource.
5.  Wait for the deployment to complete and provides a URL to the Vertex AI Console Playground.

## Configuration
The deployment can be customized using command-line flags or environment variables (see `app/app_utils/deploy.py` for all available options). Common configurations include:
- `--project`: GCP Project ID.
- `--location`: GCP Region (e.g., `us-central1`).
- `--display-name`: The name shown in the Vertex AI console.
- `--min-instances` / `--max-instances`: Auto-scaling bounds.
