GOOGLE_CLOUD_PROJECT ?= $(shell gcloud config get-value project)
GOOGLE_CLOUD_PROJECT_NUMBER ?= $(shell gcloud projects describe ${GOOGLE_CLOUD_PROJECT} --format="value(projectNumber)")
GOOGLE_CLOUD_LOCATION ?= $(shell gcloud config get-value compute/region)
DOCUMENT_AI_LOCATION ?= us
DOCUMENT_AI_PROCESSOR_ID=24ec41d66617b372
##NOTE: DO NOT change us-west1; us-central1 is not supported
VERTEX_RAG_CORPUS_NAME=projects/${GOOGLE_CLOUD_PROJECT}/locations/us-west1/ragCorpora/4611686018427387904
REASONING_ENGINE_APP_NAME=projects/${GOOGLE_CLOUD_PROJECT}/locations/${GOOGLE_CLOUD_LOCATION}/reasoningEngines/3166398874436763648
GEMINI_MODEL_NAME=gemini-2.5-pro

.PHONY: install start build clean deploy

install:
	uv sync

start:
	export GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION} ;\
	export GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT} ;\
	export GOOGLE_CLOUD_PROJECT_NUMBER=${GOOGLE_CLOUD_PROJECT_NUMBER} ;\
	export DOCUMENT_AI_LOCATION=${DOCUMENT_AI_LOCATION} ;\
	export DOCUMENT_AI_PROCESSOR_ID=${DOCUMENT_AI_PROCESSOR_ID} ;\
	export VERTEX_RAG_CORPUS_NAME=${VERTEX_RAG_CORPUS_NAME} ;\
	export REASONING_ENGINE_APP_NAME=${REASONING_ENGINE_APP_NAME} ;\
	export GEMINI_MODEL_NAME=${GEMINI_MODEL_NAME} ;\
	uv run uvicorn main:app --reload --port 8000

build:
	@echo "Python builds are typically just dependencies, use 'make install'"

clean:
	rm -rf .venv

deploy:
	export GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION} ;\
	gcloud builds submit --config .cloudbuild/deploy.yaml --region=${GOOGLE_CLOUD_LOCATION} --substitutions _COMMIT_SHA=$(shell git rev-parse --short HEAD),_REGION=${GOOGLE_CLOUD_LOCATION} .
