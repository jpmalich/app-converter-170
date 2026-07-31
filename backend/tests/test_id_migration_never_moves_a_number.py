"""ID MIGRATION NEVER MOVES A NUMBER (Howard ruled 2026-07-31).

The precondition he set before authorizing ID binding: "A migration that
re-derives is a migration that can change a number." This pin holds the
writer to it forever: the migration STAMPS item_id and cannot move any
other field — human-typed quantities, frozen prices, notes, adders all
byte-identical. Unresolved names are left alone, never guessed.
"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")

from catalog_ids import ITEM_IDS, NAME_INDEX
from catalog_seed import SECTION_LAYOUT, build_tier_sections


# ═══════════ THE REGISTER — literal, unique, total ══════════════════════
def test_226_unique_literal_ids():
    assert len(ITEM_IDS) == 226
    assert len(set(ITEM_IDS.values())) == 226, "ids must never collide"
    src = (BACKEND / "catalog_ids.py").read_text()
    for iid in list(ITEM_IDS.values())[:5] + list(ITEM_IDS.values())[-5:]:
        assert f'"{iid}"' in src, "ids are LITERALS in the file, never runtime-minted"


def test_register_covers_every_catalog_row():
    for title, _asc, names in SECTION_LAYOUT:
        for n in names:
            assert (title, n) in ITEM_IDS, f"unregistered row: [{title}] {n}"


def test_seed_attaches_the_id_to_every_item():
    for sec in build_tier_sections("Contractor"):
        for it in sec["items"]:
            assert it.get("item_id") == ITEM_IDS[(sec["title"], it["name"])]


def test_estimate_line_declares_item_id():
    from models import EstimateLine
    assert "item_id" in EstimateLine.model_fields, \
        "item_id must be a DECLARED field — the silent-strip lesson"


# ═══════════ THE WRITER — stamps, never derives ═════════════════════════
@pytest.fixture()
def seeded_estimate():
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    eid = f"TEST_IDMIG-{uuid.uuid4().hex[:8]}"
    lines = [
        # derivation-owned row — resolvable
        {"tab": "vinyl", "section": "Siding Accessories", "name": "House Wrap",
         "unit": "ROLL", "qty": 3.0, "mat": 119.11, "lab": 10.0,
         "note": "machine note", "_waste_included": True},
        # HUMAN-typed row with note + adders — resolvable
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": "J-blocks - Split Blocks (82A009)", "unit": "Each",
         "qty": 4.0, "qty_src": "human", "mat": 13.49, "lab": 0,
         "contractor_note": "east wall", "adders": [{"name": "arch", "qty": 1}]},
        # UNRESOLVABLE legacy name — must be left alone entirely
        {"tab": "vinyl", "section": "Ghost Section", "name": "No Such Item",
         "unit": "Each", "qty": 2.0, "qty_src": "human", "mat": 99.99, "lab": 1.0},
    ]
    db.estimates.insert_one({"id": eid, "company_id": "TEST", "kind": "siding",
                             "customer_name": "TEST_IDMIG", "test_artifact": True,
                             "created_at": "2026-07-31T15:00:00+00:00",
                             "lines": [dict(l) for l in lines]})
    yield eid, lines, db
    db.estimates.delete_many({"id": eid})


def _run_migration():
    r = subprocess.run([sys.executable, str(BACKEND / "migrate_2026_07_31_item_ids.py")],
                       capture_output=True, text=True, cwd=str(BACKEND))
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_id_migration_never_moves_a_number(seeded_estimate):
    eid, before, db = seeded_estimate
    out = _run_migration()
    after = db.estimates.find_one({"id": eid})["lines"]
    assert len(after) == len(before)
    for b, a in zip(before, after):
        stripped = {k: v for k, v in a.items() if k != "item_id"}
        assert json.dumps(stripped, sort_keys=True, default=str) == \
               json.dumps(b, sort_keys=True, default=str), \
            f"a non-item_id field moved on {b['name']} — the migration derived"
    assert after[0]["item_id"] == ITEM_IDS[("Siding Accessories", "House Wrap")]
    assert after[1]["item_id"] == ITEM_IDS[("Siding Accessories", "J-blocks - Split Blocks (82A009)")]
    assert after[1]["qty"] == 4.0 and after[1]["qty_src"] == "human", "human qty is untouchable"
    assert "item_id" not in after[2], "unresolved names are LEFT ALONE, never guessed"
    assert "No Such Item" in out, "the receipt must NAME the unresolved row"


def test_migration_is_idempotent(seeded_estimate):
    eid, _before, db = seeded_estimate
    _run_migration()
    once = db.estimates.find_one({"id": eid})["lines"]
    _run_migration()
    twice = db.estimates.find_one({"id": eid})["lines"]
    assert json.dumps(once, sort_keys=True, default=str) == \
           json.dumps(twice, sort_keys=True, default=str)


def test_name_index_never_guesses_ambiguous_names():
    # duplicate names across sections resolve to None by name alone
    from collections import Counter
    dupes = [n for n, c in Counter(n for (_s, n) in ITEM_IDS).items() if c > 1]
    for n in dupes:
        assert NAME_INDEX.get(n) is None, f"ambiguous name {n!r} must not name-resolve"


# ═══════════ THE CARRY — item_id survives every strip layer ═════════════
def test_frontend_carries_item_id():
    js = (Path("/app/frontend/src/lib/useEstimate.js")).read_text()
    assert "item_id: l.item_id" in js, "buildPayload must send item_id"
    assert "item_id: it.item_id || (saved && saved.item_id)" in js, \
        "catalog merge must carry item_id (catalog wins, saved falls back)"


def test_rebuild_inherits_item_id():
    src = (BACKEND / "routes" / "hover.py").read_text()
    assert '"item_id"' in src.split('for k in ("mat", "lab", "adders", "ami_part"')[1][:60], \
        "rebuilt lines must inherit the stamped identity"


# ═══════════ DAY 2 — THE BINDING FLIP (journeys) ════════════════════════
import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
API = (os.environ.get("REACT_APP_BACKEND_URL")
       or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/") + "/api"

MEAS = {"siding_sqft": 2000, "eaves_lf": 120, "rakes_lf": 80,
        "soffit_sqft": 200, "outside_corner_count": 4,
        "inside_corner_count": 2, "window_count": 10, "door_count": 2,
        "overhang_in": 12}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": "hhunt6677@yahoo.com",
                        "password": _ENV.get("ADMIN_PASSWORD", "")})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture()
def journey_est(s):
    r = s.post(f"{API}/estimates",
               json={"customer_name": f"TEST_IDBIND-{uuid.uuid4().hex[:6]}",
                     "kind": "siding"})
    eid = r.json()["id"]
    s.put(f"{API}/estimates/{eid}",
          json={"hover_measurements": dict(MEAS), "waste_pct": 10})
    yield eid
    s.delete(f"{API}/estimates/{eid}")


def _rederive(s, eid):
    r = s.post(f"{API}/estimates/{eid}/rederive", json={"trigger": "test"})
    assert r.status_code == 200, r.text
    return r.json()["lines"]


def test_derived_lines_carry_identity_from_birth(journey_est, s):
    lines = _rederive(s, journey_est)
    hw = [l for l in lines if l.get("name") == "House Wrap" and l.get("tab") == "vinyl"][0]
    assert hw.get("item_id") == ITEM_IDS[("Siding Accessories", "House Wrap")], \
        "a freshly derived line must be born with its app-minted identity"


def test_rename_cannot_orphan_a_human_quantity(journey_est, s):
    """THE CLASS THIS KILLS: line identity was the name string. A saved
    line whose display name drifted (rename) but whose item_id matches
    must still hand its human qty, price and note to the rebuild."""
    lines = _rederive(s, journey_est)
    hw = [l for l in lines if l.get("name") == "House Wrap" and l.get("tab") == "vinyl"][0]
    hw["name"] = "House Wrap (2026 label)"   # the rename, simulated on the saved doc
    hw["qty"] = 9.0
    hw["qty_src"] = "human"
    hw["contractor_note"] = "renamed but mine"
    r = s.put(f"{API}/estimates/{journey_est}", json={"lines": lines})
    assert r.status_code == 200, r.text
    after = _rederive(s, journey_est)
    hw2 = [l for l in after if l.get("item_id") == ITEM_IDS[("Siding Accessories", "House Wrap")]
           and l.get("tab") == "vinyl"]
    assert len(hw2) == 1, f"renamed line must bind ONCE by id, not duplicate: {len(hw2)}"
    hw2 = hw2[0]
    assert hw2["qty"] == 9.0 and hw2.get("qty_src") == "human", \
        "the human quantity was orphaned by a rename — the id bind failed"
    assert hw2.get("contractor_note") == "renamed but mine"


def test_resolved_catalog_serves_the_identity(s):
    r = s.get(f"{API}/catalog")
    assert r.status_code == 200, r.text
    items = [it for sec in r.json()["sections"] for it in sec["items"]]
    with_id = [it for it in items if it.get("item_id")]
    assert len(with_id) >= 200, \
        f"resolved catalog must carry item_id on its rows ({len(with_id)}/{len(items)})"
