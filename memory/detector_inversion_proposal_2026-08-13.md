# REMOVAL-SHAPE DETECTOR — INVERSION PROPOSAL
Report only, requested with the SEND-11 handback. No build.

Howard's ruling (2026-08-13): "Enumerating removal shapes keeps
losing to the next shape. Three for three. I am not ordering a
fourth patch. Propose an inversion and report it — I want to know
whether the detector can be turned around so that a data path
DECLARES what it returns whole, rather than the detector guessing
at every way a thing can be cut."

## THE THREE SHAPES SO FAR
 1. FILTERING COMPREHENSIONS — `[x for x in xs if cond]`. Caught by
    `test_seam_accounting_2026_08_09.py`'s AST walker (list-comp
    with an `if` clause over any WATCHED collection name).
 2. SLICES / min(len()) CAPS — `xs[:N]`, `xs[:min(len(xs), N)]`.
    Widened into the same detector after the page-cap miss (send-7).
 3. DB `.limit()` — the shape that just landed the protected-ledger
    truncation defect. The AST walker cannot see it: `.limit()` is
    a chained call on a motor cursor, not a comprehension, not a
    subscription slice, not a `min()` cap. It is arbitrary attribute
    syntax that happens to mean "truncate".

The pattern is now clear: **the detector is chasing SYNTACTIC
shapes across a Turing-complete language**. Every new way to remove
data is a new shape and the detector arrives after the miss.

## THE INVERSION — FEASIBILITY: YES, WORTH IT: YES
### Core idea
Stop asking "what shapes might cut data?". Start asking:
**"for every data path that leaves a boundary, is the count that
went out equal to the count that could have gone out?"**

The instrument becomes a WHOLENESS CONTRACT at the boundary, not a
shape catalog inside the function. A boundary is any place data
crosses out of the process into a consumer that cannot see the
producer's internal state:
  - HTTP response body → API consumer
  - Mongo read result → an in-process aggregator
  - JSON serialization → disk / another process
  - IPC / job payload → a worker

Every boundary crossing carries, alongside the payload:
  - `emitted` — count of records the payload actually contains
  - `available` — count of records the source had (honestly)
  - `truncated` — bool; ledgered when true
  - `truncation_reason` — enum: `explicit_paginate | cap | filter |
    schema_project | none`
  - `filter_names` — every named filter the payload passed through
    (each name is a REGISTERED SEAM in `seam_accounting`)

A payload that reaches a boundary WITHOUT these fields is a
protocol violation — the boundary decorator (see below) raises.

### Where the contract lives
Not in the caller. Not in the callee. In the **shared boundary
carrier** — a lightweight envelope every crossing wraps its data
in. Adopting it is intrusive but bounded: FastAPI response models,
Mongo repository helpers, and job payload schemas are the only
producers that matter. Each of those is a handful of files, not a
whole codebase.

### The four instruments the inversion buys
 1. **DECLARATIVE COMPLETENESS at the boundary.** A caller reads
    `.total`, `.emitted`, `.truncated` and knows without inspecting
    the producer. The protected-ledger fix is already this shape —
    generalise it, don't repeat it 40 times.
 2. **BUILD-FAIL on missing declaration.** A new endpoint whose
    response type is not `Envelope[T]` fails the schema-consumer
    test the same way an unregistered seam already fails
    `test_seam_accounting`. The AST walker becomes an ADAPTER
    LOOKING AT THE BOUNDARY, one shape (missing declaration), not
    thirty (every possible way to cut).
 3. **RUNTIME CROSS-CHECK on every response.** A middleware / model
    validator computes `available - emitted` from the query the
    producer names and asserts it matches the declared numbers.
    Cheap sanity, catches the case where the producer says "total
    247" and returns 250 rows (or vice versa).
 4. **SEAM LEDGER FED AUTOMATICALLY.** Every truncated boundary
    crossing appends to `_seam_ledger` on the way out. The registry
    stops being a manual afterthought; the boundary IS the ledger.

### Costed at MUV size
 - `envelope.py` (backend): `Envelope[T]` pydantic model + decorator
   that wraps a repository read into the model. Files touched: 1
   new file + ~10 lines each in `db.py` and `server.py` middleware.
 - `RepositoryReader` helper — a thin wrapper around motor queries
   that carries `available` (count_documents) alongside the cursor
   walk. Replaces the raw `db.X.find(...).limit(...)` pattern used
   in 40-ish read endpoints. Files touched: refactor 40 read
   endpoints. Each refactor is 4-6 lines.
 - `EnvelopeAdapter` for JSON exports (CSV/tape-check/etc). 1 new
   helper + 5-6 call sites.
 - Tests: adapt `test_schema_consumer_keys` and
   `test_seam_accounting` to look at boundaries instead of shapes.
   Net-neutral test count; ~50 lines of pin churn.

**Sessions**: ~2.5 to land the envelope + refactor the 40 read
endpoints + retire the AST shape-walker.

### Why this is worth it (Howard's rubric)
 - The AST detector is at 3 shapes and losing. The 4th shape will
   be `agg().project()` or `find_one_and_update({...})` or an
   iterator that quits early. The catalog grows without bound.
 - The BOUNDARY is where honesty lives. The seam-accounting rule
   already implies this: "any layer that truncates must account
   for what it removed." Making the boundary refuse an un-accounted
   crossing is the same rule at compile-time, not run-time.
 - The protected-ledger endpoint just SHOWED the shape works. The
   inversion is generalising the fix, not inventing a new class.

### Where the inversion falls short
 - It only sees CROSSINGS. A filter inside a function whose output
   never leaves the boundary — an intermediate rewrite of `walls`,
   for instance — is invisible to this instrument. That class stays
   with the AST walker, and the walker gets simpler because it
   only has to look at internal writes, not boundary crossings.
   Net result: two instruments, one shape each, instead of one
   instrument chasing every shape.
 - Some boundaries are legitimately partial (a paginated list is
   truncated on purpose). The envelope handles this: `truncated =
   true` + `truncation_reason = explicit_paginate` is honest. The
   contract is not "never truncate", it is "never truncate silently".
 - The refactor touches every read endpoint. Not a small edit.
   Callable as one session but visible to the reviewer.

## VERDICT
**Feasible. Worth it. ~2.5 sessions.** The inversion turns the
catalog problem (chasing shapes) into a declaration problem
(refuse un-declared crossings), which is the same move
`seam_accounting.SEAM_REGISTRY` already made for INTERNAL removals
and the same move `test_normalizer_registry` already made for
per-field normalization. This is the third instance of the same
turn, and each earlier one held.

## RECOMMENDED NEXT STEP
Prototype `Envelope[T]` + one refactor (the ledger endpoint we
just fixed) in isolation. Verify the contract holds on the smallest
producer→consumer pair; if it does, the 40-endpoint refactor is
mechanical. If it does not, the inversion has a bug and I want to
know before ordering the ~2.5 sessions of build.

Awaiting the ruling.
