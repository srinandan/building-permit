import os
import logging

try:
    from google.cloud import modelarmor_v1
    from google.cloud.modelarmor_v1.types import DataItem, SanitizeUserPromptRequest
    from google.api_core.exceptions import GoogleAPIError
except ImportError:
    modelarmor_v1 = None

logger = logging.getLogger(__name__)

_client = None

def get_client():
    """Lazily initialize and return the Model Armor client."""
    global _client
    if _client is None and modelarmor_v1:
        try:
            _client = modelarmor_v1.ModelArmorClient()
        except Exception as e:
            logger.error(f"Failed to initialize Model Armor client: {e}")
    return _client

def sanitize_text(text: str) -> str:
    """Sanitize the input text using GCP Model Armor."""
    if os.getenv("ENABLE_MODEL_ARMOR", "").lower() != "true":
        logger.info("Model Armor is disabled. Skipping sanitisation.")
        return text

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4")

    if not project_id:
        logger.warning("GOOGLE_CLOUD_PROJECT is not set. Cannot use Model Armor. Skipping.")
        return text

    if not modelarmor_v1:
        logger.warning("google-cloud-modelarmor package is not installed. Skipping Model Armor sanitisation.")
        return text

    template_name = f"projects/{project_id}/locations/{location}/templates/permit-guard-template"

    client = get_client()
    if not client:
        return text

    try:
        request = SanitizeUserPromptRequest(
            name=template_name,
            user_prompt_data=DataItem(
                text=text
            )
        )

        response = client.sanitize_user_prompt(request=request)

        if response.sanitization_result and response.sanitization_result.sanitize_data_item:
             return response.sanitization_result.sanitize_data_item.text

        # If no sanitized data is returned, return the original text
        return text

    except GoogleAPIError as e:
        logger.error(f"Google API Error calling Model Armor: {e}")
        return text
    except Exception as e:
        logger.error(f"Unexpected error calling Model Armor: {e}")
        return text
