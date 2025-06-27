import os

from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

DJANGO_HOST = os.environ.get("DJANGO_HOST", "api.finetune.build")
BROKER = os.environ.get("FTW_BROKER_URL", "sqla+sqlite:///celery_broker.sqlite")
BACKEND = os.environ.get("FTW_CELERY_BACKEND_URL", "db+sqlite:///celery_results.sqlite")

WORKER_ID = os.environ.get("FINETUNE_WORKER_ID")
ACCESS_TOKEN = os.environ.get("FINETUNE_ACCESS_TOKEN")
HOST = os.environ.get("FINETUNE_HOST")

# Session id just in case the same worker id and same worker token are reused simultaneously.
SESSION_UUID = uuid4()
PROCESS_ID = os.getpid()
