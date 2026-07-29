"""LINE-WRITE PATH REGISTER + COUNT-DISPLAY PROVENANCE — sealed by Howard
2026-07-28 (post f3e7d728).

ITEM 1 — "every class killed today is only as dead as the write paths its
detector covers." The autosave-replay clobber (514 lap pieces on a B&B
house) was the PARTIAL-PUT CLOBBER family returning through a door its
detector did not watch: WRITE ORDERING, not partial-field semantics.

THE REGISTER (every path that can persist estimate lines):
  W1 PUT /api/estimates/{id} ......... the ONE generic writer; every UI
       surface funnels here (debounced autosave, explicit Save, Hover
       apply, Blueprint/AI apply, catalog sync, SettingsRow recompute,
       ISS editor, JobInfoPanel). Covered: partial-put clobber class
       (model_fields_set — test_partial_put_clobber_class). NOT covered
       by construction: write ORDERING (last-write-wins on the whole
       lines array) — mitigated by W2/W3 adopt pins below; named
       limitation: two live browser tabs remain last-write-wins.
  W2 POST hover-lp-run ............... server rebuild (routes/hover.py).
       Covered: one-family zeroing, human-qty survival, price
       inheritance pins + ORDERING via the ADOPT pin (caller re-fetches
       server truth so an armed autosave replays the re-derivation).
  W3 POST lp-package/materialize ..... server rebuild (lp_package_routes).
       Covered: apply-gate pins + ADOPT pin (JobInfoPanel update(fresh)).
  W4 lp_admin tier reprice ........... admin-only price rebind on lines.
       Covered: none (admin surface, no concurrent-editor story) — NAMED.
  W5 estimates create / duplicate .... lines written at birth; nothing to
       clobber. Structurally safe.
  W6 demo seed (routes/demo.py) ...... demo estimates only. NAMED.
  W7 services.py startup migrations .. field-scoped array-filter updates
       (lines.$[l].field) — cannot clobber the array. Structurally safe.
  Run-result writers (ai_measure / ai_blueprint / hover worker) write RUN
  docs, never estimate lines — they persist only through W1 applies.

The detector below fails when a NEW estimate-lines writer appears outside
this register, and when a frontend caller of W2/W3 stops adopting.

ITEM 3 — SEALED: any UI element naming a number that feeds a count reads
it FROM THE EMITTER THAT COMPUTED IT — never a family default, never a
local constant, never a remembered value (the toast said 10% while the
B&B field carried 30; that percentage multiplies the counts).
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND = Path("/app/backend")
SRC = Path("/app/frontend/src")

# W-register: files allowed to $set / seed estimate "lines"
LINE_WRITER_REGISTER = {
    "estimates.py",         # W1 PUT + W5 create/duplicate
    "hover.py",             # W2 hover-lp-run rebuild
    "lp_package_routes.py", # W3 materialize rebuild
    "lp_admin.py",          # W4 admin tier reprice — NAMED, uncovered
    "demo.py",              # W6 demo seed — NAMED, demo only
    "services.py",          # W7 startup field-scoped migrations
}

_WRITE_PAT = re.compile(
    r"db\.estimates\.(update_one|update_many|replace_one|insert_one)")


def _estimate_line_writers():
    hits = {}
    for p in sorted(list((BACKEND / "routes").glob("*.py")) + [BACKEND / "services.py"]):
        text = p.read_text()
        for m in _WRITE_PAT.finditer(text):
            # window after the call — does this write touch "lines"?
            window = text[m.start():m.start() + 600]
            if '"lines"' in window or "'lines'" in window or 'est_set' in window:
                hits.setdefault(p.name, 0)
                hits[p.name] += 1
    return hits


def test_w_register_no_unregistered_line_writer():
    writers = _estimate_line_writers()
    rogue = set(writers) - LINE_WRITER_REGISTER
    assert not rogue, (
        "UNREGISTERED estimate-lines writer (write-path register, sealed "
        f"2026-07-28 — register it WITH its clobber coverage): {rogue}")


def test_w2_w3_every_caller_adopts_server_truth():
    """ORDERING coverage: a server-side rebuild's caller must re-fetch and
    adopt the server truth, or an armed debounced autosave replays the
    pre-pick state over the finished rebuild (f3e7d728: lap 514 / B&B 0)."""
    callers = {}
    for p in sorted(SRC.rglob("*.jsx")) + sorted(SRC.rglob("*.js")):
        if "node_modules" in str(p):
            continue
        t = p.read_text()
        if re.search(r"api\.post\(`?/estimates/.*?/(hover-lp-run|lp-package/materialize)", t):
            callers[p.name] = t
    assert callers, "no W2/W3 callers found — scan broken"
    for name, t in callers.items():
        adopts = ("update(fresh)" in t) or ("freshEst" in t)
        assert adopts, (
            f"{name} calls a server-side line writer but never adopts the "
            "server truth — the autosave-replay clobber door is open")


# ── ITEM 3: count-display provenance — the figure a contractor reads is
# the figure the emitter computed. ────────────────────────────────────────
def test_waste_toast_reads_the_emitter_not_the_prefill():
    t = (SRC / "components" / "estimate" / "HoverImportButton.jsx").read_text()
    assert "Waste ${appliedWastePct}%" in t
    assert "Waste ${wastePct}%" not in t          # the 10-vs-30 lie is dead
    assert "appliedWastePct = Number(freshEst.waste_pct" in t


def test_count_display_sources_are_emitter_outputs():
    # recon card preview % = the server-provided prefill, not a local guess
    t = (SRC / "components" / "estimate" / "HoverImportButton.jsx").read_text()
    assert "wastePct={wasteFieldPrefill}" in t
    assert "_waste_field_prefill_pct" in t
    # printed material list % = the estimate field the bake actually applied
    ml = (SRC / "lib" / "materialList.js").read_text()
    assert "Number(estimate.waste_pct)" in ml
    # LP panel chip = the engine's own waste_pct_applied
    lp = (SRC / "components" / "estimate" / "LpMaterialListPanel.jsx").read_text()
    assert "waste_pct_applied" in lp


def test_no_local_family_waste_table_in_frontend():
    """Family waste defaults live in ONE emitter (backend lp_conventions).
    A frontend map re-declaring them is a remembered value that will drift
    and then multiply somebody's counts."""
    pat = re.compile(r"board_batten['\"]?\s*:\s*30|nickel_gap['\"]?\s*:\s*12")
    offenders = []
    for p in sorted(SRC.rglob("*.js*")):
        if "node_modules" in str(p) or ".test." in p.name:
            continue
        for i, ln in enumerate(p.read_text().splitlines()):
            if pat.search(ln) and not ln.strip().startswith(("//", "*")):
                offenders.append(f"{p.name}:{i + 1}")
    assert not offenders, f"local family-waste table declared in UI: {offenders}"


