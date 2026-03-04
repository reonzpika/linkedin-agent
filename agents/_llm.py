"""Shared LLM invocation using config/model_config.json and langchain-anthropic."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "model_config.json"


def get_model(agent_name: str):
    """Load ChatAnthropic model for the given agent from config."""
    from langchain_anthropic import ChatAnthropic

    raw = CONFIG_PATH.read_text(encoding="utf-8")
    config = json.loads(raw)
    entry = config.get(agent_name, {})
    model_id = entry.get("model", "claude-sonnet-4-6")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    kwargs = {"model": model_id, "api_key": api_key}
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatAnthropic(**kwargs)


def invoke(agent_name: str, system: str, user: str) -> str:
    """Invoke Claude for the agent; return content string."""
    model = get_model(agent_name)
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    response = model.invoke(messages)
    return getattr(response, "content", "") or str(response)
