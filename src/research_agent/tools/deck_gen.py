"""Render an animated HTML deck from a deck.json script.

Bridges the pipeline to the animated-mermaid-deck skill's builder
(`.claude/skills/animated-mermaid-deck/build_deck.py`, pure stdlib), so every
research run can ship a presentation deck without a manual Claude Code step.
The visual agent authors the deck.json (hand-authored SVG scenes per
assets/brand/STYLE.md); this tool turns it into the final deck.html.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

_BUILDER_RELPATH = Path(".claude/skills/animated-mermaid-deck/build_deck.py")


def find_deck_builder(start: Path) -> Path | None:
    """Locate build_deck.py by walking up from `start` toward the filesystem root.

    Runs land in projects/<slug>/ inside the repo, so walking up finds the
    repo's skill copy. DECK_BUILDER_PATH overrides for exotic layouts (CI
    checkouts, installs outside the repo).
    """
    override = os.environ.get("DECK_BUILDER_PATH")
    if override:
        p = Path(override)
        return p if p.is_file() else None

    current = start.resolve()
    for candidate_root in [current, *current.parents]:
        candidate = candidate_root / _BUILDER_RELPATH
        if candidate.is_file():
            return candidate
    return None


@tool(
    "render_deck",
    "Build the animated HTML presentation deck from a *.deck.json script file "
    "(author the deck.json first, with hand-authored SVG scenes per the brand "
    "standard). Writes deck.html next to the script.",
    {"deck_json_path": str, "output_path": str},
)
async def render_deck(args: dict[str, Any]) -> dict[str, Any]:
    """Shell out to the deck skill's stdlib builder."""
    script_path = Path(args.get("deck_json_path") or "")
    if not script_path.is_file():
        return {
            "content": [
                {"type": "text", "text": f"ERROR: deck script not found: {script_path}"}
            ]
        }

    output_path = Path(args.get("output_path") or script_path.parent / "deck.html")

    builder = find_deck_builder(script_path.parent)
    if builder is None:
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "ERROR: could not locate the deck builder "
                        f"({_BUILDER_RELPATH}) above {script_path.parent}. "
                        "Set DECK_BUILDER_PATH to the build_deck.py file."
                    ),
                }
            ]
        }

    proc = subprocess.run(
        [sys.executable, str(builder), str(script_path), "-o", str(output_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
        return {
            "content": [
                {"type": "text", "text": f"ERROR: deck build failed:\n{detail}"}
            ]
        }

    result = {
        "status": "success",
        "deck_html": str(output_path.resolve()),
        "size_bytes": output_path.stat().st_size if output_path.exists() else 0,
    }
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
