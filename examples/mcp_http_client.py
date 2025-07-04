# test_client_with_logging.py
import asyncio
import json
import logging
from datetime import datetime
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("TestClient")


async def test_server_connection(server_url: str = "http://127.0.0.1:8000/mcp"):
    """Test connection to MCP server with detailed logging."""
    
    logger.info("=" * 60)
    logger.info(f"🔌 Testing connection to: {server_url}")
    logger.info("=" * 60)
    
    try:
        logger.info("📡 Opening streamable HTTP connection...")
        async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
            logger.info("✅ Transport connection established")
            
            logger.info("🔐 Creating client session...")
            async with ClientSession(read_stream, write_stream) as session:
                
                # Initialize session
                logger.info("🚀 Initializing session...")
                await session.initialize()
                logger.info("✅ Session initialized successfully!")
                
                # List tools
                logger.info("\n" + "=" * 40)
                logger.info("📋 Listing available tools...")
                tools = await session.list_tools()
                logger.info(f"Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    logger.info(f"  🔧 {tool.name}: {tool.description}")
                
                # List resources
                logger.info("\n" + "=" * 40)
                logger.info("📚 Listing available resources...")
                resources = await session.list_resources()
                logger.info(f"Found {len(resources.resources)} resources:")
                for resource in resources.resources:
                    logger.info(f"  📄 {resource.uri}: {resource.name}")
                
                # Test echo tool
                logger.info("\n" + "=" * 40)
                logger.info("🧪 Testing 'echo' tool...")
                echo_result = await session.call_tool(
                    "echo",
                    arguments={"message": "Hello from test client!"}
                )
                logger.info(f"✅ Echo result: {echo_result.content}")
                
                # Test add tool
                logger.info("\n" + "=" * 40)
                logger.info("🧪 Testing 'add' tool...")
                add_result = await session.call_tool(
                    "add",
                    arguments={"a": 10, "b": 32}
                )
                logger.info(f"✅ Add result: {add_result.content}")
                
                # Test health tool
                logger.info("\n" + "=" * 40)
                logger.info("🧪 Testing 'health' tool...")
                try:
                    health_result = await session.call_tool("health", arguments={})
                    logger.info(f"✅ Health result: {health_result.content}")
                except Exception as e:
                    logger.warning(f"Health tool not available: {e}")
                
                # Read server info resource
                logger.info("\n" + "=" * 40)
                logger.info("🧪 Reading 'info://server' resource...")
                content, mime_type = await session.read_resource("info://server")
                logger.info(f"✅ Resource content: {content}")
                logger.info(f"   MIME type: {mime_type}")
                
                logger.info("\n" + "=" * 40)
                logger.info("✅ All tests completed successfully!")
                
    except Exception as e:
        logger.error(f"❌ Connection failed: {type(e).__name__}: {e}")
        logger.debug("Full error:", exc_info=True)
        
        # Provide helpful debugging info
        logger.info("\n🔍 Debugging tips:")
        logger.info("1. Is the server running? Check server logs")
        logger.info("2. Is the URL correct? Default is http://127.0.0.1:8000/mcp")
        logger.info("3. Check firewall/network settings")
        logger.info("4. Try: curl -X POST http://127.0.0.1:8000/mcp")


async def test_multiple_servers():
    """Test multiple servers if running."""
    servers = [
        ("http://127.0.0.1:8000/mcp", "Default MCP endpoint"),
        ("http://127.0.0.1:8000/echo", "Echo server endpoint"),
        ("http://127.0.0.1:8000/math", "Math server endpoint"),
    ]
    
    for url, description in servers:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {description}")
        logger.info(f"URL: {url}")
        try:
            await test_server_connection(url)
        except Exception as e:
            logger.error(f"Failed to connect to {description}: {e}")


def main():
    """Run the test client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MCP Server Connection")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/mcp",
        help="Server URL (default: http://127.0.0.1:8000/mcp)"
    )
    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Test multiple server endpoints"
    )
    
    args = parser.parse_args()
    
    print("MCP Server Test Client")
    print("=" * 60)
    
    if args.test_all:
        asyncio.run(test_multiple_servers())
    else:
        asyncio.run(test_server_connection(args.url))


if __name__ == "__main__":
    main()