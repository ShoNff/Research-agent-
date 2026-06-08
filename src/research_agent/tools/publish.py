"""Project publishing tool — the mandatory final step of every research run.

Calling ``publish_project`` is what turns a pile of generated files into a
first-class deliverable: it writes ``manifest.json`` into the project folder so
the web app can list it and the shared-memory index can recall it. A run that
doesn't publish hasn't produced anything the rest of the system can see, which
is why ``main.py`` treats a missing manifest as a failed run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from research_agent.projects import build_manifest, read_manifest, write_manifest


@tool(
    "publish_project",
    (
        "Publish the completed research project as a deliverable. MUST be called "
        "as the final step of every research run, after all artifacts (report.md, "
        "diagrams, decks) have been written to the project directory. Writes "
        "manifest.json so the project appears in the web app library and the "
        "shared-memory index. Pass project_dir (the projects/<slug> path you were "
        "given) and manifest_json: a JSON object string with keys slug, title, "
        "topic, summary, tags (list of strings), sources (list), and optionally "
        "artifacts (list of {type, path}) and changelog_note. Artifacts are "
        "auto-discovered from disk if omitted."
    ),
    {"project_dir": str, "manifest_json": str},
)
async def publish_project(args: dict[str, Any]) -> dict[str, Any]:
    """Write the project manifest, creating or updating the project."""
    project_dir = Path(args["project_dir"])

    try:
        data = json.loads(args["manifest_json"])
        if not isinstance(data, dict):
            raise ValueError("manifest_json must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        return _error(f"Invalid manifest_json: {exc}")

    if not data.get("slug"):
        data["slug"] = project_dir.name

    # An existing manifest means this is a re-run of an already-published
    # topic: preserve its history and bump the version (living reports).
    existing = read_manifest(project_dir)
    manifest = build_manifest(project_dir, data, existing=existing)

    try:
        path = write_manifest(project_dir, manifest)
    except OSError as exc:
        return _error(f"Failed to write manifest: {exc}")

    action = "updated" if existing else "created"
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "status": "success",
                        "action": action,
                        "slug": manifest["slug"],
                        "version": manifest["version"],
                        "manifest_path": str(path),
                        "artifacts": manifest["artifacts"],
                    }
                ),
            }
        ]
    }


def _error(message: str) -> dict[str, Any]:
    return {
        "content": [
            {"type": "text", "text": json.dumps({"status": "error", "message": message})}
        ]
    }
