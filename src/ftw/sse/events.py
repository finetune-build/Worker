import aiohttp
import json

from ftw.conf import settings
from ftw.sse.tasks import run_task_by_name
from ftw.sse.utils import * # Applies prepended print statement.
from ftw.ws.conversation import start_conversation_thread, shutdown_conversation_thread
from ftw.ws.worker import start_worker_thread

async def respond_to_ping():
    url = f"https://{settings.HOST}/v1/worker/{settings.WORKER_ID}/pong/"
    headers = {
        "Authorization": f"Worker {settings.WORKER_TOKEN}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post(
                url, ssl=False, json={"worker_id": settings.WORKER_ID}
            ) as resp:
                if resp.status != 200:
                    print(f"Failed to respond to ping. Status: {resp.status}")
        except Exception as e:
            print(f"Ping response error: {e}")

async def handle_event(data):
    """
    Default events expected from API server.
    """
    if data.get("type") == "ping":
        print(f"Ping received. Sending pong...")
        await respond_to_ping()

    elif data.get("type") == "tool":
        tool_name = data.get("tool_name")
        run_task_by_name(tool_name)
        print(f"Tool request received. Sending confirmation...")

    elif data.get("type") == "open_worker_websocket":
        print(f"Starting Worker Websocket Thread: {settings.WORKER_ID}")
        start_worker_thread(settings.WORKER_ID)

    elif data.get("type") == "open_conversation_websocket":
        content = data["data"]["content"]
        conversation_id = data["data"]["conversation_id"]
        print(f"Starting Conversation Websocket Thread: {conversation_id}")
        start_conversation_thread(conversation_id, content)

    # Not sure if necessary to be sent with SSE as this can
    # be done inside websocket.
    # Will keep around just in case.
    elif data.get("type") == "close_conversation_websocket":
        conversation_id = data["data"]["conversation_id"]
        print("Closing WebSocket connection for conversation in a thread...")
        shutdown_conversation_thread(conversation_id)

    else:
        print(f"Received message: {data}")

async def listen_for_events(on_event):
    url = f"https://{settings.HOST}/v1/worker/{settings.WORKER_ID}/sse/"
    headers = {"Authorization": f"Worker {settings.WORKER_TOKEN}"}

    timeout = aiohttp.ClientTimeout(sock_read=None)  # Disable read timeout
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(url, ssl=False) as response:
            print(f"Connected as {settings.WORKER_ID}, status: {response.status}")

            if response.status != 200:
                error_details = await response.text()
                print(f"Error details: {error_details}")
                response.raise_for_status()

            async for line in response.content:
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data:"):
                    message = decoded[5:].strip()
                    try:
                        data = json.loads(message)
                        await on_event(data)
                    except json.JSONDecodeError:
                        print(f"Received non-JSON message: {message}")
                elif decoded.startswith(":"):
                    print(f"Heartbeat")
