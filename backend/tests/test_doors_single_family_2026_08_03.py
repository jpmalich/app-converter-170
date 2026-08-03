"""DOORS ARE SINGLE-FAMILY AND ESTIMATES ARE SELF-CONTAINED (Howard ruled
2026-08-03). REGISTERED: cross-family fill is post-September.

The blank-seeding class dies by construction: this detector fails the
build if any door creates more than one estimate, or if any
estimate-creation path reads from another estimate."""
import re
from pathlib import Path

FE = Path("/app/frontend/src")
BE = Path("/app/backend/routes")

DOOR_FILES = [
    FE / "components/estimate/HoverImportButton.jsx",
    FE / "components/estimate/BlueprintMeasureButton.jsx",
    FE / "components/estimate/PhotoMeasureButton.jsx",
]

PAIR_CALL = re.compile(r"/estimates/\$\{[^}]+\}/pair(-lp)?`")


def test_no_door_writes_a_second_estimate():
    """A door writes ONLY its own estimate: no pair call, no POST that
    creates a sibling. Scanned on every door file."""
    for p in DOOR_FILES:
        src = p.read_text()
        assert not PAIR_CALL.search(src), f"{p.name} pairs a sibling estimate"
        creates = re.findall(r'api\.post\(\s*[`"\']/estimates[`"\']', src)
        assert not creates, f"{p.name} creates an estimate from inside a door"


def test_no_frontend_code_calls_the_pairing_api():
    for p in FE.rglob("*.jsx"):
        src = p.read_text()
        assert not PAIR_CALL.search(src), f"{p} calls the retired pairing API"
        assert "pair-lp" not in src, f"{p} references the retired pair-lp flow"


def test_backend_has_no_pairing_routes():
    for p in BE.glob("*.py"):
        src = p.read_text()
        assert '"/estimates/{est_id}/pair"' not in src, f"{p.name}: /pair route back"
        assert '"/estimates/{est_id}/pair-lp"' not in src, f"{p.name}: /pair-lp route back"


def test_no_creation_path_writes_pair_pointers():
    """No estimate-creation path stamps a cross-estimate pointer — the
    self-contained rule holds at the write site."""
    for p in BE.glob("*.py"):
        src = p.read_text()
        for field in ("paired_estimate_id", "paired_lp_estimate_id"):
            assert f'"{field}":' not in src, \
                f"{p.name} writes {field} — an estimate is binding to a neighbor"
            assert f'"{field}": 1' not in src, \
                f"{p.name} projects {field} — a reader is growing back"


def test_no_derivation_reads_a_paired_estimate():
    """PURITY (sealed, re-enforced on the doors 2026-08-03): no run
    loader or composition path consults a sibling estimate — scanned
    comment-blind on the code, not the prose."""
    src = (BE / "lp_package_routes.py").read_text()
    region = src.split("def _geometry_basis")[0]
    code = re.sub(r'""".*?"""', "", region, flags=re.S)
    code = re.sub(r"^\s*#.*$", "", code, flags=re.M)
    assert "paired" not in code, \
        "_load_run region references paired estimates again"


def test_ruling_is_registered():
    src = (BE / "estimates.py").read_text()
    assert "cross-family fill is post-September" in src.lower() or \
        "Cross-family fill is post-September" in src, \
        "the 2026-08-03 registration comment was removed"
