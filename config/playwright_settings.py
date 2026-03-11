"""
Playwright settings for LinkedIn automation.
Headed mode only (never headless); persistent browser profile for cookies, local storage, and preferences.
"""

import os
import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Headed mode only; headless triggers LinkedIn bot detection
HEADLESS = False

# Viewport
VIEWPORT = {"width": 1280, "height": 800}

# Realistic Chrome on macOS user agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Credentials for login when profile is empty or session expired
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Legacy: used by scripts/login.py for session-file flow only
LINKEDIN_SESSION_PATH = os.getenv(
    "LINKEDIN_SESSION_PATH", "./auth/linkedin_session.json"
)

# Persistent profile directory (cookies, local storage, IndexedDB)
BROWSER_PROFILE_DIR = Path("./browser_profile")


def _random_delay() -> None:
    """Delay between 500-1500 ms to simulate human behaviour."""
    import time

    time.sleep(random.uniform(0.5, 1.5))


def get_browser_context():
    """
    Return an authenticated Playwright browser context with persistent storage.
    Uses a persistent context so cookies, local storage, and preferences persist between runs.
    If not logged in (feed redirects to login), logs in via LINKEDIN_EMAIL / LINKEDIN_PASSWORD if set.
    """
    from playwright.sync_api import sync_playwright

    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        str(BROWSER_PROFILE_DIR),
        headless=HEADLESS,
        slow_mo=500,
        viewport=VIEWPORT,
        user_agent=USER_AGENT,
        locale="en-NZ",
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )

    page = context.pages[0] if context.pages else context.new_page()

    try:
        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
            timeout=15000,
        )
        _random_delay()

        if "/login" in page.url or page.locator("text=Sign in").count() > 0:
            if not (LINKEDIN_EMAIL and LINKEDIN_PASSWORD):
                raise RuntimeError(
                    "Not logged in and no credentials provided. "
                    "Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env, or run: python scripts/login.py"
                )
            page.goto(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            _random_delay()
            page.get_by_label("Email or phone").fill(LINKEDIN_EMAIL)
            _random_delay()
            page.get_by_label("Password").fill(LINKEDIN_PASSWORD)
            _random_delay()
            page.get_by_role("button", name="Sign in", exact=True).click()
            page.wait_for_url("**/feed/**", timeout=30000)
            _random_delay()
    except Exception as e:
        try:
            print(f"Login check failed: {e}")
        except UnicodeEncodeError:
            print("Login check failed (message contains non-ASCII characters)")
    # Do not close the page: leave it open so callers can reuse context.pages[0].
    # Closing the only page causes "Failed to open a new tab" on Windows when
    # scrape_personal_feed (or others) later call context.new_page().

    return context
