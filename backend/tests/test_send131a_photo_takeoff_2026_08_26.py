"""SEND-131A PINS — PHOTO TAKEOFF PHASE 1 (Howard ruled 2026-08-26).

The contractor marks the PHOTOS. The blueprint discipline carries over
verbatim, and these pins are what holds it:

  1. A PROVISIONAL MARK CARRIES NO QUANTITY — it is listed and named.
  2. THE TAPE WINS over the two-tap anchor on the same span.
  3. NO SCALE = A NAMED REFUSAL, never a 0.
  4. ADJUSTING A CONFIRMED MARK DROPS IT BACK TO PROVISIONAL — a
     confirmation cannot outlive the figure it was given for.
  5. A PHASE-2 KIND IS REFUSED AND NAMED, never guessed.
  6. 423 ON A PROTECTED ESTIMATE for the derived write (apply).
  7. THE ANNOTATION IMPORT IS IDEMPOTENT and lands provisional.
  8. QUANTITY ONLY — no money, no priced line; the photo lane does not
     mix into hover_measurements or any blueprint/derived total.
  9. A LANE WITH NO CONFIRMED MARK OF ITS KIND REPORTS None, NEVER 0.
 10. OPENINGS REPORT SEPARATELY — nothing is deducted in phase 1.

Everything runs over HTTP against a DISPOSABLE estimate; cleanup always
runs. No real estimate is touched.
"""
import re
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API  # env-derived
from creds_for_tests import TEST_PASSWORD

PHOTO = "TEST_send131a_front.jpg"
SRC = Path("/app/backend/routes/photo_takeoff.py")


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": "hhunt6677@yahoo.com",
                     "password": TEST_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip("env:live_auth: test login unavailable")
    return s


