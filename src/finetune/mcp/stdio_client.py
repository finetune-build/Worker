import asyncio
import os

from typing import Callable, Any, Optional

from finetune import settings

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

class MCPClient:
    def __init__(self, on_event: Optional[Callable[[dict], Any]] = None):
        self.session = None
        self._stop_event = asyncio.Event()
        self._read_stream = None
        self._write_stream = None
        self._session_task = None
        self.on_event = on_event or self._default_event_handler
        
        # Server parameters for stdio connection
        self.server_params = StdioServerParameters(
            command="python",
            # args=[settings.MCP_SERVER_PATH],
            # env=os.environ,
        )

    async def _default_event_handler(self, event: dict):
        """Default event handler that just logs the event."""
        print(f"[MCP] Event: {event}")

    async def start(self):
        """Start the MCP client and wait for it to finish."""
        if hasattr(self, '_client_task') and not self._client_task.done():
            raise RuntimeError("Client is already running")

        print(f"[MCP] Starting client...")
        self._client_task = asyncio.create_task(self._run_client())
        
        # Wait for the client to finish (this will block until stopped)
        await self._client_task

    async def start_background(self):
        """Start the MCP client in the background (non-blocking)."""
        if hasattr(self, '_client_task') and not self._client_task.done():
            raise RuntimeError("Client is already running")

        print(f"[MCP] Starting client in background...")
        self._client_task = asyncio.create_task(self._run_client())

    async def _run_client(self):
        """Internal method that runs the entire client lifecycle."""
        try:
            print(f"[MCP] Current working directory: {os.getcwd()}")

            async with stdio_client(self.server_params) as (read_stream, write_stream):
                # Create MCP session
                self.session = ClientSession(read_stream, write_stream)

                # Initialize the session
                print("[MCP] Initializing session...")
                await self.session.initialize()
                print(f"[MCP] Connected to MCP server")

                # Run until stopped
                await self._handle_notifications()

        except asyncio.CancelledError:
            print("[MCP] Client cancelled")
            raise
        except Exception as e:
            print(f"[MCP] Error in client: {e}")
            raise
        finally:
            print("[MCP] Client stopped")
            self.session = None

    
    async def _handle_notifications(self):
        """
        Handle incoming notifications from the MCP server.
        """
        try:
            while not self._stop_event.is_set():
                # This is a simplified example - in practice, you'd need to handle
                # the MCP protocol's notification system properly
                await asyncio.sleep(0.1)  # Prevent busy loop
                
                # Check if session is still active
                if not self.session:
                    break
                    
        except Exception as e:
            print(f"[MCP] Error in notification handler: {e}")
    
    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a single MCP request.
        
        Args:
            request: The MCP request to process
            
        Returns:
            The response dictionary
        """
        if not self.session:
            raise RuntimeError("MCP client not connected")
            
        try:
            print(f"[MCP] Processing request: {request}")
            result = None
            params = request.get("params", {})
            
            method = request.get("method")
            
            if method == "ping":
                result = await self.session.send_ping()
                result = result.model_dump(exclude_none=True)
                
            elif method == "resources/list":
                result = await self.session.list_resources()
                result = result.model_dump(exclude_none=True)
                
            elif method == "resources/templates/list":
                result = await self.session.list_resource_templates()
                result = result.model_dump(exclude_none=True)
                
            elif method == "resources/read":
                uri = params.get("uri")
                result = await self.session.read_resource(uri)
                result = result.model_dump(exclude_none=True)
                
            elif method == "resources/subscribe":
                uri = params.get("uri")
                result = await self.session.subscribe_to_resource(uri)
                result = result.model_dump(exclude_none=True)
                
            elif method == "resources/unsubscribe":
                uri = params.get("uri")
                result = await self.session.unsubscribe_from_resource(uri)
                result = result.model_dump(exclude_none=True)
                
            elif method == "prompts/list":
                result = await self.session.list_prompts()
                result = result.model_dump(exclude_none=True)
                
            elif method == "prompts/get":
                name = params.get("name")
                args = params.get("args")
                result = await self.session.get_prompt(name, args)
                result = result.model_dump(exclude_none=True)
                
            elif method == "tools/list":
                result = await self.session.list_tools()
                result = {
                    "tools": [tool.model_dump(exclude_none=True) for tool in result.tools],
                    "nextCursor": result.nextCursor
                }
                
            elif method == "tools/call":
                name = params.get("name")
                args = params.get("args")
                result = await self.session.call_tool(name, args)
                result = result.model_dump(exclude_none=True)
                
            elif method == "notifications/roots/list_changed":
                result = await self.session.list_roots()
                result = result.model_dump(exclude_none=True)
                
            elif method == "logging/setLevel":
                level = params.get("level")
                result = await self.session.set_logging_level(level)
                result = result.model_dump(exclude_none=True)
                
            else:
                raise ValueError(f"Unknown method: {method}")
            
            response = {
                "jsonrpc": "2.0",
                "result": result,
                "id": request.get("id")
            }
            
            print(f"[MCP] Sending response: {response}")
            
            # Call the event handler with the response
            await self.on_event(response)
            
            return response
            
        except Exception as e:
            print(f"[MCP] Error processing request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request.get("id")
            }
            await self.on_event(error_response)
            return error_response
    
    async def stop(self):
        """Stop the MCP client gracefully."""
        if not hasattr(self, '_client_task'):
            return
        
        print("[MCP] Stopping client...")
        self._stop_event.set()
        
        # Cancel the main client task
        if not self._client_task.done():
            self._client_task.cancel()
            try:
                await self._client_task
            except asyncio.CancelledError:
                pass
    
    def is_running(self) -> bool:
        """Check if the client is still running."""
        return not self._stop_event.is_set() and self.session is not None