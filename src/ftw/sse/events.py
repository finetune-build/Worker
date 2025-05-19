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
    Handle JSON-RPC 2.0 formatted requests.
    """
    method = data.get("method")
    params = data.get("params", {})
    request_id = data.get("id")

    if method == "ping":
        print("Ping received. Sending pong...")
        await respond_to_ping()
        return {
            "jsonrpc": "2.0",
            "result": "pong",
            "id": request_id,
        }

    elif method == "tool":
        tool_name = params.get("tool_name")
        run_task_by_name(tool_name)
        print(f"Tool request received. Running tool: {tool_name}")
        return {
            "jsonrpc": "2.0",
            "result": f"Tool {tool_name} executed",
            "id": request_id,
        }

    elif method == "open_worker_websocket":
        print(f"Starting Worker Websocket Thread: {settings.WORKER_ID}")
        start_worker_thread(settings.WORKER_ID)
        return {
            "jsonrpc": "2.0",
            "result": f"Worker {settings.WORKER_ID} websocket opened",
            "id": request_id,
        }

    elif method == "open_conversation_websocket":
        content = params.get("content")
        conversation_id = params.get("conversation_id")
        print(f"Starting Conversation Websocket Thread: {conversation_id}")
        start_conversation_thread(conversation_id, content)
        return {
            "jsonrpc": "2.0",
            "result": f"Conversation {conversation_id} websocket opened",
            "id": request_id,
        }

    elif method == "close_conversation_websocket":
        conversation_id = params.get("conversation_id")
        print("Closing WebSocket connection for conversation in a thread...")
        shutdown_conversation_thread(conversation_id)
        return {
            "jsonrpc": "2.0",
            "result": f"Conversation {conversation_id} websocket closed",
            "id": request_id,
        }

    else:
        print(f"Received unknown method: {method}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found"
            },
            "id": request_id,
        }


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
