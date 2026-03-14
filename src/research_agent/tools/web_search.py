"""Tavily web search tool."""

from __future__ import annotations

import json
import os
from typing import Any

from claude_agent_sdk import tool


@tool(
    "tavily_search",
    "Search the web for information on a topic. Returns structured search results with titles, URLs, and content snippets.",
    {"query": str, "max_results": int},
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

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=api_key)
        max_results = args.get("max_results", 5)
        response = await client.search(
            query=args["query"],
            max_results=min(max_results, 10),
            include_answer=True,
        )

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
