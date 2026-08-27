"""RULING Y SYNTHETIC PIN (Howard sealed 2026-08-14 send-23).

The gable/body SPAN DISAGREEMENT — the load-bearing accuracy defect on
EST-713272 RIGHT. A wall segment with a REAL width but a DEAD height:
  - the BODY drops it (body area gates on width AND height),
  - the GABLE keeps it (gable width gates on WIDTH ONLY — the triangle
    above a real-width segment physically exists),
so the two paths span different segments. Ruling Y: do NOT shrink the gable
to match (that would exclude a real width for a height reason and improve
the number by accident — tuning, forbidden). Instead BOTH go PARTIAL and the
difference is NAMED. The gable STAYS as wide as its real widths.
"""
import sys

sys.path.insert(0, "/app/backend")

from measure_staging import GABLE_TRIANGLE_FACTOR, walk_walls  # noqa: E402


def _wall():
    # right-like: main body 2-story (30×20, derivable) + bonus room (9 wide,
    # height dead) + a gable rise. gable width = 30+9 = 39 (both widths real).
    return {"label": "right",
            "gable_triangle_height_ft": 11.4,
            "height_segments": [
                {"label": "main body 2-story", "width_ft": 30.0, "height_ft": 20.0},
                {"label": "bonus room section", "width_ft": 9.0, "height_ft": 0.0},
            ]}


def test_gable_keeps_full_width_body_drops_the_dead_height_segment():
    out = walk_walls([_wall()])
    # gable stays as wide as its REAL widths (30+9=39) — NOT shrunk to 30.
    # NAMED PIN UPDATE (SEND-137, 2026-08-27): the factor is now ½ (the
    # measured triangle) — Ruling Y's intent is UNCHANGED and is what this
    # pin holds: the gable stays as wide as its REAL widths (30+9=39),
    # never shrunk to 30 for a height reason.
    assert round(out["gable_sqft"], 1) == round(
        GABLE_TRIANGLE_FACTOR * 39.0 * 11.4, 1)
    # body counts only the height-derivable segment (30×20 = 600).
    d = out["detail"][0]
    assert sum(sw * sh for sw, sh in d["segments"]) == 600.0


def test_gable_body_span_disagreement_is_named_and_both_partial():
    out = walk_walls([_wall()])
    # BODY partial names the dropped bonus segment.
    body = [f for f in out["faces_not_derivable"]
            if f.get("surface") == "body_segment"]
    assert body and body[0].get("partial") is True
    assert body[0].get("segment") == "bonus room section"
    # GABLE partial names the SPAN difference (Ruling Y).
    gab = [f for f in out["faces_not_derivable"]
           if f.get("surface") == "gable_segment"]
    assert gab and gab[0].get("partial") is True
    assert set(gab[0]["gable_spans"]) == {"main body 2-story", "bonus room section"}
    assert set(gab[0]["body_spans"]) == {"main body 2-story"}
    assert "bonus room section" in gab[0]["reason"]
    assert "height not read" in gab[0]["reason"]


def test_gable_convention_is_labelled_not_a_bare_float():
    # Ruling X req 1: the convention must be NAMED on the surface, never a
    # bare float. NAMED PIN UPDATE (SEND-137): the convention it names is
    # now ½ × width × rise — the 0.70 field factor is retired, and the
    # label must say so where a reader can see it.
    out = walk_walls([_wall()])
    conv = out["detail"][0]["gable_convention"] or ""
    assert "½ × width × rise" in conv
    assert "RETIRED" in conv


def test_agreeing_segments_raise_no_gable_span_flag():
    # main + wing both fully derivable → spans agree → no gable_segment flag.
    w = {"label": "front", "gable_triangle_height_ft": 8.0,
         "height_segments": [
             {"label": "a", "width_ft": 20.0, "height_ft": 9.0},
             {"label": "b", "width_ft": 14.0, "height_ft": 9.0}]}
    out = walk_walls([w])
    assert not [f for f in out["faces_not_derivable"]
                if f.get("surface") == "gable_segment"]
