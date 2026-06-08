"""Generate the architecture deck (architecture.deck.json) and render deck.html.

Run from the repo root:
    python projects/research-agent-architecture/build_deck.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SKILL = REPO / ".claude" / "skills" / "animated-mermaid-deck"

# --- Master architecture diagram (shared by the core-architecture scenes) -----
# Reveals are cumulative across scenes that share this exact source: each scene
# shows everything earlier scenes revealed and animates only its own new tokens.
MASTER = """flowchart TB
  anthropic["Anthropic — Claude Opus / Sonnet"]:::brain
  subgraph sandboxes["Ephemeral Sandboxes — Claude Code on the web"]
    cc["Claude Code"]:::agent
    orch(["orchestrator"]):::agent
    sub["search · writer · qa · visual subagents"]:::agent
    tavily["Web search (Tavily)"]:::ext
  end
  subgraph github["GitHub — Single Source of Truth"]
    projects["projects/{slug}/ — manifest · report · diagrams"]:::truth
    memory[("memory/index.json")]:::store
    code["src/ · web/ — the system's own code"]:::res
  end
  subgraph vercel["Vercel — Runtime and Presentation"]
    build["build-library.mjs"]:::res
    app["Next.js research library"]:::res
  end
  gate{{"Password gate — middleware.ts"}}:::portal
  reader["Reader"]:::client

  anthropic --> cc
  cc --> orch
  orch --> sub
  sub --> tavily
  sub -->|"commit + push"| projects
  projects --> memory
  projects -->|"rebuild on push"| build
  build --> app
  reader --> gate
  gate --> app
  classDef brain fill:#7b4fb5,stroke:#4a2d73,color:#ffffff,font-weight:bold;
  classDef agent fill:#4682b4,stroke:#29417a,color:#ffffff;
  classDef ext fill:#dfe5ee,stroke:#5b6b8a,color:#29417a;
  classDef truth fill:#daa520,stroke:#7a5c00,color:#1a1a1a,font-weight:bold;
  classDef store fill:#29417a,stroke:#1c2d54,color:#ffffff;
  classDef res fill:#e8eef7,stroke:#4682b4,color:#29417a;
  classDef portal fill:#bcd2f0,stroke:#29417a,color:#16233f,font-weight:bold;
  classDef client fill:#dfe5ee,stroke:#5b6b8a,color:#29417a;
  style github fill:#daa520,fill-opacity:0.08,stroke:#daa520,stroke-width:4px,color:#7a5c00;
  style sandboxes fill:#4682b4,fill-opacity:0.08,stroke:#4682b4,stroke-width:3px,color:#29417a;
  style vercel fill:#1c2d54,fill-opacity:0.06,stroke:#29417a,stroke-width:3px,color:#29417a;"""

# --- Standalone diagrams for the pattern / hosting scenes ----------------------
GRAPH = """flowchart LR
  src["Source documents / feeds"]:::client
  subgraph parse["Agentic parsing layer (Claude Code)"]
    extract["Extract entities + relationships"]:::agent
  end
  gdb[("Graph database")]:::store
  gapp["App (runtime layer)"]:::res
  src --> extract
  extract -->|"commit schema + data"| gdb
  gdb --> gapp
  classDef client fill:#dfe5ee,stroke:#5b6b8a,color:#29417a;
  classDef agent fill:#4682b4,stroke:#29417a,color:#ffffff;
  classDef store fill:#29417a,stroke:#1c2d54,color:#ffffff;
  classDef res fill:#e8eef7,stroke:#4682b4,color:#29417a;
  style parse fill:#4682b4,fill-opacity:0.08,stroke:#4682b4,stroke-width:3px,color:#29417a;"""

PM = """flowchart LR
  subgraph repos["Templated repos — one per source"]
    direction TB
    devops["Repo: Azure DevOps"]:::truth
    jira["Repo: Jira"]:::truth
    sp["Repo: SharePoint"]:::truth
  end
  conn["Plugins · Skills · Integrations (MCP / SDK connectors)"]:::portal
  cc2["Claude Code (write path)"]:::agent
  rt["Runtime layer (read path)"]:::res
  devops --> conn
  jira --> conn
  sp --> conn
  conn --> cc2
  cc2 --> rt
  classDef truth fill:#daa520,stroke:#7a5c00,color:#1a1a1a,font-weight:bold;
  classDef portal fill:#bcd2f0,stroke:#29417a,color:#16233f,font-weight:bold;
  classDef agent fill:#4682b4,stroke:#29417a,color:#ffffff;
  classDef res fill:#e8eef7,stroke:#4682b4,color:#29417a;
  style repos fill:#daa520,fill-opacity:0.08,stroke:#daa520,stroke-width:3px,color:#7a5c00;"""

