# Brand & Graphics Standard

The quality bar for diagrams and decks: **hand-authored SVG with a real icon kit, brand
colors, soft depth, and large readable type** — not auto-laid-out Mermaid "wire" boxes.
SVG renders crisply at any size, stays diff-able in git, and needs no rasterizer.

## Palette

| Token | Hex | Use |
|------|------|-----|
| Navy (deep) | `#1c2d54` | Primary text, environment cards |
| Navy (mid) | `#34518f` | Gradjuent tops, zone labels |
| Steel | `#3a6fae` / `#5b91c8` | Tools, secondary cards, accents |
| Blaze orange | `#e8732b` / `#f0822f` → `#d2541a` | Blaze hub, the deploy/compliance path, emphasis |
| Gold | `#daa520` / `#f3d27a` | Source-of-truth (templates), manual-gate accents |
| Card surface | `#ffffff` on canvas `#f6f9fd → #e7eef8` | Light cards |
| Muted text | `#4a5b80`; sub-label `#5a6b8f`; zone label `#8194b8` |
| Status | pass `#3ba66a` · pending `#d9a92e` · next/queued `#3a6fae` |

## Building blocks (see `blaze-flow.svg` for a worked example)

- **Gradients** per surface: `gNavy`, `gSteel`, `gBlaze`, `gGold`, `gCanvas`. Define once in `<defs>`.
- **Depth**: `filter: soft` (dy 6, blur 9, navy @18%) for cards; `softLg` (warm, stronger) for the hero/Blaze element only.
- **Cards**: `rx="14–22"`, white fill, `stroke="#d8e1f0"`, optional 6px top accent bar in the card's color.
- **Arrows**: `stroke-width 2.4` neutral (`#6b7da6`, marker `arw`) for build flow; `3.2` blaze-orange
  (marker `arwO`) for the deploy → comply → run path so the governed path reads as one bright thread.
- **Type scale**: card title 19–22 / 700; hero 36–40 / 800; body 15–16; chips/labels 14 / 600–700;
  zone labels 15 / 700 / `letter-spacing:2` uppercase. Keep body ≥ 15px — nothing tiny.
- **Chips**: `rx=15` pills, `#eaf1fa` fill, `#cdddf0` stroke, steel text — for enumerations (tools, env tiers).

## Icon kit — `symbols.svg`

24×24, stroke-based, `stroke-width 1.8`, round caps, `stroke="currentColor"`. Set the color on the
consuming `<g color="…">`. Current set: `template, ai, app, flame, shield, approval, cloud, gateway, bell`.
Add new icons to `symbols.svg` first, then **inline** them into the consumer's `<defs>` (cross-file
`<use href>` is blocked by CORS in self-contained files, so deck SVGs carry their own copy).

## Composition rules

- Lay out in **named zones** (BUILD · DEPLOY · COMPLIANCE · RUN · STATUS) with uppercase zone labels.
- One **hero** element per diagram (here: the Blaze hub) gets the strongest color + shadow; everything
  else is calmer so the eye lands on the point.
- 16:9 framing (`viewBox 0 0 1320 820`) for slide use; let it scale with `width:100%`.
- Prefer **explicit coordinates** over auto-layout: it's the only way to get text that always fits.
