# Building Permit Compliance Portal - Project Specification

## 1. Project Overview
The **Building Permit Compliance Portal** is an end-to-end system designed for residents of Santa Clara County (SCC) to streamline the building permit submission and analysis process. The core value proposition is the use of Generative AI (Gemini, Vertex AI, and Document AI) to provide near-instant compliance checks on submitted building plan PDFs, reducing the manual burden on county reviewers and providing immediate feedback to applicants.

### Goals:
- Provide a user-friendly dashboard for residents to manage properties and permit applications.
- Automate the preliminary review of building plans for compliance with local regulations.
- Maintain a historical record of submissions and analysis reports for each permit application.
- Scalable architecture using a Go-based API gateway and A2A-compliant AI agents (Compliance & Contractor agents).
- Interoperability between agents using the Agent-to-Agent (A2A) protocol.

---

## 2. System Architecture

The project consists of several primary components communicating over standard HTTP and A2A protocols:

### A. Frontend (React)
- **Framework:** Vite + React + TypeScript.
- **Styling:** TailwindCSS with Lucide-React icons.
- **State Management:** Zustand.
- **API Communication:** Axios.
- **Key Features:**
    - User Login (email-based).
    - Property management (auto-creates a default property for demo).
    - Permit application tracking.
    - PDF submission and real-time analysis results visualization.
    - Interactive chat modal for follow-up questions on specific violations.

### B. API Gateway (Go Backend)
- **Framework:** Gin Gonic.
- **ORM:** GORM with SQLite (`building_plans.db`).
- **Observability:** OpenTelemetry (Google Cloud Trace).
- **Responsibilities:**
    - User authentication and property/permit management.
    - File upload handling and proxying to the Compliance Agent.
    - Persisting analysis results in the database.
    - Proxying chat requests to the Compliance Agent.
    - CORS management for frontend requests.

### C. Compliance Agent (Python AI Service)
- **Framework:** FastAPI.
- **AI Stack:** 
    - **Vertex AI (Gemini 1.5 Pro/Flash):** For visual and text analysis of building plans.
    - **Document AI:** For high-fidelity text extraction from PDFs.
    - **Vertex AI Search (RAG):** (Planned/Integrated) For querying against local building codes.
- **Observability:** OpenTelemetry (Google Cloud Trace).
- **Responsibilities:**
    - Processing PDF files.
    - Extracting and analyzing building plan details.
    - Handling interactive follow-up questions about violations using conversational AI.
    - Returning structured JSON compliance reports.

### D. Contractor Agent (A2A AI Service)
- **Framework:** FastAPI + `a2a-sdk`.
- **AI Stack:** 
    - **Vertex AI (Gemini 2.5 Flash):** For reasoning and tool use.
    - **Google Search:** Tool for finding real-world contractor data.
- **Observability:** OpenTelemetry.
- **Responsibilities:**
    - Finding licensed contractors based on specific job needs and location.
    - Providing contact information and fit analysis.
    - Exposing an A2A-compliant interface for interoperability with other agents.

---

## 3. Data Model (Database Schema)

The system uses SQLite for simplicity in the current implementation.

### User
| Field | Type | Description |
|---|---|---|
| `id` | uint (PK) | Unique identifier |
| `email` | string (Unique) | User's email |
| `name` | string | User's display name |
| `created_at` | time | Timestamp of creation |
| `updated_at` | time | Timestamp of last update |

### Property
| Field | Type | Description |
|---|---|---|
| `id` | uint (PK) | Unique identifier |
| `user_id` | uint (FK) | Reference to User |
| `address` | string | Street address |
| `city` | string | City |
| `zip_code` | string | Zip code |
| `created_at` | time | Timestamp of creation |

### Permit
| Field | Type | Description |
|---|---|---|
| `id` | uint (PK) | Unique identifier |
| `property_id` | uint (FK) | Reference to Property |
| `title` | string | Permit application title |
| `description` | string | Brief description |
| `status` | string | Current status (Draft, Submitted, Approved, etc.) |
| `created_at` | time | Timestamp of creation |

