import aiohttp
import json

from finetune.conf import settings

class EventListener:
    def __init__(self, on_event):
        self.on_event = on_event
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
        timeout = aiohttp.ClientTimeout(sock_read=None)
        
        async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
            async with session.get(self.url, ssl=False) as response:
                if response.status != 200:
                    error_details = await response.text()
                    print(f"Error details: {error_details}")
                    response.raise_for_status()
                
                print(f"Connected as {settings.WORKER_ID}, status: {response.status}")
                
                async for line in response.content:
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
    