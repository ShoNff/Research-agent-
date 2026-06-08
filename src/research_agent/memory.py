"""Shared memory — a keyword-searchable index across every research project.

This is the system's organizational brain. `projects/` is the source of truth;
this index is *derived* from project manifests so the agent can recall prior
work before researching (the orchestrator's Recall phase) and so topics stay
organized by meaning — tags and claims — rather than a rigid folder tree.

Kept as plain JSON under `memory/index.json`: git-tracked, inspectable, and
rebuildable from `projects/` at any time. The publish step keeps it in sync, so
no separate bookkeeping is required.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

INDEX_NAME = "index.json"

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall((text or "").lower())


def _entry_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Project the fields needed for recall out of a full manifest."""
    return {
        "slug": manifest.get("slug", ""),
        "title": manifest.get("title", ""),
        "topic": manifest.get("topic", ""),
        "summary": manifest.get("summary", ""),
        "tags": manifest.get("tags", []),
        "key_claims": manifest.get("key_claims", []),
        "updated": manifest.get("updated", ""),
        "version": manifest.get("version", 1),
    }


def _sort_recent(entries: list[dict[str, Any]]) -> None:
    entries.sort(key=lambda p: (p.get("updated", ""), p.get("version", 0)), reverse=True)


class MemoryStore:
    """File-backed keyword index over project manifests."""

    def __init__(self, memory_dir: str | Path):
        self.memory_dir = Path(memory_dir)
        self.index_path = self.memory_dir / INDEX_NAME

    def _load(self) -> dict[str, Any]:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"projects": []}

    def _save(self, data: dict[str, Any]) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def entries(self) -> list[dict[str, Any]]:
        return self._load().get("projects", [])

    def upsert_project(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Add or replace a project's entry (keyed by slug)."""
        data = self._load()
        entry = _entry_from_manifest(manifest)
        projects = [p for p in data.get("projects", []) if p.get("slug") != entry["slug"]]
        projects.append(entry)
        _sort_recent(projects)
        data["projects"] = projects
        self._save(data)
        return entry

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Keyword search over title/topic/summary/tags/key_claims.

        Scores by token overlap, with tag hits weighted extra. An empty query
        returns the most recently updated projects (useful for "what do we know
        about anything?").
        """
        entries = self.entries()
        q = set(_tokens(query))
        if not q:
            return entries[:limit]

        scored: list[tuple[int, dict[str, Any]]] = []
        for p in entries:
            text = " ".join(
                [
                    p.get("title", ""),
                    p.get("topic", ""),
                    p.get("summary", ""),
                    " ".join(p.get("tags", [])),
                    " ".join(p.get("key_claims", [])),
                ]
            )
            haystack = set(_tokens(text))
            overlap = q & haystack
            if not overlap:
                continue
            tag_hits = q & set(_tokens(" ".join(p.get("tags", []))))
            scored.append((len(overlap) + len(tag_hits), p))

        scored.sort(key=lambda x: (x[0], x[1].get("updated", "")), reverse=True)
        return [p for _, p in scored[:limit]]

    def rebuild(self, projects_root: str | Path) -> list[dict[str, Any]]:
        """Regenerate the whole index from project manifests on disk."""
        projects_root = Path(projects_root)
        projects: list[dict[str, Any]] = []
        if projects_root.exists():
            for child in sorted(projects_root.iterdir()):
                manifest_path = child / "manifest.json"
                if not manifest_path.exists():
                    continue
                try:
                    manifest = json.loads(manifest_path.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                projects.append(_entry_from_manifest(manifest))
        _sort_recent(projects)
        self._save({"projects": projects})
        return projects


def _main() -> None:
    """`python -m research_agent.memory rebuild [projects_root] [memory_dir]`."""
    import sys

    args = sys.argv[1:]
    if not args or args[0] != "rebuild":
        print("usage: python -m research_agent.memory rebuild [projects_root] [memory_dir]")
        return
    projects_root = Path(args[1]) if len(args) > 1 else Path("./projects")
    memory_dir = Path(args[2]) if len(args) > 2 else projects_root.resolve().parent / "memory"
    entries = MemoryStore(memory_dir).rebuild(projects_root)
    print(f"Rebuilt memory index: {len(entries)} project(s) -> {memory_dir / INDEX_NAME}")


if __name__ == "__main__":
    _main()
