#!/usr/bin/env bash
# HANDBACK GREEN GUARD (ruled 2026-07-18, HARDENED same day; RESULT-HARDENED
# by Howard's ruling 2026-07-22): greens must be real by construction.
# HARD-FAILS on a dirty tree — no handback may be stamped, logged, or
# reported while uncommitted changes exist.
# HARD-FAILS on ANY non-green suite result (failures, errors, or an
# unparseable result line) — a stamp is IMPOSSIBLE over a non-green run,
# same absolutism as the dirty-tree rule. (The retired stamp-the-tail
# behavior stamped CLEAN over a 3-fail run on 2026-07-22 and a 6-error run
# on 2026-07-20 — see verification_integrity_register.)
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
if echo "${OUT}" | grep -qE "failed|error" || ! echo "${OUT}" | grep -qE "^[0-9]+ passed"; then
  echo "GUARD HARD-FAIL: SUITE NOT GREEN — nothing stamped, nothing logged."
  echo "RESULT: ${OUT}"
  exit 1
fi
echo "- ${TS} · ${HASH} · CLEAN · [${TARGETS}] · ${OUT}" >> /app/memory/handback_green_log.md
echo "RECORDED: ${TS} · ${HASH} · CLEAN"
echo "RESULT: ${OUT}"
