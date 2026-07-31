"""TEST-DATA HYGIENE PIN (Howard ruled 2026-07-31). 2,039 TEST companies
and 146 resend.dev invitations sat untagged and unreachable by the purge
tool; 293 more hid under the suite's derived default "Tester's Company".

Pinned:
  · a company created by ANY test path (TEST_* convention OR the suite's
    legacy "Tester's Company" derived default) is tagged test_artifact at
    creation — the pollution cannot silently repopulate
  · real company names are NOT tagged
  · the census + purge endpoints exist and cover companies, users,
    catalogs, estimates and invitations
  · resend.dev invitations are tagged at insert
"""
import asyncio
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_test_named_companies_are_tagged_at_creation():
    import os
    from dotenv import load_dotenv
    from motor.motor_asyncio import AsyncIOMotorClient
    load_dotenv(BACKEND / ".env")

    async def go():
        # fresh client bound to THIS loop — the shared db.py client may be
        # bound to another test's loop in a full-suite run
        cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
        dbx = cli[os.environ["DB_NAME"]]
        import services
        orig = services.db
        services.db = dbx
        made = []
        try:
            for name, tagged in (
                (f"TEST_HygienePin {uuid.uuid4().hex[:6]}", True),
                ("Tester's Company", True),
                (f"Pappans Real Siding {uuid.uuid4().hex[:6]}", False),
            ):
                c = await services.create_company(name, owner_user_id=f"pin-{uuid.uuid4().hex[:8]}")
                made.append(c["id"])
                doc = await dbx.companies.find_one({"id": c["id"]}, {"_id": 0})
                assert bool(doc.get("test_artifact")) is tagged, \
                    f"'{name}': test_artifact must be {tagged}"
        finally:
            services.db = orig
            await dbx.companies.delete_many({"id": {"$in": made}})
            await dbx.catalogs.delete_many({"company_id": {"$in": made}})
            cli.close()

    _run(go())


def test_purge_and_census_cover_all_test_surfaces():
    src = (BACKEND / "routes" / "branding.py").read_text()
    for pattern in ("^TEST_", "^Tester's Company", "@resend\\\\.dev$"):
        assert pattern in src, f"purge/census must cover {pattern}"
    for fn in ("admin_test_data_census", "admin_test_data_purge"):
        assert fn in src
    # invitations tagged at insert
    assert 'endswith("@resend.dev")' in src, \
        "resend.dev invitations must be tagged test_artifact at insert"


def test_suite_self_cleans_its_own_residue():
    """SUITE SELF-CLEAN (Howard ruled 2026-07-31): every run used to leave
    ~7 tagged TEST companies. The session-end fixture deletes the run's
    own residue — companies, users, catalogs, invitations, TEST_
    estimates — while protected/fixture docs stay untouchable."""
    src = (BACKEND / "tests" / "conftest.py").read_text()
    assert "def suite_self_clean" in src and "autouse=True" in src
    for needle in ("test_artifact", "^Tester's Company", '"protected": {"$ne": True}'):
        assert needle in src, f"self-clean must keep covering: {needle}"
