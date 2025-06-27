import asyncio
import json
import ssl
import threading
import time
import websockets

from finetune_sdk.conf import settings

# Should only be one worker websocket thread per each worker process.
# Separate threads / processes should be made for cases when the worker is
# handling multiple tasks in parallel, but only one worker websocket thread
# would be need at a given time.
# (i.e. two worker programs running this script would have two different
# worker websocket thread references)
worker_websocket_thread = None
shutdown_event = None

def worker_start_websocket_thread():
    """
    Starts the worker websocket thread if not already running.
    """
    global worker_websocket_thread, shutdown_event
    if worker_websocket_thread is not None and worker_websocket_thread.is_alive():
        return worker_websocket_thread
    print("Starting new worker websocket thread.")
    shutdown_event = threading.Event()
    worker_websocket_thread = threading.Thread(
        target=run_websocket, args=(shutdown_event,), daemon=True
    )
    worker_websocket_thread.start()
    return worker_websocket_thread

def worker_shutdown_websocket_thread():
    """
    Signals the websocket thread to shut down.
    """
    global shutdown_event
    if shutdown_event is not None:
        shutdown_event.set()

def run_websocket(shutdown_event):
    """
    Target function for the websocket thread.
    """
    client = WorkerWebSocketClient(shutdown_event)
    asyncio.run(client.run())

class WorkerWebSocketClient:
    def __init__(self, shutdown_event):
        self.shutdown_event = shutdown_event
        self.websocket = None

    async def respond_to_prompt(self, content):
        print(f"Responding to prompt: {content}")
        # Simulate processing time
        time.sleep(3)
        # You can use AGENT_REGISTRY here if needed
        response = f"response to: {content}"
        return response

    async def handle_message(self, request):
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
        }
        try:
            method = request.get("method")
            if method == "close":
                print(f"WebSocket worker {settings.WORKER_ID} instructed to close.")
                response["result"] = "closed"
                await self.websocket.send(json.dumps(response))
                return "close"
            elif method == "prompt_query":
                content = request["params"]["content"]
                result = await self.respond_to_prompt(content)
                response["result"] = result
            else:
                response["error"] = {
                    "code": -32601,
                    "message": "Method not found"
                }
            await self.websocket.send(json.dumps(response))
        except Exception as e:
            print(f"Error handling message: {e}")
            response["error"] = {
                "code": -32603,
                "message": str(e)
            }
            await self.websocket.send(json.dumps(response))

    async def run(self):
        uri = f"wss://{settings.DJANGO_HOST}/ws/worker/{settings.WORKER_ID}/machine/"
        headers = {
            "Authorization": f"Access {settings.ACCESS_TOKEN}",
            "X-Worker-ID": settings.WORKER_ID,
            "X-Session-ID": str(settings.SESSION_UUID),
        }
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            async with websockets.connect(uri, additional_headers=headers, ssl=ssl_context) as websocket:
                self.websocket = websocket
                print(f"WebSocket for worker_id: {settings.WORKER_ID} opened")

                while not self.shutdown_event.is_set():
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        request = json.loads(message)
                        print(f"[WebSocket] Received: {request}")

                        if request.get("jsonrpc") == "2.0" and "method" in request:
                            result = await self.handle_message(request)
                            if result == "close":
                                break
                        else:
                            print("Invalid JSON-RPC message received.")

                    except asyncio.TimeoutError:
                        print("WebSocket timeout, checking for shutdown...")

                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"WebSocket connection closed: {e}")
                        break

                    except Exception as e:
                        print(f"Unexpected error: {e}")
                        # Try to send error response if possible
                        try:
                            response = {
                                "jsonrpc": "2.0",
                                "id": request.get("id") if 'request' in locals() else None,
                                "error": {
                                    "code": -32603,
                                    "message": str(e)
                                }
                            }
                            await websocket.send(json.dumps(response))
                        except Exception as send_error:
                            print(f"Failed to send error response: {send_error}")
                            break

                await websocket.close()
                print(f"WebSocket for worker_id {settings.WORKER_ID} closed gracefully.")

        except Exception as e:
            print(f"WebSocket error: {e}")

        finally:
            global worker_websocket_thread
            worker_websocket_thread = None
            print("WebSocket worker cleanup complete.")
