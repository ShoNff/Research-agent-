# Daily Editions

Each day's paper lives in `editions/YYYY-MM-DD/`:

- `edition.json` — the validated edition (the contract; see
  `src/research_agent/models/edition.py`). The web front page and the
  `/paper` archive are built from these by `web/scripts/build-editions.mjs`.
- `edition.md` — the same content as a readable markdown page.
- `logs/` — run traces (git-ignored).

Editions are date-keyed snapshots, not living reports — they are never
revised after publication. They are produced by the `research-paper` CLI
(`src/research_agent/paper.py`), normally via the `daily-paper` GitHub
Actions workflow, which also emails the edition through Resend and commits
the results here. Standing interests, the watch list, and email recipients
are configured in `config/interests.json`.
