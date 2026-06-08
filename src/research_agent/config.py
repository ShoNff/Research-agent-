"""Configuration loading for the research agent system."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class ModelConfig:
    orchestrator: str = "opus"
    search: str = "sonnet"
    writer: str = "opus"
    qa: str = "sonnet"
    visual: str = "sonnet"


@dataclass
class Config:
    formats: list[str] = field(default_factory=lambda: ["markdown"])
    # The projects root. Each run creates a project folder under it
    # (projects/<slug>/) that holds the manifest and all generated artifacts.
    output_dir: Path = field(default_factory=lambda: Path("./projects"))
    writing_style: str = "concise"
    visual_emphasis: str = "high"
    max_qa_revisions: int = 2
    max_budget_usd: float = 2.0
    models: ModelConfig = field(default_factory=ModelConfig)
    tavily_api_key: str = ""
    log_level: str = "summary"  # "off", "summary", "full"
    log_dir: Path | None = None  # defaults to output_dir/logs/


def load_config(
    config_path: str | None = None,
    cli_overrides: dict | None = None,
) -> Config:
    """Load configuration from environment and CLI overrides."""
    load_dotenv()

    config = Config(
        tavily_api_key=os.environ.get("TAVILY_API_KEY", ""),
    )

    if cli_overrides:
        if "formats" in cli_overrides:
            config.formats = cli_overrides["formats"]
        if "output_dir" in cli_overrides:
            config.output_dir = Path(cli_overrides["output_dir"])
        if "writing_style" in cli_overrides:
            config.writing_style = cli_overrides["writing_style"]
        if "visual_emphasis" in cli_overrides:
            config.visual_emphasis = cli_overrides["visual_emphasis"]
        if "max_budget_usd" in cli_overrides:
            config.max_budget_usd = cli_overrides["max_budget_usd"]
        if cli_overrides.get("model_override"):
            model = cli_overrides["model_override"]
            config.models = ModelConfig(
                orchestrator=model,
                search=model,
                writer=model,
                qa=model,
                visual=model,
            )
        if "log_level" in cli_overrides:
            config.log_level = cli_overrides["log_level"]
        if "log_dir" in cli_overrides:
            config.log_dir = Path(cli_overrides["log_dir"])

    config.output_dir.mkdir(parents=True, exist_ok=True)

    # log_dir is resolved per-run in run_research() to <project_dir>/logs once
    # the project slug is known. Leave it as the explicit override, or None.

    return config
