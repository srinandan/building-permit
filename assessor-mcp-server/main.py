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
import grpc
from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from db import get_connection, init_db
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import asyncio
import google.auth
import google.auth.transport.requests
from opentelemetry.resourcedetector.gcp_resource_detector import (
    GoogleCloudResourceDetector,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource, get_aggregated_resources
from fastmcp.server.middleware import Middleware, MiddlewareContext
from opentelemetry.instrumentation.mcp import McpInstrumentor

OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "building-permit-assessor-mcp-server")

credentials, project_id = google.auth.default()
resource = get_aggregated_resources(
    detectors=[GoogleCloudResourceDetector()],
    initial_resource=Resource.create(
        attributes={
            SERVICE_NAME: OTEL_SERVICE_NAME,
            "gcp.project_id": project_id,
        }
    ),
)

# Initialize database
init_db()

request = google.auth.transport.requests.Request()
auth_metadata_plugin = AuthMetadataPlugin(credentials=credentials, request=request)
channel_creds = grpc.composite_channel_credentials(
    grpc.ssl_channel_credentials(),
    grpc.metadata_call_credentials(auth_metadata_plugin),
)
# Set up OpenTelemetry Python SDK
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            credentials=channel_creds,
            endpoint="https://telemetry.googleapis.com:443/v1/traces",
        )
    )
)
trace.set_tracer_provider(tracer_provider)

# Instrument MCP Server
McpInstrumentor().instrument()

class TraceMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):

        # print context method message.name and type
        print(f"Context method: {context.method} Context message.name: {context.message.name} Context message.type: {context.message.type}")
        tool_name = context.message.name

        # The tracer name can be any string. Using the module name is a common practice.
        tracer = trace.get_tracer(__name__)
        span_name = tool_name

        with tracer.start_as_current_span(span_name) as span:
            # Add attributes to the span for more context in Cloud Trace.
            span.set_attribute("context.method", str(context.method))
            span.set_attribute("context.name", str(context.message.name))
            span.set_attribute("context.type", str(context.type))
            # Allow other tools to proceed
            return await call_next(context)

# Initialize FastMCP Server
mcp_server = FastMCP(
    name=OTEL_SERVICE_NAME,
    middleware=[TraceMiddleware()]
)

@mcp_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    )
)
def lookup_parcel(apn: str) -> dict:
    """Lookup property details by Assessor's Parcel Number (APN)."""
    print(f"lookup_parcel called with apn: {apn}")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM parcels WHERE apn = ?", (apn,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"error": f"Parcel not found for APN: {apn}"}

@mcp_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    )
)
def get_zoning_classification(address: str) -> str:
    """Get the zoning classification code for a given address."""
    print(f"get_zoning_classification called with address: {address}")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT zoning_code FROM zoning_by_address WHERE address LIKE ?", (f"%{address}%",))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return "Unknown"

@mcp_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    )
)
def get_setback_requirements(zoning_code: str) -> dict:
    """Get setback requirements, lot coverage limits, and height limits for a given zoning code."""
    print(f"get_setback_requirements called with zoning_code: {zoning_code}")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM zoning_rules WHERE zoning_code = ?", (zoning_code,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"error": f"Zoning code not found: {zoning_code}"}


@mcp_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=False,
        destructiveHint=True,
    )
)
def add_parcel(apn: str, address: str, lot_size_sqft: int, owner: str, assessed_value: int) -> dict:
    """Add a new property to the assessor's database."""
    print(f"add_parcel called with apn: {apn}, address: {address}, lot_size_sqft: {lot_size_sqft}, owner: {owner}, assessed_value: {assessed_value}")
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO parcels (apn, address, lot_size_sqft, owner, assessed_value) VALUES (?, ?, ?, ?, ?)",
            (apn, address, lot_size_sqft, owner, assessed_value)
        )
        conn.commit()
        return {"status": "success", "message": f"Parcel {apn} added successfully."}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@mcp_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=False,
        destructiveHint=True,
    )
)
def rezone_address(address: str, new_zoning_code: str) -> dict:
    """Update the zoning classification code for a specific address."""
    print(f"rezone_address called with address: {address}, new_zoning_code: {new_zoning_code}")
    conn = get_connection()
    c = conn.cursor()
    try:
        # Check if address exists
        c.execute("SELECT address FROM zoning_by_address WHERE address LIKE ?", (f"%{address}%",))
        row = c.fetchone()
        if row:
            actual_address = row[0]
            c.execute("UPDATE zoning_by_address SET zoning_code = ? WHERE address = ?", (new_zoning_code, actual_address))
        else:
            # If not exists, insert it
            c.execute("INSERT INTO zoning_by_address (address, zoning_code) VALUES (?, ?)", (address, new_zoning_code))

        conn.commit()
        return {"status": "success", "message": f"Address '{address}' rezoned to {new_zoning_code}."}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@mcp_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=True,
        destructiveHint=True,
    )
)
def add_zoning_rule(zoning_code: str, description: str, max_height_ft: int, max_lot_coverage_percent: int, front_setback_ft: int, rear_setback_ft: int, side_setback_ft: int) -> dict:
    """Add or update the setback requirements and lot coverage limits for a zoning code."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO zoning_rules (zoning_code, description, max_height_ft, max_lot_coverage_percent, front_setback_ft, rear_setback_ft, side_setback_ft)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zoning_code) DO UPDATE SET
                description=excluded.description,
                max_height_ft=excluded.max_height_ft,
                max_lot_coverage_percent=excluded.max_lot_coverage_percent,
                front_setback_ft=excluded.front_setback_ft,
                rear_setback_ft=excluded.rear_setback_ft,
                side_setback_ft=excluded.side_setback_ft
        ''', (zoning_code, description, max_height_ft, max_lot_coverage_percent, front_setback_ft, rear_setback_ft, side_setback_ft))
        conn.commit()
        return {"status": "success", "message": f"Zoning rule for '{zoning_code}' added/updated."}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    # Could also use 'sse' transport, host="0.0.0.0" required for Cloud Run.
    asyncio.run(
        mcp_server.run_async(
            transport="streamable-http", 
            host="0.0.0.0", 
            port=8002,
        )
    )