# Research Agent

A multi-agent research system powered by the [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview). Give it a topic — it searches the web, evaluates sources, writes a report, checks quality, generates diagrams, and **publishes a project** that shows up automatically in a browsable web library.

Each run writes `projects/<slug>/` (a `manifest.json` plus artifacts). That folder is the source of truth: the `web/` app builds a searchable research library from it with zero manual curation. Re-running a topic updates its project in place. See [`projects/README.md`](projects/README.md) and [`web/README.md`](web/README.md).

## Architecture

```
                         CLI / MCP Server
                              │
                    ┌─────────▼──────────┐
                    │   Orchestrator      │  (opus)
                    │   Decomposes topic, │
                    │   coordinates flow  │
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
   │   Search     │    │   Writer    │    │   Visual    │
   │   Agent      │    │   Agent     │    │   Agent     │
   │  Tavily +    │    │  Concise,   │    │  Mermaid    │
   │  source eval │    │  eng-minded │    │  diagrams   │
   │  (sonnet)    │    │  (opus)     │    │  (sonnet)   │
   └─────────────┘    └──────┬──────┘    └─────────────┘
                              │
                       ┌──────▼──────┐
                       │   QA Agent  │
                       │  Fact-check │
                       │  (sonnet)   │
                       └─────────────┘
```

**Flow:** **Recall** prior work (shared memory) → Decompose topic → Search (per question) → Write report → QA review → Revise if needed → Generate visuals → Render output formats → **Publish project** (`projects/<slug>/manifest.json`, also syncs memory)

## Prerequisites

