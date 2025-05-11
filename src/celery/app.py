import os

from celery import Celery

celery = Celery(
    os.environ.get("CELERY_APP_NAME"),
    broker=os.environ.get("CELERY_BROKER_URL"),
    backend=os.environ.get("CELERY_BACKEND_URL"),
)

celery.config_from_object("app.client.celery.config")
