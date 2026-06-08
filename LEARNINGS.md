# Learnings Ledger

An append-only record of preferences and conventions the research engine has learned from
conversations and applied back into the repo. Maintained by the `conversation-retrospective`
skill (run it with `/retrospective` at the end of a session).

Each entry records a durable preference, the source-of-truth file it was applied to, and why —
so the repo's behavior and its rationale stay in one auditable place. Newest entries go at the
bottom.

## Entry format

```
## YYYY-MM-DD — <short learning title>
- **Learning:** <what the user prefers / decided>
- **Applied to:** <file(s) changed>
- **Change:** <one-line description of the edit>
- **Rationale:** <why / where in the conversation it came from>
```

---

<!-- New learnings are appended below this line. -->

## 2026-06-08 — Prefer durable, committed, user-visible records over ephemeral ones
- **Learning:** The user wants to see and audit the engine's activity from GitHub or a clone — not just inside the remote sandbox. Git-ignored, sandbox-only artifacts are effectively invisible to them, so observability/records should default to committed-and-visible.
- **Applied to:** `RETROSPECTIVE-LOG.md` (new committed activity trail), `.claude/skills/conversation-retrospective/SKILL.md`, `CLAUDE.md`
- **Rationale:** User asked "where is the log?", then "I don't see a Claude log folder," and chose to add a committed, visible activity log (kept the ephemeral one too).

## 2026-06-08 — Retrospective must not commit/push on no-op runs (loop guard)
- **Learning:** The push-triggered auto-retrospective will loop forever if it commits and pushes on every run, because each push re-fires the hook. No-op runs must update the watermark only and stop.
- **Applied to:** `.claude/skills/conversation-retrospective/SKILL.md` (loop guard in "Apply and record")
- **Rationale:** Observed live — successive bookkeeping pushes each re-triggered the hook during this session.
