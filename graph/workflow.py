"""
DEPRECATED: Chat-first flow uses scripts (plan_from_url, research, scout, draft) and tools/executor.py instead.
LangGraph DAG for the LinkedIn Engine (legacy). Planner -> Researcher -> Scout -> Architect -> Strategist -> Human review (interrupt) -> Executor.
"""

import asyncio
import os
from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph
from loguru import logger

from graph.state import LinkedInContext


# Lazy imports for agents to avoid circular deps and allow optional LangSmith
def _get_agents():
    from agents import architect, researcher, scout, strategist

    return researcher, scout, architect, strategist


def _log(state: LinkedInContext, message: str) -> list:
    """Append a timestamped log entry (return value for state['logs'] reducer)."""
    return [f"[{datetime.utcnow().isoformat()}Z] {message}"]


def planner_node(state: LinkedInContext) -> dict:
    """PS+ initialisation; identify pillar and plan from raw_input."""
    logs = _log(state, "planner: PS+ initialisation")
    # Required phrase before any agent acts (AGENTS.md Initialisation Protocol)
    plan_text = "Let's first understand the problem, extract relevant variables and their corresponding numerals, and make a plan."
    logs.append(_log(state, f"planner: {plan_text}")[0])
    # Heuristic pillar from keywords; plan is a one-line placeholder until we have LLM
    raw = (state.get("raw_input") or "").lower()
    if (
        "alex" in raw
        or "medtech" in raw
        or "api" in raw
        or "healthlink" in raw
        or "infrastructure" in raw
    ):
        pillar = "pillar_1"
    elif (
        "build" in raw
        or "gp feedback" in raw
        or "feature" in raw
        or "clinical tool" in raw
    ):
        pillar = "pillar_2"
    elif (
        "policy" in raw
        or "admin" in raw
        or "prescription" in raw
        or "workforce" in raw
        or "pho" in raw
    ):
        pillar = "pillar_3"
    else:
        pillar = "pillar_1"
    plan = f"Topic: {state.get('raw_input', '')}. Pillar: {pillar}. Proceed to research then scout then draft."
    return {"logs": logs, "pillar": pillar, "plan": plan}


def researcher_node(state: LinkedInContext) -> dict:
    """Run Researcher agent; pass only <SOLUTION> output to state. On dehallucination trigger, interrupt."""
    from langgraph.types import interrupt as _interrupt

    researcher, _, _, _ = _get_agents()
    update = researcher.run(state)
    if update.get("interrupt_dehallucination"):
        _interrupt(update["interrupt_dehallucination"])
        return {"logs": _log(state, "researcher: dehallucination interrupt resolved")}
    return {
        **{k: v for k, v in update.items() if k != "interrupt_dehallucination"},
        "logs": _log(state, "researcher: completed"),
    }


def scout_node(state: LinkedInContext) -> dict:
    """Run Scout agent; pass only <SOLUTION> output to state."""
    _, scout, _, _ = _get_agents()
    update = scout.run(state)
    scout_logs = (update.get("logs") or []) + _log(state, "scout: completed")
    return {**update, "logs": scout_logs}


def architect_node(state: LinkedInContext) -> dict:
    """Run Architect agent; pass only <SOLUTION> output to state."""
    _, _, architect, _ = _get_agents()
    update = architect.run(state)
    return {**update, "logs": _log(state, "architect: completed")}


def strategist_node(state: LinkedInContext) -> dict:
    """Run Strategist agent; approve or request revision (max 2 loops)."""
    _, _, _, strategist = _get_agents()
    update = strategist.run(state)
    return {**update, "logs": _log(state, "strategist: completed")}


def human_review_node(state: LinkedInContext) -> dict:
    """Interrupt for consolidated human review. Resume value can be True (approve) or dict with edits."""
    from langgraph.types import interrupt as _interrupt

    # Expose draft for review (AGENTS.md format)
    review_block = (
        "REVIEW REQUIRED\n\n"
        f"POST DRAFT:\n{state.get('post_draft', '')}\n\n"
        f"HASHTAGS: {state.get('hashtags', [])}\n"
        f"FIRST COMMENT: {state.get('first_comment', '')}\n\n"
        "PRE-ENGAGEMENT COMMENTS (Golden Hour):\n"
        + "\n".join(
            f"{i+1}. {c}" for i, c in enumerate(state.get("comments_list") or [])
        )
        + "\n\nType APPROVE to proceed, or paste your corrections below."
    )
    result = _interrupt(review_block)
    if result is True:
        return {"human_approved": True, "logs": _log(state, "human_review: approved")}
    if isinstance(result, dict):
        out = {
            "human_approved": True,
            "logs": _log(state, "human_review: approved with edits"),
        }
        if "post_draft" in result:
            out["post_draft"] = result["post_draft"]
        if "comments_list" in result:
            out["comments_list"] = result["comments_list"]
        if "first_comment" in result:
            out["first_comment"] = result["first_comment"]
        return out
    return {"human_approved": True, "logs": _log(state, "human_review: approved")}


