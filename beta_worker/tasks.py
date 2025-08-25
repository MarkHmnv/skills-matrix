from celery import states
from celery_app import celery
import config
import api


@celery.task(name="beta.request", bind=True, max_retries=config.MAX_RETRIES)
def request_3p(self, payload: dict) -> dict:
    """Call 3p beta; fallback to stable after retries.

    Args:
        payload: Input.

    Returns:
        API response.
    """
    try:
        return api.call_beta(payload)
    except api.TransientApiError as exc:
        # Retry with exponential backoff; on final attempt, fall back to stable.
        if self.request.retries < self.max_retries:
            countdown = config.BASE_BACKOFF_SECONDS * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        # Retries exhausted -> downgrade
        try:
            return api.call_stable(payload)
        except Exception as stable_exc:
            dead_letter.apply_async(
                args=[payload, f"stable_after_transient_failed: {stable_exc}"],
                queue=config.DLQ_QUEUE,
                priority=9,  # lowest priority for DLQ
            )
            raise stable_exc

    except api.FatalApiError as exc:
        # Hard beta error -> immediately downgrade
        try:
            return api.call_stable(payload)
        except Exception as stable_exc:
            dead_letter.apply_async(
                args=[payload, f"stable_after_fatal_failed: {stable_exc}"],
                queue=config.DLQ_QUEUE,
                priority=9,
            )
            raise stable_exc


@celery.task(name="beta.dead_letter")
def dead_letter(payload: dict, reason: str) -> None:
    """Capture permanently failed requests.

    Args:
        payload: Original input.
        reason: Failure reason.
    """
    # Minimal: append to a local log file
    with open("dlq.log", "a", encoding="utf-8") as f:
        f.write(f"{reason} :: {payload}\n")
