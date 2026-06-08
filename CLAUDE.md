# Research Agent — Claude Code Context

## What This Is

A multi-agent research system using the Claude Agent SDK. Five specialized agents (orchestrator, search, writer, QA, visual) collaborate to research topics and produce reports in multiple formats. Each run publishes a **project** into `projects/<slug>/`, which a Next.js web app (`web/`) turns into a browsable research library.

## The Core Rule

**Every research run must end by publishing a project. Everything we research becomes a deliverable in the web app — automatically, with no manual step.**

- The orchestrator's final mandatory phase calls `mcp__publish__publish_project`, which writes `projects/<slug>/manifest.json`.
- `projects/` is the single source of truth. The web app library and (future) shared-memory index are *derived* from it — never hand-curated.
- Re-running a topic updates the same `projects/<slug>/` in place (deterministic slug). The orchestrator detects the prior manifest (`main.py:_build_update_context`), reads the existing `report.md`, and **revises** it — preserving still-accurate content, integrating new findings, bumping `version`, and appending a descriptive `changelog` entry (living reports). `created` is preserved.
- A run that finishes without a manifest has produced nothing the system can see; `main.py` warns when that happens.

See `projects/README.md` for the manifest contract and `web/README.md` for how it reaches the app.

## Learning From Conversations

