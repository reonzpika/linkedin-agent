"""
Assemble session_state.json from session folder files for execute_post.py.
Reads plan.json, research.md, research_meta.json, engagement.json, draft_final.md,
draft_meta.json; writes session_state.json with scout_targets, comments_list,
post_draft, first_comment required by executor_run. Run from repo root.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble session_state.json for execution.")
    parser.add_argument("--session-dir", type=str, required=True, help="Path to session folder")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    engagement_file = session_dir / "engagement.json"
    draft_md = session_dir / "draft_final.md"
    draft_meta_file = session_dir / "draft_meta.json"

    if not engagement_file.exists():
        print(f"Error: engagement.json not found in {session_dir}", file=sys.stderr)
        return 1
    if not draft_md.exists():
        print(f"Error: draft_final.md not found. Run scripts/draft.py first.", file=sys.stderr)
        return 1
    if not draft_meta_file.exists():
        print(f"Error: draft_meta.json not found. Run scripts/draft.py first.", file=sys.stderr)
        return 1

    engagement = json.loads(engagement_file.read_text(encoding="utf-8"))
    post_draft = draft_md.read_text(encoding="utf-8")
    draft_meta = json.loads(draft_meta_file.read_text(encoding="utf-8"))

    state = {
        "scout_targets": engagement.get("scout_targets") or [],
        "comments_list": engagement.get("comments_list") or [],
        "post_draft": post_draft,
        "first_comment": draft_meta.get("first_comment") or "",
    }

    if (session_dir / "plan.json").exists():
        plan_data = json.loads((session_dir / "plan.json").read_text(encoding="utf-8"))
        state["plan"] = plan_data.get("plan") or ""
        state["pillar"] = plan_data.get("pillar") or "pillar_1"
    if (session_dir / "research_meta.json").exists():
        research_meta = json.loads((session_dir / "research_meta.json").read_text(encoding="utf-8"))
        state["target_urls"] = research_meta.get("target_urls") or []
    if (session_dir / "input.json").exists():
        input_data = json.loads((session_dir / "input.json").read_text(encoding="utf-8"))
        state["raw_input"] = (input_data.get("topic") or "") or (input_data.get("url") or "")

    (session_dir / "session_state.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )
    print(f"Wrote session_state.json to {session_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
