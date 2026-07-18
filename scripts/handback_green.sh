#!/usr/bin/env bash
# HANDBACK GREEN GUARD (ruled 2026-07-18, HARDENED same day): greens must be
# real by construction. HARD-FAILS on a dirty tree — no handback may be
# stamped, logged, or reported while uncommitted changes exist (the retired
# "TREE DIRTY" warning was ignorable; that class of handback-state mismatch
# produced the 6987ffa/128a23c mislabel — see verification_integrity_register).
# Every handback report must quote its recorded log line VERBATIM.
set -u
cd /app
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "GUARD HARD-FAIL: TREE DIRTY — commit first. Nothing stamped, nothing logged."
  git status --short | sed 's/^/  /'
  exit 1
fi
TARGETS="${*:-tests}"
HASH=$(git rev-parse --short HEAD)
TS=$(date -u +"%Y-%m-%d %H:%M UTC")
cd /app/backend
OUT=$(python3 -m pytest ${TARGETS} -q 2>&1 | tail -1)
echo "- ${TS} · ${HASH} · CLEAN · [${TARGETS}] · ${OUT}" >> /app/memory/handback_green_log.md
echo "RECORDED: ${TS} · ${HASH} · CLEAN"
echo "RESULT: ${OUT}"
