import asyncio
import json
import ssl
import threading
import websockets

from ftw.agent.registry import AGENT_REGISTRY
from ftw.conf import settings

# Global dictionary to track active threads by worker_id
worker_threads = {}

# Thread-safe lock to manage active_threads dictionary
thread_lock = threading.Lock()

# Flag to indicate if a thread should keep running
worker_shutdown_event = threading.Event()

# Dictionary to track shutdown events for each worker ID
shutdown_events = {}

# Modify the start_worker_thread function to use shutdown events
def start_worker_thread():
    """
    Starts a new thread for the worker or joins an existing one.
    """
    with thread_lock:
        if settings.WORKER_ID in worker_threads:
            print(f"worker {settings.WORKER_ID} already active. Joining existing thread.")
            # The thread is already running, return the existing thread
            return worker_threads[settings.WORKER_ID]
        else:
            print(f"Starting a new thread for worker {settings.WORKER_ID}.")
            # Create a shutdown event for the worker ID
            shutdown_event = threading.Event()
            shutdown_events[settings.WORKER_ID] = shutdown_event
            
            # Create and start the new thread
            new_thread = threading.Thread(target=run_worker, args=(shutdown_event))
            new_thread.start()
            
            worker_threads[settings.WORKER_ID] = new_thread
            return new_thread

def shutdown_worker_thread():
    """
    Sets the shutdown event for the specified worker thread to stop it.
    """
    with thread_lock:
        if settings.WORKER_ID in shutdown_events:
            print(f"Shutting down worker thread for {settings.WORKER_ID}.")
            shutdown_events[settings.WORKER_ID].set()  # Signal the thread to stop
        else:
            print(f"No active thread found for worker {settings.WORKER_ID}.")

def run_worker(shutdown_event=None):
    """
    The function to handle the WebSocket connection and worker for a specific worker_id.
    """
    asyncio.run(open_worker_websocket(shutdown_event))

async def open_worker_websocket(shutdown_event=None):
    uri = f"wss://{settings.HOST}/ws/worker/{settings.WORKER_ID}/machine/"
    headers = {
        "Authorization": f"Worker {settings.WORKER_TOKEN}",
        "X-Worker-ID": settings.WORKER_ID,
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(uri, additional_headers=headers, ssl=ssl_context) as websocket:
            print(f"WebSocket for worker_id: {settings.WORKER_ID} opened")

            async def respond_to_prompt(content):
                print(f"Responding to prompt: {content}")
                # response = generate_response(content)
                # response = f"response to: {content}"
                response = AGENT_REGISTRY["generate_text"](content)
                message = {"type": "prompt_response", "content": response}
                await websocket.send(json.dumps(message))

            if content is not None:
                await respond_to_prompt(content)

            while not shutdown_event.is_set():  # Check if the shutdown event is set
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(message)

                    print(f"[WebSocket] Received: {data}")

                    if data.get("type") == "close":
                        print(f"WebSocket worker {settings.WORKER_ID} instructed to close.")
                        break

                    elif data.get("type") == "prompt_query":
                        content = data["data"]["content"]
                        await respond_to_prompt(content)

                except asyncio.TimeoutError:
                    print("WebSocket timeout, checking for shutdown...")

                except websockets.exceptions.ConnectionClosed as e:
                    print(f"WebSocket connection closed: {e}")
                    break

            # Close WebSocket after finishing
            await websocket.close()
            print(f"WebSocket for worker_id {settings.WORKER_ID} closed gracefully.")

    except Exception as e:
        print(f"WebSocket error: {e}")

    finally:
        with thread_lock:
            if settings.WORKER_ID in worker_threads:
                del worker_threads[settings.WORKER_ID]
            print(f"Cleaned up worker thread {settings.WORKER_ID}.")

        print("WebSocket worker cleanup complete.")
