"""Configuration loading for the research agent system."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class ModelConfig:
    orchestrator: str = "opus"
    search: str = "sonnet"
    writer: str = "opus"
    qa: str = "sonnet"
    # opus: the visual agent hand-authors presentation-grade SVG deck scenes,
    # the quality-sensitive step ("light" profile drops it back to sonnet).
    visual: str = "opus"


@dataclass
class RunLimits:
    """Hard per-run tool budgets, enforced inside the search/fetch tools."""

    max_searches: int = 25
    max_extracts: int = 12
    max_research_rounds: int = 2


# Profiles trade depth for cost. "deep" widens the budgets and follow-up
# rounds; "light" narrows them and drops every agent to sonnet.
PROFILES: dict[str, dict] = {
    "deep": {
        "limits": RunLimits(max_searches=40, max_extracts=20, max_research_rounds=3),
        "models": None,  # keep defaults (opus orchestrator/writer)
    },
    "standard": {
        "limits": RunLimits(),
        "models": None,
    },
    "light": {
        "limits": RunLimits(max_searches=10, max_extracts=5, max_research_rounds=1),
        "models": ModelConfig(
            orchestrator="sonnet", search="sonnet", writer="sonnet",
            qa="sonnet", visual="sonnet",
        ),
    },
}


@dataclass
class Config:
    formats: list[str] = field(default_factory=lambda: ["markdown"])
    # The projects root. Each run creates a project folder under it
    # (projects/<slug>/) that holds the manifest and all generated artifacts.
    output_dir: Path = field(default_factory=lambda: Path("./projects"))
    writing_style: str = "concise"
    profile: str = "standard"
    max_qa_revisions: int = 2
    limits: RunLimits = field(default_factory=RunLimits)
    models: ModelConfig = field(default_factory=ModelConfig)
    tavily_api_key: str = ""
    log_level: str = "summary"  # "off", "summary", "full"
    log_dir: Path | None = None  # defaults to output_dir/logs/


def _apply_profile(config: Config, profile: str) -> None:
    spec = PROFILES.get(profile)
    if not spec:
        return
    config.profile = profile
    config.limits = replace(spec["limits"])
    if spec["models"] is not None:
        config.models = replace(spec["models"])


def _apply_config_file(config: Config, path: Path) -> None:
    """Apply overrides from a JSON config file (limits, models, style)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if "profile" in data:
        _apply_profile(config, data["profile"])
    if "writing_style" in data:
        config.writing_style = data["writing_style"]
    if "formats" in data:
        config.formats = list(data["formats"])
    if "max_qa_revisions" in data:
        config.max_qa_revisions = int(data["max_qa_revisions"])
    for key in ("max_searches", "max_extracts", "max_research_rounds"):
        if key in data.get("limits", {}):
            setattr(config.limits, key, int(data["limits"][key]))
    for agent, model in data.get("models", {}).items():
        if hasattr(config.models, agent):
            setattr(config.models, agent, model)


def load_config(
    config_path: str | None = None,
    cli_overrides: dict | None = None,
) -> Config:
    """Load configuration from environment, optional config file, and CLI overrides.

    Precedence (lowest to highest): defaults -> research-agent.config.json
    (repo root, or explicit config_path) -> CLI overrides.
    """
    load_dotenv()

    config = Config(
        tavily_api_key=os.environ.get("TAVILY_API_KEY", ""),
    )

    file_path = Path(config_path) if config_path else Path("research-agent.config.json")
    if file_path.is_file():
        _apply_config_file(config, file_path)

    if cli_overrides:
        if cli_overrides.get("profile"):
            _apply_profile(config, cli_overrides["profile"])
        if "formats" in cli_overrides:
            config.formats = cli_overrides["formats"]
        if "output_dir" in cli_overrides:
            config.output_dir = Path(cli_overrides["output_dir"])
        if "writing_style" in cli_overrides:
            config.writing_style = cli_overrides["writing_style"]
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
