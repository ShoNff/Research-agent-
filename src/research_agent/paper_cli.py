"""CLI entry point for the daily newspaper: `research-paper`."""

from __future__ import annotations

import asyncio
import sys
from datetime import date as date_type
from pathlib import Path

import click


@click.command()
@click.option(
    "--date",
    "edition_date",
    default=None,
    help="Edition date (YYYY-MM-DD). Default: today",
)
@click.option(
    "--repo-root",
    default=".",
    help="Repo root containing config/, projects/, memory/, editions/. Default: .",
)
@click.option("--no-email", is_flag=True, help="Skip sending the email edition")
@click.option(
    "--refresh-stale",
    type=int,
    default=0,
    help="After the edition, run a full research refresh on up to N stale projects",
)
@click.option("--dry-run", is_flag=True, help="Show configuration without executing")
@click.option("--verbose", "-v", is_flag=True, help="Show agent activity in real-time")
def main(
    edition_date: str | None,
    repo_root: str,
    no_email: bool,
    refresh_stale: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Produce today's edition of the personal daily research briefing.

    Sweeps the standing interests in config/interests.json, pulse-checks the
    research library, writes editions/<date>/edition.{json,md}, and emails the
    rendered edition via Resend (RESEND_API_KEY).
    """
    from dotenv import load_dotenv

    load_dotenv()

    from research_agent.paper import (
        PAPER_MAX_EXTRACTS,
        PAPER_MAX_SEARCHES,
        PAPER_MODEL,
        load_interests,
        run_paper,
    )

    root = Path(repo_root).resolve()
    resolved_date = edition_date or date_type.today().isoformat()

    try:
        interests = load_interests(root)
    except FileNotFoundError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(2)

    if dry_run:
        click.echo("Research Paper — Dry Run")
        click.echo(f"  Edition date:   {resolved_date}")
        click.echo(f"  Edition dir:    {root / 'editions' / resolved_date}")
        click.echo(f"  Interests:      {', '.join(i['id'] for i in interests.get('interests', []))}")
        click.echo(f"  Watch mode:     {interests.get('watch_library', {}).get('mode', 'all')}")
        click.echo(f"  Email to:       {', '.join(interests.get('email', {}).get('to', [])) or '(none)'} "
                   f"{'(skipped: --no-email)' if no_email else ''}")
        click.echo(f"  Refresh stale:  up to {refresh_stale}")
        click.echo(f"  Model:          {PAPER_MODEL}")
        click.echo(f"  Budget:         {PAPER_MAX_SEARCHES} searches, {PAPER_MAX_EXTRACTS} extracts")
        sys.exit(0)

    click.echo(f"Producing edition {resolved_date} …")
    result = asyncio.run(
        run_paper(
            root,
            edition_date=resolved_date,
            send_email=not no_email,
            refresh_stale=refresh_stale,
            verbose=verbose,
        )
    )

    if result.error:
        click.echo(f"\nerror: {result.error}", err=True)
        sys.exit(1)

    edition = result.edition
    click.echo(f"\nEdition: {edition.headline}")
    for section in edition.sections:
        click.echo(f"  {section.title}: {len(section.items)} item(s)")
    click.echo(f"Files: {result.edition_dir}/edition.json, edition.md")
    if result.email_sent:
        click.echo("Email: sent")
    if result.refreshed_slugs:
        click.echo(f"Refreshed: {', '.join(result.refreshed_slugs)}")
    if edition.refresh_recommendations:
        remaining = [
            s for s in edition.refresh_recommendations if s not in result.refreshed_slugs
        ]
        if remaining:
            click.echo(f"Stale (not refreshed): {', '.join(remaining)}")


if __name__ == "__main__":
    main()
