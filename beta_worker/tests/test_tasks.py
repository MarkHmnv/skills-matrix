from types import SimpleNamespace
import pytest
from beta_worker import tasks


class FakeRetry(Exception):
    """Raised by our patched self.retry to simulate Celery retry."""
    def __init__(self, countdown, exc):
        super().__init__(str(exc))
        self.countdown = countdown
        self.exc = exc


@pytest.fixture
def task_state(monkeypatch):
    """Prepare the bound task state and helpers."""
    # Ensure a request object with a mutable retries counter
    tasks.request_3p.request.retries = 0

    # Capture retries + raise FakeRetry like Celery does
    countdowns = []

    def fake_retry(*, exc, countdown):
        countdowns.append(countdown)
        raise FakeRetry(countdown, exc)

    # Patch retry and DLQ dispatch
    monkeypatch.setattr(tasks.request_3p, "retry", fake_retry, raising=True)
    dlq_calls = []

    def fake_apply_async(*args, **kwargs):
        dlq_calls.append(
            {
                "args": kwargs.get("args", args[0] if args else None),
                "queue": kwargs.get("queue"),
                "priority": kwargs.get("priority"),
            }
        )

    monkeypatch.setattr(tasks.dead_letter, "apply_async", fake_apply_async)

    return SimpleNamespace(task=tasks.request_3p,
                           countdowns=countdowns,
                           dlq_calls=dlq_calls)


def test_request_ok(task_state, monkeypatch):
    monkeypatch.setattr(tasks.api, "call_beta",
                        lambda p: {"version": "beta", "ok": True, "echo": p})
    res = task_state.task.run({"job": 1})
    assert res["version"] == "beta"
    assert task_state.countdowns == []
    assert task_state.dlq_calls == []


def test_transient_then_success_on_retry(task_state, monkeypatch):
    seq = [
        tasks.api.TransientApiError("beta 5xx"),
        {"version": "beta", "ok": True, "echo": {"job": 2}},
    ]

    def beta(p):
        v = seq.pop(0)
        if isinstance(v, Exception):
            raise v
        return v

    monkeypatch.setattr(tasks.api, "call_beta", beta)

    # 1st attempt -> retry with base backoff
    with pytest.raises(FakeRetry) as e1:
        task_state.task.run({"job": 2})
    assert e1.value.countdown == tasks.config.BASE_BACKOFF_SECONDS * (2 ** 0)

    # 2nd attempt -> success
    task_state.task.request.retries = 1
    res = task_state.task.run({"job": 2})
    assert res["version"] == "beta"
    assert task_state.dlq_calls == []


def test_transient_exhaust_then_fallback_success(task_state, monkeypatch):
    # Two retries allowed, then fallback on 3rd attempt
    monkeypatch.setattr(task_state.task, "max_retries", 2, raising=False)

    def always_transient(_):
        raise tasks.api.TransientApiError("beta 5xx")

    monkeypatch.setattr(tasks.api, "call_beta", always_transient)
    monkeypatch.setattr(tasks.api, "call_stable",
                        lambda p: {"version": "stable", "ok": True, "echo": p, "fallback": True})

    # Attempt 1 -> retry
    with pytest.raises(FakeRetry) as e1:
        task_state.task.run({"job": 3})
    assert e1.value.countdown == tasks.config.BASE_BACKOFF_SECONDS * (2 ** 0)

    # Attempt 2 -> retry
    task_state.task.request.retries = 1
    with pytest.raises(FakeRetry) as e2:
        task_state.task.run({"job": 3})
    assert e2.value.countdown == tasks.config.BASE_BACKOFF_SECONDS * (2 ** 1)

    # Attempt 3 -> fallback succeeds
    task_state.task.request.retries = 2
    out = task_state.task.run({"job": 3})
    assert out["version"] == "stable"
    assert task_state.dlq_calls == []


def test_transient_exhaust_then_fallback_fails_sends_dlq(task_state, monkeypatch):
    monkeypatch.setattr(task_state.task, "max_retries", 2, raising=False)

    def always_transient(_):
        raise tasks.api.TransientApiError("beta 5xx")

    monkeypatch.setattr(tasks.api, "call_beta", always_transient)
    monkeypatch.setattr(tasks.api, "call_stable", lambda p: (_ for _ in ()).throw(RuntimeError("stable boom")))

    # Simulate two retries already done -> now fallback and fail
    task_state.task.request.retries = 2
    with pytest.raises(RuntimeError, match="stable boom"):
        task_state.task.run({"job": 4})

    assert len(task_state.dlq_calls) == 1
    call = task_state.dlq_calls[0]
    # args = [payload, reason]
    assert call["args"][0] == {"job": 4}
    assert "stable_after_transient_failed" in call["args"][1]
    assert call["queue"] == tasks.config.DLQ_QUEUE
    assert call["priority"] == 9


def test_fatal_immediate_fallback_success(task_state, monkeypatch):
    monkeypatch.setattr(tasks.api, "call_beta",
                        lambda p: (_ for _ in ()).throw(tasks.api.FatalApiError("fatal")))
    monkeypatch.setattr(tasks.api, "call_stable",
                        lambda p: {"version": "stable", "ok": True, "echo": p, "fallback": True})

    res = task_state.task.run({"job": 5})
    assert res["version"] == "stable"
    assert task_state.countdowns == []  # no retries
    assert task_state.dlq_calls == []


def test_fatal_immediate_fallback_fails_sends_dlq(task_state, monkeypatch):
    monkeypatch.setattr(tasks.api, "call_beta",
                        lambda p: (_ for _ in ()).throw(tasks.api.FatalApiError("fatal")))
    monkeypatch.setattr(tasks.api, "call_stable",
                        lambda p: (_ for _ in ()).throw(RuntimeError("stable down")))

    with pytest.raises(RuntimeError, match="stable down"):
        task_state.task.run({"job": 6})

    assert len(task_state.dlq_calls) == 1
    call = task_state.dlq_calls[0]
    assert call["args"][0] == {"job": 6}
    assert "stable_after_fatal_failed" in call["args"][1]
    assert call["queue"] == tasks.config.DLQ_QUEUE
    assert call["priority"] == 9


def test_exponential_backoff_sequence(task_state, monkeypatch):
    # Make base/backoff obvious
    monkeypatch.setattr(tasks.config, "BASE_BACKOFF_SECONDS", 3, raising=False)
    monkeypatch.setattr(task_state.task, "max_retries", 3, raising=False)

    def always_transient(_):
        raise tasks.api.TransientApiError("beta 5xx")

    monkeypatch.setattr(tasks.api, "call_beta", always_transient)

    # Attempt 1 -> 3s, Attempt 2 -> 6s, Attempt 3 -> 12s
    for i, expected in enumerate([3, 6, 12]):
        task_state.task.request.retries = i
        with pytest.raises(FakeRetry) as e:
            task_state.task.run({"job": 7})
        assert e.value.countdown == expected
    # (Next attempt would fallback; we don't call it here.)


def test_dead_letter_writes_file(tmp_path, monkeypatch):
    # Ensure writes go to a temp folder
    monkeypatch.chdir(tmp_path)
    payload = {"job": 99}
    reason = "unit_test"
    # dead_letter is non-bound; run() calls the underlying function directly
    tasks.dead_letter.run(payload, reason)

    log_path = tmp_path / "dlq.log"
    content = log_path.read_text(encoding="utf-8")
    assert "unit_test" in content and "{'job': 99}" in content
