"""INTEGRAL-J TOGGLE WIRING pins (Howard reported 2026-08-06: "the toggle
I built specifically for this house fails on this house").

ROOT CAUSE — the F2 silent-strip class, BOTH halves at once:
1. frontend buildPayload's PUT whitelist dropped windows_integral_j — the
   checkbox toasted "Saved" but the flag never persisted;
2. the /rederive live-override list ignored it — the rebuild always
   derived with the flag OFF from the (never-updated) stored doc.
Net: the toggle no-oped and any transient failure surfaced only the
generic fallback. The derivation itself was always correct (pinned in
test_boni_rulings_2026_08_05: flag touches exactly four lines).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
USE_EST = (FRONTEND / "lib" / "useEstimate.js").read_text()
SETTINGS = (FRONTEND / "components" / "estimate" / "SettingsRow.jsx").read_text()
API_LIB = (FRONTEND / "lib" / "api.js").read_text()
DICTS = (FRONTEND / "lib" / "dictionaries.js").read_text()
HOVER = (Path(__file__).resolve().parents[1] / "routes" / "hover.py").read_text()


def test_put_whitelist_carries_the_integral_j_flag():
    """buildPayload must send windows_integral_j — the F2 silent-strip
    half that made the toggle lose its state on every save."""
    assert re.search(r"windows_integral_j:\s*source\.windows_integral_j", USE_EST), \
        "buildPayload dropped windows_integral_j — the toggle never persists"


def test_rederive_override_list_accepts_the_flag():
    """The spec-save race guard: the client passes the flag it just
    flipped so the rebuild never reads the stale stored value."""
    loop = HOVER.split('@router.post("/estimates/{est_id}/rederive")', 1)[1]
    override_block = loop.split("for k in (", 1)[1].split("):", 1)[0]
    assert '"windows_integral_j"' in override_block, \
        "/rederive ignores the windows_integral_j the client just flipped"


def test_toggle_rederive_failure_speaks_contractor_language():
    """A failed line-rebuild after a spec save must tell the contractor
    what happened and what to do — never fail silently, never dev-speak."""
    assert 't("err.spec.lines")' in SETTINGS, \
        "spec-save rederive failure no longer surfaces a plain-language toast"
    assert DICTS.count('"err.spec.lines":') == 2, \
        "err.spec.lines must exist in en AND es"


def test_generic_fallback_is_actionable_not_vague():
    assert "Something went wrong" not in API_LIB, \
        "the vague fallback is back — say what to do instead"
    assert "check your connection" in API_LIB


def test_validation_reject_logs_field_and_layer_server_side():
    """RULING 3 (2026-08-06): better copy did not fix the blindness — a
    failing PUT names which field, which validation, which layer, in the
    SERVER log only. Nothing contractor-visible."""
    import asyncio
    from fastapi.exceptions import RequestValidationError
    from server import _log_validation_reject

    class _Url:
        path = "/api/estimates/x"

    class _Req:
        method = "PUT"
        url = _Url()

    exc = RequestValidationError(
        [{"loc": ("body", "waste_pct"), "msg": "Input should be a valid number"}])
    import logging as _logging
    records = []

    class _Grab(_logging.Handler):
        def emit(self, r):
            records.append(self.format(r))

    h = _Grab()
    _logging.getLogger().addHandler(h)
    try:
        resp = asyncio.run(_log_validation_reject(_Req(), exc))
    finally:
        _logging.getLogger().removeHandler(h)
    assert resp.status_code == 422, "response shape unchanged — log-only"
    blob = "\n".join(records)
    assert "VALIDATION REJECT" in blob
    assert "waste_pct" in blob and "layer=pydantic-request" in blob


def test_zeroed_cap_window_survives_the_put_filter():
    """RULING 2 (2026-08-06) — THE QTY-0 FILTER DIES EVERYWHERE: any line
    a spec correctly drives to zero prints at 0 with its note (not a
    Cap-window exception). Only bare note-less catalog rows still drop."""
    assert re.search(r'\(l\.note \|\| ""\)\.trim\(\)', USE_EST), \
        "buildPayload's qty-0 filter eats zeroed rows that carry a note"


def test_derivation_moves_the_four_ruled_lines():
    """End-to-end at the derivation layer: flag ON drops window perimeter
    from J, windows from caulk, the window term from wrap coil, zeroes
    Cap window; flag OFF restores. (Line-level exactness pinned in
    test_boni_rulings_2026_08_05 — this guards the on/off round trip.)"""
    from routes.hover import _build_lines

    m = {
        "siding_with_openings_sqft": 4110, "eaves_lf": 167, "rakes_lf": 118,
        "soffit_overhang_in": 12, "porch_ceiling_sqft": 99,
        "window_count": 22, "door_count": 5, "patio_door_count": 1,
        "garage_door_count": 2,
        "windows": [{"width_in": 36, "height_in": 60}] * 22,
    }
    def _qty(lines, frag):
        return sum(l.get("qty") or 0 for l in lines
                   if frag.lower() in (l.get("name") or "").lower()
                   and (l.get("tab") or "vinyl") == "vinyl")

    off = _build_lines({**m, "_windows_integral_j": False})
    on = _build_lines({**m, "_windows_integral_j": True})

    assert _qty(on, "cap window") == 0, "Cap window must zero when integral-J is ON"
    assert _qty(off, "cap window") > 0
    assert _qty(on, '3/4" j-channel') < _qty(off, '3/4" j-channel'), \
        "window perimeter must leave wall-J when integral-J is ON"
    assert _qty(on, "caulking") < _qty(off, "caulking"), \
        "windows must leave caulk when integral-J is ON"
    # OFF again is byte-identical to never having toggled
    off2 = _build_lines({**m, "_windows_integral_j": False})
    assert off == off2, "toggling back OFF must restore the exact derivation"
