import asyncio
import aiohttp
from typing import Any
from finetune.processes.base import BaseProcess
from finetune.events import EventListener, handle_event

class EventsProcess(BaseProcess):
    """Process that listens for events via SSE."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown_event = None
        self._main_task = None
    
    async def run_event_listener(self):
        """Run the event listener with retry logic."""
        self._shutdown_event = asyncio.Event()
        retry_delay = 1  # Start with 1 second
        max_delay = 60   # Maximum 60 seconds between retries
        
        # Create a shared session for connection reuse
        timeout = aiohttp.ClientTimeout(sock_read=None)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while not self._shutdown_event.is_set():
                try:
                    self.logger.info("Starting event listener...")
                    
                    # Create event listener (optionally pass session if you modify EventListener)
                    event_listener = EventListener(handle_event)
                    
                    # Run listener until shutdown or connection closes
                    listener_task = asyncio.create_task(event_listener.start())
                    shutdown_task = asyncio.create_task(self._shutdown_event.wait())
                    
                    # Wait for either listener to finish or shutdown signal
                    done, pending = await asyncio.wait(
                        [listener_task, shutdown_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel the other task
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                    
                    # If shutdown was requested, exit
                    if shutdown_task in done:
                        self.logger.info("Shutdown requested, stopping event listener")
                        break
                        
                    # Otherwise, the listener finished (connection closed/error)
                    self.logger.warning("Event listener connection closed")
                    
                except aiohttp.ClientResponseError as e:
                    self.logger.error(f"HTTP error occurred: {e.status} - {e.message}")
                except asyncio.CancelledError:
                    self.logger.info("Event listener cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"An unexpected error occurred: {str(e)}")
                
                # Only retry if we're still supposed to be running
                if not self._shutdown_event.is_set():
                    self.logger.info(f"Retrying in {retry_delay}s...")
                    
                    try:
                        # Wait for either shutdown or timeout
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), 
                            timeout=retry_delay
                        )
                        # If we get here, shutdown was requested
                        self.logger.info("Shutdown requested during retry delay")
                        break
                    except asyncio.TimeoutError:
                        # Timeout expired, continue with retry
                        pass
                    
                    # Exponential backoff
                    retry_delay = min(retry_delay * 2, max_delay)
                else:
                    break
                    
        self.logger.info("Event listener stopped")
    
    def run(self):
        """Main process loop - runs the async event listener."""
        try:
            # Use asyncio.run for cleaner event loop management
            asyncio.run(self.run_event_listener())
        except Exception as e:
            self.logger.error(f"Event listener process error: {e}")
    
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        # Set the shutdown event if we have an event loop running
        if self._shutdown_event:
            # Get the event loop if it exists
            try:
                loop = asyncio.get_running_loop()
                # Thread-safe way to set the event
                asyncio.run_coroutine_threadsafe(
                    self._set_shutdown_event(),
                    loop
                )
            except RuntimeError:
                # No event loop running yet or already stopped
                pass
    
    async def _set_shutdown_event(self):
        """Set the shutdown event (must be called from async context)."""
        self._shutdown_event.set()
    
    def cleanup(self):
        """Clean up resources when shutting down."""
        self.logger.info("Cleaning up event listener...")
        
        # Parent cleanup handles redis client
        super().cleanup()


def main():
    """Entry point for running as module."""
    process = EventsProcess(name="events")
    process.start()


if __name__ == "__main__":
    main()
