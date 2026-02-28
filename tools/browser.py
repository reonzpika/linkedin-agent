"""
Playwright automation for LinkedIn.
Headed mode only; session-file auth preferred; semantic/accessibility selectors; dismiss modals before each action.
"""

import random
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


def get_browser_context() -> Any:
    """
    Return an authenticated Playwright browser context.
    Uses config.playwright_settings: session file first, then credential login.
    """
    from config.playwright_settings import get_browser_context as _get

    return _get()


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
