"""
Research script for chat-first LinkedIn workflow.
Reads input.json and plan.json from session dir; calls Researcher agent;
writes research.md and research_meta.json. On dehallucination, writes
research_dehallucination.txt and exits non-zero. Run from repo root.
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
    parser = argparse.ArgumentParser(description="Run research phase for LinkedIn post.")
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
        print(f"Error: plan.json not found in {session_dir}. Run scripts/plan_from_url.py first.", file=sys.stderr)
        return 1

    input_data = json.loads(input_file.read_text(encoding="utf-8"))
    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))

    topic = (input_data.get("topic") or "").strip()
    raw_input = topic or (input_data.get("url") or "").strip()
    if not raw_input:
        print("Error: input.json must have topic or url.", file=sys.stderr)
        return 1

    pillar = (plan_data.get("pillar") or "pillar_1").strip()
    plan_text = (plan_data.get("plan") or "").strip()

    state = {
        "raw_input": raw_input,
        "pillar": pillar,
        "plan": plan_text,
    }
    answer_file = session_dir / "research_dehallucination_answer.txt"
    if answer_file.exists():
        state["dehallucination_answer"] = answer_file.read_text(encoding="utf-8").strip()

    from agents.researcher import run as researcher_run

    update = researcher_run(state)

    if update.get("interrupt_dehallucination"):
        question = update["interrupt_dehallucination"]
        (session_dir / "research_dehallucination.txt").write_text(question, encoding="utf-8")
        print(f"Dehallucination: {question}", file=sys.stderr)
        return 2

    research_summary = update.get("research_summary") or ""
    target_urls = update.get("target_urls") or []
    pillar_out = update.get("pillar") or pillar

    (session_dir / "research.md").write_text(research_summary, encoding="utf-8")
    (session_dir / "research_meta.json").write_text(
        json.dumps({"target_urls": target_urls, "pillar": pillar_out}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote research.md and research_meta.json to {session_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
