import asyncio
import threading
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import asyncio
import os

from ftw.conf import settings

# Global variables for managing client state
worker_mcp_client_thread = None
shutdown_event = None
client_session = None

def worker_start_mcp_client():
    """
    Starts the worker mcp_client thread if not already running.
    """
    global worker_mcp_client_thread, shutdown_event
    if worker_mcp_client_thread is not None and worker_mcp_client_thread.is_alive():
        print("[MCP] Client already running, reusing existing connection")
        return worker_mcp_client_thread
    
    print("[MCP] Starting new worker mcp_client thread.")
    shutdown_event = threading.Event()
    
    def run_async_mcp_client():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_mcp_client(shutdown_event))
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

async def run_mcp_client(shutdown_event):
    """
    Target function for the mcp_client thread.
    Maintains the connection until shutdown is requested.
    """
    try:
        await main(shutdown_event)
    except Exception as e:
        print(f"[MCP] mcp_client error: {e}")
    finally:
        print("[MCP] mcp_client connection closed gracefully")

async def main(shutdown_event):
    """
    Main MCP client loop that maintains the connection until shutdown.
    """
    global client_session
    
    server_params = StdioServerParameters(
        command="python",
        args=["examples/mcp/worker-integration/weather.py"],
        env=os.environ,
    )

    while not shutdown_event.is_set():
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    client_session = session
                    await session.initialize()
                    tools = await session.list_tools()
                    print("[MCP] Available tools:", tools)
                    
                    # Keep the connection alive until shutdown is requested
                    while not shutdown_event.is_set():
                        try:
                            await asyncio.sleep(1)  # Prevent busy waiting
                        except asyncio.CancelledError:
                            break
                    
                    client_session = None
                    
            if shutdown_event.is_set():
                break
                
            # If we get here, the connection was lost but shutdown wasn't requested
            print("[MCP] Connection lost, attempting to reconnect in 5 seconds...")
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"[MCP] Error in main loop: {e}")
            if not shutdown_event.is_set():
                print("[MCP] Will attempt to reconnect in 5 seconds...")
                await asyncio.sleep(5)
            else:
                break
    # async with Client() as client:
    #     # Call tools
    #     result = await client.call_tool("get_alerts_pa")
    #     print("Result:", result)
