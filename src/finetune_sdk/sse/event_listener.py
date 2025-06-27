import asyncio
import aiohttp
import json

from finetune_sdk.api.worker import get_worker_task_list

from finetune_sdk.conf import settings
# from finetune_sdk.sse.utils import * # Applies prepended print statement.
# from finetune_sdk.ws.worker import worker_start_websocket_thread

class EventListener:
    def __init__(self, on_event):
        self.on_event = on_event
        self.pending_tasks = []
        self._shutdown = asyncio.Event()
        self.url = f"https://{settings.DJANGO_HOST}/v1/worker/{settings.WORKER_ID}/sse/"
        self.headers = {
            "Authorization": f"Access {settings.ACCESS_TOKEN}",
            "X-Worker-ID": settings.WORKER_ID,
            "X-Session-ID": str(settings.SESSION_UUID),
            "X-Client-Role": "machine",
        }
        self.client = None

    async def start(self):
        """
        Opens stream with API server for SSE.
        """
        timeout = aiohttp.ClientTimeout(sock_read=None)
        self.client = aiohttp.ClientSession(timeout=timeout, headers=self.headers)
        async with self.client as session:
            async with session.get(self.url, ssl=False) as response:
                if response.status != 200:
                    error_details = await response.text()
                    print(f"Error details: {error_details}")
                    response.raise_for_status()

                print(f"Connected as {settings.WORKER_ID}, status: {response.status}")
                # await self.synchronize()

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
                        print(f"Heartbeat")

    async def synchronize(self):
        print(f"Retrieving Tasks...")
        task_list_response = await get_worker_task_list()
        if task_list_response["success"]:
            self.worker_tasks = task_list_response["data"]["results"]
            print(f"{task_list_response['data']['count']} Submitted Worker Tasks")
            # worker_start_websocket_thread()

    async def shutdown(self):
        self._shutdown.set()
        if self.client:
            await self.client.close()
