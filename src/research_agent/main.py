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
    from research_agent.tracing import ResearchLogger

    mcp_servers = _build_mcp_servers()
    agents = _build_agent_definitions(config)

    logger = ResearchLogger(
        log_dir=config.log_dir or config.output_dir / "logs",
        level=config.log_level,
        topic=topic,
    )

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

    try:
        async for message in query(prompt=prompt, options=options):
            _process_message(message, logger, verbose)

            if isinstance(message, ResultMessage):
                result_text = getattr(message, "result", None)
    finally:
        logger.close()

    return result_text


def _process_message(message, logger, verbose: bool) -> None:
    """Process a single SDK message — log it and optionally print to stdout."""
    # SystemMessage (session init)
    if hasattr(message, "subtype") and not isinstance(message, ResultMessage):
        subtype = getattr(message, "subtype", None)
        if subtype == "init":
            data = getattr(message, "data", {}) or {}
            session_id = getattr(message, "session_id", None) or data.get("session_id", "")
            logger.log_session_start(
                session_id=session_id,
                model=data.get("model"),
                tools=data.get("tools"),
                mcp_servers=data.get("mcp_servers"),
            )
            if verbose:
                print(f"  [init] session={session_id}")
            return

    # AssistantMessage — text blocks and tool calls
    if isinstance(message, AssistantMessage):
        parent_id = getattr(message, "parent_tool_use_id", None)
        for block in message.content:
            # Text block
            if hasattr(block, "text"):
                logger.log_text(block.text, parent_tool_use_id=parent_id)
                if verbose:
                    agent = logger._resolve_agent(parent_id)
                    text = block.text
                    if len(text) > 200:
                        text = text[:200] + "..."
                    indent = "    " if agent != "orchestrator" else "  "
                    print(f"{indent}[{agent}] {text}")

            # Tool use block
            elif hasattr(block, "name"):
                tool_name = block.name
                tool_id = getattr(block, "id", "")
                tool_input = getattr(block, "input", {}) or {}

                # Agent delegation — track subagent mapping
                if tool_name in ("Agent", "Task"):
                    agent_name = tool_input.get("subagent_type", tool_input.get("description", "unknown"))
                    prompt_preview = tool_input.get("prompt", tool_input.get("description", ""))
                    logger.log_agent_delegate(agent_name, tool_id, prompt_preview)
                    if verbose:
                        print(f"  --> Delegating to: {agent_name}")
                else:
                    logger.log_tool_call(tool_name, tool_id, tool_input, parent_tool_use_id=parent_id)
                    if verbose:
                        agent = logger._resolve_agent(parent_id)
                        indent = "    " if agent != "orchestrator" else "  "
                        print(f"{indent}--> Tool: {tool_name}")
        return

    # UserMessage — tool results
    if hasattr(message, "tool_use_result") or hasattr(message, "content"):
        parent_id = getattr(message, "parent_tool_use_id", None)
        tool_use_id = None
        content_text = ""
        is_error = False

        # Try to extract tool result info
        msg_content = getattr(message, "content", None)
        if isinstance(msg_content, list):
            for block in msg_content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id", "")
                        content_text = str(block.get("content", ""))
                        is_error = block.get("is_error", False)
                elif hasattr(block, "tool_use_id"):
                    tool_use_id = block.tool_use_id
                    content_text = str(getattr(block, "content", ""))
                    is_error = getattr(block, "is_error", False)

        if tool_use_id:
            logger.log_tool_result(tool_use_id, content_text, is_error, parent_tool_use_id=parent_id)

            # Check if this is an Agent tool result (subagent completion)
            if tool_use_id in logger._tool_use_to_agent:
                logger.log_agent_complete(tool_use_id, content_text[:200])
        return

    # ResultMessage — session end
    if isinstance(message, ResultMessage):
        logger.log_session_end(
            cost_usd=getattr(message, "total_cost_usd", None),
            num_turns=getattr(message, "num_turns", None),
            duration_ms=getattr(message, "duration_ms", None),
            duration_api_ms=getattr(message, "duration_api_ms", None),
            usage=getattr(message, "usage", None),
            stop_reason=getattr(message, "stop_reason", None),
            subtype=message.subtype,
        )
        if verbose:
            cost = getattr(message, "total_cost_usd", None)
            turns = getattr(message, "num_turns", None)
            print(f"\n  Research {message.subtype}.")
            if cost is not None:
                print(f"  Cost: ${cost:.4f}")
            if turns is not None:
                print(f"  Turns: {turns}")
        return
