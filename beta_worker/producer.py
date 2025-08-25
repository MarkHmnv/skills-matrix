from tasks import request_3p
import config

def enqueue(payload: dict, priority: int = 5):
    """Enqueue a beta request.

    Args:
        payload: Input.
        priority: 0 (highest) .. 9 (lowest).
    """
    return request_3p.apply_async(
        args=[payload],
        queue=config.BETA_QUEUE,
        priority=priority,
    )

if __name__ == "__main__":
    enqueue({"job": 1, "mode": "ok"}, priority=0)          # fast lane
    enqueue({"job": 2, "mode": "transient"}, priority=5)   # will retry then fallback
    enqueue({"job": 3, "mode": "fatal"}, priority=5)       # immediate fallback
    print("Enqueued 3 demo jobs.")
