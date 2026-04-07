# AGENTS.md

This document describes the AI agent architecture of the **Building Permit Compliance Portal**, providing guidance for AI coding agents (e.g., Codex, Jules, Claude Code) working in this repository.

---

## Repository Layout

```
.
├── agent/                  # Compliance Agent (Python/FastAPI) — port 8000
├── contractor-agent/       # Contractor Agent (Python/FastAPI + a2a-sdk) — port 8081
├── assessor-mcp-server/    # Assessor MCP Server (Python/FastAPI + mcp) — port 8002
├── agent-engine/           # Vertex AI Agent Engine (Python/ADK) — shared services
├── api/                    # API Gateway (Go/Gin) — port 8080
├── frontend/               # React/Vite/TypeScript UI — port 5173
├── infra/                  # GCP provisioning scripts and Makefile
├── building-codes/         # Source documents for the Vertex AI RAG corpus
├── plan/
│   ├── DESIGN.md           # UI/UX design system — authoritative source for all frontend styling
│   └── spec.md             # Full project specification — authoritative source for features & architecture
└── .agents/
    └── skills/
        └── building-reviewer/SKILL.md   # Agent skill definition for this repo
```

---

## Ground Rules for All Agents

1. **Read `plan/` before making changes.** `plan/DESIGN.md` and `plan/spec.md` are the authoritative sources for UI design rules, architecture decisions, and feature goals. Do not contradict them.
2. **Read `.agents/skills/building-reviewer/SKILL.md`** for a summary of embedded agent capabilities before modifying any AI or analysis logic.
3. **Never use 1px solid borders** in the frontend. Boundaries are expressed via background color shifts only (see `plan/DESIGN.md` §2 "The No-Line Rule").
4. **Do not use raw `#000000`** for text anywhere in the UI. Use `on-surface` (`#191c1e`).
5. **Do not add standard drop shadows.** Use tonal layering or the approved ambient shadow token (`0 20px 40px rgba(25,28,30,0.06)`) only.

---

## Services & Agent Descriptions

### 1. Compliance Agent (`agent/`)

The core AI analysis service. It receives a building plan PDF, extracts text via Document AI, queries a Vertex AI RAG corpus for relevant California Title 24 / San Paloma County codes, and uses Gemini 2.5 Pro/Flash to produce a structured compliance report.

**Key responsibilities:**
- POST `/analyze` — multimodal PDF compliance analysis
- POST `/chat` — conversational follow-up on specific violations, guarded by Model Armor
- Integrates `FunctionTool` wrappers around the RAG engine to stay compatible with multimodal Gemini calls
- Emits OpenTelemetry traces to Google Cloud Trace
- Reports agent analytics to BigQuery via `google.adk.plugins.bigquery_agent_analytics_plugin`

**Model Armor guardrails:**
- Blocks prompt injection and toxicity
- Filters custom PII phrase list (e.g., `LEGAL_LIABILITY_PHRASES`) to prevent the agent from assuming legal liability or certifying engineering advice

**AI response schema** (must be maintained):
```json
{
  "status": "Approved" | "Changes Suggested" | "Rejected",
  "violations": [
    {
      "section": "string",
      "description": "string",
      "suggestion": "string"
    }
  ],
  "approved_elements": ["string"]
}
```

---

### 2. Contractor Agent (`contractor-agent/`)

An A2A-compliant agent for finding licensed contractors based on job type and location. Communicates with the Compliance Agent and other agents via the Agent-to-Agent (A2A) protocol.

**Key responsibilities:**
- Exposes a standardized `/.well-known/agent-card.json` for agent discovery
- Accepts JSON-RPC requests at POST `/a2a/contractor_agent`
- Uses Gemini 2.5 Flash + Google Search tool to locate real-world licensed contractors
- Provides fit analysis and contact information in its response

**A2A notes:**
- Uses `a2a-sdk` for protocol compliance
- Agent card must accurately reflect current tool capabilities and security requirements
- Do not modify the A2A endpoint paths without updating the agent card

---

### 3. Assessor MCP Server (`assessor-mcp-server/`)

Provides fake San Paloma County property and zoning data to AI agents via the Model Context Protocol (MCP) over Streamable HTTP on port 8002.

**Exposed MCP tools:**
| Tool | Description |
|---|---|
| `lookup_parcel` | Fetch parcel data by address or APN |
| `get_zoning_classification` | Return zoning class for a parcel |
| `get_setback_requirements` | Return setback rules for a zoning class |
| `add_parcel` | Insert a new parcel record |
| `rezone_address` | Update zoning for an address |
| `add_zoning_rule` | Add a new zoning rule |

**Notes:**
- Backend is SQLite (`assessor.db`)
- The Compliance Agent consumes these tools at analysis time to provide parcel-aware code checks
- Do not change tool names or signatures without updating all agent callers

---

### 4. Agent Engine (`agent-engine/`)

A shared Vertex AI Agent Engine deployment that provides centralized infrastructure for all agents in the system.

