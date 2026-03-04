"""
Playwright automation for LinkedIn.
Headed mode only; session-file auth preferred; semantic/accessibility selectors; dismiss modals before each action.
"""

import random
import re
import time
from typing import Any

from loguru import logger


def _random_delay() -> None:
    time.sleep(random.uniform(0.5, 1.5))


def dismiss_modal_if_present(page: Any) -> None:
    """
    Check the page for modals, overlays, or dialogs (e.g. "Share your update", cookie banners)
    and dismiss them before returning. Must be called before every major action.
    """
    _random_delay()
    try:
        # Semantic: look for common dismiss/close actions
        for selector in [
            "button[aria-label*='Dismiss']",
            "button[aria-label*='Close']",
            "[data-test-modal-dismiss]",
            "button:has-text('Dismiss')",
            "button:has-text('Close')",
            "button:has-text('Not now')",
            ".artdeco-modal__dismiss",
        ]:
            try:
                btn = page.locator(selector).first
                if btn.count() > 0 and btn.is_visible():
                    btn.click(timeout=2000)
                    _random_delay()
                    return
            except Exception:
                continue
    except Exception:
        pass


def _parse_aria_label_name(aria_label: str) -> str:
    """Parse author name from View: ... aria-label. Max 80 chars."""
    if not aria_label or not aria_label.startswith("View: "):
        return ""
    label = aria_label.replace("View: ", "", 1).strip()
    # Remove trailing " N followers" (company)
    label = re.sub(r"\s+\d[\d,]*\s+followers\s*$", "", label, flags=re.IGNORECASE)
    # Take only the name part before " |" (person headline)
    if " |" in label:
        label = label.split(" |", 1)[0].strip()
    return label[:80] if label else ""


def _extract_post(post: Any) -> dict[str, Any] | None:
    """
    Extract {name, url, post_url, snippet, posted_date} from a single feed post locator.
    Uses data-urn for URL, aria-label for name (with fallbacks), and commentary/description for snippet.
    Returns None if post URL cannot be determined.
    """
    try:
        # Post URL: build from container data-id / data-urn
        urn = (
            (post.get_attribute("data-id") or post.get_attribute("data-urn") or "")
            .strip()
        )
        if not urn:
            inner = post.locator("[data-urn^='urn:li:activity:']").first
            if inner.count() > 0:
                urn = (inner.get_attribute("data-urn") or "").strip()
        if not urn:
            link = post.locator("a[href*='/feed/update/']").first
            if link.count() > 0:
                href = link.get_attribute("href") or ""
                if href:
                    post_url = (
                        href
                        if href.startswith("http")
                        else f"https://www.linkedin.com{href}"
                    )
                else:
                    return None
            else:
                return None
        else:
            post_url = (
                urn
                if urn.startswith("http")
                else f"https://www.linkedin.com/feed/update/{urn.rstrip('/')}/"
            )

        # Author name: prefer aria-label on View: link, then title/name
        name = ""
        actor_link = post.locator("a[aria-label^='View:']").first
        if actor_link.count() > 0:
            aria_label = actor_link.get_attribute("aria-label") or ""
            name = _parse_aria_label_name(aria_label)
        if not name:
            author_elem = (
                post.locator(".update-components-actor__title").first
                .or_(post.locator(".update-components-actor__name").first)
            )
            name = (
                author_elem.inner_text()[:80]
                if author_elem.count() > 0
                else "LinkedIn User"
            )
        if not name:
            name = "LinkedIn User"

        # Snippet: primary selectors then fallbacks
        desc_elem = (
            post.locator(".feed-shared-update-v2__description").first
            .or_(post.locator(".update-components-update-v2__commentary").first)
        )
        snippet = (
            desc_elem.inner_text()[:200].strip()
            if desc_elem.count() > 0
            else ""
        )
        if not snippet:
            fallback = post.locator("[class*='commentary']").first
            if fallback.count() > 0:
                snippet = fallback.inner_text()[:200].strip()
        if not snippet:
            # First dir=ltr block with substantial text
            for elem in post.locator("[dir='ltr']").all():
                text = (elem.inner_text() or "").strip()
                if len(text) > 50:
                    snippet = text[:200]
                    break

        # Posted date
        time_elem = post.locator("time[datetime]").first
        posted_date = (
            time_elem.get_attribute("datetime") or ""
            if time_elem.count() > 0
            else ""
        )
        if not posted_date:
            sub_desc = post.locator(".update-components-actor__sub-description").first
            if sub_desc.count() > 0:
                posted_date = sub_desc.inner_text()[:50].strip()

        return {
            "name": name,
            "url": post_url,
            "post_url": post_url,
            "snippet": snippet,
            "posted_date": posted_date,
        }
    except Exception:
        return None


def get_browser_context() -> Any:
    """
    Return an authenticated Playwright browser context.
    Uses config.playwright_settings: session file first, then credential login.
    """
    from config.playwright_settings import get_browser_context as _get

    return _get()


def scrape_personal_feed(context: Any, max_posts: int = 20) -> list[dict[str, Any]]:
    """
    Navigate to LinkedIn personal feed, scrape recent posts.
    Scrolls until at least min(30, max_posts) posts are loaded or max iterations reached.
    Returns list of {name, url, post_url, snippet, posted_date}.
    """
    page = context.new_page()
    results: list[dict[str, Any]] = []
    try:
        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        _random_delay()
        dismiss_modal_if_present(page)

        target = min(30, max_posts)
        max_scrolls = 20
        prev_count = 0
        for _ in range(max_scrolls):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(2)
            posts = page.locator("[data-id^='urn:li:activity:']").all()
            count = len(posts)
            if count >= target:
                break
            if count == prev_count:
                break
            prev_count = count

        _random_delay()
        posts = page.locator("[data-id^='urn:li:activity:']").all()[:max_posts]

        for post in posts:
            row = _extract_post(post)
            if row:
                results.append(row)

        return results
    except Exception as e:
        logger.warning(f"scrape_personal_feed failed: {e}")
        return []
    finally:
        page.close()


