"""
LinkedIn Scout: Golden Hour target discovery via personal feed + hashtag scraping.
Returns 6 recent post targets for engagement; does NOT draft comments (Architect's job).
"""

import json
import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"
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
    Find 6 recent posts from target audience for Golden Hour engagement.
    Primary: scrape personal feed. Fallback: hashtag scraping if <6 found.
    Returns scout_targets only (no comments).
    """
    raw_input = state.get("raw_input") or ""
    recent_urls = _load_recent_engagement_urls()

    from tools.browser import get_browser_context, scrape_personal_feed, scrape_hashtag_posts

    ctx = get_browser_context()
    scout_targets: list[dict] = []

    try:
        feed_posts = scrape_personal_feed(ctx, max_posts=30)

        filtered = _filter_spam_and_recruiters(feed_posts)
        filtered = [p for p in filtered if p.get("post_url") not in recent_urls]

        if raw_input:
            keywords = raw_input.lower().split()[:3]
            relevant = []
            for post in filtered:
                snippet = (post.get("snippet") or "").lower()
                if any(kw in snippet for kw in keywords):
                    relevant.append(post)
            if len(relevant) >= 3:
                filtered = relevant

        scout_targets = filtered[:30]

        if len(scout_targets) < 30:
            hashtag_path = KNOWLEDGE / "hashtag_library.md"
            if hashtag_path.exists():
                hashtag_text = hashtag_path.read_text(encoding="utf-8")
                hashtags = re.findall(r"#[A-Za-z0-9_]+", hashtag_text)[:5]

                if hashtags:
                    hashtag_posts = scrape_hashtag_posts(
                        ctx, hashtags, max_posts=30
                    )
                    filtered_hashtag = _filter_spam_and_recruiters(
                        hashtag_posts
                    )
                    filtered_hashtag = [
                        p
                        for p in filtered_hashtag
                        if p.get("post_url") not in recent_urls
                    ]
                    seen = {t.get("post_url") for t in scout_targets}
                    for post in filtered_hashtag:
                        if len(scout_targets) >= 30:
                            break
                        if post.get("post_url") not in seen:
                            seen.add(post.get("post_url"))
                            scout_targets.append(post)
    finally:
        ctx.close()

    for target in scout_targets:
        if "snippet" in target and "rationale" not in target:
            target["rationale"] = target["snippet"]

    return {"scout_targets": scout_targets}
