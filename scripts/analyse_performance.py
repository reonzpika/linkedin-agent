"""
Performance analysis script for LinkedIn post review workflow.
Reads analytics.json, draft_final.md, engagement.json, and performance_history.md
from the session folder; runs the Analyst agent; writes:
  - performance_report.md   (human-readable analysis for Cursor chat display)
  - proposed_updates.json   (knowledge and system updates pending approval)

Run from repo root:
  python scripts/analyse_performance.py --session-dir outputs/<session_id>

Updates knowledge/performance_history.md automatically (no approval needed).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

KNOWLEDGE = ROOT / "knowledge"


def _score_label(score: str) -> str:
    return {
        "poor": "❌ Poor",
        "acceptable": "⚠️ Acceptable",
        "good": "✅ Good",
        "excellent": "🌟 Excellent",
    }.get((score or "").lower(), score or "unknown")


def build_performance_report(
    session_id: str,
    analytics: dict,
    score: dict,
    what_worked: list,
    what_failed: list,
    insights: str,
    proposed_updates: list,
    post_draft: str,
    pillar: str,
) -> str:
    """Build markdown performance report for Cursor chat display."""
    scraped_at = analytics.get("scraped_at", "unknown")
    post_url = analytics.get("post_url", "unknown")

    lines = [
        f"# Performance Report: {session_id}",
        f"**Post URL:** {post_url}",
        f"**Analysed at:** {scraped_at}",
        f"**Pillar:** {pillar}",
        "",
        "## Scores",
        "| Dimension | Score |",
        "|---|---|",
        f"| Overall | {_score_label(score.get('overall', ''))} |",
        f"| Impressions | {_score_label(score.get('impressions', ''))} |",
        f"| Engagement | {_score_label(score.get('engagement', ''))} |",
        f"| Golden Hour | {_score_label(score.get('golden_hour', ''))} |",
        f"| Audience Quality | {_score_label(score.get('audience_quality', ''))} |",
        "",
        "## Raw Metrics (48 hours)",
        "| Metric | Value |",
        "|---|---|",
        f"| Impressions | {analytics.get('impressions', 0)} |",
        f"| Reactions | {analytics.get('reactions', 0)} |",
        f"| Comments | {analytics.get('comments', 0)} |",
        f"| Reposts | {analytics.get('reposts', 0)} |",
        f"| Saves | {analytics.get('saves', 0)} |",
        f"| Sends | {analytics.get('sends', 0)} |",
        f"| Profile views from post | {analytics.get('profile_views_from_post', 0)} |",
        f"| Followers gained | {analytics.get('followers_gained', 0)} |",
    ]

    replies = analytics.get("golden_hour_replies", {})
    reply_count = sum(
        1 for v in replies.values()
        if (isinstance(v, dict) and v.get("replies", 0) > 0) or (isinstance(v, bool) and v)
    )
    gh_impressions = sum(v.get("impressions", 0) for v in replies.values() if isinstance(v, dict))
    gh_likes = sum(v.get("likes", 0) for v in replies.values() if isinstance(v, dict))
    lines.append(f"| Golden Hour replies received | {reply_count}/6 |")
    lines.append(f"| Golden Hour comment impressions | {gh_impressions} |")
    lines.append(f"| Golden Hour comment likes | {gh_likes} |")

    if analytics.get("selector_stale"):
        lines += [
            "",
            "> ⚠️ **Selector warning:** all metrics returned zero. LinkedIn's frontend "
            "may have changed. Verify manually and consider raising a system update.",
        ]

    lines += ["", "## What Worked"]
    for item in (what_worked or ["Nothing identified"]):
        lines.append(f"- {item}")

    lines += ["", "## What Failed"]
    for item in (what_failed or ["Nothing identified"]):
        lines.append(f"- {item}")

    lines += ["", "## Analysis", insights or "No analysis available.", ""]

    # Split proposed updates into knowledge and system for display
    knowledge_updates = [u for u in proposed_updates if u.get("type") == "knowledge"]
    system_updates = [u for u in proposed_updates if u.get("type") == "system"]

    if not proposed_updates:
        lines += ["## Proposed Updates", "No updates proposed for this post.", ""]
    else:
        lines += [
            "## Proposed Updates",
            f"**{len(proposed_updates)} update(s) proposed.** "
            "Type `APPROVE ALL`, `REJECT ALL`, or list numbers to approve selectively.",
            "",
        ]

        if knowledge_updates:
            lines += ["### Knowledge Updates", ""]
            for update in knowledge_updates:
                n = update.get("number", "?")
                lines += [
                    f"**Update {n} — `{update.get('file', 'unknown')}`** "
                    f"(section: {update.get('section', 'unknown')})",
                    f"Rationale: {update.get('rationale', '')}",
                    f"Confidence: {update.get('confidence', '')}",
                    "",
                    "Current rule:",
                    f"> {update.get('current_rule', '(new rule)')}",
                    "",
                    "Proposed rule:",
                    f"> {update.get('proposed_rule', '')}",
                    "",
                ]

        if system_updates:
            lines += [
                "### System Updates",
                "> These require Cursor agent mode. Cursor will read the system map "
                "and present an implementation plan for your approval before touching any files.",
                "",
            ]
            for update in system_updates:
                n = update.get("number", "?")
                lines += [
                    f"**Update {n} — `{update.get('file', 'unknown')}`**",
                    f"What: {update.get('what', '')}",
                    f"Why: {update.get('why', '')}",
                    f"Outcome: {update.get('outcome', '')}",
                    f"Confidence: {update.get('confidence', '')}",
                    f"Scope: {update.get('scope', '')}",
                    f"Reversibility: {update.get('reversibility', '')}",
                    f"Dependencies: {update.get('dependencies', 'none identified')}",
                    f"Verification: {update.get('verification', '')}",
                    "",
                ]

    lines += [
        "---",
        f"*Generated by linkedin-post-review at "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')} NZST*",
    ]

    return "\n".join(lines)


def update_performance_history(
    session_id: str,
    analytics: dict,
    score: dict,
    pillar: str,
    post_draft: str,
    proposed_updates: list,
) -> None:
    """
    Append this post's summary to knowledge/performance_history.md.
    Includes system_updates_flagged list.
    Also maintains the Open System Updates section at the top of the file.
    """
    history_file = KNOWLEDGE / "performance_history.md"

    # Initialise file if it does not exist
    if not history_file.exists():
        history_file.write_text(
            "# Performance History\n\n"
            "Running log of post performance. Updated automatically after each review "
            "by `scripts/analyse_performance.py`.\n"
            "Used by the Analyst agent to detect patterns across posts.\n\n"
            "---\n\n"
            "## Open System Updates\n\n"
            "System updates flagged but not yet confirmed implemented.\n\n"
            "| # | Session | File | What | Status |\n"
            "|---|---|---|---|---|\n\n"
            "---\n\n"
            "## Implemented System Updates\n\n"
            "| # | Flagged in | Implemented in | File | What |\n"
            "|---|---|---|---|---|\n\n"
            "---\n\n"
            "<!-- New post entries are inserted below this line -->\n\n",
            encoding="utf-8",
        )

    hook = post_draft.split("\n")[0][:100] if post_draft else "(unknown)"
    system_updates = [u for u in (proposed_updates or []) if u.get("type") == "system"]
    system_update_numbers = [str(u.get("number", "?")) for u in system_updates]

    gh_replies = analytics.get("golden_hour_replies", {})
    reply_count = sum(
        1 for v in gh_replies.values()
        if (isinstance(v, dict) and v.get("replies", 0) > 0) or (isinstance(v, bool) and v)
    )
    gh_impressions = sum(v.get("impressions", 0) for v in gh_replies.values() if isinstance(v, dict))
    gh_likes = sum(v.get("likes", 0) for v in gh_replies.values() if isinstance(v, dict))

    entry_lines = [
        f"## {session_id}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
        f"**Pillar:** {pillar}",
        f"**Overall score:** {score.get('overall', 'unknown')}",
        f"**Hook:** {hook}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Impressions | {analytics.get('impressions', 0)} |",
        f"| Reactions | {analytics.get('reactions', 0)} |",
        f"| Comments | {analytics.get('comments', 0)} |",
        f"| Reposts | {analytics.get('reposts', 0)} |",
        f"| Saves | {analytics.get('saves', 0)} |",
        f"| Sends | {analytics.get('sends', 0)} |",
        f"| Profile views | {analytics.get('profile_views_from_post', 0)} |",
        f"| Followers gained | {analytics.get('followers_gained', 0)} |",
        f"| GH replies | {reply_count}/6 |",
        f"| GH comment impressions | {gh_impressions} |",
        f"| GH comment likes | {gh_likes} |",
        "",
        f"**System updates flagged:** "
        f"{', '.join(system_update_numbers) if system_update_numbers else 'none'}",
        "",
        "---",
        "",
    ]

    existing = history_file.read_text(encoding="utf-8")
    insert_marker = "<!-- New post entries are inserted below this line -->\n\n"

    if insert_marker in existing:
        pos = existing.index(insert_marker) + len(insert_marker)
        new_content = (
            existing[:pos]
            + "\n".join(entry_lines)
            + "\n"
            + existing[pos:]
        )
    else:
        new_content = existing + "\n" + "\n".join(entry_lines) + "\n"

    # If there are new system updates, append them to the Open System Updates table
    if system_updates:
        for u in system_updates:
            new_row = (
                f"| {u.get('number', '?')} "
                f"| {session_id} "
                f"| `{u.get('file', 'unknown')}` "
                f"| {u.get('what', '')[:80]} "
                f"| Open |\n"
            )
            # Insert before the second --- (after the Open System Updates table)
            open_table_marker = "| # | Session | File | What | Status |\n|---|---|---|---|---|\n"
            if open_table_marker in new_content:
                pos = new_content.index(open_table_marker) + len(open_table_marker)
                new_content = new_content[:pos] + new_row + new_content[pos:]

    history_file.write_text(new_content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyse LinkedIn post performance and propose knowledge and system updates."
    )
    parser.add_argument(
        "--session-dir",
        type=str,
        required=True,
        help="Path to session folder (e.g. outputs/2026-03-05_topic)",
    )
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    analytics_file = session_dir / "analytics.json"
    draft_file = session_dir / "draft_final.md"
    engagement_file = session_dir / "engagement.json"
    plan_file = session_dir / "plan.json"
    input_file = session_dir / "input.json"

    if not analytics_file.exists():
        print(
            "Error: analytics.json not found. Run scripts/collect_analytics.py first.",
            file=sys.stderr,
        )
        return 1
    if not draft_file.exists():
        print("Error: draft_final.md not found.", file=sys.stderr)
        return 1

    analytics = json.loads(analytics_file.read_text(encoding="utf-8"))
    post_draft = draft_file.read_text(encoding="utf-8")

    scout_targets = []
    comments_list = []
    if engagement_file.exists():
        engagement = json.loads(engagement_file.read_text(encoding="utf-8"))
        scout_targets = engagement.get("scout_targets") or []
        comments_list = engagement.get("comments_list") or []

    pillar = "pillar_1"
    if plan_file.exists():
        plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
        pillar = plan_data.get("pillar") or "pillar_1"

    raw_input = ""
    if input_file.exists():
        input_data = json.loads(input_file.read_text(encoding="utf-8"))
        raw_input = (input_data.get("topic") or input_data.get("url") or "").strip()

    history = ""
    history_file = KNOWLEDGE / "performance_history.md"
    if history_file.exists():
        history = history_file.read_text(encoding="utf-8")[:4000]

    state = {
        "analytics": analytics,
        "post_draft": post_draft,
        "comments_list": comments_list,
        "scout_targets": scout_targets,
        "pillar": pillar,
        "raw_input": raw_input,
        "performance_history": history,
    }

    from agents.analyst import run as analyst_run

    result = analyst_run(state)

    performance_score = result.get("performance_score") or {}
    what_worked = result.get("what_worked") or []
    what_failed = result.get("what_failed") or []
    insights = result.get("performance_insights") or ""
    proposed_updates = result.get("proposed_updates") or []

    session_id = session_dir.name

    report = build_performance_report(
        session_id=session_id,
        analytics=analytics,
        score=performance_score,
        what_worked=what_worked,
        what_failed=what_failed,
        insights=insights,
        proposed_updates=proposed_updates,
        post_draft=post_draft,
        pillar=pillar,
    )

    (session_dir / "performance_report.md").write_text(report, encoding="utf-8")
    (session_dir / "proposed_updates.json").write_text(
        json.dumps(proposed_updates, indent=2), encoding="utf-8"
    )

    # Always update performance history (no approval needed)
    update_performance_history(
        session_id, analytics, performance_score, pillar, post_draft, proposed_updates
    )

    knowledge_count = sum(1 for u in proposed_updates if u.get("type") == "knowledge")
    system_count = sum(1 for u in proposed_updates if u.get("type") == "system")

    print(f"Wrote performance_report.md and proposed_updates.json to {session_dir}")
    print(f"Updated knowledge/performance_history.md")
    print(f"Overall score: {performance_score.get('overall', 'unknown')}")
    print(f"Proposed updates: {len(proposed_updates)} "
          f"({knowledge_count} knowledge, {system_count} system)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
