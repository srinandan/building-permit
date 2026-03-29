# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

PROJECT_ID ?= $(shell gcloud config get-value project)
PROJECT_NUMBER ?= $(shell gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
REGION ?= us-central1

.PHONY: install start clean deploy

install:
	uv sync

test:
	uv run python test_main.py

test-network:
	uv run python test_network.py

start:
	uv run main.py --reload --port 8002 --host 0.0.0.0

clean:
	rm -rf .venv

deploy:
	export REGION=${REGION} ;\
	export PROJECT_ID=${PROJECT_ID} ;\
	export PROJECT_NUMBER=${PROJECT_NUMBER} ;\
	gcloud builds submit --config .cloudbuild/deploy.yaml --region=${REGION} --substitutions _COMMIT_SHA=$(shell git rev-parse --short HEAD),_REGION=${REGION} .
