"""Shared-memory MCP tools — recall prior research before starting new work."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from research_agent.memory import MemoryStore


@tool(
    "search_memory",
    (
        "Search shared memory for prior research projects related to a query. "
        "Call this BEFORE researching a new topic to see what has already been "
        "covered. Returns matching projects with their slug, title, summary, key "
        "claims, and tags so you can avoid duplicate work, focus on gaps, decide "
        "whether this run is an update to an existing project, and cross-link "
        "related projects. Pass memory_dir (given to you) and query (the topic)."
    ),
    {"memory_dir": str, "query": str},
)
async def search_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Return prior projects matching the query, ordered by relevance."""
    store = MemoryStore(args["memory_dir"])
    matches = store.search(args.get("query", ""), limit=5)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {"status": "success", "count": len(matches), "matches": matches}
                ),
            }
        ]
    }
