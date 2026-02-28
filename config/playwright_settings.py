"""
Playwright settings for LinkedIn automation.
Headed mode only (never headless); session-file auth preferred; human-like delays.
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

# Session and credentials
LINKEDIN_SESSION_PATH = os.getenv(
    "LINKEDIN_SESSION_PATH", "./auth/linkedin_session.json"
)
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")


def _random_delay() -> None:
    """Delay between 500-1500 ms to simulate human behaviour."""
    import time

    time.sleep(random.uniform(0.5, 1.5))


def get_browser_context():
    """
    Return an authenticated Playwright browser context.
    Prefer session file at LINKEDIN_SESSION_PATH; fall back to credential login only
    if session is absent or expired. After credential login, save session automatically.
    """
    from playwright.sync_api import sync_playwright

    session_path = Path(LINKEDIN_SESSION_PATH)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=HEADLESS)
    context_options = {
        "viewport": VIEWPORT,
        "user_agent": USER_AGENT,
        "locale": "en-NZ",
    }

    if session_path.exists():
        try:
            context = browser.new_context(
                storage_state=str(session_path), **context_options
            )
            # Quick validation: open login page and check if we're still logged in
            page = context.new_page()
            page.goto(
                "https://www.linkedin.com/feed/",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            _random_delay()
            if "/login" in page.url or page.locator("text=Sign in").count() > 0:
                context.close()
                context = _login_with_credentials(
                    browser, context_options, session_path
                )
            else:
                page.close()
            return context
        except Exception:
            context = _login_with_credentials(browser, context_options, session_path)
            return context
    else:
        return _login_with_credentials(browser, context_options, session_path)


def _login_with_credentials(browser, context_options: dict, session_path: Path):
    """Log in via LINKEDIN_EMAIL / LINKEDIN_PASSWORD and save session to session_path."""
    if not (LINKEDIN_EMAIL and LINKEDIN_PASSWORD):
        raise RuntimeError(
            "LinkedIn session file is absent or expired. Run: python scripts/login.py"
        )
    context = browser.new_context(**context_options)
    page = context.new_page()
    page.goto(
        "https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=15000
    )
    _random_delay()
    page.get_by_label("Email or phone").fill(LINKEDIN_EMAIL)
    _random_delay()
    page.get_by_label("Password").fill(LINKEDIN_PASSWORD)
    _random_delay()
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url("**/feed/**", timeout=30000)
    context.storage_state(path=str(session_path))
    page.close()
    return context
