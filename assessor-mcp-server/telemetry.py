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

import atexit
import logging
import os

import google.auth
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from google import auth
from google.auth.transport.grpc import AuthMetadataPlugin
import grpc

def setup_telemetry():
    """Configure OpenTelemetry and GenAI telemetry."""
    credentials, project_id = google.auth.default()
    request = google.auth.transport.requests.Request()
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", project_id or "")
    commit_sha = os.environ.get("COMMIT_SHA", "dev")

    # 1. Set environment variables for instrumentation logic FIRST
    os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental")
    os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = f"{PROJECT_ID}"
    os.environ["OTEL_RESOURCE_ATTRIBUTES"] = f"gcp.project_id={PROJECT_ID}"
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "building-permit-assessor-mcp-server")
    os.environ["OTEL_TRACES_EXPORTER"] = "otlp"
    os.environ["OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT"] = "512"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://telemetry.googleapis.com"    

    # 2. Build all Resource attributes safely in a dictionary
    attributes = {
        SERVICE_NAME: OTEL_SERVICE_NAME,
        "service.version": commit_sha,
    }
    
    # GCP's OTLP endpoint strictly requires 'gcp.project_id' to route the traces!
    if PROJECT_ID:
        attributes["gcp.project_id"] = PROJECT_ID

    # 3. Create the resource AFTER defining all attributes
    resource = Resource.create(attributes=attributes)

    # 4. Set up gRPC Authentication
    auth_metadata_plugin = AuthMetadataPlugin(credentials=credentials, request=request)
    channel_creds = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(auth_metadata_plugin),
    )

    # 5. Initialize Provider and Exporter
    trace_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            credentials=channel_creds,
            endpoint="telemetry.googleapis.com:443", 
        )
    )
    trace_provider.add_span_processor(processor)
    trace.set_tracer_provider(trace_provider)

    return

from opentelemetry import trace

def teardown_telemetry():
    """Flushes remaining spans and shuts down the OpenTelemetry tracer provider."""
    provider = trace.get_tracer_provider()
    
    # Check if the provider has a shutdown method (safeguard against NoOp providers)
    if hasattr(provider, "shutdown"):
        provider.shutdown()

# Automatically trigger the cleanup when the Python process terminates
atexit.register(teardown_telemetry)