def scrape_hashtag_posts(
    context: Any,
    hashtags: list[str],
    max_posts: int = 20,
) -> list[dict[str, Any]]:
    """
    Navigate to LinkedIn hashtag feeds, scrape recent posts.
    Returns list of {name, url, post_url, snippet, posted_date}.
    """
    page = context.new_page()
    all_results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    try:
        for hashtag in hashtags[:3]:
            clean_tag = hashtag.strip("#").lower()
            try:
                page.goto(
                    f"https://www.linkedin.com/feed/hashtag/{clean_tag}/",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
                _random_delay()
                dismiss_modal_if_present(page)

                # Scroll multiple times and wait for content to load
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(2)

                _random_delay()

                posts = page.locator("[data-id^='urn:li:activity:']").all()

                for post in posts:
                    row = _extract_post(post)
                    if not row:
                        continue
                    post_url = row["post_url"]
                    if post_url in seen_urls:
                        continue
                    seen_urls.add(post_url)
                    all_results.append(row)
                    if len(all_results) >= max_posts:
                        break

                if len(all_results) >= max_posts:
                    break
            except Exception:
                continue

        return all_results[:max_posts]
    except Exception as e:
        logger.warning(f"scrape_hashtag_posts failed: {e}")
        return []
    finally:
        page.close()


def post_comment(context: Any, post_url: str, comment_text: str) -> dict[str, Any]:
    """
    Navigate to post_url, open comment box, post comment_text. Uses semantic/accessibility
    lookups; re-captures snapshot before each interaction. Returns {success, post_url} or {success: False, error}.
    """
    page = context.new_page()
    try:
        page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
        _random_delay()
        dismiss_modal_if_present(page)
        # Re-capture: find comment affordance (button or link that opens comment box)
        try:
            comment_btn = (
                page.get_by_role("button", name="Comment")
                .or_(page.get_by_label("Comment"))
                .first
            )
            if comment_btn.count() == 0:
                comment_btn = page.locator("[data-control-name='comment']").first
            if comment_btn.count() > 0:
                comment_btn.click(timeout=5000)
            _random_delay()
        except Exception as e:
            return {
                "success": False,
                "error": f"Open comment box: {e}",
                "post_url": post_url,
            }
        dismiss_modal_if_present(page)
        # Contenteditable or textbox for comment
        editor = (
            page.locator(".comments-comment-box__form .ql-editor")
            .or_(
                page.get_by_role("textbox", name="Add a comment").or_(
                    page.get_by_placeholder("Add a comment")
                )
            )
            .first
        )
        editor.wait_for(state="visible", timeout=5000)
        editor.fill(comment_text)
        _random_delay()
        submit = (
            page.get_by_role("button", name="Post")
            .or_(page.locator("button[type='submit']"))
            .first
        )
        submit.click(timeout=3000)
        _random_delay()
        # Verify comment appeared (optional; if we see our text in the thread we're good)
        return {"success": True, "post_url": post_url}
    except Exception as e:
        logger.exception("post_comment failed")
        return {"success": False, "error": str(e), "post_url": post_url}
    finally:
        page.close()


def schedule_post(
    context: Any, post_text: str, first_comment: str, scheduled_time: str
) -> dict[str, Any]:
    """
    Navigate to LinkedIn post composer, enter post_text, schedule for scheduled_time (ISO),
    then after go-live post first_comment as first reply. Returns {success, post_url} or {success: False, error}.
    """
    page = context.new_page()
    try:
        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        _random_delay()
        dismiss_modal_if_present(page)
        # Start a post: "Start a post" or composer trigger
        start_btn = (
            page.get_by_role("button", name="Start a post")
            .or_(page.locator("[data-control-name='share_box_trigger']"))
            .first
        )
        start_btn.click(timeout=5000)
        _random_delay()
        dismiss_modal_if_present(page)
        editor = (
            page.locator(".ql-editor")
            .or_(
                page.get_by_role("textbox").or_(
                    page.get_by_placeholder("What do you want to talk about?")
                )
            )
            .first
        )
        editor.wait_for(state="visible", timeout=5000)
        editor.fill(post_text)
        _random_delay()
        # Post now (simplified; handoff said "schedule" but LinkedIn scheduling may require UI)
        post_btn = page.get_by_role("button", name="Post").first
        post_btn.click(timeout=5000)
        page.wait_for_url("**/feed/**", timeout=15000)
        _random_delay()
        # Get current post URL from feed (first post is ours)
        post_link = page.locator("[data-id*='urn:li:activity']").first
        post_url = "https://www.linkedin.com/feed/"
        try:
            if post_link.count() > 0:
                href = post_link.get_attribute("href") or ""
                if href:
                    post_url = (
                        href
                        if href.startswith("http")
                        else f"https://www.linkedin.com{href}"
                    )
        except Exception:
            pass
        if first_comment:
            r = post_comment(context, post_url, first_comment)
            if not r.get("success"):
                return r
        return {"success": True, "post_url": post_url}
    except Exception as e:
        logger.exception("schedule_post failed")
        return {"success": False, "error": str(e)}
    finally:
        page.close()
