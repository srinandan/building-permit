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
import json
import logging
import re
from typing import Dict, Any

from google.cloud import documentai
from pydantic import BaseModel, Field
from google.cloud import aiplatform
import vertexai
from vertexai.preview import rag
from google.genai.types import Part, Content, Blob
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import VertexAiSessionService
from google.adk.memory import VertexAiMemoryBankService
from google.adk.tools import load_memory, FunctionTool

from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from a2a.client import ClientConfig, ClientFactory
from a2a.types import TransportProtocol

from opentelemetry.propagate import inject
from google.adk.integrations.agent_registry import AgentRegistry

from google.adk.plugins.bigquery_agent_analytics_plugin import (
    BigQueryAgentAnalyticsPlugin,
    BigQueryLoggerConfig,
)
from google.cloud import bigquery

import pypdf
import io
from model_armor import sanitize_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize BigQuery Analytics
_plugins = []
_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
_dataset_id = os.environ.get("BQ_ANALYTICS_DATASET_ID", "adk_agent_analytics")
_location = os.environ.get("BQ_ANALYTICS_DATASET_LOCATION", "us")

if _project_id:
    try:
        bq = bigquery.Client(project=_project_id)
        bq.create_dataset(f"{_project_id}.{_dataset_id}", exists_ok=True)

        _plugins.append(
            BigQueryAgentAnalyticsPlugin(
                project_id=_project_id,
                dataset_id=_dataset_id,
                location=_location,
                config=BigQueryLoggerConfig(
                    gcs_bucket_name=os.environ.get("BQ_ANALYTICS_GCS_BUCKET"),
                    connection_id=os.environ.get("BQ_ANALYTICS_CONNECTION_ID"),
                ),
            )
        )
    except Exception as e:
        logging.warning(f"Failed to initialize BigQuery Analytics: {e}")


def otel_header_provider(context) -> dict[str, str]:
    headers = {}
    inject(headers)
    return headers


class Violation(BaseModel):
    section: str
    description: str
    suggestion: str


class PlanAnalysisResponse(BaseModel):
    status: str = Field(description="Approved | Changes Suggested | Rejected")
    violations: list[Violation]
    approved_elements: list[str]


