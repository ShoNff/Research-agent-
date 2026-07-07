"""Daily newspaper pipeline — a cheaper second orchestration.

One sonnet agent (no subagents) sweeps the reader's standing interests,
pulse-checks the research library, and writes a validated edition into
editions/YYYY-MM-DD/. Delivery (email via Resend) and any full library
refreshes happen deterministically in code after the agent finishes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date as date_type
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from pydantic import ValidationError

from research_agent.memory import MemoryStore
from research_agent.models.edition import Edition
from research_agent.prompts.paper import (
    PAPER_SYSTEM_PROMPT,
    PAPER_USER_PROMPT_TEMPLATE,
    build_interests_block,
    build_watch_block,
)
from research_agent.tools.limits import get_budget, reset_budget

# The paper runs daily and unattended; keep it cheap and bounded.
PAPER_MAX_SEARCHES = 14
PAPER_MAX_EXTRACTS = 6
PAPER_MAX_TURNS = 40
PAPER_MODEL = "sonnet"


@dataclass
class PaperResult:
    edition: Edition | None = None
    edition_dir: Path | None = None
    email_sent: bool = False
    refreshed_slugs: list[str] = field(default_factory=list)
    error: str | None = None


def load_interests(repo_root: Path) -> dict:
    path = repo_root / "config" / "interests.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"interests config not found at {path} — create config/interests.json"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _watched_projects(memory: MemoryStore, watch_cfg: dict) -> list[dict]:
    entries = memory.entries()
    slugs = watch_cfg.get("slugs")
    if watch_cfg.get("mode") == "all" or not slugs:
        return entries
    wanted = set(slugs)
    return [e for e in entries if e.get("slug") in wanted]


async def run_paper(
    repo_root: Path,
    edition_date: str | None = None,
    send_email: bool = True,
    refresh_stale: int = 0,
    verbose: bool = False,
) -> PaperResult:
    """Produce today's edition; optionally email it and refresh stale projects."""
    from research_agent.main import _build_mcp_servers
    from research_agent.tracing import ResearchLogger

    result = PaperResult()
    repo_root = repo_root.resolve()
    edition_date = edition_date or date_type.today().isoformat()

    interests_cfg = load_interests(repo_root)
    memory_dir = repo_root / "memory"
    memory = MemoryStore(memory_dir)
    watched = _watched_projects(memory, interests_cfg.get("watch_library", {}))

    edition_dir = repo_root / "editions" / edition_date
    edition_dir.mkdir(parents=True, exist_ok=True)
    result.edition_dir = edition_dir

    reset_budget(max_searches=PAPER_MAX_SEARCHES, max_extracts=PAPER_MAX_EXTRACTS)

    prompt = PAPER_USER_PROMPT_TEMPLATE.format(
        date=edition_date,
        persona=interests_cfg.get("reader", {}).get("persona", "A curious generalist."),
        interests_block=build_interests_block(interests_cfg.get("interests", [])),
        watch_block=build_watch_block(watched),
        memory_dir=str(memory_dir),
        edition_dir=str(edition_dir),
        max_searches=PAPER_MAX_SEARCHES,
        max_extracts=PAPER_MAX_EXTRACTS,
    )

    logger = ResearchLogger(
        log_dir=edition_dir / "logs",
        level="summary",
        topic=f"daily edition {edition_date}",
    )

    mcp_servers = _build_mcp_servers()
    options = ClaudeAgentOptions(
        system_prompt=PAPER_SYSTEM_PROMPT,
        mcp_servers={
            "search": mcp_servers["search"],
            "memory": mcp_servers["memory"],
        },
        allowed_tools=[
            "Read",
            "Write",
            "mcp__search__*",
            "mcp__memory__*",
        ],
        permission_mode="bypassPermissions",
        model=PAPER_MODEL,
        max_turns=PAPER_MAX_TURNS,
        cwd=str(edition_dir),
    )

    from research_agent.main import _process_message

    try:
        async for message in query(prompt=prompt, options=options):
            _process_message(message, logger, verbose)
            if isinstance(message, ResultMessage) and verbose:
                pass
    finally:
        if verbose:
            print(f"\n  Paper budget used: {get_budget().summary()}")
        logger.close()

    # Validate the edition IN CODE — a malformed edition fails the run before
    # anything is emailed or committed.
    edition_path = edition_dir / "edition.json"
    if not edition_path.is_file():
        result.error = f"run finished without writing {edition_path}"
        return result
    try:
        result.edition = Edition.model_validate_json(
            edition_path.read_text(encoding="utf-8")
        )
    except ValidationError as e:
        result.error = f"edition.json failed validation: {e}"
        return result

    # Normalize the file to the validated model (stable field order/values).
    edition_path.write_text(
        result.edition.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    if send_email:
        from research_agent.tools.send_email import send_edition_email

        email_cfg = interests_cfg.get("email", {})
        to = email_cfg.get("to") or []
        if not to:
            result.error = "email requested but config/interests.json has no email.to"
            return result
        await send_edition_email(
            result.edition,
            to=to,
            from_addr=email_cfg.get("from", "Research Agent <onboarding@resend.dev>"),
            subject_prefix=email_cfg.get("subject_prefix", "The Daily Brief"),
            library_base=email_cfg.get("library_base", ""),
        )
        result.email_sent = True

    # Full living-report refreshes for stale projects, reusing the normal
    # research pipeline (its own budget, models, and publish flow).
    if refresh_stale > 0 and result.edition.refresh_recommendations:
        from research_agent.config import load_config
        from research_agent.main import run_research
        from research_agent.projects import read_manifest

        for slug in result.edition.refresh_recommendations[:refresh_stale]:
            manifest = read_manifest(repo_root / "projects" / slug)
            topic = (manifest or {}).get("topic")
            if not topic:
                continue
            if verbose:
                print(f"\n  Refreshing stale project: {slug}")
            config = load_config(
                cli_overrides={"output_dir": repo_root / "projects"}
            )
            await run_research(topic, config, verbose=verbose)
            result.refreshed_slugs.append(slug)

    return result
