# Retrospective Activity Log

A chronological, **committed** record of every `conversation-retrospective` run — including
no-ops — so you can see, from GitHub or any clone, when the engine reflected on a session and
what it did. Written by the `conversation-retrospective` skill at the end of each run.

- **This file** = the run-by-run activity trail (when it fired, what triggered it, the outcome).
- **`LEARNINGS.md`** = the detailed ledger of *applied* learnings (what actually changed, and where).
- **`.claude/logs/retrospective-hook.log`** = an ephemeral, git-ignored per-session firing log for
  in-session debugging only (not visible outside the sandbox; cleared when the container is reclaimed).

| When (UTC) | Trigger | Outcome | Commit |
|---|---|---|---|
| 2026-06-08T19:20Z | push | No-op — building the retrospective feature; nothing to capture | 4994b60 |
| 2026-06-08T20:02Z | push | No-op — adding the firing log; nothing to capture | 0358c52 |
| 2026-06-08T20:05Z | manual | Added this committed activity log (RETROSPECTIVE-LOG.md) per user request for a visible trail | 346f989 |
| 2026-06-08T20:08Z | push | 1 learning applied: prefer durable/committed/visible records over ephemeral ones (see LEARNINGS.md) | _this commit_ |
