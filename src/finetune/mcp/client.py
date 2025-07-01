import asyncio
import os
from typing import Callable, Any, Optional
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from finetune import settings

class MCPClient:
    def __init__(self, on_event: Callable):
        self.on_event = on_event
        self.session: Optional[ClientSession] = None
        self._stop_event = asyncio.Event()
        self._read_stream = None
        self._write_stream = None
        self._session_task = None
        
        # Server parameters for stdio connection
        self.server_params = StdioServerParameters(
            command="python",
            args=[settings.MCP_SERVER_PATH],
            env=os.environ,
        )
    
    async def start(self):
        """
        Opens connection with MCP server and starts listening for requests.
        """
        try:
            # Create stdio connection
            self._read_stream, self._write_stream = await stdio_client(self.server_params).__aenter__()
            
            # Create MCP session
            self.session = ClientSession(self._read_stream, self._write_stream)
            
            # Initialize the session
            print("[MCP] Initializing session...")
            await self.session.initialize()
            print(f"[MCP] Connected to MCP server")
            
            # Start the event loop to handle incoming notifications
            self._session_task = asyncio.create_task(self._handle_notifications())
            
        except Exception as e:
            print(f"[MCP] Error starting client: {e}")
            await self.stop()
            raise
    
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
        self._stop_event.set()
        
        # Cancel the notification handler task
        if self._session_task and not self._session_task.done():
            self._session_task.cancel()
            try:
                await self._session_task
            except asyncio.CancelledError:
                pass
        
        # Close the session
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        
        # Close the stdio connection
        if self._read_stream and self._write_stream:
            await stdio_client(self.server_params).__aexit__(None, None, None)
            self._read_stream = None
            self._write_stream = None
        
        print("[MCP] Client stopped")
    
    def is_running(self) -> bool:
        """Check if the client is still running."""
        return not self._stop_event.is_set() and self.session is not None


# Example usage:
async def main():
    async def handle_mcp_event(event):
        print(f"Received MCP event: {event}")
    
    client = MCPClient(on_event=handle_mcp_event)
    
    try:
        # Start the client
        await client.start()
        
        # Example: send a request
        request = {
            "method": "tools/list",
            "params": {},
            "id": 1
        }
        response = await client.handle_request(request)
        
        # Keep running for a while
        await asyncio.sleep(10)
        
    finally:
        # Stop the client
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())