@pytest.fixture(scope="module")
def eid(sess):
    r = sess.post(f"{API}/estimates",
                  json={"kind": "lp_smart",
                        "customer_name": "ZZ TEST_send131a-photo-takeoff TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    _id = r.json()["id"]
    yield _id
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"],
                     serverSelectionTimeoutMS=2000)[os.environ["DB_NAME"]]
    db.photo_takeoff_marks.delete_many({"estimate_id": _id})
    db.photo_takeoff_scale.delete_many({"estimate_id": _id})
    db.ai_measure_sessions.delete_many({"estimate_id": _id})
    db.estimates.delete_many({"id": _id})


def _box(x, y, w, h):
    return [{"x": x, "y": y}, {"x": x + w, "y": y},
            {"x": x + w, "y": y + h}, {"x": x, "y": y + h}]


def _get(sess, eid, photo_key=PHOTO):
    r = sess.get(f"{API}/estimates/{eid}/photo-takeoff",
                 params={"photo_key": photo_key}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _qty(sess, eid, photo_key=PHOTO):
    body = _get(sess, eid, photo_key)
    return (body.get("per_photo") or {}).get(photo_key, {}).get(
        "quantities") or {}


def _wipe(sess, eid, photo_key=PHOTO):
    for m in _get(sess, eid, photo_key)["marks"]:
        sess.delete(f"{API}/estimates/{eid}/photo-takeoff/marks/{m['id']}",
                    timeout=15)
    sess.put(f"{API}/estimates/{eid}/photo-takeoff/scale",
             json={"photo_key": photo_key, "clear": True}, timeout=15)


def _add(sess, eid, **kw):
    kw.setdefault("photo_key", PHOTO)
    r = sess.post(f"{API}/estimates/{eid}/photo-takeoff/marks",
                  json=kw, timeout=15)
    return r


def _scale(sess, eid, inches, tape=None, photo_key=PHOTO):
    """A 100 px span. 100 in over 100 px = 1 in per px."""
    r = sess.put(f"{API}/estimates/{eid}/photo-takeoff/scale",
                 json={"photo_key": photo_key,
                       "anchor": {"p1": {"x": 0, "y": 0},
                                  "p2": {"x": 100, "y": 0},
                                  "inches": inches},
                       "tape_inches": tape}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# ── PIN 1 ────────────────────────────────────────────────────────────
def test_a_provisional_mark_carries_no_quantity_and_is_named(sess, eid):
    _wipe(sess, eid)
    _scale(sess, eid, 100.0)
    r = _add(sess, eid, kind="siding_zone", points=_box(0, 0, 120, 120))
    assert r.status_code == 200, r.text
    assert r.json()["mark"]["status"] == "provisional", (
        "a new mark must land PROVISIONAL — it is the contractor's "
        "confirmation that turns geometry into a quantity")
    q = _qty(sess, eid)
    assert q["siding_sqft"] is None, (
        f"a provisional mark fed a quantity: siding_sqft={q['siding_sqft']}")
    assert q["provisional_marks"] == 1
    assert q["confirmed_marks"] == 0
    assert q["provisional_note"] and "NOT CONFIRMED" in q["provisional_note"], (
        "the unconfirmed mark must be NAMED, not silently absent")


# ── PIN 2 ────────────────────────────────────────────────────────────
def test_the_tape_wins_over_the_anchor_on_the_same_span(sess, eid):
    _wipe(sess, eid)
    # anchor says the 100 px span is 100 in; the tape says 200 in.
    _scale(sess, eid, 100.0)
    r = _add(sess, eid, kind="siding_zone", points=_box(0, 0, 120, 120))
    mid = r.json()["mark"]["id"]
    sess.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
               json={"status": "confirmed"}, timeout=15)
    q_anchor = _qty(sess, eid)
    assert q_anchor["scale_basis"] == "anchor"
    assert q_anchor["siding_sqft"] == 100.0, (
        f"anchor basis math moved: {q_anchor['siding_sqft']} (120x120 px "
        "at 1 in/px = 14400 in² = 100 ft²)")
    body = _scale(sess, eid, 100.0, tape=200.0)
    assert body["basis"] == "tape", (
        "WHERE A TAPE IS PRESENT, THE TAPE WINS — the anchor did not "
        "give way")
    q_tape = _qty(sess, eid)
    assert q_tape["scale_basis"] == "tape"
    assert q_tape["siding_sqft"] == 400.0, (
        "the tape doubled the span, so the area must quadruple: got "
        f"{q_tape['siding_sqft']}, expected 400.0")


# ── PIN 3 ────────────────────────────────────────────────────────────
def test_no_scale_is_a_named_refusal_never_a_zero(sess, eid):
    _wipe(sess, eid)
    r = _add(sess, eid, kind="siding_zone", points=_box(0, 0, 120, 120))
    mid = r.json()["mark"]["id"]
    sess.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
               json={"status": "confirmed"}, timeout=15)
    q = _qty(sess, eid)
    assert q["siding_sqft"] is None, (
        "a confirmed mark on an unscaled photo produced a quantity — no "
        "anchor and no tape means NO quantity")
    assert q["siding_sqft"] != 0, "the refusal must never render as 0"
    assert q["scale_basis"] is None
    assert q["scale_refusal"] and "no scale" in q["scale_refusal"].lower(), (
        f"the refusal is not named: {q['scale_refusal']!r}")
    # a tape figure cannot stand without the span it describes
    r = sess.put(f"{API}/estimates/{eid}/photo-takeoff/scale",
                 json={"photo_key": PHOTO, "tape_inches": 120.0}, timeout=15)
    assert r.status_code == 400, (
        "a tape with no two-tap span was accepted — the tape describes "
        "THAT span, it cannot stand alone")


# ── PIN 4 ────────────────────────────────────────────────────────────
def test_adjusting_a_confirmed_mark_returns_it_to_provisional(sess, eid):
    _wipe(sess, eid)
    _scale(sess, eid, 100.0)
    mid = _add(sess, eid, kind="siding_zone",
               points=_box(0, 0, 120, 120)).json()["mark"]["id"]
    sess.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
               json={"status": "confirmed"}, timeout=15)
    assert _qty(sess, eid)["siding_sqft"] == 100.0
    r = sess.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
                   json={"points": _box(0, 0, 240, 240)}, timeout=15)
    assert r.status_code == 200, r.text
    mark = r.json()["mark"]
    assert mark["status"] == "provisional", (
        "the confirmation outlived the figure it was given for")
    assert mark["refused_reason"] and "re-confirm" in mark["refused_reason"]
    q = _qty(sess, eid)
    assert q["siding_sqft"] is None, (
        "the adjusted geometry kept carrying a quantity on the old "
        f"confirmation: {q['siding_sqft']}")


