"""
DEPRECATED: Use chat and the linkedin-post-create skill with scripts (plan_from_url, research, scout, draft) instead.
LinkedIn Post Preparation Script (legacy). Runs workflow (planner through strategist) then EXITS. Writes outputs and review marker for Cursor orchestration.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import os
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> None:
    topic = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else None
    if not topic:
        print("Error: No topic provided")
        sys.exit(1)

    from main import output_dir_for_topic
    from graph.workflow import get_compiled_graph_prepare

    thread_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_compiled_graph_prepare()
    initial = {"raw_input": topic, "logs": []}

    result = graph.invoke(initial, config=config)

    output_dir = output_dir_for_topic(topic)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "research.md").write_text(
        result.get("research_summary") or "", encoding="utf-8"
    )
    (output_dir / "plan.md").write_text(
        result.get("plan") or "", encoding="utf-8"
    )
    (output_dir / "draft_final.md").write_text(
        result.get("post_draft") or "", encoding="utf-8"
    )
    (output_dir / "engagement.json").write_text(
        json.dumps(
            {
                "scout_targets": result.get("scout_targets", []),
                "comments_list": result.get("comments_list", []),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    state_for_save = {
        k: v
        for k, v in result.items()
        if k not in ("logs", "__interrupt__")
    }
    (output_dir / "session_state.json").write_text(
        json.dumps(state_for_save, indent=2, default=str), encoding="utf-8"
    )

    marker = {
        "status": "ready_for_review",
        "session_id": output_dir.name,
        "output_dir": str(output_dir),
        "thread_id": thread_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    temp_dir = ROOT / "temporary"
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "review_ready.json").write_text(
        json.dumps(marker, indent=2), encoding="utf-8"
    )

    print(f"Draft completed. Outputs saved to {output_dir}")
    print("Review marker written to temporary/review_ready.json")
    sys.exit(0)


if __name__ == "__main__":
    main()
