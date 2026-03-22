import uvicorn
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp_server = FastMCP(name="assessor")

# Fake Santa Clara County Assessor Data
PARCELS = {
    "123-45-678": {
        "apn": "123-45-678",
        "address": "123 Main St, Santa Clara, CA 95050",
        "lot_size_sqft": 6000,
        "owner": "John Doe",
        "assessed_value": 1200000
    },
    "987-65-432": {
        "apn": "987-65-432",
        "address": "456 Elm St, San Jose, CA 95112",
        "lot_size_sqft": 8000,
        "owner": "Jane Smith",
        "assessed_value": 1500000
    }
}

ZONING_BY_ADDRESS = {
    "123 Main St, Santa Clara, CA 95050": "R-1",
    "456 Elm St, San Jose, CA 95112": "R-1-8"
}

ZONING_RULES = {
    "R-1": {
        "description": "Single-Family Residential",
        "max_height_ft": 30,
        "max_lot_coverage_percent": 40,
        "setbacks": {
            "front_ft": 20,
            "rear_ft": 20,
            "side_ft": 5
        }
    },
    "R-1-8": {
        "description": "Single-Family Residential (8,000 sq ft min lot)",
        "max_height_ft": 35,
        "max_lot_coverage_percent": 35,
        "setbacks": {
            "front_ft": 25,
            "rear_ft": 25,
            "side_ft": 8
        }
    }
}


@mcp_server.tool()
def lookup_parcel(apn: str) -> dict:
    """Lookup property details by Assessor's Parcel Number (APN)."""
    if apn in PARCELS:
        return PARCELS[apn]
    return {"error": f"Parcel not found for APN: {apn}"}

@mcp_server.tool()
def get_zoning_classification(address: str) -> str:
    """Get the zoning classification code for a given address."""
    for known_address, zoning in ZONING_BY_ADDRESS.items():
        if address.lower() in known_address.lower() or known_address.lower() in address.lower():
             return zoning
    return "Unknown"

@mcp_server.tool()
def get_setback_requirements(zoning_code: str) -> dict:
    """Get setback requirements, lot coverage limits, and height limits for a given zoning code."""
    if zoning_code in ZONING_RULES:
        return ZONING_RULES[zoning_code]
    return {"error": f"Zoning code not found: {zoning_code}"}


app = mcp_server.sse_app

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
