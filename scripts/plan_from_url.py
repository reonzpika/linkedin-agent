"""
Planning script for chat-first LinkedIn workflow.
Reads input.json from session dir; optionally fetches URL content; calls Claude (planner)
to produce execution plan; writes plan.json. Run from repo root.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

KNOWLEDGE = ROOT / "knowledge"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate execution plan from topic/URL for LinkedIn post.")
    parser.add_argument("--session-dir", type=str, required=True, help="Path to session folder (e.g. outputs/2026-03-03_topic)")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    input_file = session_dir / "input.json"
    if not input_file.exists():
        print(f"Error: input.json not found in {session_dir}. Create session and write input.json first.", file=sys.stderr)
        return 1

    input_data = json.loads(input_file.read_text(encoding="utf-8"))
    topic = (input_data.get("topic") or "").strip()
    url = (input_data.get("url") or "").strip()
    pillar_preference = input_data.get("pillar_preference") or ""
    angle = (input_data.get("angle") or "").strip()

    if not topic and not url:
        print("Error: input.json must have 'topic' and/or 'url'.", file=sys.stderr)
        return 1

    summary_from_url = ""
    if url:
        from tools.search import fetch_page_content
        raw = fetch_page_content(url)
        summary_from_url = (raw or "").strip()[:15000]

    nz_context = ""
    strategy = ""
    if (KNOWLEDGE / "nz_health_context.md").exists():
        nz_context = (KNOWLEDGE / "nz_health_context.md").read_text(encoding="utf-8")[:4000]
    if (KNOWLEDGE / "clinicpro_strategy.md").exists():
        strategy = (KNOWLEDGE / "clinicpro_strategy.md").read_text(encoding="utf-8")[:4000]

    from agents._llm import invoke

    system = f"""You are the planner for a LinkedIn content engine (NZ primary care, Dr Ryo Eguchi / ClinicPro).
Given a topic and/or URL content, produce a short execution plan for one LinkedIn post.

NZ context (abridged): {nz_context}

Strategy (abridged): {strategy}

Output a single JSON object (no markdown fence) with exactly these keys:
- "pillar": one of "pillar_1", "pillar_2", "pillar_3"
  (pillar_1 = Infrastructure/Medtech/APIs, pillar_2 = Building in Public/GP feedback, pillar_3 = Policy/Admin/Workforce)
- "angle": one short sentence (the hook or takeaway)
- "plan": string with 3-5 bullet points describing the execution plan (research focus, scout, draft emphasis, etc.)
If the user provided a pillar_preference, respect it when it matches a pillar; otherwise infer from topic/URL."""

    user_parts = [f"Topic: {topic or '(from URL)'}"]
    if pillar_preference:
        user_parts.append(f"Pillar preference: {pillar_preference}")
    if angle:
        user_parts.append(f"Requested angle: {angle}")
    if summary_from_url:
        user_parts.append(f"URL content (for context):\n{summary_from_url}")
    user = "\n\n".join(user_parts)

    out = invoke("planner", system, user)

    plan_text = ""
    pillar = "pillar_1"
    angle_out = angle or ""
    try:
        json_match = re.search(r"\{[\s\S]*\}", out)
        if json_match:
            obj = json.loads(json_match.group(0))
            plan_text = (obj.get("plan") or "").strip() or out[:2000]
            pillar = (obj.get("pillar") or "pillar_1").strip()
            if obj.get("angle"):
                angle_out = (obj.get("angle") or "").strip()
    except json.JSONDecodeError:
        plan_text = out[:2000]
        pillar_match = re.search(r"pillar[_\s]*[:\s]*(\w+)", out, re.I)
        if pillar_match:
            p = pillar_match.group(1).lower()
            if "2" in p or "pillar_2" in p:
                pillar = "pillar_2"
            elif "3" in p or "pillar_3" in p:
                pillar = "pillar_3"
            else:
                pillar = "pillar_1"

    plan_data = {
        "plan": plan_text,
        "pillar": pillar,
        "angle": angle_out,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if summary_from_url:
        plan_data["summary_from_url"] = summary_from_url[:5000]

    (session_dir / "plan.json").write_text(json.dumps(plan_data, indent=2), encoding="utf-8")
    print(f"Wrote plan.json to {session_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
