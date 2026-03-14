"""Structured logging and tracing for the research agent pipeline.

Produces two log files per session:
- trace.jsonl: Machine-readable, one JSON event per line (for programmatic analysis)
- summary.log: Human-readable timeline showing agent→tool flow

Uses parent_tool_use_id from the SDK to track which agent context each message belongs to.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class ResearchLogger:
    """Traces agent activity to structured log files.

    Tracks agent delegations, tool calls, results, and session lifecycle.
    Maps tool_use_ids to agent names so every event can be attributed to
    the right agent.
    """

    def __init__(self, log_dir: Path, level: str = "summary", topic: str = ""):
        """Initialize the logger.

        Args:
            log_dir: Directory to write log files into.
            level: "off" (no logging), "summary" (human-readable only),
                   "full" (JSONL trace + summary).
            topic: The research topic (for log headers).
        """
        self.level = level
        self.topic = topic
        self.log_dir = log_dir
        self.session_id: str | None = None
        self.start_time = datetime.now(timezone.utc)

        # Agent context tracking
        # Maps tool_use_id → agent name (for correlating subagent messages)
        self._tool_use_to_agent: dict[str, str] = {}
        # Currently active agent per parent_tool_use_id
        self._active_agent: str = "orchestrator"

        # Counters for summary
        self._agent_calls: Counter = Counter()
        self._tool_calls: Counter = Counter()
        self._output_files: list[str] = []

        # File handles
        self._trace_file = None
        self._summary_file = None

        if level == "off":
            return

        self.log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self._summary_path = self.log_dir / f"{timestamp}_summary.log"
        self._summary_file = open(self._summary_path, "w", encoding="utf-8")

        if level == "full":
            self._trace_path = self.log_dir / f"{timestamp}_trace.jsonl"
            self._trace_file = open(self._trace_path, "w", encoding="utf-8")

        # Write header
        self._write_summary(f"=== Research Agent Session ===")
        self._write_summary(f"Topic: {topic}")
        self._write_summary(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self._write_summary("")

    # ------------------------------------------------------------------
    # Public API — called from the message loop in main.py
    # ------------------------------------------------------------------

    def log_session_start(
        self,
        session_id: str,
        model: str | None = None,
        tools: list[str] | None = None,
        mcp_servers: list | None = None,
    ) -> None:
        """Log session initialization from SystemMessage(subtype='init')."""
        self.session_id = session_id
        self._write_summary(f"Session ID: {session_id}")
        if model:
            self._write_summary(f"Model: {model}")
        self._write_summary("")

        self._write_trace({
            "event": "session_start",
            "session_id": session_id,
            "model": model,
            "tools": tools or [],
            "mcp_servers": [
                {"name": s.get("name", "?"), "status": s.get("status", "?")}
                for s in (mcp_servers or [])
            ],
        })

    def log_agent_delegate(
        self,
        agent_name: str,
        tool_use_id: str,
        prompt_preview: str,
    ) -> None:
        """Log when the orchestrator delegates to a subagent via the Agent tool."""
        self._tool_use_to_agent[tool_use_id] = agent_name
        self._agent_calls[agent_name] += 1

        preview = _truncate(prompt_preview, 120)
        self._write_summary(
            f"{self._ts()} ORCHESTRATOR \u2192 {agent_name}: \"{preview}\""
        )
        self._write_trace({
            "event": "agent_delegate",
            "agent": agent_name,
            "tool_use_id": tool_use_id,
            "prompt_preview": _truncate(prompt_preview, 500),
        })

    def log_tool_call(
        self,
        tool_name: str,
        tool_use_id: str,
        input_data: dict,
        parent_tool_use_id: str | None = None,
    ) -> None:
        """Log a tool call from any agent."""
        agent = self._resolve_agent(parent_tool_use_id)
        self._tool_calls[tool_name] += 1

        # Build a concise input preview
        input_preview = _summarize_tool_input(tool_name, input_data)
        indent = "  " if agent != "orchestrator" else ""
        self._write_summary(
            f"{self._ts()} {indent}{agent} > tool: {tool_name} ({input_preview})"
        )
        self._write_trace({
            "event": "tool_call",
            "agent": agent,
            "tool": tool_name,
            "tool_use_id": tool_use_id,
            "input_preview": _truncate(str(input_data), 500),
        })

    def log_tool_result(
        self,
        tool_use_id: str,
        content: str | None,
        is_error: bool = False,
        parent_tool_use_id: str | None = None,
    ) -> None:
        """Log a tool result."""
        agent = self._resolve_agent(parent_tool_use_id)
        status = "ERROR" if is_error else "ok"

        self._write_trace({
            "event": "tool_result",
            "agent": agent,
            "tool_use_id": tool_use_id,
            "is_error": is_error,
            "result_preview": _truncate(content or "", 500),
        })

        # Only log errors to summary (tool results are usually too verbose)
        if is_error:
            preview = _truncate(content or "unknown error", 200)
            indent = "  " if agent != "orchestrator" else ""
            self._write_summary(
                f"{self._ts()} {indent}{agent} > ERROR: {preview}"
            )

    def log_agent_complete(
        self, tool_use_id: str, result_preview: str = ""
    ) -> None:
        """Log when a subagent finishes (Agent tool result returned)."""
        agent = self._tool_use_to_agent.get(tool_use_id, "unknown-agent")
        preview = _truncate(result_preview, 100)
        self._write_summary(f"{self._ts()}   {agent} > DONE{f' ({preview})' if preview else ''}")
        self._write_trace({
            "event": "agent_complete",
            "agent": agent,
            "tool_use_id": tool_use_id,
            "result_preview": _truncate(result_preview, 500),
        })

    def log_text(
        self, text: str, parent_tool_use_id: str | None = None
    ) -> None:
        """Log assistant text output."""
        agent = self._resolve_agent(parent_tool_use_id)
        preview = _truncate(text, 150)
        indent = "  " if agent != "orchestrator" else ""
        self._write_summary(f"{self._ts()} {indent}{agent}: {preview}")
        self._write_trace({
            "event": "text",
            "agent": agent,
            "text_preview": _truncate(text, 1000),
        })

    def log_output_file(self, path: str) -> None:
        """Track an output file that was generated."""
        self._output_files.append(path)

    def log_session_end(
        self,
        cost_usd: float | None = None,
        num_turns: int | None = None,
        duration_ms: int | None = None,
        duration_api_ms: int | None = None,
        usage: dict | None = None,
        stop_reason: str | None = None,
        subtype: str = "success",
    ) -> None:
        """Log session completion from ResultMessage."""
        self._write_summary("")
        self._write_summary("=== Summary ===")

        if duration_ms is not None:
            api_part = f" (API: {duration_api_ms / 1000:.1f}s)" if duration_api_ms else ""
            self._write_summary(f"Duration: {duration_ms / 1000:.1f}s{api_part}")
        if num_turns is not None:
            self._write_summary(f"Turns: {num_turns}")
        if cost_usd is not None:
            self._write_summary(f"Cost: ${cost_usd:.4f}")
        if usage:
            input_t = usage.get("input_tokens", 0)
            output_t = usage.get("output_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            self._write_summary(
                f"Tokens: {input_t:,} input / {output_t:,} output"
                + (f" / {cache_read:,} cache read" if cache_read else "")
                + (f" / {cache_create:,} cache created" if cache_create else "")
            )
        if stop_reason:
            self._write_summary(f"Stop reason: {stop_reason}")
        self._write_summary(f"Result: {subtype}")

        # Agent usage breakdown
        if self._agent_calls:
            parts = [f"{name} (\u00d7{count})" for name, count in self._agent_calls.most_common()]
            self._write_summary(f"Agents used: {', '.join(parts)}")

        # Tool usage breakdown
        if self._tool_calls:
            parts = [f"{name} (\u00d7{count})" for name, count in self._tool_calls.most_common()]
            self._write_summary(f"Tools called: {', '.join(parts)}")

        # Output files
        if self._output_files:
            self._write_summary(f"Output files: {', '.join(self._output_files)}")

        self._write_trace({
            "event": "session_end",
            "subtype": subtype,
            "cost_usd": cost_usd,
            "num_turns": num_turns,
            "duration_ms": duration_ms,
            "duration_api_ms": duration_api_ms,
            "usage": usage,
            "stop_reason": stop_reason,
            "agent_calls": dict(self._agent_calls),
            "tool_calls": dict(self._tool_calls),
            "output_files": self._output_files,
        })

        self.close()

    def close(self) -> None:
        """Flush and close log files."""
        if self._summary_file:
            self._summary_file.close()
            self._summary_file = None
        if self._trace_file:
            self._trace_file.close()
            self._trace_file = None

    @property
    def summary_path(self) -> Path | None:
        return getattr(self, "_summary_path", None)

    @property
    def trace_path(self) -> Path | None:
        return getattr(self, "_trace_path", None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_agent(self, parent_tool_use_id: str | None) -> str:
        """Resolve which agent a message belongs to from its parent_tool_use_id."""
        if parent_tool_use_id is None:
            return "orchestrator"
        return self._tool_use_to_agent.get(parent_tool_use_id, "subagent")

    def _ts(self) -> str:
        """Current timestamp for summary lines."""
        return datetime.now(timezone.utc).strftime("[%H:%M:%S]")

    def _write_summary(self, line: str) -> None:
        """Write a line to the summary log."""
        if self._summary_file:
            self._summary_file.write(line + "\n")
            self._summary_file.flush()

    def _write_trace(self, data: dict) -> None:
        """Write a JSON event to the trace log."""
        if self._trace_file:
            data["ts"] = datetime.now(timezone.utc).isoformat()
            self._trace_file.write(json.dumps(data, default=str) + "\n")
            self._trace_file.flush()


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    text = text.strip().replace("\n", " ")
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _summarize_tool_input(tool_name: str, input_data: dict) -> str:
    """Create a concise summary of tool input for the summary log."""
    # Agent tool — show which subagent
    if tool_name in ("Agent", "Task"):
        agent = input_data.get("subagent_type", input_data.get("description", "?"))
        return f"agent={agent}"

    # Search tools — show query
    if "query" in input_data:
        return f"query=\"{_truncate(str(input_data['query']), 60)}\""

    # Source eval — show domain
    if "domain" in input_data:
        return f"domain={input_data['domain']}"

    # Diagram — show filename
    if "output_filename" in input_data:
        return f"file={input_data['output_filename']}"
    if "mermaid_source" in input_data:
        return f"mermaid ({len(input_data['mermaid_source'])} chars)"

    # Render tools — show output path
    if "output_path" in input_data:
        return f"path={input_data['output_path']}"

    # Write tool — show file path
    if "file_path" in input_data:
        return f"file={input_data['file_path']}"

    # Fallback — show first key=value
    for key in ("url", "file_path", "path", "title", "pptx_path"):
        if key in input_data:
            return f"{key}={_truncate(str(input_data[key]), 60)}"

    return f"{len(input_data)} params"
