Research a topic using the multi-agent research system.

Run the research-agent CLI with the provided topic. Use the --verbose flag to show agent activity. Default output format is markdown.

Usage: /research <topic>

Steps:
1. Run: `research-agent "$ARGUMENTS" --format markdown --style concise -v`
2. If the command is not found, install first: `pip install -e .`
3. The run publishes a project to `projects/<slug>/` (with `manifest.json`). Report the results and the project path. Commit the project folder so it appears in the web library.
