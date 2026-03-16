"""
Golden Hour posting protocol: post 6 pre-engagement comments then schedule main post.
Used by execute_post.py. State dict must have scout_targets, comments_list, post_draft, first_comment.
"""

import json
import time
from pathlib import Path
from typing import Any

import pytz  # type: ignore[import-untyped]

_DEBUG_LOG = Path(__file__).resolve().parent.parent / "debug-99fe3a.log"


def _dbg(msg: str, hypothesis_id: str, data: dict | None = None) -> None:
    try:
        payload = {"sessionId": "99fe3a", "hypothesisId": hypothesis_id, "location": "executor.py:executor_run", "message": msg, "data": data or {}, "timestamp": time.time() * 1000}
        _DEBUG_LOG.open("a", encoding="utf-8").write(json.dumps(payload) + "\n")
    except Exception:
        pass


def executor_run(state: dict, context: Any) -> dict:
    """
    Execute Golden Hour posting protocol at 7:40am NZST. Called by execute_post.py.

    Workflow:
    1. Posts 6 pre-engagement comments immediately (7:40am)
    2. Waits 20 minutes
    3. Posts main post + first comment (8:00am)

    Raises RuntimeError on failure.
    """
    # #region agent log
    _dbg("executor_run started", "B", {"scout_targets_len": len((state.get("scout_targets") or [])[:6]), "has_post_draft": bool((state.get("post_draft") or "").strip())})
    # #endregion
    from tools.browser import post_comment, post_comment_on_company_latest, schedule_post

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
        company_posts_url = target.get("company_posts_url")
        if company_posts_url and comment_text:
            r = post_comment_on_company_latest(context, company_posts_url, comment_text)
            results.append(
                {
                    "type": "comment",
                    "target": target.get("name", ""),
                    "post_url": company_posts_url,
                    "result": r,
                }
            )
            if not r.get("success"):
                raise RuntimeError(r.get("error", "post_comment_on_company_latest failed"))
        else:
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
    # #region agent log
    _dbg("Phase 1 done, sleeping 20 min", "B", {"comments_count": len(results)})
    # #endregion
    print("Posted 6 Golden Hour comments. Waiting 20 minutes before main post...")
    time.sleep(1200)  # 20 minutes = 1200 seconds

    # Phase 3: Post main content
    # #region agent log
    _dbg("Phase 2 done, calling schedule_post", "B", {})
    # #endregion
    # Note: schedule_post currently posts immediately (LinkedIn native scheduling not implemented)
    r = schedule_post(context, post_draft, first_comment, scheduled_time="")
    # #region agent log
    _dbg("schedule_post returned", "C", {"success": r.get("success"), "error": r.get("error", "")[:200] if r.get("error") else ""})
    # #endregion
    results.append({"type": "main_post", "result": r})
    if not r.get("success"):
        raise RuntimeError(r.get("error", "schedule_post failed"))

    return {"execution_results": results}


def executor_run_comments_only(state: dict, context: Any) -> dict:
    """
    Post 6 Golden Hour comments only. No sleep, no main post.
    Used for Phase 1 of two-phase "execute now" (Phase 2 scheduled via OS).
    """
    from tools.browser import post_comment, post_comment_on_company_latest

    scout_targets = (state.get("scout_targets") or [])[:6]
    comments_list = state.get("comments_list") or []
    results: list[dict] = []
    for i, target in enumerate(scout_targets):
        if i >= len(comments_list):
            break
        comment_text = comments_list[i]
        company_posts_url = target.get("company_posts_url")
        if company_posts_url and comment_text:
            r = post_comment_on_company_latest(context, company_posts_url, comment_text)
            results.append(
                {
                    "type": "comment",
                    "target": target.get("name", ""),
                    "post_url": company_posts_url,
                    "result": r,
                }
            )
            if not r.get("success"):
                raise RuntimeError(r.get("error", "post_comment_on_company_latest failed"))
        else:
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
