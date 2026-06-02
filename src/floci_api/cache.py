"""In-memory TTL cache for floci API plan responses.

Avoids re-provisioning Moto for identical scenario requests.
Cache entries expire after TTL seconds.
"""

import hashlib
import json
import time
from threading import Lock


class TTLCache:
    """Simple in-memory cache with per-key TTL expiration."""

    def __init__(self, ttl: int = 300):
        self._ttl = ttl
        self._store: dict[str, tuple[float, dict]] = {}
        self._lock = Lock()

    def _key(self, endpoint: str, scenario: str, action: str) -> str:
        raw = f"{endpoint}|{scenario}|{action}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, endpoint: str, scenario: str, action: str) -> dict | None:
        k = self._key(endpoint, scenario, action)
        with self._lock:
            entry = self._store.get(k)
            if entry is None:
                return None
            ts, value = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[k]
                return None
            return value

    def set(self, endpoint: str, scenario: str, action: str, value: dict) -> None:
        k = self._key(endpoint, scenario, action)
        with self._lock:
            self._store[k] = (time.monotonic(), value)

    def stats(self) -> dict:
        with self._lock:
            now = time.monotonic()
            total = len(self._store)
            fresh = sum(1 for ts, _ in self._store.values() if now - ts <= self._ttl)
        return {"cached_entries": total, "fresh_entries": fresh, "ttl_seconds": self._ttl}


# Singleton — shared across all workers in the same process
plan_cache = TTLCache(ttl=300)  # 5 minutes
