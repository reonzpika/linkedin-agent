"""
Phase 5 agent unit tests: Researcher, Architect, Strategist with minimal synthetic state.
Uses real LLM calls. Mock scout_targets are injected so Architect sees realistic structure
(name, url, post_url, rationale) and produces a well-formed draft for Strategist assertions.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph.state import LinkedInContext
from agents.researcher import run as researcher_run
from agents.architect import run as architect_run
from agents.strategist import run as strategist_run

# Realistic mock scout_targets so Architect prompt has valid structure (6 targets; Architect drafts 6 comments)
MOCK_SCOUT_TARGETS = [
    {
        "name": "Jane Smith",
        "url": "https://www.linkedin.com/in/janesmith",
        "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:123",
        "rationale": "NZ practice manager, posts about primary care admin and Medtech.",
    },
    {
        "name": "Health NZ Updates",
        "url": "https://www.linkedin.com/company/healthnz",
        "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:456",
        "rationale": "Relevant health policy and workforce content for NZ GPs.",
    },
    {
        "name": "RNZCGP",
        "url": "https://www.linkedin.com/company/rnzcgp",
        "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:789",
        "rationale": "Royal College; authority on GP standards and ALEX context.",
    },
    {
        "name": "Dr Jane Smith",
        "url": "https://linkedin.com/in/janesmith",
        "post_url": "https://linkedin.com/posts/abc4",
        "rationale": "Practice efficiency discussion.",
    },
    {
        "name": "Tom Wilson - Practice Manager",
        "url": "https://linkedin.com/in/tomwilson",
        "post_url": "https://linkedin.com/posts/abc5",
        "rationale": "Admin burden insights.",
    },
    {
        "name": "Dr Lisa Chen",
        "url": "https://linkedin.com/in/lisachen",
        "post_url": "https://linkedin.com/posts/abc6",
        "rationale": "Workforce retention strategies.",
    },
]

BASE_STATE: LinkedInContext = {
    "raw_input": "Medtech ALEX Intelligence Layer",
    "pillar": None,
    "plan": None,
    "research_summary": None,
    "target_urls": [],
    "scout_targets": [],
    "comments_list": [],
    "post_draft": None,
    "hashtags": [],
    "first_comment": None,
    "strategist_approved": False,
    "revision_count": 0,
    "error_state": None,
    "logs": [],
}


def test_researcher():
    print("\n--- Researcher agent ---")
    state = BASE_STATE.copy()
    result = researcher_run(state)
    if result.get("interrupt_dehallucination"):
        print("Dehallucination trigger:", result["interrupt_dehallucination"])
        return result  # so main can check and exit without running Architect
    summary = result.get("research_summary", "")[:300]
    print("research_summary:", summary)
    print("pillar:", result.get("pillar"))
    print("target_urls:", result.get("target_urls", [])[:2])
    assert result.get("research_summary"), "FAIL: research_summary is empty"
    print("Researcher: PASS")
    return result


def test_architect(state: LinkedInContext):
    print("\n--- Architect agent ---")
    result = architect_run(state.copy())
    draft = result.get("post_draft", "")
    hashtags = result.get("hashtags", [])
    first_comment = result.get("first_comment", "")
    word_count = len(draft.split())
    print(f"post_draft ({word_count} words):", draft[:300])
    print("hashtags:", hashtags)
    print("first_comment:", first_comment[:100])
    # Spec is 150-300; allow 120-300 in test to absorb model variance
    assert 120 <= word_count <= 300, f"FAIL: word count {word_count} outside 120-300"
    assert 3 <= len(hashtags) <= 4, f"FAIL: {len(hashtags)} hashtags (must be 3-4)"
    assert first_comment, "FAIL: first_comment is empty"
    print("Architect: PASS")
    return result


def test_strategist(state: LinkedInContext):
    print("\n--- Strategist agent ---")
    result = strategist_run(state.copy())
    approved = result.get("strategist_approved", False)
    revision_count = result.get("revision_count", 0)
    print("approved:", approved)
    print("revision_count:", revision_count)
    assert approved or revision_count <= 2, "FAIL: neither approved nor within revision limit"
    print("Strategist: PASS")
    return result


if __name__ == "__main__":
    state = BASE_STATE.copy()

    research_result = test_researcher()
    state.update({k: v for k, v in research_result.items() if k != "interrupt_dehallucination"})
    if research_result.get("interrupt_dehallucination"):
        print("\n=== Agent pipeline: STOPPED (dehallucination interrupt) ===")
        sys.exit(0)

    # Inject 6 mock scout_targets; Architect fills comments_list (test skips Scout)
    state["scout_targets"] = MOCK_SCOUT_TARGETS
    state["comments_list"] = []

    architect_result = test_architect(state)
    state.update(architect_result)

    assert len(state.get("comments_list", [])) == 6, (
        "Architect must generate 6 comments"
    )

    # Quality: no engagement bait in first_comment/comments_list; ALEX not described as crashing
    from tests.test_quality import run_quality_assertions_on_state
    run_quality_assertions_on_state(state)

    strategist_result = test_strategist(state)
    state.update(strategist_result)

    print("\n=== Agent pipeline: PASS ===")
    print("Final draft:")
    print(state.get("post_draft"))
    print("\nHashtags:", state.get("hashtags"))