class AIService:
    def __init__(self):
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.docai_processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        self.docai_location = os.getenv("DOCUMENT_AI_LOCATION", "us")
        self.rag_corpus_name = os.getenv("VERTEX_RAG_CORPUS_NAME")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")
        self.reasoning_engine_app_name = os.getenv("REASONING_ENGINE_APP_NAME")

        if self.project_id:
            try:
                vertexai.init(project=self.project_id, location=self.location)
                logger.info(f"Initialized Vertex AI for project {self.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI: {e}")
        else:
            logger.warning("GOOGLE_CLOUD_PROJECT not set. GCP services will not work.")

        # Initialize Document AI
        self.docai_client = None
        self.docai_processor_name = None
        if self.project_id and self.docai_processor_id:
            client_options = {"api_endpoint": f"{self.docai_location}-documentai.googleapis.com"}
            self.docai_client = documentai.DocumentProcessorServiceClient(client_options=client_options)
            self.docai_processor_name = self.docai_client.processor_path(
                self.project_id, self.docai_location, self.docai_processor_id
            )

        # Find Registry Assets
        self.registry = AgentRegistry(
            project_id=self.project_id,
            location=self.location,
            header_provider=otel_header_provider,
        )
        servers = self.registry.list_mcp_servers(
            filter_str="displayName:assessor-mcp-server", page_size=1
        )
        mcp_server_name = servers.get("mcpServers", [])[0]["name"]

        if not mcp_server_name:
            raise ValueError("Assessor MCP Server not found in Agent Registry")

        logger.info(f"Found assessor-mcp-server: {mcp_server_name}")
        self.mcp_server_name = mcp_server_name
        self.mcp_toolset = self.registry.get_mcp_toolset(mcp_server_name)

        agents_list = self.registry.list_agents(
            filter_str="displayName:building_permit_contractor_agent", page_size=1
        )
        a2a_server_name = agents_list.get("agents", [])[0]["name"]

        if not a2a_server_name:
            raise ValueError("building_permit_contractor_agent not found in Agent Registry")

        logger.info(f"Found building_permit_contractor_agent: {a2a_server_name}")
        self.contractor_agent_name = a2a_server_name

        # Build the RAG retrieval FunctionTool
        # -----------------------------------------------------------------------
        # WHY FunctionTool instead of VertexAiRagRetrieval?
        #
        # VertexAiRagRetrieval is implemented as a Vertex AI *grounding* config.
        # The Gemini API rejects grounding tools the moment the request contains
        # any non-text Part (e.g. inline PDF bytes), raising:
        #   "grounding is not supported non-text input"
        #
        # FunctionTool wraps a plain Python coroutine and is invoked through the
        # model's *function-calling* mechanism instead.  Function calling works
        # fine alongside multimodal content, so the PDF + RAG combination works.
        #
        # From the agent's perspective the behaviour is identical: it chooses
        # when to call the tool and what query to pass.
        # -----------------------------------------------------------------------
        self.rag_function_tool = None
        if self.rag_corpus_name:
            self.rag_function_tool = self._build_rag_function_tool(self.rag_corpus_name)
            logger.info(f"RAG FunctionTool initialised for corpus: {self.rag_corpus_name}")
        else:
            logger.warning("VERTEX_RAG_CORPUS_NAME not set — agent will have no building-code knowledge.")

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Use Document AI to extract text from a PDF.

        NOTE: Document AI extraction is still useful here as a pre-processing
        step — it gives cleaner structured text from scanned/complex PDFs.
        However, it should NOT be used to drive the RAG query directly.
        """
        if not self.docai_client or not self.docai_processor_name:
            logger.warning("Document AI not configured. Returning empty text.")
            return ""

        raw_document = documentai.RawDocument(content=pdf_bytes, mime_type="application/pdf")
        request = documentai.ProcessRequest(
            name=self.docai_processor_name, raw_document=raw_document
        )
        result = self.docai_client.process_document(request=request)
        return result.document.text

    @staticmethod
    def _build_rag_function_tool(rag_corpus_name: str) -> FunctionTool:
        """Return a FunctionTool that queries the RAG corpus via function calling.

        Using FunctionTool (function-calling) instead of VertexAiRagRetrieval
        (grounding) is necessary because the Gemini API does not allow grounding
        tools in the same request as non-text content such as inline PDF bytes.
        Function calling has no such restriction.
        """

        async def retrieve_california_building_codes(query: str) -> str:
            """Search the California Building Standards Code (Title 24) and Santa Clara
            County local reach codes (CalGreen, All-Electric requirements) for specific
            requirements, thresholds, and code sections.

            Use targeted queries such as:
              - "CA Title 24 Part 6 Section 150.0 residential lighting efficacy"
              - "CalGreen mandatory measures new residential construction"
              - "All-electric reach code panel sizing"

            Always call this tool before citing a violation or approving an element.

            Args:
                query: Specific building code topic or section to look up.

            Returns:
                Relevant excerpts from the California Building Standards Code corpus,
                separated by "---". Returns a not-found message if no chunks match.
            """
            try:
                response = rag.retrieval_query(
                    rag_resources=[rag.RagResource(rag_corpus=rag_corpus_name)],
                    text=query,
                    similarity_top_k=10,
                    vector_distance_threshold=0.5,
                )
                if (
                    hasattr(response, "contexts")
                    and hasattr(response.contexts, "contexts")
                    and response.contexts.contexts
                ):
                    chunks = [
                        ctx.text
                        for ctx in response.contexts.contexts
                        if ctx.text and ctx.text.strip()
                    ]
                    if chunks:
                        return "\n\n---\n\n".join(chunks)
                return "No relevant code sections found for this query."
            except Exception as e:
                logger.error(f"RAG retrieval error for query '{query}': {e}")
                return f"Error retrieving building codes: {e}"

        return FunctionTool(func=retrieve_california_building_codes)

    async def analyze_plan_with_gemini(
        self, extracted_text: str, pdf_bytes: bytes
    ) -> Dict[str, Any]:
        """Use Gemini + RAG FunctionTool to analyse the plan against building codes."""
        if not self.project_id:
            logger.warning("GCP Project ID not configured. Using fallback mock response.")
            return self._get_mock_response()

        try:
            # ---------------------------------------------------------
            # The system prompt now explicitly instructs the agent to USE the
            # RAG tool.  Previously the prompt said "You have access to a tool
            # to search past conversation memories" — that describes load_memory,
            # not the building-codes corpus, so the agent had no idea RAG existed.
            # -----------------------------------------------------------------
            prompt = """
You are an expert Building Code Compliance Inspector for Santa Clara County, California.

You have access to two key tools:
1. **retrieve_california_building_codes** — searches the California Building Standards Code
   (Title 24) and Santa Clara County local reach codes (CalGreen, All-Electric requirements).
   You MUST call this tool to look up specific requirements before citing a violation
   or approving an element.  Make multiple targeted calls — one per code area you are
   checking (e.g. lighting, insulation, HVAC, electrical panel sizing, CalGreen prerequisites).

2. **load_memory** — retrieves relevant notes from past review sessions with this user.
   Use it to cross-reference previously flagged issues on related permits.

