"""SEND-135 PINS — HOVER RESTORE IS LANE-LOCKED AND CLICK-ONLY.

Howard, 2026-08-27, on a BRAND-NEW estimate he had not asked anything of:
a dialog offered "APPLY 56 LINES & SAVE" under the words *HOVER Lines
Restored (Cached) · Source: cached HOVER measurements*. The numbers were
that session's AI PHOTO MEASURE numbers. He cancelled. P0, money.

WHAT THESE PINS HOLD:

  1. THE DOOR IS AN ALLOW-LIST, NOT A DENY-LIST. Only HOVER-sourced
     measurements (or a legacy blob with no stamp) can light the restore
     button. The old guard named "blueprint" and "ai_photo" and the
     photo apply writes "photo" — a deny-list cannot hold, because every
     future door must remember to add itself, and this one did not.
  2. THE CLICK IS THE ONLY TRIGGER. The component carries NO effect of
     any kind: nothing runs on page load, and no AI-Photo path can reach
     the restore.
  3. THE REFUSAL IS ENFORCED SERVER-SIDE. A caller naming its lane
     (`expect_source`) is held to it — another door's numbers are never
     mapped and dressed as that lane's lines.
  4. WHERE THE DOOR IS OFF IT SAYS SO — a missing button with no reason
     sends a contractor hunting for a restore that must not exist.
  5. A FRESH ESTIMATE HAS NOTHING TO RESTORE AND WRITES NO LINE: born
     empty, read twice, still empty.
  6. NO ESTIMATE INFLUENCES ANOTHER: the restore reads only
     `est.hover_measurements` — this estimate's own document. There is no
     account-wide cache and no device cache on that path.
"""
import re
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API  # env-derived
from creds_for_tests import TEST_PASSWORD

