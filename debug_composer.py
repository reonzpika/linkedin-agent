"""
Standalone debug script for LinkedIn post composer.
Clicks "Start a post", takes screenshots at 0.5s, 1s, 2s, 3s (no DOM queries before),
then checks DOM at 3s. Does not call dismiss_modal_if_present.
"""
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.browser import get_browser_context


def debug() -> None:
    context = get_browser_context()
    page = context.new_page()

    try:
        print("Opening LinkedIn feed...")
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)

        print("\nClicking 'Start a post'...")
        start_btn = page.locator("button:has-text('Start a post')").first
        start_btn.click()

        print("\n=== TAKING SCREENSHOTS AT DIFFERENT TIMES ===\n")
        os.makedirs("outputs", exist_ok=True)

        time.sleep(0.5)
        page.screenshot(path="outputs/composer_0.5s.png")
        print("Screenshot at 0.5s saved to outputs/composer_0.5s.png")

        time.sleep(0.5)
        page.screenshot(path="outputs/composer_1s.png")
        print("Screenshot at 1s saved to outputs/composer_1s.png")

        time.sleep(1)
        page.screenshot(path="outputs/composer_2s.png")
        print("Screenshot at 2s saved to outputs/composer_2s.png")

        time.sleep(1)
        page.screenshot(path="outputs/composer_3s.png")
        print("Screenshot at 3s saved to outputs/composer_3s.png")

        print("\n=== CHECKING DOM AT 3s ===\n")

        all_editable = page.locator("[contenteditable='true']").all()
        print(f"Contenteditable elements: {len(all_editable)}")

        if len(all_editable) > 0:
            print("\nFound contenteditable elements:")
            for i, elem in enumerate(all_editable[:3]):
                try:
                    visible = elem.is_visible()
                    role = elem.get_attribute("role")
                    classes = elem.get_attribute("class")
                    cls_preview = (classes[:80] + "...") if classes and len(classes) > 80 else (classes or "none")
                    print(f"  Element {i}: visible={visible}, role={role}, class={cls_preview}")
                except Exception as e:
                    print(f"  Element {i}: error={e}")
        else:
            print("\nNo contenteditable elements found.")

        modals = page.locator("[role='dialog']").count()
        print(f"\n[role='dialog'] count: {modals}")

        share_box = page.locator(".share-creation-state").count()
        print(f".share-creation-state count: {share_box}")

        artdeco_modal = page.locator(".artdeco-modal").count()
        print(f".artdeco-modal count: {artdeco_modal}")

        print("\n=== Pausing 30 seconds; check browser and screenshots ===")
        time.sleep(30)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.close()


if __name__ == "__main__":
    debug()
