---
name: animated-mermaid-deck
description: >
  Build a single self-contained, movie-like HTML presentation from a JSON
  "deck script": animated text beats plus a Mermaid diagram that progressively
  builds itself, auto-advancing with optional spoken narration and play/pause /
  prev/next controls. Use when someone wants an animated explainer, a concept
  walkthrough, or a reusable "animated diagram" slideshow (e.g. teaching a
  technical concept to an audience). Author or edit a *.deck.json, then run the
  builder to produce one portable .html that plays offline.
---

# Animated Mermaid Deck

Turn a structured **deck script** (JSON) into one **self-contained HTML file** that
plays like a short movie: each scene fades in text and reveals parts of a Mermaid
diagram in lockstep, auto-advancing over a couple of minutes, with optional Web
Speech narration and playback controls. The JSON is the editable *source*; the
HTML is a rebuildable *artifact*.

## Quick start

```bash
# From the repo root:
python .claude/skills/animated-mermaid-deck/build_deck.py \
  .claude/skills/animated-mermaid-deck/examples/azure_workspaces.deck.json \
  --output output/azure_workspaces.html
# Then open output/azure_workspaces.html in a browser and click "▶ Play".
```

- `--cdn` loads `mermaid.js` from a CDN instead of inlining it (smaller file, needs internet).
  By default `template/mermaid.min.js` is inlined so the output is fully offline/portable.
- The builder is **pure Python standard library** — copy the whole `animated-mermaid-deck/`
  folder into any repo and it works without installing anything.

## Authoring a deck

Create a `*.deck.json` file. Top-level fields:

| Field | Notes |
|-------|-------|
| `title`, `subtitle` | Shown on the title scene + start overlay. |
| `theme` | `{ "primary", "secondary", "accent", "text", "bg" }` hex. Defaults to navy/steel/gold. |
| `targetDurationSec` | Advisory total length; used to size scenes that omit `durationSec`. |
| `defaultAdvance` | `"auto"` or `"click"`. |
| `audio` | `{ "enabled": true, "voiceHint": "en", "rate": 1.0 }`. Narration via the browser's Web Speech API. |
| `mermaidConfig` | Optional overrides merged into `mermaid.initialize`. |
| `scenes` | Ordered array (below). |

**Scene**: `id` (unique), `kind` (`title`\|`content`\|`diagram`\|`svg`), `beats[]`,
`mermaid?` **or** a hand-authored SVG source (`svg`\|`svgFile`\|`svgRef`, see below),
`buildSteps?`, `narration?` (spoken text; defaults to the beats' text), `durationSec?`,
`advance?`, `caption?`.

**Beat**: `text` (inline `<b>`/`<i>` allowed), `style` (`h1`\|`h2`\|`body`\|`note`),
`anim` (`fade-up`\|`typewriter`\|`fade`), `atMs?`.

**BuildStep**: `atBeat` (which beat triggers it) or `atMs`, `reveal` (token list),
`effect` (`appear`\|`draw`\|`pulse`).

### Reveal tokens (how the diagram builds)

A build step reveals parts of that scene's Mermaid diagram. Tokens:

- **Node id** — e.g. `"app"` for `app["App Service"]`.
- **Subgraph / cluster id** — e.g. `"workspace"`; reveals the boundary box + its label.
  (Great for drawing a container *around* already-revealed nodes.)
- **Edge** — `"edge:A-->B"` (readable; the builder resolves it to an index) or `"edge:N"`
  (0-based, in declaration order). `effect:"draw"` makes the arrow extend from source to target.

Reveals are **cumulative across scenes that share the same Mermaid source**: a scene shows
everything earlier scenes revealed, animates only its own new tokens, and keeps not-yet-introduced
parts hidden. So define one master diagram and reveal more of it each scene.

## Hand-authored SVG scenes (the presentation-grade path)

Mermaid is auto-laid-out and reads like engineering scaffolding — thin strokes, cramped
labels. For anything shown to an audience, prefer a **hand-authored SVG** built to the brand
graphics standard (`assets/brand/STYLE.md` + the `assets/brand/symbols.svg` icon kit). SVG
renders crisply, stays diff-able, and needs no rasterizer.

A `kind: "svg"` scene is **full-bleed** (the SVG fills the stage; beats sit as a compact title
on top) and supplies its diagram as:

- `"svg"`: inline SVG markup, **or**
- `"svgFile"`: a path **relative to the deck JSON**, read and inlined at build time, **or**
- `"svgRef"`: a key into a deck-level `"svgAssets": { "<key>": "<svg…>" }` map.

**Progressive reveal works exactly like shared-Mermaid scenes**: point several scenes at the
**same** SVG (same `svgFile`/`svgRef`) and each scene reveals more of it. Wrap each revealable
chunk of the SVG in a group with a `data-reveal` token:

```xml
<g data-reveal="blaze"> … the Blaze hub, its label, its arrow … </g>
```

Then a buildStep's `reveal` lists those tokens (plain ids, no `edge:` syntax):
`{ "atBeat": 0, "reveal": ["blaze"], "effect": "pulse" }`. Tokens match `data-reveal="…"`
(space-separated lists allowed) or an element `id`. `effect`: `appear` (opacity), `pulse`
(scales the group's shape), or `draw` (animates a revealed `<path>`). Anything in the SVG
**without** a `data-reveal` token is static — always visible — so use that for the background.
A deck built entirely from SVG scenes drops Mermaid from the output (~3 MB smaller).

Worked example: `projects/blaze-deployment-platform/` (deck) + `assets/brand/blaze-flow.svg`
(one master SVG, seven `data-reveal` zones, revealed one scene at a time).

### Layout tips (learned the hard way)

- **Unconnected nodes overlap.** Give Mermaid structure: connect nodes with edges, or use
  invisible links `A ~~~ B` to force ranks. A node fanning out to children (`rg --> vm`, `rg --> sql`, …)
  lays out cleanly. Keep diagrams roughly ≤ 4:1 aspect or `width:100%` scaling makes them a thin strip.
- The engine renders labels as **SVG text** (`htmlLabels:false`) for reliable positioning, and
  **never animates CSS `transform` on SVG groups** (it would override their positioning transform) —
  reveals use opacity; pulse scales the shape child. Keep these invariants if you edit the engine.

## Playback

The output opens with a **▶ Play** overlay (a user gesture is required before browsers allow
audio). Controls: Space = play/pause, ← → = prev/next, R = replay, plus a 🔊/🔇 narration toggle.
`prefers-reduced-motion` disables autoplay and reveals everything instantly (navigate with ⏮ ⏭).

## Pre-rendered (studio) narration — optional

Web Speech quality varies by browser. To use recorded audio instead, add `"audioSrc"` to a scene
with a base64 data-URI MP3; the engine will play that `<audio>` instead of TTS. (Not used by the
Azure example.)

## Files

```
animated-mermaid-deck/
├── build_deck.py            # stdlib builder: build_deck(script, out, cdn=False) + CLI
├── template/
│   ├── deck.html.j2         # single-file HTML shell (filled by simple string replacement)
│   ├── deck_engine.js       # render → reveal → timeline + audio (vanilla JS)
│   ├── deck_styles.css      # scenes/beats/controls + reduced-motion
│   └── mermaid.min.js       # vendored (pinned v10) — inlined for offline output
└── examples/
    └── azure_workspaces.deck.json   # worked example: KPMG Azure Workspaces (16 scenes, ~3 min)
```

Start from `examples/azure_workspaces.deck.json` when authoring a new topic — copy it, swap the
scenes, rebuild.
