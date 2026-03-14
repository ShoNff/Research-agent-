"""MCP server wrapper — exposes the research agent as a tool for Claude Code."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool


@tool(
    "research",
    "Research a topic using a multi-agent system. Breaks the topic into questions, searches the web, writes a report with source reliability evaluation, generates diagrams, and produces output in the requested format(s).",
    {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The research topic or question to investigate",
            },
            "format": {
                "type": "string",
                "description": "Output format(s), comma-separated: markdown, docx, pptx, email. Default: markdown",
            },
            "style": {
                "type": "string",
                "description": "Writing style: concise, detailed, or executive. Default: concise",
            },
            "output_dir": {
                "type": "string",
                "description": "Output directory path. Default: ./output",
            },
        },
        "required": ["topic"],
    },
)
async def research_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Run the full research pipeline as an MCP tool."""
    from research_agent.config import load_config
    from research_agent.main import run_research

    formats = args.get("format", "markdown")
    format_list = [f.strip() for f in formats.split(",")]
    output_dir = args.get("output_dir", "./output")
    style = args.get("style", "concise")

    config = load_config(
        cli_overrides={
            "formats": format_list,
            "output_dir": Path(output_dir),
            "writing_style": style,
        },
    )

    result = await run_research(args["topic"], config, verbose=False)

    if result:
        return {"content": [{"type": "text", "text": result}]}
    else:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Research completed. Output files are in {output_dir}/",
                }
            ]
        }


# Create the MCP server
server = create_sdk_mcp_server(
    name="research-agent",
    version="0.1.0",
    tools=[research_tool],
)

if __name__ == "__main__":
    # When run directly, this module serves as an MCP stdio server
    # The claude-agent-sdk handles the MCP protocol
    print("Research Agent MCP Server ready", file=sys.stderr)
