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
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_analyze_plan_invalid_file_type():
    # Send a plain text file instead of PDF
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]

def test_analyze_plan_mock_pdf():
    # Create a simple dummy PDF in memory
    # PDF magic number
    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    files = {"file": ("test_plan.pdf", dummy_pdf_content, "application/pdf")}
    response = client.post("/analyze", files=files)

    # It should return 200 with the mock response (since GCP vars are likely not set in this environment)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "violations" in data
    assert "approved_elements" in data

    # Check if mock response fallback is working
    assert data["status"] == "Changes Suggested"
    assert len(data["violations"]) > 0
    assert data["violations"][0]["section"].startswith("Mock CA Title 24")

@patch("main.ai_service.chat_about_violation", new_callable=AsyncMock)
def test_chat_success(mock_chat):
    mock_chat.return_value = "This is a successful chat response."

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

@patch("main.ai_service.chat_about_violation", new_callable=AsyncMock)
def test_chat_with_violation(mock_chat):
    mock_chat.return_value = "You can fix it by using LED fixtures."

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

@patch("main.ai_service.chat_about_violation", new_callable=AsyncMock)
def test_chat_error(mock_chat):
    mock_chat.side_effect = Exception("Simulated service error")

    payload = {
        "messages": [
            {"role": "user", "content": "Trigger an error"}
        ]
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 500
    assert "Simulated service error" in response.json()["detail"]
