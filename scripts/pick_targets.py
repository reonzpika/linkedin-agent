"""
Pick the best 6 targets from scout output for Golden Hour engagement.
When scout_targets_pinned is present, one slot is reserved: pick (6 - len(pinned)) from feed.
Reads engagement.json and plan.json; calls Claude (picker); overwrites scout_targets,
preserves scout_targets_all (feed only). Run from repo root after scout.py, before draft.py.
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
    pinned = engagement.get("scout_targets_pinned") or []
    need_to_pick = 6 - len(pinned)

    if need_to_pick <= 0:
        engagement["scout_targets"] = pinned[:6]
        engagement["comments_list"] = []
        engagement_file.write_text(json.dumps(engagement, indent=2), encoding="utf-8")
        print("Only pinned targets; no feed pick needed. Wrote engagement.json.")
        return 0

    if len(candidates) <= need_to_pick:
        chosen = candidates + pinned
        engagement["scout_targets_all"] = candidates
        engagement["scout_targets"] = chosen[:6]
        engagement["comments_list"] = []
        engagement_file.write_text(json.dumps(engagement, indent=2), encoding="utf-8")
        print(f"Only {len(candidates)} feed targets; using all + {len(pinned)} pinned. Wrote engagement.json.")
        return 0

    plan_file = session_dir / "plan.json"
    plan_data = {}
    if plan_file.exists():
        plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    topic = (plan_data.get("angle") or plan_data.get("plan") or "")[:500]
    pillar = plan_data.get("pillar") or "pillar_1"

    from agents._llm import invoke

    system = """You are the picker for a LinkedIn Golden Hour workflow. You receive a list of candidate posts and must choose exactly N that are best for "warming up" the algorithm before the user posts their own content.

Selection criteria (mix of all; topic alignment is primary when our post has a specific theme):
1. Same specific topic (primary when our post has a clear theme): When our post is about a specific theme (e.g. healthOS, AI platforms, platform ownership, health infrastructure), prefer candidates whose snippet/content is about that same theme. Deprioritise or exclude candidates that are health-adjacent but off-topic (e.g. RACGP Hackathon or Eko stethoscope trial when our post is about platform ownership). Goal: at least 4 of the chosen N should be clearly on the same specific topic as our post, so comments land in conversations where the user's point of view is directly relevant.
2. Audience relevance: posts from or relevant to the user's audience (NZ primary care, GPs, practice managers, health tech).
3. Commentability: posts with enough substance in the snippet that we can write a genuine, substantive comment. Prefer non-empty, meaningful snippets.
4. Recency/activity: when posted_date is provided, you may favour more recent posts as a proxy for an active account.
5. Engagement: when reaction_count or comment_count are provided, prefer posts with higher engagement (more likely to get a reply).

Output format: reply with exactly N integers on one line, separated by spaces: the 0-based indices of the chosen candidates in the order you want them used. Example: 0 3 5 7 12
Do not output any other text before or after the indices."""

    user_parts = [
        f"Topic/context for our post: {topic}",
        f"Pillar: {pillar}",
        f"Choose exactly {need_to_pick} candidates (one slot reserved for pinned).",
        "",
        "Candidates (index, name, snippet, post_url, posted_date, engagement):",
    ]
    for i, t in enumerate(candidates):
        name = (t.get("name") or "").strip() or "(no name)"
        snippet = (t.get("snippet") or t.get("rationale") or "").strip()[:300]
        url = (t.get("post_url") or t.get("url") or "").strip()
        posted = (t.get("posted_date") or "").strip() or ""
        engagement_str = ""
        if t.get("reaction_count") is not None or t.get("comment_count") is not None:
            engagement_str = f" reactions={t.get('reaction_count', '')} comments={t.get('comment_count', '')}"
        user_parts.append(f"{i}: name={name} snippet={snippet} url={url} posted_date={posted}{engagement_str}")
    user = "\n".join(user_parts)

    out = invoke("picker", system, user)
    indices = []
    for match in re.finditer(r"\b(\d+)\b", out):
        idx = int(match.group(1))
        if 0 <= idx < len(candidates) and idx not in indices:
            indices.append(idx)
        if len(indices) >= need_to_pick:
            break
    indices = indices[:need_to_pick]

    if len(indices) < need_to_pick:
        indices = list(range(min(need_to_pick, len(candidates))))

    chosen_feed = [candidates[i] for i in indices]
    chosen = chosen_feed + pinned
    engagement["scout_targets_all"] = candidates
    engagement["scout_targets"] = chosen[:6]
    engagement["comments_list"] = []
    engagement_file.write_text(json.dumps(engagement, indent=2), encoding="utf-8")
    print(f"Picked {need_to_pick} from feed (indices {indices}) + {len(pinned)} pinned. Wrote engagement.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
