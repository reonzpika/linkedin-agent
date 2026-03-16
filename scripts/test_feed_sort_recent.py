"""
Quick test: open LinkedIn feed, set sort to Recent, verify the button shows Recent.
Requires valid LinkedIn session (auth/linkedin_session.json). Run from repo root.
Headed browser will open briefly.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    session_path = Path(
        os.getenv("LINKEDIN_SESSION_PATH", "auth/linkedin_session.json")
    )
    if not session_path.is_absolute():
        session_path = ROOT / session_path
    if not session_path.exists():
        print("FAIL: LinkedIn session not found. Run python scripts/login.py first.")
        return 1

    from tools.browser import (
        dismiss_modal_if_present,
        get_browser_context,
        _set_feed_sort_to_recent,
    )

    ctx = get_browser_context()
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        from tools.browser import _random_delay

        _random_delay()
        dismiss_modal_if_present(page)
        _set_feed_sort_to_recent(page)
        # Verify: sort trigger should now show "Recent"
        trigger = page.locator("button.artdeco-dropdown__trigger").filter(
            has_text="Sort by"
        )
        if trigger.count() == 0:
            print("FAIL: Sort dropdown trigger not found.")
            return 1
        text = trigger.first.text_content() or ""
        if "Recent" not in text:
            print("FAIL: Sort still not Recent. Button text:", repr(text))
            return 1
        print("PASS: Feed sort set to Recent.")
        return 0
    finally:
        ctx.close()


if __name__ == "__main__":
    sys.exit(main())
