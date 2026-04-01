import os
import logging

try:
    from google.cloud import modelarmor_v1
    from google.cloud.modelarmor_v1.types import DataItem, SanitizeUserPromptRequest
    from google.api_core.exceptions import GoogleAPIError
except ImportError:
    modelarmor_v1 = None

logger = logging.getLogger(__name__)

class ModelArmorBlockError(Exception):
    """Raised when Model Armor blocks the input due to a policy violation."""
    pass

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

        result = response.sanitization_result
        if not result:
            return text

        # Check for matched filters indicating a blocked state
        matched_filters = []
        if hasattr(result, "filter_results") and result.filter_results:
             for filter_name, filter_result in result.filter_results.items():
                 # Check if this specific filter triggered a match
                 if hasattr(filter_result, "match_state") and filter_result.match_state.name == "MATCH_FOUND":
                     matched_filters.append(filter_name.lower())

        # You could also check result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND

        if matched_filters:
            logger.warning(f"Model Armor blocked input. Threats detected: {matched_filters}")

            # Create user-friendly message based on threat type, tuned to the permit-guard-template
            if 'pi_and_jailbreak' in matched_filters:
                message = (
                    "I apologize, but I cannot process this request. "
                    "Your message appears to contain instructions that could "
                    "compromise my safety guidelines or attempt a prompt injection. Please rephrase your question."
                )
            elif 'sdp' in matched_filters or 'custom_pii' in matched_filters or any('legal_liability' in f for f in matched_filters):
                message = (
                    "I apologize, but I cannot process this request. "
                    "Your message contains sensitive information or attempts to solicit "
                    "legal guarantees. I cannot provide legal liability or certify engineering advice. "
                    "Please rephrase your question."
                )
            elif any(f.startswith('rai') for f in matched_filters):
                message = (
                    "I apologize, but I cannot respond to this type of request. "
                    "Please rephrase your question in a respectful manner, and "
                    "I'll be happy to help."
                )
            else:
                message = (
                    "I apologize, but I cannot process this request due to "
                    "security or policy concerns. Please rephrase your question."
                )

            raise ModelArmorBlockError(message)

        if result.sanitize_data_item:
             return result.sanitize_data_item.text

        # If no sanitized data is returned and no blocks occurred, return the original text
        return text

    except GoogleAPIError as e:
        logger.error(f"Google API Error calling Model Armor: {e}")
        return text
    except Exception as e:
        logger.error(f"Unexpected error calling Model Armor: {e}")
        return text
