import os

from dotenv import load_dotenv

load_dotenv()

HOST = os.environ.get("FINETUNE_HOST", "api.finetune.build")
BROKER = os.environ.get("FINETUNE_CELERY_BROKER_URL", "sqla+sqlite:///celery_broker.sqlite")
BACKEND = os.environ.get("FINETUNE_CELERY_BACKEND_URL", "db+sqlite:///celery_results.sqlite")

WORKER_ID = os.environ.get("FINETUNE_WORKER_ID")
WORKER_TOKEN = os.environ.get("FINETUNE_WORKER_TOKEN")
