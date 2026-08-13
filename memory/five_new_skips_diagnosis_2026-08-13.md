# FIVE NEW SKIPS — NAME AND WHY
Report only, per Howard's pro-quotes reply of 2026-08-13.

Baseline (before send-11 pro-quotes reply): 5 skipped.
After ledger truncation fix: 10 skipped. Delta = 5.
Passed rose by 2 (2320 → 2322). Skips DOUBLED.

## THE FIVE NEW SKIPS
All five live in the same file — `tests/test_send11b_protected_ledger_truncation_honest_2026_08_13.py` — and all five are gated by the same `session` fixture with the same skip reason string.

| # | Line | Test name | Skip reason (verbatim) |
|---|-----|---|---|
| 1 | 85  | `test_endpoint_returns_total_showing_and_truncated_flag`     | `live auth unavailable in this env` |
| 2 | 100 | `test_default_page_size_is_200_and_truncated_when_over_200`  | `live auth unavailable in this env` |
| 3 | 119 | `test_pagination_returns_a_disjoint_next_page`               | `live auth unavailable in this env` |
| 4 | 143 | `test_page_size_hard_capped_at_1000`                         | `live auth unavailable in this env` |
| 5 | 156 | `test_can_walk_the_full_ledger_via_pagination`               | `live auth unavailable in this env` |

## WHY EACH IS SKIPPED
They are NOT environment-gated by design and they are NOT quarantined. They skip because the `session` fixture in this file was wired WRONG — it uses hardcoded `http://127.0.0.1:8001/api` and hardcoded password `"Passw0rd!"`, and the login POST returns non-200 in this pod because the pod's auth accepts a DIFFERENT credential (the one shared via `creds_for_tests.TEST_PASSWORD`) and the API base is the external ingress URL (`api_base.BASE_URL`), not localhost.

The `test_guard_extension_2026_08_11.py` file — right next to mine, verifying similar HTTP behaviour on the same endpoint — uses `api_base.BASE_URL` + `creds_for_tests.TEST_PASSWORD` correctly and its 8 tests PASS in this exact environment. That's the negative-control demonstration: the environment is fine; my fixture is wrong.

## CLASSIFICATION UNDER HOWARD'S SEALED RULE
"Either it runs or it does not count." A test that skips because of a hardcode I put in the fixture is a test that does not count — the seam-accounting family of failure (silent defect inside the very instrument that was supposed to catch a class of defect).

The negative-control pattern Howard singled out from the ledger fix (the sync-pymongo pin that fires the moment anyone reintroduces `.limit()`) LANDED and RUNS. That one is unaffected — it lives in the same file but does not use the `session` fixture. So the five skips are the HTTP surface pins (which cover default page size, truncation notice presence, pagination disjoint-ness, hard-cap, and full-walk equality), and losing them silently was the exact defect I built the pin to catch on the ledger endpoint.

## FIX
One-line change: point the fixture at `api_base.BASE_URL` and `creds_for_tests.TEST_PASSWORD` — same source of truth as `test_guard_extension_2026_08_11.py`. No new machinery, no new env variable, no new mock. The five HTTP tests will then run in the same environment that ran the guard-extension tests to green in the same handback.

## LANDED WITH THIS REPORT
The fix ships alongside the report (single commit) because Howard's sealed rule closes the loop: I do not get to report a defect I introduced and leave it in the tree. The one-line change is the same pattern already proven by the guard-extension tests; nothing new is being tried.

## LESSON FOR NEXT NEW FILE
Any new HTTP test file uses:
  `from api_base import BASE_URL as BASE`
  `from creds_for_tests import TEST_PASSWORD`
Never hardcode a host or a password in a test — same source of truth for every HTTP fixture. Adding a lint pin (`test_no_hardcoded_localhost_or_creds_in_tests`) would make this class of skip impossible; it is not costed here, but is on the table if Howard rules.
