"""
Playwright automation for LinkedIn.
Headed mode only; session-file auth preferred; semantic/accessibility selectors; dismiss modals before each action.
"""

import random
import re
import time
from typing import Any

from loguru import logger

# Configurable thresholds for feed scrolling and extraction (tune in one place)
MIN_SNIPPET_LENGTH = 50
STALLED_THRESHOLD = 2
SCROLL_DELAY_MIN = 2.0
SCROLL_DELAY_MAX = 3.0


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


def _filter_activity_urn_locators(locators: list[Any]) -> list[Any]:
    """
    Keep only locators whose data-id is strictly urn:li:activity: (exclude inAppPromotion, aggregate).
    """
    filtered: list[Any] = []
    for loc in locators:
        try:
            data_id = loc.get_attribute("data-id")
        except Exception:
            continue
        if (
            data_id
            and data_id.startswith("urn:li:activity:")
            and "inAppPromotion" not in data_id
            and "aggregate" not in data_id
        ):
            filtered.append(loc)
    return filtered


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
    Returns None if post URL cannot be determined or snippet is too short (below MIN_SNIPPET_LENGTH).
    """
    try:
        # Post URL: build from container data-id / data-urn
        urn = (
            post.get_attribute("data-id") or post.get_attribute("data-urn") or ""
        ).strip()
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
            author_elem = post.locator(".update-components-actor__title").first.or_(
                post.locator(".update-components-actor__name").first
            )
            name = (
                author_elem.inner_text()[:80]
                if author_elem.count() > 0
                else "LinkedIn User"
            )
        if not name:
            name = "LinkedIn User"

        # Snippet: one element only (strict mode). Prefer commentary, then description.
        desc_elem = post.locator(
            ".update-components-update-v2__commentary, .feed-shared-update-v2__description"
        ).first
        snippet = desc_elem.inner_text()[:200].strip() if desc_elem.count() > 0 else ""
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

        # Validate snippet length
        snippet_text = snippet.strip()
        if len(snippet_text) < MIN_SNIPPET_LENGTH:
            logger.debug(
                "Skipping post (snippet too short): {} chars, name='{}', url={}",
                len(snippet_text),
                (name[:30] if name else "None"),
                post_url[:80] if post_url else "unknown",
            )
            return None

        # Posted date
        time_elem = post.locator("time[datetime]").first
        posted_date = (
            time_elem.get_attribute("datetime") or "" if time_elem.count() > 0 else ""
        )
        if not posted_date:
            sub_desc = post.locator(".update-components-actor__sub-description").first
            if sub_desc.count() > 0:
                posted_date = sub_desc.inner_text()[:50].strip()

        # Skip promoted posts
        if "Promoted" in posted_date or "Promoted" in (name or ""):
            logger.debug(
                "Skipping promoted post: name='{}', url={}",
                (name[:30] if name else "None"),
                post_url[:80] if post_url else "unknown",
            )
            return None

        logger.debug(
            "Extracted post: name='{}', snippet_len={}, url={}",
            (name[:30] if name else "None"),
            len(snippet_text),
            post_url[:80] if post_url else "unknown",
        )
        return {
            "name": name,
            "url": post_url,
            "post_url": post_url,
            "snippet": snippet_text,
            "posted_date": posted_date,
        }
    except Exception as e:
        logger.debug("Extract post exception: {}", e)
        return None


def get_browser_context() -> Any:
    """
    Return an authenticated Playwright browser context.
    Uses config.playwright_settings: session file first, then credential login.
    """
    from config.playwright_settings import get_browser_context as _get

    return _get()


def _scroll_feed_until_ready(
    page: Any, target_count: int = 30, max_scrolls: int = 30
) -> tuple[list[Any], int, str]:
    """
    Scroll feed until target_count activity posts or stalled/max_scrolls.
    Uses scroll-last-post-into-view (or End key) to trigger LinkedIn lazy loading.
    Returns (filtered_post_locators, actual_count, stopped_reason).
    stopped_reason one of: "target_reached" | "stalled" | "max_scrolls"
    """
    prev_count = 0
    stalled_count = 0
    stopped_reason = "max_scrolls"
    logger.debug(
        "Starting scroll loop: target={}, max_scrolls={}", target_count, max_scrolls
    )
    for scroll_attempts in range(max_scrolls):
        # Get current posts before scrolling
        raw = page.locator("[data-id^='urn:li:activity:']").all()
        filtered = _filter_activity_urn_locators(raw)
        # Scroll last post into view to trigger lazy load; fallback to End key or wheel
        if len(filtered) > 0:
            try:
                filtered[-1].scroll_into_view_if_needed(timeout=3000)
            except Exception:
                page.mouse.wheel(0, 800)
        else:
            page.keyboard.press("End")
        time.sleep(random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX))
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception as e:
            logger.debug("networkidle timeout: {}", e)
        # Re-query after scroll
        raw = page.locator("[data-id^='urn:li:activity:']").all()
        filtered = _filter_activity_urn_locators(raw)
        current_count = len(filtered)
        logger.debug(
            "Scroll #{}: found {} raw posts, {} after URN filter",
            scroll_attempts + 1,
            len(raw),
            current_count,
        )
        if current_count >= target_count:
            stopped_reason = "target_reached"
            break
        if current_count == prev_count:
            stalled_count += 1
            logger.debug(
                "Stalled check: count unchanged at {}, stalled_count={}",
                current_count,
                stalled_count,
            )
            if stalled_count >= STALLED_THRESHOLD:
                stopped_reason = "stalled"
                break
        else:
            stalled_count = 0
        prev_count = current_count
    # Final query for extraction (fresh locators)
    raw = page.locator("[data-id^='urn:li:activity:']").all()
    filtered = _filter_activity_urn_locators(raw)
    logger.debug(
        "Scroll stopped: {} after {} scrolls, {} posts",
        stopped_reason,
        min(scroll_attempts + 1, max_scrolls),
        len(filtered),
    )
    return filtered, len(filtered), stopped_reason


def scrape_personal_feed(context: Any, max_posts: int = 30) -> list[dict[str, Any]]:
    """
    Navigate to LinkedIn personal feed, scrape recent posts.
    Scrolls until we have max_posts valid targets (after extraction and filtering).
    Returns list of {name, url, post_url, snippet, posted_date}.
    """
    page = context.new_page()
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    try:
        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        _random_delay()
        dismiss_modal_if_present(page)

        max_scroll_attempts = 100
        scroll_count = 0
        stalled_count = 0
        prev_total_posts = 0

        logger.debug("Starting feed extraction: target={} valid targets", max_posts)

        while len(results) < max_posts and scroll_count < max_scroll_attempts:
            # Scroll
            raw = page.locator("[data-id^='urn:li:activity:']").all()
            filtered = _filter_activity_urn_locators(raw)

            if len(filtered) > 0:
                try:
                    filtered[-1].scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    page.mouse.wheel(0, 800)
            else:
                page.keyboard.press("End")

            time.sleep(random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX))

            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception as e:
                logger.debug("networkidle timeout: {}", e)

            # Re-query posts
            raw = page.locator("[data-id^='urn:li:activity:']").all()
            filtered = _filter_activity_urn_locators(raw)
            total_posts = len(filtered)

            scroll_count += 1
            logger.debug(
                "Scroll #{}: {} total posts, {} valid targets so far",
                scroll_count,
                total_posts,
                len(results),
            )

            # Extract from all posts we have so far (to catch newly loaded ones)
            for post in filtered:
                if len(results) >= max_posts:
                    break

                row = _extract_post(post)
                if not row:
                    continue

                post_url = row["post_url"]
                if post_url in seen_urls:
                    continue

                seen_urls.add(post_url)
                results.append(row)
                logger.debug(
                    "Added target #{}: name='{}', snippet_len={}",
                    len(results),
                    (row["name"][:30] if row.get("name") else ""),
                    len(row.get("snippet", "")),
                )

            # Check if stalled (no new posts loaded)
            if total_posts == prev_total_posts:
                stalled_count += 1
                logger.debug(
                    "Stalled: no new posts after scroll #{}, stalled_count={}",
                    scroll_count,
                    stalled_count,
                )
                if stalled_count >= 3:
                    logger.warning(
                        "Feed stalled at {} posts, stopping (have {} valid targets)",
                        total_posts,
                        len(results),
                    )
                    break
            else:
                stalled_count = 0

            prev_total_posts = total_posts

            # Safety: if we have way more posts than needed, stop scrolling
            if total_posts > max_posts * 3:
                logger.debug(
                    "Enough posts loaded ({}), finishing extraction", total_posts
                )
                break

        logger.info(
            "Feed scraping complete: {} valid targets from {} total posts after {} scrolls",
            len(results),
            prev_total_posts,
            scroll_count,
        )

        return results[:max_posts]

    except Exception as e:
        logger.warning("scrape_personal_feed failed: {}", e)
        return []
    finally:
        page.close()


# DEPRECATED: Hashtag scraping disabled; using personal feed only.
def scrape_hashtag_posts(
    context: Any,
    hashtags: list[str],
    max_posts: int = 20,
) -> list[dict[str, Any]]:
    """
    Navigate to LinkedIn hashtag feeds, scrape recent posts.
    Uses same scroll loop as personal feed (mouse wheel, stalled detection, URN filter).
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
                # Wait for posts to appear before scrolling (hashtag DOM may load later)
                try:
                    page.wait_for_selector(
                        "[data-id^='urn:li:activity:']",
                        state="attached",
                        timeout=10000,
                    )
                    logger.debug("Hashtag #{}: posts loaded", clean_tag)
                except Exception as e:
                    logger.warning(
                        "Hashtag #{}: no posts found after 10s: {}", clean_tag, e
                    )
                    continue
                dismiss_modal_if_present(page)

                filtered_posts, actual_count, reason = _scroll_feed_until_ready(
                    page, target_count=30, max_scrolls=30
                )
                _random_delay()

                for post in filtered_posts:
                    if len(all_results) >= max_posts:
                        break
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
    Navigate to post_url, open comment box, post comment_text.
    Uses form-scoped selectors so we click the submit button inside the comment form,
    not the post-level "Comment" button that opens the box.
    Returns {success, post_url} or {success: False, error}.
    """
    page = context.new_page()
    try:
        page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
        _random_delay()
        dismiss_modal_if_present(page)
        # Step 1: Click the post-level "Comment" button to OPEN the comment box
        try:
            open_comment_btn = (
                page.get_by_role("button", name="Comment")
                .or_(page.get_by_label("Comment"))
                .or_(page.locator("[data-control-name='comment']"))
                .first
            )
            if open_comment_btn.count() > 0:
                open_comment_btn.click(timeout=5000)
                logger.debug("Clicked to open comment box")
            _random_delay()
        except Exception as e:
            logger.debug("Open comment box failed: {}", e)
            return {
                "success": False,
                "error": f"Open comment box: {e}",
                "post_url": post_url,
            }
        dismiss_modal_if_present(page)
        # Step 2: Locate the FORM container (critical for scoping submit button)
        try:
            form = page.locator("form.comments-comment-box__form").first
            form.wait_for(state="attached", timeout=10000)
            logger.debug("Comment form located")
        except Exception as e:
            logger.debug("Comment form not found: {}", e)
            return {
                "success": False,
                "error": f"Comment form timeout: {e}",
                "post_url": post_url,
            }
        # Step 3: Find editor INSIDE the form
        editor = (
            form.locator(".ql-editor")
            .or_(form.locator("div[contenteditable='true'][role='textbox']"))
            .first
        )
        try:
            editor.wait_for(state="visible", timeout=10000)
            logger.debug("Comment editor visible")
        except Exception as e:
            logger.debug("Comment editor not visible: {}", e)
            return {
                "success": False,
                "error": f"Editor timeout: {e}",
                "post_url": post_url,
            }
        # Step 4: Fill the comment text
        try:
            editor.click()
            time.sleep(0.5)
            editor.fill(comment_text)
            time.sleep(1)
            logger.debug("Filled comment text ({} chars)", len(comment_text))
        except Exception as e:
            logger.debug("Fill comment failed: {}", e)
            return {
                "success": False,
                "error": f"Fill failed: {e}",
                "post_url": post_url,
            }
        # Step 5: Find submit button INSIDE the form (scoped; not the open-comment button)
        submit = (
            form.locator("button.comments-comment-box__submit-button--cr")
            .or_(form.locator("button:has-text('Comment')"))
            .first
        )
        try:
            submit.wait_for(state="visible", timeout=5000)
            logger.debug("Submit button visible")
            if not submit.is_enabled():
                logger.debug("Submit button is disabled")
                return {
                    "success": False,
                    "error": "Submit button disabled",
                    "post_url": post_url,
                }
            submit.click(timeout=5000)
            logger.debug("Clicked submit button")
        except Exception as e:
            logger.debug("Submit button click failed: {}", e)
            return {
                "success": False,
                "error": f"Submit click failed: {e}",
                "post_url": post_url,
            }
        # Step 6: Wait and optionally verify (editor clears or comment appears)
        time.sleep(2)
        try:
            editor_content = editor.inner_text().strip()
            if len(editor_content) == 0:
                logger.debug("Comment editor cleared - submission successful")
            else:
                time.sleep(3)
                new_comment = page.locator(
                    ".comments-comments-list__comment-item"
                ).filter(has_text=comment_text[:50]).first
                if new_comment.count() > 0:
                    logger.debug("Comment found in thread - submission successful")
                else:
                    logger.debug(
                        "Comment may not have posted (editor not cleared, not in thread)"
                    )
        except Exception as e:
            logger.debug("Post-submit verification warning: {}", e)
        time.sleep(2)
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
        # Click "Start a post"
        start_btn = (
            page.locator("button:has-text('Start a post')")
            .or_(page.get_by_role("button", name="Start a post"))
            .or_(page.locator("[data-control-name='share_box_trigger']"))
            .or_(page.locator("button.artdeco-button--muted:has-text('Start a post')"))
            .first
        )
        try:
            start_btn.wait_for(state="visible", timeout=10000)
            start_btn.click(timeout=5000)
            logger.debug("Clicked 'Start a post'")
        except Exception as e:
            logger.debug("Start post button click failed: {}", e)
            return {"success": False, "error": f"Start post failed: {e}"}
        _random_delay()
        time.sleep(2)

        # Post settings dialog is handled after first Post click (below).

        time.sleep(1)

        # Find editor
        editor = page.locator(".ql-editor").first
        try:
            editor.wait_for(state="visible", timeout=10000)
            logger.debug("Post editor visible")
        except Exception as e:
            logger.debug("Post editor timeout: {}", e)
            return {"success": False, "error": f"Editor not found: {e}"}
        try:
            editor.click()
            time.sleep(0.5)
            editor.fill(post_text)
            time.sleep(1)
            logger.debug("Filled post text ({} chars)", len(post_text))
        except Exception as e:
            logger.debug("Fill text failed: {}", e)
            return {"success": False, "error": f"Fill text failed: {e}"}
        # Verify text actually filled
        try:
            editor_content = editor.inner_text().strip()
            if len(editor_content) < 10:
                logger.debug("Editor content too short: {}", editor_content[:50])
                return {"success": False, "error": "Text did not fill properly"}
            logger.debug("Verified editor contains {} chars", len(editor_content))
        except Exception as e:
            logger.debug("Could not verify editor content: {}", e)
        # Post button: use share-box_actions for specificity (footer button, not "Post to Anyone")
        post_btn = (
            page.locator(
                ".share-box_actions button.share-actions__primary-action"
            )
            .or_(
                page.locator(
                    "div.share-box_actions button:has-text('Post')"
                )
            )
            .or_(
                page.locator(
                    "button.share-actions__primary-action:has-text('Post')"
                )
            )
            .first
        )
        try:
            post_btn.wait_for(state="visible", timeout=10000)
            logger.debug("Post button visible")
            try:
                button_text = post_btn.inner_text().strip()
                logger.debug("Post button text: '{}'", button_text)
            except Exception:
                pass
            enabled = False
            for _ in range(30):
                if post_btn.is_enabled():
                    enabled = True
                    break
                time.sleep(0.1)
            if not enabled:
                logger.debug("Post button never enabled")
                return {"success": False, "error": "Post button stayed disabled"}
            logger.debug("Post button is enabled")
            post_btn.click(timeout=5000)
            logger.debug("Clicked Post button")
        except Exception as e:
            logger.debug("Post button click failed: {}", e)
            return {"success": False, "error": f"Post button failed: {e}"}

        try:
            time.sleep(2)
            composer_gone = page.locator(".share-creation-state").count() == 0
            if composer_gone:
                logger.debug("Composer closed - post likely published")
            else:
                logger.debug("Composer still visible - uncertain if posted")
            page.wait_for_url("**/feed/**", timeout=15000)
            logger.debug("Post published, returned to feed")
        except Exception as e:
            logger.debug("Post-publish transition warning: {}", e)
        _random_delay()
        time.sleep(3)
        # Get post URL from feed (first post should be ours)
        post_url = "https://www.linkedin.com/feed/"
        try:
            time.sleep(2)
            first_post = page.locator(
                "[data-id^='urn:li:activity:']"
            ).first
            if first_post.count() > 0:
                data_id = first_post.get_attribute("data-id") or ""
                if data_id and data_id.startswith("urn:li:activity:"):
                    post_url = (
                        f"https://www.linkedin.com/feed/update/{data_id}/"
                    )
                    logger.debug("Got post URL: {}", post_url[:80])
                else:
                    logger.debug(
                        "Invalid data-id: {}",
                        data_id[:50] if data_id else "None",
                    )
            else:
                logger.debug(
                    "No posts found on feed after publish"
                )
        except Exception as e:
            logger.debug("Could not extract post URL: {}", e)

        if not post_url or post_url == "https://www.linkedin.com/feed/":
            logger.warning(
                "Could not get specific post URL, skipping first comment"
            )
            first_comment = ""

        if first_comment:
            logger.debug("Posting first comment...")
            r = post_comment(context, post_url, first_comment)
            if not r.get("success"):
                logger.warning("First comment failed: {}", r.get("error"))
                return r
        return {"success": True, "post_url": post_url}
    except Exception as e:
        logger.exception("schedule_post failed")
        return {"success": False, "error": str(e)}
    finally:
        page.close()
