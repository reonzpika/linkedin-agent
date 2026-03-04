"""
Draft script for chat-first LinkedIn workflow.
Reads plan, research, engagement from session dir; runs Architect then Strategist
(up to 2 revision loops); writes draft_final.md, draft_meta.json, and updates
engagement.json with comments_list. Run from repo root.
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
    parser = argparse.ArgumentParser(description="Run Architect + Strategist to produce draft.")
    parser.add_argument("--session-dir", type=str, required=True, help="Path to session folder")
    parser.add_argument("--revision-feedback", type=str, default="", help="User feedback for revision (e.g. when skill re-runs after Regenerate)")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    input_file = session_dir / "input.json"
    plan_file = session_dir / "plan.json"
    research_file = session_dir / "research.md"
    research_meta_file = session_dir / "research_meta.json"
    engagement_file = session_dir / "engagement.json"

    for f in (input_file, plan_file, research_file, engagement_file):
        if not f.exists():
            print(f"Error: {f.name} not found in {session_dir}", file=sys.stderr)
            return 1

    input_data = json.loads(input_file.read_text(encoding="utf-8"))
    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    research_summary = research_file.read_text(encoding="utf-8")
    engagement_data = json.loads(engagement_file.read_text(encoding="utf-8"))

    if research_meta_file.exists():
        research_meta = json.loads(research_meta_file.read_text(encoding="utf-8"))
        pillar = research_meta.get("pillar") or plan_data.get("pillar") or "pillar_1"
    else:
        pillar = plan_data.get("pillar") or "pillar_1"

    raw_input = (input_data.get("topic") or "").strip() or (input_data.get("url") or "").strip()
    scout_targets = (engagement_data.get("scout_targets") or [])[:6]

    state = {
        "raw_input": raw_input,
        "plan": plan_data.get("plan") or "",
        "pillar": pillar,
        "research_summary": research_summary,
        "scout_targets": scout_targets,
        "revision_count": 0,
        "source_url": (input_data.get("url") or "").strip(),
    }
    if (args.revision_feedback or "").strip():
        state["revision_feedback"] = args.revision_feedback.strip()

    from agents.architect import run as architect_run
    from agents.strategist import run as strategist_run

    for attempt in range(2):
        arch_update = architect_run(state)
        state.update(arch_update)
        strat_update = strategist_run(state)
        state.update(strat_update)

        if strat_update.get("strategist_approved") is True:
            break
        if attempt == 0 and (state.get("revision_count") or 0) < 2:
            state["revision_feedback"] = strat_update.get("strategist_revision_instructions") or strat_update.get("strategist_failure_notes") or "Address the guardrail failures above."

    post_draft = state.get("post_draft") or ""
    first_comment = state.get("first_comment") or ""
    hashtags = state.get("hashtags") or []
    comments_list = state.get("comments_list") or []

    (session_dir / "draft_final.md").write_text(post_draft, encoding="utf-8")
    (session_dir / "draft_meta.json").write_text(
        json.dumps({"first_comment": first_comment, "hashtags": hashtags}, indent=2),
        encoding="utf-8",
    )
    engagement_data["comments_list"] = comments_list
    (session_dir / "engagement.json").write_text(
        json.dumps(engagement_data, indent=2), encoding="utf-8"
    )
    print(f"Wrote draft_final.md, draft_meta.json, engagement.json to {session_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
