from celery import Celery
from ftw.conf import settings

celery = Celery(f"finetune-worker-{settings.WORKER_ID}", broker=settings.BROKER, backend=settings.BACKEND)

celery.config_from_object("ftw.celery.config")
