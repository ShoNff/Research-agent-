Build a self-contained animated Mermaid HTML presentation from a deck script.

Uses the `animated-mermaid-deck` skill. Given a path to a `*.deck.json` script (or a
request to create one), produce a single portable `.html` that plays like a short movie:
animated text plus a progressively-building Mermaid diagram, with narration and controls.

Usage: /animated-deck <path/to/deck.json>

Steps:
1. If given a script path, build it:
   `python .claude/skills/animated-mermaid-deck/build_deck.py "$ARGUMENTS" --output output/deck.html`
2. If asked to create a new deck, copy `.claude/skills/animated-mermaid-deck/examples/azure_workspaces.deck.json`
   as a starting point, edit the scenes for the requested topic, then build it.
3. Report the output path and how to open it (open the .html and click "▶ Play").

See `.claude/skills/animated-mermaid-deck/SKILL.md` for the deck-script schema and reveal-token reference.
