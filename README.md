# Research Agent

A multi-agent research system powered by the [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview). Give it a topic — it searches the web, evaluates sources, writes a report, checks quality, generates diagrams, and outputs in your preferred format.

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

**Flow:** Decompose topic → Search (per question) → Write report → QA review → Revise if needed → Generate visuals → Render output formats

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
  --output-dir ./output \
  --visual-emphasis high \
  --max-budget 3.0 \
  -v
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--format`, `-f` | Output formats (comma-separated): `markdown`, `docx`, `pptx`, `email` | `markdown` |
| `--style`, `-s` | Writing style: `concise`, `detailed`, `executive` | `concise` |
| `--output-dir`, `-o` | Where to write output files | `./output` |
| `--visual-emphasis` | Diagram quantity: `low`, `medium`, `high` | `high` |
| `--model` | Override model for all agents: `opus`, `sonnet`, `haiku` | per-agent defaults |
| `--max-budget` | Max API spend in USD | `2.00` |
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

| Format | File | Description |
|--------|------|-------------|
| **Markdown** | `report.md` | Full report with source citations and reliability annotations |
| **Word** | `report.docx` | Formatted document with color-coded source tiers and embedded diagrams |
| **PowerPoint** | `report.pptx` | Slide deck: title → takeaways → one slide per finding with diagrams |
| **HTML Email** | `report.html` | Concise email with key takeaways, top findings, base64 embedded images |

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
│   └── html_email.py    # HTML email generation (Jinja2)
└── templates/
    ├── email_base.html  # Jinja2 email template
    └── slide_layouts.py # PowerPoint layout constants
```

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
