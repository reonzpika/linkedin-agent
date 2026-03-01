"""
Output quality tests: engagement bait, ALEX framing, Scout structure, Strategist guardrail.
Run from repo root: python tests/test_quality.py
Or via scripts/run_tests.py (Phase 5b).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Banned engagement-bait phrases (must match Strategist and algorithm_sop / voice_profile)
ENGAGEMENT_BAIT_PHRASES = [
    "what do you think",
    "what's your experience",
    "share your experience",
    "how's your experience",
    "your experience?",
    "your thoughts?",
    "let me know what you think",
    "curious what you think",
    "would love to hear your thoughts",
]


def _has_engagement_bait(text: str) -> list[str]:
    t = (text or "").lower()
    return [p for p in ENGAGEMENT_BAIT_PHRASES if p.lower() in t]


def assert_no_engagement_bait(first_comment: str, comments_list: list) -> None:
    """Raise AssertionError if first_comment or any comment contains engagement bait."""
    bait = _has_engagement_bait(first_comment)
    if bait:
        raise AssertionError(f"first_comment contains engagement bait: {bait}")
    for i, c in enumerate(comments_list or []):
        bait = _has_engagement_bait(c)
        if bait:
            raise AssertionError(f"comments_list[{i}] contains engagement bait: {bait}")


def assert_alex_not_crashes(post_draft: str) -> None:
    """Raise if post_draft implies ALEX crashes during consultations (simple heuristic)."""
    draft = (post_draft or "").lower()
    # Avoid "ALEX crash" / "ALEX crashing" / "ALEX crashes" type phrasing
    if "alex" in draft and ("crash" in draft or "crashes" in draft or "crashing" in draft):
        raise AssertionError(
            "post_draft implies ALEX crashing; ALEX is an API platform, not a clinical UI"
        )


def assert_scout_targets_structure(
    scout_targets: list, comments_list: list, require_post_url: bool = True
) -> None:
    """Each target must have name, url, post_url, rationale; post_url non-empty when url set; lengths align."""
    for i, t in enumerate(scout_targets or []):
        if not isinstance(t, dict):
            raise AssertionError(f"scout_targets[{i}] is not a dict")
        for key in ("name", "url", "post_url", "rationale"):
            if key not in t:
                raise AssertionError(f"scout_targets[{i}] missing key: {key}")
        url = t.get("url") or ""
        post_url = t.get("post_url") or ""
        if require_post_url and url and not post_url:
            raise AssertionError(f"scout_targets[{i}] has url but empty post_url")
        if post_url is None:
            raise AssertionError(f"scout_targets[{i}] post_url must be set (use url if same)")
    clen = len(comments_list or [])
    tlen = len(scout_targets or [])
    if tlen > 0 and clen < tlen:
        raise AssertionError(
            f"comments_list length {clen} < scout_targets length {tlen}; comments map by index to targets"
        )


def test_strategist_rejects_engagement_bait() -> None:
    """Strategist must not approve when first_comment contains engagement bait."""
    from graph.state import LinkedInContext
    from agents.strategist import run as strategist_run

    state: LinkedInContext = {
        "post_draft": "A" * 200,  # valid length
        "hashtags": ["#NewZealandGP", "#PrimaryHealthCare", "#MedtechNZ"],
        "first_comment": "Great post. What's your experience?",
        "comments_list": ["Substantive comment one.", "Another substantive point."],
        "revision_count": 0,
    }
    result = strategist_run(state)
    approved = result.get("strategist_approved", False)
    instructions = result.get("strategist_revision_instructions", "")
    assert not approved or "engagement bait" in instructions.lower() or "experience" in instructions.lower(), (
        f"Strategist should reject or request revision for engagement bait; got approved={approved}, instructions={instructions!r}"
    )
    print("Strategist rejects engagement bait in first_comment: PASS")


def run_quality_assertions_on_state(state: dict) -> None:
    """Run engagement-bait and ALEX framing checks on state (e.g. after Architect or at interrupt)."""
    first_comment = state.get("first_comment") or ""
    comments_list = state.get("comments_list") or []
    post_draft = state.get("post_draft") or ""
    scout_targets = state.get("scout_targets") or []

    assert_no_engagement_bait(first_comment, comments_list)
    if "alex" in (state.get("raw_input") or "").lower() or "medtech" in (state.get("raw_input") or "").lower():
        assert_alex_not_crashes(post_draft)
    if scout_targets:
        assert_scout_targets_structure(scout_targets, comments_list)
    print("Quality assertions (engagement bait, ALEX framing, Scout structure): PASS")


if __name__ == "__main__":
    print("=== Quality tests ===")
    test_strategist_rejects_engagement_bait()
    # Run quality assertions on mock state
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_agents", ROOT / "tests" / "test_agents.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mock_state = {**mod.BASE_STATE, "scout_targets": mod.MOCK_SCOUT_TARGETS}
    mock_state["first_comment"] = "Link to follow."
    mock_state["comments_list"] = ["Substantive.", "Another point."] * 3
    mock_state["post_draft"] = "Medtech's ALEX Intelligence Layer is an API platform. " * 20
    run_quality_assertions_on_state(mock_state)
    print("\n=== Quality tests: PASS ===")
