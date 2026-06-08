# Research Projects

This folder is the **source of truth** for the whole system. Every research run
publishes exactly one project here, and everything downstream — the web app
library, the shared-memory index — is derived from these folders. Nothing else
is canonical.

## The rule

**A research run is only complete when it has published a project.** The
orchestrator's final mandatory step calls `mcp__publish__publish_project`
(see `src/research_agent/tools/publish.py`), which writes the `manifest.json`
below. A run that finishes without a manifest has produced nothing the rest of
the system can see, and `main.py` warns when that happens.

## Layout

```
projects/
└── <slug>/                 # deterministic slug of the topic (see projects.slugify)
    ├── manifest.json        # the contract — metadata + provenance
    ├── report.md            # canonical report (rendered to HTML for the web app)
    ├── *.html               # decks / standalone pages
    ├── *.png / *.svg        # diagrams
    └── *.docx / *.pptx      # optional Office artifacts
```

The slug is deterministic, so re-running a topic targets the **same folder** and
updates it in place — preserving `created`, bumping `version`, and appending to
the `changelog` (living reports).

## manifest.json

Written and normalized by `research_agent.projects.build_manifest`. Shape:

```json
{
  "slug": "what-is-webassembly",
  "title": "What is WebAssembly?",
  "topic": "the original research topic",
  "summary": "1-2 sentence plain-language summary",
  "tags": ["web", "compilers"],
  "created": "2026-06-08",
  "updated": "2026-06-08",
  "published_at": "2026-06-08T10:30:00+00:00",
  "version": 1,
  "artifacts": [{ "type": "report", "path": "report.md" }],
  "sources": [{ "url": "...", "title": "...", "domain": "...", "reliability_tier": "established", "confidence_score": 0.95 }],
  "related": ["other-slug"],
  "changelog": [{ "version": 1, "date": "2026-06-08", "note": "initial research" }]
}
```

`artifacts` is auto-discovered from the files on disk if the publish call omits
it, so a deck or diagram still appears in the web app even if it wasn't listed
explicitly.

## How this reaches the web app

`web/scripts/build-library.mjs` reads every `manifest.json` here before each
`dev`/`build`, copies servable artifacts into `web/public/library/<slug>/`, and
renders `report.md` to HTML. Commit the project folder and push — Vercel
rebuilds and the card appears automatically. See `web/README.md`.

> Project folders are committed to git; this is the deliverable archive. Keep
> `report.md`/HTML/PNG as the web-facing artifacts; large Office files are
> optional downloads.
