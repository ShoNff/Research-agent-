#!/bin/bash
# SessionStart hook for Claude Code on the web.
# Installs Python + web dependencies so the CLI, linters, and the web library
# build are ready before the agent loop starts. Idempotent and non-interactive;
# safe to re-run (pip/npm no-op when everything is already satisfied).
set -euo pipefail

# Only run in remote (Claude Code on the web) sessions — local machines already
# have their own environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# 1. Python package — editable install so `import research_agent` and the
#    `research-agent` CLI work, and ruff can lint the source.
#
#    The base image ships PyJWT via the distro package manager, which pip can't
#    uninstall ("RECORD file not found"). Nothing here needs a newer PyJWT
#    (oauthlib only wants >=2.0.0,<3), so pin it to the installed version to
#    stop pip's resolver from trying to upgrade — otherwise the install aborts.
echo "[session-start] Installing Python package (editable)…"
SYS_PYJWT="$(python -c 'import importlib.metadata as m; print(m.version("PyJWT"))' 2>/dev/null || true)"
if [ -n "$SYS_PYJWT" ]; then
  printf 'PyJWT==%s\n' "$SYS_PYJWT" > /tmp/research-agent-constraints.txt
  pip install -e . -c /tmp/research-agent-constraints.txt
else
  pip install -e .
fi

# 2. Web app — Node deps so `next lint` / `next build` / the library build work.
echo "[session-start] Installing web dependencies…"
cd web
npm install

echo "[session-start] Done."
