#!/usr/bin/env python3
"""Build a single self-contained animated-Mermaid HTML deck from a JSON script.

Pure standard library (json, re, pathlib, argparse) so this skill folder can be
copied into any repository and run without installing anything.

Usage:
    python build_deck.py path/to/deck.json --output out/deck.html
    python build_deck.py path/to/deck.json --output out/deck.html --cdn
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE_DIR = HERE / "template"
CDN_TAG = '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>'

DEFAULT_THEME = {
    "primary": "#29417a",
    "secondary": "#4682b4",
    "accent": "#daa520",
    "text": "#1c2533",
    "bg": "#0d1626",
}

# Arrow tokens we recognise when parsing flowchart edges (declaration order).
_ARROW_RE = re.compile(r"(<-->|-->|---|-\.->|-\.-|==>|===|--x|--o|x--x|o--o|~~~)")
_SKIP_PREFIXES = (
    "classDef", "class ", "style ", "linkStyle", "subgraph", "end",
    "%%", "flowchart", "graph", "direction",
)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _validate(deck: dict) -> None:
    if not isinstance(deck, dict):
        raise ValueError("Deck script must be a JSON object.")
    scenes = deck.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Deck must have a non-empty 'scenes' array.")
    seen = set()
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {i} must be an object.")
        sid = scene.get("id")
        if not sid:
            raise ValueError(f"Scene {i} is missing an 'id'.")
        if sid in seen:
            raise ValueError(f"Duplicate scene id: {sid!r}.")
        seen.add(sid)
        for b in scene.get("beats", []) or []:
            if "text" not in b:
                raise ValueError(f"A beat in scene {sid!r} is missing 'text'.")
        for step in scene.get("buildSteps", []) or []:
            if "reveal" not in step:
                raise ValueError(f"A buildStep in scene {sid!r} is missing 'reveal'.")
            if "atBeat" not in step and "atMs" not in step:
                raise ValueError(
                    f"A buildStep in scene {sid!r} needs 'atBeat' or 'atMs'."
                )


# --------------------------------------------------------------------------- #
# Edge alias resolution: rewrite "edge:A-->B" reveal tokens to "edge:N"
# --------------------------------------------------------------------------- #
def _parse_edge_order(mermaid_src: str) -> dict:
    """Return {"src-->tgt": index} mapping in Mermaid declaration order."""
    order: dict[str, int] = {}
    idx = 0
    for raw in mermaid_src.splitlines():
        line = raw.strip()
        if not line or line.startswith(_SKIP_PREFIXES):
            continue
        m = _ARROW_RE.search(line)
        if not m:
            continue
        left = line[: m.start()].strip()
        right = line[m.end():].strip()
        if right.startswith("|"):  # strip edge label  -->|text|
            close = right.find("|", 1)
            right = right[close + 1:].strip() if close != -1 else right[1:].strip()
        src = re.split(r"[\[\(\{<]", left.split()[-1])[0].strip() if left.split() else ""
        tgt = re.split(r"[\[\(\{<]", right.split()[0])[0].strip() if right.split() else ""
        if src and tgt:
            order.setdefault(f"{src}-->{tgt}", idx)
        idx += 1
    return order


def _resolve_svg_sources(deck: dict, base_dir: Path) -> None:
    """Expand hand-authored SVG scene sources into an inline ``svg`` string.

    A scene may supply its diagram as a hand-authored SVG instead of Mermaid via:
      - ``svg``: inline SVG markup (used as-is), or
      - ``svgFile``: a path (relative to the deck JSON) read and inlined, or
      - ``svgRef``: a key into the deck-level ``svgAssets`` map.

    Several scenes referencing the **same** file/ref get the **same** inlined
    string, which is what the engine keys on to reveal one master SVG cumulatively
    across scenes (mirroring shared-Mermaid scenes). ``svgFile``/``svgRef`` keys
    are removed after expansion; the top-level ``svgAssets`` map is dropped.
    """
    assets = deck.get("svgAssets") or {}
    for scene in deck["scenes"]:
        if "svg" in scene:
            continue
        ref = scene.pop("svgRef", None)
        path = scene.pop("svgFile", None)
        if ref is not None:
            if ref not in assets:
                raise ValueError(f"scene {scene.get('id')!r}: svgRef {ref!r} not in svgAssets")
            scene["svg"] = assets[ref]
        elif path is not None:
            f = (base_dir / path).resolve()
            if not f.exists():
                raise FileNotFoundError(f"scene {scene.get('id')!r}: svgFile not found: {f}")
            scene["svg"] = f.read_text(encoding="utf-8")
    deck.pop("svgAssets", None)


def _resolve_edge_aliases(deck: dict) -> list[str]:
    warnings: list[str] = []
    for scene in deck["scenes"]:
        src = scene.get("mermaid")
        steps = scene.get("buildSteps")
        if not src or not steps:
            continue
        order = _parse_edge_order(src)
        for step in steps:
            new_tokens = []
            for tok in step.get("reveal", []):
                if isinstance(tok, str) and tok.startswith("edge:") and "-->" in tok:
                    key = tok[len("edge:"):].replace(" ", "")
                    if key in order:
                        new_tokens.append(f"edge:{order[key]}")
                    else:
                        warnings.append(
                            f"scene {scene['id']!r}: edge alias {tok!r} not found in diagram"
                        )
                        new_tokens.append(tok)
                else:
                    new_tokens.append(tok)
            step["reveal"] = new_tokens
    return warnings


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def _theme_vars(deck: dict) -> str:
    theme = dict(DEFAULT_THEME)
    theme.update(deck.get("theme") or {})
    return "".join(f"--{k}:{v};" for k, v in theme.items())


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_deck(script_path, output_path, *, cdn: bool = False) -> str:
    """Render a deck JSON file to a single self-contained HTML file.

    Returns the output path as a string.
    """
    script_path = Path(script_path)
    output_path = Path(output_path)

    deck = json.loads(_read(script_path))
    _validate(deck)
    _resolve_svg_sources(deck, script_path.parent)
    for w in _resolve_edge_aliases(deck):
        print(f"warning: {w}", file=sys.stderr)

    template = _read(TEMPLATE_DIR / "deck.html.j2")
    css = _read(TEMPLATE_DIR / "deck_styles.css")
    engine = _read(TEMPLATE_DIR / "deck_engine.js")

    # Mermaid.js is only needed when a scene actually uses Mermaid. A deck built
    # entirely from hand-authored SVG scenes skips it, dropping ~3 MB from the file.
    needs_mermaid = any(s.get("mermaid") for s in deck["scenes"])
    mermaid_file = TEMPLATE_DIR / "mermaid.min.js"
    use_cdn = cdn or not mermaid_file.exists()
    if needs_mermaid and cdn is False and not mermaid_file.exists():
        print(
            "warning: template/mermaid.min.js not found — falling back to CDN "
            "(output will require internet). Vendor it for a fully offline file.",
            file=sys.stderr,
        )

    # JSON embedded in <script>; escape </ so it can't close the tag early.
    deck_json = json.dumps(deck, ensure_ascii=False).replace("</", "<\\/")

    html = template
    html = html.replace("{{THEME_VARS}}", _theme_vars(deck))
    html = html.replace("{{DECK_TITLE}}", deck.get("title", "Animated Deck"))
    html = html.replace("{{DECK_SUBTITLE}}", deck.get("subtitle", ""))
    html = html.replace("{{INLINE_CSS}}", css)

    if not needs_mermaid:
        html = html.replace("<script>{{MERMAID_SCRIPT}}</script>", "")
    elif use_cdn:
        html = html.replace("<script>{{MERMAID_SCRIPT}}</script>", CDN_TAG)
    else:
        html = html.replace("{{MERMAID_SCRIPT}}", _read(mermaid_file))

    html = html.replace("{{DECK_JSON}}", deck_json)
    html = html.replace("{{ENGINE_JS}}", engine)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build an animated Mermaid HTML deck.")
    parser.add_argument("script", help="Path to the deck JSON script.")
    parser.add_argument(
        "-o", "--output", default="output/deck.html", help="Output HTML path."
    )
    parser.add_argument(
        "--cdn", action="store_true",
        help="Load mermaid.js from a CDN instead of inlining it (smaller, needs internet).",
    )
    args = parser.parse_args(argv)
    try:
        out = build_deck(args.script, args.output, cdn=args.cdn)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Built deck: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
