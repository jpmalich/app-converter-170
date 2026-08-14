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
FULL_LOG=/tmp/handback_green_pytest.log
python3 -m pytest ${TARGETS} -q -rs 2>&1 > "${FULL_LOG}"
OUT=$(tail -1 "${FULL_LOG}")
if echo "${OUT}" | grep -qE "failed|error" || ! echo "${OUT}" | grep -qE "^[0-9]+ passed"; then
  echo "GUARD HARD-FAIL: SUITE NOT GREEN — nothing stamped, nothing logged."
  echo "RESULT: ${OUT}"
  # NAME THE FAILURES (Howard ruled 2026-07-29: surface the name on the
  # FIRST failure — an unnameable flake is not investigable).
  echo "FAILED TESTS:"
  grep -E "^(FAILED|ERROR) " "${FULL_LOG}" | sed 's/^/  /'
  grep -E "^(FAILED|ERROR) " "${FULL_LOG}" | sed "s/^/- $(date -u +'%Y-%m-%d %H:%M UTC') · ${HASH} · GUARD-FAIL · /" >> /app/memory/handback_green_log.md
  exit 1
fi
echo "- ${TS} · ${HASH} · CLEAN · [${TARGETS}] · ${OUT}" >> /app/memory/handback_green_log.md
echo "RECORDED: ${TS} · ${HASH} · CLEAN"
echo "RESULT: ${OUT}"

# CENSUS PIN STATUS (Ruling P — green must not read as clean).
if [ -f /app/memory/census_pin_status.txt ]; then
  echo "CENSUS: $(cat /app/memory/census_pin_status.txt)"
fi

# SKIP ROSTER (Ruling O sealed 2026-08-14 send-18): every skip, its ruling
# text, and its age in sends; anything older than three sends names its
# blocker and who owes the unblock. A held ruling must not die unread.
echo "----------------------------------------------------------------------"
python3 scripts/skip_roster.py "${FULL_LOG}"
echo "----------------------------------------------------------------------"

# INGRESS CADENCE (Howard ruled 2026-08-07): the external path a real
# user travels runs before every handback stamp is REPORTED — local
# green without ingress smoke is suite-green/browser-broken wearing a
# performance win. Failure is recorded loudly; the local stamp above
# stands but the handback must report the smoke result verbatim.
SMOKE_LOG=/tmp/handback_external_smoke.log
TEST_API_EXTERNAL=1 python3 -m pytest tests/test_external_smoke_2026_08_07.py -q 2>&1 > "${SMOKE_LOG}"
SMOKE_OUT=$(tail -1 "${SMOKE_LOG}")
if echo "${SMOKE_OUT}" | grep -qE "failed|error"; then
  echo "INGRESS SMOKE FAIL: ${SMOKE_OUT}"
  echo "- ${TS} · ${HASH} · INGRESS-SMOKE-FAIL · ${SMOKE_OUT}" >> /app/memory/handback_green_log.md
  exit 2
fi
echo "- ${TS} · ${HASH} · INGRESS-SMOKE-CLEAN · ${SMOKE_OUT}" >> /app/memory/handback_green_log.md
echo "INGRESS SMOKE: ${SMOKE_OUT}"
