"""REGISTRY-DRIVEN SPEC ROUND-TRIP (Howard RULING 1, 2026-08-06).

The integral-J toggle was the FOURTH per-field pin for a defect that is
not per-field: hand-maintained lists let a brand-new spec slip both the
PUT whitelist and the rederive override list at once. This test walks
EVERY field OFF TRADE_SPEC_FAMILY_REGISTER through the whole pipe —
UI control → PUT whitelist → PUT model → /rederive projection →
/rederive live-override list → a derivation consumer — and fails any
spec control that exists in the UI but is not registered. Nothing added
to the contractor's workflow.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

from lp_conventions import TRADE_SPEC_FAMILY_REGISTER as REGISTER  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"

USE_EST = (FRONTEND / "lib" / "useEstimate.js").read_text()
SETTINGS = (FRONTEND / "components" / "estimate" / "SettingsRow.jsx").read_text()
MODELS = (BACKEND / "models.py").read_text()
HOVER = (BACKEND / "routes" / "hover.py").read_text()
LP_PKG = (BACKEND / "lp_package.py").read_text()

_REDERIVE = HOVER.split('@router.post("/estimates/{est_id}/rederive")', 1)[1]
PROJECTION = _REDERIVE.split("find_one(", 1)[1].split(")", 1)[0]
OVERRIDES = _REDERIVE.split("for k in (", 1)[1].split("):", 1)[0]


def _frontend_blob():
    blobs = []
    for base in ("components", "pages", "lib"):
        for f in (FRONTEND / base).rglob("*.js*"):
            try:
                blobs.append(f.read_text())
            except UnicodeDecodeError:
                pass
    return "\n".join(blobs)


FE_ALL = _frontend_blob()


def test_every_registered_spec_walks_the_whole_pipe():
    for field in REGISTER:
        assert field in FE_ALL, \
            f"{field}: no UI surface references it — the control is gone"
        assert re.search(rf"\b{field}\s*:", USE_EST), \
            f"{field}: buildPayload's PUT whitelist silently strips it " \
            "(the integral-J class)"
        assert field in MODELS, \
            f"{field}: the backend PUT model doesn't declare it"
        assert f'"{field}": 1' in PROJECTION, \
            f"{field}: the /rederive projection doesn't load it — the " \
            "rebuild reads a default instead of the stored spec"
        assert f'"{field}"' in OVERRIDES, \
            f"{field}: the /rederive live-override list ignores the value " \
            "the client just changed (stale-autosave race)"
        # A CONSUMER MUST EXIST (Howard ruled 2026-08-07): lp_soffit_type
        # passed whitelist, model AND override — and was ignored on
        # arrival. Transport is not consumption: the field must be READ
        # by derivation-side code (est.get / a scoped _key), not merely
        # appear in the projection dict or the override tuple.
        consumed = (f'est.get("{field}"' in HOVER
                    or f'est["{field}"' in HOVER
                    or f'"_{field}"' in HOVER
                    or f'"_{field}"' in LP_PKG
                    or f'est.get("{field}"' in LP_PKG)
        assert consumed, \
            f"{field}: the value ARRIVES but nothing consumes it — a " \
            "spec that transports and is ignored is the lp_soffit_type " \
            "class (silent no-op)"


def test_a_spec_control_that_is_not_registered_fails_the_suite():
    """A field that exists but is not registered is the exact hole the
    integral-J toggle fell through — the register is the contract."""
    ui_fields = set(re.findall(r"saveSpec\(\{\s*(\w+):", SETTINGS))
    for known in ("waste_pct", "overhang_in", "porch_ceilings"):
        if known in SETTINGS:
            ui_fields.add(known)
    ui_fields.discard("trigger")
    # PHOTO FILL-INS are measurement gap-fills, not trade specs — they
    # ride their own contract, walked here instead of the register:
    photo_fields = {f for f in ui_fields if f.startswith("photo_")}
    for f in photo_fields:
        assert re.search(rf"\b{f}\s*:", USE_EST), \
            f"{f}: photo fill-in dropped by the PUT whitelist"
        assert f'"{f}": 1' in PROJECTION and f'"{f}"' in OVERRIDES, \
            f"{f}: photo fill-in doesn't ride the rederive pipe"
    ui_fields -= photo_fields
    unregistered = ui_fields - set(REGISTER)
    assert not unregistered, (
        f"spec control(s) in the UI but NOT in TRADE_SPEC_FAMILY_REGISTER: "
        f"{sorted(unregistered)} — register them (families + ruling) or "
        "the next field slips the pipe exactly like windows_integral_j did")


def test_register_entries_carry_families_and_rulings():
    for field, entry in REGISTER.items():
        assert entry.get("families"), f"{field}: families must be NAMED"
        assert entry.get("ruled"), f"{field}: ruling date required"
        if set(entry["families"]) != {"vinyl", "ascend", "lp_smart"}:
            assert entry.get("different_by_nature"), \
                f"{field}: family-specific specs need the DIFFERENT-BY-" \
                "NATURE reason recorded"
