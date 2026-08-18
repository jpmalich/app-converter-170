"""SEND-48 pins — Ruling YY (structural inset-title test) and the ruled
contested-heights language.

YY: a duplicate face title competes ONLY if its band holds FIRST FLOOR +
TOP OF PLATE datum lines and vertical rails. Empty-band titles (insets/
references) are DROPPED with provenance. Qualifying duplicates that agree
corroborate; disagreeing ones refuse naming both pages. A single-title
face always evaluates directly. No sheet-type classification, no job
names, no value filters.
"""
import sys

sys.path.insert(0, "/app/backend")

from height_read import derive_face_heights
from tests.test_height_build_2026_08_18_send47 import (_front_rear_page,
                                                       _label, _rail, _page)

REAL_FRONT = [_label("TOP OF PLATE", 20.0), _rail("9'-1\"", 25.0),
              _label("FIRST FLOOR", 30.0)]


def test_yy_empty_band_title_is_dropped_not_competing():
    ot = {"1": _front_rear_page(REAL_FRONT),
          "9": _page([_label("FRONT ELEVATION", 60.0, x=70.0)])}
    r = derive_face_heights(ot)["front"]
    assert r["status"] == "DERIVED" and r["page"] == "1"
    assert r["dropped_titles"][0]["page"] == "9"
    assert "Ruling YY" in r["dropped_titles"][0]["reason"]


def test_yy_agreeing_duplicate_corroborates():
    ot = {"1": _front_rear_page(REAL_FRONT),
          "9": _page([_label("FRONT ELEVATION", 60.0),
                      _label("TOP OF PLATE", 20.0),
                      _rail("9'-1\"", 25.0),
                      _label("FIRST FLOOR", 30.0)])}
    r = derive_face_heights(ot)["front"]
    assert r["status"] == "DERIVED"
    assert r.get("corroborated_by_pages") == ["9"]


def test_yy_disagreeing_duplicate_refuses_naming_both_pages():
    ot = {"1": _front_rear_page(REAL_FRONT),
          "9": _page([_label("FRONT ELEVATION", 60.0),
                      _label("TOP OF PLATE", 20.0),
                      _rail("8'-1\"", 25.0),
                      _label("FIRST FLOOR", 30.0)])}
    r = derive_face_heights(ot)["front"]
    assert r["status"] == "REFUSED"
    assert "pages 1, 9" in r["refusal"] and "do not agree" in r["refusal"]


def test_yy_never_drops_a_single_title_face():
    # missing FIRST FLOOR: the face still refuses on ITS OWN gap, it is
    # not dropped as a non-source (YY applies to duplicates only)
    ot = {"1": _front_rear_page([_label("TOP OF PLATE", 20.0),
                                 _rail("9'-1\"", 25.0)])}
    r = derive_face_heights(ot)["front"]
    assert "no FIRST FLOOR datum located" in r["refusal"]


def test_ruled_contested_language_verbatim():
    ot = {"1": _front_rear_page([
        _label("TOP OF PLATE", 20.0),
        _rail("9'-1\"", 25.0, x=6.0), _rail("9'-11\"", 25.0, x=60.0),
        _label("FIRST FLOOR", 30.0)])}
    r = derive_face_heights(ot)["front"]
    assert r["refusal"] == (
        "Two different wall heights found on this elevation (9'-1\" and "
        "9'-11\"). This usually means the front and rear plate heights "
        "are different (common with cut-short side gables or stepped "
        "foundations). Please verify or draw a zone.")


def test_no_job_names_in_height_read_source():
    src = open("/app/backend/height_read.py").read().lower()
    assert "boni" not in src and "letrick" not in src
