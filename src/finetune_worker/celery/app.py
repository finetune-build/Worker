import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

WORKER_ID = os.environ.get("FINETUNE_WORKER_ID", "UNKNOWN_WORKER_ID")
BROKER = os.environ.get("FINETUNE_CELERY_BROKER_URL", "sqla+sqlite:///celery_broker.sqlite")
BACKEND = os.environ.get("FINETUNE_CELERY_BACKEND_URL", "db+sqlite:///celery_results.sqlite")

celery = Celery(f"finetune-worker-{WORKER_ID}", broker=BROKER, backend=BACKEND)

celery.config_from_object("finetune_worker.celery.config")