# ── ITEM 2: the epsilon lives IN THE CEIL ITSELF — an integer-landing
# raw × waste comes back as the integer, not integer+1. ──────────────────
def test_integer_landing_never_buys_an_extra_piece():
    from routes.hover import _bake_tab_waste
    # AREA-GOOD probe row (sealed 2026-07-29: length-cut rows take no
    # percentage at all — the epsilon pins ride the vinyl siding shape).
    # 40 × 1.3 = 52.000000000000007 in IEEE754 — the LP B&B panel shape.
    row = {"tab": "vinyl", "section": "Vinyl Siding",
           "name": "Charter Oak lap", "unit": "SQ", "qty": 40.0}
    assert _bake_tab_waste([dict(row)], 30)[0]["qty"] == 52.0   # not 53
    # 100 × 1.1 = 110.000…01 — the 540-trim shape (also pinned in
    # test_one_waste_emitter as the 110.5 regression).
    assert _bake_tab_waste([dict(row, qty=100.0)], 10)[0]["qty"] == 110.0
    # 200 × 1.15 = 229.99999999999997 — noise BELOW the integer must still
    # round UP to it, never down past it.
    assert _bake_tab_waste([dict(row, qty=200.0)], 15)[0]["qty"] == 230.0
    # non-cut-prone branch carries the same epsilon
    coil = {"tab": "vinyl", "section": "Vinyl Accessories",
            "name": ".019 Coil", "unit": "ROLL", "qty": 52.000000000000007}
    assert _bake_tab_waste([dict(coil)], 10)[0]["qty"] == 52.0
    # and the frontend ceil is the same construction (epsilon INSIDE it)
    js = (SRC / "lib" / "wasteLogic.js").read_text()
    assert "Math.ceil(x - 1e-9)" in js
    py = (BACKEND / "routes" / "hover.py").read_text()
    assert py.count("- 1e-9)") >= 2               # both _bake_tab_waste branches


# ── W1 FIELD PRESERVATION (sealed 2026-07-29) ────────────────────────────
def test_w1_put_preserves_derivation_fields_verbatim():
    """THE STRIP CLASS: the EstimateLine whitelist was silently dropping
    `note`, `_waste_included`, `base_item` (+ any future derivation
    field) on EVERY api write — the browser autosave then destroyed the
    waste flags and notes the derivations wrote. Suite green, broken in
    the browser (found on the Casile fixture 2026-07-29). Extra fields
    round-trip verbatim now; this pin fails if the whitelist ever comes
    back."""
    import uuid

    import requests

    from api_base import API
    from creds_for_tests import TEST_EMAIL, TEST_PASSWORD
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    probe = {"tab": "lp_smart", "section": "LP Smart Siding", "name": "probe",
             "unit": "PCS", "qty": 5, "note": "KEEP ME",
             "_waste_included": True, "base_item": "base-x",
             "raw_qty": 4.5, "qty_src": "human", "lab_src": "pending"}
    r = s.post(f"{API}/estimates", json={
        "customer_name": f"TEST_w1strip_{uuid.uuid4().hex[:6]}",
        "kind": "lp_smart", "lines": [dict(probe)]}, timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    try:
        got = s.get(f"{API}/estimates/{eid}", timeout=15).json()
        assert s.put(f"{API}/estimates/{eid}", json=got, timeout=15).status_code == 200
        back = s.get(f"{API}/estimates/{eid}", timeout=15).json()["lines"][0]
        for k in ("note", "_waste_included", "base_item", "raw_qty",
                  "qty_src", "lab_src"):
            assert back.get(k) == probe[k], (
                f"W1 write STRIPPED {k!r}: {back.get(k)!r} != {probe[k]!r}")
    finally:
        s.delete(f"{API}/estimates/{eid}", timeout=15)