# ── PIN 5 ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("kind", ["j_channel", "outside_corner", "soffit",
                                 "fascia", "starter", "inside_corner",
                                 "finish_trim"])
def test_a_phase_two_kind_is_refused_and_named_never_guessed(sess, eid, kind):
    r = _add(sess, eid, kind=kind, points=_box(0, 0, 10, 10))
    assert r.status_code == 400, (
        f"{kind} was accepted — phase 2 is not built; a linear run must "
        "not be silently stored as an area mark")
    assert "phase-2" in r.json()["detail"], r.text


def test_an_unknown_kind_is_refused(sess, eid):
    r = _add(sess, eid, kind="chimney_chase", points=_box(0, 0, 10, 10))
    assert r.status_code == 400
    assert "unknown mark kind" in r.json()["detail"]


def test_a_non_siding_zone_needs_a_known_category(sess, eid):
    r = _add(sess, eid, kind="non_siding_zone", category="marble",
             points=_box(0, 0, 10, 10))
    assert r.status_code == 400, (
        "an unknown material category was accepted — the categories are "
        "brick/stone/stucco/garage_door/other")


# ── PIN 6 ────────────────────────────────────────────────────────────
def test_apply_is_423_on_a_protected_estimate(sess):
    """The photo-takeoff write is a DERIVED write. It refuses on a
    protected estimate exactly as the blueprint lane does."""
    r = sess.get(f"{API}/estimates", timeout=15)
    prot = next((e["id"] for e in r.json()
                 if e.get("estimate_number") == "EST-886440"), None)
    if not prot:
        pytest.skip("env:fixture_estimate: EST-886440 not on this account")
    r = sess.post(f"{API}/estimates/{prot}/photo-takeoff/apply", timeout=20)
    assert r.status_code == 423, (
        f"the derived write was not refused on a protected estimate: "
        f"{r.status_code}")
    assert "protected" in r.json()["detail"].lower()


# ── PIN 7 ────────────────────────────────────────────────────────────
def test_the_annotation_import_lands_provisional_and_is_idempotent(sess, eid):
    _wipe(sess, eid)
    ann = {
        PHOTO: {
            "elevation": "front",
            "reference": {"p1": {"x": 0, "y": 0}, "p2": {"x": 100, "y": 0},
                          "inches": 100.0},
            "zones": [{"id": "z-1", "kind": "rect", "category": "brick",
                       "points": _box(10, 10, 60, 60)}],
            "windows": [{"id": "w-1", "x": 300, "y": 200,
                         "style": "double-hung"}],
        }
    }
    r = sess.put(f"{API}/measure/sessions/{eid}",
                 json={"estimate_id": eid, "photo_urls": [PHOTO],
                       "photo_annotations": ann}, timeout=15)
    assert r.status_code == 200, r.text
    r = sess.post(f"{API}/estimates/{eid}/photo-takeoff/import-annotations",
                  params={"photo_key": PHOTO}, timeout=20)
    assert r.status_code == 200, r.text
    first = r.json()
    assert first["imported"] == 2, (
        f"the brick zone and the tagged window did not both come in: "
        f"{first['imported']}")
    assert all(m["status"] == "provisional" for m in first["marks"]), (
        "an imported mark landed confirmed — nothing imported carries a "
        "quantity until a human confirms it here")
    kinds = sorted(m["kind"] for m in first["marks"])
    assert kinds == ["non_siding_zone", "opening"], kinds
    win = next(m for m in first["marks"] if m["kind"] == "opening")
    assert win["shape"] == "point" and len(win["points"]) == 1, (
        "a tagged window is a TAP — it must come in as a point opening, "
        "not as a box with invented corners")
    # the photo's own anchor came in as the scale
    body = _get(sess, eid)
    assert body["per_photo"][PHOTO]["scale"], "the existing anchor was dropped"
    r2 = sess.post(f"{API}/estimates/{eid}/photo-takeoff/import-annotations",
                   params={"photo_key": PHOTO}, timeout=20)
    assert r2.json()["imported"] == 0, (
        "a second import duplicated the marks — the import must be "
        "idempotent")
    assert len(_get(sess, eid)["marks"]) == 2


