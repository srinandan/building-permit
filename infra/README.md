# Infrastructure Setup

The `infra` directory contains automation scripts and Makefiles to bootstrap the Google Cloud environment for the **Building Permit Compliance Portal**. This includes enabling necessary APIs, setting up Identity and Access Management (IAM), and initializing AI-specific services like the Vertex AI RAG Engine.

## Features
- **API Enablement:** Automatically enables Vertex AI, Document AI, Cloud Trace, and other required Google Cloud services.
- **Service Account Management:** Creates the necessary service accounts and assigns granular IAM roles for least-privilege security.
- **RAG Engine Bootstrap:** Sets up the Vertex AI Search (RAG) corpus and uploads the San Paloma County building codes (PDFs) from the `building-codes/` directory.
- **Agent Engine Deployment:** Orchestrates the deployment of the reasoning engine via the `agent-engine` component.

## Usage

All infrastructure tasks are managed through the provided `Makefile`.

### Prerequisites
- `gcloud` CLI installed and authenticated.
- A Google Cloud project selected (`gcloud config set project [PROJECT_ID]`).
- Python 3.10+ (required for the RAG setup script).

### Automated Setup
To perform a complete setup of all infrastructure and services:
```bash
make setup
```

### Individual Tasks
If you need to run specific parts of the infrastructure setup:

- **Enable GCP APIs:**
  ```bash
  make apis
  ```
- **Create Service Account & IAM Roles:**
  ```bash
  make sa
  ```
- **Initialize RAG Engine Corpus:**
  ```bash
  make rag
  ```
- **Deploy Vertex AI Agent Engine:**
  ```bash
  make agent-engine
  ```

## Key Scripts
- `setup.sh`: A bash script for service enablement and IAM configuration.
- `rag_setup.py`: A Python script using the Vertex AI SDK to manage RAG corpora and documents.
