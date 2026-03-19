# Building Plan Compliance Checker

An Agentic application to review building plans against the California Building Standards Code and Santa Clara County reach codes.

## Architecture

This is a monorepo containing microservices designed for deployment on **Google Kubernetes Engine (GKE)**:
1. **Frontend**: React application built with Vite and Tailwind CSS.
2. **API Gateway**: Go backend using the Gin framework to handle file uploads and orchestrate the AI analysis.
3. **AI Agent**: Python service using FastAPI, Google Cloud Document AI, Vertex AI RAG Engine, and Gemini. It leverages **Vertex AI Session** and **MemoryBank** for robust, persistent conversation history.
4. **Contractor Agent**: Python service for contractor-specific queries.

All services are containerized and deployed to a GKE cluster for scalability, routing, and deep integration with **Security Command Center (SCC)** for vulnerability tracing.


## Prerequisites

- Node.js & npm (for the frontend)
- Go (for the API gateway)
- Python 3.12+ & `uv` (for the AI Agent)
- Google Cloud Project with Billing enabled
- Google Cloud Service Account with permissions for Vertex AI and Document AI

## Google Cloud Setup

### 1. Automated Infrastructure Setup

We provide a set of scripts in the `infra` directory to automate the one-time setup of GCP APIs, Service Accounts, and the Vertex AI RAG Engine.

```bash
cd infra
make setup
```

This will:
- Enable necessary APIs (Vertex AI, Document AI, Telemetry, etc.).
- Create a service account `build-permit-sa` with the required IAM roles.
- Create a Vertex AI RAG Corpus named `ca-building-codes` in `us-west1` and upload documents from `building-codes/`.
- Deploys the Vertex AI Agent Engine using the logic in the `agent-engine/` directory.


### 2. Manual Setup (Document AI)

After running the automated setup, you need to manually create a Document AI Processor:
- Go to the [Document AI console](https://console.cloud.google.com/ai/document-ai/processors).
- Click **Create Processor** and select **Document OCR**.
- Note the **Processor ID** and add it to your `.env` file in the `agent` directory.

### 3. GKE Deployment

We use Kubernetes manifests located in the `k8s/` directory to deploy the application to GKE.

#### Prerequisite: GKE Cluster
Ensure you have an active GKE cluster. You will need to configure your Cloud Build triggers with your cluster name and region.

#### Deploying with Cloud Build
The application uses Cloud Build for automated CI/CD to GKE. Triggers should be configured for each service's `.cloudbuild/deploy.yaml` file:

*   **API Gateway**: `api/.cloudbuild/deploy.yaml`
*   **AI Agent**: `agent/.cloudbuild/deploy.yaml`
*   **Frontend**: `frontend/.cloudbuild/deploy.yaml`

These triggers will automatically:
1.  Build the Docker images.
2.  Push them to Artifact Registry.
3.  Apply the Kubernetes manifests using `kubectl apply`.

#### Manual Manifest Application
You can also apply the manifests manually using `kubectl` (ensure you are connected to your cluster):

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/
```

> [!IMPORTANT]
> **Workload Identity**: Ensure your GKE pods have permissions to access Vertex AI and Document AI (using Workload Identity or Service Accounts).

## Local Development

### 1. Setup the Python AI Agent

```bash
cd agent
uv sync
```

Edit the Makefile and fill in the GCP details.

Start the agent:
```bash
make start
# Runs on http://127.0.0.1:8000
```

### 2. Setup the Go API Gateway

Open a new terminal:
```bash
cd api
go mod download
make start
# Runs on http://localhost:8080
```

### 3. Setup the React Frontend

Open a new terminal:
```bash
cd frontend
npm install
make start
# Runs on http://localhost:3000
```

## Usage

1. Open `http://localhost:3000` in your browser.
2. Upload a sample PDF building plan.
3. The frontend will send the PDF to the Go API, which forwards it to the Python Agent.
4. The Python Agent will extract text using Document AI, query the RAG engine for relevant codes, and use Gemini to generate a compliance report.
5. The UI will display the results, including specific code violations and suggestions.

## Contributing

Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details on how to contribute to this project.

## Support

This demo is *NOT* endorsed by Google or Google Cloud. The repo is intended for educational/hobbyists use only.

## License

This project is licensed under the terms of the [LICENSE](./LICENSE) file.
