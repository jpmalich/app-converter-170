#!/usr/bin/env bash
# HANDBACK GREEN GUARD (ruled 2026-07-18): greens must be real by construction.
# Runs the given pytest targets (default: full backend suite) at the CURRENT
# tree, records HEAD hash + dirty-state + result in the handback log.
# A green recorded with a dirty tree is flagged — the handback commit must
# match the run state.
set -u
cd /app
TARGETS="${*:-tests}"
HASH=$(git rev-parse --short HEAD)
DIRTY=""
if ! git diff --quiet || ! git diff --cached --quiet; then
  DIRTY=" · TREE DIRTY AT RUN (hash valid only after auto-commit — re-run if code changed)"
fi
TS=$(date -u +"%Y-%m-%d %H:%M UTC")
cd /app/backend
OUT=$(python3 -m pytest ${TARGETS} -q 2>&1 | tail -1)
echo "- ${TS} · ${HASH}${DIRTY} · [${TARGETS}] · ${OUT}" >> /app/memory/handback_green_log.md
echo "RECORDED: ${TS} · ${HASH}${DIRTY}"
echo "RESULT: ${OUT}"
