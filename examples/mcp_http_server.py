from mcp.server.fastmcp import FastMCP
from mcp.types import Completion, ResourceTemplateReference

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

# Completion
# https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/122
@mcp.completion()
async def handle_completion(ref, argument, context):
    if isinstance(ref, ResourceTemplateReference):
        # Return completions based on ref, argument, and context
        return Completion(values=["option1", "option2"])
    return None

# Resources 
@mcp.resource("info://server")
def server_info() -> str:
    """Get server information"""
    print("called Simple MCP Server v1.0")
    return "Simple MCP Server v1.0"

@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration here"

# Resource Templates
@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """Dynamic user data"""
    return f"Profile data for user {user_id}"

def create_app():
    mcp.run(transport="streamable-http")
