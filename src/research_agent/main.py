"""Main orchestrator — wires agents, tools, and runs the research pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
)

from research_agent.config import Config
from research_agent.prompts.orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    ORCHESTRATOR_USER_PROMPT_TEMPLATE,
)
from research_agent.prompts.qa import QA_AGENT_PROMPT
from research_agent.prompts.search import SEARCH_AGENT_PROMPT
from research_agent.prompts.visual import VISUAL_AGENT_PROMPT
from research_agent.prompts.writer import build_writer_prompt
from research_agent.tools.diagram_gen import generate_diagram
from research_agent.tools.doc_gen import render_docx
from research_agent.tools.html_email import render_email
from research_agent.tools.slides_gen import generate_slide, render_pptx
from research_agent.tools.source_eval import evaluate_source
from research_agent.tools.web_search import tavily_search


def _build_mcp_servers():
    """Build the custom MCP tool servers."""
    search_server = create_sdk_mcp_server(
        name="search",
        version="1.0.0",
        tools=[tavily_search, evaluate_source],
    )

    output_server = create_sdk_mcp_server(
        name="output",
        version="1.0.0",
        tools=[
            generate_diagram,
            render_docx,
            render_pptx,
            render_email,
            generate_slide,
        ],
    )

    return {"search": search_server, "output": output_server}


def _build_agent_definitions(config: Config) -> dict[str, AgentDefinition]:
    """Build all subagent definitions."""
    return {
        "search-agent": AgentDefinition(
            description=(
                "Web research specialist. Use this agent to search the web for "
                "information about a specific research question. It searches using "
                "Tavily and evaluates source reliability. Invoke once per research question."
            ),
            prompt=SEARCH_AGENT_PROMPT,
            tools=[
                "WebSearch",
                "mcp__search__tavily_search",
                "mcp__search__evaluate_source",
            ],
            model=config.models.search,
        ),
        "writer-agent": AgentDefinition(
            description=(
                "Report writing specialist. Composes a structured research report "
                "from findings. Weights sources by reliability tier. Adapts writing "
                "style to user preferences. Pass all findings in the prompt."
            ),
            prompt=build_writer_prompt(config.writing_style),
            tools=[],  # Writer is pure text generation
            model=config.models.writer,
        ),
        "qa-agent": AgentDefinition(
            description=(
                "Quality assurance reviewer. Reviews a report draft for accuracy, "
                "completeness, source quality, and coherence. Can do additional web "
                "searches to fact-check claims."
            ),
            prompt=QA_AGENT_PROMPT,
            tools=[
                "WebSearch",
                "mcp__search__evaluate_source",
            ],
            model=config.models.qa,
        ),
        "visual-agent": AgentDefinition(
            description=(
                "Visual design specialist. Creates diagrams, flowcharts, and visual "
                "representations of report content using Mermaid syntax. Renders "
                "diagrams to image files."
            ),
            prompt=VISUAL_AGENT_PROMPT,
            tools=[
                "Bash",
                "Write",
                "mcp__output__generate_diagram",
                "mcp__output__generate_slide",
            ],
            model=config.models.visual,
        ),
    }


def _build_user_prompt(topic: str, config: Config) -> str:
    """Build the orchestrator's user prompt."""
    return ORCHESTRATOR_USER_PROMPT_TEMPLATE.format(
        topic=topic,
        formats=", ".join(config.formats),
        style=config.writing_style,
        max_revisions=config.max_qa_revisions,
        output_dir=str(config.output_dir.resolve()),
    )


async def run_research(
    topic: str,
    config: Config,
    verbose: bool = False,
) -> str | None:
    """Execute the full research pipeline.

    Returns the final result text, or None if the pipeline failed.
    """
    mcp_servers = _build_mcp_servers()
    agents = _build_agent_definitions(config)

    options = ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        agents=agents,
        mcp_servers=mcp_servers,
        allowed_tools=[
            "Agent",
            "Read",
            "Write",
            "Bash",
            "WebSearch",
            "mcp__search__*",
            "mcp__output__*",
        ],
        permission_mode="bypassPermissions",
        model=config.models.orchestrator,
        max_turns=60,
        cwd=str(config.output_dir.resolve()),
    )

    prompt = _build_user_prompt(topic, config)
    result_text = None

    async for message in query(prompt=prompt, options=options):
        if verbose:
            _print_verbose(message)

        if isinstance(message, ResultMessage):
            if message.subtype == "success":
                result_text = getattr(message, "result", None)
                if verbose:
                    cost = getattr(message, "total_cost_usd", None)
                    turns = getattr(message, "num_turns", None)
                    print(f"\nResearch complete.")
                    if cost is not None:
                        print(f"Total cost: ${cost:.4f}")
                    if turns is not None:
                        print(f"Turns used: {turns}")
            else:
                if verbose:
                    print(f"\nResearch stopped: {message.subtype}")

    return result_text


def _print_verbose(message) -> None:
    """Print real-time progress for verbose mode."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if hasattr(block, "text"):
                text = block.text
                if len(text) > 200:
                    text = text[:200] + "..."
                print(f"  [orchestrator] {text}")
            elif hasattr(block, "name"):
                name = block.name
                if name == "Agent":
                    agent_type = getattr(block, "input", {}).get(
                        "subagent_type", "unknown"
                    )
                    desc = getattr(block, "input", {}).get("description", "")
                    print(f"  --> Delegating to: {agent_type} ({desc})")
                else:
                    print(f"  --> Tool: {name}")
