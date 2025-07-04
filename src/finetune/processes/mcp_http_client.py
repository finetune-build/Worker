# process_manager.py
import asyncio
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

    def setup_subscriptions(self):
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe(self.channels)
        self.logger.info(f"Subscribed to channels: {self.channels}")

    async def process_redis_messages(self):
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                print(f"message: {message}")
                if message and message['type'] == 'message':
                    data = message["data"]
                    # Check if data is valid jsonrpc first
                    if isinstance(data, dict) and data.get("jsonrpc") == '2.0':
                        await self.mcp_client_handle_request(data)
            except Exception as e:
                self.logger.error(f"Error in Redis message processor: {e}")

    async def mcp_client_handle_request(self, data):
        try:
            response = await self._mcp_client.handle_request(data)
            self.logger.info(f"MCP Client Response: {response}")
        except Exception as e:
            self.logger.error(f"Error routing message to MCP: {e}")

    async def run_mcp_client(self):
        retry_delay = 1
        max_delay = 60

        while self.running:
            try:
                self.logger.info("Starting MCP HTTP client...")
                self._mcp_client = HTTPClient(redis_client=self.redis_client)

                # Run MCP client in background
                client_task = asyncio.create_task(self._mcp_client.start())

                # Run other async tasks concurrently
                await asyncio.gather(
                    client_task,
                    self.process_redis_messages(),
                )

            except asyncio.CancelledError:
                self.logger.info("MCP client cancelled")
                break
            except Exception as e:
                self.logger.error(f"MCP client error: {e}")
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
        self.setup_subscriptions()
        try:
            asyncio.run(self.run_mcp_client())
        except Exception as e:
            self.logger.error(f"MCP client process error: {e}")

    def _shutdown(self, signum: int, frame: Any):
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
        if self.pubsub:
            self.pubsub.close()
        self.logger.info("Cleaning up MCP client...")
        super().cleanup()

def main():
    process = MCPHTTPClientProcess(name="mcp_client")
    process.start()

if __name__ == "__main__":
    main()
