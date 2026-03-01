"""
Content Architect: Insider GP voice; drafts main post and first_comment; 3-4 hashtags; 150-300 words.
"""

import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


def run(state: LinkedInContext) -> dict:
    """
    Draft main post (hook, systemic point, insider take), first_comment, and 3-4 hashtags.
    Returns state update with post_draft, first_comment, hashtags.
    """
    raw_input = state.get("raw_input") or ""
    research_summary = state.get("research_summary") or ""
    pillar = state.get("pillar") or "pillar_1"
    scout_targets = state.get("scout_targets") or []
    comments_list = state.get("comments_list") or []

    voice_path = KNOWLEDGE / "voice_profile.md"
    algo_path = KNOWLEDGE / "algorithm_sop.md"
    hashtag_path = KNOWLEDGE / "hashtag_library.md"
    voice = (
        voice_path.read_text(encoding="utf-8")
        if voice_path.exists()
        else "First-person, direct, no marketing fluff."
    )
    algo = (
        algo_path.read_text(encoding="utf-8")
        if algo_path.exists()
        else "150-300 words; hook then systemic point then take."
    )
    hashtag_lib = (
        hashtag_path.read_text(encoding="utf-8")
        if hashtag_path.exists()
        else "#NewZealandGP #PrimaryHealthCare #MedtechNZ"
    )

    from agents._llm import invoke

    system = f"""You are the Content Architect. Draft one LinkedIn post in the "Insider GP" voice.

Voice and rules: {voice[:2500]}

Algorithm: {algo[:1500]}

Hashtag library (pick 3-4): {hashtag_lib[:1500]}

First comment and engagement bait: first_comment must NOT end with or contain engagement-bait questions (e.g. "what do you think?", "what's your experience?", "share your experience", "how's your experience?"). End with a substantive point or a link placeholder only. The algorithm penalises engagement bait.

Medtech/ALEX framing: When the topic involves Medtech or ALEX Intelligence Layer, describe it accurately. ALEX is an API/integration platform for third-party builders, not a clinical consultation UI. Do NOT describe ALEX as "crashing" during consultations. Acknowledge Medtech's progress (e.g. provider inbox API) before naming any remaining workflow gaps.

Output format (use exactly this):
<SOLUTION>
post_draft:
[150-300 words. Structure: Hook (1-2 sentences, specific clinical observation) then systemic point (1-2 paragraphs) then insider take (1 paragraph, conclusion not question). No links in body. No banned terms.]
first_comment:
[Placeholder for outbound URL or short first comment; links go here only. No engagement-bait questions.]
hashtags:
[3-4 hashtags, one per line]
</SOLUTION>"""

    user = f"Topic: {raw_input}. Pillar: {pillar}. Research: {research_summary[:2000]}."
    out = invoke("architect", system, user)

    post_draft = ""
    first_comment = ""
    hashtags = []
    match = re.search(r"<SOLUTION>\s*(.*?)\s*</SOLUTION>", out, re.DOTALL)
    if match:
        block = match.group(1)
        pd = re.search(r"post_draft:\s*(.+?)(?=first_comment:)", block, re.DOTALL)
        fc = re.search(r"first_comment:\s*(.+?)(?=hashtags:)", block, re.DOTALL)
        ht = re.search(r"hashtags:\s*(.+)", block, re.DOTALL)
        if pd:
            post_draft = pd.group(1).strip()[:4000]
        if fc:
            first_comment = fc.group(1).strip()[:500]
        if ht:
            hashtags = [
                h.strip()
                for h in ht.group(1).strip().split("\n")
                if h.strip() and h.strip().startswith("#")
            ][:4]
    if not post_draft:
        post_draft = out[:3000]
    if not hashtags:
        hashtags = ["#NewZealandGP", "#PrimaryHealthCare", "#MedtechNZ"]
    return {
        "post_draft": post_draft,
        "first_comment": first_comment,
        "hashtags": hashtags,
    }
