---
name: conversation-retrospective
description: >
  End-of-conversation retrospective for the research engine. Reads the current
  conversation, distills the durable preferences, corrections, and conventions the
  user expressed (e.g. "turn the deck sound off by default", "I like shorter
  reports", "always also export a docx", "add a map"), routes each learning to the
  correct source-of-truth file (agent prompts, config defaults, skill internals,
  settings, or CLAUDE.md), and proposes a changeset for approval before editing.
  Approved changes are applied and recorded in an append-only LEARNINGS.md ledger
  so the repo gets permanently smarter and the user never has to repeat themselves.
  Use at the end of a working session, or whenever the user says "remember this",
  "learn from this", "update the repo so I don't have to tell you again", or runs
  /retrospective.
---

# Conversation Retrospective

Turn a finished working session into **durable improvements to the research engine**.

This repo keeps its behavior in a handful of **sources of truth**: agent prompts
(`src/research_agent/prompts/*.py`), defaults (`src/research_agent/config.py`), skill
internals (like the deck audio toggle), harness settings (`.claude/settings.json`), and the
conventions doc (`CLAUDE.md`). When a preference only lives in chat, it's lost at the end of
the session. This skill captures those preferences and writes them back into the right file —
**with your approval** — and logs each one in `LEARNINGS.md`.

You (Claude) already have the conversation in context. **Do not parse transcripts or log
files** — analyze the conversation you just had.

## When to use

- At the **end of a session**, to capture how the user wants things done going forward.
- When the user says "remember this", "learn from this", "make the repo smarter", "update the
  master repo so I don't have to tell you again", or runs `/retrospective`.
- **Automatically after a push or pull request.** A `PostToolUse` hook in `.claude/settings.json`
  detects a `git push` (or a `create_pull_request` / `update_pull_request` action) and injects a
  reminder to run this skill. When triggered that way, work **incrementally** (see step 0): only
  analyze what is new since the last run, and no-op quietly if nothing has changed.

## Workflow

Follow these steps in order. **Never edit a file before the user approves it.**

### 0. Set scope (incremental watermark)

This skill keeps a watermark at `.claude/retrospective-state.json` so repeated runs — e.g. the
automatic trigger on every PR push — only analyze new ground:

```json
{ "last_analyzed_at": "2026-06-08T12:00:00Z", "last_commit": "<sha>" }
```

- If the file is **missing**, analyze the **entire** conversation.
- If it **exists**, only consider conversation that happened **after `last_analyzed_at`**, and in
  all cases skip anything already recorded in `LEARNINGS.md`.
- If nothing new is found, say so in one line and **stop** — do not re-propose old learnings.
- At the **end** of every run (even a no-op), update `last_analyzed_at` to the current time and
  `last_commit` to `git rev-parse HEAD`. This file is git-ignored — it is per-environment state,
  not a shared artifact.

### 1. Extract candidate learnings

Scan the conversation for signals that a *preference or convention* was expressed:

- **Explicit preferences** — "I like X", "always do Y", "default to Z".
- **Corrections** — "don't do that", "off by default", "stop doing X", "that's wrong, do it
  this way".
- **Repeated manual requests** — something the user had to ask for more than once that could be
  a default.
- **Friction / annoyance** — "the sound is annoying", "this is too long", "too many prompts".
- **Decisions about defaults or conventions** — naming, formats, structure, process.

Write each as a one-sentence learning.

### 2. Filter to what's generalizable

Keep only learnings that apply to **future work**. Discard anything specific to a single topic
or report (e.g. "the Azure report's third diagram should be purple" is a one-off; "I prefer
diagrams over prose" is generalizable). This guard keeps prompts and config clean — when in
doubt, ask the user whether a learning is a general rule or a one-off.

### 3. Classify and route each learning

Map each surviving learning to its source of truth using the **Routing Table** below.
**Read the target file first** so the proposed change is precise and minimal — find the exact
default, prompt line, or schema field to change, not a vague "update the prompt".

### Routing Table

| Learning | Source of truth to change |
|---|---|
| Report style / length / tone | `src/research_agent/prompts/writer.py` (style rules) and/or the `writing_style` default in `src/research_agent/config.py` |
| Visuals — diagrams / maps / pictures, how many | `src/research_agent/prompts/visual.py` |
| Deck sound / narration default | `.claude/skills/animated-mermaid-deck/template/deck_engine.js` (`narrationIntended` — controls whether narration plays), the `audio.enabled` field in that skill's `SKILL.md` schema, and the `audio` block in example decks |
| Source-reliability strictness | `src/research_agent/prompts/qa.py`, `src/research_agent/prompts/search.py`, `src/research_agent/tools/source_eval.py` |
| Default formats / models / depth budgets | defaults in `src/research_agent/config.py` (`formats`, `models`, `RunLimits`, `PROFILES`); update `--format`/option help in `src/research_agent/cli.py` to match |
| Workflow / process conventions (phases, ordering, mandatory steps) | `src/research_agent/prompts/orchestrator.py` |
| Harness behavior (hooks, env vars, "stop asking me to confirm X") | **delegate to the `update-config` skill** — it owns `.claude/settings.json`. Do not hand-edit settings here. |
| Reduce permission prompts | **delegate to the `fewer-permission-prompts` skill** |
| New skill / capability the user wants | scaffold `.claude/skills/<new>/SKILL.md` (+ supporting files) and a `.claude/commands/<new>.md` wrapper, mirroring the existing skills |
| Cross-cutting convention / philosophy that isn't a single setting | `CLAUDE.md` |

If a learning is both a behavior change *and* worth documenting, change the behavior file **and**
note the convention in `CLAUDE.md`.

### 4. Present the changeset

Show the user a numbered list. For each item:

1. **Learning** — the one-sentence preference.
2. **Target** — the file (and the specific default / line / field).
3. **Proposed change** — a concrete diff or before→after, minimal.
4. **Rationale** — one line: where in the conversation it came from.
5. **Confidence** — high / medium / low.

Group anything that requires a new file (a new skill, or a settings.json delegated to
`update-config`) and call it out explicitly.

### 5. Get approval

- If any item is ambiguous — could be interpreted multiple ways, is low confidence, or might be
  a one-off — use the **`AskUserQuestion`** tool before touching it.
- Wait for the user to confirm which items to apply. Do not edit until then.

### 6. Apply and record

For each approved item:

1. Make the **minimal** edit to the routed file (or delegate to `update-config` /
   `fewer-permission-prompts`, or scaffold the new skill).
2. **Append an entry to `LEARNINGS.md`** (repo root) using the template below.
3. If a prompt module (`src/research_agent/prompts/*.py`) or any Python file changed, run
   `python -c "import research_agent"` to confirm it still imports.

Then offer to commit the changes on the current development branch.

When a run **applies changes** (learnings, a new skill, config edits), append one row to
`RETROSPECTIVE-LOG.md` (repo root) — time, trigger (`push` / `pull-request` / `manual`), outcome
(e.g. "2 learnings applied: …"), and commit — and commit it alongside those changes. This is the
committed, GitHub-visible activity trail. (The git-ignored `.claude/logs/retrospective-hook.log`
is a separate ephemeral firing log — do not rely on it for the durable record.)

**Loop guard (critical for the push trigger).** On a **no-op run** — nothing new since the
watermark, which is the common case when the trigger was your own administrative/bookkeeping push
— update `.claude/retrospective-state.json` **only**, and **stop without committing or pushing
anything**. Creating a commit and pushing it would re-fire the push hook and loop indefinitely.
Do not append a `RETROSPECTIVE-LOG.md` row for a no-op (the ephemeral firing log already shows the
hook fired). Only ever commit/push from this skill when there is a real, approved learning to
record.

## LEARNINGS.md entry template

Append one block per applied learning, newest at the bottom:

```
## YYYY-MM-DD — <short learning title>
- **Learning:** <what the user prefers / decided>
- **Applied to:** <file(s) changed>
- **Change:** <one-line description of the edit>
- **Rationale:** <why / where in the conversation it came from>
```

## Guardrails

- **Never edit silently.** Propose first, apply only what's approved.
- **One minimal change per learning.** Don't rewrite a whole prompt to encode one preference.
- **Don't pollute prompts with one-offs.** Topic-specific details belong in that project's
  report, not in agent prompts or config.
- **Keep edits reversible** and consistent with surrounding code style.
- **Reuse, don't reinvent.** Harness settings → `update-config`; permission noise →
  `fewer-permission-prompts`. This skill owns prompts, config, skill internals, the ledger, and
  CLAUDE.md.
