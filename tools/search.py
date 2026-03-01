"""
Search and content fetching for the LinkedIn Engine.
NZ-health search (Tavily), LinkedIn topic search (Serper), full-page fetch (Crawl4AI).
Research pipeline: Tavily search + Crawl4AI fetch + Claude Haiku summarisation.
"""

import asyncio
import os
from concurrent import futures
from typing import Any

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def _safe_exc_str(e: BaseException) -> str:
    """ASCII-safe exception string for logging on Windows (avoids charmap encode errors)."""
    try:
        return str(e).encode("ascii", "replace").decode("ascii")
    except Exception:
        return "unknown error"


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
        from tavily import TavilyClient  # type: ignore[import-untyped]

        client = TavilyClient(api_key=api_key)
        # Add NZ context to query
        q = f"{query} New Zealand"
        response = client.search(q, max_results=max_results + 10, search_depth="basic")
        results = (response.get("results") if isinstance(response, dict) else getattr(response, "results", None)) or []
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
        import requests  # type: ignore[import-untyped]

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


def _run_async_fetch(url: str) -> str:
    """Run Crawl4AI async crawl; returns markdown or empty string. Used by fetch_page_content."""

    async def _crawl() -> str:
        try:
            from crawl4ai import AsyncWebCrawler  # type: ignore[import-untyped]
            from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig  # type: ignore[import-untyped]

            browser_config = BrowserConfig(headless=True, verbose=False)
            run_config = CrawlerRunConfig(
                word_count_threshold=10,
                page_timeout=30_000,
            )
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
            if not result or not getattr(result, "success", True):
                return ""
            md = getattr(result, "markdown", None)
            if md is None:
                return ""
            out = getattr(md, "fit_markdown", None) or getattr(md, "raw_markdown", None)
            if out is None and isinstance(md, str):
                out = md
            return (out or "").strip()
        except Exception as e:
            logger.warning("Crawl4AI fetch failed for {}: {}", url, _safe_exc_str(e))
            return ""

    return asyncio.run(_crawl())


def fetch_page_content(url: str) -> str:
    """
    Full-page Markdown via Crawl4AI (local, no per-call cost).
    Uses AsyncWebCrawler with fit_markdown-style content filtering; headless=True
    (separate from the headed LinkedIn browser in browser.py). Returns clean Markdown;
    on failure or empty returns "" and does not crash.
    """
    if not (url or "").strip():
        return ""
    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return _run_async_fetch(url)
        with futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_async_fetch, url)
            return future.result(timeout=35)
    except Exception as e:
        logger.warning("fetch_page_content failed for {}: {}", url, _safe_exc_str(e))
        return ""


def research_with_agent(prompt: str) -> str:
    """
    Local research pipeline: Tavily search -> Crawl4AI fetch -> Claude Haiku summarisation.
    Returns a single summarised string for NZ primary care relevance. Empty prompt returns "".
    """
    if not (prompt or "").strip():
        return ""
    try:
        results = search_nz_health(prompt, max_results=3)
        if not results:
            logger.warning("research_with_agent: search_nz_health returned no results")
            return ""
        collected: list[str] = []
        for r in results:
            if len(collected) >= 3:
                break
            u = r.get("url")
            if not u:
                continue
            content = fetch_page_content(u)
            if content:
                collected.append(f"--- {u} ---\n{content[:10000]}")
        if not collected:
            logger.warning("research_with_agent: all fetches returned empty")
            return ""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("research_with_agent: ANTHROPIC_API_KEY not set")
            return ""
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage

        system = (
            "You are a research assistant. Summarise the following web content "
            "focusing on what is relevant to NZ primary care and GP practice. "
            "Be factual. Do not invent details not present in the content."
        )
        user_content = f"Prompt: {prompt}\n\nFetched content:\n\n" + "\n\n".join(
            collected
        )
        kwargs: dict[str, Any] = {
            "model": "claude-3-5-haiku-20241022",
            "api_key": api_key,
        }
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        model = ChatAnthropic(**kwargs)
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ]
        response = model.invoke(messages)
        text = getattr(response, "content", "") or str(response)
        return (text or "").strip()
    except Exception as e:
        logger.warning("research_with_agent failed: {}", _safe_exc_str(e))
        return ""