Workflow:
  Step 1  Visually inspect the attached building-plan PDF to identify all systems and
          elements present (structural, mechanical, electrical, plumbing, energy, etc.).
  Step 2  For each element, call retrieve_california_building_codes with a precise query
          (e.g. "CA Title 24 Part 6 Section 150 residential lighting efficacy requirements").
  Step 3  Compare what you retrieved against what the plan shows.  Flag discrepancies.
  Step 4  Produce your final answer as a JSON object matching EXACTLY this structure:

{
  "status": "Approved | Changes Suggested | Rejected",
  "violations": [
    {"section": "CA Title 24, Part 6, Section 150.0(k)",
     "description": "...",
     "suggestion": "..."}
  ],
  "approved_elements": ["..."]
}

Output ONLY the JSON object, with no preamble or markdown fences.
"""
            # -----------------------------------------------------------------
            # Build the tools list conditionally.  The rag_function_tool is the
            # primary knowledge source; load_memory is the session-history source.
            # They are different things and must both be present.
            # -----------------------------------------------------------------
            agent_tools = [load_memory]
            if self.rag_function_tool:
                agent_tools.append(self.rag_function_tool)
            else:
                logger.warning(
                    "RAG tool unavailable — agent will rely only on its parametric knowledge, "
                    "which may be incomplete or out of date."
                )
            agent_tools.append(self.mcp_toolset)

            async def auto_save_session_to_memory_callback(callback_context):
                await callback_context._invocation_context.memory_service.add_session_to_memory(
                    callback_context._invocation_context.session
                )

            agent = LlmAgent(
                name="plan_analyzer",
                model=self.model_name,
                instruction=prompt,
                tools=agent_tools,
                sub_agents=[self.registry.get_remote_a2a_agent(self.contractor_agent_name)],
                after_agent_callback=auto_save_session_to_memory_callback,
            )

            agent_engine_id = self.reasoning_engine_app_name.split("/")[-1]
            session_service = VertexAiSessionService(
                self.project_id, self.location, agent_engine_id=agent_engine_id
            )
            runner = Runner(
                app_name=self.reasoning_engine_app_name,
                agent=agent,
                session_service=session_service,
                memory_service=VertexAiMemoryBankService(agent_engine_id=agent_engine_id),
                plugins=_plugins,
            )

            # -----------------------------------------------------------------
            # Combine user prompt components for sanitisation via Model Armor
            # -----------------------------------------------------------------
            base_prompt = "Please analyse the attached building plan document for compliance."
            combined_text = base_prompt

            if extracted_text and extracted_text.strip():
                combined_text += f"\n\nExtracted Text:\n{extracted_text[:8000]}"

            try:
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                metadata = reader.metadata
                if metadata:
                    meta_text = "\n".join([f"{k}: {v}" for k, v in metadata.items() if v])
                    if meta_text:
                        combined_text += f"\n\nPDF Metadata:\n{meta_text}"
            except Exception as e:
                logger.warning(f"Failed to extract PDF metadata: {e}")

            # Sanitize the combined text prompt
            sanitized_text = sanitize_text(combined_text)

            pdf_part = Part(inline_data=Blob(data=pdf_bytes, mime_type="application/pdf"))

            user_content_parts = [
                Part(text=sanitized_text),
                pdf_part,
            ]

            new_message = Content(role="user", parts=user_content_parts)

            list_sessions_response = await session_service.list_sessions(
                app_name=self.reasoning_engine_app_name, user_id="default_user"
            )

            if list_sessions_response.sessions:
                session = list_sessions_response.sessions[0]
            else:
                session = await session_service.create_session(
                    app_name=self.reasoning_engine_app_name, user_id="default_user"
                )

            final_text = ""
            async for event in runner.run_async(
                user_id="default_user",
                session_id=session.id,
                new_message=new_message,
            ):
                if hasattr(event, "text") and event.text:
                    final_text += event.text
                elif isinstance(event, str):
                    final_text += event
                elif hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text += part.text

            if not final_text:
                logger.error("No response text received from agent.")
                return self._get_mock_response()

            self.mcp_toolset.close()

            # JSON extraction (unchanged from original)
            try:
                cleaned_text = final_text.strip()
                json_match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        logger.debug("Regex-matched JSON block failed to parse.")

                if "```json" in cleaned_text:
                    cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
                elif "```" in cleaned_text:
                    cleaned_text = cleaned_text.split("```")[1].split("```")[0]

                return json.loads(cleaned_text.strip())
            except Exception as e:
                logger.error(f"Error parsing agent response: {e}. Raw: {final_text}")
                return self._get_mock_response()

        except Exception as e:
            logger.error(f"Error during Gemini analysis: {e}")
            return self._get_mock_response()

    async def chat_about_violation(self, request: Any) -> str:
        """Handle chat interactions about a specific violation."""
        if not self.project_id:
            return "This is a mock response. Please configure GCP Project ID to use the agent."

        try:
            system_instruction = """
