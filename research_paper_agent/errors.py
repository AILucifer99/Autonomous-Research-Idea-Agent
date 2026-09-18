"""
Error types, retry decorator, and structured error tracking.

Extends the existing try/except → fallback pattern (bwa_backend.py L164-184, L506-518)
into a reusable retry framework with exponential backoff + jitter.
"""

from __future__ import annotations

import functools
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Type

logger = logging.getLogger("research_paper_agent")


# ── Error Classification ─────────────────────────────────────────────

class RetryableError(Exception):
    """Transient failures: API timeout, rate limit, 5xx, network issues."""


class NonRetryableError(Exception):
    """Permanent failures: invalid schema, auth failure, bad input."""


class DegradedResultError(Exception):
    """Partial success: some results available but quality is reduced."""


# ── Retry Decorator ──────────────────────────────────────────────────

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[BaseException], ...] = (
        RetryableError, TimeoutError, ConnectionError, OSError,
    ),
):
    """
    Decorator that retries a function with exponential backoff + optional jitter.

    Non-retryable exceptions propagate immediately.
    After exhausting retries the last retryable exception is re-raised.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Optional[BaseException] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        if jitter:
                            delay *= 0.5 + random.random()
                        logger.warning(
                            "[retry] %s attempt %d/%d failed: %s — retrying in %.1fs",
                            func.__name__, attempt + 1, max_retries, exc, delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "[retry] %s exhausted %d retries — last error: %s",
                            func.__name__, max_retries, exc,
                        )
                except NonRetryableError:
                    raise
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("retry_with_backoff: unreachable")  # pragma: no cover
        return wrapper
    return decorator


# ── Error Entry Builder ──────────────────────────────────────────────

def make_error_entry(
    node_name: str,
    error: Exception,
    *,
    retryable: bool = True,
    fallback_used: str = "",
) -> Dict[str, Any]:
    """Build a structured error dict for the ``errors`` state field."""
    return {
        "node": node_name,
        "type": "retryable" if retryable else "non_retryable",
        "error_class": type(error).__name__,
        "message": str(error),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retryable": retryable,
        "fallback_used": fallback_used,
    }


def make_log_entry(node_name: str, status: str, detail: str = "") -> str:
    """Build a structured log string for the ``execution_log`` state field."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = f"[{ts}] [{node_name}] {status}"
    if detail:
        msg += f" {detail}"
    return msg