**Key responsibilities:**
- `VertexAiSessionService` — persistent, scalable conversation history shared across the Compliance and Contractor agents
- `VertexAiMemoryBankService` — long-term memory for regulatory context, past violations, and interaction history
- Deployed as a container to Vertex AI Agent Engine (see `agent-engine/README.md`)

**Notes:**
- All agents should use this service for session and memory management rather than implementing their own
- Session state is managed by Google ADK (`google.adk`)

---

### 5. API Gateway (`api/`)

The Go/Gin backend that sits between the frontend and the AI services. Manages users, properties, and permits in SQLite via GORM, and proxies analysis and chat requests to the Compliance Agent.

**Key endpoints:**

| Method | Path | Description |
|---|---|---|
| POST | `/api/login` | Login or register by email |
| GET | `/api/users/:id/properties` | List user properties |
| POST | `/api/users/:id/properties` | Create a property |
| GET | `/api/properties/:id/permits` | List permits for a property |
| POST | `/api/properties/:id/permits` | Create a permit application |
| GET | `/api/permits/:id` | Get permit + submission history |
| DELETE | `/api/permits/:id` | Delete a permit |
| POST | `/api/analyze-plan` | Upload PDF → proxy to Compliance Agent |
| POST | `/api/chat` | Proxy chat message to Compliance Agent |
| GET | `/health` | Health check |

**Notes:**
- Database: `building_plans.db` (SQLite via GORM)
- Emits OpenTelemetry traces to Google Cloud Trace
- CORS is configured for frontend requests from `localhost:5173`

---

### 6. Frontend (`frontend/`)

React + Vite + TypeScript SPA. All styling decisions are governed by `plan/DESIGN.md`. Do not introduce new UI patterns without checking that document first.

**Stack:** React, TypeScript, Vite, TailwindCSS, Zustand, Axios, Lucide-React, OpenTelemetry

**Design system highlights (enforced):**
- Color palette anchored on `#0051ae` (primary), `#006e2b` (approved/secondary), `#50555b` (metadata)
- No borders — use background tonal shifts (`surface-container-low` → `surface-container-highest`)
- Typography: Inter, with monospace accents (`ui-monospace`) for permit IDs and code references
- Cards use a 4px left-edge status bar (green = approved, red = violation), not dot indicators
- Primary buttons use a 135° gradient from `#0051ae` to `#0969da`
- Progress trackers use backdrop-blur (20px) at 80% opacity on white

---

## Inter-Agent Communication

```
Frontend
  └─▶ API Gateway (Go :8080)
        ├─▶ Compliance Agent (Python :8000)
        │     ├─▶ Document AI  (GCP)
        │     ├─▶ Vertex AI RAG Engine  (GCP)
        │     ├─▶ Gemini 2.5 Pro/Flash  (GCP)
        │     ├─▶ Model Armor  (GCP)
        │     └─▶ Assessor MCP Server (Python :8002)  [via MCP]
        └─▶ (results persisted to SQLite)

Compliance Agent
  └─▶ Contractor Agent (Python :8081)  [via A2A protocol]

All Agents
  └─▶ Agent Engine (Vertex AI)  [session + memory]
```

---

## Running Locally

```bash
# Install all dependencies
make install

# Start all services
make all

# Stop all services
make stop
```

Individual services:
```bash
cd agent && make start                # Compliance Agent   :8000
cd contractor-agent && make start     # Contractor Agent   :8081
cd assessor-mcp-server && make start  # MCP Server         :8002
cd api && make start                  # API Gateway        :8080
cd frontend && make start             # Frontend           :5173
```

Access the app at `http://localhost:5173` (or `http://localhost:3000` if using the production frontend build).

---

## GCP Setup

```bash
cd infra && make setup    # Enable APIs, create service account, provision RAG corpus, deploy Agent Engine
cd infra && make onboard  # Register deployed agents in Agent Registry
```

After running `make setup`, manually create a **Document AI → Document OCR** processor in the [GCP console](https://console.cloud.google.com/ai/document-ai/processors) and add the Processor ID to `agent/.env`.

---

## Testing & CI

- GitHub Actions runs CodeQL security scanning on every push (see `.github/workflows/codeql.yml`)
- CI workflow status is reflected in the README badges
- Each service has its own `make test` target — run from the service directory

---

## Key Constraints for Agents Modifying This Repo

- **Regulatory data** lives in `building-codes/` and is indexed into a Vertex AI RAG corpus named `ca-building-codes` in `us-west1`. Do not modify document structure without re-running `make setup`.
- **MCP tool signatures** in `assessor-mcp-server/` are consumed by the Compliance Agent. Changing them is a breaking change.
- **A2A agent card** at `contractor-agent/.well-known/agent-card.json` must stay in sync with actual endpoint paths and capabilities.
- **Model Armor filter lists** (e.g., `LEGAL_LIABILITY_PHRASES`) must not be removed or weakened — they are a liability guardrail.
- **Session/memory state** must route through the Agent Engine (`agent-engine/`), not be implemented locally in individual agents.
- San Paloma County is a **fictitious jurisdiction** used for demo purposes only. Do not replace it with real county data.
