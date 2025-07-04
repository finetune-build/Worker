# http_client.py
import asyncio
import os
from typing import Callable, Any, Optional

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from finetune.utils.redis_client import RedisClient 

class HTTPClient:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.session = None
        self._stop_event = asyncio.Event()
        self._client_task = None

    async def start(self):
        """Start and run the MCP client."""
        print("[MCP] Starting client...")
        try:
            print(f"[MCP] Current working directory: {os.getcwd()}")
            print("[MCP] Attempting to connect to MCP server...")

            async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read_stream, write_stream, _):
                print("[MCP] Transport connection established")

                self.session = ClientSession(read_stream, write_stream)
                await self.session.__aenter__()  # Manually enter async context

                try:
                    print("[MCP] Initializing session...")
                    await self.session.initialize()
                    print("[MCP] Session initialized")

                    print("\nListing available tools:")
                    tools = await self.session.list_tools()
                    for tool in tools.tools:
                        print(f"  - {tool.name}: {tool.description}")

                    print("\nListing available resources:")
                    resources = await self.session.list_resources()
                    for resource in resources.resources:
                        print(f"  - {resource.uri}: {resource.name}")

                    print("\nCalling echo tool:")
                    echo_result = await self.session.call_tool(
                        "echo",
                        arguments={"message": "Hello from MCP client!"}
                    )
                    print(f"Echo result: {echo_result.content}")

                    print("\nCalling add tool:")
                    add_result = await self.session.call_tool(
                        "add",
                        arguments={"a": 5, "b": 3}
                    )
                    print(f"Add result: {add_result.content}")

                    print("\nReading server info resource:")
                    content, mime_type = await self.session.read_resource("info://server")
                    print(f"Server info: {content}")

                    await self._stop_event.wait()

                finally:
                    print("[MCP] Cleaning up session...")
                    await self.session.__aexit__(None, None, None)

        except Exception as e:
            import traceback
            print(f"[MCP] Exception: {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            print("[MCP] Client stopped")
            self.session = None

    async def stop(self):
        """Stop the MCP client gracefully."""
        print("[MCP] Stopping client...")
        self._stop_event.set()


    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        if not self.session:
            raise RuntimeError("Client not connected")

        try:
            print(f"[MCP] Processing request: {request}")
            result = None
            params = request.get("params", {})
            method = request.get("method")

            if method == "ping":
                result = await self.session.send_ping()
                result = result.model_dump(exclude_none=True)
            elif method == "resources/list":
                result = await self.session.list_resources()
                result = result.model_dump(exclude_none=True)
            elif method == "tools/list":
                tools = await self.session.list_tools()
                result = {
                    "tools": [tool.model_dump(exclude_none=True) for tool in tools.tools]
                }
            elif method == "tools/call":
                name = params.get("name")
                args = params.get("args")
                result = await self.session.call_tool(name, args)
                result = result.model_dump(exclude_none=True)
            else:
                raise ValueError(f"Unknown method: {method}")

            response = {"jsonrpc": "2.0", "result": result, "id": request.get("id")}
            print("Received MCP Response")
            if self.redis_client is None:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Event listener pubsub not initialized"
                    },
                    "id": None,
                }
            else:
                self.redis_client.publish('mcp_responses', response)
            return response

        except Exception as e:
            print(f"[MCP] Request error: {e}")
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request.get("id")
            }
            return response