Preferences and conventions the user expresses in a session ("deck sound off by default", "I
like shorter reports", "always also export a docx") are captured back into the repo by the
`conversation-retrospective` skill — run it with `/retrospective` at the end of a session. It
distills the durable learnings, routes each to its **source of truth** (an agent prompt in
`src/research_agent/prompts/`, a default in `config.py`, a skill internal, harness settings via
the `update-config` skill, or this doc), **proposes a changeset for approval**, then applies the
approved edits and appends them to the append-only `LEARNINGS.md` ledger. The skill's routing
table (`.claude/skills/conversation-retrospective/SKILL.md`) is the map from "kind of preference"
to "file to change"; `LEARNINGS.md` is the auditable record of what was learned and where it
landed. This is how the engine gets smarter without the user repeating themselves.

## Running

```bash
# Install in dev mode
pip install -e .

# Required environment variables (set in .env)
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...

# Run a research task — publishes projects/<slug>/
research-agent "your topic" --format markdown --style concise -v

# Dry run (shows the resolved project folder + config)
research-agent "your topic" --dry-run

# Browse the research library locally (reads projects/)
cd web && npm install && npm run dev
```

## Key Files

| File | What It Does |
|------|-------------|
| `src/research_agent/main.py` | **Start here.** Wires all agents, MCP servers, computes the per-run project dir, and runs the orchestrator `query()` loop. |
| `src/research_agent/cli.py` | CLI entry point using Click. Parses args, loads config, calls `run_research()`. |
| `src/research_agent/config.py` | Configuration dataclass. Loads from `.env` + CLI overrides. `output_dir` is the projects root. |
| `src/research_agent/projects.py` | Project library helpers: `slugify`, manifest build/read/write, artifact discovery. |
| `src/research_agent/memory.py` | Shared-memory keyword index (`MemoryStore`): upsert/search/rebuild over manifests. |
| `src/research_agent/tracing.py` | Structured logging: JSONL trace + human-readable summary log. See "Logging & Tracing" below. |
| `src/research_agent/mcp_server.py` | Wraps the research pipeline as an MCP tool for Claude Code. |
| `src/research_agent/prompts/*.py` | System prompts for each agent. These control agent behavior — edit carefully. |
| `src/research_agent/tools/*.py` | Custom MCP tools using `@tool` decorator + `create_sdk_mcp_server()`. Includes `publish.py` (the mandatory publish step). |
| `src/research_agent/models/*.py` | Pydantic models for source metadata, findings, reports, QA reviews. |
| `src/research_agent/templates/` | Jinja2 email template + PowerPoint layout constants. |
| `projects/<slug>/` | Published projects — the source of truth. See `projects/README.md`. |
| `memory/index.json` | Shared-memory index derived from manifests. See `memory/README.md`. |
| `web/` | Next.js research-library front end. Auto-built from `projects/`. See `web/README.md`. |

## Architecture

The orchestrator is the primary `query()` agent. It delegates to 4 subagents via the SDK's `Agent` tool:

- **search-agent** (sonnet) — Tavily web search + source reliability evaluation
- **writer-agent** (opus) — Report composition with source-tier-aware language
- **qa-agent** (sonnet) — Reviews report for accuracy, completeness, coherence
- **visual-agent** (sonnet) — Mermaid diagrams rendered to PNG

Subagents **cannot** spawn other subagents (SDK constraint). The orchestrator passes all context explicitly in the Agent tool's prompt string since subagents have no access to parent conversation history.

Four MCP tool servers are created in-process (`main.py:_build_mcp_servers()`):
- `search` server: `tavily_search`, `evaluate_source`
- `output` server: `generate_diagram`, `render_docx`, `render_pptx`, `render_email`, `generate_slide`
- `publish` server: `publish_project` (the mandatory final step)
- `memory` server: `search_memory` (recall prior work before researching)

The orchestrator workflow runs in phases (`prompts/orchestrator.py`): **recall** → decompose → research → write → QA → revise → visuals → output → **publish**. Every run's `cwd` is its own `projects/<slug>/` folder, so all artifacts land there. Phase 0 recalls prior projects from shared memory; the last phase publishes the manifest.

### The project library + web app
- `projects/<slug>/manifest.json` is written by `publish_project` and is the contract every consumer reads.
- `web/scripts/build-library.mjs` rebuilds the web library from `projects/` before each `dev`/`build`: copies servable artifacts into `web/public/library/<slug>/`, renders `report.md` to HTML, and emits `web/lib/library.generated.ts`. No manual curation.

### Shared memory + how topics are organized
- Projects are stored **flat** (`projects/<slug>/`) and organized by **tags** (many-to-many faceting) plus the **memory index** — not by nested topic folders (a folder tree forces one rigid taxonomy and breaks the deterministic slug→path that living reports depend on).
- `memory/index.json` is a keyword index derived from manifests (`research_agent.memory.MemoryStore`). The publish step upserts each run; `python -m research_agent.memory rebuild` regenerates it from `projects/`. See `memory/README.md`.

## Logging & Tracing

Every research run produces log files in `<project_dir>/logs/` (i.e. `projects/<slug>/logs/`, configurable via `--log-dir`). The log dir is resolved per-run in `run_research()` once the slug is known.

**Log levels** (`--log-level`):
- `summary` (default): Human-readable `*_summary.log` showing agent→tool flow timeline
- `full`: Summary + `*_trace.jsonl` with one JSON event per line (machine-readable)
- `off`: No log files

**Summary log** shows the full execution timeline:
```
=== Research Agent Session ===
Topic: What is WebAssembly?
Started: 2026-03-14 10:30:00 UTC
Session ID: abc-123

[10:30:01] orchestrator: Decomposing topic into research questions...
[10:30:05] ORCHESTRATOR → search-agent: "What is WebAssembly?"
[10:30:06]   search-agent > tool: mcp__search__tavily_search (query="What is WebAssembly")
[10:30:08]   search-agent > tool: mcp__search__evaluate_source (domain="developer.mozilla.org")
[10:30:10]   search-agent > DONE

=== Summary ===
Duration: 96s (API: 72s)
Cost: $0.0523
Agents used: search-agent (×3), writer-agent (×1), qa-agent (×1), visual-agent (×1)
Tools called: tavily_search (×6), evaluate_source (×9), generate_diagram (×2)
```

**JSONL trace** events: `session_start`, `agent_delegate`, `tool_call`, `tool_result`, `agent_complete`, `text`, `session_end`. Each line is a self-contained JSON object with timestamp.

**How tracing works internally** (`tracing.py`):
- `ResearchLogger` is instantiated in `main.py:run_research()`
- The message loop in `_process_message()` inspects each SDK message type
- `parent_tool_use_id` on AssistantMessage/UserMessage maps messages to their subagent
- A `tool_use_id → agent_name` dict tracks which Agent tool call belongs to which subagent
- Counters track agent invocations and tool calls for the summary

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
6. If the artifact should show in the web app, make sure its extension is in `SERVABLE` in `web/scripts/build-library.mjs` and rendered by `web/app/projects/[slug]/page.tsx`

### Changing the project/manifest shape or the web library
- Manifest fields are normalized in `research_agent.projects.build_manifest`; the publish tool is `tools/publish.py`. Update `projects/README.md` (the contract) alongside any change.
- The web app reads manifests via `web/scripts/build-library.mjs` → `web/lib/library.generated.ts` → `web/lib/library.ts` (typed loader). The library build uses **no npm dependencies** (don't add any without regenerating `web/package-lock.json`).

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

# Dry run (shows the resolved project folder)
research-agent "test topic" --dry-run

# Full run (requires API keys) — should leave a projects/<slug>/manifest.json
research-agent "What is WebAssembly?" --format markdown -v
ls projects/what-is-webassembly/manifest.json

# Verify the web library builds from projects/
cd web && node scripts/build-library.mjs   # writes lib/library.generated.ts
```
