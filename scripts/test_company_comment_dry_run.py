"""
Dry-run test for post_comment_on_company_latest: navigate to company page,
find first post, click Comment, verify comment form appears. Does NOT fill or submit.
Run from repo root with valid LinkedIn session. No comment is posted.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HINZ_URL = "https://www.linkedin.com/company/health-informatics-new-zealand-hinz-/posts/?feedView=all"


def main() -> int:
    from tools.browser import (
        _filter_company_activity_posts,
        dismiss_modal_if_present,
        get_browser_context,
    )
    import time

    print("Dry-run: open company page, find first post, click Comment, check form visible. No comment posted.")
    ctx = get_browser_context()
    had_page = len(ctx.pages) > 0
    page = ctx.pages[0] if had_page else ctx.new_page()
    try:
        page.goto(HINZ_URL, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
        dismiss_modal_if_present(page)
        time.sleep(1.5)

        raw = page.locator("[data-urn^='urn:li:activity:']").all()
        filtered = _filter_company_activity_posts(raw)
        if not filtered:
            page.mouse.wheel(0, 600)
            time.sleep(2)
            raw = page.locator("[data-urn^='urn:li:activity:']").all()
            filtered = _filter_company_activity_posts(raw)
        if not filtered:
            print("FAIL: no activity posts found on company page")
            return 1
        print(f"OK: found {len(filtered)} activity post(s), using first")

        first_post = filtered[0]
        comment_btn = (
            first_post.get_by_role("button", name="Comment")
            .or_(first_post.locator("button[aria-label='Comment']"))
            .or_(first_post.locator("[data-finite-scroll-hotkey='c']"))
            .first
        )
        if comment_btn.count() == 0:
            print("FAIL: Comment button not found on first post")
            return 1
        comment_btn.click(timeout=5000)
        print("OK: clicked Comment")
        time.sleep(1.5)
        dismiss_modal_if_present(page)

        form = page.locator("form.comments-comment-box__form").first
        try:
            form.wait_for(state="visible", timeout=10000)
        except Exception as e:
            print(f"FAIL: comment form not visible: {e}")
            return 1
        print("OK: comment form visible (dry-run stops here; no fill, no submit)")
        return 0
    finally:
        if not had_page:
            page.close()
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
