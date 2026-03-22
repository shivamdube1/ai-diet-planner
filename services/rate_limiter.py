"""
Simple in-memory rate limiter — no external packages needed.
Works per IP, resets every window_seconds.
"""
import time
from collections import defaultdict
from threading import Lock

_store: dict = defaultdict(list)
_lock = Lock()


def is_allowed(key: str, max_calls: int = 5, window_seconds: int = 60) -> bool:
    """Return True if allowed, False if rate-limited."""
    now = time.time()
    with _lock:
        calls = [t for t in _store[key] if now - t < window_seconds]
        if len(calls) >= max_calls:
            _store[key] = calls
            return False
        calls.append(now)
        _store[key] = calls
        return True


def get_ip(request) -> str:
    """Get real IP even behind Render's proxy."""
    ip = (request.headers.get('X-Forwarded-For', request.remote_addr) or '127.0.0.1').split(',')[0].strip()
    return ip if ip else '127.0.0.1'
