from mcp.server.fastmcp import FastMCP
from finetune.sse.lifespan import create_lifespan

# Initialize FastMCP server
mcp = FastMCP("worker-integration", lifespan=create_lifespan())

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
