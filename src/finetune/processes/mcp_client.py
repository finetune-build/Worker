import asyncio
from typing import Any

from finetune.processes.base import BaseProcess
from finetune.mcp import MCPClient

class MCPClientProcess(BaseProcess):
    """Process for spinning up MCP client to communicate with MCP server."""
    
    def __init__(self, channels = ['events'], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mcp_client = None
        self.pubsub = None
        self.channels = channels
    
    def setup_subscriptions(self):
        """Setup Redis subscriptions."""
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe(self.channels)
        self.logger.info(f"Subscribed to channels: {self.channels}")
    
    async def handle_mcp_event(self, event: dict):
        """Handle events from the MCP client."""
        self.logger.info(f"Received MCP event: {event}")
        # Add your event handling logic here
    
    async def process_redis_messages(self):
        """Process incoming Redis messages."""
        try:
            while self.running:
                # Check for Redis messages with timeout
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    try:
                        # Process the message
                        self.logger.info(f"Processing Redis message: {message}")
                        # Add your Redis message processing logic here

                        data = message["data"]
                        if isinstance(data, dict) and data.get("jsonrpc") == '2.0':
                            await self.mcp_client_handle_request(data)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing Redis message: {e}")
                
                # Small delay to prevent busy loop
                await asyncio.sleep(0.01)
                
        except Exception as e:
            self.logger.error(f"Error in Redis message processor: {e}")

    async def mcp_client_handle_request(self, data):
        try:
            response = await self._mcp_client.handle_request(data)
            self.logger.info(f"MCP Client Response: {response}")
        except Exception as e:
            self.logger.error(f"Error routing message to MCP: {e}")
    
    async def process_mcp_requests(self):
        """Process MCP requests."""
        try:
            while self.running and self._mcp_client and self._mcp_client.is_running():
                # Example: process any queued MCP requests
                # This is where you'd handle incoming requests to your MCP client
                
                # For now, just check if client is still running
                await asyncio.sleep(1.0)
                
        except Exception as e:
            self.logger.error(f"Error in MCP request processor: {e}")
    
    async def run_mcp_client(self):
        """Run the MCP client with retry logic."""
        retry_delay = 1  # Start with 1 second
        max_delay = 60   # Maximum 60 seconds between retries
        
        while self.running:
            try:
                self.logger.info("Starting MCP client...")
                
                # Create MCP client with event handler
                self._mcp_client = MCPClient(on_event=self.handle_mcp_event)
                
                # Start the client in background (non-blocking)
                await self._mcp_client.start_background()
                
                # Run message processing concurrently with MCP client
                await asyncio.gather(
                    self._mcp_client._client_task,  # Wait for MCP client to finish
                    self.process_redis_messages(),
                    self.process_mcp_requests(),
                    return_exceptions=True
                )
                
                # If we get here, something stopped
                if self.running:
                    self.logger.warning("MCP client stopped unexpectedly")
                
            except asyncio.CancelledError:
                self.logger.info("MCP client cancelled")
                break
            except Exception as e:
                self.logger.error(f"MCP client error: {e}")
            
            finally:
                # Stop the client if it's running
                if self._mcp_client:
                    try:
                        await self._mcp_client.stop()
                    except Exception as e:
                        self.logger.error(f"Error stopping MCP client: {e}")
                    self._mcp_client = None
            
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
        
        self.logger.info("MCP client stopped")
    
    def run(self):
        """Main process loop - runs the async MCP client."""
        self.setup_subscriptions()
        try:
            # Use asyncio.run for cleaner event loop management
            asyncio.run(self.run_mcp_client())
        except Exception as e:
            self.logger.error(f"MCP client process error: {e}")
    
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        # Stop the MCP client if it's running
        if self._mcp_client:
            # Schedule the stop coroutine in the event loop
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(
                    self._mcp_client.stop(),
                    loop
                )
            except RuntimeError:
                # No event loop running yet or already stopped
                pass
    
    def cleanup(self):
        """Clean up resources when shutting down."""
        if self.pubsub:
            self.pubsub.close()
        self.logger.info("Cleaning up MCP client...")
        
        # Parent cleanup handles redis client
        super().cleanup()


def main():
    """Entry point for running as module."""
    process = MCPClientProcess(name="mcp_client")
    process.start()


if __name__ == "__main__":
    main()