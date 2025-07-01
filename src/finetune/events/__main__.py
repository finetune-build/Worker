import aiohttp
import asyncio
import json
from typing import Callable
from finetune.conf import settings


class EventListener:
    def __init__(self, on_event: Callable):
        self.on_event = on_event
        self.session = None
        self._stop_event = asyncio.Event()
        self.url = f"https://{settings.DJANGO_HOST}/v1/worker/{settings.WORKER_ID}/sse/"
        self.headers = {
            "Authorization": f"Access {settings.ACCESS_TOKEN}",
            "X-Worker-ID": settings.WORKER_ID,
            "X-Session-ID": str(settings.SESSION_UUID),
            "X-Client-Role": "machine",
        }
    
    async def start(self):
        """
        Opens stream with API server for SSE.
        """
        # Create session with no read timeout for SSE
        timeout = aiohttp.ClientTimeout(sock_read=None)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            async with self.session.get(self.url, ssl=False, headers=self.headers) as response:
                if response.status != 200:
                    error_details = await response.text()
                    print(f"Error details: {error_details}")
                    response.raise_for_status()
                
                print(f"Connected as {settings.WORKER_ID}, status: {response.status}")
                
                # Read stream until stopped or connection closes
                async for line in response.content:
                    # Check if we should stop
                    if self._stop_event.is_set():
                        print("Stop requested, closing connection")
                        break
                        
                    decoded = line.decode("utf-8").strip()
                    if decoded.startswith("data:"):
                        message = decoded[5:].strip()
                        try:
                            data = json.loads(message)
                            await self.on_event(data)
                        except json.JSONDecodeError:
                            print(f"Received non-JSON message: {message}")
                    elif decoded.startswith(":"):
                        print("Heartbeat")
                        
        finally:
            # Always clean up session
            await self.session.close()
    
    async def stop(self):
        """Stop the event listener gracefully."""
        self._stop_event.set()
    
    def is_running(self) -> bool:
        """Check if the listener is still running."""
        return not self._stop_event.is_set()
