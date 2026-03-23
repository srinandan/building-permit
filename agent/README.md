# Compliance Agent

The **Compliance Agent** is a Python-based AI microservice designed to automate the review of building plans (PDFs) against complex regulatory frameworks. It serves as the core analysis engine for the Building Permit Compliance Portal.

## Features
- **Multimodal Analysis:** Uses **Gemini 1.5 Pro/Flash** to interpret architectural drawings and text.
- **High-Fidelity OCR:** Leverages **Google Cloud Document AI** for precise text extraction and layout analysis.
- **Regulatory Retrieval (RAG):** Integrates with **Vertex AI Search (RAG Engine)** to query against California Building Standards (Title 24) and local San Paloma County codes.
- **Structured Reporting:** Generates detailed compliance reports in JSON format, mapping violations to specific code sections.
- **Conversational AI:** Supports interactive follow-up questions about violations using a conversational interface.
- **Observability:** Built-in distributed tracing with **OpenTelemetry** and Google Cloud Trace.

## Tech Stack
- **Framework:** FastAPI
- **AI Stack:** Vertex AI (Gemini), Document AI, Vertex AI Search (RAG)
- **Dependency Management:** `uv`
- **Observability:** OpenTelemetry

## Local Development

### Prerequisites
- Python 3.10+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Google Cloud credentials configured (`gcloud auth application-default login`)

### Setup and Execution
1.  **Install dependencies:**
    ```bash
    make install
    ```
2.  **Start the server:**
    ```bash
    make start
    ```
    The agent will be available at `http://localhost:8000`.

## Deployment

The service is containerized and ready for deployment to **Google Cloud Run** using Cloud Build.

```bash
make deploy
```

This command uses the `.cloudbuild/deploy.yaml` configuration to build a Docker image and deploy it to your configured Google Cloud project.
