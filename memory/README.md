# Shared Memory

The system's organizational brain: a keyword-searchable index across **every**
research project. It's how the agent recalls prior work before researching, and
how topics stay organized — by tags and claims, not a folder tree.

## How topics are organized

Projects are stored **flat** in `projects/<slug>/` and organized *virtually*:

- **Tags** (in each manifest) give many-to-many faceting — a project can be
  `["ai", "healthcare", "regulation"]` at once. The web app filters by tag.
- **This index** lets the agent (and you) find projects by meaning, and links
  related work via each manifest's `related` slugs.

No nested topic folders: a folder tree forces one rigid taxonomy and breaks the
deterministic slug → path that living-reports rely on. Tags + this index scale
better to hundreds of projects.

## Files

```
memory/
└── index.json   # one entry per project: slug, title, topic, summary, tags,
                 # key_claims, updated, version
```

`index.json` is **derived from `projects/<slug>/manifest.json`** — `projects/`
remains the single source of truth. It's git-tracked and inspectable.

## How it stays in sync

- The publish step (`tools/publish.py`) upserts the project's entry on every run
  (`research_agent.memory.MemoryStore.upsert_project`).
- Rebuild the whole index from manifests at any time:

  ```bash
  python -m research_agent.memory rebuild            # ./projects -> ./memory
  python -m research_agent.memory rebuild ./projects ./memory
  ```

## How the agent uses it

Before researching, the orchestrator's **Phase 0: Recall** calls
`mcp__memory__search_memory` with the topic. The matches (summaries + key claims)
let it skip what's already known, focus on gaps, treat a close match as an update
to an existing project, and cross-link related projects. See
`prompts/orchestrator.py` and `tools/memory_tools.py`.
