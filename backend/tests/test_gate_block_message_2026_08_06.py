"""PLAIN-LANGUAGE ERRORS + MATERIAL-LIST GATE SPLIT pins (Howard ruled
2026-08-06).

1. NO DEVELOPER LANGUAGE ON SCREEN: no user-facing error string may carry
   a bare HTTP status code, an internal gate/function name, or a stack-
   trace phrase ("render failed"). The code stays in the console/logs.
2. GATE SPLIT: price/labor blockers do NOT stop a materials print (the
   contractor doesn't need his own prices to order material); scope/
   geometry blockers still do. The full quote gate stays on every
   customer surface.
"""
import re
import sys
import asyncio
from pathlib import Path

import pytest

sys.path.insert(0, "/app/backend")

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
GATE_LIB = (FRONTEND / "lib" / "gateMessages.js").read_text()
EDITOR = (FRONTEND / "pages" / "EstimateEditor.jsx").read_text()
ISS = (FRONTEND / "pages" / "ISSEstimateEditor.jsx").read_text()
QUOTE_MODAL = (FRONTEND / "components" / "QuoteModal.jsx").read_text()
FINAL_JOB = (FRONTEND / "components" / "estimate" / "FinalJobSurface.jsx").read_text()
DICTS = (FRONTEND / "lib" / "dictionaries.js").read_text()

FORBIDDEN = ("409", "assert_", "render failed", "request failed",
             "GATE blocked", "QUOTE GATE", "ORDER GATE", "COMPUERTA")


def _user_strings(src):
    """String literals a user can see: toast.error(...), window.alert(...),
    new Error(...), setError(...)."""
    out = []
    for m in re.finditer(
            r'(?:toast\.error|window\.alert|new Error|setError)\(([^)]*)\)', src):
        out.append(m.group(1))
    return out


def test_no_developer_language_reaches_a_user_surface():
    for name, src in (("gateMessages", GATE_LIB), ("EstimateEditor", EDITOR),
                      ("ISSEstimateEditor", ISS), ("QuoteModal", QUOTE_MODAL),
                      ("FinalJobSurface", FINAL_JOB)):
        for lit in _user_strings(src):
            if "console" in lit:
                continue
            for bad in FORBIDDEN:
                assert bad not in lit, \
                    f"{name}: developer language '{bad}' reaches the screen: {lit[:90]}"
            assert not re.search(r'\$\{\s*(?:res|e(?:\.response)?)\.status\s*\}', lit), \
                f"{name}: raw status code interpolated on screen: {lit[:90]}"


def test_error_dictionary_is_plain_both_languages():
    for key in ("err.pdf.generic", "err.gate.quote", "err.gate.materials",
                "err.gate.order", "err.gate.action", "err.gate.more"):
        assert DICTS.count(f'"{key}":') == 2, f"{key} must exist in en AND es"
    for m in re.finditer(r'"err\.[a-z.]+":\s*"([^"]+)"', DICTS):
        val = m.group(1)
        assert not re.search(r"\b[45]\d\d\b", val), f"status code leaked: {val}"
        for bad in ("GATE", "COMPUERTA", "assert_", "render"):
            assert bad not in val, f"developer word '{bad}' leaked: {val}"


def test_status_code_stays_in_the_console():
    assert "console.warn" in GATE_LIB and "res.status" in GATE_LIB, \
        "the code must still be logged for debugging — just never shown"


def test_material_list_sends_its_surface_and_quote_does_not():
    assert 'surface: "material_list"' in EDITOR
    assert 'surface: "material_list"' in ISS
    assert 'surface: "material_list"' not in QUOTE_MODAL, \
        "the quote PDF must keep the full quote gate"


# ---- gate-split behavior (monkeypatched evaluate_gates, no DB) ----
MONEY = [
    {"code": "Cap window", "kind": "labor_pending_row", "label": "LABOR PENDING — Cap window (qty 20)", "blocking": True},
    {"code": "Fascia/rake or frieze", "kind": "unpriced_row", "label": "Unpriced row: Fascia/rake (vinyl)", "blocking": True},
]
SCOPE = [
    {"code": "siding_family_conflict", "kind": "family_conflict", "label": "SIDING FAMILY CONFLICT", "blocking": True},
]


def _run_gate(fn, blocking, monkeypatch):
    import routes.lp_package_routes as lpr

    async def fake_eval(est_id, user):
        return {"quote": {"blocked": bool(blocking), "blocking": blocking}}

    monkeypatch.setattr(lpr, "evaluate_gates", fake_eval)
    return asyncio.run(fn("e1", {"id": "u"}))


def test_money_blockers_do_not_stop_the_material_list(monkeypatch):
    from routes.lp_package_routes import assert_material_list_gate
    assert _run_gate(assert_material_list_gate, MONEY, monkeypatch) is None


def test_scope_blockers_still_stop_the_material_list(monkeypatch):
    from fastapi import HTTPException
    from routes.lp_package_routes import assert_material_list_gate
    with pytest.raises(HTTPException) as ei:
        _run_gate(assert_material_list_gate, MONEY + SCOPE, monkeypatch)
    d = ei.value.detail
    assert ei.value.status_code == 409
    assert d["gate"] == "material_list"
    codes = [b["code"] for b in d["blocking"]]
    assert codes == ["siding_family_conflict"], \
        "only the scope blocker survives the material-list split"


def test_quote_gate_still_blocks_on_money(monkeypatch):
    from fastapi import HTTPException
    from routes.lp_package_routes import assert_quote_gate
    with pytest.raises(HTTPException) as ei:
        _run_gate(assert_quote_gate, MONEY, monkeypatch)
    assert ei.value.status_code == 409
    assert ei.value.detail["gate"] == "quote"


def test_backend_409_body_names_gate_and_blockers():
    src = (Path(__file__).resolve().parents[1] / "routes" / "lp_package_routes.py").read_text()
    for fn in ("async def assert_quote_gate", "async def assert_material_list_gate"):
        body = src.split(fn, 1)[1].split("async def", 1)[0]
        assert '"blocking"' in body and '"label"' in body and '"code"' in body
