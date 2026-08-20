"""SEND-71 pins — the straddle ruling (ONE-OFF CLEANUP, registered).

EST-713272 zone 33e4b47a straddles LEFT and RIGHT. Ruled: redrawn as
two zones, NOT forced to one face. Path taken: FLAG ONLY — the app
draws nothing; the zone stops binding; Howard redraws both halves so
their human provenance is earned, not assigned.

REGISTER (Howard, verbatim intent): this is the ONLY genuine straddle
in 52 zones and it PREDATES the SEND-66 FACE_AMBIGUOUS write gate. A
one-off cleanup, NOT a class — nobody builds a splitting feature for a
problem that occurs once.
"""
import sys

sys.path.insert(0, "/app/backend")
from routes.pdf_overlay import apply_overlay_to_takeoff  # noqa: E402

LINE = {"description": "siding line", "qty": 22.0, "raw_qty": 22.0,
        "unit": "SQ", "qty_src": "derived", "section": "siding"}


def _zone(sqft, **kw):
    z = {"id": "z1", "face_id": "right", "material_class": "siding",
         "sqft": sqft, "derived_baseline_qty": 22.0}
    z.update(kw)
    return z


def test_a_suspended_zone_never_enters_the_takeoff_math():
    bound = apply_overlay_to_takeoff([dict(LINE)], [_zone(95.8)])
    assert bound[0]["qty"] != 22.0            # an unflagged zone binds
    flagged = apply_overlay_to_takeoff(
        [dict(LINE)],
        [_zone(95.8, binding_suspended={"code": "FACE_AMBIGUOUS",
                                        "ruling": "SEND-71"})])
    assert flagged[0]["qty"] == 22.0          # a flagged zone does not
    assert flagged[0].get("overlay_sqft") is None


def test_a_suspended_zone_does_not_hold_an_override_alive_on_delete():
    with open("/app/backend/routes/pdf_overlay.py", encoding="utf-8") as f:
        src = f.read()
    assert '"binding_suspended": {"$exists": False}' in src


def test_register_one_off_not_a_class_no_splitting_feature():
    """The app never splits a zone: no code path clips a polygon at a
    band boundary into new zone documents."""
    import glob
    for path in glob.glob("/app/backend/**/*.py", recursive=True):
        if "/tests/" in path:
            continue
        with open(path, encoding="utf-8") as f:
            src = f.read()
        assert "split_zone" not in src and "clip_polygon" not in src, path
