"""Per-run tool budget enforcement.

The SDK gives agents agency over how many searches/extractions they perform;
prompts alone can't guarantee an upper bound. This module is the hard stop:
tools check the shared RunBudget before doing work, and once a counter is
exhausted they return a clear "budget exhausted" message instead of calling
out to the network. run_research()/run_paper() reset the budget at the start
of each run with limits from Config.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RunBudget:
    max_searches: int = 25
    max_extracts: int = 12
    searches_used: int = 0
    extracts_used: int = 0
    exhausted_events: list[str] = field(default_factory=list)

    def try_search(self) -> bool:
        if self.searches_used >= self.max_searches:
            self.exhausted_events.append("search")
            return False
        self.searches_used += 1
        return True

    def try_extract(self) -> bool:
        if self.extracts_used >= self.max_extracts:
            self.exhausted_events.append("extract")
            return False
        self.extracts_used += 1
        return True

    def summary(self) -> str:
        return (
            f"searches {self.searches_used}/{self.max_searches}, "
            f"extracts {self.extracts_used}/{self.max_extracts}"
        )


# Module-level budget shared by the search/fetch tools. The MCP tool servers
# run in-process, so a plain module global is visible to every tool call.
_budget = RunBudget()


def get_budget() -> RunBudget:
    return _budget


def reset_budget(max_searches: int, max_extracts: int) -> RunBudget:
    global _budget
    _budget = RunBudget(max_searches=max_searches, max_extracts=max_extracts)
    return _budget


def exhausted_message(kind: str, budget: RunBudget) -> str:
    return (
        f"BUDGET EXHAUSTED: no more {kind}s are available this run "
        f"({budget.summary()}). Do not retry — synthesize your findings from "
        "the material you have already gathered."
    )
