import os

# Broker/Backend
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Queues
BETA_QUEUE = "beta"
DLQ_QUEUE = "beta.dlq"

# Retries
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))  # total attempts on beta = MAX_RETRIES+1
BASE_BACKOFF_SECONDS = int(os.getenv("BASE_BACKOFF_SECONDS", "2"))
