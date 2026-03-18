.PHONY: setup apis sa rag agent-engine help

help:
	@echo "Usage:"
	@echo "  make setup   - Run full setup (APIs, SA, IAM, and RAG)"
	@echo "  make apis    - Enable necessary GCP APIs"
	@echo "  make sa      - Create service account and assign roles"
	@echo "  make rag     - Setup RAG engine corpus and upload documents"
	@echo "  make agent-engine - Deploy the Vertex AI Agent Engine"

setup: apis sa rag agent-engine

apis:
	@echo "Enabling APIs..."
	./setup.sh # This script currently does both apis and sa, but we can refine if needed

sa:
	@echo "Setting up Service Account..."
	./setup.sh

rag:
	@echo "Setting up RAG Engine..."
	uv run --with google-cloud-aiplatform,google-cloud-storage,pyopenssl python3 rag_setup.py

agent-engine:
	@echo "Deploying Agent Engine..."
	cd ../agent-engine && make deploy

chmod:
	chmod +x setup.sh
