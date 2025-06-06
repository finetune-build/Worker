from mcp.client import Client
import asyncio

async def main():
    # Connect to the MCP server
    async with Client() as client:
        # Call the get_alerts tool
        result = await client.call_tool("get_alerts", {"state": "CA"})
        print("Weather alerts:", result)
        
        # Call the get_forecast tool
        result = await client.call_tool("get_forecast", {
            "latitude": 37.7749,
            "longitude": -122.4194
        })
        print("Weather forecast:", result)

if __name__ == "__main__":
    asyncio.run(main()) 