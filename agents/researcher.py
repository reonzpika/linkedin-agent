"""
NZ Health Researcher: NZ primary care infrastructure and policy.
Reads knowledge, runs Tavily search + Crawl4AI fetch + Claude summarisation via research_with_agent; passes content to Claude for synthesis; checks dehallucination.
"""

import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


def run(state: LinkedInContext) -> dict:
    """
    Run research phase. Returns state update with pillar, research_summary, target_urls.
    If dehallucination trigger matches, returns {interrupt_dehallucination: "question"} for workflow to interrupt.
    """
    raw_input = state.get("raw_input") or ""
    pillar = state.get("pillar") or "pillar_1"

    nz_context = (KNOWLEDGE / "nz_health_context.md").read_text(encoding="utf-8")
    dehallucination = (KNOWLEDGE / "dehallucination_triggers.md").read_text(
        encoding="utf-8"
    )

    from tools.search import search_nz_health, research_with_agent

    # NZ-contextualised search and fetched content (Tavily + Crawl4AI + Claude Haiku via research_with_agent)
    query = f"{raw_input} New Zealand primary care"
    results = search_nz_health(query, max_results=5)
    target_urls = [r["url"] for r in results if r.get("url")][:5]
    research_content = research_with_agent(f"{raw_input} New Zealand primary care")

    system = f"""You are an NZ Health Researcher. Use only the following context. Output a single block in this exact format:

<SOLUTION>
pillar: pillar_1|pillar_2|pillar_3
research_summary: [max 300 words, synthesised from the provided sources; NZ focus]
target_urls: [comma-separated list of 3-5 source URLs from the context]
</SOLUTION>

NZ context (glossary): {nz_context[:3000]}

Dehallucination: if the topic touches any of these, output instead a single line: DEHALLUCINATION: [the exact clarification question from the table]. Topics: {dehallucination[:2000]}
"""

    user = f"Topic: {raw_input}\n\nFetched content (Tavily + Crawl4AI + Claude Haiku):\n{research_content[:12000]}"

    from agents._llm import invoke

    out = invoke("researcher", system, user)

    if "DEHALLUCINATION:" in out:
        q = out.split("DEHALLUCINATION:")[-1].strip().split("\n")[0].strip()
        return {"interrupt_dehallucination": q}

    match = re.search(r"<SOLUTION>\s*(.*?)\s*</SOLUTION>", out, re.DOTALL)
    if not match:
        return {
            "research_summary": out[:2000],
            "target_urls": target_urls,
            "pillar": pillar,
        }
    block = match.group(1)
    pillar_match = re.search(r"pillar:\s*(\S+)", block)
    summary_match = re.search(
        r"research_summary:\s*(.+?)(?=target_urls:)", block, re.DOTALL
    )
    urls_match = re.search(r"target_urls:\s*(.+)", block, re.DOTALL)
    research_summary = summary_match.group(1).strip() if summary_match else block[:2000]
    research_summary = research_summary[:3000]
    urls_str = urls_match.group(1).strip() if urls_match else ""
    target_urls = [
        u.strip()
        for u in re.split(r"[\s,]+", urls_str)
        if u.strip() and u.startswith("http")
    ][:5]
    if not target_urls and results:
        target_urls = [r["url"] for r in results[:5] if r.get("url")]
    pillar = pillar_match.group(1).strip() if pillar_match else pillar
    return {
        "research_summary": research_summary,
        "target_urls": target_urls,
        "pillar": pillar,
    }
