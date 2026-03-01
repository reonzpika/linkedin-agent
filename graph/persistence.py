"""
Redis-backed LangGraph checkpointer for session persistence.
Snapshot state after every node completion; supports Time Travel Debugging via thread_id.

Production: Redis is required. The system must not silently run without it in production.
Testing: When Redis is unavailable, get_checkpointer() returns None so the graph can
compile without a checkpointer for local/test runs. Callers must handle None.
"""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

def _normalise_redis_url(url: str) -> str:
    """Ensure URL has a scheme (redis:// or rediss://) so redis.from_url accepts it."""
    u = (url or "").strip()
    # In case the value accidentally includes the key (e.g. REDIS_URL=rediss://...)
    if u.upper().startswith("REDIS_URL="):
        u = u.split("=", 1)[1].strip()
    if not u:
        return "redis://localhost:6379"
    if u.startswith("redis://") or u.startswith("rediss://") or u.startswith("unix://"):
        return u
    return "redis://" + u


REDIS_URL = _normalise_redis_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Hold reference to the context manager so the Redis connection is not closed when the saver is in use
_checkpointer_cm: Any = None


def get_checkpointer() -> Any:
    """
    Create and return a LangGraph Redis checkpointer, or None if Redis is unavailable.
    Reads REDIS_URL from environment (scheme is added if missing).
    Calls .setup() to ensure Redis search indexes exist before the graph runs.

    Production requires Redis. When Redis is unavailable (e.g. local test without
    Redis running), returns None so tests can still run; the graph compiles without
    persistence. Do not rely on this fallback in production.
    """
    global _checkpointer_cm
    try:
        from langgraph.checkpoint.redis import RedisSaver

        # from_conn_string returns a context manager; enter it and keep a ref so the connection stays open
        _checkpointer_cm = RedisSaver.from_conn_string(REDIS_URL)
        checkpointer = _checkpointer_cm.__enter__()
        checkpointer.setup()
        return checkpointer
    except Exception as e:
        print(f"Redis checkpointer failed: {e}")
        return None


def resume_from_checkpoint(thread_id: str) -> Any:
    """
    Utility for Time Travel Debugging: load the latest checkpoint for the given thread.
    Returns the checkpoint state dict, or None if no checkpoint exists.
    """
    from langgraph.checkpoint.redis import RedisSaver

    with RedisSaver.from_conn_string(REDIS_URL) as checkpointer:
        config = {"configurable": {"thread_id": thread_id}}
        checkpoints = list(checkpointer.list(config))
        if not checkpoints:
            return None
        latest = checkpoints[-1]
        return checkpointer.get(config, latest)
