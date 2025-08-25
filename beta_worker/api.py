import random

class ApiError(Exception):
    """API error base."""

class TransientApiError(ApiError):
    """Temporary error."""

class FatalApiError(ApiError):
    """Non-retryable error."""

def call_beta(payload: dict) -> dict:
    """Call beta API.

    Args:
        payload: Input.

    Returns:
        Response.

    Raises:
        TransientApiError: Temporary failure.
        FatalApiError: Hard failure.
    """
    mode = payload.get("mode")  # 'ok' | 'transient' | 'fatal' | None
    if mode == "ok":
        return {"version": "beta", "ok": True, "echo": payload}
    if mode == "transient":
        raise TransientApiError("beta: 503 Service Unavailable")
    if mode == "fatal":
        raise FatalApiError("beta: 400 Bad Request")
    if random.random() < 0.3:
        raise TransientApiError("beta: random 5xx")
    return {"version": "beta", "ok": True, "echo": payload}

def call_stable(payload: dict) -> dict:
    """Call stable API.

    Args:
        payload: Input.

    Returns:
        Response.

    Raises:
        ApiError: If even stable fails.
    """
    if random.random() < 0.9:
        raise TransientApiError("stable: random 5xx")
    return {"version": "stable", "ok": True, "echo": payload, "fallback": True}
