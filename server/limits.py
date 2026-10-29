"""Caps that keep a public deployment from being used to burn the Gemini quota.

Everything is in-memory and per process, which is right for the single-container deploy this
project ships. Behind several replicas each one would enforce its own share.
Every limit is set from the environment and ``0`` disables it.
"""
import logging
import os
import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

MAX_TRACKED_CLIENTS = 10_000


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


class RequestGuard:
    def __init__(
        self,
        max_code_chars: int = 20_000,
        per_minute: int = 6,
        daily_budget: int = 100,
        max_concurrent: int = 3,
        trust_proxy_headers: bool = False,
        clock=time.time,
    ):
        self.max_code_chars = max_code_chars
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self.max_concurrent = max_concurrent
        self.trust_proxy_headers = trust_proxy_headers
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, deque] = {}
        self._day = ""
        self._used_today = 0
        self._active = 0

    @classmethod
    def from_env(cls) -> "RequestGuard":
        return cls(
            max_code_chars=_int_env("MAX_CODE_CHARS", 20_000),
            per_minute=_int_env("RATE_LIMIT_PER_MINUTE", 6),
            daily_budget=_int_env("DAILY_REVIEW_BUDGET", 100),
            max_concurrent=_int_env("MAX_CONCURRENT_REVIEWS", 3),
            trust_proxy_headers=_truthy("TRUST_PROXY_HEADERS"),
        )

    def client_ip(self, request: Request) -> str:
        if self.trust_proxy_headers:
            # The last entry is the one appended by the nearest proxy, so a client cannot choose it.
            # Only enable this behind a proxy that sets the header, or anyone can spoof their address.
            forwarded = request.headers.get("x-forwarded-for", "")
            if forwarded.strip():
                return forwarded.split(",")[-1].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request, code: str) -> None:
        """Raise HTTPException (413 or 429) if this request should not run. Counts it against the budget otherwise."""
        if self.max_code_chars and len(code) > self.max_code_chars:
            raise HTTPException(
                status_code=413,
                detail=f"Code is {len(code):,} characters; the limit is {self.max_code_chars:,}.",
            )

        now = self._clock()
        ip = self.client_ip(request)
        with self._lock:
            if self.per_minute:
                hits = self._hits.setdefault(ip, deque())
                while hits and now - hits[0] >= 60:
                    hits.popleft()
                if len(hits) >= self.per_minute:
                    retry = max(1, int(60 - (now - hits[0])) + 1)
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit: at most {self.per_minute} reviews per minute. Try again in {retry}s.",
                        headers={"Retry-After": str(retry)},
                    )
                if len(self._hits) > MAX_TRACKED_CLIENTS:
                    self._drop_idle_clients(now)

            if self.daily_budget:
                today = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
                if today != self._day:
                    self._day, self._used_today = today, 0
                if self._used_today >= self.daily_budget:
                    logger.warning("Daily review budget of %d reached", self.daily_budget)
                    raise HTTPException(
                        status_code=429,
                        detail="The daily review budget for this demo is used up. Try again tomorrow (UTC).",
                        headers={"Retry-After": "3600"},
                    )
                self._used_today += 1

            if self.per_minute:
                self._hits[ip].append(now)

    def _drop_idle_clients(self, now: float) -> None:
        for ip in [ip for ip, hits in self._hits.items() if not hits or now - hits[-1] >= 60]:
            del self._hits[ip]

    def admit(self, request: Request, code: str) -> "Ticket":
        """Run every check and take a concurrency slot. The caller must ``release()`` the ticket."""
        self._acquire()
        try:
            self.check(request, code)
        except BaseException:
            self._release()
            raise
        return Ticket(self._release)

    def _acquire(self) -> None:
        with self._lock:
            if self.max_concurrent and self._active >= self.max_concurrent:
                raise HTTPException(
                    status_code=429,
                    detail="The server is busy with other reviews. Try again in a few seconds.",
                    headers={"Retry-After": "5"},
                )
            self._active += 1

    def _release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    @contextmanager
    def admitted(self, request: Request, code: str):
        ticket = self.admit(request, code)
        try:
            yield
        finally:
            ticket.release()


class Ticket:
    """A held concurrency slot. Releasing twice is harmless, which matters for streams that can end in several ways."""

    def __init__(self, on_release):
        self._on_release = on_release
        self._lock = threading.Lock()
        self._released = False

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._on_release()
