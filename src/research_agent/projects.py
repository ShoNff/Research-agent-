"""Project library helpers — slugging, paths, and manifest I/O.

A "project" is a single research deliverable stored as a folder under the
projects root (``projects/<slug>/``). Each folder is self-contained and
git-tracked: a ``manifest.json`` describing it plus the generated artifacts
(``report.md``, decks, diagrams, …). The web app and the shared-memory index
both read from these folders, so the manifest is the contract everything else
keys off.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"

# Artifacts we know how to discover by extension when the agent doesn't list
# them explicitly. Maps a glob to the artifact "type" recorded in the manifest.
_ARTIFACT_GLOBS: list[tuple[str, str]] = [
    ("report.md", "report"),
    ("*.html", "deck"),
    ("*.pptx", "slides"),
    ("*.docx", "document"),
    ("*.png", "diagram"),
    ("*.svg", "diagram"),
]


def slugify(text: str, max_length: int = 60) -> str:
    """Turn a topic string into a stable, filesystem- and URL-safe slug.

    Deterministic: the same topic always yields the same slug, which is what
    lets re-running a topic update the existing project in place (living
    reports) rather than spawning a duplicate folder.
    """
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    # Drop anything that isn't alphanumeric or whitespace/hyphen, then collapse
    # runs of separators into single hyphens.
    ascii_text = re.sub(r"[^a-z0-9\s-]", "", ascii_text)
    slug = re.sub(r"[\s-]+", "-", ascii_text).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"


def project_dir_for(projects_root: Path, slug: str) -> Path:
    """Resolve the directory for a project slug under the projects root."""
    return projects_root / slug


def manifest_path(project_dir: Path) -> Path:
    return project_dir / MANIFEST_NAME


def read_manifest(project_dir: Path) -> dict[str, Any] | None:
    """Load an existing manifest, or None if the project hasn't been published."""
    path = manifest_path(project_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def discover_artifacts(project_dir: Path) -> list[dict[str, str]]:
    """Scan a project dir for known artifact files.

    Used as a fallback when the publish call doesn't enumerate artifacts, so a
    deck or diagram on disk still shows up in the web app even if the agent
    forgot to list it.
    """
    seen: set[str] = set()
    artifacts: list[dict[str, str]] = []
    for pattern, kind in _ARTIFACT_GLOBS:
        for match in sorted(project_dir.glob(pattern)):
            if match.name == MANIFEST_NAME:
                continue
            rel = match.relative_to(project_dir).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            artifacts.append({"type": kind, "path": rel})
    return artifacts


def build_manifest(
    project_dir: Path,
    data: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize raw publish data into a complete, well-formed manifest.

    Fills in dates, version, and a changelog entry, and discovers artifacts on
    disk if none were provided. When ``existing`` is supplied (a re-run of an
    already-published topic) the created date is preserved and the version is
    bumped — the foundation the living-report flow builds on.
    """
    today = date.today().isoformat()
    now = datetime.now(timezone.utc).isoformat()

    slug = data.get("slug") or project_dir.name
    artifacts = data.get("artifacts") or discover_artifacts(project_dir)

    if existing:
        created = existing.get("created", today)
        version = int(existing.get("version", 1)) + 1
        changelog = list(existing.get("changelog", []))
    else:
        created = today
        version = 1
        changelog = []

    note = data.get("changelog_note") or (
        "initial research" if version == 1 else "updated research"
    )
    changelog.append({"version": version, "date": today, "note": note})

    return {
        "slug": slug,
        "title": data.get("title") or slug.replace("-", " ").title(),
        "topic": data.get("topic", ""),
        "summary": data.get("summary", ""),
        "tags": data.get("tags", []),
        "created": created,
        "updated": today,
        "published_at": now,
        "version": version,
        "artifacts": artifacts,
        "sources": data.get("sources", []),
        "related": data.get("related", []),
        "changelog": changelog,
    }


def write_manifest(project_dir: Path, manifest: dict[str, Any]) -> Path:
    """Write the manifest to disk, returning its path."""
    project_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_path(project_dir)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return path
