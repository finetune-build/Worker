from finetune_sdk.api.worker import worker_pong

from finetune_sdk.conf import settings
# from finetune_sdk.sse.tasks import run_task_by_name
# from finetune_sdk.sse.utils import * # Applies prepended print statement.
from finetune_sdk.ws.conversation import start_conversation_thread, shutdown_conversation_thread
from finetune_sdk.ws.worker import worker_start_websocket_thread
from finetune_sdk.mcp.client import run_mcp_request 
from finetune_sdk.api.worker import worker_mcp_response

async def handle_event(data):
    """
    Handle JSON-RPC 2.0 formatted requests.
    """
    method = data.get("method")
    params = data.get("params", {})
    request_id = data.get("id")

    if method == "worker_ping" or method == "worker_ping_all_active":
        print("Worker Ping Received. Sending pong...")
        await worker_pong()
        return {
            "jsonrpc": "2.0",
            "result": "pong",
            "id": request_id,
        }

    elif method == "worker_mcp_request":
        print("Starting MCP Client")
        response = await run_mcp_request(params)
        print(f"response: {response}")
        await worker_mcp_response(response)
        return {
            "jsonrpc": "2.0",
            "result": "MCP request processed",
            "id": request_id,
        }

    # elif method == "tool":
    #     tool_name = params.get("tool_name")
    #     run_task_by_name(tool_name)
    #     print(f"Tool request received. Running tool: {tool_name}")
    #     return {
    #         "jsonrpc": "2.0",
    #         "result": f"Tool {tool_name} executed",
    #         "id": request_id,
    #     }

    elif method == "worker_task_created":
        print(f"Received Worker Task")
        return {
            "jsonrpc": "2.0",
            "result": f"Worker {settings.WORKER_ID} received task",
            "id": request_id,
        }

    elif method == "worker_start_websocket_thread":
        # Occurs when user visits worker page on web.
        # Worker also automatically opens websocket on initial synchronization
        # if there are any tasks.
        print(f"Starting Worker Websocket Thread: {settings.WORKER_ID}")
        worker_start_websocket_thread(settings.WORKER_ID)
        return {
            "jsonrpc": "2.0",
            "result": f"Worker {settings.WORKER_ID} websocket opened",
            "id": request_id,
        }

    elif method == "conversation_open_websocket":
        content = params.get("content")
        conversation_id = params.get("conversation_id")
        print(f"Starting Conversation Websocket Thread: {conversation_id}")
        start_conversation_thread(conversation_id, content)
        return {
            "jsonrpc": "2.0",
            "result": f"Conversation {conversation_id} websocket opened",
            "id": request_id,
        }

    # Not really used because conversation is closed from within websocket.
    elif method == "conversation_close_websocket":
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

