"""Tiny background-job helper: run a slow computation once, let callers poll for the result."""

from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tp-job")
_JOBS: dict[Any, Future] = {}
_LOCK = threading.Lock()


def get_or_start(key: Any, fn: Callable[[], Any], wait: float = 3.0) -> tuple[bool, Any]:
    """Return (done, value). Starts ``fn`` the first time ``key`` is seen and waits up to ``wait`` seconds,
    so fast (cached) work answers immediately and slow work answers 'not done yet' for the caller to poll."""
    with _LOCK:
        fut = _JOBS.get(key)
        if fut is None or (fut.done() and fut.exception() is not None):
            fut = _JOBS[key] = _POOL.submit(fn)
    try:
        return True, fut.result(timeout=wait)
    except TimeoutError:
        return False, None
    except Exception:
        with _LOCK:
            _JOBS.pop(key, None)          # allow a retry next time
        raise