# ── PIN 8 + 9 + 10 ───────────────────────────────────────────────────
def test_apply_writes_a_separate_quantity_lane_and_no_money(sess, eid):
    _wipe(sess, eid)
    _scale(sess, eid, 100.0)
    ids = []
    for kw in ({"kind": "siding_zone", "points": _box(0, 0, 120, 120)},
               {"kind": "non_siding_zone", "category": "stone",
                "points": _box(200, 0, 120, 120)},
               {"kind": "opening", "shape": "rect",
                "points": _box(400, 0, 60, 60)},
               {"kind": "opening", "shape": "point",
                "points": [{"x": 600, "y": 50}]}):
        r = _add(sess, eid, **kw)
        assert r.status_code == 200, r.text
        ids.append(r.json()["mark"]["id"])
    for mid in ids:
        sess.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
                   json={"status": "confirmed"}, timeout=15)
    r = sess.post(f"{API}/estimates/{eid}/photo-takeoff/apply", timeout=20)
    assert r.status_code == 200, r.text
    block = r.json()["photo_takeoff"]
    assert block["photo_siding_sqft"] == 100.0
    assert block["photo_non_siding_sqft"] == 100.0
    assert block["photo_opening_sqft"] == 25.0
    assert block["photo_opening_count"] == 2
    # OPENINGS REPORT SEPARATELY — no deduction in phase 1.
    per = block["per_photo"][PHOTO]
    assert per["openings_deducted"] is False
    assert per["siding_sqft"] == 100.0, (
        "the opening was deducted from the siding ft² — phase 1 reports "
        "openings, it does not deduct them")
    assert per["openings_without_extent"] == 1
    assert per["openings_without_extent_note"], (
        "the tap-only opening's missing ft² was not named")
    assert per["non_siding_by_category"] == {"stone": 100.0}
    est = sess.get(f"{API}/estimates/{eid}", timeout=15).json()
    assert est["photo_siding_sqft"] == 100.0
    assert est["photo_non_siding_sqft"] == 100.0
    assert est["photo_opening_count"] == 2
    # THE LANE IS SEPARATE: it does not mix into the derived measurement
    # store, and it writes no money.
    hm = est.get("hover_measurements") or {}
    for k in ("photo_siding_sqft", "photo_non_siding_sqft",
              "photo_opening_sqft", "photo_opening_count"):
        assert k not in hm, (
            f"{k} leaked into hover_measurements — the photo lane must "
            "not mix into blueprint/derived totals")
    assert not est.get("lines"), (
        "the photo takeoff created priced lines — it writes QUANTITY, "
        "never money")


def test_a_lane_with_no_confirmed_mark_of_its_kind_reports_none(sess, eid):
    _wipe(sess, eid)
    _scale(sess, eid, 100.0)
    mid = _add(sess, eid, kind="siding_zone",
               points=_box(0, 0, 120, 120)).json()["mark"]["id"]
    sess.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
               json={"status": "confirmed"}, timeout=15)
    q = _qty(sess, eid)
    assert q["siding_sqft"] == 100.0
    assert q["non_siding_sqft"] is None, (
        "an unmeasured lane reported 0.0 — a zero reads as 'measured and "
        "empty' when nothing was measured at all")
    assert q["opening_count"] is None
    assert q["opening_sqft"] is None


def test_a_refused_mark_carries_nothing_and_keeps_its_reason(sess, eid):
    _wipe(sess, eid)
    _scale(sess, eid, 100.0)
    mid = _add(sess, eid, kind="siding_zone",
               points=_box(0, 0, 120, 120)).json()["mark"]["id"]
    r = sess.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
                   json={"status": "refused",
                         "refused_reason": "that is the neighbour's wall"},
                   timeout=15)
    assert r.json()["mark"]["refused_reason"] == "that is the neighbour's wall"
    q = _qty(sess, eid)
    assert q["siding_sqft"] is None
    assert q["confirmed_marks"] == 0


