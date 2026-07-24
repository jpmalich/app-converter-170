"""Suite-wide MEASURE-RUN POLLUTION TRIPWIRE (ruled 2026-07-24).

No test may attach measure-run documents (ai_measure_runs /
ai_blueprint_runs) to a PRE-EXISTING, non-TEST_ estimate. This defect
class has bitten three times (red-house waste residue, Letrick residue,
the EST-644081 "PREVIOUS READ" blueprint banner) — it dies here.

Allowed targets: no estimate_id at all, estimates BORN during this suite
run (self-created throwaways of any name), and estimates whose
customer_name starts with TEST_. Anything else fails the whole session
by name, with receipts.
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _naive_utc(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


@pytest.fixture(scope="session", autouse=True)
def measure_run_pollution_tripwire():
    from pymongo import MongoClient
    start = datetime.now(timezone.utc).replace(tzinfo=None)
    yield
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    violations = []
    for coll in ("ai_measure_runs", "ai_blueprint_runs"):
        for run in db[coll].find(
                {"created_at": {"$gte": start}},
                {"run_id": 1, "estimate_id": 1, "created_at": 1}):
            eid = run.get("estimate_id")
            if not eid:
                continue
            est = db.estimates.find_one(
                {"id": eid},
                {"customer_name": 1, "created_at": 1, "lp_source_run_id": 1})
            if est is None:
                continue  # throwaway already deleted by its own teardown
            # SANCTIONED: the estimate's OWN standing derivation record
            # (deterministic lp_run_id, upserted by re-derivation tests on
            # the ruled fixture estimates — e.g. Jon's
            # hover-…-board_batten). Pollution is FOREIGN artifacts, not
            # an estimate's own run refreshed in place.
            if run.get("run_id") and run["run_id"] == est.get("lp_source_run_id"):
                continue
            name = str(est.get("customer_name") or "")
            born = _naive_utc(est.get("created_at"))
            if name.startswith("TEST_") or (born is not None and born >= start):
                continue
            violations.append(
                {"collection": coll, "run_id": run.get("run_id"),
                 "estimate_id": eid, "customer_name": name})
    client.close()
    assert not violations, (
        "MEASURE-RUN POLLUTION TRIPWIRE (ruled 2026-07-24): test(s) attached "
        "run docs to pre-existing non-TEST_ estimates — the residue-banner "
        f"defect class, and it dies here: {violations}")
