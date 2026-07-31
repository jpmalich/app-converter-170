"""Test-artifact tagging pins (ruled 2026-07-18).

Pins:
  • test-harness-created runs carry test_artifact=True stamped AT CREATION
    (never inferred retroactively) — every direct test insert into a run
    substrate or fixture_runs is tagged
  • production run-creation code can NEVER set the tag (static pin)
  • admin purge deletes ONLY tagged docs; untagged archives survive
  • purge endpoints are admin-token gated
"""
import os
import re
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BACKEND = Path(__file__).resolve().parent.parent
from api_base import API  # env-derived (un-hardcoded 2026-07-23)
ADMIN_TOKEN = os.environ.get("SUPPLIER_ADMIN_TOKEN", "")

# Production files ALLOWED to reference the tag: run_archive owns the
# fixture_runs query surface; branding exposes the admin endpoints.
# SUPERSEDED IN PART (Howard ruled 2026-07-31, test-data hygiene): a
# company created by any TEST PATH (TEST_* name convention or the suite's
# "Tester's Company" derived default) IS tagged at creation — 2,332
# untagged test companies proved the gap. services.py::create_company is
# the ONE production site allowed to SET the tag, and only off the name
# convention. Runs remain governed by the 2026-07-18 ruling.
_ALLOWED_REFS = {"run_archive.py", "routes/branding.py"}
# EXTENDED (Howard ruled 2026-07-31, purge pre-flight): TEST_-named
# ESTIMATES tag at creation too — routes/estimates.py::create_estimate is
# the one estimate-side setter, gated on the customer_name convention.
_ALLOWED_SETTERS = {"services.py", "routes/estimates.py"}
_SETTER_LINE = {
    "services.py": 'company["test_artifact"] = True',
    "routes/estimates.py": 'doc["test_artifact"] = True',
}


def _production_sources():
    for p in list(BACKEND.glob("*.py")) + list((BACKEND / "routes").glob("*.py")):
        rel = str(p.relative_to(BACKEND))
        if rel.startswith("tests"):
            continue
        yield rel, p.read_text()


def test_production_code_never_sets_the_tag():
    for rel, src in _production_sources():
        if rel in _ALLOWED_SETTERS:
            # ruled 2026-07-31: the creation convention tags — exactly one
            # setter per file, gated on the TEST name convention.
            assert _SETTER_LINE[rel] in src, rel
            _code = "\n".join(l for l in src.splitlines()
                              if not l.strip().startswith("#"))
            assert _code.count("test_artifact") == 1, (
                f"{rel}: the tag may only be set at the creation "
                "convention site — nowhere else")
            continue
        if rel in _ALLOWED_REFS:
            # even here: query/projection only — never a $set write.
            assert not re.search(r'"\$set"[^)]*test_artifact', src), rel
            # ruled 2026-07-31: branding may tag INVITATION records off the
            # resend.dev convention at insert (the one allowed write there);
            # all its other occurrences are census/purge QUERY filters.
            continue
        assert "test_artifact" not in src, (
            f"{rel} references test_artifact — production run-creation "
            "paths must never carry the tag (ruled 2026-07-18)")


def test_every_direct_test_run_insert_is_tagged():
    """Harness pin: any test inserting into a run substrate or
    fixture_runs must stamp the tag at creation (this file excepted —
    its inserts below prove purge behavior with explicit control docs)."""
    ins_re = re.compile(
        r"\.(?:ai_measure_runs|ai_blueprint_runs|hover_import_runs|fixture_runs)\.insert_(?:one|many)\(")
    me = Path(__file__).name
    for p in (BACKEND / "tests").glob("test_*.py"):
        if p.name == me:
            continue
        lines = p.read_text().splitlines()
        for i, line in enumerate(lines):
            if not ins_re.search(line):
                continue
            window = "\n".join(lines[max(0, i - 4):i + 3])
            assert "test_artifact" in window, (
                f"{p.name}:{i+1} inserts a run doc without the "
                "test_artifact stamp (ruled 2026-07-18)")


@pytest.fixture()
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def test_purge_deletes_only_tagged_docs(mongo_db):
    assert ADMIN_TOKEN, "SUPPLIER_ADMIN_TOKEN missing from backend/.env"
    tagged_id = "test-artifact-pin-" + uuid.uuid4().hex[:10]
    control_id = "test-artifact-pin-" + uuid.uuid4().hex[:10]
    mongo_db.fixture_runs.insert_one(
        {"test_artifact": True, "run_id": tagged_id, "substrate": "ai_measure_runs"})
    # control doc: deliberately untagged to prove purge scope — removed
    # manually in finally (it IS test debris; the tag absence is the point).
    mongo_db.fixture_runs.insert_one({"run_id": control_id, "substrate": "ai_measure_runs"})
    try:
        r = requests.get(f"{API}/admin/fixture-runs/test-artifacts",
                         headers={"X-Admin-Token": ADMIN_TOKEN}, timeout=15)
        assert r.status_code == 200, r.text
        assert any(x["run_id"] == tagged_id for x in r.json()["runs"])
        assert not any(x["run_id"] == control_id for x in r.json()["runs"])
        r = requests.delete(f"{API}/admin/fixture-runs/test-artifacts",
                            headers={"X-Admin-Token": ADMIN_TOKEN}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["deleted"] >= 1
        assert mongo_db.fixture_runs.find_one({"run_id": tagged_id}) is None
        assert mongo_db.fixture_runs.find_one({"run_id": control_id}) is not None
    finally:
        mongo_db.fixture_runs.delete_many({"run_id": {"$in": [tagged_id, control_id]}})


def test_purge_endpoints_admin_gated():
    for method in (requests.get, requests.delete):
        r = method(f"{API}/admin/fixture-runs/test-artifacts", timeout=15)
        assert r.status_code in (401, 403), r.status_code