# ── STRUCTURAL ───────────────────────────────────────────────────────
def test_the_module_touches_no_money_key_structurally():
    """The photo lane writes quantity. A price key appearing in this
    module is the defect this pin exists to catch.

    NAMED PIN UPDATE (SEND-132): the module now READS `est["lines"]` to
    list the body-siding products already on the job for the per-zone
    picker. A read is not a write — the ban is narrowed to exactly that:
    `lines` may be read, and may never appear in a write."""
    src = SRC.read_text()
    for token in ("unit_price", "mat_price", "lab_price", "margin",
                  "total_price", "sell_price", "pricing_source"):
        assert token not in src, (
            f"{token!r} appears in photo_takeoff.py — this path writes "
            "QUANTITY ONLY; money depends on the product and stays out")
    # the ONLY permitted mention of lines is the product read
    assert src.count('"lines"') == 1 and 'est.get("lines")' in src, (
        "photo_takeoff.py mentions `lines` somewhere other than the "
        "product read — this path may never write a priced line")
    for token in ('"lines":', "'lines':"):
        assert token not in src, (
            f"{token!r} appears in photo_takeoff.py — a lines WRITE from "
            "the photo lane is exactly the defect this pin exists to catch")


def test_phase_two_kinds_are_declared_and_unimplemented():
    """Phase 2 is NAMED as not built. Silence would let a later reader
    assume the linear runs exist."""
    src = SRC.read_text()
    m = re.search(r"PHASE2_KINDS\s*=\s*\{(.*?)\}", src, re.S)
    assert m, "PHASE2_KINDS is gone — the phase boundary must stay explicit"
    for kind in ("outside_corner", "inside_corner", "j_channel", "starter",
                 "soffit", "fascia", "finish_trim"):
        assert kind in m.group(1), f"{kind} dropped from the phase-2 set"
    assert "PHASE 2 (next pass, NOT built)" in src


def test_the_router_is_registered_under_the_api_prefix():
    """A route file nobody mounts is a route file that does nothing —
    this send's own first defect."""
    comp = Path("/app/backend/routes/__init__.py").read_text()
    assert "photo_takeoff" in comp
    assert "api_router.include_router(photo_takeoff.router)" in comp


# ── THE SURFACE (structural — the editor and its entry point) ────────
FE = Path("/app/frontend/src")
EDITOR = (FE / "components" / "estimate" / "PhotoTakeoffEditor.jsx").read_text()
AIM = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()


def test_the_editor_carries_every_ruled_surface():
    for tid in ("photo-takeoff-modal", "photo-takeoff-close",
                "photo-takeoff-tool-${t.key}",
                "photo-takeoff-scale-basis", "photo-takeoff-scale-refusal",
                "photo-takeoff-tape-commit", "photo-takeoff-qty-siding",
                "photo-takeoff-qty-nonsiding",
                "photo-takeoff-qty-opening-count",
                "photo-takeoff-qty-opening-sqft",
                "photo-takeoff-import-btn", "photo-takeoff-apply-btn",
                "photo-takeoff-canvas-img"):
        assert tid in EDITOR, tid
    for t in ("siding_zone", "non_siding_zone", "opening", "scale"):
        assert f'key: "{t}"' in EDITOR, t
    assert "photo-takeoff-category-${c.key}" in EDITOR
    for cat in ("brick", "stone", "garage_door", "stucco", "other"):
        assert f'key: "{cat}"' in EDITOR, cat
    # confirm / refuse / adjust / delete per mark
    for act in ("confirm", "refuse", "adjust", "delete"):
        assert f"photo-takeoff-{act}-${{m.id}}" in EDITOR, act


def test_the_editor_states_the_scale_that_governs_and_never_shows_a_zero():
    assert "TAPE GOVERNS" in EDITOR
    assert "TWO-TAP ANCHOR" in EDITOR
    assert "no zero is shown in its place" in EDITOR
    assert "scale_refusal" in EDITOR


