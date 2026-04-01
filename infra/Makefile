.PHONY: setup apis sa rag agent-engine artifact-registry onboard-assessor onboard-contractor onboard help

help:
	@echo "Usage:"
	@echo "  make setup   - Run full setup (APIs, SA, IAM, AR, and RAG)"
	@echo "  make apis    - Enable necessary GCP APIs"
	@echo "  make sa      - Create service account and assign roles"
	@echo "  make artifact-registry - Create Artifact Registry repository"
	@echo "  make rag     - Setup RAG engine corpus and upload documents"
	@echo "  make onboard-assessor - Onboard Assessor MCP server"
	@echo "  make onboard-contractor - Onboard Contractor Agent"
	@echo "  make onboard - Onboard all agents"

setup: apis sa artifact-registry rag agent-engine

apis:
	@echo "Enabling APIs..."
	python3 setup.py

sa:
	@echo "Setting up Service Account..."
	python3 setup.py

artifact-registry:
	@echo "Setting up Artifact Registry..."
	python3 setup.py

rag:
	@echo "Setting up RAG Engine..."
	python3 rag_setup.py

agent-engine:
	@echo "Deploying Agent Engine..."
	cd ../agent-engine && make deploy

onboard-assessor:
	@echo "Onboarding Assessor MCP Server..."
	python3 onboard_assessor_mcp.py

onboard-contractor:
	@echo "Onboarding Contractor Agent..."
	python3 onboard_contractor_agent.py

model-armor:
	@echo "Setting up Model Armor..."
	python3 setup_model_armor.py

onboard: onboard-assessor onboard-contractor
