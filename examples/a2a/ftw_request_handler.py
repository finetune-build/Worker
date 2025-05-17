from ftw.sse.events import respond_to_ping

# Applies prepended print statement.
from ftw.conf import settings
from ftw.ws.conversation import start_conversation_thread, shutdown_conversation_thread
from ftw.ws.worker import start_worker_thread

from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler

class FTWRequestHandler(DefaultRequestHandler):
    """
    Extends default request handler to connect to FineTune API server for all
    incoming requests.
    """

    def __init__(self, agent_executor, task_store, queue_manager=None, push_notifier=None):
        super().__init__(agent_executor, task_store, queue_manager, push_notifier)

    async def handle_event(self, data):
        """
        Default events expected from API server.
        """
        if data.get("type") == "ping":
            print(f"Ping received. Sending pong...")
            await respond_to_ping()

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

    async def on_get_task(self, params):
        # You can override methods from DefaultRequestHandler
        print("Custom behavior before calling super().on_get_task")
        task = await super().on_get_task(params)
        print("Custom behavior after calling super().on_get_task")
        return task
