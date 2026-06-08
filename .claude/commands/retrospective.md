Capture preferences and conventions from this conversation back into the repo.

Runs an end-of-conversation retrospective: distills the durable preferences, corrections, and
conventions you expressed (e.g. "deck sound off by default", "shorter reports", "always export a
docx"), routes each to the right source-of-truth file, and **proposes a changeset for your
approval before editing anything**. Approved changes are applied and logged in `LEARNINGS.md`.

Usage: /retrospective [optional focus, e.g. "just the deck preferences"]

Steps:
1. Use the `conversation-retrospective` skill on the current conversation.
2. If a focus is given in "$ARGUMENTS", scope the retrospective to that area; otherwise review
   the whole session.
3. Present the proposed changes for approval, apply the approved ones, and append them to
   `LEARNINGS.md`.

See `.claude/skills/conversation-retrospective/SKILL.md` for the routing table and the workflow.
