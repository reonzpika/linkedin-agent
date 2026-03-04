"""
DEPRECATED: Use chat and the linkedin-post-create skill instead. This entry point is kept for reference or local testing only.
LinkedIn Engine entry point (legacy). Load env, compile graph, run workflow. On interrupt: show draft, accept edits, resume. Save outputs with collision-safe folder names.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Repo root
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def slugify(text: str, max_length: int = 30) -> str:
    """Lowercase, hyphenated, alphanumeric slug; max 30 chars."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_length] if len(s) > max_length else s


def output_dir_for_topic(topic: str) -> Path:
    """Return outputs/YYYY-MM-DD_<slug> with collision prevention (increment suffix if exists)."""
    date = datetime.utcnow().strftime("%Y-%m-%d")
    base_slug = slugify(topic or "run")
    base_name = f"{date}_{base_slug}"
    out_root = ROOT / "outputs"
    out_root.mkdir(parents=True, exist_ok=True)
    path = out_root / base_name
    if not path.exists():
        return path
    n = 2
    while (out_root / f"{base_name}-{n}").exists():
        n += 1
    return out_root / f"{base_name}-{n}"


def main() -> None:
    raw_input = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else None
    if not raw_input:
        raw_input = input("Enter topic or URL: ").strip()
    if not raw_input:
        logger.error("No topic or URL provided")
        sys.exit(1)

    logger.info(
        "Let's first understand the problem, extract relevant variables and their corresponding numerals, and make a plan."
    )
    from graph.workflow import get_compiled_graph
    from langgraph.types import Command

    graph = get_compiled_graph()
    thread_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    config = {"configurable": {"thread_id": thread_id}}
    initial = {"raw_input": raw_input, "logs": []}

    result = graph.invoke(initial, config=config)

    while result.get("__interrupt__"):
        interrupt_value = result["__interrupt__"]
        if isinstance(interrupt_value, list) and interrupt_value:
            val = interrupt_value[0]
            if hasattr(val, "value"):
                val = val.value
            else:
                val = interrupt_value[0]
        else:
            val = interrupt_value
        # Write outputs on first interrupt so aborting at review still leaves folder populated (for test suite Phase 7)
        out_dir = output_dir_for_topic(raw_input)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "research.md").write_text(
            result.get("research_summary") or "", encoding="utf-8"
        )
        (out_dir / "plan.md").write_text(result.get("plan") or "", encoding="utf-8")
        (out_dir / "draft_final.md").write_text(
            result.get("post_draft") or "", encoding="utf-8"
        )
        (out_dir / "engagement.json").write_text(
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
            k: v for k, v in result.items() if k not in ("logs", "__interrupt__")
        }
        (out_dir / "session_state.json").write_text(
            json.dumps(state_for_save, indent=2, default=str), encoding="utf-8"
        )
        logger.info("Review required:\n{}", val)
        user_input = input(
            "Type APPROVE to proceed, or paste edits (post_draft / comments_list / first_comment): "
        ).strip()
        if user_input.upper() == "APPROVE":
            resume_value = True
        else:
            try:
                resume_value = (
                    json.loads(user_input)
                    if user_input.strip().startswith("{")
                    else user_input
                )
            except Exception:
                resume_value = user_input
        result = graph.invoke(Command(resume=resume_value), config=config)

    out_dir = output_dir_for_topic(raw_input)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "research.md").write_text(
        result.get("research_summary") or "", encoding="utf-8"
    )
    (out_dir / "plan.md").write_text(result.get("plan") or "", encoding="utf-8")
    (out_dir / "draft_final.md").write_text(
        result.get("post_draft") or "", encoding="utf-8"
    )
    (out_dir / "engagement.json").write_text(
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
        k: v for k, v in result.items() if k not in ("logs", "__interrupt__")
    }
    (out_dir / "session_state.json").write_text(
        json.dumps(state_for_save, indent=2, default=str), encoding="utf-8"
    )
    logger.info("Outputs saved to {}", out_dir)


if __name__ == "__main__":
    main()
