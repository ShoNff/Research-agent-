"""Tavily web search tool."""

from __future__ import annotations

import json
import os
from typing import Any

from claude_agent_sdk import tool

from research_agent.tools.limits import exhausted_message, get_budget


@tool(
    "tavily_search",
    "Search the web for information on a topic. Returns structured search results "
    "with titles, URLs, and content snippets (use tavily_extract to read the full "
    "text of promising results). Optional: topic='news' with time_range "
    "(d/w/m/y) for recent coverage, include_domains to restrict sources.",
    {"query": str, "max_results": int, "topic": str, "time_range": str, "include_domains": list, "search_depth": str},
)
async def tavily_search(args: dict[str, Any]) -> dict[str, Any]:
    """Search the web using the Tavily API."""
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "ERROR: TAVILY_API_KEY environment variable is not set.",
                }
            ]
        }

    budget = get_budget()
    if not budget.try_search():
        return {"content": [{"type": "text", "text": exhausted_message("search", budget)}]}

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=api_key)
        max_results = args.get("max_results", 5)
        search_kwargs: dict[str, Any] = {
            "query": args["query"],
            "max_results": min(max_results, 10),
            "include_answer": True,
            "search_depth": args.get("search_depth") or "advanced",
        }
        if args.get("topic") in ("news", "general", "finance"):
            search_kwargs["topic"] = args["topic"]
        if args.get("time_range") in ("d", "w", "m", "y", "day", "week", "month", "year"):
            search_kwargs["time_range"] = args["time_range"]
        if args.get("include_domains"):
            search_kwargs["include_domains"] = list(args["include_domains"])[:10]

        response = await client.search(**search_kwargs)

        results = []
        for result in response.get("results", []):
            results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                }
            )

        output = {
            "query": args["query"],
            "answer": response.get("answer", ""),
            "results": results,
            "budget": budget.summary(),
        }

        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}

    except ImportError:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "ERROR: tavily-python not installed. Run: pip install tavily-python",
                }
            ]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"ERROR: Tavily search failed: {e}"}]
        }
