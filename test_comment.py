"""
Test script to verify comment posting. Run in headed browser to confirm
the Comment button is clicked and the comment appears.
Usage: python test_comment.py [post_url]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import os

os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

# Default: one of the session target posts
DEFAULT_TEST_URL = (
    "https://www.linkedin.com/feed/update/urn:li:activity:7431922597384331264/"
)
TEST_COMMENT = "Test comment - please ignore"


def main() -> None:
    post_url = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or DEFAULT_TEST_URL
    from tools.browser import get_browser_context, post_comment

    context = get_browser_context()
    try:
        result = post_comment(context, post_url, TEST_COMMENT)
        print(f"Result: {result}")
        if result.get("success"):
            print("Comment posted successfully.")
            print(f"Check here: {post_url}")
        else:
            print(f"Failed: {result.get('error')}")
    finally:
        context.close()


if __name__ == "__main__":
    main()
