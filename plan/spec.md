# Building Permit Compliance Portal - Project Specification

## 1. Project Overview
The **Building Permit Compliance Portal** is an end-to-end system designed for residents of Santa Clara County (SCC) to streamline the building permit submission and analysis process. The core value proposition is the use of Generative AI (Gemini, Vertex AI, and Document AI) to provide near-instant compliance checks on submitted building plan PDFs, reducing the manual burden on county reviewers and providing immediate feedback to applicants.

### Goals:
- Provide a user-friendly dashboard for residents to manage properties and permit applications.
- Automate the preliminary review of building plans for compliance with local regulations.
- Maintain a historical record of submissions and analysis reports for each permit application.
- Scalable architecture using a Go-based API gateway and a Python-based AI agent.

---

## 2. System Architecture

The project consists of three primary components:

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

### B. API Gateway (Go Backend)
- **Framework:** Gin Gonic.
- **ORM:** GORM with SQLite (`building_plans.db`).
- **Observability:** OpenTelemetry (Google Cloud Trace).
- **Responsibilities:**
    - User authentication and property/permit management.
    - File upload handling and proxying to the Compliance Agent.
    - Persisting analysis results in the database.
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
    - Returning structured JSON compliance reports.

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
| `/health` | GET | Health check | N/A |

### 4.2. Compliance Agent (Python - Port 8000)

| Endpoint | Method | Description | Payload |
|---|---|---|---|
| `/analyze` | POST | Core AI analysis engine | `file: (Binary PDF)` |
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
