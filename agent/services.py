import os
import json
import logging
from typing import List, Dict, Any

from google.cloud import documentai
from google.cloud import aiplatform
import vertexai
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel, Part

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Load environment variables
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.docai_processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        self.docai_location = os.getenv("DOCUMENT_AI_LOCATION", "us")
        self.rag_corpus_name = os.getenv("VERTEX_RAG_CORPUS_NAME")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")

        # Initialize Vertex AI
        if self.project_id:
            try:
                vertexai.init(project=self.project_id, location=self.location)
                logger.info(f"Initialized Vertex AI for project {self.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI: {e}")
        else:
            logger.warning("GCP_PROJECT_ID not set. GCP services will not work.")

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Use Document AI to extract text from a PDF."""
        if not self.project_id or not self.docai_processor_id:
            logger.warning("Document AI not configured. Returning empty text.")
            return ""

        # For Document AI, we need to specify the api_endpoint if it's not the global default
        client_options = {"api_endpoint": f"{self.docai_location}-documentai.googleapis.com"}
        client = documentai.DocumentProcessorServiceClient(client_options=client_options)

        name = client.processor_path(self.project_id, self.docai_location, self.docai_processor_id)

        raw_document = documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf"
        )
        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document
        )

        result = client.process_document(request=request)
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
            context = ""
            for context_item in response.contexts:
                 context += context_item.text + "\n\n"
            return context
        except Exception as e:
             logger.error(f"Failed to retrieve context from RAG: {e}")
             return ""

    def analyze_plan_with_gemini(self, extracted_text: str, pdf_bytes: bytes) -> Dict[str, Any]:
        """Use Gemini to analyze the plan and the images (multimodal) against the building codes."""
        if not self.project_id:
             logger.warning("GCP Project ID not configured. Using fallback mock response.")
             return self._get_mock_response()

        # Combine the text extraction and multimodal capability of Gemini
        # We pass the PDF directly to Gemini as a Part to analyze diagrams
        try:
             model = GenerativeModel(self.model_name)

             # Create a prompt that asks the model to output JSON
             prompt = """
             You are an expert Building Code Compliance Inspector for Santa Clara County, California.
             Review the provided building plan PDF document (which may contain text and architectural drawings).

             Check the plans against the California Building Standards Code (Title 24) and Santa Clara County specific local reach codes (like CalGreen and All-Electric requirements).

             Analyze the document to identify:
             1. Elements that comply with the codes and are approved.
             2. Elements that violate the codes or need changes. For each violation, specify the exact code section (e.g. "CA Title 24, Part 6, Section 150.0"), describe the issue, and provide a suggestion for fixing it.

             Your response MUST be a valid JSON object with the following schema:
             {
                 "status": "Approved" | "Changes Suggested" | "Rejected",
                 "violations": [
                     {
                         "section": "string",
                         "description": "string",
                         "suggestion": "string"
                     }
                 ],
                 "approved_elements": ["string"]
             }

             Do not include any markdown formatting like ```json ... ```, just output the raw JSON.
             """

             # You can optionally pass retrieved RAG context here as well:
             rag_context = self.retrieve_code_context("building code requirements " + extracted_text[:1000])
             if rag_context:
                 prompt += f"\n\nHere is relevant code context to reference:\n{rag_context}"

             # Create the document part
             pdf_part = Part.from_data(data=pdf_bytes, mime_type="application/pdf")

             response = model.generate_content([prompt, pdf_part])

             try:
                 # Try to parse the response as JSON
                 cleaned_response = response.text.strip()
                 if cleaned_response.startswith('```json'):
                     cleaned_response = cleaned_response[7:]
                 if cleaned_response.endswith('```'):
                     cleaned_response = cleaned_response[:-3]

                 return json.loads(cleaned_response)
             except json.JSONDecodeError as e:
                 logger.error(f"Failed to parse Gemini JSON output: {response.text}")
                 logger.error(f"JSON Error: {e}")
                 return self._get_mock_response()

        except Exception as e:
             logger.error(f"Error during Gemini analysis: {e}")
             return self._get_mock_response()

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
