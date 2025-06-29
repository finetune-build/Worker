import asyncio
import threading
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import os

from finetune.conf import settings

# Global variables for managing client state
worker_mcp_client_thread = None
shutdown_event = None
client_session = None
response_ready = None  # Event to signal when response is ready

def worker_start_mcp_client(request, callback=None):
    """
    Starts the worker mcp_client thread if not already running.
    
    Args:
        request: The MCP request to process
        callback: Optional callback function to handle the response
    """
    global worker_mcp_client_thread, shutdown_event, response_ready
    if worker_mcp_client_thread is not None and worker_mcp_client_thread.is_alive():
        print("[MCP] Client already running, reusing existing connection")
        return worker_mcp_client_thread
    
    print("[MCP] Starting new worker mcp_client thread.")
    shutdown_event = threading.Event()
    response_ready = asyncio.Event()  # Create new event for response synchronization
    
    def run_async_mcp_client():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_mcp_client(shutdown_event, response_ready, request, callback))
        except Exception as e:
            print(f"[MCP] Error in mcp_client thread: {e}")
        finally:
            loop.close()
    
    worker_mcp_client_thread = threading.Thread(
        target=run_async_mcp_client, daemon=True
    )
    worker_mcp_client_thread.start()
    return worker_mcp_client_thread

def worker_shutdown_mcp_client_thread():
    """
    Signals the mcp_client thread to shut down.
    """
    global shutdown_event, worker_mcp_client_thread, client_session
    if shutdown_event is not None:
        print("[MCP] Initiating shutdown...")
        shutdown_event.set()
        if client_session:
            client_session = None
        if worker_mcp_client_thread:
            worker_mcp_client_thread = None

async def run_mcp_client(shutdown_event, response_ready, request, callback=None):
    """
    Target function for the mcp_client thread.
    Maintains the connection until shutdown is requested.
    """
    try:
        await main(shutdown_event, response_ready, request, callback)
    except Exception as e:
        print(f"[MCP] mcp_client error: {e}")
    finally:
        print("[MCP] mcp_client connection closed gracefully")

async def main(shutdown_event, response_ready, request, callback=None):
    """
    Main MCP client loop that maintains the connection until shutdown.
    """
    global client_session
    
    server_params = StdioServerParameters(
        command="python",
        args=["examples/mcp/worker-integration/weather.py"],
        env=os.environ,
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                print(f"[MCP] MCP Client Request: {request}")
                client_session = session
                await session.initialize()
                
                result = None
                
                if request.get("method") == "tools/list":
                    result = await session.list_tools()
                elif request.get("method") == "resources/list":
                    result = await session.list_resources()
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "resources/read":
                    result = await session.read_resource(request.get("params").get("resource_id"))
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "tools/call":
                    result = await session.call_tool(
                        request.get("params").get("tool_name"), 
                        request.get("params").get("args")
                    )
                
                if callback:
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": request.get("id")
                    }
                    
                    try:
                        await callback(response)
                        # Signal that response has been processed
                        response_ready.set()
                        
                        # Wait for shutdown signal
                        # while not shutdown_event.is_set():
                        #     await asyncio.sleep(0.1)
                            
                    except Exception as e:
                        print(f"[MCP] Error in callback: {e}")
                    finally:
                        # Signal completion and cleanup
                        print("[MCP] Request completed, initiating shutdown...")
                        client_session = None
                
    except Exception as e:
        print(f"[MCP] Error in main loop: {e}")
        if client_session:
            client_session = None
        shutdown_event.set()
