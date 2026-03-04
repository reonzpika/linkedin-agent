"""
Golden Hour posting protocol: post 6 pre-engagement comments then schedule main post.
Used by execute_post.py. State dict must have scout_targets, comments_list, post_draft, first_comment.
"""

from datetime import datetime, timedelta
from typing import Any


def executor_run(state: dict, context: Any) -> dict:
    """
    Execute Golden Hour posting protocol. Called by execute_post.py.
    Posts 6 pre-engagement comments then schedules main post. Raises RuntimeError on failure.
    """
    from tools.browser import post_comment, schedule_post

    scout_targets = (state.get("scout_targets") or [])[:6]
    comments_list = state.get("comments_list") or []
    post_draft = state.get("post_draft") or ""
    first_comment = state.get("first_comment") or ""

    results: list[dict] = []

    for i, target in enumerate(scout_targets):
        if i >= len(comments_list):
            break
        comment_text = comments_list[i]
        post_url = target.get("post_url") or target.get("url")
        if post_url and comment_text:
            r = post_comment(context, post_url, comment_text)
            results.append({
                "type": "comment",
                "target": target.get("name", ""),
                "post_url": post_url,
                "result": r,
            })
            if not r.get("success"):
                raise RuntimeError(
                    r.get("error", "post_comment failed")
                )

    n = datetime.utcnow()
    days_ahead = (1 - n.weekday()) % 7
    if days_ahead == 0 and n.hour >= 21:
        days_ahead = 7
    scheduled = (
        (n + timedelta(days=days_ahead))
        .replace(hour=19, minute=0, second=0, microsecond=0)
        .isoformat()
        + "Z"
    )
    r = schedule_post(context, post_draft, first_comment, scheduled)
    results.append({"type": "main_post", "result": r})
    if not r.get("success"):
        raise RuntimeError(r.get("error", "schedule_post failed"))

    return {"execution_results": results}
