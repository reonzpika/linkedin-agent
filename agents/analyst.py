"""
LinkedIn Performance Analyst: Scores post performance against benchmarks,
identifies what drove or killed reach, and proposes specific, testable updates
to knowledge files (knowledge updates) or system behaviour (system updates).
Called by scripts/analyse_performance.py.
"""

import json
import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"

CURSOR_SYSTEM_UPDATE_INSTRUCTION = (
    "Before planning implementation of this system update, read the following files in order "
    "and reason about which layer of the system is the best place to make this change: "
    "1. AGENTS.md (system architecture and entry points) "
    "2. .cursor/skills/ (all skill files — what workflows already exist) "
    "3. agents/ (what agents already exist and what they can do) "
    "4. The specific file(s) named in read_before_planning. "
    "Only after reading all of those should you produce an implementation plan. "
    "Your plan must explicitly state which layer you chose and why you ruled out the others. "
    "Present the plan in chat and wait for approval before touching any files."
)


def run(state: LinkedInContext) -> dict:
    """
    Analyse post performance. Returns state update with:
    - performance_score: dict (overall + per-dimension scores)
    - performance_insights: str (markdown analysis)
    - proposed_updates: list of knowledge or system update dicts
    """
    analytics = state.get("analytics") or {}
    post_draft = state.get("post_draft") or ""
    first_comment = state.get("first_comment") or ""
    comments_list = state.get("comments_list") or []
    scout_targets = state.get("scout_targets") or []
    pillar = state.get("pillar") or "pillar_1"
    raw_input = state.get("raw_input") or ""
    history = state.get("performance_history") or ""

    voice_path = KNOWLEDGE / "voice_profile.md"
    algo_path = KNOWLEDGE / "algorithm_sop.md"
    strategy_path = KNOWLEDGE / "clinicpro_strategy.md"

    voice = voice_path.read_text(encoding="utf-8") if voice_path.exists() else ""
    algo = algo_path.read_text(encoding="utf-8") if algo_path.exists() else ""
    strategy = strategy_path.read_text(encoding="utf-8") if strategy_path.exists() else ""

    from agents._llm import invoke

    system = f"""You are the LinkedIn Performance Analyst for Dr Ryo Eguchi's ClinicPro account.
Your job is to score a post's performance, explain what worked and what did not, and propose
specific, testable updates — either to knowledge files (knowledge updates) or to system
behaviour (system updates).

Voice rules (abridged): {voice[:2000]}
Algorithm rules (abridged): {algo[:2000]}
Strategy (abridged): {strategy[:2000]}

## Benchmarks for a small NZ primary care personal profile (100-300 connections)

Important context: small accounts have structurally higher engagement rates (8-12% by
impressions) than large accounts. Do not penalise normal small-account numbers.
Dwell time and saves are the strongest algorithmic signals — weight them accordingly.
Comments of 15+ words carry roughly 2x the algorithmic weight of short comments.
Saves carry roughly 5x the weight of a like. Sends signal strong relevance.
Hashtags have zero effect on reach since October 2024 — do not reference them.

| Metric           | Poor   | Acceptable | Good     | Excellent |
|------------------|--------|------------|----------|-----------|
| Impressions (48h)| <50    | 50-200     | 200-500  | 500+      |
| Reactions        | 0-2    | 3-6        | 7-15     | 16+       |
| Comments         | 0      | 1-2        | 3-5      | 6+        |
| Reposts          | 0      | 1          | 2-3      | 4+        |
| Saves            | 0      | 1          | 2-4      | 5+        |
| Sends            | 0      | 1          | 2-3      | 4+        |
| Profile views    | 0-1    | 2-4        | 5-10     | 11+       |
| Followers gained | 0      | 1          | 2-3      | 4+        |
| GH replies (of 6)| 0      | 1-2        | 3-4      | 5-6       |

## Engagement signal weights (for overall score reasoning)
- Saves: 5x a reaction
- Sends: 3x a reaction
- Substantive comments (15+ words): 2x a short comment
- Reactions: baseline
- Reposts: 4x a reaction
- Impressions: context signal only, not engagement

## Output format

Respond with a single JSON object (no markdown fence) with exactly these keys:

{{
  "performance_score": {{
    "overall": "poor|acceptable|good|excellent",
    "impressions": "poor|acceptable|good|excellent",
    "engagement": "poor|acceptable|good|excellent",
    "golden_hour": "poor|acceptable|good|excellent",
    "audience_quality": "poor|acceptable|good|excellent"
  }},
  "what_worked": ["short bullet", "short bullet"],
  "what_failed": ["short bullet", "short bullet"],
  "performance_insights": "2-3 paragraph markdown analysis. Name the specific post element (hook, structure, topic, golden hour comments) that drove or killed reach. Reference actual post content. Do not mention hashtags.",
  "proposed_updates": []
}}

## Rules for proposed_updates

Total cap: maximum 5 updates per analysis (maximum 2 may be system updates).
Only propose updates when performance was poor or excellent (not acceptable or good).
If no updates are warranted, return an empty array.
Each update must be specific and testable, not vague advice.

### Knowledge update (for rule changes in markdown knowledge files)

Only update voice_profile.md or algorithm_sop.md.
Never propose changes to clinicpro_strategy.md — that requires Dr Ryo's direct decision.
Never propose changes to performance_history.md — it is auto-updated by the script.

Knowledge update structure:
{{
  "type": "knowledge",
  "number": 1,
  "file": "knowledge/voice_profile.md",
  "section": "Structural Rules",
  "current_rule": "exact quoted text of current rule, or empty string if new",
  "proposed_rule": "exact replacement text",
  "rationale": "one sentence linking this post's data to the proposed change",
  "confidence": "observed once — may be coincidence | observed in N of M reviews"
}}

### System update (for behaviour changes to scripts, agents, or skill files)

Only raise a system update when:
- The SAME gap appears across at least 2 reviews in performance history, OR
- A single review shows a COMPLETE failure of a specific mechanism
  (e.g. zero replies from all 6 Golden Hour targets, sends returning null across reviews)

Do not raise system updates on single-post anomalies — that is noise.

System update structure:
{{
  "type": "system",
  "number": 2,
  "file": "scripts/scout.py",
  "what": "Plain English description of what needs to change in this file or component",
  "why": "What the data showed across reviews that identified this as a gap",
  "outcome": "Behaviour description of the successful result — no code, no implementation detail",
  "confidence": "observed in N of M reviews | single review — complete mechanism failure",
  "scope": "affects this post type only | affects all future posts | affects the review system itself",
  "reversibility": "easy — parameter change | medium — logic change | hard — schema change",
  "dependencies": "Other files likely affected by this change, even if you are unsure how",
  "verification": "How Dr Ryo will know the change worked after the next review",
  "read_before_planning": [
    "AGENTS.md",
    ".cursor/skills/linkedin-post-review",
    "agents/analyst.py",
    "scripts/scout.py"
  ],
  "cursor_instruction": "{CURSOR_SYSTEM_UPDATE_INSTRUCTION}"
}}
"""

    golden_hour_data = []
    for i, target in enumerate(scout_targets[:6]):
        comment = comments_list[i] if i < len(comments_list) else ""
        gh_entry = analytics.get("golden_hour_replies", {}).get(str(i), False)
        if isinstance(gh_entry, dict):
            reply_received = gh_entry.get("replies", 0) > 0
            gh_impressions = gh_entry.get("impressions", 0)
            gh_likes = gh_entry.get("likes", 0)
        else:
            # Backward compatible with old bool format
            reply_received = bool(gh_entry)
            gh_impressions = 0
            gh_likes = 0
        golden_hour_data.append({
            "target_name": target.get("name", ""),
            "target_snippet": (target.get("snippet") or "")[:200],
            "our_comment": comment,
            "reply_received": reply_received,
            "comment_impressions": gh_impressions,
            "comment_likes": gh_likes,
        })

    user = f"""Topic: {raw_input}
Pillar: {pillar}

POST (first 500 chars):
{post_draft[:500]}

FIRST COMMENT:
{first_comment[:200]}

ANALYTICS (48 hours after posting):
{json.dumps(analytics, indent=2)}

GOLDEN HOUR COMMENT PERFORMANCE:
{json.dumps(golden_hour_data, indent=2)}

RECENT PERFORMANCE HISTORY (for pattern detection — use this to determine whether
a gap is recurring across multiple reviews before raising a system update):
{history[:3000]}
"""

    out = invoke("analyst", system, user)

    try:
        json_match = re.search(r"\{[\s\S]*\}", out)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            result = {}
    except (json.JSONDecodeError, ValueError):
        result = {}

    return {
        "performance_score": result.get("performance_score", {}),
        "what_worked": result.get("what_worked", []),
        "what_failed": result.get("what_failed", []),
        "performance_insights": result.get("performance_insights", out[:3000]),
        "proposed_updates": result.get("proposed_updates", []),
    }