You are a helpful assistant specialised in building codes for Santa Clara County.
You are helping a user understand a specific building plan violation and how to fix it.

You have access to retrieve_california_building_codes to look up the exact code text,
acceptable alternative compliance paths, and prescriptive measures that would resolve
the violation.  Always retrieve the relevant section before advising the user.
"""
            context = ""
            if request.permit_id:
                context += f"Permit ID: {request.permit_id}\n"
            if request.violation:
                context += f"Violation Section: {request.violation.section}\n"
                context += f"Description: {request.violation.description}\n"
                context += f"Suggestion: {request.violation.suggestion}\n"

            if context:
                system_instruction += f"\nContext regarding the violation:\n{context}\n"

            # -----------------------------------------------------------------
            # Give the chat agent the RAG tool too so it can look up code details
            # when answering follow-up questions.  Previously the chat agent had
            # no access to the corpus at all.
            # -----------------------------------------------------------------
            chat_tools = []
            if self.rag_function_tool:
                chat_tools.append(self.rag_function_tool)

            agent = LlmAgent(
                name="chat_analyzer",
                model=self.model_name,
                instruction=system_instruction,
                tools=chat_tools,
                sub_agents=[self.registry.get_remote_a2a_agent(self.contractor_agent_name)],
            )

            agent_engine_id = (
                self.reasoning_engine_app_name.split("/")[-1]
                if self.reasoning_engine_app_name
                else "default-engine"
            )
            session_service = VertexAiSessionService(
                self.project_id, self.location, agent_engine_id=agent_engine_id
            )
            runner = Runner(
                app_name=self.reasoning_engine_app_name or "default-app",
                agent=agent,
                session_service=session_service,
                memory_service=VertexAiMemoryBankService(agent_engine_id=agent_engine_id),
                plugins=_plugins,
            )

            new_user_message_text = request.messages[-1].content if request.messages else ""

            list_sessions_response = await session_service.list_sessions(
                app_name=self.reasoning_engine_app_name or "default-app",
                user_id="default_user",
            )

            if list_sessions_response.sessions:
                session = list_sessions_response.sessions[0]
            else:
                session = await session_service.create_session(
                    app_name=self.reasoning_engine_app_name or "default-app",
                    user_id="default_user",
                )

            history_text = "\n".join(
                [f"{msg.role}: {msg.content}" for msg in request.messages[:-1]]
            )
            if history_text:
                new_user_message_text = (
                    f"Previous conversation:\n{history_text}\n\nNew message:\n{new_user_message_text}"
                )

            new_message = Content(role="user", parts=[Part(text=new_user_message_text)])

            final_text = ""
            async for event in runner.run_async(
                user_id="default_user",
                session_id=session.id,
                new_message=new_message,
            ):
                if hasattr(event, "text") and event.text:
                    final_text += event.text
                elif isinstance(event, str):
                    final_text += event
                elif hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text += part.text

            return final_text.strip() if final_text else "I am sorry, I couldn't generate a response."

        except Exception as e:
            logger.error(f"Error during Gemini chat: {e}")
            return f"Error communicating with agent: {str(e)}"

    def get_remote_a2a_agent(self) -> RemoteA2aAgent:
        contractor_agent_url = os.getenv(
            "CONTRACTOR_AGENT_URL",
            "http://0.0.0.0:8081/a2a/building_permit_contractor_agent/.well-known/agent-card.json",
        )
        client_factory = ClientFactory(
            ClientConfig(
                supported_transports=[TransportProtocol.http_json, TransportProtocol.jsonrpc],
                use_client_preference=True,
            )
        )
        return RemoteA2aAgent(
            name="building_permit_contractor_agent",
            description=(
                "An agent that helps find licensed contractors for specific jobs in a given area. "
                "Use this agent when the user asks for help finding a contractor."
            ),
            agent_card=f"{contractor_agent_url}",
            a2a_client_factory=client_factory,
        )

    def get_assessor_mcp_server(self) -> McpToolset:
        assessor_mcp_server_url = os.getenv("ASSESSOR_MCP_SERVER_URL", "http://0.0.0.0:8002")
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=assessor_mcp_server_url),
            header_provider=otel_header_provider,
        )

    def _get_mock_response(self) -> Dict[str, Any]:
        return {
            "status": "Changes Suggested",
            "violations": [
                {
                    "section": "Mock CA Title 24, Part 6, Section 150.0(e)",
                    "description": "Mock failure: Lighting requirement not met.",
                    "suggestion": "Update lighting plan to use LED fixtures.",
                }
            ],
            "approved_elements": ["Structural framing", "Plumbing layout"],
        }


# Singleton instance
ai_service = AIService()