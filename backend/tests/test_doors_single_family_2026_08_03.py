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


# ─── LINE-SURFACE PINS (Howard ruled 2026-08-04) ─────────────────────────
# "The single-family rule covers the LINE RESTORE, not just estimate
# creation." The 2026-08-03 pins above watched creation while the Hover
# door's restore sat one click from landing 87 cross-family lines on an
# LP estimate — the whole-units lesson again. These pins live ON the
# line surface: every door's apply filter, both directions, plus a live
# DB invariant that fails if any cross-family restore ever lands.

def _door(name):
    return (FE / "components" / "estimate" / name).read_text()


def test_hover_door_has_the_cut_and_single_family_tabs():
    src = _door("HoverImportButton.jsx")
    assert "applicableRestoreLines" in src, "hover apply lost the family filter"
    assert 'if (k === "lp_smart") return [];' in src, \
        "THE CUT left the hover door — lp_smart must merge no composition lines"
    assert "SIDING_TABS" not in src, \
        "hover door builds its own tab set again instead of the shared filter"


def test_preview_and_apply_count_read_the_same_filter():
    """The modal never advertises lines the apply must not land — the
    '87 lines' over-count was the visible half of the bug."""
    src = _door("HoverImportButton.jsx")
    assert "Auto-generated Line Items ({applicableRestoreLines(" in src
    assert "Apply ${applicableRestoreLines(" in src
    assert "Apply ${result.lines?.length" not in src


def test_blueprint_door_keeps_the_cut_and_sheds_pairing_residue():
    src = _door("BlueprintMeasureButton.jsx")
    assert 'srcKind === "lp_smart"' in src and "? []" in src, \
        "blueprint door lost THE CUT"
    for residue in ("wastedPaired", "pairedLines"):
        assert residue not in src, f"retired pairing residue {residue} regrew"
    assert "wastedPaired" not in _door("HoverImportButton.jsx").replace(
        "residue (pairedLines/wastedPaired) is gone", "")


def test_photo_door_scopes_families_at_the_merge():
    src = (FE / "components" / "estimate" / "JobInfoPanel.jsx").read_text()
    assert 'SIDING_TABS = new Set(["vinyl", "ascend"])' in src, \
        "photo-door merge lost its family scoping"
    assert "lp-package/materialize" in src, "photo-door LP cut lost its engine door"


def test_lp_materialize_doors_scope_through_the_one_copy():
    """THE SECOND RE-CONTAMINATION PATH (found 2026-08-04, suite run):
    rebuild_lp_tab_lines emits EVERY tab; /rederive filtered but
    hover-lp-run and lp-package/materialize wrote the rebuild WHOLESALE —
    every materialize re-landed vinyl/ascend rows on the LP estimate
    (Jon Casile, EST-536665 live). All three doors must scope through
    the ONE COPY (scope_to_lp_family), never a wholesale write."""
    hover_src = (BE / "hover.py").read_text()
    assert "def scope_to_lp_family" in hover_src, "the one-copy scoping helper is gone"
    assert hover_src.count("scope_to_lp_family(") >= 3, \
        "hover.py must define + use the scoper at BOTH its doors (rederive, hover-lp-run)"
    assert 'est_set["lines"] = rebuilt_lines' in hover_src and \
        "scope_to_lp_family(rebuilt_lines" in hover_src, \
        "hover-lp-run writes the rebuild wholesale again"
    lp_src = (BE / "lp_package_routes.py").read_text()
    assert "scope_to_lp_family(tab_lines" in lp_src, \
        "lp-package/materialize writes the rebuild wholesale again"


def test_no_estimate_carries_cross_family_lines():
    """LIVE INVARIANT — the pin that would have been red while Howard
    looked at the modal. Any restore that lands a wrong-family line on
    any estimate turns this red: the siding families (vinyl/ascend/
    lp_smart) and windows never cross kinds. The ISS gutter tab is a
    SERVICE overlay, not a siding family — outside the 2026-08-04
    ruling, so not scanned here."""
    import os
    from pymongo import MongoClient
    from dotenv import dotenv_values
    env = dotenv_values("/app/backend/.env")
    db = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
    offenders = []
    for e in db.estimates.find({}, {"estimate_number": 1, "kind": 1, "lines": 1}):
        kind = e.get("kind") or "siding"
        for l in e.get("lines") or []:
            tab = l.get("tab") or "vinyl"
            if (l.get("qty") or 0) <= 0:
                continue
            if l.get("cross_family_flag"):
                # typed-dollar survivors restored under Howard's guard
                # ("flag it for me, do not silently delete it") — visible,
                # awaiting his ruling, never a silent pass for new lines
                continue
            bad = (
                (kind == "lp_smart" and tab in ("vinyl", "ascend", "windows"))
                or (kind == "windows" and tab in ("vinyl", "ascend", "lp_smart"))
                or (kind == "siding" and tab == "lp_smart")
            )
            if bad:
                offenders.append((e.get("estimate_number"), kind, tab, l.get("name")))
    assert not offenders, \
        f"cross-family lines landed on {len(offenders)} row(s): {offenders[:8]}"
