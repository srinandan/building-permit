import unittest
import unittest.mock
import sys
import os

os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'
os.environ['DOCUMENT_AI_PROCESSOR_ID'] = 'test-processor'

import types
class MockImporter:
    def find_module(self, fullname, path=None):
        prefixes = ('google', 'a2a', 'vertexai', 'opentelemetry')
        if any(fullname.startswith(p) for p in prefixes):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        mod = types.ModuleType(fullname)
        mod.__getattr__ = lambda name: unittest.mock.MagicMock()

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

# Mock agent entirely
sys.modules['agent'] = unittest.mock.MagicMock()

from unittest.mock import patch
with patch("google.adk.cli.fast_api.get_fast_api_app", return_value=__import__('fastapi').FastAPI()), \
     patch("google.auth.default", return_value=(unittest.mock.MagicMock(universe_domain="googleapis.com"), "test")):
    import main

client = TestClient(main.app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_feedback():
    feedback = {"rating": 5, "comment": "Excellent service!"}
    response = client.post("/feedback", json=feedback)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_feedback_invalid():
    # missing rating
    feedback = {"comment": "Excellent service!"}
    response = client.post("/feedback", json=feedback)
    assert response.status_code == 422
