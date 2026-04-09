PROJECT_ID ?= $(shell gcloud config get-value project)
PROJECT_NUMBER ?= $(shell gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
REGION ?= $(shell gcloud config get compute/region)

.PHONY: install start build clean deploy

install:
	npm install

start:
	npm run dev

build:
	npm run build

clean:
	rm -rf node_modules dist

deploy:
	export REGION=${REGION} ;\
	export PROJECT_ID=${PROJECT_ID} ;\
	export PROJECT_NUMBER=${PROJECT_NUMBER} ;\
	gcloud builds submit --config .cloudbuild/deploy.yaml --region=${REGION} --substitutions _COMMIT_SHA=$(shell git rev-parse --short HEAD),_REGION=${REGION} .
