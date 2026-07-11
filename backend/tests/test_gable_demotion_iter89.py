"""Iter 79j.89 — oblique demotion-rule pins (pre-registered, Howard-approved
with 3 edits). Detector pinned against ALL historical admitted-inflation
verbatims and ALL honest cannot-measure nulls. Re-selection: n=1 → value;
n=2 → LOWER + gable_pair_low; n≥3 → lower-median. Never average, never
higher. Zero prompt changes."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    _OBLIQUE_VOCAB_RE, _apply_gable_demotion, _prompt_version_hash,
)

# Every historical admitted-inflation / admits-and-compensates verbatim
# (Letrick 1a/1b/1c/C2 + red house 1c/C2 run docs) — ALL must trip.
ADMITTED_INFLATION = [
    "reads roughly 8-10 in/ft after discounting horizontal foreshortening — best estimate 8/12",
    "rise vs half-span (corrected for the oblique viewing angle compressing the horizontal) reads steep, ~10/12",
    "reads ~8/12 after allowing for mild perspective compression",
    "but horizontal foreshortening inflates the vertical conversion, so true pitch reads closer to 10/12",
    "suggests roughly 8/12, though perspective tilt adds uncertainty",
    "reads roughly 110-130\" after correcting for foreshortening, closest to 8/12",
    "consistent with ~6/12; perspective tilt adds some uncertainty",
    "(~205 px rise over ~230 px foreshortened half-width, corrected for wall angle) gives roughly 8/12",
    "measures near 10/12 after allowing for horizontal foreshortening of the gable plane",
    "the rise measures roughly 8.5-9 ft, \u22487/12; corner foreshortening limits precision",
    "Gable end visible but foreshortened; apparent rise-over-run at the gable reads steep",
    "(~250 px, slightly foreshortened) gives ~9/12 apparent; correcting for perspective compression of the run, 8/12 is the best fit",
    "reads roughly 8/12 despite some perspective tilt",
    "though camera angle foreshortens the right rake so integer confidence is moderate",
    "(~195 px rise vs ~255 px half-run after allowing for the wall's slight angle) gives roughly 7/12",
    "apparent rake angle ~34-38\u00b0 suggests ~8/12, but perspective skew limits precision",
]

# Honest cannot-measure nulls — vocabulary present, NO retained read; the
# detector regex may match the text, but demotion must never fire because
# the numeric-read requirement excludes them (pinned via _apply path).
HONEST_NULLS = [
    "Eave-on view; roof plane is foreshortened toward camera so rise/run cannot be measured from this photo.",
    "No gable face visible (hip roof, straight-on front view); roof slope is foreshortened so rise/run cannot be measured from this photo.",
    "No clean gable-end triangle visible from this angle; both roof planes are foreshortened, so rise/run cannot be measured honestly.",
    "This is an eave-side view; the roof slope is foreshortened toward the camera and no gable triangle is visible, so pitch cannot be measured from this photo.",
    "No gable triangle visible; the low shed roof rising to the clerestory is viewed nearly edge-on and foreshortened, so rise/run cannot be measured honestly.",
]

CLEAN_READS = [
    "Gable end fully visible; triangle rise (~7 ft) versus half-span (~14 ft) yields roughly 6/12.",
    "Gable triangle measured ~89 in rise over ~165 in half-span using the 324-inch wall ref \u2192 \u22486.5/12, closest to 6/12.",
]


def _ex(idx, gable, wall, elev, reasoning, pitch="8/12"):
    return {
        "index": idx,
        "gable_triangle_height_ft_observed": gable,
        "gable_wall_label": wall,
        "elevation": elev,
        "pitch_ratio_observed": pitch,
        "pitch_reasoning": reasoning,
    }


def _final(gables=None):
    walls = []
    for lbl in ("front", "back", "left", "right"):
        w = {"label": lbl, "height_ft": 9.0}
        if gables and lbl in gables:
            w["gable_triangle_height_ft"] = gables[lbl]
        walls.append(w)
    return {"walls": walls}


def _wall(f, label):
    return next(w for w in f["walls"] if w["label"] == label)


def test_prompt_contract_unchanged():
    # 79j.89 is a mechanics candidate — zero prompt changes.
    assert _prompt_version_hash() == "53f2bfa3344b1057"


def test_detector_trips_on_every_historical_admitted_inflation():
    for text in ADMITTED_INFLATION:
        assert _OBLIQUE_VOCAB_RE.search(text), f"detector missed: {text[:80]}"


def test_clean_reads_do_not_trip():
    for text in CLEAN_READS:
        assert not _OBLIQUE_VOCAB_RE.search(text), f"false positive: {text[:80]}"


def test_honest_nulls_never_demote():
    # vocabulary present but no retained numeric read → no demotion, no audit
    f = _final()
    _apply_gable_demotion(f, [
        _ex(0, 0, "left", "front", HONEST_NULLS[0], pitch=None),
        _ex(1, None, "right", "back", HONEST_NULLS[3], pitch=None),
    ])
    assert "_gable_demotion_audit" not in f


def test_admits_and_compensates_demotes_reselect_square_on():
    # canonical p5: oblique 12.5 admitted-inflation vs clean square-on 8.75
    f = _final(gables={"right": 12.5})
    _apply_gable_demotion(f, [
        _ex(5, 12.5, "right", "rear-right", ADMITTED_INFLATION[3], pitch="10/12"),
        _ex(6, 8.75, "right", "right", CLEAN_READS[0], pitch="7/12"),
    ])
    w = _wall(f, "right")
    assert w["gable_triangle_height_ft"] == 8.75
    a = f["_gable_demotion_audit"]["walls"]["right"]
    assert a["rule"] == "single_non_demoted" and a["selected"] == 8.75
    assert any(p["demoted"] for p in a["photos"])


def test_pair_takes_lower_with_flag():
    f = _final(gables={"right": 12.5})
    _apply_gable_demotion(f, [
        _ex(5, 12.5, "right", "rear-right", ADMITTED_INFLATION[1]),
        _ex(6, 9.6, "right", "right", CLEAN_READS[0]),
        _ex(7, 8.75, "right", "right", CLEAN_READS[1]),
    ])
    w = _wall(f, "right")
    assert w["gable_triangle_height_ft"] == 8.75  # LOWER, never average/higher
    assert w["gable_pair_low"] is True
    assert f["_gable_demotion_audit"]["walls"]["right"]["rule"] == "pair_low"


def test_three_plus_takes_lower_median():
    f = _final(gables={"left": 11.0})
    _apply_gable_demotion(f, [
        _ex(1, 11.0, "left", "front-left", ADMITTED_INFLATION[4]),
        _ex(2, 8.5, "left", "left", CLEAN_READS[0]),
        _ex(3, 8.75, "left", "left", CLEAN_READS[1]),
        _ex(4, 9.3, "left", "left", CLEAN_READS[0]),
    ])
    assert _wall(f, "left")["gable_triangle_height_ft"] == 8.75  # sorted[1] of 3


def test_all_demoted_keeps_value_flags_estimated():
    f = _final(gables={"right": 12.5})
    _apply_gable_demotion(f, [
        _ex(5, 12.5, "right", "rear-right", ADMITTED_INFLATION[3]),
        _ex(7, 10.0, "right", "front-right", ADMITTED_INFLATION[6]),
    ])
    w = _wall(f, "right")
    assert w["gable_triangle_height_ft"] == 12.5  # untouched
    assert w["gable_estimated"] is True
    assert f["_gable_demotion_audit"]["walls"]["right"]["rule"] == "all_demoted_estimated"


def test_untouched_wall_left_alone():
    f = _final(gables={"left": 8.8})
    _apply_gable_demotion(f, [_ex(2, 8.8, "left", "left", CLEAN_READS[0])])
    assert _wall(f, "left")["gable_triangle_height_ft"] == 8.8
    assert "_gable_demotion_audit" not in f


# CORPUS MAINTENANCE pins (standing protocol) — each entry logged with
# its source run. #1: red house 32a55599 p3.
MAINTENANCE_ESCAPES = [
    ("32a55599", "Measured rise vs half-span on the visible back gable triangle; "
                 "the gable face is angled away so run is compressed - read as ~10/12 with moderate confidence."),
]


def test_maintenance_corpus_trips():
    for src, text in MAINTENANCE_ESCAPES:
        assert _OBLIQUE_VOCAB_RE.search(text), f"maintenance escape not covered ({src})"


def test_all_demoted_zero_gable_wall_suppresses_cosmetic_flag():
    # Letrick p5 mislabel case: wall="back" carries no gable geometry —
    # the estimated flag is suppressed, the audit records why.
    f = _final()  # back has no gable_triangle_height_ft
    _apply_gable_demotion(f, [
        _ex(5, 11.0, "back", "rear-right", ADMITTED_INFLATION[4], pitch="9/12"),
    ])
    w = _wall(f, "back")
    assert "gable_estimated" not in w
    a = f["_gable_demotion_audit"]["walls"]["back"]
    assert a["rule"] == "all_demoted_estimated"
    assert a["flag_suppressed"] == "no_gable_geometry"


def test_amended_residual_language():
    f = _final(gables={"right": 12.5})
    _apply_gable_demotion(f, [
        _ex(5, 12.5, "right", "rear-right", ADMITTED_INFLATION[3]),
        _ex(6, 8.75, "right", "right", CLEAN_READS[0]),
    ])
    note = f["_gable_demotion_audit"]["residual_note"]
    assert "second net, not a wall" in note and "pinned corpus" in note


def test_residual_logged_openly():
    f = _final(gables={"right": 12.5})
    _apply_gable_demotion(f, [
        _ex(5, 12.5, "right", "rear-right", ADMITTED_INFLATION[3]),
        _ex(6, 8.75, "right", "right", CLEAN_READS[0]),
    ])
    assert "admitted inflation only" in f["_gable_demotion_audit"]["residual_note"]