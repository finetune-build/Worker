# server.py
from mcp.server.fastmcp import FastMCP

# Create a stateless MCP server
mcp = FastMCP(name="SimpleServer", stateless_http=True)

# Add a simple echo tool
@mcp.tool(description="Echo a message back")
def echo(message: str) -> str:
    """Echo the provided message"""
    print(f"Echo: {message}")
    return f"Echo: {message}"


# Add a simple math tool
@mcp.tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    print(a + b)
    return a + b


# Add a simple resource
@mcp.resource("info://server")
def server_info() -> str:
    """Get server information"""
    print("called Simple MCP Server v1.0")
    return "Simple MCP Server v1.0"

def create_app():
    mcp.run(transport="streamable-http")
