from celery_app import celery
from mailer import init_db, fetch_due, send_email, mark_sent


@celery.on_after_configure.connect
def _ensure_db(sender, **kwargs):
    """Init DB on startup."""
    init_db()


@celery.task(bind=True, name="tasks.send_due_emails", max_retries=3, default_retry_delay=30)
def send_due_emails(self):
    """Send any due emails.

    Returns:
        Summary dict.
    """
    # init_db()
    batch = fetch_due(limit=200)
    sent, failed = 0, 0

    for row in batch:
        try:
            send_email(row)
            mark_sent(row["id"])
            sent += 1
        except Exception as exc:
            failed += 1
            # Retry the whole task; simple for demo
            raise self.retry(exc=exc)

    return {"checked": len(batch), "sent": sent, "failed": failed}
