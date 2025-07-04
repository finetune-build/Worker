import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    Prompt
)

class MCPServer:
    def __init__(self, name: str = "finetune-mcp-server", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.server = Server(name, version)
        self._stop_event = asyncio.Event()
        
        # Set up request handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP request handlers."""
        
        # Note: Ping is automatically handled by the Server class
        # No need to define a ping handler - it's built-in
        
        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """Handle list resources requests."""
            print(f"[MCP Server] Received list resources request")
            # Return empty list for now - you can add resources later
            return []
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """Handle list tools requests."""
            print(f"[MCP Server] Received list tools request")
            # Return empty list for now - you can add tools later
            return []
        
        @self.server.list_prompts()
        async def handle_list_prompts() -> list[Prompt]:
            """Handle list prompts requests."""
            print(f"[MCP Server] Received list prompts request")
            # Return empty list for now - you can add prompts later
            return []
    
    async def start(self):
        """Start the MCP server and run until stopped."""
        try:
            print(f"[MCP Server] Starting {self.name} v{self.version}")
            print(f"[MCP Server] Listening on stdio...")
            
            # Run the stdio server until stopped
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
                
        except asyncio.CancelledError:
            print("[MCP Server] Server cancelled")
            raise
        except Exception as e:
            print(f"[MCP Server] Error in server: {e}")
            raise
        finally:
            print("[MCP Server] Server stopped")
    
    async def start_background(self):
        """Start the MCP server in the background (non-blocking)."""
        if hasattr(self, '_server_task') and not self._server_task.done():
            raise RuntimeError("Server is already running")
        
        print(f"[MCP Server] Starting server in background...")
        self._server_task = asyncio.create_task(self.start())
    
    async def stop(self):
        """Stop the MCP server gracefully."""
        if not hasattr(self, '_server_task'):
            return
        
        print("[MCP Server] Stopping server...")
        self._stop_event.set()
        
        # Cancel the server task
        if not self._server_task.done():
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
    
    def is_running(self) -> bool:
        """Check if the server is still running."""
        return (
            hasattr(self, '_server_task') and 
            not self._server_task.done() and 
            not self._stop_event.is_set()
        )


# Example usage for testing
async def main():
    """Example usage of the MCP server."""
    server = MCPServer()
    
    try:
        # Start the server (this will block until stopped)
        await server.start()
    except KeyboardInterrupt:
        print("\nReceived interrupt, stopping server...")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())