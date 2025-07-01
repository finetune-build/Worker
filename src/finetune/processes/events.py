import asyncio
from typing import Any
from finetune.processes.base import BaseProcess
from finetune.events import EventListener, handle_event


class EventsProcess(BaseProcess):
    """Process that listens for events via SSE."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_listener = None
        self.pubsub = None

    def setup_subscriptions(self):
        """Setup Redis subscriptions."""
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe(['events'])
        self.logger.info("Subscribed to events channel")
    
    async def run_event_listener(self):
        """Run the event listener with retry logic."""
        retry_delay = 1  # Start with 1 second
        max_delay = 60   # Maximum 60 seconds between retries
        
        while self.running:
            try:
                self.logger.info("Starting event listener...")
                
                # Create event listener - it will manage its own session
                self._event_listener = EventListener(handle_event)
                
                # Run listener until it completes or we're shutting down
                await self._event_listener.start()
                
                # If we get here, the connection closed
                if self.running:
                    self.logger.warning("Event listener connection closed")
                
            except asyncio.CancelledError:
                self.logger.info("Event listener cancelled")
                break
            except Exception as e:
                self.logger.error(f"An error occurred: {str(e)}")
            
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
                
        self.logger.info("Event listener stopped")
    
    def run(self):
        """Main process loop - runs the async event listener."""
        self.setup_subscriptions()

        try:
            # Use asyncio.run for cleaner event loop management
            asyncio.run(self.run_event_listener())
        except Exception as e:
            self.logger.error(f"Event listener process error: {e}")
    
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        # Stop the event listener if it's running
        if self._event_listener:
            # Schedule the stop coroutine in the event loop
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(
                    self._event_listener.stop(),
                    loop
                )
            except RuntimeError:
                # No event loop running yet or already stopped
                pass
    
    def cleanup(self):
        """Clean up resources when shutting down."""
        if self.pubsub:
            self.pubsub.close()

        self.logger.info("Cleaning up event listener...")
        
        # Parent cleanup handles redis client
        super().cleanup()


def main():
    """Entry point for running as module."""
    process = EventsProcess(name="events")
    process.start()


if __name__ == "__main__":
    main()
