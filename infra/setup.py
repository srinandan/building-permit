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

import os
import subprocess
import sys
import json
import urllib.request
import re
def run_command(command, ignore_errors=False):
    """Run a shell command and print its output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0 and not ignore_errors:
        print(f"Error executing: {command}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()

def setup_infrastructure():
    # Configuration
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        project_id = run_command("gcloud config get-value project", ignore_errors=True)
    if not project_id:
        print("Error: Could not determine GOOGLE_CLOUD_PROJECT. Set it as an environment variable or via gcloud config.")
        sys.exit(1)

    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    if not location:
        location = run_command("gcloud config get-value compute/region", ignore_errors=True)
    if not location:
        location = "us-central1"

    service_account_name = "build-permit-sa"
    service_account_email = f"{service_account_name}@{project_id}.iam.gserviceaccount.com"

    # Define resource names
    buckets = [
        f"gs://{project_id}-building-permit-db",
        f"gs://{project_id}-building-permit-assessor-db",
        f"gs://{project_id}-logs-bucket",
        f"gs://{project_id}-bq-analytics",
        f"gs://{project_id}"  # Default bucket used as artifact_service_uri
    ]

    print(f"Using Project ID: {project_id}")
    print(f"Using Location: {location}")

    # 1. Enable APIs
    print("\n--- Enabling necessary APIs ---")
    apis = [
        "aiplatform.googleapis.com",
        "documentai.googleapis.com",
        "iam.googleapis.com",
        "serviceusage.googleapis.com",
        "storage.googleapis.com",
        "cloudresourcemanager.googleapis.com",
        "telemetry.googleapis.com",
        "artifactregistry.googleapis.com",
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "cloudtrace.googleapis.com",
        "agentregistry.googleapis.com",
        "bigquery.googleapis.com",
        "secretmanager.googleapis.com",
        "modelarmor.googleapis.com",
        "mapstools.googleapis.com",
        "dlp.googleapis.com",
    ]
    for api in apis:
        print(f"Enabling {api}...")
        run_command(f"gcloud services enable {api} --project {project_id}")

    # 2. Create Service Account
    print("\n--- Creating Service Account ---")
    sa_check = run_command(f"gcloud iam service-accounts describe {service_account_email} --project {project_id}", ignore_errors=True)
    if not sa_check:
        print(f"Creating service account: {service_account_name}...")
        run_command(f'gcloud iam service-accounts create {service_account_name} --display-name="Building Permit Compliance SA" --project {project_id}')
    else:
        print(f"Service account {service_account_name} already exists.")

    # 3. Assign Roles
    print("\n--- Assigning Roles to Service Account ---")
    roles = [
        "roles/aiplatform.user",
        "roles/documentai.apiUser",
        "roles/storage.objectViewer",
        "roles/storage.objectCreator",
        "roles/storage.admin",
        "roles/telemetry.writer",
        "roles/cloudtrace.agent",
        "roles/telemetry.metricsWriter",
        "roles/agentregistry.viewer",
        "roles/logging.logWriter",
        "roles/serviceusage.serviceUsageConsumer",
        "roles/bigquery.admin",
        "roles/secretmanager.secretAccessor",
        "roles/browser",
        "roles/cloudapiregistry.viewer",
        "roles/monitoring.metricWriter",
        "roles/modelarmor.admin"
    ]
    for role in roles:
        print(f"Adding role {role}...")
        run_command(f"gcloud projects add-iam-policy-binding {project_id} --member=serviceAccount:{service_account_email} --role={role} > /dev/null", ignore_errors=True)

    # 4. Create GCS Buckets
    print("\n--- Creating GCS Buckets ---")
    for bucket in buckets:
        bucket_check = run_command(f"gsutil ls -b {bucket}", ignore_errors=True)
        if not bucket_check:
            print(f"Creating GCS bucket: {bucket} in {location}...")
            run_command(f"gsutil mb -l {location} {bucket}")
        else:
            print(f"GCS bucket {bucket} already exists.")

    # 5. Create Artifact Registry Repository
    print("\n--- Creating Artifact Registry ---")
    repository_name = "building-permit"
    repo_check = run_command(f"gcloud artifacts repositories describe {repository_name} --location={location} --project={project_id}", ignore_errors=True)
    if not repo_check:
        print(f"Creating Artifact Registry repository: {repository_name} in {location}...")
        run_command(f'gcloud artifacts repositories create {repository_name} --repository-format=docker --location={location} --project={project_id} --description="Docker repository for building-permit images"')
    else:
        print(f"Artifact Registry repository {repository_name} already exists.")

    # 6. Create Secrets
    print("\n--- Creating Secrets ---")
    secrets = ["maps-api-key", "otlp-api-key"]
    for secret in secrets:
        secret_check = run_command(f"gcloud secrets describe {secret} --project {project_id}", ignore_errors=True)
        if not secret_check:
            print(f"Creating Secret Manager secret: {secret}...")
            run_command(f"gcloud secrets create {secret} --replication-policy=automatic --project {project_id}")
        else:
            print(f"Secret {secret} already exists.")

    # 6a. Create, restrict, and store Maps API Key
    print("\n--- Creating and Storing Maps API Key ---")
    # Check if a key with display name "Maps API Key" already exists
    # Note: gcloud services api-keys list does not support filtering by display name directly
    # So, we list all and filter manually
    existing_keys_json = run_command(f"gcloud services api-keys list --project={project_id} --format=json", ignore_errors=True)
    existing_keys = json.loads(existing_keys_json) if existing_keys_json else []
    
    key_exists = False
    key_name = None # To store the resource name of the existing key if found
    for key in existing_keys:
        if key.get("displayName") == "Maps API Key":
            key_exists = True
            key_name = key.get("name") # e.g., projects/PROJECT_NUMBER/locations/global/keys/KEY_ID
            print(f"Maps API Key with display name 'Maps API Key' already exists: {key_name}. Skipping creation.")
            break

    if not key_exists:
        print("Creating Maps API Key with restriction to mapstools.googleapis.com...")
        # Create the key with display name and API target restriction
        # Output: Created new key: projects/PROJECT_NUMBER/locations/global/keys/KEY_ID
        create_output = run_command(f"gcloud services api-keys create --display-name=\"Maps API Key\" --api-target=service=mapstools.googleapis.com --project={project_id}")

        match = re.search(r"projects/.*/locations/.*/keys/.*", create_output)
        if match:
            key_name = match.group(0) # This will be the full resource name of the key
            print(f"Successfully created key: {key_name}")

            # Get the cleartext key string
            print("Retrieving key string...")
            key_string = run_command(f"gcloud services api-keys get-key-string {key_name} --project={project_id}")

            if key_string:
                # Store the key in Secret Manager
                print("Storing key in Secret Manager...")
                run_command(f"echo -n '{key_string}' | gcloud secrets versions add maps-api-key --data-file=- --project={project_id}")
                print("Successfully stored Maps API Key in Secret Manager.")
            else:
                print("Error: Failed to retrieve API key string after creation.")
        else:
            print("Error: Failed to parse key name from creation output.")
    else: # If key already exists, still try to store its string in Secret Manager
        if key_name:
            print(f"Retrieving key string for existing key: {key_name}...")
            key_string = run_command(f"gcloud services api-keys get-key-string {key_name} --project={project_id}")
            if key_string:
                print("Storing existing key in Secret Manager...")
                run_command(f"echo -n '{key_string}' | gcloud secrets versions add maps-api-key --data-file=- --project={project_id}")
                print("Successfully stored existing Maps API Key in Secret Manager.")
            else:
                print("Error: Failed to retrieve API key string for existing key.")

    # 6b. Grant Compute Engine SA access to the secret
    print("\n--- Granting Compute Engine SA access to Maps API Key secret ---")
    project_number = run_command(f"gcloud projects describe {project_id} --format=\"value(projectNumber)\"")
    compute_sa_email = f"{project_number}-compute@developer.gserviceaccount.com"
    print(f"Granting 'secretmanager.secretAccessor' role to {compute_sa_email} for secret 'maps-api-key'...")
    run_command(f"gcloud secrets add-iam-policy-binding maps-api-key --member=serviceAccount:{compute_sa_email} --role=roles/secretmanager.secretAccessor --project={project_id}", ignore_errors=True)
    print("Successfully granted access.")

    # 7. Create BigQuery Dataset
    print("\n--- Creating BigQuery Dataset ---")
    bq_dataset = "adk_agent_analytics"
    bq_check = run_command(f"bq show {project_id}:{bq_dataset}", ignore_errors=True)
    if "Not found" in bq_check or not bq_check:
        print(f"Creating BigQuery dataset: {bq_dataset}...")
        run_command(f"bq mk --location={location} -d {project_id}:{bq_dataset}")
    else:
        print(f"BigQuery dataset {bq_dataset} already exists.")

    # 8. Create Document AI Processor
    print("\n--- Creating Document AI Processor ---")
    docai_location = "us" # Document AI usually uses 'us' or 'eu' region
    docai_display_name = "ca-building-codes"
    
    token = run_command("gcloud auth application-default print-access-token", ignore_errors=True)
    docai_processor_id = None
    if token:
        docai_url = f"https://{docai_location}-documentai.googleapis.com/v1/projects/{project_id}/locations/{docai_location}/processors"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Check if exists
        req_list = urllib.request.Request(docai_url, headers=headers, method="GET")
        processor_exists = False
        try:
            with urllib.request.urlopen(req_list) as response:
                result = json.loads(response.read().decode("utf-8"))
                for proc in result.get("processors", []):
                    if proc.get("displayName") == docai_display_name:
                        processor_exists = True
                        docai_processor_id = proc.get("name").split("/")[-1]
                        print(f"Document AI Processor '{docai_display_name}' already exists: {proc.get('name')}")
                        break
        except Exception as e:
            print(f"Warning: Failed to list Document AI processors: {e}")
            
        if not processor_exists:
            print(f"Creating Document AI processor: {docai_display_name}...")
            data = {"displayName": docai_display_name, "type": "OCR_PROCESSOR"}
            req_create = urllib.request.Request(docai_url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req_create) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    docai_processor_id = result.get("name").split("/")[-1]
                    print(f"Successfully created processor '{result.get('displayName')}' with name: {result.get('name')}")
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                print(f"Failed to create processor. HTTP Error {e.code}: {e.reason}")
                print(f"Details: {error_body}")
            except Exception as e:
                print(f"Failed to create processor: {e}")
                
        # Update config files
        if docai_processor_id:
            import re
            makefile_path = "../agent/Makefile"
            deploy_yaml_path = "../agent/.cloudbuild/deploy.yaml"

            if os.path.exists(makefile_path):
                with open(makefile_path, "r") as f:
                    content = f.read()
                content = re.sub(r"DOCUMENT_AI_PROCESSOR_ID=[a-zA-Z0-9]+", f"DOCUMENT_AI_PROCESSOR_ID={docai_processor_id}", content)
                with open(makefile_path, "w") as f:
                    f.write(content)
                print(f"Updated agent/Makefile with Document AI processor ID: {docai_processor_id}")

            if os.path.exists(deploy_yaml_path):
                with open(deploy_yaml_path, "r") as f:
                    content = f.read()
                content = re.sub(r"_DOCUMENT_AI_PROCESSOR_ID: [a-zA-Z0-9]+", f"_DOCUMENT_AI_PROCESSOR_ID: {docai_processor_id}", content)
                with open(deploy_yaml_path, "w") as f:
                    f.write(content)
                print(f"Updated agent/.cloudbuild/deploy.yaml with Document AI processor ID: {docai_processor_id}")
    else:
        print("Warning: Could not fetch auth token. Skipping Document AI processor creation.")

    print("\nModel Armor setup has been extracted to setup_model_armor.py. Run 'make model-armor' inside the infra directory to set it up.")

    print("\nInfrastructure setup script completed successfully.")

if __name__ == "__main__":
    setup_infrastructure()
