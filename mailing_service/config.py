import os
from datetime import timedelta

# Celery
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Beat schedule: how often to flush the outbox
SEND_INTERVAL_SECONDS = int(os.getenv("SEND_INTERVAL_SECONDS", "30"))

BEAT_SCHEDULE = {
    "send-due-emails": {
        "task": "tasks.send_due_emails",
        "schedule": timedelta(seconds=SEND_INTERVAL_SECONDS),
    }
}

# Email (defaults fit local dev with MailHog or a debug SMTP server)
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() in {"1", "true", "yes"}
FROM_ADDR = os.getenv("FROM_ADDR", "noreply@example.com")

# SQLite outbox
DB_PATH = os.getenv("OUTBOX_DB", "outbox.sqlite3")