async def executor_node(state: LinkedInContext) -> dict:
    """Execute Golden Hour posting protocol (async-safe). Runs sync Playwright in a thread to avoid async conflict."""

    def _sync_execute() -> dict:
        """Run sync Playwright in thread to avoid async conflict."""
        from config.playwright_settings import get_browser_context

        context = get_browser_context()
        try:
            return executor_run(state, context)
        finally:
            context.close()

    try:
        result = await asyncio.to_thread(_sync_execute)
        return {
            **result,
            "logs": _log(state, "executor: completed"),
        }
    except Exception as e:
        logger.exception("Executor failed")
        return {
            "logs": _log(state, f"Executor failed: {str(e)}"),
            "execution_results": [],
        }


def _strategist_routing(state: LinkedInContext) -> str:
    """Route from strategist: human_review if approved or max revisions reached, else architect."""
    if state.get("strategist_approved") is True:
        return "human_review"
    revision = state.get("revision_count") or 0
    if revision >= 2:
        return "human_review"  # Pass to human with failure notes
    return "architect"


def build_graph():
    """Build and return the StateGraph (not yet compiled)."""
    builder = StateGraph(LinkedInContext)
    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("scout", scout_node)
    builder.add_node("architect", architect_node)
    builder.add_node("strategist", strategist_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("executor", executor_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "scout")
    builder.add_edge("scout", "architect")
    builder.add_edge("architect", "strategist")
    builder.add_conditional_edges(
        "strategist",
        _strategist_routing,
        {"human_review": "human_review", "architect": "architect"},
    )
    builder.add_edge("human_review", "executor")
    builder.add_edge("executor", END)

    return builder


def build_graph_prepare():
    """Build graph for preparation only: planner -> researcher -> scout -> architect -> strategist -> (architect | END)."""
    builder = StateGraph(LinkedInContext)
    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("scout", scout_node)
    builder.add_node("architect", architect_node)
    builder.add_node("strategist", strategist_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "scout")
    builder.add_edge("scout", "architect")
    builder.add_edge("architect", "strategist")
    builder.add_conditional_edges(
        "strategist",
        _strategist_routing_prepare,
        {"architect": "architect", "end": END},
    )

    return builder


def _strategist_routing_prepare(state: LinkedInContext) -> str:
    """Route from strategist: end if approved or max revisions, else architect (revision loop)."""
    if state.get("strategist_approved") is True:
        return "end"
    revision = state.get("revision_count") or 0
    if revision >= 2:
        return "end"
    return "architect"


def executor_run(state: dict, context: Any) -> dict:
    """
    Execute Golden Hour posting protocol. Called standalone by execute_post.py.
    Posts 6 pre-engagement comments then schedules main post. Raises RuntimeError on failure.
    """
    from datetime import timedelta
    from tools.browser import post_comment, schedule_post

    scout_targets = (state.get("scout_targets") or [])[:6]
    comments_list = state.get("comments_list") or []
    post_draft = state.get("post_draft") or ""
    first_comment = state.get("first_comment") or ""

    results: list[dict] = []

    for i, target in enumerate(scout_targets):
        if i >= len(comments_list):
            break
        comment_text = comments_list[i]
        post_url = target.get("post_url") or target.get("url")
        if post_url and comment_text:
            r = post_comment(context, post_url, comment_text)
            results.append({
                "type": "comment",
                "target": target.get("name", ""),
                "post_url": post_url,
                "result": r,
            })
            if not r.get("success"):
                raise RuntimeError(
                    r.get("error", "post_comment failed")
                )

    n = datetime.utcnow()
    days_ahead = (1 - n.weekday()) % 7
    if days_ahead == 0 and n.hour >= 21:
        days_ahead = 7
    scheduled = (
        (n + timedelta(days=days_ahead))
        .replace(hour=19, minute=0, second=0, microsecond=0)
        .isoformat()
        + "Z"
    )
    r = schedule_post(context, post_draft, first_comment, scheduled)
    results.append({"type": "main_post", "result": r})
    if not r.get("success"):
        raise RuntimeError(r.get("error", "schedule_post failed"))

    return {"execution_results": results}


def get_compiled_graph_prepare():
    """
    Compile graph for preparation only (stops after strategist).
    Used by prepare_post.py. No human_review or executor nodes.
    """
    from graph.persistence import get_checkpointer

    builder = build_graph_prepare()
    checkpointer = get_checkpointer()
    if checkpointer is not None:
        checkpointer.setup()
    return builder.compile(
        checkpointer=checkpointer if checkpointer is not None else None
    )


def get_compiled_graph():
    """Compile graph with Redis checkpointer when available; optionally wrap with LangSmith tracing.
    Production requires Redis; when Redis is unavailable (e.g. local test), the graph compiles
    without a checkpointer so tests can run. See graph.persistence module docstring.
    """
    from graph.persistence import get_checkpointer

    builder = build_graph()
    checkpointer = get_checkpointer()
    if checkpointer is not None:
        checkpointer.setup()
    graph = builder.compile(checkpointer=checkpointer if checkpointer is not None else None)

    if os.getenv("LANGSMITH_API_KEY"):
        try:
            from langsmith import traceable

            # Wrap invoke/stream with LangSmith (project from LANGSMITH_PROJECT)
            project = os.getenv("LANGSMITH_PROJECT", "clinicpro-linkedin-agent")
            # LangSmith auto-instruments when LANGSMITH_API_KEY is set; no extra wrap needed for LangGraph
            pass
        except Exception:
            pass
    return graph
