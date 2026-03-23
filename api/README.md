# API Gateway

The **API Gateway** is a Go-based backend service that coordinates the flow of information between the frontend and the AI-driven compliance agents. It serves as the single point of entry for the Building Permit Compliance Portal.

## Features
- **User Management:** Handles email-based login and registration.
- **Property & Permit Lifecycle:** Manage properties and track building permit applications.
- **File Upload & Proxy:** Handles PDF uploads, persists them, and proxies analysis requests to the Compliance Agent.
- **Chat Proxy:** Routes interactive chat queries between the frontend and the AI agents.
- **Database:** Uses **GORM** with **SQLite** for metadata and history persistence.
- **Observability:** Distributed tracing with **OpenTelemetry** and Google Cloud Trace.

## Tech Stack
- **Language:** Go 1.21+
- **Framework:** Gin Gonic
- **ORM:** GORM (SQLite)
- **Observability:** OpenTelemetry

## Local Development

### Prerequisites
- Go 1.21+ installed.
- Access to the Compliance Agent (running on `localhost:8000` by default).

### Setup and Execution
1.  **Install dependencies:**
    ```bash
    make install
    ```
2.  **Start the API server:**
    ```bash
    make start
    ```
    The gateway will be available at `http://localhost:8080`.

## Deployment

The API Gateway is containerized and ready for deployment to **Google Cloud Run** via Cloud Build.

```bash
make deploy
```

This command builds the Docker image and deploys it according to the `.cloudbuild/deploy.yaml` configuration.
