"""Debug script: capture LinkedIn feed HTML and test selectors."""
from tools.browser import (
    get_browser_context,
    dismiss_modal_if_present,
    _random_delay,
)
import time

ctx = get_browser_context()
page = ctx.new_page()

try:
    page.goto(
        "https://www.linkedin.com/feed/",
        wait_until="domcontentloaded",
        timeout=20000,
    )
    _random_delay()
    dismiss_modal_if_present(page)

    for _ in range(3):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(2)

    # Save page HTML to file
    html = page.content()
    with open("linkedin_feed.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved linkedin_feed.html")

    # Try different selectors
    selectors_to_test = [
        '[data-id*="urn:li:activity"]',
        ".feed-shared-update-v2",
        "[data-urn]",
        "article",
        ".scaffold-finite-scroll__content > div",
    ]

    for selector in selectors_to_test:
        count = page.locator(selector).count()
        print(f"{selector}: {count} elements")

finally:
    ctx.close()
