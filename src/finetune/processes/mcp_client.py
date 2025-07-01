import asyncio
import json
from typing import Any, Dict
from finetune.processes.base import BaseProcess
from finetune.mcp import MCPClient  # Assuming you put MCPClient in a module


class MCPClientProcess(BaseProcess):
    """Process for spinning up MCP client to communicate with MCP server."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mcp_client = None
        self.pubsub = None
        self._request_queue = asyncio.Queue()
        self._response_channel = 'mcp_responses'
        self._request_channel = 'mcp_requests'
    
    def setup_subscriptions(self):
        """Setup Redis subscriptions."""
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe([self._request_channel])
        self.logger.info(f"Subscribed to {self._request_channel} channel")
    
    async def handle_mcp_response(self, response: Dict[str, Any]):
        """Handle responses from MCP server."""
        try:
            # Publish response back to Redis
            self.redis_client.publish(self._response_channel, response)
            self.logger.info(f"Published MCP response: {response.get('id')}")
        except Exception as e:
            self.logger.error(f"Error publishing MCP response: {e}")
    
    async def process_redis_messages(self):
        """Process incoming Redis messages and queue them for MCP."""
        while self.running:
            try:
                # Get message with timeout
                message = self.pubsub.get_message(timeout=0.1)
                
                if message and message['type'] == 'message':
                    channel = message.get('channel', b'').decode('utf-8')
                    data = message.get('data')
                    
                    if channel == self._request_channel and data:
                        try:
                            # Parse the request
                            if isinstance(data, bytes):
                                data = data.decode('utf-8')
                            request = json.loads(data) if isinstance(data, str) else data
                            
                            # Add to queue for processing
                            await self._request_queue.put(request)
                            self.logger.info(f"Queued MCP request: {request.get('method')}")
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Invalid JSON in request: {e}")
                        except Exception as e:
                            self.logger.error(f"Error processing Redis message: {e}")
                
                await asyncio.sleep(0.01)  # Small delay to prevent busy loop
                
            except Exception as e:
                self.logger.error(f"Error in Redis message loop: {e}")
                await asyncio.sleep(1)
    
    async def process_mcp_requests(self):
        """Process queued MCP requests."""
        while self.running:
            try:
                # Wait for request with timeout
                request = await asyncio.wait_for(
                    self._request_queue.get(), 
                    timeout=1.0
                )
                
                if self._mcp_client and self._mcp_client.is_running():
                    # Send request to MCP server
                    await self._mcp_client.handle_request(request)
                else:
                    self.logger.warning("MCP client not running, dropping request")
                    
                    # Send error response
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": "MCP client not connected"
                        },
                        "id": request.get("id")
                    }
                    await self.handle_mcp_response(error_response)
                    
            except asyncio.TimeoutError:
                # Normal timeout, continue
                pass
            except Exception as e:
                self.logger.error(f"Error processing MCP request: {e}")
    
    async def run_mcp_client(self):
        """Run the MCP client with retry logic."""
        retry_delay = 1  # Start with 1 second
        max_delay = 60   # Maximum 60 seconds between retries
        
        while self.running:
            try:
                self.logger.info("Starting MCP client...")
                
                # Create MCP client
                self._mcp_client = MCPClient(on_event=self.handle_mcp_response)
                
                # Start the client
                await self._mcp_client.start()
                
                # Run both Redis message processor and MCP request processor
                await asyncio.gather(
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
