from celery import Celery
from finetune.conf import settings

celery = Celery(f"finetune-worker-{settings.WORKER_ID}", broker=settings.BROKER, backend=settings.BACKEND)

celery.config_from_object("finetune.celery.config")