FE = Path("/app/frontend/src")
BTN = (FE / "components" / "estimate" / "HoverImportButton.jsx")
PANEL = (FE / "components" / "estimate" / "JobInfoPanel.jsx")
MAP_SRC = Path("/app/backend/routes/ai_measure.py")


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
def fresh(sess):
    r = sess.post(f"{API}/estimates",
                  json={"kind": "siding",
                        "customer_name": "ZZ TEST_send135-fresh-estimate TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    yield eid
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"],
                     serverSelectionTimeoutMS=2000)[os.environ["DB_NAME"]]
    db.estimates.delete_many({"id": eid})


# ── PIN 1 — THE DOOR IS AN ALLOW-LIST ────────────────────────────────
def test_the_hover_door_is_source_locked_by_allow_list():
    src = BTN.read_text()
    assert 'const cachedIsHover = !cachedSource || cachedSource === "hover";' in src, (
        "the HOVER door's source lock is not an allow-list — only "
        "hover-stamped (or unstamped legacy) measurements may restore")
    assert "const hasCached = hasAnyCached && cachedIsHover;" in src
    # THE DENY-LIST IS GONE. It is the defect: it named two doors and the
    # photo door writes a third string.
    assert 'cachedSource !== "blueprint"' not in src, (
        "the deny-list guard is back — every future door would have to "
        "remember to add itself, and the photo door did not")
    assert 'cachedSource !== "ai_photo"' not in src


def test_the_photo_apply_writes_a_source_the_hover_door_must_not_accept():
    """The photo apply stamps `_source: "photo"`. That is the exact
    string the old deny-list never named. The pin ties the two files
    together so a rename on either side cannot re-open the hole."""
    panel = PANEL.read_text()
    assert 'patch.hover_measurements = { ...measurements, _source: "photo" };' in panel, (
        "the photo apply's source stamp changed — re-check the HOVER "
        "door's allow-list against the new string")
    src = BTN.read_text()
    # the ONLY value the door accepts, stated once
    assert src.count('cachedSource === "hover"') == 1
    assert '"photo"' not in src.split("const hasCached")[0].split(
        "const cachedIsHover")[1], (
        "the door's lock mentions the photo lane — the allow-list must "
        "name only what it ACCEPTS")


# ── PIN 2 — THE CLICK IS THE ONLY TRIGGER ────────────────────────────
def test_nothing_can_trigger_the_restore_except_the_click():
    src = BTN.read_text()
    assert "useEffect" not in src, (
        "HoverImportButton grew an effect — the restore must never run "
        "on page load, on mount, or as any door's side effect")
    assert src.count("onClick={restore}") == 1, (
        "the restore is wired to more than one control")
    # no other call site anywhere in the app
    calls = []
    for p in FE.rglob("*.jsx"):
        for m in re.finditer(r"\brestore\(\s*\)", p.read_text()):
            calls.append((p.name, m.start()))
    assert not calls or all(n == "HoverImportButton.jsx" for n, _ in calls), (
        f"restore() is called from outside its own component: {calls}")
    # and it is not auto-clicked from anywhere
    for p in FE.rglob("*.jsx"):
        t = p.read_text()
        assert "hover-restore-btn" not in t or p.name == "HoverImportButton.jsx", (
            f"{p.name} reaches for the restore button by testid — the "
            "click must come from the contractor")


def test_the_restore_checks_the_source_at_the_click():
    src = BTN.read_text()
    body = src.split("const restore = async () => {")[1].split("\n  };")[0]
    assert "if (!cachedIsHover) {" in body, (
        "the restore does not re-check the lane at the moment of the "
        "click — the allow-list alone leaves a stale-props window")
    assert "not a HOVER report" in body
    assert 'expect_source: "hover"' in body, (
        "the restore does not name its lane to the server")
    assert "est.hover_measurements" in body, (
        "the restore reads something other than THIS estimate's own blob")


def test_the_restore_reads_only_this_estimates_own_document():
    """NO ESTIMATE INFLUENCES ANOTHER. The restore's cache key is the
    estimate document itself — no account-wide fetch, no localStorage,
    no 'latest import' lookup."""
    src = BTN.read_text()
    body = src.split("const restore = async () => {")[1].split("\n  };")[0]
    for forbidden in ("localStorage", "sessionStorage", "latest", "recent"):
        assert forbidden not in body, (
            f"the restore path touches {forbidden!r} — the only source is "
            "this estimate's own hover_measurements")


# ── PIN 3 — THE SERVER REFUSES A CROSS-LANE RESTORE ──────────────────
def test_the_mapper_refuses_a_cross_lane_restore_by_name(sess):
    photo_blob = {"_source": "photo", "siding_sqft": 1243.8, "eaves_lf": 48}
    r = sess.post(f"{API}/measure/map",
                  json={"measurements": photo_blob, "expect_source": "hover"},
                  timeout=30)
    assert r.status_code == 400, (
        f"the mapper mapped PHOTO numbers for a HOVER restore: {r.status_code}")
    d = r.json()["detail"]
    assert "PHOTO door" in d and "HOVER" in d, d
    assert "never" in d


def test_the_mapper_still_serves_the_hover_lane_and_the_shared_doors(sess):
    hover_blob = {"_source": "hover", "siding_sqft": 1000.0, "eaves_lf": 40,
                  "rakes_lf": 40, "starter_lf": 80}
    r = sess.post(f"{API}/measure/map",
                  json={"measurements": hover_blob, "expect_source": "hover"},
                  timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("lines"), "the hover restore stopped mapping"
    # THE MAPPER IS SHARED. The photo door and the per-elevation override
    # door call it with photo numbers and NAME NO LANE — they must not be
    # caught by this guard.
    r = sess.post(f"{API}/measure/map",
                  json={"measurements": {"_source": "photo",
                                         "siding_sqft": 1000.0,
                                         "eaves_lf": 40, "rakes_lf": 40}},
                  timeout=30)
    assert r.status_code == 200, (
        "the shared mapper now refuses its own legitimate photo callers")
    # a legacy blob with no stamp still restores (back-compat)
    r = sess.post(f"{API}/measure/map",
                  json={"measurements": {"siding_sqft": 1000.0, "eaves_lf": 40},
                        "expect_source": "hover"}, timeout=30)
    assert r.status_code == 200, "legacy unstamped HOVER data stopped restoring"


def test_the_guard_lives_in_the_mapper_and_names_itself():
    src = MAP_SRC.read_text()
    assert 'expect_source = payload.get("expect_source")' in src
    assert "A LANE MAY ONLY RESTORE" in src, (
        "the server-side rule is unnamed — the next reader will not know "
        "why it is there")


# ── PIN 4 — THE OFF STATE IS NAMED ───────────────────────────────────
def test_where_the_door_is_off_the_reason_renders():
    src = BTN.read_text()
    assert 'data-testid="hover-restore-off-reason"' in src
    assert "hasAnyCached && !cachedIsHover" in src
    assert "never restored as HOVER lines" in src


# ── PIN 5 — A FRESH ESTIMATE HAS NOTHING TO RESTORE ──────────────────
def test_a_fresh_estimate_is_born_with_no_hover_source_and_no_lines(sess, fresh):
    """OPENING A FRESH ESTIMATE NEVER OPENS THE DIALOG AND NEVER WRITES A
    LINE. The dialog needs `hover_measurements`; a new estimate has none,
    and READING it twice (what a page load does) creates none."""
    for pass_no in (1, 2):
        r = sess.get(f"{API}/estimates/{fresh}", timeout=15)
        assert r.status_code == 200, r.text
        est = r.json()
        hm = est.get("hover_measurements") or {}
        assert not hm, (
            f"pass {pass_no}: a fresh estimate carries hover_measurements "
            f"({list(hm)[:6]}) — the restore door would light up on a job "
            "that has never seen a HOVER report")
        assert not (est.get("lines") or []), (
            f"pass {pass_no}: a fresh estimate carries "
            f"{len(est.get('lines') or [])} line(s) — nothing may write a "
            "line without an explicit apply")
        assert not est.get("photo_takeoff")
        assert not est.get("waste_pct")


def test_a_photo_sourced_estimate_offers_no_hover_restore(sess, fresh):
    """The exact shape of the bug: an estimate whose ONLY measurements
    came from the AI PHOTO door. The door must be shut — and the shut
    door is decided by the same expression the surface renders."""
    est = sess.get(f"{API}/estimates/{fresh}", timeout=15).json()
    est["hover_measurements"] = {"_source": "photo", "siding_sqft": 1243.8,
                                 "eaves_lf": 48, "rakes_lf": 57.8}
    r = sess.put(f"{API}/estimates/{fresh}", json=est, timeout=15)
    assert r.status_code == 200, r.text
    got = sess.get(f"{API}/estimates/{fresh}", timeout=15).json()
    src_stamp = (got.get("hover_measurements") or {}).get("_source")
    assert src_stamp == "photo", src_stamp
    # the surface's own rule, applied to the stored stamp
    cached_is_hover = (not src_stamp) or src_stamp == "hover"
    assert cached_is_hover is False, (
        "a photo-sourced estimate satisfies the HOVER door's lock — this "
        "is EST-381546 all over again")
    # and the server refuses the restore even if a UI forgot
    r = sess.post(f"{API}/measure/map",
                  json={"measurements": got["hover_measurements"],
                        "expect_source": "hover"}, timeout=30)
    assert r.status_code == 400, (
        "the photo-sourced blob was still mappable as a HOVER restore")
    # nothing about that refusal wrote a line
    after = sess.get(f"{API}/estimates/{fresh}", timeout=15).json()
    assert not (after.get("lines") or []), (
        "a refused restore wrote lines onto the estimate")
