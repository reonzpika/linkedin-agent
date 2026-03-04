"""
DEPRECATED: Chat-first flow uses session folder files and plain dicts; LinkedInContext kept for type reference and legacy agents.
Shared state schema for the LinkedIn Engine (legacy). LinkedInContext is the single source of truth passed between all nodes.
"""

from typing import Annotated, List, Optional, TypedDict
import operator


class LinkedInContext(TypedDict, total=False):
    """Cognitive kernel passed between all workflow nodes. All data flows through state."""

    # Input
    raw_input: str  # URL or clinical topic provided by human

    # Research phase
    research_summary: str  # Synthesised findings from Researcher agent
    target_urls: List[str]  # URLs grounding the research

    # Discovery phase
    scout_targets: List[dict]  # 5-6 LinkedIn accounts for Golden Hour engagement
    # Each dict: {name, url, post_url, rationale}

    # Drafting phase
    post_draft: str  # Main LinkedIn post (150-300 words)
    comments_list: List[str]  # 6 pre-engagement comments for Golden Hour
    first_comment: str  # Link/URL to go in first post comment

    # Metadata
    pillar: str  # "pillar_1", "pillar_2", or "pillar_3"
    plan: str  # PS+ plan from entry node (for outputs/plan.md)
    hashtags: List[str]  # 3-4 approved hashtags for this post

    # Memory reducers: append-only execution log (never overwrite)
    logs: Annotated[List[str], operator.add]

    # Control flow
    revision_count: int  # Tracks Reflexion loop iterations (max 2)
    strategist_approved: bool  # Set by Strategist when all guardrails pass
    human_approved: bool  # Set to True after HITL interrupt
    error_state: Optional[str]  # Populated on failure for interrupt handover