- Python 3.10+
- [Anthropic API key](https://platform.claude.com/)
- [Tavily API key](https://tavily.com/) (for web search)
- Optional: `mmdc` ([mermaid-cli](https://github.com/mermaid-js/mermaid-cli)) for diagram rendering

## Installation

```bash
# Clone and install
git clone <repo-url> && cd Research-agent-
pip install -e .

# Set API keys
cp .env.example .env
# Edit .env with your keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   TAVILY_API_KEY=tvly-...

# Optional: install mermaid-cli for diagram rendering
npm install -g @mermaid-js/mermaid-cli
```

## Usage

### CLI

```bash
# Basic research (markdown output)
research-agent "What is WebAssembly and how does it compare to JavaScript?"

# Multiple output formats
research-agent "Compare React vs Vue vs Svelte" --format markdown,pptx,docx

# Executive style, verbose output
research-agent "State of AI in healthcare 2025" --style executive -v

# All options
research-agent "topic" \
  --format markdown,docx,pptx,email \
  --style concise \
  --output-dir ./projects \
  --visual-emphasis high \
  --max-budget 3.0 \
  -v
```

Output lands in `projects/<slug>/` (the slug is derived from the topic). Running the same topic again updates that folder in place.

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--format`, `-f` | Output formats (comma-separated): `markdown`, `docx`, `pptx`, `email` | `markdown` |
| `--style`, `-s` | Writing style: `concise`, `detailed`, `executive` | `concise` |
| `--output-dir`, `-o` | Projects root; each run creates `projects/<slug>/` | `./projects` |
| `--visual-emphasis` | Diagram quantity: `low`, `medium`, `high` | `high` |
| `--model` | Override model for all agents: `opus`, `sonnet`, `haiku` | per-agent defaults |
| `--max-budget` | Max API spend in USD | `2.00` |
| `--log-level` | Logging: `off`, `summary` (readable log), `full` (JSONL trace + summary) | `summary` |
| `--log-dir` | Log file directory | `<output-dir>/logs/` |
| `--verbose`, `-v` | Show real-time agent activity | off |
| `--dry-run` | Show config without executing | off |

### Claude Code (MCP Server)

The `.mcp.json` is pre-configured. From Claude Code, the research tool is available automatically:

```
Use the research tool to investigate "quantum computing applications in drug discovery"
```

### Python API

```python
import asyncio
from research_agent.config import load_config
from research_agent.main import run_research

config = load_config(cli_overrides={
    "formats": ["markdown", "pptx"],
    "writing_style": "concise",
})
result = asyncio.run(run_research("Your topic here", config, verbose=True))
```

## Output Formats

All artifacts are written into the run's project folder, `projects/<slug>/`:

| Format | File | Description |
|--------|------|-------------|
| **Markdown** | `report.md` | Full report with source citations and reliability annotations |
| **Word** | `report.docx` | Formatted document with color-coded source tiers and embedded diagrams |
| **PowerPoint** | `report.pptx` | Slide deck: title → takeaways → one slide per finding with diagrams |
| **HTML Email** | `report.html` | Concise email with key takeaways, top findings, base64 embedded images |

## Logging & Tracing

Every run produces log files so you can see exactly what each agent did.

```bash
# Default: human-readable summary log
research-agent "topic"
# → projects/<slug>/logs/20260314_103000_summary.log

# Full trace: structured JSONL + summary
research-agent "topic" --log-level full
# → projects/<slug>/logs/20260314_103000_summary.log
# → projects/<slug>/logs/20260314_103000_trace.jsonl

# Disable logging
research-agent "topic" --log-level off
```

**Summary log** — shows the timeline of which agent did what:
```
=== Research Agent Session ===
Topic: What is WebAssembly?

[10:30:05] ORCHESTRATOR → search-agent: "What is WebAssembly?"
[10:30:06]   search-agent > tool: mcp__search__tavily_search (query="What is WebAssembly")
[10:30:08]   search-agent > tool: mcp__search__evaluate_source (domain="developer.mozilla.org")
[10:30:10]   search-agent > DONE
[10:31:00] ORCHESTRATOR → writer-agent: Writing report...

=== Summary ===
Duration: 96s | Cost: $0.0523 | Turns: 18
Agents used: search-agent (×3), writer-agent (×1), qa-agent (×1), visual-agent (×1)
Tools called: tavily_search (×6), evaluate_source (×9), generate_diagram (×2)
```

**JSONL trace** — one JSON event per line, for programmatic analysis:
```json
{"ts":"2026-03-14T10:30:05Z","event":"agent_delegate","agent":"search-agent","tool_use_id":"abc"}
{"ts":"2026-03-14T10:30:06Z","event":"tool_call","agent":"search-agent","tool":"mcp__search__tavily_search","input_preview":"..."}
{"ts":"2026-03-14T10:30:08Z","event":"tool_result","tool_use_id":"def","is_error":false}
```

## Source Reliability

Every source is evaluated and tagged:

- **Established** — `.gov`, `.edu`, peer-reviewed journals, major institutions
- **Reputable** — Major news outlets, official documentation, established tech publications
- **Emerging** — Newer credible sources, pre-prints, startup blogs
- **Opinion** — Personal blogs, social media, forums
- **Unknown** — Cannot determine

Reports adjust language based on source tier. Claims from opinion sources are explicitly flagged.

## Project Structure

```
src/research_agent/
├── main.py              # Orchestrator: wires agents + MCP servers, runs pipeline
├── cli.py               # CLI entry point (click)
├── mcp_server.py        # MCP server for Claude Code integration
├── config.py            # Configuration loading
├── projects.py          # Project library: slugify, manifest build/read/write
├── memory.py            # Shared-memory keyword index (recall across projects)
├── models/
│   ├── source.py        # SourceMetadata, ReliabilityTier, Finding
│   └── report.py        # ReportDraft, ReportSection, QAReview
├── prompts/
│   ├── orchestrator.py  # Orchestrator system + user prompt templates
│   ├── search.py        # Search agent prompt
│   ├── writer.py        # Writer agent prompt (parameterized by style)
│   ├── qa.py            # QA agent prompt
│   └── visual.py        # Visual agent prompt
├── tools/
│   ├── web_search.py    # Tavily search wrapper
│   ├── source_eval.py   # Domain-based reliability scoring
│   ├── diagram_gen.py   # Mermaid → PNG rendering
│   ├── doc_gen.py       # Word document generation (python-docx)
│   ├── slides_gen.py    # PowerPoint generation (python-pptx)
│   ├── html_email.py    # HTML email generation (Jinja2)
│   ├── publish.py       # publish_project — the mandatory final step
│   └── memory_tools.py  # search_memory — recall prior work
└── templates/
    ├── email_base.html  # Jinja2 email template
    └── slide_layouts.py # PowerPoint layout constants

projects/                # Published projects (source of truth) — see projects/README.md
└── <slug>/manifest.json # + report.md, decks, diagrams per run

memory/                  # Shared-memory index derived from projects/ — see memory/README.md
└── index.json           # keyword recall across all projects

web/                     # Next.js research-library front end — see web/README.md
└── scripts/build-library.mjs  # builds the library from projects/ (no npm deps)
```

Topics are organized by **tags + shared memory**, not nested folders — a project
can carry many tags, the web app filters by them, and the agent recalls related
work via `memory/`. See [`memory/README.md`](memory/README.md).

## Research Library (web app)

The `web/` directory is a password-gated Next.js app that turns `projects/` into
a searchable library — one card per project, each with a detail page rendering
the report, deck, diagrams, sources, and version history. It's **auto-built**:
`scripts/build-library.mjs` reads every `projects/<slug>/manifest.json` before
each `dev`/`build`, so anything researched appears with no manual step.

```bash
cd web
npm install
npm run dev      # http://localhost:3000  (rebuilds the library first)
```

Deploys on Vercel with **Root Directory = `web`**. See [`web/README.md`](web/README.md).

## Configuration

Defaults can be overridden via CLI flags. Model assignments per agent:

| Agent | Default Model | Role |
|-------|--------------|------|
| Orchestrator | `opus` | Topic decomposition, workflow coordination |
| Search | `sonnet` | Fast web search and source evaluation |
| Writer | `opus` | High-quality report writing |
| QA | `sonnet` | Structured quality review |
| Visual | `sonnet` | Diagram design and generation |

## License

See repository license.
