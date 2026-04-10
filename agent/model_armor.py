import os
import json
import logging
from typing import Optional

try:
    from google.cloud import modelarmor_v1
    from google.cloud.modelarmor_v1.types import DataItem, SanitizeUserPromptRequest
    from google.api_core.exceptions import GoogleAPIError
except ImportError:
    modelarmor_v1 = None

from google.adk.agents.context import Context
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

logger = logging.getLogger(__name__)

class ModelArmorGuard:
    def __init__(self, template_name: str, block_on_match: bool = True):
        self.template_name = template_name
        self.block_on_match = block_on_match
        self.client = None
        if modelarmor_v1:
            try:
                self.client = modelarmor_v1.ModelArmorClient()
            except Exception as e:
                logger.error(f"Failed to initialize Model Armor client: {e}")

    def _get_matched_filters(self, result: modelarmor_v1.SanitizeUserPromptResponse) -> list[str]:
        matched_filters = []
        if not hasattr(result, "filter_results") or not result.filter_results:
            return matched_filters

        for filter_name, filter_obj in result.filter_results.items():
            # Check standard match state
            if hasattr(filter_obj, 'match_state') and filter_obj.match_state.name == 'MATCH_FOUND':
                matched_filters.append(filter_name.lower())

            # Special handling for SDP
            elif filter_name == 'sdp' and hasattr(filter_obj, 'inspect_result'):
                if hasattr(filter_obj.inspect_result, 'match_state'):
                    if filter_obj.inspect_result.match_state.name == 'MATCH_FOUND':
                        matched_filters.append('sdp')

            # Special handling for RAI
            elif filter_name == 'rai':
                if hasattr(filter_obj, 'rai_filter_type_results'):
                    for sub_result in filter_obj.rai_filter_type_results:
                        if hasattr(sub_result, 'value') and hasattr(sub_result.value, 'match_state'):
                            if sub_result.value.match_state.name == 'MATCH_FOUND':
                                matched_filters.append(f"rai:{getattr(sub_result, 'key', 'unknown')}")

        return matched_filters

    def _extract_user_text(self, llm_request: LlmRequest) -> str:
        """Extract the user's text from the LLM request.
        We only want the text from the actual user content parts, skipping
        the first part which is our system preamble 'Please analyse the attached...'
        """
        user_text_fragments = []
        try:
            if llm_request.contents:
                for content in reversed(llm_request.contents):
                    if content.role == "user":
                        # Skip the first text part which is the hardcoded "Please analyse..." instruction
                        # We only extract the dynamic Extracted Text and PDF Metadata parts
                        for i, part in enumerate(content.parts):
                            if hasattr(part, 'text') and part.text:
                                if i == 0 and "Please analyse the attached building plan" in part.text:
                                    continue
                                user_text_fragments.append(part.text)
                        break
        except Exception as e:
            logger.error(f"Error extracting user text: {e}")

        return "\n".join(user_text_fragments)

    async def before_model_callback(
            self,
            context: Context,
            llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """
        Callback called BEFORE the LLM processes the request.
        """
        if os.getenv("ENABLE_MODEL_ARMOR", "").lower() != "true":
            logger.info("Model Armor is disabled. Skipping sanitisation callback.")
            return None

        if not self.client:
            logger.warning("Model Armor client not initialized. Skipping sanitisation.")
            return None

        user_text = self._extract_user_text(llm_request)
        if not user_text.strip():
            return None

        try:
            sanitize_request = SanitizeUserPromptRequest(
                name=self.template_name,
                user_prompt_data=DataItem(text=user_text),
            )
            result = self.client.sanitize_user_prompt(request=sanitize_request)

            matched_filters = self._get_matched_filters(result.sanitization_result)

            if matched_filters and self.block_on_match:
                logger.warning(f"Model Armor BLOCKED input. Threats detected: {matched_filters}")

                if 'pi_and_jailbreak' in matched_filters:
                    violation_desc = (
                        "Your message appears to contain instructions that could "
                        "compromise safety guidelines or attempt a prompt injection."
                    )
                elif 'sdp' in matched_filters or 'custom_pii' in matched_filters or any('legal_liability' in f for f in matched_filters):
                    violation_desc = (
                        "Your message contains sensitive personal information or attempts to solicit "
                        "legal guarantees. I cannot provide legal liability or certify engineering advice."
                    )
                elif any(f.startswith('rai') for f in matched_filters):
                    violation_desc = (
                        "Your request violates safety constraints regarding respectful and appropriate content."
                    )
                else:
                    violation_desc = "Security or policy concerns detected in the uploaded document."

                # We MUST return the expected JSON output format so the API gateway can parse it
                # PlanAnalysisResponse schema
                rejected_response = {
                    "status": "Rejected",
                    "violations": [
                        {
                            "section": "Security Policy (Model Armor)",
                            "description": violation_desc,
                            "suggestion": "Please review the document to ensure it complies with our safety, PII, and content guidelines."
                        }
                    ],
                    "approved_elements": []
                }

                json_str = json.dumps(rejected_response)

                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=json_str)]
                    )
                )

            # If no blocks, but sanitised data exists, we technically should update the llm_request.
            # However, ADK's before_model_callback currently does not mutate the request directly easily
            # unless we modify the llm_request.contents array in place.
            if result.sanitization_result and result.sanitization_result.sanitize_data_item:
                 sanitized_text = result.sanitization_result.sanitize_data_item.text
                 # Find and replace the user text part
                 if llm_request.contents:
                    for content in reversed(llm_request.contents):
                        if content.role == "user":
                            for i, part in enumerate(content.parts):
                                if hasattr(part, 'text') and part.text and "Please analyse" not in part.text:
                                    part.text = sanitized_text
                            break

        except GoogleAPIError as e:
            logger.error(f"Google API Error calling Model Armor: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling Model Armor: {e}")

        return None

def create_model_armor_guard() -> Optional[ModelArmorGuard]:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4")

    if not project_id:
        logger.warning("GOOGLE_CLOUD_PROJECT is not set. Cannot use Model Armor.")
        return None

    template_name = f"projects/{project_id}/locations/{location}/templates/permit-guard-template"
    return ModelArmorGuard(template_name=template_name)
