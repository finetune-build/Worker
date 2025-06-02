import asyncio
import json
import ssl
import threading
import websockets
import time

from ftw.agent.registry import AGENT_REGISTRY
from ftw.conf import settings

# Global dictionary to track active threads by conversation_id
conversation_threads = {}

# Thread-safe lock to manage active_threads dictionary
thread_lock = threading.Lock()

# Flag to indicate if a thread should keep running
conversation_shutdown_event = threading.Event()

# Dictionary to track shutdown events for each conversation ID
shutdown_events = {}

# Modify the start_conversation_thread function to use shutdown events
def start_conversation_thread(conversation_id, content=None):
    """
    Starts a new thread for the conversation or joins an existing one.
    """
    with thread_lock:
        if conversation_id in conversation_threads:
            print(f"Conversation {conversation_id} already active. Joining existing thread.")
            # The thread is already running, return the existing thread
            return conversation_threads[conversation_id]
        else:
            print(f"Starting a new thread for conversation {conversation_id}.")
            # Create a shutdown event for the conversation ID
            shutdown_event = threading.Event()
            shutdown_events[conversation_id] = shutdown_event
            
            # Create and start the new thread
            new_thread = threading.Thread(target=run_conversation, args=(conversation_id, content, shutdown_event))
            new_thread.start()
            
            conversation_threads[conversation_id] = new_thread
            return new_thread

def shutdown_conversation_thread(conversation_id):
    """
    Sets the shutdown event for the specified conversation thread to stop it.
    """
    with thread_lock:
        if conversation_id in shutdown_events:
            print(f"Shutting down conversation thread for {conversation_id}.")
            shutdown_events[conversation_id].set()  # Signal the thread to stop
        else:
            print(f"No active thread found for conversation {conversation_id}.")

def run_conversation(conversation_id, content=None, shutdown_event=None):
    """
    The function to handle the WebSocket connection and conversation for a specific conversation_id.
    """
    asyncio.run(open_conversation_websocket(conversation_id, content, shutdown_event))

async def open_conversation_websocket(conversation_id, content=None, shutdown_event=None):
    uri = f"wss://{settings.DJANGO_HOST}/ws/conversation/{conversation_id}/machine/"
    headers = {
        "Authorization": f"Worker {settings.WORKER_TOKEN}",
        "X-Worker-ID": settings.WORKER_ID,
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(uri, additional_headers=headers, ssl=ssl_context) as websocket:
            print(f"WebSocket for conversation_id: {conversation_id} opened")

            async def respond_to_prompt(content):
                # message = {"type": "prompt_response", "content": {
                #     "state": "working",
                #     "worker_id": settings.WORKER_ID,
                # }}
                # await websocket.send(json.dumps(message))

                print(f"Responding to prompt: {content}")
                # response = generate_response(content)
                response = f"response to: {content}"
                # response = AGENT_REGISTRY["generate_text"](content)

                time.sleep(3)
                message = {
                    "jsonrpc": "2.0",
                    "method": "prompt_response",
                    "params": {
                        "content": response
                    }
                }
                await websocket.send(json.dumps(message))

            if content is not None:
                await respond_to_prompt(content)

            while not shutdown_event.is_set():
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    request = json.loads(message)

                    if request.get("jsonrpc") == "2.0" and "method" in request:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                        }

                        print(f"[WebSocket] Received: {request}")

                        if request.get("method") == "close":
                            print(f"WebSocket conversation {conversation_id} instructed to close.")
                            break
                        
                        elif request.get("method") == "prompt_query":
                            response["result"] = await respond_to_prompt(request["params"]["content"])

                        else:
                            response["error"] = {
                                "code": -32601,
                                "message": "Method not found"
                            }

                        await websocket.send(json.dumps(response))

                except asyncio.TimeoutError:
                    print("WebSocket timeout, checking for shutdown...")

                except websockets.exceptions.ConnectionClosed as e:
                    print(f"WebSocket connection closed: {e}")
                    break
                
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id") if 'request' in locals() else None,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
                    try:
                        await websocket.send(json.dumps(response))
                    except Exception as send_error:
                        print(f"Failed to send error response: {send_error}")
                        break



            # Close WebSocket after finishing
            await websocket.close()
            print(f"WebSocket for conversation_id {conversation_id} closed gracefully.")

    except Exception as e:
        print(f"WebSocket error: {e}")

    finally:
        with thread_lock:
            if conversation_id in conversation_threads:
                del conversation_threads[conversation_id]
            print(f"Cleaned up conversation thread {conversation_id}.")

        print("WebSocket conversation cleanup complete.")
