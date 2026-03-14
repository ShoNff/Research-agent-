# Research Agent — Claude Code Context

## What This Is

A multi-agent research system using the Claude Agent SDK. Five specialized agents (orchestrator, search, writer, QA, visual) collaborate to research topics and produce reports in multiple formats.

## Running

```bash
# Install in dev mode
pip install -e .

# Required environment variables (set in .env)
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...

# Run a research task
research-agent "your topic" --format markdown --style concise -v

# Dry run (show config only)
research-agent "your topic" --dry-run
```

## Key Files

| File | What It Does |
|------|-------------|
| `src/research_agent/main.py` | **Start here.** Wires all agents, MCP servers, and runs the orchestrator `query()` loop. |
| `src/research_agent/cli.py` | CLI entry point using Click. Parses args, loads config, calls `run_research()`. |
| `src/research_agent/config.py` | Configuration dataclass. Loads from `.env` + CLI overrides. |
| `src/research_agent/mcp_server.py` | Wraps the research pipeline as an MCP tool for Claude Code. |
| `src/research_agent/prompts/*.py` | System prompts for each agent. These control agent behavior — edit carefully. |
| `src/research_agent/tools/*.py` | Custom MCP tools using `@tool` decorator + `create_sdk_mcp_server()`. |
| `src/research_agent/models/*.py` | Pydantic models for source metadata, findings, reports, QA reviews. |
| `src/research_agent/templates/` | Jinja2 email template + PowerPoint layout constants. |

## Architecture

The orchestrator is the primary `query()` agent. It delegates to 4 subagents via the SDK's `Agent` tool:

- **search-agent** (sonnet) — Tavily web search + source reliability evaluation
- **writer-agent** (opus) — Report composition with source-tier-aware language
- **qa-agent** (sonnet) — Reviews report for accuracy, completeness, coherence
- **visual-agent** (sonnet) — Mermaid diagrams rendered to PNG

Subagents **cannot** spawn other subagents (SDK constraint). The orchestrator passes all context explicitly in the Agent tool's prompt string since subagents have no access to parent conversation history.

Two MCP tool servers are created in-process:
- `search` server: `tavily_search`, `evaluate_source`
- `output` server: `generate_diagram`, `render_docx`, `render_pptx`, `render_email`, `generate_slide`

## Code Conventions

- Python 3.10+, uses `from __future__ import annotations`
- Async throughout — all tools are `async def`, main loop uses `async for message in query()`
- Custom tools use the `@tool` decorator from `claude_agent_sdk` with dict-based schemas
- MCP servers built with `create_sdk_mcp_server(name=..., tools=[...])`
- Agent definitions use `AgentDefinition(description=..., prompt=..., tools=[...], model=...)`
- Allowed tools follow MCP naming: `mcp__<server-name>__<tool-name>` with wildcard support `mcp__search__*`
- Config uses plain dataclasses (not pydantic-settings) for simplicity
- Output tools return `{"content": [{"type": "text", "text": "..."}]}` per MCP protocol

## Common Modifications

### Adding a new output format
1. Create a tool in `src/research_agent/tools/` with `@tool` decorator
2. Add it to the `output` server in `main.py:_build_mcp_servers()`
3. Add `mcp__output__<tool_name>` to orchestrator's allowed_tools in `main.py`
4. Update orchestrator prompt in `prompts/orchestrator.py` Phase 7 to handle the new format
5. Add the format name to the CLI `--format` option help text in `cli.py`

### Adding a new agent
1. Write a system prompt in `src/research_agent/prompts/<agent>.py`
2. Add an `AgentDefinition` in `main.py:_build_agent_definitions()`
3. Give it specific tools from existing MCP servers (use `mcp__<server>__<tool>` names)
4. Update the orchestrator prompt to include the new agent in the workflow
5. Add a model config field in `config.py:ModelConfig`

### Adding a new search/research tool
1. Create the tool with `@tool` in `src/research_agent/tools/`
2. Add it to the `search` server in `main.py:_build_mcp_servers()`
3. Add to search-agent's tool list in `_build_agent_definitions()`

### Modifying report style
Edit `src/research_agent/prompts/writer.py`. The `WRITER_PROMPT_TEMPLATE` has a `{style}` parameter that controls output length and tone. The source reliability language rules are also there.

### Changing source reliability heuristics
Edit `src/research_agent/tools/source_eval.py`. The `ESTABLISHED_DOMAINS`, `REPUTABLE_DOMAINS`, and `OPINION_INDICATORS` sets control domain classification. Title-based adjustments are in the `evaluate_source` function body.

## Dependencies

Core: `claude-agent-sdk`, `click`, `pydantic`, `python-dotenv`
Search: `tavily-python`, `aiohttp`
Output: `python-docx`, `python-pptx`, `Jinja2`, `Pillow`
Diagrams: `mmdc` CLI (npm package `@mermaid-js/mermaid-cli`) — optional, degrades gracefully

## Testing

No test suite yet. To verify manually:
```bash
# Syntax check
python -c "import research_agent"

# Dry run
research-agent "test topic" --dry-run

# Full run (requires API keys)
research-agent "What is WebAssembly?" --format markdown -v
```
