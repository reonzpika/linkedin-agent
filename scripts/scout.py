"""
Scout script for chat-first LinkedIn workflow.
Reads input.json and plan.json from session dir; calls Scout agent;
writes engagement.json with scout_targets only (comments_list added by draft script).
Run from repo root. Requires valid LinkedIn session (auth/linkedin_session.json).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Scout for Golden Hour targets.")
    parser.add_argument("--session-dir", type=str, required=True, help="Path to session folder")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    input_file = session_dir / "input.json"
    plan_file = session_dir / "plan.json"
    if not input_file.exists():
        print(f"Error: input.json not found in {session_dir}", file=sys.stderr)
        return 1
    if not plan_file.exists():
        print(f"Error: plan.json not found. Run scripts/plan_from_url.py first.", file=sys.stderr)
        return 1

    input_data = json.loads(input_file.read_text(encoding="utf-8"))
    topic = (input_data.get("topic") or "").strip()
    url = (input_data.get("url") or "").strip()
    raw_input = topic or url or ""

    state = {"raw_input": raw_input}

    from agents.scout import run as scout_run

    update = scout_run(state)
    scout_targets = update.get("scout_targets") or []
    scout_targets_pinned = update.get("scout_targets_pinned") or []

    engagement = {
        "scout_targets": scout_targets,
        "scout_targets_pinned": scout_targets_pinned,
        "comments_list": [],
    }
    (session_dir / "engagement.json").write_text(
        json.dumps(engagement, indent=2), encoding="utf-8"
    )
    pin_msg = f", {len(scout_targets_pinned)} pinned" if scout_targets_pinned else ""
    print(f"Wrote engagement.json with {len(scout_targets)} targets{pin_msg} to {session_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
