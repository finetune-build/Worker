import asyncio
from contextlib import asynccontextmanager

from ftw.sse.events import handle_event
from ftw.sse.event_listener import EventListener

def create_lifespan(on_event = handle_event):
    @asynccontextmanager
    async def lifespan(app):
        try:
            # Setup phase
            print("Starting SSE event listener...")
            event_listener = EventListener(on_event)
            task = asyncio.create_task(event_listener.start())
            yield
        finally:
            # Cleanup phase
            print("Shutting down SSE event listener...")
            await event_listener.shutdown()
            print("SSE event listener shutdown complete")
    
    return lifespan