import asyncio
from typing import Any
from finetune.processes.base import BaseProcess
from finetune.events import EventListener

class EventsProcess(BaseProcess):
    """Process that listens for events via SSE and processes Redis messages."""
    
    def __init__(self, channels=['mcp_responses'], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_listener = None
        self.pubsub = None
        self.channels = channels
        self._redis_task = None
        self._event_task = None

    def setup_subscriptions(self):
        """Setup Redis subscriptions."""
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe(self.channels)
        self.logger.info(f"Subscribed to channels: {self.channels}")

    async def handle_redis_message(self, data):
        """Handle incoming Redis messages."""
        method = data.get("method")
        params = data.get("params", {})
        
        if method == "mcp_response":
            self.logger.info(f"Received MCP response: {params}")
            # Handle MCP response here
            
        elif method == "worker_notification":
            self.logger.info(f"Received worker notification: {params}")
            # Handle worker notifications
            
        else:
            self.logger.warning(f"Unknown Redis message method: {method}")

    async def process_redis_messages(self):
        """Process Redis messages in background."""
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                print(f"message: {message}")
                if message and message['type'] == 'message':
                    data = message["data"]
                    channel = message["channel"]
                    if isinstance(data, dict) and data.get("jsonrpc") == '2.0':
                        # await self.handle_redis_message(data)
                        print(f"channel: {channel}")
                        if channel == "mcp_responses":
                            await self._event_listener.send_worker_mcp_response(data)
            except Exception as e:
                self.logger.error(f"Error in Redis message processor: {e}")
            
            # CRITICAL: Add a small delay to yield control to other tasks
            await asyncio.sleep(0.01)

    async def run_event_listener_with_redis(self):
        """Run event listener and Redis processor concurrently using asyncio.wait."""
        retry_delay = 1
        max_delay = 60

        while self.running:
            try:
                self.logger.info("Starting event listener...")
                self._event_listener = EventListener(self.redis_client)

                # Create tasks but don't use gather() - use wait() instead
                self._event_task = asyncio.create_task(self._event_listener.start())
                self._redis_task = asyncio.create_task(self.process_redis_messages())

                # Use asyncio.wait with FIRST_EXCEPTION instead of gather
                done, pending = await asyncio.wait(
                    [self._event_task, self._redis_task],
                    return_when=asyncio.FIRST_EXCEPTION
                )

                # Handle completed tasks
                for task in done:
                    if task.exception():
                        exc = task.exception()
                        self.logger.error(f"Task failed with exception: {exc}")
                        # Re-raise the exception to trigger retry
                        raise exc

                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # If we get here without exception, connection closed normally
                if self.running:
                    self.logger.warning("Event listener connection closed normally")

            except asyncio.CancelledError:
                self.logger.info("Event listener cancelled")
                break
            except Exception as e:
                self.logger.error(f"Event listener error: {e}")
            finally:
                # Clean up event listener
                if self._event_listener:
                    try:
                        await self._event_listener.stop()
                    except Exception as e:
                        self.logger.error(f"Error stopping event listener: {e}")
                    self._event_listener = None
                
                # Clean up tasks
                if self._event_task and not self._event_task.done():
                    self._event_task.cancel()
                if self._redis_task and not self._redis_task.done():
                    self._redis_task.cancel()

            if self.running:
                self.logger.info(f"Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)

        self.logger.info("Event listener stopped")

    def run(self):
        """Main process loop."""
        self.setup_subscriptions()
        try:
            asyncio.run(self.run_event_listener_with_redis())
        except Exception as e:
            self.logger.error(f"Event listener process error: {e}")
    
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        if self._event_listener:
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(
                    self._event_listener.stop(),
                    loop
                )
            except RuntimeError:
                pass
    
    def cleanup(self):
        """Clean up resources when shutting down."""
        if self.pubsub:
            self.pubsub.close()
        self.logger.info("Cleaning up event listener...")
        super().cleanup()


def main():
    """Entry point for running as module."""
    process = EventsProcess(name="events")
    process.start()


if __name__ == "__main__":
    main()