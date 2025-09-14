import pytest
from beta_worker import api


def test_call_beta_modes():
    assert api.call_beta({"mode": "ok"})["version"] == "beta"
    with pytest.raises(api.TransientApiError):
        api.call_beta({"mode": "transient"})
    with pytest.raises(api.FatalApiError):
        api.call_beta({"mode": "fatal"})


def test_call_beta_random_paths(monkeypatch):
    # Force transient
    monkeypatch.setattr(api.random, "random", lambda: 0.2)
    with pytest.raises(api.TransientApiError):
        api.call_beta({})
    # Force success
    monkeypatch.setattr(api.random, "random", lambda: 0.9)
    out = api.call_beta({"foo": "bar"})
    assert out == {"version": "beta", "ok": True, "echo": {"foo": "bar"}}


def test_call_stable_random(monkeypatch):
    # Force failure
    monkeypatch.setattr(api.random, "random", lambda: 0.3)
    with pytest.raises(api.TransientApiError):
        api.call_stable({})
    # Force success
    monkeypatch.setattr(api.random, "random", lambda: 0.95)
    out = api.call_stable({"x": 1})
    assert out == {"version": "stable", "ok": True, "echo": {"x": 1}, "fallback": True}
