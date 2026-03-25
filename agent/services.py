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
from typing import List, Dict, Any

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
from google.adk.tools import load_memory
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent


from google.adk.integrations.agent_registry import AgentRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # Force the GenAI SDK to use Vertex AI endpoints for ADC support
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        # Load environment variables
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.docai_processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        self.docai_location = os.getenv("DOCUMENT_AI_LOCATION", "us")
        self.rag_corpus_name = os.getenv("VERTEX_RAG_CORPUS_NAME")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")
        self.reasoning_engine_app_name = os.getenv("REASONING_ENGINE_APP_NAME")

        # Initialize Vertex AI
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
            self.docai_processor_name = self.docai_client.processor_path(self.project_id, self.docai_location, self.docai_processor_id)

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Use Document AI to extract text from a PDF."""
        if not self.docai_client or not self.docai_processor_name:
            logger.warning("Document AI not configured. Returning empty text.")
            return ""

        raw_document = documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf"
        )
        request = documentai.ProcessRequest(
            name=self.docai_processor_name,
            raw_document=raw_document
        )

        result = self.docai_client.process_document(request=request)
        document = result.document
        return document.text

    def retrieve_code_context(self, query: str) -> str:
        """Retrieve relevant context from the Vertex AI RAG Engine."""
        if not self.rag_corpus_name:
            logger.warning("Vertex RAG Corpus not configured. Skipping retrieval.")
            return ""

        try:
            response = rag.retrieval_query(
                rag_resources=[rag.RagResource(rag_corpus=self.rag_corpus_name)],
                text=query,
                similarity_top_k=5,  # Optional
            )

            # Extract text from retrieved chunks
            if hasattr(response, "contexts") and hasattr(response.contexts, "contexts"):
                return "".join(context_item.text + "\n\n" for context_item in response.contexts.contexts)
            return ""
        except Exception as e:
             logger.error(f"Failed to retrieve context from RAG: {e}")
             return ""

    async def analyze_plan_with_gemini(self, extracted_text: str, pdf_bytes: bytes) -> Dict[str, Any]:
        """Use Gemini to analyze the plan and the images (multimodal) against the building codes."""
        if not self.project_id:
             logger.warning("GCP Project ID not configured. Using fallback mock response.")
             return self._get_mock_response()

        # Combine the text extraction and multimodal capability of Gemini
        # We pass the PDF directly to Gemini as a Part to analyze diagrams
        try:
             # Create a prompt that asks the model to output structured data
             prompt = """
             You are an expert Building Code Compliance Inspector for San Paloma County, California.
             Review the provided building plan PDF document (which may contain text and architectural drawings).

             Check the plans against the California Building Standards Code (Title 24) and San Paloma County specific local reach codes (like CalGreen and All-Electric requirements).

             Analyze the document to identify:
             1. Elements that comply with the codes and are approved.
             2. Elements that violate the codes or need changes. For each violation, specify the exact code section (e.g. "CA Title 24, Part 6, Section 150.0"), describe the issue, and provide a suggestion for fixing it.

             You have access to a tool to search past conversation memories. Use it to refer back to past discussions or previously noted violations if they are relevant to the current analysis.
             """

             # You can optionally pass retrieved RAG context here as well:
             rag_context = self.retrieve_code_context("building code requirements " + extracted_text[:1000])
             if rag_context:
                 prompt += f"\n\nHere is relevant code context to reference:\n{rag_context}"

             async def auto_save_session_to_memory_callback(callback_context):
                 await callback_context._invocation_context.memory_service.add_session_to_memory(
                     callback_context._invocation_context.session
                 )

             registry = AgentRegistry(project_id=self.project_id, location=self.location)
             servers = registry.list_mcp_servers(filter_str="displayName:'Assessor MCP Server'").get("mcpServers", [])
             mcp_server_name = None
             if servers:
                mcp_server_name = servers[0].get("name")

             if not mcp_server_name:
                 raise ValueError("Assessor MCP Server not found in Agent Registry")

             mcp_toolset = registry.get_mcp_toolset(mcp_server_name)

             # Lookup ContractorAgent
             agents_list = registry.list_agents(filter_str="displayName:'ContractorAgent'").get("agents", [])
             contractor_agent = None
             if agents_list:
                contractor_agent = registry.get_remote_a2a_agent(agents_list[0].get("name"))

             if not contractor_agent:
                 raise ValueError("ContractorAgent not found in Agent Registry")

             agent = LlmAgent(
                 name="plan_analyzer",
                 model=self.model_name,
                 instruction=prompt,
                 tools=[load_memory, mcp_toolset],
                 sub_agents=[contractor_agent],
                 output_schema=PlanAnalysisResponse,
                 after_agent_callback=auto_save_session_to_memory_callback
             )

             # Create runner with Vertex AI Memory and Session Stores
             # Assuming a default engine ID or creating one if needed for the app
             agent_engine_id = self.reasoning_engine_app_name.split('/')[-1]
             session_service = VertexAiSessionService(self.project_id, self.location, agent_engine_id=agent_engine_id)
             runner = Runner(
                 app_name=self.reasoning_engine_app_name,
                 agent=agent,
                 session_service=session_service,
                 memory_service=VertexAiMemoryBankService(agent_engine_id=agent_engine_id)
             )

             # Create the document part
             pdf_part = Part(inline_data=Blob(data=pdf_bytes, mime_type="application/pdf"))

             # Run the agent
             new_message = Content(
                 role="user",
                 parts=[
                     Part(text="Please analyze the attached building plan document."),
                     pdf_part
                 ]
             )

             # Use existing session or create a new one
             list_sessions_response = await session_service.list_sessions(app_name=self.reasoning_engine_app_name, user_id="default_user")

             if list_sessions_response.sessions:
                 # Use the first available session
                 session = list_sessions_response.sessions[0]
             else:
                 # Create a new session
                 session = await session_service.create_session(app_name=self.reasoning_engine_app_name, user_id="default_user")

             final_text = ""
             # Run asynchronously
             async for event in runner.run_async(user_id="default_user", session_id=session.id, new_message=new_message):
                 # Accumulate text from events
                 if hasattr(event, 'text') and event.text:
                     final_text += event.text
                 elif isinstance(event, str):
                     final_text += event
                 elif hasattr(event, 'content') and event.content and event.content.parts:
                     for part in event.content.parts:
                         if part.text:
                            final_text += part.text

             if not final_text:
                  logger.error("No response text received from agent.")
                  return self._get_mock_response()

             try:
                 # Improved JSON extraction matching the user sample pattern
                 cleaned_text = final_text.strip()

                 # Try to find JSON block if mixed with other text
                 json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                 if json_match:
                     potential_json = json_match.group(0)
                     try:
                         return json.loads(potential_json)
                     except json.JSONDecodeError:
                         pass

                 # Markdown cleanup fallback
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
            logger.warning("GCP Project ID not configured. Using fallback chat response.")
            return "This is a mock response. Please configure GCP Project ID to use the agent."

        try:
            # We don't use VertexAiMemoryBankService's full memory logic here directly,
            # because the frontend will send the conversation history in `request.messages`.
            # We construct a prompt with context and pass it to the agent.

            system_instruction = """
            You are a helpful assistant specialized in building codes for San Paloma County.
            You are helping a user understand a specific building plan violation and how to fix it.
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

            # Setup A2A contractor agent call
            # Setup A2A contractor agent call from Registry
            registry = AgentRegistry(project_id=self.project_id, location=self.location)
            agents_list = registry.list_agents()
            contractor_agent = None
            for a in agents_list.get("agents", []):
                if a.get("displayName") == "ContractorAgent":
                    logger.info(f"Found ContractorAgent: {a['name']}")
                    contractor_agent = registry.get_remote_a2a_agent(a["name"])
                    break

            if not contractor_agent:
                raise ValueError("ContractorAgent not found in Agent Registry")

            agent = LlmAgent(
                name="chat_analyzer",
                model=self.model_name,
                instruction=system_instruction,
                sub_agents=[contractor_agent]
            )

            agent_engine_id = self.reasoning_engine_app_name.split('/')[-1] if self.reasoning_engine_app_name else "default-engine"
            session_service = VertexAiSessionService(self.project_id, self.location, agent_engine_id=agent_engine_id)

            runner = Runner(
                app_name=self.reasoning_engine_app_name or "default-app",
                agent=agent,
                session_service=session_service,
                memory_service=VertexAiMemoryBankService(agent_engine_id=agent_engine_id)
            )

            # Build the conversation history
            # The last message is the new user input
            new_user_message_text = request.messages[-1].content if request.messages else ""

            # Use existing session or create a new one
            list_sessions_response = await session_service.list_sessions(app_name=self.reasoning_engine_app_name or "default-app", user_id="default_user")

            if list_sessions_response.sessions:
                # Use the first available session
                session = list_sessions_response.sessions[0]
            else:
                # Create a new session
                session = await session_service.create_session(app_name=self.reasoning_engine_app_name or "default-app", user_id="default_user")

            # Just passing the last user message as new_message and trusting ADK memory / context.
            # However, for simplicity and adherence to standard OpenAI payload:
            history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages[:-1]])
            if history_text:
                new_user_message_text = f"Previous conversation:\n{history_text}\n\nNew message:\n{new_user_message_text}"

            new_message = Content(
                 role="user",
                 parts=[Part(text=new_user_message_text)]
            )

            final_text = ""
            async for event in runner.run_async(user_id="default_user", session_id=session.id, new_message=new_message):
                 if hasattr(event, 'text') and event.text:
                     final_text += event.text
                 elif isinstance(event, str):
                     final_text += event
                 elif hasattr(event, 'content') and event.content and event.content.parts:
                     for part in event.content.parts:
                         if part.text:
                            final_text += part.text

            return final_text.strip() if final_text else "I am sorry, I couldn't generate a response."

        except Exception as e:
             logger.error(f"Error during Gemini chat: {e}")
             return f"Error communicating with agent: {str(e)}"

    def _get_mock_response(self) -> Dict[str, Any]:
         return {
            "status": "Changes Suggested",
            "violations": [
                {
                    "section": "Mock CA Title 24, Part 6, Section 150.0(e)",
                    "description": "Mock failure: Lighting requirement not met.",
                    "suggestion": "Update lighting plan to use LED fixtures."
                }
            ],
            "approved_elements": ["Structural framing", "Plumbing layout"]
        }

# Singleton instance
ai_service = AIService()
