import websockets
import json
import ssl
import os

HOST = os.environ.get("FINETUNE_HOST", "api.finetune.build")
WORKER_ID = os.environ.get("FINETUNE_WORKER_ID")
WORKER_TOKEN = os.environ.get("FINETUNE_WORKER_TOKEN")

async def open_websocket_connection(worker_instance_id, worker_token):
    uri = f"wss://{HOST}/ws/worker/{worker_instance_id}/machine/"
    headers = {"Authorization": f"Worker {worker_token}"}

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with websockets.connect(
        uri, additional_headers=headers, ssl=ssl_context
    ) as websocket:
        print(f"WebSocket connection established for {worker_instance_id}")

        async def respond_to_ping():
            pong_message = {"type": "pong", "status": "ok"}
            await websocket.send(json.dumps(pong_message))

        while True:
            try:
                message = await websocket.recv()
                print(f"WebSocket message received: {message}")

                data = json.loads(message)
                if data.get("type") == "ping":
                    print(f"Ping received via WebSocket. Sending pong...")
                    await respond_to_ping()

                else:
                    print(f"Received WebSocket message: {data}")

            except websockets.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting...")
                break

# import asyncio
# import threading

# from threading import Lock

# conversation_thread_running = False
# conversation_thread_lock = Lock()

# def open_conversation_websocket_thread(conversation_id, content = None):
#     global conversation_thread_running

#     def thread_target():
#         global conversation_thread_running
#         try:
#             asyncio.run(open_conversation_websocket(conversation_id, content))
#         finally:
#             with conversation_thread_lock:
#                 conversation_thread_running = False  # Reset after it finishes

#     with conversation_thread_lock:
#         if conversation_thread_running:
#             print("Conversation WebSocket already running. Skipping.")
#             return
#         conversation_thread_running = True

#     thread = threading.Thread(target=thread_target, daemon=True)
#     thread.start()

# conversation_shutdown_event = asyncio.Event()

# def shutdown_conversation_websocket():
#     conversation_shutdown_event.set()

# import asyncio
# import websockets
# import ssl
# import json
# import os

# async def open_conversation_websocket(conversation_id, content=None):
#     uri = f"wss://{os.environ.get('DJANGO_HOST')}/ws/conversation/{conversation_id}/machine/"
#     headers = {
#         "Authorization": f"Worker {os.environ.get('WORKER_TOKEN')}",
#         "X-Worker-ID": os.environ.get("WORKER_ID"),
#     }

#     # Set up SSL context for WebSocket connection
#     ssl_context = ssl.create_default_context()
#     ssl_context.check_hostname = False
#     ssl_context.verify_mode = ssl.CERT_NONE

#     try:
#         async with websockets.connect(uri, additional_headers=headers, ssl=ssl_context) as websocket:
#             print(f"WebSocket for conversation_id: {conversation_id} opened")

#             async def respond_to_prompt(content):
#                 print(f"Responding to prompt: {content}")
#                 response = generate_response(content)
#                 message = {"type": "prompt_response", "content": response}
#                 print(message)
#                 await websocket.send(json.dumps(message))

#             # Initial response if content is attached
#             if content is not None:
#                 await respond_to_prompt(content)
#                 print('sent message')

#             # # Keep-alive task to ensure connection remains open
#             # async def keep_alive():
#             #     while conversation_thread_running:
#             #         try:
#             #             if websocket.open:
#             #                 await websocket.send(json.dumps({"type": "ping"}))  # Send a ping every 30 seconds
#             #             await asyncio.sleep(30)  # Ping every 30 seconds
#             #         except Exception as e:
#             #             print(f"Error in keep-alive task: {e}")
#             #             break

#             # # Start the keep-alive task in the background
#             # keep_alive_task = asyncio.create_task(keep_alive())

#             while not conversation_shutdown_event.is_set():
#                 try:
#                     message = await asyncio.wait_for(websocket.recv(), timeout=10)  # 10s timeout for responsiveness
#                     data = json.loads(message)

#                     # Handle incoming messages
#                     print(f"[WebSocket] Received: {data}")

#                     if data.get("type") == "close":
#                         print("WebSocket conversation instructed to close.")
#                         break

#                     elif data.get("type") == "prompt_query":
#                         content = data["data"]["content"]
#                         print(f"Prompt query message received: {content}")
#                         await respond_to_prompt(content)

#                 except asyncio.TimeoutError:
#                     print("WebSocket timeout, checking for shutdown...")

#                 except websockets.exceptions.ConnectionClosed as e:
#                     print(f"WebSocket connection closed: {e}")
#                     break

#             # Close WebSocket after finishing
#             await websocket.close()
#             print("WebSocket closed gracefully.")

#     except Exception as e:
#         print(f"WebSocket error: {e}")

#     finally:
#         with conversation_thread_lock:
#             global conversation_thread_running
#             conversation_thread_running = False
#             print("Cleaned up thread flag.")

#         # # Ensure that the keep-alive task is canceled when the conversation is done
#         # if keep_alive_task:
#         #     keep_alive_task.cancel()
#         #     await keep_alive_task  # Wait for the keep-alive task to finish

#         print("WebSocket conversation cleanup complete.")

import threading
import asyncio
import websockets
import os
import json
import ssl

# Global dictionary to track active threads by conversation_id
active_threads = {}

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
        if conversation_id in active_threads:
            print(f"Conversation {conversation_id} already active. Joining existing thread.")
            # The thread is already running, return the existing thread
            return active_threads[conversation_id]
        else:
            print(f"Starting a new thread for conversation {conversation_id}.")
            # Create a shutdown event for the conversation ID
            shutdown_event = threading.Event()
            shutdown_events[conversation_id] = shutdown_event
            
            # Create and start the new thread
            new_thread = threading.Thread(target=run_conversation, args=(conversation_id, content, shutdown_event))
            new_thread.start()
            
            active_threads[conversation_id] = new_thread
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

def run_conversation(conversation_id, content=None):
    """
    The function to handle the WebSocket connection and conversation for a specific conversation_id.
    """
    # This will be the main function for handling WebSocket communication for a specific conversation
    asyncio.run(open_conversation_websocket(conversation_id, content))

def run_conversation(conversation_id, content=None, shutdown_event=None):
    """
    The function to handle the WebSocket connection and conversation for a specific conversation_id.
    """
    asyncio.run(open_conversation_websocket(conversation_id, content, shutdown_event))

async def open_conversation_websocket(conversation_id, content=None, shutdown_event=None):
    uri = f"wss://{HOST}/ws/conversation/{conversation_id}/machine/"
    headers = {
        "Authorization": f"Worker {os.environ.get('WORKER_TOKEN')}",
        "X-Worker-ID": os.environ.get("WORKER_ID"),
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(uri, additional_headers=headers, ssl=ssl_context) as websocket:
            print(f"WebSocket for conversation_id: {conversation_id} opened")

            async def respond_to_prompt(content):
                print(f"Responding to prompt: {content}")
                # response = generate_response(content)
                response = f"response to: {content}"
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
                        print(f"WebSocket conversation {conversation_id} instructed to close.")
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
            print(f"WebSocket for conversation_id {conversation_id} closed gracefully.")

    except Exception as e:
        print(f"WebSocket error: {e}")

    finally:
        with thread_lock:
            if conversation_id in active_threads:
                del active_threads[conversation_id]
            print(f"Cleaned up conversation thread {conversation_id}.")

        print("WebSocket conversation cleanup complete.")
