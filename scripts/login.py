"""
Manual LinkedIn session refresh script.

Run this when:
- LINKEDIN_SESSION_PATH is missing, or
- The saved session has expired (LinkedIn will show login page when the workflow runs).

Steps:
1. Run: python scripts/login.py (from the LinkedIn repo root)
2. A browser window opens at linkedin.com/login
3. Log in manually in the browser (including 2FA if enabled)
4. When you see your feed, return to the terminal and press Enter
5. The script saves the session to LINKEDIN_SESSION_PATH (default: ./auth/linkedin_session.json)

Session validity: LinkedIn sessions typically last several days to weeks; re-run this script when the workflow reports an expired or missing session.
"""

import os
import sys
import time
from pathlib import Path

# Repo root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv()

LINKEDIN_SESSION_PATH = os.getenv(
    "LINKEDIN_SESSION_PATH", "./auth/linkedin_session.json"
)


def main() -> None:
    from playwright.sync_api import sync_playwright

    session_path = Path(LINKEDIN_SESSION_PATH)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    # When stdin is not a TTY (e.g. run from Cursor), input() often never receives Enter.
    # Use a timeout so the user can log in and the session saves automatically.
    interactive = sys.stdin.isatty()
    wait_seconds = 120 if not interactive else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        if interactive:
            print("Opening browser. Log in to LinkedIn in the window that appears.")
            print("When you see your feed, return here and press Enter to save the session.")
            input("Press Enter after you have logged in and see your feed...")
        else:
            print("Opening browser. Log in to LinkedIn in the window that appears.")
            print(f"You have {wait_seconds} seconds. Session will save automatically.")
            time.sleep(wait_seconds)
        context.storage_state(path=str(session_path))
        browser.close()
    print(f"Session saved to {session_path}")


if __name__ == "__main__":
    main()
