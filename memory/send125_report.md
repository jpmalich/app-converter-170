# SEND-125 — CLAIM DISTINCTION RECORDED (no code moved)

Date: 2026-08-24 · pro-quote 8-14-2026

## 1. WHAT THIS SEND DID
Nothing was built, changed, adjusted, or predicted. SEND-125 is a
recording send. No file under /app/backend or /app/frontend was
modified. EST-886440 untouched. Purity pin untouched. fixture_figures.py
untouched (Dart NOT sealed — no figures added).

## 2. THE DISTINCTION, AS RECORDED
Foreign-drafter derivation to date, quantities only:
- Dart:  0 / 4 derived
- Tanis: 0 / 4 derived
Guards fired correctly in every case. No quantity was fabricated.

EARNED CLAIM:
  "It fails safe on unfamiliar sets."

NOT EARNED:
  "It reads unfamiliar sets."

These are different claims. Only the first is currently earned. On a
foreign set the product still returns to CREATION, not CORRECTION.
Recorded not as an argument against the guards — the guards had to come
first — but so the phase AFTER Dart is scored aims at the READ itself,
not at more guards.

## 2b. ENFORCEMENT AUTHORIZED (both (b) and (c))
The distinction is now held by DATA, not by memory.

(c) SCOREBOARD — `/app/backend/foreign_drafter_scoreboard.py`
    Registry of foreign-drafter derived-vs-total: tanis 0/4, dart 0/4
    (dart's scored read still waits on the seal). `earned_claim()`
    COMPUTES the claim from those figures; the read-claim is returned
    only when MORE THAN ONE foreign drafter shows real derivation
    (`MIN_DRAFTERS_DERIVING = 2` — one set deriving is an anecdote, the
    same bar the fixture registry holds Tanis to). Today it returns
    "fails safe on unfamiliar sets". House names are data, as in
    fixture_figures.py.

(b) LEXICAL PIN — `tests/test_send125_claim_distinction_2026_08_24.py`
    Scans /app/memory/*.md, all backend .py and all frontend src for
    assertions of the unearned claim (reads unfamiliar/foreign/unseen,
    generalizes to/across, drafter-agnostic, works on unfamiliar,
    generalization earned). Recording it as NOT earned stays legal: a
    hit must carry a negation marker on its line or within the three
    lines above. In PROMPT constants the phrases are banned OUTRIGHT —
    the model is never told it reads unfamiliar sets. The ban is
    COUPLED to the scoreboard: if the figures ever earn the read-claim,
    `earned_claim()` flips and the ban lifts by itself. Six pins,
    including a self-check that the scan catches a real assertion and
    does not flag a legal recording.

## 3. STATE OF THE PROPERTY
- Fails-safe property: complete pending Dart's scored read (4th house).
- Read property: not started. No guard work is queued to substitute for
  it. Next phase after Dart's score targets extraction, not refusal.

## 4. WHAT HOWARD OWES
Dart's sealed ground truth — widths, depths, heights, opening counts,
projections. On seal: figures enter fixture_figures.py, predictions are
written FIRST, then the scored read.

## 5. HELD / UNAUTHORIZED
- Dart read/prediction — BLOCKED until seal.
- Symbols placement — NOT AUTHORIZED (first job on authorization: Boni's
  two side-entry garage doors on the front).
- Material-card tap-to-confirm write path — awaits 423 ruling.
- Walkout manual-flag entry surface — awaits ruling.
- Catch-all message inventory — still owed by agent.
- rot180 held. CCC unvalidated at n=2.

Standing rules unchanged: no cross-drawing borrowing, no guessing, no
job names in operative code, model heights hypothesis-only.
