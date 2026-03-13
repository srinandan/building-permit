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
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

import vertexai
from google.genai.types import Part, Content
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import VertexAiSessionService
from google.adk.memory import VertexAiMemoryBankService
from google.adk.tools import google_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")
reasoning_engine_app_name = os.getenv("REASONING_ENGINE_APP_NAME", "default-app")
agent_engine_id = reasoning_engine_app_name.split('/')[-1] if reasoning_engine_app_name else "default-engine"

# Initialize Vertex AI
if project_id:
    try:
        vertexai.init(project=project_id, location=location)
        logger.info(f"Initialized Vertex AI for project {project_id}")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}")

app = FastAPI(title="Contractor Agent Service")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    permit_id: Optional[str] = None

class ChatChoice(BaseModel):
    message: ChatMessage

class ChatResponse(BaseModel):
    choices: List[ChatChoice]

def create_contractor_agent() -> LlmAgent:
    """Creates an ADK LlmAgent configured to find licensed contractors."""
    system_instruction = """
    You are an expert at finding licensed contractors for specific jobs in a given area.
    Use the google_search tool to find real, highly-rated, licensed contractors that match the user's needs.
    Always provide contact information, a brief description of the contractor, and why they are a good fit for the job.
    If the user asks for contractors in a specific area (like Santa Clara County), focus your search there.
    """

    return LlmAgent(
        name="contractor_agent",
        model=model_name,
        instruction=system_instruction,
        tools=[google_search]
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not project_id:
        logger.warning("GCP Project ID not configured. Using fallback chat response.")
        return ChatResponse(
            choices=[ChatChoice(message=ChatMessage(role="assistant", content="This is a mock response from the contractor agent. Please configure GCP Project ID."))]
        )

    try:
        agent = create_contractor_agent()
        session_service = VertexAiSessionService(project_id, location, agent_engine_id=agent_engine_id)

        runner = Runner(
            app_name=reasoning_engine_app_name or "default-app",
            agent=agent,
            session_service=session_service,
            memory_service=VertexAiMemoryBankService(agent_engine_id=agent_engine_id)
        )

        session_id_suffix = f"-contractor-{request.permit_id}" if request.permit_id else "-contractor-chat"
        list_sessions_response = await session_service.list_sessions(app_name=reasoning_engine_app_name or "default-app", user_id="contractor_user")

        if list_sessions_response.sessions:
            session = list_sessions_response.sessions[0]
        else:
            session = await session_service.create_session(app_name=reasoning_engine_app_name or "default-app", user_id="contractor_user")

        new_user_message_text = request.messages[-1].content if request.messages else ""

        history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages[:-1]])
        if history_text:
            new_user_message_text = f"Previous conversation:\n{history_text}\n\nNew message:\n{new_user_message_text}"

        new_message = Content(
             role="user",
             parts=[Part(text=new_user_message_text)]
        )

        final_text = ""
        async for event in runner.run_async(user_id="contractor_user", session_id=session.id, new_message=new_message):
             if hasattr(event, 'text') and event.text:
                 final_text += event.text
             elif isinstance(event, str):
                 final_text += event
             elif hasattr(event, 'content') and event.content and event.content.parts:
                 for part in event.content.parts:
                     if part.text:
                        final_text += part.text

        response_text = final_text.strip() if final_text else "I am sorry, I couldn't generate a response."

        return ChatResponse(
            choices=[
                ChatChoice(
                    message=ChatMessage(
                        role="assistant",
                        content=response_text
                    )
                )
            ]
        )
    except Exception as e:
        logger.error(f"Error communicating with contractor agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
