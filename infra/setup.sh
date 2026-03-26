#!/bin/bash
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


# Configuration
GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
GOOGLE_CLOUD_LOCATION=$(gcloud config get-value compute/region)
if [ -z "$GOOGLE_CLOUD_LOCATION" ]; then
  GOOGLE_CLOUD_LOCATION="us-central1"
fi
SERVICE_ACCOUNT_NAME="build-permit-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
DB_BUCKET="${GOOGLE_CLOUD_PROJECT}-building-permit-db"

echo "Using Project ID: $GOOGLE_CLOUD_PROJECT"
echo "Using Location: $GOOGLE_CLOUD_LOCATION"

# 1. Enable APIs
echo "Enabling necessary APIs..."
APIS=(
  "aiplatform.googleapis.com"
  "documentai.googleapis.com"
  "iam.googleapis.com"
  "serviceusage.googleapis.com"
  "storage.googleapis.com"
  "cloudresourcemanager.googleapis.com"
  "telemetry.googleapis.com"
  "artifactregistry.googleapis.com"
  "run.googleapis.com"
  "cloudbuild.googleapis.com"
  "cloudtrace.googleapis.com"
  "agentregistry.googleapis.com"
)

for api in "${APIS[@]}"; do
  echo "Enabling $api..."
  gcloud services enable "$api" --project "$GOOGLE_CLOUD_PROJECT"
done

# 2. Create Service Account if it doesn't exist
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project "$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  echo "Creating service account: $SERVICE_ACCOUNT_NAME..."
  gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name="Building Permit Compliance SA" \
    --project "$GOOGLE_CLOUD_PROJECT"
else
  echo "Service account $SERVICE_ACCOUNT_NAME already exists."
fi

# 3. Assign Roles
echo "Assigning roles to service account..."
ROLES=(
  "roles/aiplatform.user"
  "roles/documentai.apiUser"
  "roles/storage.objectViewer"
  "roles/storage.objectCreator"
  "roles/storage.admin"
  "roles/telemetry.writer"
  "roles/cloudtrace.agent"
  "roles/telemetry.metricsWriter"
  "roles/agentregistry.viewer"
  "roles/logging.logWriter"
  "roles/serviceusage.serviceUsageConsumer"
)

for role in "${ROLES[@]}"; do
  echo "Adding role $role..."
  gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="$role" >/dev/null
done

# 4. Create GCS Bucket for Database if it doesn't exist
if ! gsutil ls -b "gs://${DB_BUCKET}" >/dev/null 2>&1; then
  echo "Creating GCS bucket for database: $DB_BUCKET in $GOOGLE_CLOUD_LOCATION..."
  gsutil mb -l "$GOOGLE_CLOUD_LOCATION" "gs://${DB_BUCKET}"
else
  echo "GCS bucket $DB_BUCKET already exists."
fi

# 5. Create Artifact Registry Repository if it doesn't exist
REPOSITORY_NAME="building-permit"
if ! gcloud artifacts repositories describe "$REPOSITORY_NAME" --location="$GOOGLE_CLOUD_LOCATION" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  echo "Creating Artifact Registry repository: $REPOSITORY_NAME in $GOOGLE_CLOUD_LOCATION..."
  gcloud artifacts repositories create "$REPOSITORY_NAME" \
    --repository-format=docker \
    --location="$GOOGLE_CLOUD_LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --description="Docker repository for building-permit images"
else
  echo "Artifact Registry repository $REPOSITORY_NAME already exists."
fi

echo "Setup script completed successfully."
