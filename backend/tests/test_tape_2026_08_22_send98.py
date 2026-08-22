"""SEND-98 register (Howard, 2026-08-14, verbatim core):

"REAR TAPE ENTRY + CARD PRINTING. AUTHORIZED. 1. A TAPED FIGURE
GOVERNS — top of the evidence ladder. 2. CLEARLY LABELLED AS A TAPED
HUMAN MEASUREMENT, never absorbed into the read. 3. THE ORIGINAL
CONTESTANTS ARE KEPT IN THE RECORD."

Item 1: "BUILD IT FOR EVERY FACE, NOT FOR LETRICK'S REAR ... where a
tape CONTRADICTS AN ALREADY-RESOLVED READ, IT GOVERNS AND SAYS SO."

Item 2: "WHAT A CONTRACTOR CAN TAPE IS NOT WHAT THE DERIVATION USES
... DO NOT ASSUME THEY MATCH."

Item 4: "ACCEPTS FEET-INCHES NOTATION ... ECHOES BACK WHAT IT PARSED
... REJECT rather than guess ... an inch component of 12 or more is
not feet-inches (Ruling HH)."
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API
from creds_for_tests import TEST_PASSWORD
from routes.pdf_overlay import _TIER_RANK, parse_feet_inches


def test_parser_accepts_the_forms_howard_will_type():
    assert parse_feet_inches("9'-11\"")[0] == 9.9167
    assert parse_feet_inches("9-11")[0] == 9.9167
    assert parse_feet_inches("9' 11\"")[0] == 9.9167
    assert parse_feet_inches("9-1 1/8")[0] == 9.0938
    assert parse_feet_inches("9")[0] == 9.0
    assert parse_feet_inches("9.92")[0] == 9.92    # decimal allowed too


def test_parser_echoes_what_it_parsed():
    val, echo = parse_feet_inches("9-11")
    assert "9'-11\"" in echo and "9.9167 ft" in echo


def test_parser_rejects_rather_than_guesses():
    # Ruling HH: an inch component of 12+ is not feet-inches
    val, why = parse_feet_inches("9-12")
    assert val is None and "Ruling HH" in why
    assert parse_feet_inches("")[0] is None
    assert parse_feet_inches("about nine")[0] is None
    assert parse_feet_inches("9-1 1/0")[0] is None
    assert parse_feet_inches("0")[0] is None


def test_taped_human_sits_at_the_top_of_the_ladder():
    assert _TIER_RANK["taped_human"] < min(
        v for k, v in _TIER_RANK.items() if k != "taped_human")


def test_structural_governance_and_plane_honesty_are_wired():
    import pathlib
    src = pathlib.Path("/app/backend/routes/pdf_overlay.py").read_text()
    assert "TAPED HUMAN MEASUREMENT" in src
    assert "never absorbed into the read" in src.lower() or \
        "never absorbed into " in src
    assert "bands DIFFER" in src
    assert "taped_over" in src            # contestants kept
    assert '"tapes": tapes_report' in src
    assert "plane_matches_band" in src
    # cards carry the job and the face — a card with no identifier is
    # a hazard
    assert '"estimate_number": est.get("estimate_number")' in src
    assert '"tape_points"' in src


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
def rig(sess):
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"],
                     serverSelectionTimeoutMS=2000)[os.environ["DB_NAME"]]
    src = db.ai_blueprint_runs.find_one(
        {"estimate_id": "264b6230-5d0f-49ea-b07d-8d33a537f293",
         "status": "done"}, sort=[("created_at", -1)])
    if not src:
        pytest.skip("env:fixture_data: source blueprint run not in datastore")
    r = sess.post(f"{API}/estimates",
                  json={"kind": "lp_smart",
                        "customer_name": "ZZ TEST_tape98 TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_tape98-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_deletion_ledger.delete_many({"estimate_id": eid})
    db.human_dimensions.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def test_live_parse_echo_commits_nothing(sess, rig):
    eid = rig["eid"]
    r = sess.post(f"{API}/estimates/{eid}/pdf-overlay/tape/parse",
                  json={"text": "9-6"}, timeout=15)
    assert r.status_code == 200 and r.json()["ok"]
    assert "9'-6\"" in r.json()["echo"]
    assert rig["db"].human_dimensions.count_documents(
        {"estimate_id": eid}) == 0


def test_live_ambiguous_tape_is_rejected_over_http(sess, rig):
    r = sess.post(f"{API}/estimates/{rig['eid']}/pdf-overlay/tape",
                  json={"face_id": "back", "text": "9-13",
                        "ref_from": "first_floor_line",
                        "ref_to": "top_of_plate_line"}, timeout=15)
    assert r.status_code == 422
    assert "Ruling HH" in r.json()["detail"]


def test_live_band_matched_tape_governs_the_contested_rear(sess, rig):
    """9'-6\" agrees with NEITHER contestant (9'-11 vs 9'-1x) — the
    tape still governs, both contestants stay in the record, and the
    chase row stops refusing (the contest is resolved)."""
    eid = rig["eid"]
    r = sess.post(f"{API}/estimates/{eid}/pdf-overlay/tape",
                  json={"face_id": "back", "text": "9'-6\"",
                        "ref_from": "first_floor_line",
                        "ref_to": "top_of_plate_line"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "GOVERNS" in body["statement"]
    assert body["tape"]["prior_read"]["tier"] == "contested_pick_larger"
    # PIN UPDATED (SEND-104, named per SEND-99 condition 1): this
    # sub-pin previously asserted a top_of_foundation → bottom_of_soffit
    # tape on LEFT is RECORDED only ("bands DIFFER", never governs, left
    # stays derived_chain). The SEND-104 reachable-plane ruling made
    # that value wrong: "A TAPED MEASUREMENT RESOLVES BOTH THE HEIGHT
    # AND THE SCALE" — the same tape now GOVERNS the sided height
    # directly and calibrates LEFT's scale (both endpoint datums are
    # drawn on Letrick left). The old behavior is not a regression; the
    # new assertions pin the ruled behavior.
    r2 = sess.post(f"{API}/estimates/{eid}/pdf-overlay/tape",
                   json={"face_id": "left", "text": "10-2",
                         "ref_from": "top_of_foundation",
                         "ref_to": "bottom_of_soffit"}, timeout=15)
    assert r2.status_code == 200
    assert "SIDED HEIGHT directly" in r2.json()["statement"]
    assert r2.json()["tape"]["resolves"] == "height+scale"
    # propose — the tape governs rear; left is governed by ITS OWN tape
    rp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                   timeout=240)
    assert rp.status_code == 200, rp.text
    d = rp.json()
    rear = [p for p in d["proposed"] if p["face_id"] == "back"
            and not str(p["face_id"]).startswith("chase:")]
    assert rear and all(p["tier"] == "taped_human" for p in rear)
    assert all(p["proposed_from"]["height_ft"] == 9.5 for p in rear)
    assert "TAPED HUMAN MEASUREMENT" in rear[0]["basis"]
    assert "Kept in the record" in rear[0]["basis"]
    assert d["tapes"]["back"]["governs"] is True
    assert "both" in d["tapes"]["back"]["statement"].lower()
    # left face (SEND-104): its own reachable tape governs it — height
    # and scale, prior derived_chain read kept in the record
    assert d["tapes"]["left"]["governs"] is True
    assert "height AND scale" in d["tapes"]["left"]["statement"]
    assert ("contradicts the prior derived_chain read"
            in d["tapes"]["left"]["statement"])
    left = next(p for p in d["proposed"] if p["face_id"] == "left")
    assert left["tier"] == "taped_human"
    assert left["proposed_from"]["height_ft"] == 10.1667
    assert "Kept in the record" in left["basis"]
    # the rear CHASE stops refusing: contested cleared by the tape
    chase = next(p for p in d["proposed"] if p["face_id"] == "chase:back")
    assert "CONTESTED" not in chase["basis"]
    assert chase["tier"] == "taped_human"
    # and the quote gate clears when such a zone binds: no contested
    # marker means apply_overlay prices the row (unit-pinned in
    # test_chase_quote_2026_08_22_send96)


def test_live_height_cards_carry_the_job_and_the_face(sess, rig):
    r = sess.get(f"{API}/estimates/{rig['eid']}/pdf-overlay/height-cards",
                 timeout=120)
    assert r.status_code == 200
    for c in r.json()["cards"]:
        assert c["estimate_id"] == rig["eid"]
        assert c["face_id"] in ("front", "back", "left", "right")
        assert c["tape_points"]["from"] == "top_of_foundation"
        assert c["plane_matches_band"] is False   # never assumed
        assert "GOVERNS" in c["governing_alternative"]


def test_live_band_matched_tape_governs_an_already_resolved_face(sess, rig):
    """SEND-98 item 1: 'where a tape CONTRADICTS AN ALREADY-RESOLVED
    READ, IT GOVERNS AND SAYS SO.' LEFT resolved derived_chain; a
    band-matched tape at a different figure must take the face, name
    the contradiction, and keep the read in the record."""
    eid = rig["eid"]
    r = sess.post(f"{API}/estimates/{eid}/pdf-overlay/tape",
                  json={"face_id": "left", "text": "8-0",
                        "ref_from": "first_floor_line",
                        "ref_to": "top_of_plate_line"}, timeout=15)
    assert r.status_code == 200, r.text
    assert "GOVERNS" in r.json()["statement"]
    rp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                   timeout=240)
    assert rp.status_code == 200, rp.text
    d = rp.json()
    left = next(p for p in d["proposed"] if p["face_id"] == "left")
    assert left["tier"] == "taped_human"
    assert left["proposed_from"]["height_ft"] == 8.0
    assert "TAPED HUMAN MEASUREMENT" in left["basis"]
    assert "Kept in the record" in left["basis"]
    t = d["tapes"]["left"]
    assert t["governs"] is True
    assert "contradicts the prior derived_chain read" in t["statement"]
    assert "the tape governs, the read is kept" in t["statement"]
