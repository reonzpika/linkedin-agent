"""Shared LLM invocation using config/model_config.json and langchain-anthropic."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "model_config.json"


def get_model(agent_name: str):
    """Load ChatAnthropic model for the given agent from config."""
    from langchain_anthropic import ChatAnthropic

    raw = CONFIG_PATH.read_text(encoding="utf-8")
    config = json.load(raw)
    entry = config.get(agent_name, {})
    model_id = entry.get("model", "claude-3-5-sonnet-20241022")
    return ChatAnthropic(
        model=model_id, api_key=None
    )  # uses ANTHROPIC_API_KEY from env


def invoke(agent_name: str, system: str, user: str) -> str:
    """Invoke Claude for the agent; return content string."""
    model = get_model(agent_name)
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    response = model.invoke(messages)
    return getattr(response, "content", "") or str(response)
