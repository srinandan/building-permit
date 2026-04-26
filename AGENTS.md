# AGENTS.md

This document provides guidance for AI coding agents (e.g., Codex, Jules, Claude Code) working in this repository. For full architecture, data models, and API specs see `plan/spec.md`. For UI/UX design rules see `plan/DESIGN.md`.

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
        └── submit/SKILL.md # Run this skill to lint, test, and open a PR for your changes
```

---

## Ground Rules for All Agents

1. **Read `plan/` before making changes.** `plan/DESIGN.md` and `plan/spec.md` are the authoritative sources for UI design rules, architecture decisions, and feature goals. Do not contradict them.
2. **Use the `submit` skill** (`.agents/skills/submit/SKILL.md`) when you are ready to ship — it lints, tests, and opens a PR for you.
3. **Never use 1px solid borders** in the frontend. Boundaries are expressed via background color shifts only (see `plan/DESIGN.md` §2 "The No-Line Rule").
4. **Do not use raw `#000000`** for text anywhere in the UI. Use `on-surface` (`#191c1e`).
5. **Do not add standard drop shadows.** Use tonal layering or the approved ambient shadow token (`0 20px 40px rgba(25,28,30,0.06)`) only.

---

## Coding Principles (Karpathy Guidelines)

These principles are derived from Andrej Karpathy's observations on LLM coding pitfalls and aim to reduce common mistakes.

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**
- Transform tasks into verifiable goals.
- For multi-step tasks, state a brief plan with verification steps.

---

## Running Locally

```bash
make install   # Install all dependencies
make all       # Start all services
make stop      # Stop all services
```

Individual services:
```bash
cd agent && make start                # Compliance Agent   :8000
cd contractor-agent && make start     # Contractor Agent   :8081
cd assessor-mcp-server && make start  # MCP Server         :8002
cd api && make start                  # API Gateway        :8080
cd frontend && make start             # Frontend           :5173
```

Access the app at `http://localhost:5173`.

---

## GCP Setup

```bash
cd infra && make setup    # Enable APIs, create service account, provision RAG corpus, deploy Agent Engine
cd infra && make onboard  # Register deployed agents in Agent Registry
```

After `make setup`, manually create a **Document AI → Document OCR** processor in the GCP console and add the Processor ID to `agent/.env`.

---

## Testing & CI

- GitHub Actions runs CodeQL security scanning on every push (`.github/workflows/codeql.yml`).
- Each service has its own `make test` target — run from the service directory.
- Use the `submit` skill to run all checks before opening a PR.

---

## Key Constraints

- **Regulatory data** lives in `building-codes/` and is indexed into a Vertex AI RAG corpus named `ca-building-codes` in `us-west1`. Do not modify document structure without re-running `make setup`.
- **MCP tool signatures** in `assessor-mcp-server/` are consumed by the Compliance Agent. Changing them is a breaking change.
- **A2A agent card** at `contractor-agent/.well-known/agent-card.json` must stay in sync with actual endpoint paths and capabilities.
- **Model Armor filter lists** (e.g., `LEGAL_LIABILITY_PHRASES`) must not be removed or weakened — they are a liability guardrail.
- **Session/memory state** must route through the Agent Engine (`agent-engine/`), not be implemented locally in individual agents.
- San Paloma County is a **fictitious jurisdiction** used for demo purposes only. Do not replace it with real county data.
