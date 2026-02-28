"""
Redis-backed LangGraph checkpointer for session persistence.
Snapshot state after every node completion; supports Time Travel Debugging via thread_id.
"""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def get_checkpointer() -> Any:
    """
    Create and return a LangGraph Redis checkpointer.
    Reads REDIS_URL from environment. Call .setup() before use.
    Used by workflow.py when compiling the graph.
    """
    from langgraph.checkpoint.redis import RedisSaver

    checkpointer = RedisSaver.from_conn_string(REDIS_URL)
    checkpointer.setup()
    return checkpointer


def resume_from_checkpoint(thread_id: str) -> Any:
    """
    Utility for Time Travel Debugging: load the latest checkpoint for the given thread.
    Returns the checkpoint state dict, or None if no checkpoint exists.
    """
    from langgraph.checkpoint.redis import RedisSaver

    checkpointer = RedisSaver.from_conn_string(REDIS_URL)
    checkpointer.setup()
    config = {"configurable": {"thread_id": thread_id}}
    checkpoints = list(checkpointer.list(config))
    if not checkpoints:
        return None
    # Return latest checkpoint (last in list)
    latest = checkpoints[-1]
    return checkpointer.get(config, latest)
