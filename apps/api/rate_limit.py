"""
Shared rate limiting — Redis-backed sliding window with in-memory fallback.

Used by abuse_guard (hourly LLM ceiling), the WebSocket orchestrator (per-user
message rate), and /synthesize. Redis when REDIS_URL is set so limits hold
across Railway replicas and survive restarts; an in-process dict otherwise
(dev/test), so nothing here requires Redis to function.

All functions are synchronous and safe to call from async handlers (a single
fast Redis round-trip). They never raise — on any Redis error they fall back to
the in-memory path so a Redis outage degrades to per-process limiting rather
than failing requests.
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Optional

_redis = None
_redis_tried = False
_mem: dict[str, list[float]] = defaultdict(list)
_cooldowns: dict[str, float] = {}
_lock = threading.Lock()


def _get_redis():
    global _redis, _redis_tried
    if _redis is not None:
        return _redis
    if _redis_tried:
        return None
    _redis_tried = True
    url = os.getenv("REDIS_URL", "")
    if not url:
        return None
    try:
        import redis  # redis package ships both sync and asyncio clients
        client = redis.from_url(url, decode_responses=True, socket_timeout=2)
        client.ping()
        _redis = client
    except Exception:
        _redis = None
    return _redis


def hit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """
    Record one hit against `key` and report whether it's within `limit` over the
    trailing `window_seconds`. Returns (allowed, current_count).
    """
    now = time.time()
    r = _get_redis()
    if r is not None:
        try:
            zkey = f"rl:{key}"
            pipe = r.pipeline()
            pipe.zremrangebyscore(zkey, 0, now - window_seconds)
            pipe.zadd(zkey, {f"{now:.6f}-{os.urandom(4).hex()}": now})
            pipe.zcard(zkey)
            pipe.expire(zkey, window_seconds + 1)
            results = pipe.execute()
            count = int(results[2])
            return count <= limit, count
        except Exception:
            pass  # fall through to in-memory

    with _lock:
        bucket = [t for t in _mem[key] if t > now - window_seconds]
        bucket.append(now)
        _mem[key] = bucket
        return len(bucket) <= limit, len(bucket)


def set_cooldown(key: str, seconds: int) -> None:
    """Place `key` in a timed cooldown (used for abuse auto-throttle)."""
    r = _get_redis()
    if r is not None:
        try:
            r.setex(f"cd:{key}", seconds, "1")
            return
        except Exception:
            pass
    with _lock:
        _cooldowns[key] = time.time() + seconds


def cooldown_remaining(key: str) -> int:
    """Seconds remaining on a cooldown, or 0 if not cooling down."""
    r = _get_redis()
    if r is not None:
        try:
            ttl = r.ttl(f"cd:{key}")
            return max(0, int(ttl)) if ttl and ttl > 0 else 0
        except Exception:
            pass
    with _lock:
        expiry = _cooldowns.get(key)
        if expiry is None:
            return 0
        remaining = int(expiry - time.time())
        if remaining <= 0:
            _cooldowns.pop(key, None)
            return 0
        return remaining


def reset_for_testing() -> None:
    """Clear all in-memory counters and cooldowns (tests only)."""
    with _lock:
        _mem.clear()
        _cooldowns.clear()
    global _redis, _redis_tried
    _redis = None
    _redis_tried = False
