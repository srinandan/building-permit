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
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from services import ai_service

from google.adk.cli.fast_api import get_fast_api_app

from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# from telemetry import setup_telemetry

# Load environment variables
load_dotenv()

# Initialize OpenTelemetry
# setup_telemetry()

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bucket_name = f"gs://{os.getenv("GOOGLE_CLOUD_PROJECT")}"

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=False,
    artifact_service_uri=bucket_name,
    allow_origins=allow_origins,
    trace_to_cloud=False,
    otel_to_cloud=True,
)

app.title = "Building Plan Compliance Agent"

HTTPXClientInstrumentor().instrument()
FastAPIInstrumentor.instrument_app(app)

class Violation(BaseModel):
    section: str
    description: str
    suggestion: str

class ComplianceReport(BaseModel):
    status: str
    violations: List[Violation]
    approved_elements: List[str]

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    permit_id: Optional[str] = None
    violation: Optional[Violation] = None

class ChatChoice(BaseModel):
    message: ChatMessage

class ChatResponse(BaseModel):
    choices: List[ChatChoice]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response_text = await ai_service.chat_about_violation(request)
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze", response_model=ComplianceReport)
async def analyze_plan(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read the file content asynchronously
    content = await file.read()

    # 1. Use Document AI to extract text (Optional, if we want to query RAG with text specifically)
    extracted_text = ai_service.extract_text_from_pdf(content)

    # 2. Use Gemini and Vertex RAG to analyze the plan (passing the raw PDF for Vision)
    analysis_result = await ai_service.analyze_plan_with_gemini(extracted_text, content)

    # Return structured JSON
    return ComplianceReport(**analysis_result)

@app.get("/health")
def health_check():
    return {"status": "ok"}
