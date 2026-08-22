"""SEND-107 (Howard, 2026-08-23): NO TEST TOUCHES A REAL ESTIMATE.

Every fixture that needs a write becomes a DISPOSABLE CLONE through the
real duplicate door (POST /estimates/{id}/duplicate — reads the source,
writes nothing to it). Runs are copied estimate-scoped when the flow
needs them (copied docs keep their original created_at, so the
measure-run pollution tripwire never scans them). Teardown deletes the
clone and everything keyed to it. The census pin
(test_real_estate_write_census_2026_08_23_send107.py) fails any test
that resolves a hardcoded estimate id into a mutating call.
"""
import os

from pymongo import MongoClient

RUN_COLLS = ("ai_measure_runs", "ai_blueprint_runs", "fixture_runs")


def _db():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def clone_estimate(session, api, est_id, *, copy_runs=False,
                   tag="ZZ send107 clone (disposable)"):
    r = session.post(f"{api}/estimates/{est_id}/duplicate", timeout=30)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    db = _db()
    db.estimates.update_one(
        {"id": cid},
        {"$set": {"customer_name": tag, "test_artifact": True}})
    if copy_runs:
        # run_id carries a UNIQUE index — remint the copy's id, PRESERVING
        # THE FIRST 8 CHARS (verb keys and sheet keys derive from run[:8]),
        # and remap the estimate's applied-source stamp onto the copy.
        import uuid as _uuid
        remap = {}
        for coll in RUN_COLLS:
            for doc in db[coll].find({"estimate_id": est_id}):
                doc.pop("_id", None)
                old = str(doc.get("run_id") or "")
                new = (old[:8] or _uuid.uuid4().hex[:8]) + _uuid.uuid4().hex[8:]
                remap[old] = new
                doc["run_id"] = new
                doc["estimate_id"] = cid
                doc["test_artifact"] = True
                db[coll].insert_one(doc)
        src_est = db.estimates.find_one({"id": est_id}, {"lp_source_run_id": 1})
        stamped = str((src_est or {}).get("lp_source_run_id") or "").strip()
        if stamped and stamped in remap:
            db.estimates.update_one({"id": cid},
                                    {"$set": {"lp_source_run_id": remap[stamped]}})
    return cid


def drop_clone(session, api, cid):
    db = _db()
    for coll in RUN_COLLS:
        db[coll].delete_many({"estimate_id": cid})
    db.human_dimensions.delete_many({"estimate_id": cid})
    db.lp_material_list_snapshots.delete_many({"estimate_id": cid})
    session.delete(f"{api}/estimates/{cid}", timeout=30)
