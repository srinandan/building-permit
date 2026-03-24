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

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from db import get_connection, init_db

# Initialize database
init_db()

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from google import auth
from google.auth.transport.grpc import AuthMetadataPlugin
import google.auth.transport.requests
import grpc
from opentelemetry.instrumentation.mcp import McpInstrumentor

# --- OpenTelemetry Setup ---
McpInstrumentor().instrument()

try:
    credentials, project_id = auth.default()
except Exception:
    credentials, project_id = None, None

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", project_id or "")

if PROJECT_ID:
    os.environ["OTEL_RESOURCE_ATTRIBUTES"] = f"gcp.project_id={PROJECT_ID}"

os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "https://telemetry.googleapis.com")

resource = Resource.create(
    attributes={
        SERVICE_NAME: "assessor-mcp-server",
    }
)

try:
    if credentials:
        # Request used to refresh credentials upon expiry
        request = auth.transport.requests.Request()
        auth_metadata_plugin = AuthMetadataPlugin(credentials=credentials, request=request)
        channel_creds = grpc.composite_channel_credentials(
            grpc.ssl_channel_credentials(),
            grpc.metadata_call_credentials(auth_metadata_plugin),
        )
        otlp_grpc_exporter = OTLPSpanExporter(credentials=channel_creds)
    else:
        otlp_grpc_exporter = OTLPSpanExporter()

    tracer_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(otlp_grpc_exporter)
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)
except Exception as e:
    print(f"Failed to initialize OpenTelemetry: {e}")

# Initialize FastMCP Server
mcp_server = FastMCP(name="assessor", host="0.0.0.0")

@mcp_server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    )
)
def lookup_parcel(apn: str) -> dict:
    """Lookup property details by Assessor's Parcel Number (APN)."""
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

app = mcp_server.streamable_http_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
