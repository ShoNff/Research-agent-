"""CLI entry point for the research agent."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click


@click.command()
@click.argument("topic")
@click.option(
    "--format", "-f",
    "formats",
    default="markdown",
    help="Output formats, comma-separated: markdown, docx, pptx, email. Default: markdown",
)
@click.option(
    "--output-dir", "-o",
    default="./projects",
    help="Projects root directory. Each run creates projects/<slug>/. Default: ./projects",
)
@click.option(
    "--style", "-s",
    type=click.Choice(["concise", "detailed", "executive"]),
    default="concise",
    help="Writing style. Default: concise",
)
@click.option(
    "--visual-emphasis",
    type=click.Choice(["low", "medium", "high"]),
    default="high",
    help="How many diagrams to generate. Default: high",
)
@click.option(
    "--model",
    default=None,
    help="Override model for all agents (opus, sonnet, haiku)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show agent activity in real-time",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show configuration without executing",
)
@click.option(
    "--max-budget",
    type=float,
    default=2.0,
    help="Max spend in USD. Default: 2.0",
)
@click.option(
    "--log-level",
    type=click.Choice(["off", "summary", "full"]),
    default="summary",
    help="Logging level. summary=human-readable log, full=JSONL trace + summary, off=none. Default: summary",
)
@click.option(
    "--log-dir",
    default=None,
    help="Log file directory. Default: <output-dir>/logs/",
)
def main(
    topic: str,
    formats: str,
    output_dir: str,
    style: str,
    visual_emphasis: str,
    model: str | None,
    verbose: bool,
    dry_run: bool,
    max_budget: float,
    log_level: str,
    log_dir: str | None,
) -> None:
    """Research a topic using a multi-agent system powered by Claude.

    TOPIC is the research question or topic to investigate.

    Examples:

        research-agent "What is WebAssembly?" --format markdown,pptx

        research-agent "Compare React vs Vue" --style concise -v
    """
    from research_agent.config import load_config

    format_list = [f.strip() for f in formats.split(",")]

    overrides = {
        "formats": format_list,
        "output_dir": Path(output_dir),
        "writing_style": style,
        "visual_emphasis": visual_emphasis,
        "model_override": model,
        "max_budget_usd": max_budget,
        "log_level": log_level,
    }
    if log_dir:
        overrides["log_dir"] = Path(log_dir)

    config = load_config(cli_overrides=overrides)

    if dry_run:
        from research_agent.projects import slugify

        click.echo("Research Agent — Dry Run")
        click.echo(f"  Topic:            {topic}")
        click.echo(f"  Formats:          {', '.join(config.formats)}")
        click.echo(f"  Style:            {config.writing_style}")
        click.echo(f"  Visual emphasis:  {visual_emphasis}")
        click.echo(f"  Projects root:    {config.output_dir}")
        click.echo(f"  Project folder:   {config.output_dir / slugify(topic)}")
        click.echo(f"  Log level:        {config.log_level}")
        click.echo(f"  Log dir:          {config.log_dir or '<project>/logs'}")
        click.echo(f"  Max budget:       ${config.max_budget_usd:.2f}")
        click.echo(f"  Models:")
        click.echo(f"    Orchestrator:   {config.models.orchestrator}")
        click.echo(f"    Search:         {config.models.search}")
        click.echo(f"    Writer:         {config.models.writer}")
        click.echo(f"    QA:             {config.models.qa}")
        click.echo(f"    Visual:         {config.models.visual}")
        sys.exit(0)

    click.echo(f"Researching: {topic}")
    click.echo(f"Formats: {', '.join(config.formats)} | Style: {config.writing_style}")
    click.echo(f"Output: {config.output_dir}")
    if config.log_level != "off":
        click.echo(f"Logs: {config.log_dir} (level: {config.log_level})")
    click.echo()

    from research_agent.main import run_research

    result = asyncio.run(run_research(topic, config, verbose=verbose))

    if result:
        click.echo("\n" + "=" * 60)
        click.echo(result)
    else:
        click.echo("\nResearch completed. Check output directory for files.")

    # Show log file locations
    if config.log_level != "off" and config.log_dir:
        import glob
        log_files = sorted(glob.glob(str(config.log_dir / "*.log")))
        log_files += sorted(glob.glob(str(config.log_dir / "*.jsonl")))
        if log_files:
            click.echo(f"\nLog files:")
            for lf in log_files[-4:]:  # Show most recent
                click.echo(f"  {lf}")


if __name__ == "__main__":
    main()
