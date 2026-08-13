# BASELINE FIVE SKIPS — NAMED AND EXPLAINED
Report only, low priority, delivered per Howard's pro-quotes reply 3
of 2026-08-13. The rule ("either it runs or it does not count")
applies to ALL skips, not only the ones I introduced. The five that
have lived in the baseline since well before send-11 are named here.

## THE FIVE

| # | File | Line | Test | Skip reason (verbatim) |
|---|-----|-----|---|---|
| 1 | `tests/test_estimator_api.py`             | 147 | `TestCatalogPerCompany.test_catalog_isolated_between_companies` | `Obsolete under iter-6 4-tier architecture: per-company material overrides removed; material is now strictly tier-controlled (PUT /api/catalog only accepts labor overrides).` |
| 2 | `tests/test_external_smoke_2026_08_07.py` | 42  | ingress smoke #1 | `ingress smoke runs on the handback cadence (TEST_API_EXTERNAL=1)` |
| 3 | `tests/test_external_smoke_2026_08_07.py` | 50  | ingress smoke #2 | `ingress smoke runs on the handback cadence (TEST_API_EXTERNAL=1)` |
| 4 | `tests/test_external_smoke_2026_08_07.py` | 59  | ingress smoke #3 | `ingress smoke runs on the handback cadence (TEST_API_EXTERNAL=1)` |
| 5 | `tests/test_external_smoke_2026_08_07.py` | 90  | ingress smoke #4 | `ingress smoke runs on the handback cadence (TEST_API_EXTERNAL=1)` |

## WHY EACH IS SKIPPED, IN PLAIN WORDS

### Skip #1 — `test_estimator_api.py:147` (the iter-6 obsolete pin)
The suite carries a legacy contract for per-company material
overrides — the old shape where a company could override a material's
mat/lab pricing on top of the catalog. Iter-6 killed that (materials
are now strictly tier-controlled; the tier decides, the company
picks a tier). The test predates iter-6. **Kept but skipped as a
tombstone**: it names the old shape so if anyone tries to reintroduce
per-company material overrides, the file is the reminder that we
already ruled against it.

**Rule against silent skips holds**: this skip has a NAMED architectural
reason, not "flaky" or "env-gated." A tombstone that speaks is honest;
a tombstone that hides is not. If Howard prefers, the pin can be
converted to an ASSERTION that the endpoint refuses material overrides
(inverting the tombstone from "we don't test this" to "we prove this
class doesn't exist"). Report-only recommendation: yes, invert. Small
one-session cost. Awaits ruling.

### Skips #2-5 — `test_external_smoke_2026_08_07.py` (ingress smoke, four tests)
These four are the **INGRESS SMOKE** tests — they hit the external
ingress URL (ingress → nginx → gunicorn → FastAPI) to prove the
production routing path works end-to-end. They are gated by the
environment variable `TEST_API_EXTERNAL=1` and run on the **handback
cadence** (the `handback_green.sh` script sets that env var and runs
them once per handback, printing `INGRESS SMOKE: 4 passed in 1.51s`
on the stamp line). Local `pytest tests` does NOT set the env var,
so they skip in isolated runs by design.

**Why gated this way**: hitting the external URL from every dev
`pytest tests` invocation would be network-noisy, slow, and would
double-count on every rapid iteration cycle. The handback is the
"the whole thing is going to Howard" moment, which is exactly when
the external smoke should fire.

**Rule against silent skips holds**: these four skips are
ENVIRONMENT-GATED, and the environment name is on the skip reason
line — no guessing which env, no hidden condition. The handback
stamp Howard sees names the smoke result explicitly ("INGRESS
SMOKE: 4 passed in 1.51s"), so the tests DO run on the visible
cadence they're gated for.

## THREE SHAPES OF SKIP, THREE VERDICTS
 - **Tombstone** (#1) — a defunct contract kept as a
   "do-not-do-this-again" marker. Reasonable IF the message is
   read as a reminder. Better yet: invert it into an assertion
   of the current shape (recommended above).
 - **Cadence-gated** (#2-5) — env-var-driven, runs on the
   handback surface, prints its result on the stamp line. Legit
   under the rule; the cadence IS the "when it runs."
 - **My own five that landed 2026-08-13** — hardcoded-host bug in
   a fixture. **Not legit** and closed in the same commit
   (`c8adc41`).

None of the baseline five falls into the flaky category. That
class is where the rule bites hardest ("either it runs or it does
not count") — the baseline five run when they're supposed to, or
they've been reasoned out of existing. No further action ordered,
per Howard's low-priority framing.

## ONE-LINE HYGIENE RECOMMENDATION
Extend `test_seam_accounting`'s style discipline to skips: every
`pytest.skip(...)` in the suite must name its class in the reason
string (one of `tombstone`, `cadence:<var>`, or `env:<what>`). A
skip whose reason string does not begin with a known class fails
the pin. Report-only; awaits ruling.
