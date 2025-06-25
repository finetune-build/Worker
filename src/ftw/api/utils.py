import aiohttp
from ftw.conf import settings

DEFAULT_HEADERS = {
    "Authorization": f"Access {settings.ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

async def request(method, endpoint, params=None, json=None, headers=DEFAULT_HEADERS):
    """
    Wrapper for making requests to API server
    """
    domain = f"https://{settings.DJANGO_HOST}/v1/"
    url =  domain + endpoint
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.request(method, url, ssl=False, params=params, json=json) as resp:
                # TODO: Handle resp.status better.
                if resp.status not in [200, 201]:
                    # TODO: Replace with more clear error status.
                    error = f"Request failed. Status: {resp.status}"
                    return {
                        "success": False,
                        "data": None,
                        "error": error,
                    }
                data = await resp.json()
                return {
                    "success": True,
                    "data": data,
                    "error": None,
                }
        except Exception as e:
            print(f"API request error: {e}")
            return {
                "success": False,
                "data": None,
                "error": e,
            }
