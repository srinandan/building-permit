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
	gcloud builds submit --config .cloudbuild/deploy.yaml --substitutions _COMMIT_SHA=$(shell git rev-parse --short HEAD) .
