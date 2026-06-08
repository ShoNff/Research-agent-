#!/bin/bash
# SessionStart hook: install dependencies so research-agent + the web app
# can run (tests, linters, CLI) inside Claude Code on the web sessions.
#
# Runs synchronously: the session waits until deps are installed, so the agent
# never races ahead of an unfinished install.
set -euo pipefail

# Only do work in the remote (web) environment; local machines manage their own.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT"

VENV="$ROOT/.venv"

# The system Python on this image is Debian externally-managed, so an editable
# install of the package fights OS-owned packages (e.g. PyJWT). A dedicated
# virtualenv sidesteps that entirely and is cached with the container.
if [ ! -x "$VENV/bin/python" ]; then
  echo "[session-start] creating virtualenv at .venv"
  python3 -m venv "$VENV"
fi

echo "[session-start] installing Python package (editable)"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -e .

# Web app dependencies (Next.js research library). npm install (not ci) so the
# cached node_modules is reused across sessions.
if [ -f "$ROOT/web/package.json" ]; then
  echo "[session-start] installing web dependencies (npm install)"
  npm install --prefix "$ROOT/web" --no-audit --no-fund
fi

# Persist the venv on PATH for the session so `python`, `pip`, and the
# `research-agent` CLI resolve to the virtualenv automatically.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export VIRTUAL_ENV=\"$VENV\""
    echo "export PATH=\"$VENV/bin:\$PATH\""
  } >> "$CLAUDE_ENV_FILE"
fi

echo "[session-start] done"
