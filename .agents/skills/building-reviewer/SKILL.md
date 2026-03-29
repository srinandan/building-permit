---
name: building-reviewer
description: AI system to automate the review of building plans against regulatory frameworks.
license: Apache-2.0
---

# Building Plan Compliance Checker: System Skills & Capabilities

This repository implements an agentic AI system designed to automate the review of building plans against complex regulatory frameworks. Below is a detailed breakdown of the technical and functional skills embedded in this project.

## Agent Instructions & Specifications
- **Project Specifications:** When executing tasks, modifying features, or resolving issues, the agent **MUST** review and adhere to the project specifications and design rules detailed in the `plan/` directory (e.g. `plan/DESIGN.md`, `plan/spec.md`). This folder serves as the ground truth for architecture, UI design syntax, and feature goals.

## 1. Core AI & Analysis Skills

### Multimodal Document Understanding
- **PDF Analysis:** Capability to process complex architectural drawings and text directly using Gemini 1.5 Pro.
- **Structural Extraction:** Uses Google Cloud Document AI to perform high-fidelity OCR and layout analysis on building plans.
- **Visual Verification:** Ability to "see" and interpret diagrams, symbols, and annotations in blueprints to verify spatial requirements (e.g., clearance, dimensions).

### Regulatory Reasoning (RAG)
- **Contextual Retrieval:** Employs Vertex AI RAG Engine to retrieve relevant sections from the California Building Standards Code (Title 24) and San Paloma County local reach codes.
- **Compliance Mapping:** Matches extracted plan data against retrieved regulatory text to identify specific violations or approved elements.
- **Actionable Feedback:** Generates structured reports that include exact code sections, detailed descriptions of non-compliance, and specific suggestions for remediation.

### Shared Infrastructure & Persistent Context
- **Vertex AI Session Management:** Centralized session service for persistent, scalable conversation history across all agents in the ecosystem.
- **Vertex AI Memorybank:** Long-term memory service allowing agents to retrieve and reference past interactions, violations, and decisions (facilitated by the `agent-engine`).
- **Agentic Memory (ADK):** Utilizes Google ADK (Agent Development Kit) to maintain conversational state and long-term memory across sessions.

### Agent Interoperability (A2A)
- **Protocol Compliance:** Adheres to the Agent-to-Agent (A2A) Protocol Specification for seamless communication between different AI agents.
- **Agent Discovery:** Exposes standardized "Agent cards" (`.well-known/agent-card.json`) that describe agent capabilities, security requirements, and endpoints.
- **Inter-Agent Coordination:** Uses `a2a-sdk` to enable agents (e.g., Compliance Agent and Contractor Agent) to discover and interact with each other.

---

## 2. Technical Stack & Infrastructure Skills

### Assessor MCP Server (Data Retrieval)
- **MCP Protocol:** Implements the Model Context Protocol (MCP) to expose property data as structured tools.
- **Tool Integration:** Provides `lookup_parcel`, `get_zoning_classification`, and `get_setback_requirements` tools via standard HTTP (`FastMCP`).
- **Data Management:** Capabilities to `add_parcel`, `rezone_address`, and `add_zoning_rule` to the county's assessor database.

### External MCP Integrations
- **Google Maps MCP:** Proxies map search requests via `modelcontextprotocol/go-sdk` from the API Gateway directly to standard Google Maps MCP.

### Microservices Architecture
- **Polyglot Development:** Seamless integration between a Go-based API Gateway, a Python-based AI Agent, and a React-based Frontend.
- **Orchestration:** The Go backend manages business logic, user state (SQLite/GORM), and acts as a secure proxy to the AI analysis engine.

### Cloud Native Integrations
- **Google Cloud Platform (GCP):** Deep integration with Vertex AI, Document AI, Cloud Run, and Secret Manager.
- **Observability:** Built-in distributed tracing using OpenTelemetry (OTLP HTTP Exporter natively implemented in Go & Python) for monitoring analysis latency and debugging AI pipelines.
- **Scalability & Containerization:** Pre-configured Dockerfiles (annotated with OCI labels) and `service.yaml` specs for quick deployment to Google Cloud Run (supporting bounded auto-scaling) or GKE.

---

## 3. Domain Knowledge: Building Compliance

### Regulatory Frameworks
- **CA Title 24 (California Building Standards Code):** Expertise in Parts 6 (Energy) and 11 (CalGreen).
- **Local Reach Codes:** Specialized knowledge of San Paloma County requirements, including All-Electric building mandates and EV charging infrastructure.

### Architectural Standards
- **Plan Interpretation:** Understanding of standard architectural scales, legends, and sheet types (Site Plans, Floor Plans, MEP).

---

## 4. Developer & Operational Skills

### Automated Workflows
- **Standardized Tooling:** Comprehensive `Makefile` for unified management across services (start, build, test, install, stop).
- **Package Management:** Uses modern dependency managers: `uv` for Python, `npm` for Frontend, and `go mod` for the API.
- **CI/CD Ready:** Includes GitHub Actions for CodeQL security scanning and automated CI.

---

## 5. Usage Skills (What you can do)
1. **Automated Triage:** Upload a PDF and get an "Approved/Rejected" status in seconds.
2. **Issue Tracking:** View a list of specific violations mapped to the legal code.
3. **History Management:** Maintain a database of property permits and multiple submission versions.
4. **Interactive Clarification:** Ask follow-up questions about specific violations via an integrated chat interface powered by conversational AI.
5. **Local Development:** Spin up the entire stack locally for testing and customization using `make all`.