### PermitSubmission
| Field | Type | Description |
|---|---|---|
| `id` | uint (PK) | Unique identifier |
| `permit_id` | uint (FK) | Reference to Permit |
| `file_name` | string | Name of the uploaded PDF |
| `analysis_status`| string | Result status from AI (e.g., "Approved", "Changes Suggested") |
| `report_json` | text (JSON) | Detailed structured report from the AI agent |
| `created_at` | time | Timestamp of submission |

---

## 4. API Specification

### 4.1. Gateway API (Go - Port 8080)

| Endpoint | Method | Description | Payload (JSON/Form) |
|---|---|---|---|
| `/api/login` | POST | Login or register a user | `{ "email": "user@example.com" }` |
| `/api/users/:id/properties` | GET | List properties for a user | N/A |
| `/api/users/:id/properties` | POST | Add a new property | `{ "address": "...", "city": "...", "zip_code": "..." }` |
| `/api/properties/:id/permits` | GET | List permits for a property | N/A |
| `/api/properties/:id/permits` | POST | Create a permit application | `{ "title": "...", "description": "..." }` |
| `/api/permits/:id` | GET | Get permit details + history | N/A |
| `/api/permits/:id` | DELETE| Delete a permit application | N/A |
| `/api/analyze-plan` | POST | Upload PDF for AI analysis | `file: (Binary)`, `permit_id: (string)` |
| `/api/chat` | POST | Proxy chat message to AI agent | `{ "messages": [...], "permit_id": "...", "violation": {...} }` |
| `/health` | GET | Health check | N/A |

### 4.2. Compliance Agent (Python - Port 8000)

| Endpoint | Method | Description | Payload |
|---|---|---|---|
| `/analyze` | POST | Core AI analysis engine | `file: (Binary PDF)` |
| `/chat` | POST | Conversational AI follow-up | `{ "messages": [...], "permit_id": "...", "violation": {...} }` |
| `/health` | GET | Health check | N/A |

### 4.3. Contractor Agent (Python - Port 8081)

| Endpoint | Method | Description | Payload |
|---|---|---|---|
| `/a2a/contractor_agent/.well-known/agent-card.json` | GET | A2A Agent Card | N/A |
| `/a2a/contractor_agent` | POST | A2A JSON-RPC Interface | JSON-RPC Payload |
| `/health` | GET | Health check | N/A |

**AI Response Format:**
```json
{
  "status": "Approved" | "Changes Suggested" | "Rejected",
  "violations": [
    {
      "section": "Building Code Section",
      "description": "Description of violation",
      "suggestion": "How to fix it"
    }
  ],
  "approved_elements": ["Element 1", "Element 2"]
}
```

---

## 5. Deployment & Execution

### Prerequisites
- Go 1.21+
- Python 3.10+ (with `uv` or `pip`)
- Node.js 18+ (with `npm`)
- Google Cloud Project with:
    - Vertex AI API enabled.
    - Document AI API enabled.
    - Cloud Trace API enabled.

### Local Development
1. **Agent:** `cd agent && make run` (starts on port 8000)
2. **API:** `cd api && make run` (starts on port 8080)
3. **Frontend:** `cd frontend && make run` (starts on port 5173)

### Containerization
Dockerfiles are provided for each service:
- `agent/Dockerfile`
- `api/Dockerfile`
- `frontend/Dockerfile`

A `Makefile` in each directory handles build and run commands.

### E. Assessor MCP Server (Python Service)
- **Framework:** FastAPI + `mcp.server.fastmcp`.
- **Responsibilities:**
    - Exposing a Model Context Protocol (MCP) server over SSE.
    - Providing fake Santa Clara County data to the AI agents for context via tools.
    - Implementing `lookup_parcel`, `get_zoning_classification`, and `get_setback_requirements` tools.
