# process_manager.py
import asyncio
import json
import logging
from typing import Any
from finetune.processes.base import BaseProcess
from finetune.mcp import HTTPClient

# Ensure logging is configured
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class MCPHTTPClientProcess(BaseProcess):
    def __init__(self, channels=['mcp_requests'], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mcp_client = None
        self.pubsub = None
        self.channels = channels
        self._client_ready = asyncio.Event()  # Track when client is ready
        
    def setup_subscriptions(self):
        """Set up Redis pubsub"""
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe(self.channels)
        self.logger.info(f"Subscribed to channels: {self.channels}")
        
    async def process_redis_messages(self):
        """Process Redis messages using sync pubsub in async context"""
        while self.running:
            try:
                # Run the blocking call in a thread pool to not block the event loop
                loop = asyncio.get_event_loop()
                message = await loop.run_in_executor(
                    None,  # Use default executor
                    self.pubsub.get_message,
                    0.1    # timeout - your wrapper doesn't support ignore_subscribe_messages
                )
                
                if message and message['type'] == 'message':
                    # Your PubSubWrapper already deserializes JSON data
                    data = message['data']
                    
                    # Check if data is valid jsonrpc
                    if isinstance(data, dict) and data.get("jsonrpc") == '2.0':
                        # Request data, wraps around actual mcp jsonrpc request.
                        await self.mcp_client_handle_request(data)
                
                # Small sleep to prevent tight loop
                await asyncio.sleep(0.01)
                        
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error(f"Error in Redis message processor: {e}")
                await asyncio.sleep(0.1)
                
    async def mcp_client_handle_request(self, data):
        """Handle requests for MCP client"""
        # Wait for client to be ready using event
        try:
            await asyncio.wait_for(self._client_ready.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self.logger.error("MCP client not ready after 5 seconds")
            return
            
        try:
            response = await self._mcp_client.handle_request(data)
            self.logger.info(f"MCP Client Response: {response}")
        except Exception as e:
            self.logger.error(f"Error routing message to MCP: {e}")
            
    async def run_mcp_client(self):
        """Run the MCP client with proper async handling"""
        retry_delay = 1
        max_delay = 60
        
        while self.running:
            try:
                self.logger.info("Starting MCP HTTP client...")
                self._mcp_client = HTTPClient(redis_client=self.redis_client)
                
                # Create a wrapper task for the client that sets the ready event
                async def client_wrapper():
                    try:
                        # Wait a moment for initialization
                        await asyncio.sleep(0.1)
                        self._client_ready.set()
                        await self._mcp_client.start()
                    finally:
                        self._client_ready.clear()
                
                # Create tasks
                client_task = asyncio.create_task(
                    client_wrapper(),
                    name="mcp_client"
                )
                redis_task = asyncio.create_task(
                    self.process_redis_messages(),
                    name="redis_processor"
                )
                
                self.logger.info("Started MCP client and Redis processor tasks")
                
                # Run both tasks concurrently
                done, pending = await asyncio.wait(
                    [client_task, redis_task],
                    return_when=asyncio.FIRST_EXCEPTION
                )
                
                # Check which task failed
                for task in done:
                    if task.exception():
                        self.logger.error(
                            f"Task {task.get_name()} failed with: {task.exception()}"
                        )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
            except asyncio.CancelledError:
                self.logger.info("MCP client cancelled")
                break
            except Exception as e:
                self.logger.error(f"MCP client error: {e}", exc_info=True)
            finally:
                if self._mcp_client:
                    try:
                        await self._mcp_client.stop()
                    except Exception as e:
                        self.logger.error(f"Error stopping MCP client: {e}")
                    self._mcp_client = None
                    
            if self.running:
                self.logger.info(f"Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
            else:
                break
                
        self.logger.info("MCP client stopped")
        
    def run(self):
        """Main entry point"""
        self.setup_subscriptions()
        try:
            asyncio.run(self.run_mcp_client())
        except Exception as e:
            self.logger.error(f"MCP client process error: {e}")
            
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self._mcp_client:
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(
                    self._mcp_client.stop(),
                    loop
                )
            except RuntimeError:
                pass
                
    def cleanup(self):
        """Cleanup resources"""
        if self.pubsub:
            self.pubsub.close()
        self.logger.info("Cleaning up MCP client...")
        super().cleanup()

def main():
    process = MCPHTTPClientProcess(name="mcp_client")
    process.start()

if __name__ == "__main__":
    main()