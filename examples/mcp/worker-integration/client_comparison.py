import asyncio
import time
from typing import List, Any

# HTTPX Example
async def httpx_example():
    import httpx
    
    async with httpx.AsyncClient() as client:
        # Simple GET request
        response = await client.get('https://api.weather.gov/alerts')
        print("HTTPX Simple GET:", response.status_code)
        
        # Parallel requests
        urls = ['https://api.weather.gov/alerts/active/area/CA',
                'https://api.weather.gov/alerts/active/area/NY',
                'https://api.weather.gov/alerts/active/area/TX']
        async with client.stream('GET', urls[0]) as response:
            async for line in response.aiter_lines():
                # Streaming response handling
                print("HTTPX Streaming line received")
        
        # Parallel requests with error handling
        tasks = []
        for url in urls:
            tasks.append(client.get(url))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        print("HTTPX Parallel requests complete")

# AIOHTTP Example
async def aiohttp_example():
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        # Simple GET request
        async with session.get('https://api.weather.gov/alerts') as response:
            print("AIOHTTP Simple GET:", response.status)
        
        # Streaming example
        async with session.get('https://api.weather.gov/alerts/active/area/CA') as response:
            async for line in response.content:
                # Streaming response handling
                print("AIOHTTP Streaming line received")
        
        # WebSocket example (AIOHTTP specific feature)
        try:
            async with session.ws_connect('wss://echo.websocket.org') as ws:
                await ws.send_str('Hello WebSocket!')
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        print("WebSocket received:", msg.data)
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break
        except Exception as e:
            print("WebSocket error:", e)

async def performance_comparison():
    # Setup
    urls = [f'https://api.weather.gov/points/{i},{i}' for i in range(10)]
    
    # HTTPX Test
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        await asyncio.gather(*tasks, return_exceptions=True)
    httpx_time = time.time() - start_time
    
    # AIOHTTP Test
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        await asyncio.gather(*tasks, return_exceptions=True)
    aiohttp_time = time.time() - start_time
    
    print(f"HTTPX Time: {httpx_time:.2f}s")
    print(f"AIOHTTP Time: {aiohttp_time:.2f}s")

async def main():
    print("Running HTTPX Example...")
    await httpx_example()
    
    print("\nRunning AIOHTTP Example...")
    await aiohttp_example()
    
    print("\nRunning Performance Comparison...")
    await performance_comparison()

if __name__ == "__main__":
    asyncio.run(main()) 