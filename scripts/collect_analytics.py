"""
Analytics collection script for LinkedIn post review workflow.

Navigates to the profile's recent-activity page (LINKEDIN_ACTIVITY_URL), finds
the post that matches the session's draft content, clicks "View analytics",
then scrapes metrics: impressions, reactions, comments, reposts, saves, sends,
profile views, followers gained. Also checks Golden Hour target posts for replies.

Run from repo root:
  python scripts/collect_analytics.py --session-dir outputs/<session_id>

Requires: draft_final.md and LINKEDIN_ACTIVITY_URL in .env. Writes analytics.json
to the session folder. Uses headed mode via tools/browser.get_browser_context().

If all metrics return zero, the script sets selector_stale=True; raise a system
update in the next review.
"""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from loguru import logger


def _extract_number(text: str) -> int:
    """Extract the first integer from a string. Returns 0 if none found."""
    digits = "".join(c for c in text if c.isdigit() or c == ",")
    return int(digits.replace(",", "")) if digits else 0


def _try_selectors(page, selectors: list) -> int:
    """
    Try a list of selectors in order and return the first numeric value found.
    Returns 0 if no selector matches. Includes random micro-delay between attempts
    to simulate natural reading behaviour.
    """
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.count() > 0:
                text = el.inner_text().strip()
                value = _extract_number(text)
                if value > 0:
                    return value
        except Exception:
            pass
        time.sleep(random.uniform(0.1, 0.3))
    return 0


def _analytics_url_to_feed_url(analytics_url: str) -> str:
    """Derive feed post URL from analytics page URL."""
    # analytics_url like .../analytics/post-summary/urn:li:activity:ID/
    prefix = "urn:li:activity:"
    if prefix in analytics_url:
        activity_urn = analytics_url[analytics_url.find(prefix):].rstrip("/").split("?")[0]
        return f"https://www.linkedin.com/feed/update/{activity_urn}/"
    return ""


def _scroll_activity_feed(page, max_scrolls: int = 5) -> None:
    """Scroll the activity feed and click 'Show more results' so more posts load."""
    for _ in range(max_scrolls):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        time.sleep(random.uniform(1.5, 2.5))
        try:
            show_more = page.get_by_role("button", name="Show more results").first
            if show_more.is_visible():
                show_more.click(timeout=3000)
                time.sleep(random.uniform(2.0, 3.0))
        except Exception:
            pass


def _card_text_matches_draft(card_text: str, draft_snippet: str) -> bool:
    """
    Return True if card_text is likely the same post as draft_snippet.
    Uses exact substring, short substring, and signature tokens (e.g. "1,250" + "ED" or "scribe")
    so we match when LinkedIn shows slightly different wording (e.g. "hit 1,250 clinicians").
    """
    if not (card_text or "").strip() or not (draft_snippet or "").strip():
        return False
    snippet = (draft_snippet or "").strip()[:80]
    key = snippet[:50].replace("\n", " ").strip()
    key_short = snippet[:25].replace("\n", " ").strip() if len(snippet) >= 25 else ""
    ct = (card_text or "").strip()
    if key and key in ct:
        return True
    if key_short and key_short in ct:
        return True
    # Signature tokens: distinctive numbers or phrases that appear in both draft and live post
    numbers = re.findall(r"[0-9,]+", snippet)
    words = [w for w in re.findall(r"[A-Za-z]+", snippet) if len(w) >= 3]
    # Require at least one number (e.g. 1,250) and one meaningful word (ED, scribe, clinicians, emergency)
    for num in numbers:
        if num in ct and any(w in ct for w in words[:8]):
            return True
    return False


