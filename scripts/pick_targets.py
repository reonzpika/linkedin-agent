"""
Pick the best 6 targets from up to 30 scout targets for Golden Hour engagement.
Reads engagement.json and plan.json; calls Claude (picker) to select 6 (mix of
audience relevance and commentability); overwrites scout_targets in engagement.json.
Run from repo root after scout.py, before draft.py.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os

os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pick top 6 targets from scout output for Golden Hour."
    )
    parser.add_argument(
        "--session-dir",
        type=str,
        required=True,
        help="Path to session folder (e.g. outputs/2026-03-04_topic)",
    )
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    engagement_file = session_dir / "engagement.json"
    if not engagement_file.exists():
        print(f"Error: engagement.json not found in {session_dir}", file=sys.stderr)
        return 1

    engagement = json.loads(engagement_file.read_text(encoding="utf-8"))
    candidates = engagement.get("scout_targets") or []

    if len(candidates) <= 6:
        print(f"Only {len(candidates)} targets; no need to pick. Leaving as-is.")
        return 0

    plan_file = session_dir / "plan.json"
    plan_data = {}
    if plan_file.exists():
        plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    topic = (plan_data.get("angle") or plan_data.get("plan") or "")[:500]
    pillar = plan_data.get("pillar") or "pillar_1"

    from agents._llm import invoke

    system = """You are the picker for a LinkedIn Golden Hour workflow. You receive a list of candidate posts (author name, snippet, post_url) and must choose exactly 6 that are best for "warming up" the algorithm before the user posts their own content.

Selection criteria (mix of both):
1. Audience relevance: posts from or relevant to the user's audience (NZ primary care, GPs, practice managers, health tech).
2. Commentability: posts that have enough substance in the snippet that we can write a genuine, substantive comment (reply or observation) that references something specific in their post. Prefer posts with non-empty, meaningful snippets.

Output format: reply with exactly 6 integers on one line, separated by spaces: the 0-based indices of the 6 chosen candidates in the order you want them used (comment 1 for first index, etc.). Example: 0 3 5 7 12 18
Do not output any other text before or after the indices."""

    user_parts = [
        f"Topic/context for our post: {topic}",
        f"Pillar: {pillar}",
        "",
        "Candidates (index, name, snippet, post_url):",
    ]
    for i, t in enumerate(candidates):
        name = (t.get("name") or "").strip() or "(no name)"
        snippet = (t.get("snippet") or t.get("rationale") or "").strip()[:300]
        url = (t.get("post_url") or t.get("url") or "").strip()
        user_parts.append(f"{i}: name={name} snippet={snippet} url={url}")
    user = "\n".join(user_parts)

    out = invoke("picker", system, user)
    indices = []
    for match in re.finditer(r"\b(\d+)\b", out):
        idx = int(match.group(1))
        if 0 <= idx < len(candidates) and idx not in indices:
            indices.append(idx)
        if len(indices) >= 6:
            break
    indices = indices[:6]

    if len(indices) < 6:
        indices = list(range(min(6, len(candidates))))

    chosen = [candidates[i] for i in indices]
    engagement["scout_targets"] = chosen
    engagement["comments_list"] = []
    engagement_file.write_text(json.dumps(engagement, indent=2), encoding="utf-8")
    print(f"Picked 6 targets (indices {indices}). Wrote engagement.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