HOSTING = """flowchart LR
  repo[("GitHub — source of truth")]:::truth
  subgraph now["Today"]
    vercel["Vercel (Next.js)"]:::res
    pw{{"Password gate"}}:::portal
  end
  subgraph later["Long term"]
    dg["Advisory Digital Gateway (Azure)"]:::store
    entra{{"Entra ID"}}:::portal
  end
  repo --> vercel
  vercel --> pw
  repo -.->|"re-host read path"| dg
  dg --> entra
  classDef truth fill:#daa520,stroke:#7a5c00,color:#1a1a1a,font-weight:bold;
  classDef res fill:#e8eef7,stroke:#4682b4,color:#29417a;
  classDef portal fill:#bcd2f0,stroke:#29417a,color:#16233f,font-weight:bold;
  classDef store fill:#29417a,stroke:#1c2d54,color:#ffffff;
  style now fill:#4682b4,fill-opacity:0.08,stroke:#4682b4,stroke-width:3px,color:#29417a;
  style later fill:#7b4fb5,fill-opacity:0.10,stroke:#7b4fb5,stroke-width:3px,color:#4a2d73;"""


def core(scene_id, beats, builds, narration, caption, dur):
    return {
        "id": scene_id,
        "kind": "diagram",
        "durationSec": dur,
        "narration": narration,
        "beats": beats,
        "mermaid": MASTER,
        "buildSteps": builds,
        "caption": caption,
    }


