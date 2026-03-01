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
    engagement_bait_phrases = [
        "what do you think",
        "what's your experience",
        "what’s your experience",
        "share your experience",
        "how's your experience",
        "your experience?",
        "your thoughts?",
        "let me know what you think",
        "curious what you think",
        "would love to hear your thoughts",
    ]
    word_count = len(post_draft.split())
    link_in_body = "http" in post_draft or "www." in post_draft
    hashtag_ok = 3 <= len(hashtags) <= 4
    ends_question = post_draft.strip().endswith("?")
    banned_found = [b for b in banned if b.lower() in post_draft.lower()]

    def has_engagement_bait(text: str) -> list[str]:
        t = (text or "").lower()
        return [p for p in engagement_bait_phrases if p.lower() in t]

    first_comment = state.get("first_comment") or ""
    comments_list = state.get("comments_list") or []
    bait_in_first = has_engagement_bait(first_comment)
    bait_in_comments = []
    for i, c in enumerate(comments_list):
        found = has_engagement_bait(c)
        if found:
            bait_in_comments.append(f"comment {i+1}: {found}")

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
    if bait_in_first:
        failures.append(f"Engagement bait in first_comment: {bait_in_first}")
    if bait_in_comments:
        failures.append("Engagement bait in comments_list: " + "; ".join(bait_in_comments))

    scout_targets = state.get("scout_targets") or []
    if scout_targets and len(comments_list) != len(scout_targets):
        failures.append(
            f"Comment count mismatch: {len(comments_list)} comments for {len(scout_targets)} targets"
        )

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
