import asyncio
from typing import Any

from finetune.processes.base import BaseProcess
from finetune.mcp.server import MCPServer

class MCPServerProcess(BaseProcess):
    """Process for spinning up MCP server to handle MCP client requests."""
    
    def __init__(self, server_name: str = "finetune-mcp-server", server_version: str = "1.0.0", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mcp_server = None
        self.server_name = server_name
        self.server_version = server_version
    
    async def run_mcp_server(self):
        """Run the MCP server with retry logic."""
        retry_delay = 1  # Start with 1 second
        max_delay = 60   # Maximum 60 seconds between retries
        
        while self.running:
            try:
                self.logger.info(f"Starting MCP server: {self.server_name} v{self.server_version}")
                
                # Create MCP server
                self._mcp_server = MCPServer(
                    name=self.server_name,
                    version=self.server_version
                )
                
                # Start the server (this will block until stopped)
                await self._mcp_server.start()
                
                # If we get here, the server stopped
                if self.running:
                    self.logger.warning("MCP server stopped unexpectedly")
                
            except asyncio.CancelledError:
                self.logger.info("MCP server cancelled")
                break
            except Exception as e:
                self.logger.error(f"MCP server error: {e}")
            
            finally:
                # Stop the server if it's running
                if self._mcp_server:
                    try:
                        await self._mcp_server.stop()
                    except Exception as e:
                        self.logger.error(f"Error stopping MCP server: {e}")
                    self._mcp_server = None
            
            # Only retry if we're still supposed to be running
            if self.running:
                self.logger.info(f"Retrying in {retry_delay}s...")
                
                # Wait for retry delay, but check for shutdown periodically
                retry_end = asyncio.get_event_loop().time() + retry_delay
                while self.running and asyncio.get_event_loop().time() < retry_end:
                    await asyncio.sleep(0.5)  # Check every 500ms
                
                if not self.running:
                    self.logger.info("Shutdown requested during retry delay")
                    break
                
                # Exponential backoff
                retry_delay = min(retry_delay * 2, max_delay)
            else:
                # Clean shutdown requested
                break
        
        self.logger.info("MCP server stopped")
    
    def run(self):
        """Main process loop - runs the async MCP server."""
        try:
            # Use asyncio.run for cleaner event loop management
            asyncio.run(self.run_mcp_server())
        except Exception as e:
            self.logger.error(f"MCP server process error: {e}")
    
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        # Stop the MCP server if it's running
        if self._mcp_server:
            # Schedule the stop coroutine in the event loop
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(
                    self._mcp_server.stop(),
                    loop
                )
            except RuntimeError:
                # No event loop running yet or already stopped
                pass
    
    def cleanup(self):
        """Clean up resources when shutting down."""
        self.logger.info("Cleaning up MCP server...")
        
        # Parent cleanup handles any base resources
        super().cleanup()


def main():
    """Entry point for running as module."""
    process = MCPServerProcess(name="mcp_server")
    process.start()


if __name__ == "__main__":
    main()
