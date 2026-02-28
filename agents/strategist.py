"""
Strategist: Critique draft against guardrails; approve or request revision (max 2 loops).
"""

import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


def run(state: LinkedInContext) -> dict:
    """
    Evaluate post_draft against guardrails. If pass: set strategist_approved=True.
    If fail: increment revision_count and return revision instructions (workflow routes back to architect).
    Max 2 revisions; after 2 failures pass to human_review with notes.
    """
    post_draft = state.get("post_draft") or ""
    hashtags = state.get("hashtags") or []
    pillar = state.get("pillar") or "pillar_1"
    revision_count = state.get("revision_count") or 0

    voice_path = KNOWLEDGE / "voice_profile.md"
    voice = voice_path.read_text(encoding="utf-8") if voice_path.exists() else ""

    banned = [
        "innovative",
        "innovation",
        "disruptive",
        "solutions",
        "seamless",
        "game-changer",
        "excited to announce",
        "thrilled",
        "leveraging",
    ]
    word_count = len(post_draft.split())
    link_in_body = "http" in post_draft or "www." in post_draft
    hashtag_ok = 3 <= len(hashtags) <= 4
    ends_question = post_draft.strip().endswith("?")
    banned_found = [b for b in banned if b.lower() in post_draft.lower()]

    failures = []
    if word_count < 150 or word_count > 300:
        failures.append(f"Word count {word_count} (required 150-300)")
    if link_in_body:
        failures.append(
            "Outbound links in post body (links must be in first comment only)"
        )
    if not hashtag_ok:
        failures.append(f"Hashtag count {len(hashtags)} (required 3-4)")
    if banned_found:
        failures.append(f"Banned terms: {banned_found}")
    if ends_question:
        failures.append("Post ends with a question (must end with a take/conclusion)")

    if not failures:
        return {"strategist_approved": True}

    revision_count += 1
    if revision_count >= 2:
        return {
            "revision_count": revision_count,
            "strategist_approved": True,
            "strategist_failure_notes": "; ".join(failures),
        }
    return {
        "revision_count": revision_count,
        "strategist_approved": False,
        "strategist_revision_instructions": "; ".join(failures),
    }
