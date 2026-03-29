PROJECT_ID ?= $(shell gcloud config get-value project)
PROJECT_NUMBER ?= $(shell gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
REGION ?= us-central1

.PHONY: install start build clean deploy

install:
	uv sync

start:
	uv run uvicorn main:app --reload --port 8081

build:
	uv sync

clean:
	rm -rf .venv __pycache__ .pytest_cache

deploy:
	export REGION=${REGION} ;\
	export PROJECT_ID=${PROJECT_ID} ;\
	export PROJECT_NUMBER=${PROJECT_NUMBER} ;\
	gcloud builds submit --config .cloudbuild/deploy.yaml --region=${REGION} --substitutions _COMMIT_SHA=$(shell git rev-parse --short HEAD),_REGION=${REGION} .
