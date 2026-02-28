"""
LinkedIn Scout: Golden Hour target discovery and 6 pre-engagement comments.
Uses search_linkedin_topic and browser; reads outputs/**/engagement.json to avoid repeats; drafts comments from voice.
"""

import json
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"
OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"


def run(state: LinkedInContext) -> dict:
    """
    Discover 5-6 scout targets (name, url, post_url, rationale) and draft 6 comments.
    Returns state update with scout_targets and comments_list.
    """
    raw_input = state.get("raw_input") or ""
    research_summary = state.get("research_summary") or ""
    pillar = state.get("pillar") or "pillar_1"

    voice_path = KNOWLEDGE / "voice_profile.md"
    voice = (
        voice_path.read_text(encoding="utf-8")
        if voice_path.exists()
        else "First-person, direct, substantive."
    )

    # Avoid recent engagement targets (read all engagement.json in outputs)
    recent_urls = set()
    if OUTPUTS.exists():
        for p in OUTPUTS.rglob("engagement.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for t in data.get("targets", []) or data.get("scout_targets", []):
                    u = t.get("url") or t.get("post_url")
                    if u:
                        recent_urls.add(u)
            except Exception:
                pass

    from tools.search import search_linkedin_topic

    query = f"NZ GP practice manager primary care {raw_input}"
    results = search_linkedin_topic(query)
    # Filter to avoid recent
    candidates = [r for r in results if r.get("url") and r["url"] not in recent_urls][
        :10
    ]
    scout_targets = []
    for r in candidates[:6]:
        scout_targets.append(
            {
                "name": r.get("title", "LinkedIn")[:80],
                "url": r.get("url", ""),
                "post_url": r.get("url", ""),
                "rationale": r.get("snippet", "")[:200],
            }
        )

    if len(scout_targets) < 5 and results:
        for r in results:
            if r.get("url") and not any(t["url"] == r["url"] for t in scout_targets):
                scout_targets.append(
                    {
                        "name": r.get("title", "LinkedIn")[:80],
                        "url": r.get("url", ""),
                        "post_url": r.get("url", ""),
                        "rationale": r.get("snippet", "")[:200],
                    }
                )
                if len(scout_targets) >= 6:
                    break

    # Draft 6 comments in Dr Ryo's voice (2-3 sentences, substantive)
    from agents._llm import invoke

    system = f"""You are drafting 6 short LinkedIn comments for Golden Hour pre-engagement. Voice: {voice[:2000]}
Rules: 2-3 sentences each; substantive; reference a specific point from the target; no generic praise. Output exactly 6 lines, one comment per line. No numbering or bullets."""
    user = f"Topic: {raw_input}. Research context: {research_summary[:1500]}. Targets (use their rationale to tailor): {json.dumps([t.get('rationale','') for t in scout_targets[:6]])}"
    out = invoke("scout", system, user)
    lines = [ln.strip() for ln in out.strip().split("\n") if ln.strip()][:6]
    while len(lines) < 6:
        lines.append("Agree; this is an important point for NZ primary care.")
    comments_list = lines[:6]

    return {"scout_targets": scout_targets, "comments_list": comments_list}
