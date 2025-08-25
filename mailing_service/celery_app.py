import os
from celery import Celery
import config

celery = Celery(
    "mailing_service",
    broker=config.BROKER_URL,
    backend=config.RESULT_BACKEND,
)

celery.conf.update(
    imports=("tasks",),
    beat_schedule=config.BEAT_SCHEDULE,
    timezone=os.getenv("TZ", "UTC"),
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
