import aiohttp

from ftw.conf import settings
from ftw.api.utils import request

async def worker_pong():
    url = f"https://{settings.DJANGO_HOST}/v1/worker/{settings.WORKER_ID}/pong/"
    headers = {
        "Authorization": f"Worker {settings.WORKER_TOKEN}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post(
                url, ssl=False, json={"worker_id": settings.WORKER_ID}
            ) as resp:
                if resp.status != 200:
                    print(f"Failed to respond to ping. Status: {resp.status}")
        except Exception as e:
            print(f"Ping response error: {e}")

async def get_worker_task_list(task_state="submitted", protocol="a2a"):
    return await request(
        "GET",
        f"worker/{settings.WORKER_ID}/task/?task_state={task_state}&protocol={protocol}"
    )

async def put_worker_task(worker_task_id, payload):
    """
    No nested updates, update status via websocket TaskStatusUpdateEvent.
    """
    return await request(
        "PUT",
        f"worker/{settings.WORKER_ID}/task/{worker_task_id}/",
        json=payload
    )