def _gather_activity_cards_info(page) -> list[dict]:
    """
    After scrolling the activity feed, collect for each visible post card: data-urn,
    first 400 chars of commentary text, and analytics link href. Used by --debug-activity.
    """
    cards = page.locator('div.feed-shared-update-v2[data-urn]')
    n = cards.count()
    if n == 0:
        cards = page.locator('article[data-urn]')
        n = cards.count()
    if n == 0:
        return []
    out = []
    for i in range(n):
        card = cards.nth(i)
        try:
            urn = card.get_attribute("data-urn") or ""
            comm = card.locator(".update-components-update-v2__commentary")
            commentary = ""
            if comm.count() > 0:
                commentary = (comm.first.inner_text() or "")[:400]
            link = card.locator("a.analytics-entry-point").or_(
                card.locator('a[href*="/analytics/post-summary/"]')
            ).first
            href = ""
            if link.count() > 0:
                href = link.get_attribute("href") or ""
            out.append({"urn": urn, "commentary": commentary, "analytics_href": href})
        except Exception as e:
            out.append({"urn": "", "commentary": f"(error: {e})", "analytics_href": ""})
    return out


def _find_and_click_view_analytics(page, draft_snippet: str) -> bool:
    """
    On a LinkedIn recent-activity page, scroll to load posts, find the card whose
    commentary matches draft_snippet (exact substring or signature tokens), and
    click its "View analytics" link. If no match, click the first "View analytics".
    Returns True if we reached analytics.
    """
    from tools.browser import dismiss_modal_if_present

    dismiss_modal_if_present(page)
    _scroll_activity_feed(page)
    time.sleep(random.uniform(1.0, 1.5))

    cards = page.locator('div.feed-shared-update-v2[data-urn]')
    n = cards.count()
    if n == 0:
        cards = page.locator('article[data-urn]')
        n = cards.count()
    if n == 0:
        view_analytics = page.get_by_role("link", name="View analytics").or_(
            page.locator("a:has-text('View analytics')")
        )
        view_analytics.first.wait_for(state="visible", timeout=10000)
        view_analytics.first.click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(random.uniform(2.0, 3.0))
        dismiss_modal_if_present(page)
        return "analytics" in page.url

    clicked = False
    for i in range(n):
        card = cards.nth(i)
        try:
            if card.locator(".update-components-update-v2__commentary").count() == 0:
                continue
            card_text = card.locator(".update-components-update-v2__commentary").first.inner_text()
        except Exception:
            card_text = ""
        if _card_text_matches_draft(card_text or "", draft_snippet or ""):
            logger.info("Matched post by draft snippet; clicking View analytics")
            link = card.locator("a.analytics-entry-point").or_(
                card.locator('a[href*="/analytics/post-summary/"]')
            ).first
            link.click(timeout=5000)
            clicked = True
            break

    if not clicked:
        logger.info("No matching post card; clicking first View analytics (most recent)")
        view_analytics = page.get_by_role("link", name="View analytics").or_(
            page.locator("a:has-text('View analytics')")
        ).first
        view_analytics.click(timeout=5000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    time.sleep(random.uniform(2.0, 3.0))
    dismiss_modal_if_present(page)
    return "analytics" in page.url


def scrape_post_analytics(context, draft_snippet: str, profile_activity_url: str):
    """
    Navigate to profile recent-activity page, find the post matching draft_snippet,
    click "View analytics", then scrape all metrics.

    Returns (analytics_dict, page). Caller must close the page. Sets post_url in
    analytics from the analytics page URL. Sets selector_stale=True if all metrics zero.
    """
    from tools.browser import dismiss_modal_if_present

    page = context.new_page()
    analytics = {
        "impressions": 0,
        "members_reached": 0,
        "reactions": 0,
        "comments": 0,
        "reposts": 0,
        "saves": 0,
        "sends": 0,
        "profile_views_from_post": 0,
        "followers_gained": 0,
        "post_url": "",
        "selector_stale": False,
        "analytics_load_failed": False,
        "scraped_at": __import__("datetime").datetime.now().isoformat(),
    }

    try:
        logger.info("Navigating to activity page: {}", profile_activity_url)
        page.goto(profile_activity_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(random.uniform(2.5, 3.5))
        dismiss_modal_if_present(page)

        if not _find_and_click_view_analytics(page, draft_snippet):
            analytics["analytics_load_failed"] = True
            logger.warning(
                "Could not reach analytics page from activity feed. "
                "Check LINKEDIN_ACTIVITY_URL and that the post appears on the page."
            )
            return analytics, page

        analytics["post_url"] = _analytics_url_to_feed_url(page.url)

        # Natural scroll before reading
        page.evaluate("window.scrollBy(0, 300)")
        time.sleep(random.uniform(0.8, 1.5))

        try:
            if page.get_by_text("Analytics failed to load", exact=True).first.is_visible():
                analytics["analytics_load_failed"] = True
                logger.warning(
                    "LinkedIn analytics page showed 'Analytics failed to load'. "
                    "Try reloading the page manually or retry later."
                )
        except Exception:
            pass

        # Impressions — "Discovery" section: li.member-analytics-addon-summary__list-item
        analytics["impressions"] = _try_selectors(page, [
            "li.member-analytics-addon-summary__list-item:has-text('Impressions') p.text-heading-large",
            "li:has-text('Impressions') p.text-heading-large",
            "li:has-text('Impressions') p.text-body-medium-bold",
        ])

        # Members reached — second li in same "Discovery" section
        analytics["members_reached"] = _try_selectors(page, [
            "li.member-analytics-addon-summary__list-item:has-text('Members reached') p.text-heading-large",
            "li:has-text('Members reached') p.text-heading-large",
            "li:has-text('Members reached') p.text-body-medium-bold",
        ])

        # Reactions — "Social engagement" section; clickable items use <a> with resultType param
        analytics["reactions"] = _try_selectors(page, [
            "a[href*='resultType=REACTIONS'] span.member-analytics-addon__cta-list-item-text",
            "li:has-text('Reactions') span.member-analytics-addon__cta-list-item-text",
        ])

        # Comments
        analytics["comments"] = _try_selectors(page, [
            "a[href*='resultType=COMMENTS'] span.member-analytics-addon__cta-list-item-text",
            "li:has-text('Comments') span.member-analytics-addon__cta-list-item-text",
        ])

        # Reposts — non-clickable items use div.member-analytics-addon__cta-list-item-content
        analytics["reposts"] = _try_selectors(page, [
            "div.member-analytics-addon__cta-list-item-content:has-text('Reposts') span.member-analytics-addon__cta-list-item-text",
            "li:has-text('Reposts') span.member-analytics-addon__cta-list-item-text",
        ])

        # Saves
        analytics["saves"] = _try_selectors(page, [
            "div.member-analytics-addon__cta-list-item-content:has-text('Saves') span.member-analytics-addon__cta-list-item-text",
            "li:has-text('Saves') span.member-analytics-addon__cta-list-item-text",
        ])

        # Sends — label is "Sends on LinkedIn" in current LinkedIn UI
        analytics["sends"] = _try_selectors(page, [
            "div.member-analytics-addon__cta-list-item-content:has-text('Sends on LinkedIn') span.member-analytics-addon__cta-list-item-text",
            "div.member-analytics-addon__cta-list-item-content:has-text('Sends') span.member-analytics-addon__cta-list-item-text",
            "li:has-text('Sends on LinkedIn') span.member-analytics-addon__cta-list-item-text",
        ])

        # Profile views and followers gained — "Profile activity" section
        for label, key in [
            ("Profile viewers from this post", "profile_views_from_post"),
            ("Followers gained from this post", "followers_gained"),
        ]:
            value = _try_selectors(page, [
                f"div.member-analytics-addon-metric-row-list-item:has-text('{label}') span.member-analytics-addon-metric-row-list-item__value",
                f"li:has-text('{label}') span.member-analytics-addon-metric-row-list-item__value",
            ])
            analytics[key] = value

        # Selector staleness check — if all engagement metrics are zero,
        # selectors have probably changed. Do not set selector_stale when
        # the page showed "Analytics failed to load" (that is a LinkedIn API error).
        if not analytics.get("analytics_load_failed"):
            engagement_total = (
                analytics["reactions"]
                + analytics["comments"]
                + analytics["reposts"]
                + analytics["saves"]
                + analytics["sends"]
            )
            if engagement_total == 0 and analytics["impressions"] == 0:
                analytics["selector_stale"] = True
                logger.warning(
                    "SELECTOR_STALE: all metrics returned zero. "
                    "LinkedIn frontend selectors may have changed. "
                    "Raise a system update in the next review."
                )

        logger.info("Analytics scraped: {}", analytics)
        return analytics, page

    except Exception as e:
        logger.error("scrape_post_analytics failed: {}", e)
        analytics["error"] = str(e)
        return analytics, page
    # Caller closes page so context remains valid for check_golden_hour_replies


def _scroll_to_comments(page) -> None:
    """Scroll the post page so the comment section below the fold is in view."""
    from tools.browser import dismiss_modal_if_present

    dismiss_modal_if_present(page)
    for _ in range(3):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        time.sleep(random.uniform(0.4, 0.8))
    time.sleep(random.uniform(1.0, 1.5))


_COMMENT_METRICS_JS = """
(args) => {
    // Walk the DOM using a text-node TreeWalker. For each snippet length (longest first),
    // try to find a text node containing the snippet, then walk up to the comment block
    // (identified by the first ancestor that owns a .comments-comment-social-bar--cr),
    // and extract impressions, likes, and reply count from the social bar.
    const {snippet, lengths} = args;
    const parseNum = t => { const m = (t || '').match(/\\d+/); return m ? parseInt(m[0]) : 0; };

    for (const len of lengths) {
        const s = snippet.substring(0, len).trim();
        if (s.length < 10) break;

        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            if (!(node.nodeValue || '').includes(s)) continue;

            // Walk up until we find an ancestor that owns the comment social bar
            let el = node.parentElement;
            let commentBlock = null;
            for (let j = 0; j < 20 && el; j++) {
                if (el.querySelector('.comments-comment-social-bar--cr')) {
                    commentBlock = el;
                    break;
                }
                el = el.parentElement;
            }
            if (!commentBlock) continue;

            const bar = commentBlock.querySelector('.comments-comment-social-bar--cr');
            if (!bar) continue;

            const impressionsEl = bar.querySelector('.comments-comment-social-bar__impressions-count');
            const likesEl       = bar.querySelector('.comments-comment-social-bar__reactions-count--cr span[aria-hidden="true"]');
            const repliesEl     = bar.querySelector('.comments-comment-social-bar__replies-count--cr');

            return {
                found:       true,
                impressions: parseNum(impressionsEl ? impressionsEl.innerText : ''),
                likes:       parseNum(likesEl ? likesEl.innerText : ''),
                replies:     parseNum(repliesEl ? repliesEl.innerText : '')
            };
        }
    }
    return {found: false, impressions: 0, likes: 0, replies: 0};
}
"""

_EMPTY_COMMENT_METRICS: dict = {"found": False, "impressions": 0, "likes": 0, "replies": 0}


def _scrape_comment_metrics_via_js(page, our_snippet: str) -> dict:
    """
    Use a single JS evaluation to find our comment by text and extract
    impressions, likes, and reply count from the comment's social bar.

    Returns {"found": bool, "impressions": int, "likes": int, "replies": int}.

    Selectors read from the LinkedIn comment social bar HTML (March 2026):
      - Impressions: .comments-comment-social-bar__impressions-count
      - Likes:       .comments-comment-social-bar__reactions-count--cr span[aria-hidden="true"]
      - Replies:     .comments-comment-social-bar__replies-count--cr
    """
    try:
        result = page.evaluate(
            _COMMENT_METRICS_JS,
            {"snippet": our_snippet, "lengths": [50, 40, 30, 20]},
        )
        if isinstance(result, dict):
            return {
                "found":       bool(result.get("found", False)),
                "impressions": int(result.get("impressions", 0)),
                "likes":       int(result.get("likes", 0)),
                "replies":     int(result.get("replies", 0)),
            }
    except Exception as e:
        logger.debug("_scrape_comment_metrics_via_js error: {}", e)
    return dict(_EMPTY_COMMENT_METRICS)


def check_golden_hour_replies(context, scout_targets: list, comments_list: list) -> dict:
    """
    For each Golden Hour target post, navigate to the post, scroll to comments,
    and extract impressions, likes, and reply count for our pre-engagement comment.

    Returns dict mapping index (str) to:
        {"found": bool, "impressions": int, "likes": int, "replies": int}

    Caller should pass scout_targets and comments_list from session_state.json
    when present (what was actually posted); main() falls back to engagement.json.
    """
    from tools.browser import dismiss_modal_if_present

    results = {}
    for i, target in enumerate(scout_targets[:6]):
        post_url = target.get("post_url") or target.get("url")
        our_comment = comments_list[i] if i < len(comments_list) else ""
        if not post_url or not our_comment:
            results[str(i)] = dict(_EMPTY_COMMENT_METRICS)
            continue

        our_snippet = our_comment[:60].strip()

        page = context.new_page()
        try:
            page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(random.uniform(2.0, 3.0))
            _scroll_to_comments(page)

            metrics = _scrape_comment_metrics_via_js(page, our_snippet)
            results[str(i)] = metrics
            if metrics["found"]:
                logger.debug(
                    "Target {}: found=True impressions={} likes={} replies={}",
                    i, metrics["impressions"], metrics["likes"], metrics["replies"],
                )
            else:
                logger.debug("Target {}: our comment not found (snippet: {!r})", i, our_snippet[:40])

        except Exception as e:
            logger.debug("check_golden_hour_replies target {}: {}", i, e)
            results[str(i)] = dict(_EMPTY_COMMENT_METRICS)
        finally:
            page.close()
            time.sleep(random.uniform(1.5, 3.0))

    return results


def _dump_analytics_page_html(context, draft_snippet: str, profile_activity_url: str, session_dir: Path) -> None:
    """Navigate to activity page, open analytics via View analytics, dump HTML for debugging."""
    page = context.new_page()
    try:
        page.goto(profile_activity_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(random.uniform(2.5, 3.5))
        if _find_and_click_view_analytics(page, draft_snippet):
            time.sleep(random.uniform(2.0, 3.0))
        html = page.content()
        (session_dir / "analytics_page_snapshot.html").write_text(html, encoding="utf-8")
    finally:
        page.close()


def _debug_activity_page(
    context, draft_snippet: str, profile_activity_url: str, session_dir: Path
) -> None:
    """
    Navigate to activity page, scroll, gather each card's urn/commentary/analytics href,
    write activity_debug.json and print a summary. Use --debug-activity to run.
    """
    from tools.browser import dismiss_modal_if_present

    page = context.new_page()
    try:
        page.goto(profile_activity_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(random.uniform(2.5, 3.5))
        dismiss_modal_if_present(page)
        _scroll_activity_feed(page)
        time.sleep(random.uniform(1.0, 1.5))
        cards_info = _gather_activity_cards_info(page)
        payload = {
            "draft_snippet": (draft_snippet or "").strip()[:200],
            "cards_count": len(cards_info),
            "cards": cards_info,
        }
        out_file = session_dir / "activity_debug.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {out_file}")
        print(f"Draft snippet (first 80 chars): {(draft_snippet or '').strip()[:80]!r}")
        print(f"Cards found: {len(cards_info)}")
        for idx, c in enumerate(cards_info):
            match = "MATCH" if _card_text_matches_draft(c.get("commentary") or "", draft_snippet or "") else ""
            comm = (c.get("commentary") or "")[:120].replace("\n", " ")
            print(f"  [{idx}] urn={c.get('urn', '')[:50]}... | {comm!r}... {match}")
    finally:
        page.close()


def _debug_golden_hour_page(
    context,
    session_dir: Path,
    scout_targets: list,
    comments_list: list,
    target_index: int = 0,
) -> None:
    """
    Open one Golden Hour target post, scroll to comments, dump HTML and a short
    list of visible comment-like text so we can see where our comment is.
    Use --debug-golden-hour to run.
    """
    from tools.browser import dismiss_modal_if_present

    if target_index >= len(scout_targets) or target_index >= len(comments_list):
        print(f"Target index {target_index} out of range (scout_targets={len(scout_targets)}, comments_list={len(comments_list)})")
        return
    post_url = scout_targets[target_index].get("post_url") or scout_targets[target_index].get("url")
    our_comment = comments_list[target_index]
    our_snippet = (our_comment or "")[:60].strip()

    page = context.new_page()
    try:
        page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(random.uniform(2.0, 3.0))
        _scroll_to_comments(page)

        # Dump full page HTML so we can search for our snippet and inspect structure
        html_path = session_dir / f"golden_hour_debug_target{target_index}.html"
        html_path.write_text(page.content(), encoding="utf-8")
        print(f"Wrote {html_path}")

        # Also run JS to list visible text from comment-like nodes (tag/class + first 200 chars)
        comments_info = page.evaluate(
            """
            () => {
                const nodes = document.querySelectorAll('article[class*="comment"], [class*="comments-comment"], [class*="comment-entity"]');
                return Array.from(nodes).slice(0, 30).map((el, i) => ({
                    index: i,
                    tag: el.tagName,
                    className: (el.className || '').substring(0, 120),
                    text: (el.innerText || '').replace(/\\s+/g, ' ').trim().substring(0, 220)
                }));
            }
            """
        )
        out_path = session_dir / f"golden_hour_debug_target{target_index}_comments.json"
        out_path.write_text(json.dumps({"our_snippet": our_snippet, "comments": comments_info}, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")
        print(f"Our snippet (looking for): {our_snippet!r}")
        for c in comments_info[:10]:
            print(f"  [{c['index']}] {c['tag']}.{c['className'][:50]}... | {c['text'][:80]!r}...")
    finally:
        page.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect LinkedIn post analytics for review workflow."
    )
    parser.add_argument(
        "--session-dir",
        type=str,
        required=True,
        help="Path to session folder (e.g. outputs/2026-03-05_topic)",
    )
    parser.add_argument(
        "--dump-html",
        action="store_true",
        help="Navigate to activity page, open analytics, dump HTML to session_dir/analytics_page_snapshot.html for selector debugging.",
    )
    parser.add_argument(
        "--debug-activity",
        action="store_true",
        help="Navigate to activity page, scroll, gather each card's urn/commentary/analytics href; write session_dir/activity_debug.json and print summary (no analytics scrape).",
    )
    parser.add_argument(
        "--debug-golden-hour",
        type=int,
        metavar="TARGET_INDEX",
        default=None,
        help="Open one Golden Hour target post (0-5), scroll to comments, dump session_dir/golden_hour_debug_targetN.html and _comments.json so you can see where your comment is (no analytics scrape).",
    )
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    draft_file = session_dir / "draft_final.md"
    if not draft_file.exists():
        print(
            "Error: draft_final.md not found in session folder. Needed to match the post on the activity page.",
            file=sys.stderr,
        )
        return 1

    draft_snippet = draft_file.read_text(encoding="utf-8").strip()[:80]

    activity_url = os.getenv("LINKEDIN_ACTIVITY_URL", "").strip()
    if not activity_url:
        print(
            "Error: LINKEDIN_ACTIVITY_URL not set. Add it to .env (see .env.example).",
            file=sys.stderr,
        )
        return 1

    # Prefer session_state.json for Golden Hour targets and comments (what was actually posted).
    # Fall back to engagement.json when session_state is missing (e.g. pre-assembly).
    scout_targets = []
    comments_list = []
    session_state_file = session_dir / "session_state.json"
    if session_state_file.exists():
        session_state = json.loads(session_state_file.read_text(encoding="utf-8"))
        scout_targets = session_state.get("scout_targets") or []
        comments_list = session_state.get("comments_list") or []
    if not scout_targets or not comments_list:
        engagement_file = session_dir / "engagement.json"
        if engagement_file.exists():
            engagement = json.loads(engagement_file.read_text(encoding="utf-8"))
            if not scout_targets:
                scout_targets = engagement.get("scout_targets") or []
            if not comments_list:
                comments_list = engagement.get("comments_list") or []

    from tools.browser import get_browser_context

    context = get_browser_context()
    analytics_page = None
    try:
        if args.dump_html:
            _dump_analytics_page_html(context, draft_snippet, activity_url, session_dir)
            print(f"Dumped HTML to {session_dir / 'analytics_page_snapshot.html'}")
            return 0
        if args.debug_activity:
            _debug_activity_page(context, draft_snippet, activity_url, session_dir)
            return 0
        if args.debug_golden_hour is not None:
            _debug_golden_hour_page(
                context, session_dir, scout_targets, comments_list, args.debug_golden_hour
            )
            return 0

        print("Scraping analytics (activity page -> View analytics -> metrics)")
        analytics, analytics_page = scrape_post_analytics(
            context, draft_snippet, activity_url
        )

        if analytics.get("analytics_load_failed"):
            print(
                "WARNING: LinkedIn showed 'Analytics failed to load'. "
                "Try opening the analytics URL in the browser and clicking 'Reload page', or retry later."
            )
        elif analytics.get("selector_stale"):
            print(
                "WARNING: All metrics returned zero. Selectors may be stale. "
                "Check the analytics page manually and raise a system update."
            )

        print("Checking Golden Hour comment replies...")
        golden_hour_replies = check_golden_hour_replies(
            context, scout_targets, comments_list
        )
        analytics["golden_hour_replies"] = golden_hour_replies

        (session_dir / "analytics.json").write_text(
            json.dumps(analytics, indent=2), encoding="utf-8"
        )
        print(f"Wrote analytics.json to {session_dir}")
        print(f"  Impressions:   {analytics.get('impressions', 0)}")
        print(f"  Members reach: {analytics.get('members_reached', 0)}")
        print(f"  Reactions:     {analytics.get('reactions', 0)}")
        print(f"  Comments:      {analytics.get('comments', 0)}")
        print(f"  Reposts:       {analytics.get('reposts', 0)}")
        print(f"  Saves:         {analytics.get('saves', 0)}")
        print(f"  Sends:         {analytics.get('sends', 0)}")
        print(f"  Profile views: {analytics.get('profile_views_from_post', 0)}")
        print(f"  Followers:     {analytics.get('followers_gained', 0)}")
        gh_values = list(golden_hour_replies.values())
        reply_count = sum(1 for v in gh_values if isinstance(v, dict) and v.get("replies", 0) > 0)
        gh_impressions = sum(v.get("impressions", 0) for v in gh_values if isinstance(v, dict))
        gh_likes = sum(v.get("likes", 0) for v in gh_values if isinstance(v, dict))
        print(f"  GH replies:    {reply_count}/6")
        print(f"  GH impressions:{gh_impressions}")
        print(f"  GH likes:      {gh_likes}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if analytics_page:
            try:
                analytics_page.close()
            except Exception:
                pass
        try:
            context.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
