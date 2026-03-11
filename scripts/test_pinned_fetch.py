"""
One-off test: fetch HINZ (or first pinned) company latest post and print result.
Helps debug why scout_targets_pinned is empty. Run from repo root with LinkedIn session.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main() -> int:
    config_path = ROOT / "config" / "pinned_targets.json"
    if not config_path.exists():
        print("No config/pinned_targets.json")
        return 1
    urls = (json.loads(config_path.read_text(encoding="utf-8")).get("company_posts_urls") or [])[:1]
    if not urls:
        print("No company_posts_urls in config")
        return 1
    url = urls[0]
    print(f"Fetching: {url}")

    from tools.browser import get_browser_context, scrape_company_latest_post

    ctx = get_browser_context()
    try:
        row = scrape_company_latest_post(ctx, url)
        if row:
            print("OK: got post")
            print(f"  name={row.get('name', '')[:60]}")
            print(f"  post_url={row.get('post_url', '')}")
            print(f"  snippet_len={len(row.get('snippet', ''))}")
        else:
            print("Result: None (no activity posts found, or extraction failed)")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        ctx.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
