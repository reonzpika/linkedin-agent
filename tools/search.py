"""
Search and content fetching for the LinkedIn Engine.
NZ-health search (Tavily), LinkedIn topic search (Serper), full-page fetch (Firecrawl), agent research (Firecrawl).
"""

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Preferred NZ domains for search_nz_health
NZ_DOMAIN_PRIORITY = (
    ".govt.nz",
    "rnzcgp.org.nz",
    "medtech.co.nz",
    "health.govt.nz",
    "tewhatuora.govt.nz",
    "rnz.co.nz",
    "stuff.co.nz",
    "nzherald.co.nz",
)


def search_nz_health(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    NZ-contextualised web search via Tavily.
    Prefers .govt.nz, rnzcgp.org.nz, medtech.co.nz and NZ news domains.
    Returns list of {title, url, snippet} dicts.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        # Add NZ context to query
        q = f"{query} New Zealand"
        response = client.search(q, max_results=max_results + 10, search_depth="basic")
        results = getattr(response, "results", []) or []
        out = []
        for r in results:
            url = getattr(r, "url", "") or (r.get("url") if isinstance(r, dict) else "")
            title = getattr(r, "title", "") or (
                r.get("title") if isinstance(r, dict) else ""
            )
            snippet = (
                getattr(r, "content", "")
                or getattr(r, "snippet", "")
                or (r.get("content") or r.get("snippet") if isinstance(r, dict) else "")
            )
            out.append({"title": title, "url": url, "snippet": snippet})

        # Prefer NZ domains
        def score(item: dict) -> int:
            u = (item.get("url") or "").lower()
            for i, d in enumerate(NZ_DOMAIN_PRIORITY):
                if d in u:
                    return -i
            return 0

        out.sort(key=score)
        return out[:max_results]
    except Exception:
        return []


def search_linkedin_topic(query: str) -> list[dict[str, Any]]:
    """
    LinkedIn-scoped search via Serper API (site:linkedin.com).
    Used by Scout for initial target discovery without Playwright.
    Returns list of {title, url, snippet} dicts.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []
    try:
        import requests

        q = f"site:linkedin.com {query}"
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": q},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        organic = data.get("organic", [])
        return [
            {
                "title": o.get("title", ""),
                "url": o.get("link", ""),
                "snippet": o.get("snippet", ""),
            }
            for o in organic
        ]
    except Exception:
        return []


def fetch_page_content(url: str) -> str:
    """
    Full-page Markdown via Firecrawl scrape endpoint.
    Returns clean Markdown; on failure returns empty string and does not crash.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return ""
    try:
        from firecrawl import Firecrawl

        app = Firecrawl(api_key=api_key)
        result = app.scrape(url, formats=["markdown"])
        if hasattr(result, "markdown"):
            return result.markdown or ""
        if isinstance(result, dict):
            return (
                result.get("markdown", "")
                or result.get("data", {}).get("markdown", "")
                or ""
            )
        return ""
    except Exception:
        return ""


def research_with_agent(prompt: str) -> str:
    """
    Firecrawl /agent endpoint: natural-language research across the web.
    On failure, falls back to search_nz_health with extracted keywords.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return _fallback_agent_search(prompt)
    try:
        from firecrawl import Firecrawl

        app = Firecrawl(api_key=api_key)
        result = app.agent(prompt=prompt)
        if hasattr(result, "data"):
            d = result.data
        elif isinstance(result, dict):
            d = result.get("data", result)
        else:
            d = result
        if isinstance(d, str):
            return d
        if isinstance(d, dict):
            return json.dumps(d, indent=2)
        return str(d)
    except Exception:
        return _fallback_agent_search(prompt)


def _fallback_agent_search(prompt: str) -> str:
    """Extract simple keywords from prompt and run search_nz_health; return concatenated snippets."""
    words = re.findall(r"[a-zA-Z0-9]+", prompt)
    keywords = [w for w in words if len(w) > 2][:8]
    q = " ".join(keywords)
    results = search_nz_health(q, max_results=5)
    if not results:
        return ""
    return "\n\n".join(
        f"**{r.get('title', '')}**\n{r.get('snippet', '')}\nSource: {r.get('url', '')}"
        for r in results
    )
