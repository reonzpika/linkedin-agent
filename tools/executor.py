"""
Golden Hour posting protocol: post 6 pre-engagement comments then schedule main post.
Used by execute_post.py. State dict must have scout_targets, comments_list, post_draft, first_comment.
"""

import time
from typing import Any

import pytz  # type: ignore[import-untyped]


def executor_run(state: dict, context: Any) -> dict:
    """
    Execute Golden Hour posting protocol at 7:40am NZST. Called by execute_post.py.

    Workflow:
    1. Posts 6 pre-engagement comments immediately (7:40am)
    2. Waits 20 minutes
    3. Posts main post + first comment (8:00am)

    Raises RuntimeError on failure.
    """
    from tools.browser import post_comment, schedule_post

    scout_targets = (state.get("scout_targets") or [])[:6]
    comments_list = state.get("comments_list") or []
    post_draft = state.get("post_draft") or ""
    first_comment = state.get("first_comment") or ""

    results: list[dict] = []

    # Phase 1: Post 6 Golden Hour comments
    for i, target in enumerate(scout_targets):
        if i >= len(comments_list):
            break
        comment_text = comments_list[i]
        post_url = target.get("post_url") or target.get("url")
        if post_url and comment_text:
            r = post_comment(context, post_url, comment_text)
            results.append(
                {
                    "type": "comment",
                    "target": target.get("name", ""),
                    "post_url": post_url,
                    "result": r,
                }
            )
            if not r.get("success"):
                raise RuntimeError(r.get("error", "post_comment failed"))

    # Phase 2: Wait 20 minutes for algorithm warm-up
    print("Posted 6 Golden Hour comments. Waiting 20 minutes before main post...")
    time.sleep(1200)  # 20 minutes = 1200 seconds

    # Phase 3: Post main content
    # Note: schedule_post currently posts immediately (LinkedIn native scheduling not implemented)
    r = schedule_post(context, post_draft, first_comment, scheduled_time="")
    results.append({"type": "main_post", "result": r})
    if not r.get("success"):
        raise RuntimeError(r.get("error", "schedule_post failed"))

    return {"execution_results": results}


def executor_run_main_post_only(state: dict, context: Any) -> dict:
    """
    Run only the main post and first comment (no Golden Hour comments).
    Used for testing or when comments were already posted.
    """
    from tools.browser import schedule_post

    post_draft = state.get("post_draft") or ""
    first_comment = state.get("first_comment") or ""
    r = schedule_post(context, post_draft, first_comment, scheduled_time="")
    if not r.get("success"):
        raise RuntimeError(r.get("error", "schedule_post failed"))
    return {"execution_results": [{"type": "main_post", "result": r}]}
