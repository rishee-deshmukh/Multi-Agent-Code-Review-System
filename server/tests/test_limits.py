import pytest
from fastapi import HTTPException

from limits import RequestGuard, _int_env


class FakeRequest:
    def __init__(self, ip="1.2.3.4", forwarded=None):
        self.client = type("C", (), {"host": ip})()
        self.headers = {"x-forwarded-for": forwarded} if forwarded else {}


class Clock:
    def __init__(self, now=1_700_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


def guard(clock=None, **kw):
    return RequestGuard(clock=clock or Clock(), **{"max_code_chars": 100, "per_minute": 3, "daily_budget": 0, "max_concurrent": 0, **kw})


def status(g, request, code="x"):
    try:
        g.check(request, code)
    except HTTPException as e:
        return e.status_code
    return 200


def test_oversized_code_is_rejected_with_413():
    assert status(guard(), FakeRequest(), "x" * 101) == 413
    assert status(guard(), FakeRequest(), "x" * 100) == 200


def test_per_ip_limit_applies_per_client_and_expires():
    clock = Clock()
    g = guard(clock)
    assert [status(g, FakeRequest("a")) for _ in range(4)] == [200, 200, 200, 429]
    assert status(g, FakeRequest("b")) == 200  # another client is unaffected
    clock.now += 61
    assert status(g, FakeRequest("a")) == 200


def test_rate_limit_response_says_when_to_retry():
    g = guard(per_minute=1)
    g.check(FakeRequest(), "x")
    with pytest.raises(HTTPException) as e:
        g.check(FakeRequest(), "x")
    assert int(e.value.headers["Retry-After"]) >= 1


def test_daily_budget_is_global_and_resets_at_utc_midnight():
    clock = Clock(1_700_000_000.0)   # 2023-11-14 22:13 UTC
    g = guard(clock, per_minute=0, daily_budget=2)
    assert [status(g, FakeRequest(f"ip{i}")) for i in range(3)] == [200, 200, 429]
    clock.now += 2 * 3600            # past midnight UTC
    assert status(g, FakeRequest("ip9")) == 200


def test_a_request_refused_by_the_ip_limit_does_not_spend_the_daily_budget():
    g = guard(per_minute=1, daily_budget=2)
    assert [status(g, FakeRequest()) for _ in range(5)] == [200, 429, 429, 429, 429]
    assert status(g, FakeRequest("other")) == 200


def test_zero_disables_every_limit():
    g = guard(max_code_chars=0, per_minute=0, daily_budget=0, max_concurrent=0)
    assert all(status(g, FakeRequest(), "x" * 10_000) == 200 for _ in range(50))


def test_concurrency_slots_are_released_even_when_a_check_fails():
    g = guard(max_concurrent=1, per_minute=1)
    first = g.admit(FakeRequest("a"), "x")
    with pytest.raises(HTTPException) as busy:
        g.admit(FakeRequest("b"), "x")
    assert busy.value.status_code == 429
    first.release()
    first.release()                       # idempotent
    g.admit(FakeRequest("c"), "x").release()
    with pytest.raises(HTTPException):
        g.admit(FakeRequest("c"), "x")    # per-minute limit hit: must not leak a slot
    g.admit(FakeRequest("d"), "x").release()


def test_concurrency_slot_is_released_when_the_review_raises():
    g = guard(max_concurrent=1)
    with pytest.raises(RuntimeError):
        with g.admitted(FakeRequest(), "x"):
            raise RuntimeError("boom")
    g.admit(FakeRequest(), "x").release()


def test_forwarded_header_is_ignored_unless_proxy_is_trusted():
    spoof = FakeRequest("9.9.9.9", forwarded="1.1.1.1, 2.2.2.2")
    assert guard().client_ip(spoof) == "9.9.9.9"
    assert guard(trust_proxy_headers=True).client_ip(spoof) == "2.2.2.2"   # nearest proxy's entry, not the client's claim


def test_bad_env_values_fail_loudly(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "lots")
    with pytest.raises(ValueError, match="RATE_LIMIT_PER_MINUTE"):
        _int_env("RATE_LIMIT_PER_MINUTE", 6)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "-1")
    with pytest.raises(ValueError):
        _int_env("RATE_LIMIT_PER_MINUTE", 6)
