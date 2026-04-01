import os
import json
import urllib.request
import urllib.error
import subprocess

def run_command(command, ignore_errors=False):
    """Executes a shell command and returns the output."""
    try:
        result = subprocess.run(
            command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if not ignore_errors:
            print(f"Error executing command: {command}")
            print(e.stderr)
            exit(1)
        return e.stderr.strip()

def setup_model_armor():
    project_id = run_command("gcloud config get-value project")
    location = run_command("gcloud config get-value compute/region")
    
    if not project_id:
        print("Error: Could not determine Project ID. Please set it using 'gcloud config set project <PROJECT_ID>'")
        exit(1)
    if not location:
        location = "us-central1"
        print(f"Warning: Could not determine compute/region. Defaulting to {location}.")

    print(f"Using Project ID: {project_id}")
    print(f"Using Location: {location}")

    # 1. Create DLP Inspect Template
    print("\n--- Creating DLP Inspect Template ---")
    dlp_template_id = "permit-liability-guard"

    dlp_payload = {
      "inspectTemplate": {
        "displayName": "Liability Masking Template",
        "description": "Masks legal liability phrases for building permit bot.",
        "inspectConfig": {
          "customInfoTypes": [
            {
              "infoType": {
                "name": "LEGAL_LIABILITY_PHRASES"
              },
              "dictionary": {
                "wordList": {
                  "words": [
                    "legally guarantee",
                    "legally binding",
                    "certified engineering advice",
                    "assume all liability",
                    "waive inspection",
                    "override the human inspector",
                    "cannot be rejected"
                  ]
                }
              }
            }
          ]
        }
      },
      "templateId": dlp_template_id
    }

    token = run_command("gcloud auth application-default print-access-token", ignore_errors=True)
    if token:
        dlp_url = f"https://dlp.googleapis.com/v2/projects/{project_id}/locations/{location}/inspectTemplates"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id
        }
        
        # Check if exists
        req_list = urllib.request.Request(f"{dlp_url}/{dlp_template_id}", headers=headers, method="GET")
        dlp_exists = False
        try:
            with urllib.request.urlopen(req_list) as response:
                dlp_exists = True
                print(f"DLP Inspect Template '{dlp_template_id}' already exists.")
        except Exception:
            pass

        if not dlp_exists:
            print(f"Creating DLP Inspect Template: {dlp_template_id}...")
            req_create = urllib.request.Request(dlp_url, data=json.dumps(dlp_payload).encode("utf-8"), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req_create) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    print(f"Successfully created DLP Inspect template: {result.get('name')}")
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                print(f"Failed to create DLP Inspect template. HTTP Error {e.code}: {e.reason}")
                print(f"Details: {error_body}")
            except Exception as e:
                print(f"Failed to create DLP Inspect template: {e}")
    else:
        print("Warning: Could not fetch auth token. Skipping DLP Inspect template creation.")

    # 2. Create Model Armor Template
    print("\n--- Creating Model Armor Template ---")
    model_armor_location = location
    model_armor_template_id = "permit-guard-template"

    ma_command = (
        f"gcloud config set api_endpoint_overrides/modelarmor https://modelarmor.{model_armor_location}.rep.googleapis.com/ && "
        f"gcloud alpha model-armor templates create {model_armor_template_id} "
        f"--project={project_id} --location={model_armor_location} "
        f"--rai-settings-filters='[{{ \"filterType\": \"HATE_SPEECH\", \"confidenceLevel\": \"MEDIUM_AND_ABOVE\" }},{{ \"filterType\": \"HARASSMENT\", \"confidenceLevel\": \"MEDIUM_AND_ABOVE\" }},{{ \"filterType\": \"SEXUALLY_EXPLICIT\", \"confidenceLevel\": \"MEDIUM_AND_ABOVE\" }}]' "
        f"--pi-and-jailbreak-filter-settings-enforcement=enabled "
        f"--pi-and-jailbreak-filter-settings-confidence-level=LOW_AND_ABOVE "
        f"--malicious-uri-filter-settings-enforcement=enabled "
        f"--template-metadata-custom-llm-response-safety-error-code=798 "
        f"--template-metadata-custom-llm-response-safety-error-message=\"test template llm response evaluation failed\" "
        f"--template-metadata-custom-prompt-safety-error-code=799 "
        f"--template-metadata-custom-prompt-safety-error-message=\"test template prompt evaluation failed\" "
        f"--template-metadata-ignore-partial-invocation-failures "
        f"--template-metadata-log-operations "
        f"--template-metadata-log-sanitize-operations "
        f"--advanced-config-inspect-template=\"projects/{project_id}/locations/{location}/inspectTemplates/permit-liability-guard\""
    )

    out = run_command(ma_command, ignore_errors=True)
    
    # We should unset the override after to not pollute global state
    run_command("gcloud config unset api_endpoint_overrides/modelarmor", ignore_errors=True)

    if out is None:
        print(f"Failed to create Model Armor template. Please check your command and gcloud configuration.")
    elif "Failed to create" in out or "ERROR:" in out:
        if "already exists" in out or "ALREADY_EXISTS" in out:
            print(f"Model Armor template '{model_armor_template_id}' already exists.")
        else:
            print(f"Failed to create Model Armor template. Details:\n{out}")
    else:
        print(f"Successfully created Model Armor template: {model_armor_template_id}")

if __name__ == "__main__":
    setup_model_armor()
