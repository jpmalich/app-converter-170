"""GATE-BLOCK MESSAGE pins (Howard, 2026-08-06): when a gate 409s the
material-list PDF, the message must NAME the blockers — "PDF render
failed: 409" with no explanation is the defect (the block itself is
fine). The backend 409 body already ships {gate, blocking:[{code,label}]}
(assert_quote_gate); the frontend must surface it.
"""
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"

GATE_LIB = (FRONTEND / "lib" / "gateMessages.js").read_text()
EDITOR = (FRONTEND / "pages" / "EstimateEditor.jsx").read_text()
ISS = (FRONTEND / "pages" / "ISSEstimateEditor.jsx").read_text()
DICTS = (FRONTEND / "lib" / "dictionaries.js").read_text()


def test_both_editors_surface_the_gate_body_not_the_status_code():
    for name, src in (("EstimateEditor", EDITOR), ("ISSEstimateEditor", ISS)):
        assert "gateBlockMessage(res, t)" in src, f"{name} lost the named gate message"
        assert "PDF render failed: ${res.status}" not in src, \
            f"{name} regressed to the bare status-code throw"


def test_gate_message_names_blockers_dedupes_and_caps():
    assert 'd?.gate && Array.isArray(d.blocking)' in GATE_LIB
    assert "seen.has(k)" in GATE_LIB, "duplicate blocker codes must collapse"
    assert "slice(0, 3)" in GATE_LIB, "long blocker lists cap at 3 + '+n more'"
    assert 'msg = `PDF render failed: ${res.status}`' in GATE_LIB, \
        "non-gate failures keep the status fallback"


def test_gate_message_is_translated_both_languages():
    assert DICTS.count('"ml.gate.blocked":') == 2, "ml.gate.blocked must exist in en AND es"
    assert DICTS.count('"ml.gate.more":') == 2


def test_backend_409_body_names_gate_and_blockers():
    """The contract the frontend relies on: assert_quote_gate ships
    gate + blocking[{code,label}] in the 409 detail."""
    src = (Path(__file__).resolve().parents[1] / "routes" / "lp_package_routes.py").read_text()
    gate_fn = src.split("async def assert_quote_gate", 1)[1].split("async def", 1)[0]
    assert '"gate": "quote"' in gate_fn
    assert '"blocking"' in gate_fn and '"label"' in gate_fn and '"code"' in gate_fn
