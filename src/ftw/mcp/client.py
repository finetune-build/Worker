from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import os
from typing import Any
from mcp.types import InitializeResult, ClientNotification, InitializedNotification

async def handle_mcp_request(request: dict[str, Any]) -> Any:
    """
    Handles a single MCP request with a short-lived client connection.
    
    Args:
        request: The MCP request to process
        callback: Optional callback function to handle the response
    
    Returns:
        The result of the MCP request
    """
    server_params = StdioServerParameters(
        command="python",
        args=["examples/mcp/worker-integration/weather.py"],
        env=os.environ,
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                print("[MCP] Initializing session...")
                # First initialize the session
                await session.initialize()
                
                print(f"[MCP] Processing request: {request}")
                result = None
                params = request.get("params")

                if request.get("method") == "ping":
                    result = await session.send_ping()
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "resources/list":
                    result = await session.list_resources()
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "resources/templates/list":
                    result = await session.list_resource_templates()
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "resources/read":
                    uri = params.get("uri")
                    result = await session.read_resource(uri)
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "resources/subscribe":
                    uri = params.get("uri")
                    result = await session.subscribe_to_resource(uri)
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "resources/unsubscribe":
                    uri = params.get("uri")
                    result = await session.unsubscribe_from_resource(uri)
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "prompts/list":
                    result = await session.list_prompts()
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "prompts/get":
                    name = params.get("name")
                    args = params.get("args")
                    result = await session.get_prompt(name, args)
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "tools/list":
                    result = await session.list_tools()
                    result = {
                        "tools": [tool.model_dump(exclude_none=True) for tool in result.tools],
                        "nextCursor": result.nextCursor
                    }
                elif request.get("method") == "tools/call":
                    name = params.get("name")
                    args = params.get("args")
                    result = await session.call_tool(name, args)
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "notifications/roots/list_changed":
                    result = await session.list_roots()
                    result = result.model_dump(exclude_none=True)
                elif request.get("method") == "logging/setLevel":
                    level = params.get("level")
                    result = await session.set_logging_level(level)
                    result = result.model_dump(exclude_none=True)

                response = {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request.get("id")
                }
                print(f"[MCP] Sending response: {response}")
                
                return response 
                
    except Exception as e:
        print(f"[MCP] Error processing request: {e}")
        raise

async def run_mcp_request(request: dict[str, Any]) -> Any:
    """
    Runs an MCP request in a new event loop.
    
    Args:
        request: The MCP request to process
        callback: Optional callback function to handle the response
    
    Returns:
        The result of the MCP request
    """
    return await handle_mcp_request(request)
