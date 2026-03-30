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
import urllib.error

def run_command(command, ignore_errors=False):
    """Run a shell command and print its output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0 and not ignore_errors:
        print(f"Error executing: {command}")
        print(result.stderr)
        return None
    return result.stdout.strip()

def setup_model_armor_floor_settings():
    # Configuration
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        project_id = run_command("gcloud config get-value project", ignore_errors=True)
    if not project_id:
        print("Error: Could not determine GOOGLE_CLOUD_PROJECT.")
        sys.exit(1)

    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    print(f"Configuring Model Armor Floor Settings for project: {project_id} in {location}")

    token = run_command("gcloud auth application-default print-access-token", ignore_errors=True)
    if not token:
        print("Error: Could not fetch auth token. Ensure you are authenticated.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Configure Floor Settings (Responsible AI Best Practices)
    # Floor settings mandate minimum filter requirements for all templates.
    print("\n--- Configuring Model Armor Floor Settings ---")
    
    floor_setting_data = {
        "filterConfig": {
            "raiSettings": {
                "raiFilters": [
                    {"filterType": "HATE_SPEECH", "confidenceLevel": "LOW_AND_ABOVE"},
                    {"filterType": "HARASSMENT", "confidenceLevel": "LOW_AND_ABOVE"},
                    {"filterType": "DANGEROUS", "confidenceLevel": "LOW_AND_ABOVE"},
                    {"filterType": "SEXUALLY_EXPLICIT", "confidenceLevel": "LOW_AND_ABOVE"}
                ]
            },
            "piAndJailbreakFilterSettings": {
                "filterEnforcement": "ENABLED",
                "confidenceLevel": "LOW_AND_ABOVE"
            },
            "maliciousUriFilterSettings": {
                "filterEnforcement": "ENABLED"
            }
        },
        "integratedServices": ["AI_PLATFORM"],
        "aiPlatformFloorSetting": {
            "inspectAndBlock": True,
            "enableCloudLogging": True
        },
        "enableFloorSettingEnforcement": True
    }

    ma_floor_url = f"https://modelarmor.googleapis.com/v1/projects/{project_id}/locations/{location}/floorSetting"
    
    # Use PATCH to update floor settings
    # The API might require a field mask or full replacement. 
    # Based on docs, it's often a GET then PATCH or a direct PATCH.
    try:
        req = urllib.request.Request(ma_floor_url, data=json.dumps(floor_setting_data).encode("utf-8"), headers=headers, method="PATCH")
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print("Successfully updated Model Armor Floor Settings.")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Failed to update floor settings. HTTP Error {e.code}: {e.reason}")
        print(f"Details: {error_body}")
    except Exception as e:
        print(f"Failed to update floor settings: {e}")

    # 2. Update Template from file
    print("\n--- Updating Model Armor Template from model-armor/template.json ---")
    template_id = "permit-guard-template"
    
    # Try multiple possible paths to find the template file
    template_paths = [
        "model-armor/template.json",
        "../model-armor/template.json",
        os.path.join(os.path.dirname(__file__), "..", "model-armor", "template.json")
    ]
    
    template_file = None
    for path in template_paths:
        if os.path.exists(path):
            template_file = path
            break
            
    if not template_file:
        print("Error: model-armor/template.json not found in any of the searched paths.")
        return

    try:
        with open(template_file, "r") as f:
            template_data = json.load(f)
            
        print(f"Loaded template configuration from {template_file}")
        
        # In case the template has projects/YOUR_PROJECT placeholders (common pattern)
        template_str = json.dumps(template_data)
        if "YOUR_PROJECT" in template_str:
            template_str = template_str.replace("YOUR_PROJECT", project_id)
            template_data = json.loads(template_str)
            print("Replaced YOUR_PROJECT placeholders in template.")

    except Exception as e:
        print(f"Error loading template file: {e}")
        return

    ma_template_url = f"https://modelarmor.googleapis.com/v1/projects/{project_id}/locations/{location}/templates/{template_id}"
    
    try:
        # Check if template exists first
        req_check = urllib.request.Request(ma_template_url, headers=headers, method="GET")
        exists = False
        try:
            with urllib.request.urlopen(req_check) as response:
                exists = True
        except:
            pass

        if exists:
            print(f"Updating existing template: {template_id}...")
            req = urllib.request.Request(ma_template_url, data=json.dumps(template_data).encode("utf-8"), headers=headers, method="PATCH")
        else:
            print(f"Creating new template: {template_id}...")
            ma_create_url = f"https://modelarmor.googleapis.com/v1/projects/{project_id}/locations/{location}/templates?templateId={template_id}"
            req = urllib.request.Request(ma_create_url, data=json.dumps(template_data).encode("utf-8"), headers=headers, method="POST")
            
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"Successfully configured Model Armor template: {result.get('name')}")
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Failed to configure template. HTTP Error {e.code}: {e.reason}")
        print(f"Details: {error_body}")
    except Exception as e:
        print(f"Failed to configure template: {e}")

if __name__ == "__main__":
    setup_model_armor_floor_settings()
