"""Disk cache for Gemini responses, so evaluation runs are reproducible and re-runs are free.

Entries are keyed by (model, system prompt, user message). With temperature 0 a hit
returns exactly what the live call returned, so the committed cache lets anyone
regenerate the published numbers without an API key (``--offline``). Changing a
prompt, the model or the sample code changes the key and forces a live call.
"""
import hashlib
import json
import threading
import time
from pathlib import Path

import llm


class CachedLLM:
    def __init__(self, cache_dir: Path, offline: bool = False, min_interval: float = 0.0):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.min_interval = min_interval  # seconds between live calls, to stay inside rate limits
        self.calls = 0
        self.hits = 0
        self._lock = threading.Lock()
        self._last_live_call = 0.0

    def _path(self, system_prompt: str, user_message: str) -> Path:
        key = hashlib.sha256(json.dumps([llm.model_name(), system_prompt, user_message]).encode()).hexdigest()
        return self.cache_dir / key[:2] / f"{key}.json"

    def install(self) -> "CachedLLM":
        live_generate = llm._generate_text

        def cached_generate(client, system_prompt, user_message):
            path = self._path(system_prompt, user_message)
            with self._lock:
                self.calls += 1
            if path.exists():
                with self._lock:
                    self.hits += 1
                return json.loads(path.read_text(encoding="utf-8"))["text"]
            if self.offline:
                raise llm.LLMUnrecoverableError(f"cache miss in offline mode ({path.name[:12]}…); re-run without --offline to fill it")

            with self._lock:
                wait = self._last_live_call + self.min_interval - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                self._last_live_call = time.monotonic()

            started = time.monotonic()
            text = live_generate(client, system_prompt, user_message)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": llm.model_name(), "text": text,
                                        "seconds": round(time.monotonic() - started, 3)}), encoding="utf-8")
            return text

        llm._generate_text = cached_generate
        if self.offline:
            llm._client = lambda: None  # no credentials needed when every call is a cache hit
        return self
