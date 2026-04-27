import unittest
import unittest.mock
import sys
import os
import types

# Set environment variables early
os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'
os.environ['DOCUMENT_AI_PROCESSOR_ID'] = 'test-processor'

class MockImporter:
    def find_module(self, fullname, path=None):
        prefixes = ('google', 'a2a', 'vertexai', 'opentelemetry', 'model_armor')
        if any(fullname.startswith(p) for p in prefixes):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        mod = types.ModuleType(fullname)
        mod.__getattr__ = lambda name: unittest.mock.MagicMock()

        if fullname == 'google.adk.integrations.agent_registry.agent_registry':
            mod.AgentRegistry = unittest.mock.MagicMock()
        if fullname == 'google.adk.cli.fast_api':
            # Return an actual FastAPI instance here instead of a mock so testing works
            from fastapi import FastAPI
            mod.get_fast_api_app = unittest.mock.MagicMock(return_value=FastAPI())

        if fullname == 'google.auth':
            mock_credentials = unittest.mock.MagicMock()
            mock_credentials.universe_domain = "googleapis.com"
            mock_credentials.token = "fake-token"
            mod.default = unittest.mock.MagicMock(return_value=(mock_credentials, "test-project"))
            mod.exceptions = unittest.mock.MagicMock()

        sys.modules[fullname] = mod
        return mod

sys.meta_path.insert(0, MockImporter())

from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import httpx

def mock_get(url, *args, **kwargs):
    mock_resp = unittest.mock.MagicMock()
    mock_resp.status_code = 200
    if "mcpServers" in url:
        mock_resp.json.return_value = {"mcpServers": [{"name": "building-permit-assessor-mcp-server", "endpointUri": "http://mock-mcp"}]}
    else:
        mock_resp.json.return_value = {"agents": [{"name": "contractor-agent", "endpointUri": "http://mock-agent"}]}
    return mock_resp

# Mock the entire services file to avoid any of its imports entirely
sys.modules['services'] = unittest.mock.MagicMock()
mock_ai_service = unittest.mock.MagicMock()
sys.modules['services'].ai_service = mock_ai_service

# To prevent Google Cloud Storage init hitting default auth inside main.py
with patch("google.adk.cli.fast_api.get_fast_api_app", return_value=__import__('fastapi').FastAPI()), \
     patch("google.auth.default", return_value=(unittest.mock.MagicMock(universe_domain="googleapis.com"), "test")):
    import main

# Ensure we mock out any actual usage inside main
main.ai_service = mock_ai_service

client = TestClient(main.app)

# We must manually add the routes to main.app since we mocked get_fast_api_app which would normally do it
# But main.py already adds the routes to `app` directly via @app.post, so they should be there!

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_analyze_plan_invalid_file_type():
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]

def test_analyze_plan_mock_pdf():
    mock_ai_service.extract_text_from_pdf.return_value = "Extracted test content"
    async def mock_analyze(*args, **kwargs):
        return {
            "status": "Changes Suggested",
            "violations": [{"section": "Mock CA Title 24", "description": "test", "suggestion": "fix"}],
            "approved_elements": []
        }
    mock_ai_service.analyze_plan_with_gemini = mock_analyze

    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    files = {"file": ("test_plan.pdf", dummy_pdf_content, "application/pdf")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "violations" in data
    assert "approved_elements" in data

    assert data["status"] == "Changes Suggested"
    assert len(data["violations"]) > 0
    assert data["violations"][0]["section"].startswith("Mock CA Title 24")

def test_chat_success():
    async def mock_chat(*args, **kwargs):
        return "This is a successful chat response."
    mock_ai_service.chat_about_violation = mock_chat

    payload = {
        "messages": [
            {"role": "user", "content": "Hello, how can I fix the lighting violation?"}
        ]
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["content"] == "This is a successful chat response."
    assert data["choices"][0]["message"]["role"] == "assistant"

def test_chat_with_violation():
    async def mock_chat(*args, **kwargs):
        return "You can fix it by using LED fixtures."
    mock_ai_service.chat_about_violation = mock_chat

    payload = {
        "messages": [
            {"role": "user", "content": "How do I fix this?"}
        ],
        "violation": {
            "section": "CA Title 24",
            "description": "Lighting issue",
            "suggestion": "Use LEDs"
        }
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["choices"][0]["message"]["content"] == "You can fix it by using LED fixtures."

def test_chat_error():
    async def mock_chat(*args, **kwargs):
        raise Exception("Simulated service error")
    mock_ai_service.chat_about_violation = mock_chat

    payload = {
        "messages": [
            {"role": "user", "content": "Trigger an error"}
        ]
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 500
    assert "Simulated service error" in response.json()["detail"]

def test_analyze_plan_unexpected_error():
    from fastapi import HTTPException
    mock_ai_service.extract_text_from_pdf.side_effect = HTTPException(status_code=500, detail="General error during extraction")

    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    files = {"file": ("test_plan.pdf", dummy_pdf_content, "application/pdf")}

    response = client.post("/analyze", files=files)

    assert response.status_code == 500
    assert "General error during extraction" in response.json()["detail"]

def test_missing_messages():
    payload = {}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422 # FastAPI validation error
