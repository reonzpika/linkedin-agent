"""
Content Architect: Insider GP voice; drafts main post, first_comment, 3-4 hashtags, and 6 Golden Hour comments.
"""

import json
import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


def run(state: LinkedInContext) -> dict:
    """
    Draft main post (hook, systemic point, insider take), first_comment, 3-4 hashtags, 0-2 suggested_mentions, and 6 Golden Hour comments.
    Returns state update with post_draft, first_comment, hashtags, comments_list, suggested_mentions.
    """
    raw_input = state.get("raw_input") or ""
    research_summary = state.get("research_summary") or ""
    pillar = state.get("pillar") or "pillar_1"
    scout_targets = state.get("scout_targets") or []
    source_url = (state.get("source_url") or "").strip()

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
    mention_lib_path = KNOWLEDGE / "mention_library.md"
    mention_lib = (
        mention_lib_path.read_text(encoding="utf-8")
        if mention_lib_path.exists()
        else ""
    )

    from agents._llm import invoke

    system = f"""You are the Content Architect. Draft one LinkedIn post AND 6 Golden Hour engagement comments in the "Insider GP" voice.

Voice and rules: {voice[:2500]}

Algorithm: {algo[:1500]}

Hashtag library (pick 3-4): {hashtag_lib[:1500]}

Mention library (suggest 1-2 relevant mentions when post discusses their work): {mention_lib[:2000]}

MENTION RULES (from algorithm_sop.md):
- Tag 1-3 people or companies maximum per post
- Only tag when legitimately relevant (discussing their work, platform, policy)
- Never tag hoping to generate engagement
- Suggest mentions in the output; do not auto-insert into post body

POST REQUIREMENTS: 150-300 words. Structure: Hook (specific clinical observation) then systemic point (1-2 paragraphs) then insider take (conclusion, not question). No links in body, no banned terms, end with conclusion.

FIRST COMMENT REQUIREMENTS: When a source URL is provided in the user message, first_comment MUST be a short descriptor plus that exact URL (e.g. "Full source: [URL]"). Do not output "[URL to be added]" or any placeholder. When no URL is provided, use a short comment only. Links go in first_comment only; no links in post body. NO engagement-bait questions.

GOLDEN HOUR COMMENTS (6 required): Draft exactly 6 comments for pre-engagement on other LinkedIn posts. Each comment MUST respond to or reference something specific in that target's post (use the snippet for that target). Do not write a generic take on our main post topic; write a reply that engages with what that person actually said.

CRITICAL VOICE REQUIREMENTS for comments:
- LENGTH: 15-25 words MAXIMUM (one substantial sentence, or two short sentences)
- TONE: Simple, everyday English. Dr Ryo is Japanese - write naturally, not formally.
- STRUCTURE: Share practice experience ("We're seeing this too") OR ask genuine question OR state direct observation
- BANNED: "genuine infrastructure achievement", "structural headwinds", "documentation tax", "path of least resistance", any formal policy/academic language
- NEVER use essay rhythm (claim → elaborate → conclude)

Good example: "We hit this exact problem last month. Ended up calling the specialist directly to confirm they got the referral."
Bad example: "The implementation challenge you're describing from those early sites, where clinician buy-in had to be earned consultation by consultation, is exactly why rollout sequencing matters."

Comment order MUST match target order: comment 1 for target 1, comment 2 for target 2, etc. NO generic praise, NO engagement-bait questions.

Medtech/ALEX framing: ALEX is API/integration platform, not clinical UI. Don't describe as "crashing". Acknowledge Medtech progress before naming gaps.

Output format (use exactly this):
<SOLUTION>
post_draft:
[150-300 words]
first_comment:
[Short descriptor + source URL if provided; otherwise short comment. No engagement bait.]
hashtags:
[3-4 hashtags, one per line]
suggested_mentions:
[0-2 LinkedIn handles or company names, one per line, ONLY when post directly discusses their work. Format: @Medtech Global or @Lawrence Peterson. Leave empty if none are relevant.]
</SOLUTION>

<COMMENTS>
[Exactly 6 lines, one comment per line. Line 1 for target 1, line 2 for target 2, etc.]
</COMMENTS>"""

    user = f"""Topic: {raw_input}. Pillar: {pillar}. Research: {research_summary[:2000]}.

Scout targets for Golden Hour engagement (draft a comment for each that references their post):
{json.dumps([{"index": i + 1, "name": t.get("name", ""), "snippet": (t.get("snippet") or t.get("rationale") or "")[:300]} for i, t in enumerate(scout_targets[:6])], indent=2)}"""
    if source_url:
        user += f"\n\nSource URL for first comment (use this exact URL): {source_url}"
    revision_feedback = (state.get("revision_feedback") or "").strip()
    if revision_feedback:
        user += f"\n\nRevision requested:\n{revision_feedback}"
    out = invoke("architect", system, user)

    post_draft = ""
    first_comment = ""
    hashtags = []
    suggested_mentions = []
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
    if match:
        block = match.group(1)
        mentions_match = re.search(
            r"suggested_mentions:\s*(.+?)(?=\n\n|$)", block, re.DOTALL
        )
        if mentions_match:
            suggested_mentions = [
                m.strip()
                for m in mentions_match.group(1).strip().split("\n")
                if m.strip() and (m.strip().startswith("@") or "http" in m.strip())
            ][:2]

    comments_match = re.search(
        r"<COMMENTS>\s*(.*?)\s*</COMMENTS>", out, re.DOTALL
    )
    if comments_match:
        comments_block = comments_match.group(1).strip()
        comments_list = [
            ln.strip()
            for ln in comments_block.split("\n")
            if ln.strip()
        ][:6]
    else:
        comments_list = []
    while len(comments_list) < 6:
        comments_list.append(
            "Interesting perspective. This aligns with what we're seeing in NZ primary care."
        )
    comments_list = comments_list[:6]

    return {
        "post_draft": post_draft,
        "first_comment": first_comment,
        "hashtags": hashtags,
        "comments_list": comments_list,
        "suggested_mentions": suggested_mentions,
    }
