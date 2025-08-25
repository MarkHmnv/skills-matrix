import os
from celery import Celery
import config

celery = Celery(
    "beta_worker",
    broker=config.BROKER_URL,
    backend=config.RESULT_BACKEND,
)

celery.conf.update(
    imports=("tasks",),
    timezone=os.getenv("TZ", "UTC"),
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
