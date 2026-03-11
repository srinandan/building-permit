# Building Plan Compliance Checker

An Agentic application to review building plans against the California Building Standards Code and Santa Clara County reach codes.

## Architecture

This is a monorepo containing three microservices:
1. **Frontend**: React application built with Vite and Tailwind CSS.
2. **API Gateway**: Go backend using the Gin framework to handle file uploads and orchestrate the AI analysis.
3. **AI Agent**: Python service using FastAPI, Google Cloud Document AI, Vertex AI RAG Engine, and Gemini.

## Prerequisites

- Node.js & npm (for the frontend)
- Go (for the API gateway)
- Python 3.12+ & `uv` (for the AI Agent)
- Google Cloud Project with Billing enabled
- Google Cloud Service Account with permissions for Vertex AI and Document AI

## Google Cloud Setup

1. Enable the following APIs in your GCP Project:
   - Vertex AI API
   - Cloud Document AI API

2. Create a Document AI Processor:
   - Go to Document AI -> Processors -> Create Processor -> Document OCR.
   - Note the Processor ID.

3. Set up Vertex AI RAG Engine:
   - Upload your PDFs containing the Santa Clara building codes and California Building Standards to a GCS bucket.
   - Use the Vertex AI RAG Engine to create a corpus from those documents.
   - Note the Corpus ID/Name.

## Local Development

### 1. Setup the Python AI Agent

```bash
cd agent
uv sync
```

Copy the example environment file and fill in your GCP details:
```bash
cp .env.example .env
# Edit .env and point GOOGLE_APPLICATION_CREDENTIALS to your service account JSON file.
```

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

This project is licensed under the terms of the [LICENSE.txt](./LICENSE.txt) file.
