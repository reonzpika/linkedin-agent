"""
LinkedIn Scout: Golden Hour target discovery via personal feed and pinned company posts.
Returns up to 30 feed targets plus optional pinned targets (e.g. HINZ latest); does NOT draft comments (Architect's job).
"""

import json
from pathlib import Path

from graph.state import LinkedInContext

OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"


def _load_recent_engagement_urls() -> set[str]:
    """Load URLs from all engagement.json files to avoid repeats."""
    recent_urls = set()
    if OUTPUTS.exists():
        for p in OUTPUTS.rglob("engagement.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for t in data.get("targets", []) or data.get("scout_targets", []):
                    u = t.get("url") or t.get("post_url")
                    if u:
                        recent_urls.add(u)
            except Exception:
                pass
    return recent_urls


def _filter_spam_and_recruiters(posts: list[dict]) -> list[dict]:
    """Filter out recruiters, hiring posts, vendor spam."""
    filtered = []
    for post in posts:
        author_name = (post.get("name") or "").lower()
        snippet = (post.get("snippet") or "").lower()

        if any(
            word in author_name
            for word in [
                "recruiter",
                "hiring",
                "recruitment",
                "talent acquisition",
            ]
        ):
            continue

        if any(
            phrase in snippet
            for phrase in [
                "we're hiring",
                "job opening",
                "apply now",
                "join our team",
            ]
        ):
            continue

        if any(
            phrase in snippet
            for phrase in ["buy now", "limited offer", "demo", "free trial"]
        ):
            continue

        filtered.append(post)

    return filtered


def run(state: LinkedInContext) -> dict:
    """
    Gather Golden Hour targets: personal feed (up to 30) plus pinned company latest posts.
    Returns scout_targets (feed) and scout_targets_pinned (no comments).
    """
    recent_urls = _load_recent_engagement_urls()

    from tools.browser import get_browser_context, scrape_personal_feed, scrape_company_latest_post

    ctx = get_browser_context()
    scout_targets: list[dict] = []
    scout_targets_pinned: list[dict] = []

    try:
        feed_posts = scrape_personal_feed(ctx, max_posts=60)
        filtered = _filter_spam_and_recruiters(feed_posts)
        filtered = [p for p in filtered if p.get("post_url") not in recent_urls]
        scout_targets = filtered[:30]

        # Pinned: e.g. HINZ latest post (config in config/pinned_targets.json)
        try:
            config_path = Path(__file__).resolve().parent.parent / "config" / "pinned_targets.json"
            if config_path.exists():
                pinned_cfg = json.loads(config_path.read_text(encoding="utf-8"))
                for company_posts_url in (pinned_cfg.get("company_posts_urls") or [])[:5]:
                    row = scrape_company_latest_post(ctx, company_posts_url)
                    if row and row.get("post_url") and row["post_url"] not in recent_urls:
                        if "snippet" in row and "rationale" not in row:
                            row["rationale"] = row["snippet"]
                        row["company_posts_url"] = company_posts_url
                        scout_targets_pinned.append(row)
        except Exception:
            pass
    finally:
        ctx.close()

    for target in scout_targets:
        if "snippet" in target and "rationale" not in target:
            target["rationale"] = target["snippet"]

    return {"scout_targets": scout_targets, "scout_targets_pinned": scout_targets_pinned}
