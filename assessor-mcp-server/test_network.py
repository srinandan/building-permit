import asyncio
import subprocess
import time
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

def start_server():
    # Start server in background
    # Note: Ensure no other process is using port 8002
    f = open("server.log", "w")
    proc = subprocess.Popen(["uv", "run", "main.py"], stdout=f, stderr=f)
    time.sleep(5)  # Give server time to start
    return proc, f

async def test_network_lookup():
    server_proc, log_file = start_server()
    url = "http://0.0.0.0:8002/mcp"
    
    print(f"Connecting to {url}...")
    
    try:
        async with streamablehttp_client(url=url) as (read_stream, write_stream, get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # Invoke the tool
                result = await session.call_tool("lookup_parcel", arguments={"apn": "123-45-678"})
                print(f"Result: {result}")
                
                # Assertions
                assert result is not None
                # The result is expected to be a CallToolResult, which has 'content' attribute.
                # Let's verify what it returns exactly or if it prints it.
    finally:
        print("Stopping server...")
        server_proc.terminate()
        server_proc.wait()
        log_file.close()

if __name__ == "__main__":
    asyncio.run(test_network_lookup())