def test_the_editor_names_the_phase_boundary_and_writes_no_money():
    assert "Trim runs (corners, J-channel, starter, soffit, fascia) are NOT built" \
        in EDITOR
    assert "nothing is deducted from siding" in EDITOR.lower() or \
        "nothing is deducted from siding" in EDITOR
    assert "No price, no priced line, no money" in EDITOR
    assert "423" in EDITOR


def test_the_vertex_drag_tracks_the_pointer_and_pinch_zoom_exists():
    """Mirror of the blueprint editor's fix: the drag listens on WINDOW
    (so a handle re-rendering under the finger cannot cut it short) and
    normalises against the RENDERED rect exactly once, so zoom cancels
    and the vertex tracks 1:1 at any zoom. Pinch must work on a phone."""
    assert 'window.addEventListener("pointermove", move)' in EDITOR
    assert 'window.addEventListener("pointerup", up)' in EDITOR
    assert "e.clientX - r.left) / r.width" in EDITOR
    assert 'el.addEventListener("touchmove", onTouchMove, { passive: false })' \
        in EDITOR
    assert "pinch.current" in EDITOR


def test_the_entry_point_is_now_the_one_drawing_door_on_the_photo():
    """NAMED PIN UPDATE (SEND-139, Howard ruled 2026-08-27). SEND-131A put
    the takeoff editor BESIDE Annotate while the gable and dormer tools
    still lived there. Those tools MOVED into the editor, so the Annotate
    doors came off and this entry point is THE drawing door. What the pin
    holds is unchanged: the entry point exists, per photo, and opens the
    editor."""
    assert "PhotoTakeoffEditor" in AIM
    assert "ai-measure-photo-takeoff-${i}" in AIM
    assert "setTakeoffOpenFor(name)" in AIM
    # and the retired door is not quietly back
    code = "\n".join(ln for ln in AIM.splitlines()
                      if not ln.lstrip().startswith(("//", "/*", "*")))
    assert "ai-measure-photo-annotate-${i}" not in code
    assert "PhotoAnnotateModal" not in code


# ── PHOTO-GENERATED ELEVATIONS ARE OUT OF THE CONTRACTOR VIEW ────────
def test_photo_elevations_are_unreachable_in_the_contractor_ui():
    """Howard ruled 2026-08-26: the contractor works on the PHOTOS, not
    on renders made from them. One named flag + no router entry. Every
    render component, the backend route and its pins stay intact."""
    flags = (FE / "lib" / "featureFlags.js").read_text()
    assert "export const PHOTO_ELEVATIONS_ENABLED = false;" in flags
    app = (FE / "App.js").read_text()
    assert '"/estimate/:id/elevation-sheet/:which"' not in app
    assert '"/estimate/:id/elevation-sheets/print"' not in app
    ed = (FE / "pages" / "EstimateEditor.jsx").read_text()
    assert "{PHOTO_ELEVATIONS_ENABLED && <ElevationSheetsPanel est={est} />}" in ed
    fvc = (FE / "components" / "estimate" / "FieldVerifyCard.jsx").read_text()
    assert 'PHOTO_ELEVATIONS_ENABLED && door === "photo"' in fvc
    # NOTHING DELETED — the render components and the backend route stay
    for p in ("pages/ElevationSheet.jsx", "pages/ElevationSheetsPrint.jsx",
              "components/estimate/ElevationSheetsPanel.jsx"):
        assert (FE / p).exists(), p
    assert '@router.get("/estimates/{est_id}/elevation-sheet/{which}")' in (
        Path("/app/backend/routes/elevation_sheets.py").read_text())


def test_the_blueprint_lane_is_untouched():
    """PARKED means parked: the blueprint elevation route stays routed
    and the blueprint pipeline is not part of this send."""
    app = (FE / "App.js").read_text()
    assert '"/estimate/:id/blueprint-elevation/:which"' in app
    assert '@router.get("/estimates/{est_id}/blueprint-elevation/{which}")' in (
        Path("/app/backend/routes/blueprint_elevation.py").read_text())