deck = {
    "title": "Research Agent Architecture",
    "subtitle": "GitHub at the center as the source of truth, Claude Code as the write path, a runtime layer as the read path.",
    "targetDurationSec": 200,
    "defaultAdvance": "auto",
    "audio": {"enabled": True, "voiceHint": "en", "rate": 1.0},
    "theme": {"primary": "#29417a", "secondary": "#4682b4", "accent": "#daa520"},
    "scenes": [
        {
            "id": "intro",
            "kind": "title",
            "durationSec": 7,
            "narration": "The architecture of this research agent. GitHub at the center as the single source of truth, Claude Code as the write path, and a runtime layer as the read path. About three minutes.",
            "beats": [
                {"text": "Research Agent <b>Architecture</b>", "style": "h1", "anim": "fade-up"},
                {"text": "GitHub at the center — Claude Code writes, the runtime reads.", "style": "body", "anim": "fade"},
                {"text": "~3 minutes", "style": "note", "anim": "fade"},
            ],
        },
        {
            "id": "pattern",
            "kind": "content",
            "durationSec": 11,
            "narration": "One sentence holds the whole system together. GitHub is the source of truth. Claude Code is the write path that changes it. The runtime layer is the read path that presents it. And authentication sits on top of the read path. Everything else is a variation on what you put inside.",
            "beats": [
                {"text": "The pattern, in one sentence:", "style": "h2"},
                {"text": "<b>GitHub</b> is the source of truth.", "style": "body"},
                {"text": "<b>Claude Code</b> is the write path that changes it.", "style": "body"},
                {"text": "The <b>runtime layer</b> is the read path that presents it.", "style": "body"},
                {"text": "<b>Auth</b> sits on top of the read path.", "style": "note"},
            ],
        },
        core(
            "github-center",
            [
                {"text": "At the center: <b>GitHub</b>.", "style": "h2"},
                {"text": "<b>projects/{slug}/</b> is the source of truth — manifest, report, diagrams.", "style": "body"},
                {"text": "Everything downstream is <i>derived</i> from it, never hand-curated.", "style": "note"},
            ],
            [{"atBeat": 0, "reveal": ["github", "projects"], "effect": "pulse"}],
            "At the center sits GitHub. The projects folder, with a manifest per deliverable, is the single source of truth. Everything else in the system is derived from it — never hand-curated.",
            "GitHub is the single source of truth",
            12,
        ),
        core(
            "write-path",
            [
                {"text": "The write path: <b>Claude Code</b>.", "style": "h2"},
                {"text": "Agents run in <b>ephemeral sandboxes</b>, powered by <b>Anthropic</b>'s Claude.", "style": "body"},
                {"text": "An orchestrator drives search, writer, QA, and visual subagents.", "style": "body"},
                {"text": "They <b>commit and push</b> — the only way the truth changes.", "style": "note"},
            ],
            [
                {"atBeat": 0, "reveal": ["anthropic", "sandboxes", "cc"], "effect": "appear"},
                {"atBeat": 2, "reveal": ["orch", "sub", "edge:anthropic-->cc", "edge:cc-->orch", "edge:orch-->sub"], "effect": "draw"},
                {"atBeat": 3, "reveal": ["edge:sub-->projects"], "effect": "draw"},
            ],
            "The write path is Claude Code, running in ephemeral sandboxes powered by Anthropic's Claude models. An orchestrator drives four subagents — search, writer, QA, and visual — and they commit and push to the repo. That is the only way the source of truth changes.",
            "Claude Code is the only write path",
            16,
        ),
        core(
            "web-search",
            [
                {"text": "Agents reach <b>out</b> for evidence.", "style": "h2"},
                {"text": "The search agent pulls the web via <b>Tavily</b>, scoring source reliability.", "style": "body"},
            ],
            [{"atBeat": 0, "reveal": ["tavily", "edge:sub-->tavily"], "effect": "draw"}],
            "The agents reach out to the world for evidence. The search agent pulls the web through Tavily and scores each source for reliability before anything is written.",
            "Sandboxes can search the web (Tavily)",
            10,
        ),
        core(
            "memory-code",
            [
                {"text": "The repo is more than reports.", "style": "h2"},
                {"text": "A <b>memory index</b> — derived from manifests — lets future runs recall prior work.", "style": "body"},
                {"text": "And the repo holds the system's <b>own code</b>: <b>src/</b> and <b>web/</b>.", "style": "note"},
            ],
            [
                {"atBeat": 1, "reveal": ["memory", "edge:projects-->memory"], "effect": "draw"},
                {"atBeat": 2, "reveal": ["code"], "effect": "appear"},
            ],
            "The repo holds more than reports. A memory index, derived from the manifests, lets future runs recall what we already concluded. And the repo also holds the system's own code — the agent pipeline and the web app.",
            "Memory and code are derived from the same repo",
            12,
        ),
        core(
            "read-path",
            [
                {"text": "The read path: <b>Vercel</b>.", "style": "h2"},
                {"text": "On every push, <b>build-library.mjs</b> turns the repo into a Next.js library.", "style": "body"},
                {"text": "Research a topic → publish → push → the card appears. No wiring.", "style": "note"},
            ],
            [
                {"atBeat": 0, "reveal": ["vercel", "build", "edge:projects-->build"], "effect": "draw"},
                {"atBeat": 1, "reveal": ["app", "edge:build-->app"], "effect": "draw"},
            ],
            "The read path is Vercel. On every push, the build script reads the manifests and renders the repo into a Next.js research library. Research a topic, publish it, push — and the card appears, with nothing to wire up by hand.",
            "Vercel renders the repo into a library on every push",
            13,
        ),
        core(
            "auth-layer",
            [
                {"text": "On top: the <b>auth layer</b>.", "style": "h2"},
                {"text": "A single-password gate in <b>middleware.ts</b> covers every request.", "style": "body"},
                {"text": "A white-label cover over the read path — server-side only.", "style": "note"},
            ],
            [{"atBeat": 0, "reveal": ["reader", "gate", "edge:reader-->gate", "edge:gate-->app"], "effect": "draw"}],
            "On top of the runtime sits the authentication layer: a single-password gate enforced in middleware on every request. The password lives only on the server — a lightweight white-label cover over the read path.",
            "A password gate is the auth layer on top",
            12,
        ),
        core(
            "living-loop",
            [
                {"text": "Put it together: a <b>living system</b>.", "style": "h2"},
                {"text": "Agents publish, the runtime presents, re-runs revise the same folder in place.", "style": "body"},
                {"text": "The git history <i>is</i> the audit trail.", "style": "note"},
            ],
            [{"atBeat": 0, "reveal": ["github"], "effect": "pulse"}],
            "Put both paths together and the repo becomes a living, continuously improving asset. Agents publish, the runtime presents, and re-running any topic revises the same folder in place. The git history is the audit trail.",
            "The full loop — write path in, read path out, GitHub at the center",
            12,
        ),
        {
            "id": "pattern-a",
            "kind": "diagram",
            "durationSec": 15,
            "narration": "Now generalize. The center stays fixed while the inside changes. In the first pattern, the deliverable isn't a report — it's structured data. The agents become a parsing layer that extracts entities and relationships into a graph database underneath the app. Same skeleton, different payload.",
            "beats": [
                {"text": "Pattern A: <b>graph database + agentic parsing</b>.", "style": "h2"},
                {"text": "Agents extract <b>entities and relationships</b> from sources...", "style": "body"},
                {"text": "...into a <b>graph database</b> the app renders. Same skeleton, new payload.", "style": "note"},
            ],
            "mermaid": GRAPH,
            "buildSteps": [
                {"atBeat": 0, "reveal": ["src", "parse", "extract"], "effect": "appear"},
                {"atBeat": 1, "reveal": ["gdb", "edge:src-->extract", "edge:extract-->gdb"], "effect": "draw"},
                {"atBeat": 2, "reveal": ["gapp", "edge:gdb-->gapp"], "effect": "draw"},
            ],
            "caption": "Pattern A — agentic parsing into a graph database",
        },
        {
            "id": "pattern-b",
            "kind": "diagram",
            "durationSec": 16,
            "narration": "In the second pattern, the deliverable is a working surface over external systems. The template gains plugins, skills, and integrations — connectors to tools of record like Microsoft Azure DevOps, and by the same mechanism Jira or SharePoint. You keep one repo per source, each stamped from the same template plus one connector.",
            "beats": [
                {"text": "Pattern B: a <b>project-management layer</b>.", "style": "h2"},
                {"text": "<b>Plugins, skills, integrations</b> — connectors to tools of record.", "style": "body"},
                {"text": "<b>Azure DevOps</b>, Jira, SharePoint — one repo per source, one template.", "style": "note"},
            ],
            "mermaid": PM,
            "buildSteps": [
                {"atBeat": 0, "reveal": ["repos", "devops", "jira", "sp"], "effect": "appear"},
                {"atBeat": 1, "reveal": ["conn", "edge:devops-->conn", "edge:jira-->conn", "edge:sp-->conn"], "effect": "draw"},
                {"atBeat": 2, "reveal": ["cc2", "rt", "edge:conn-->cc2", "edge:cc2-->rt"], "effect": "draw"},
            ],
            "caption": "Pattern B — plugins/skills per source (e.g. Azure DevOps), one repo each",
        },
        {
            "id": "hosting",
            "kind": "diagram",
            "durationSec": 16,
            "narration": "Finally, hosting. The read path only consumes the repo's stable contract, so it's the most swappable part. Today it's Vercel behind a password gate. Long term it re-hosts into the Advisory Digital Gateway on Azure, fronted by Entra ID. The write path and the source of truth don't change — you're re-hosting the read layer, not rebuilding the system.",
            "beats": [
                {"text": "Hosting <b>evolves</b>; the core doesn't.", "style": "h2"},
                {"text": "Today: <b>Vercel</b> behind a password gate.", "style": "body"},
                {"text": "Long term: <b>Advisory Digital Gateway</b> on Azure, fronted by Entra ID.", "style": "body"},
                {"text": "Quick win now: ship on Vercel with a real APP_PASSWORD; keep the read path portable.", "style": "note"},
            ],
            "mermaid": HOSTING,
            "buildSteps": [
                {"atBeat": 0, "reveal": ["repo"], "effect": "pulse"},
                {"atBeat": 1, "reveal": ["now", "vercel", "pw", "edge:repo-->vercel", "edge:vercel-->pw"], "effect": "draw"},
                {"atBeat": 2, "reveal": ["later", "dg", "entra", "edge:repo-->dg", "edge:dg-->entra"], "effect": "draw"},
            ],
            "caption": "Vercel today → Advisory Digital Gateway tomorrow; the repo never moves",
        },
        {
            "id": "recap",
            "kind": "content",
            "durationSec": 11,
            "narration": "To recap. GitHub is the source of truth. Claude Code is the only write path. The runtime layer is the read path, with auth on top. The pattern is templatable — a graph database with agentic parsing, or a project-management layer with source connectors. And hosting evolves from Vercel to the Digital Gateway while the core stays put. That's the architecture.",
            "beats": [
                {"text": "<b>GitHub</b> = source of truth. <b>Claude Code</b> = write path. <b>Runtime</b> = read path.", "style": "h2"},
                {"text": "Auth sits on top; living reports revise in place.", "style": "body"},
                {"text": "Templatable: graph-DB + parsing, or a PM layer with source connectors.", "style": "body"},
                {"text": "Vercel today → Advisory Digital Gateway tomorrow.", "style": "body"},
                {"text": "That's the architecture.", "style": "note"},
            ],
        },
    ],
}


def main() -> int:
    json_path = HERE / "architecture.deck.json"
    json_path.write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n")
    out = HERE / "deck.html"
    cmd = [sys.executable, str(SKILL / "build_deck.py"), str(json_path), "--output", str(out)]
    print("building:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
