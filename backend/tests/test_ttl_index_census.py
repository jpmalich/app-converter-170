"""THE INDEX CENSUS — the reaper in the ledger, CLASS-WIDE (ruled 2026-08-11).

A TTL index removes data with NO code executing, so the AST seam detector
is structurally blind to it (TTL incident #3: the EST-886440 grading chain,
third instance of the class). This census is the mirror instrument on the
other substrate: it walks the LIVE database — never a registry file alone —
and fails the build on:
  • any live expiring index absent from seam_accounting.TTL_REAPER_REGISTRY
  • any registry entry the live DB does not carry (bidirectional)
  • any window mismatch between registry and live index
  • any capped collection (silent oldest-doc eviction — same class)
  • any expiring index on a TTL_FORBIDDEN collection (audit A5's
    hover_page_cache trap: a 1h index that outlived its retired code)
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from seam_accounting import SEAM_REGISTRY, TTL_FORBIDDEN, TTL_REAPER_REGISTRY  # noqa: E402


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def _live_expiring_indexes(mongo_db):
    live = {}
    for coll in mongo_db.list_collection_names():
        for iname, v in mongo_db[coll].index_information().items():
            if "expireAfterSeconds" in v:
                live[(coll, iname)] = int(v["expireAfterSeconds"])
    return live


def test_census_every_live_expiring_index_is_registered(mongo_db):
    live = _live_expiring_indexes(mongo_db)
    unregistered = {k: s for k, s in live.items() if k not in TTL_REAPER_REGISTRY}
    assert not unregistered, (
        "UNREGISTERED expiring index(es) in the LIVE database — a reaper "
        "with no ledger entry is the incident class. Register in "
        f"seam_accounting.TTL_REAPER_REGISTRY or drop the index: {unregistered}")


def test_census_windows_match_live(mongo_db):
    live = _live_expiring_indexes(mongo_db)
    mismatched = {
        k: {"live": s, "registry": TTL_REAPER_REGISTRY[k]["expire_seconds"]}
        for k, s in live.items()
        if k in TTL_REAPER_REGISTRY
        and s != TTL_REAPER_REGISTRY[k]["expire_seconds"]}
    assert not mismatched, (
        f"registry window disagrees with the LIVE index: {mismatched}")


def test_census_every_registry_entry_exists_live(mongo_db):
    """Bidirectional: a registry line for a dropped index is a stale claim."""
    for (coll, iname), spec in TTL_REAPER_REGISTRY.items():
        info = mongo_db[coll].index_information()
        assert iname in info, (
            f"registry names {coll}.{iname} but the live DB does not carry "
            "it — drop the registry line or restore the index")
        assert int(info[iname].get("expireAfterSeconds", -1)) == spec["expire_seconds"], (
            f"{coll}.{iname}: live={info[iname].get('expireAfterSeconds')} "
            f"registry={spec['expire_seconds']}")


def test_census_no_capped_collections(mongo_db):
    capped = []
    for c in mongo_db.list_collection_names():
        batch = mongo_db.command(
            "listCollections", filter={"name": c})["cursor"]["firstBatch"]
        if batch and batch[0].get("options", {}).get("capped"):
            capped.append(c)
    assert not capped, (
        "capped collection(s) found — silent oldest-doc eviction is the "
        f"same unledgered-removal class as a TTL index: {capped}")


def test_forbidden_collections_carry_no_expiring_index(mongo_db):
    """Audit A5 pin: hover_page_cache's orphaned 1h TTL index outlived its
    retired code by two weeks in the LIVE database — dropped 2026-08-11,
    and it stays gone. estimates / fixture_runs / upload_blobs are the
    permanent stores; an expiring index on any of them is data loss."""
    offenders = {}
    for coll in TTL_FORBIDDEN:
        info = mongo_db[coll].index_information() if coll in mongo_db.list_collection_names() else {}
        ttl = {n: v["expireAfterSeconds"] for n, v in info.items()
               if "expireAfterSeconds" in v}
        if ttl:
            offenders[coll] = ttl
    assert not offenders, f"expiring index on a forbidden collection: {offenders}"


def test_reaper_and_boot_purge_seams_registered():
    """The reaper class and the boot-time vero purge are named seams —
    a ledger with a known hole teaches the wrong habit."""
    assert "ttl_reaper" in SEAM_REGISTRY
    assert "vero_obsolete_boot_purge" in SEAM_REGISTRY
    # The registry text must direct readers to the census, and the census
    # walks the live DB — the claim and the instrument stay bound.
    assert "TTL_REAPER_REGISTRY" in SEAM_REGISTRY["ttl_reaper"]


def test_run_ttl_windows_mirror_registry():
    """run_archive.RUN_TTL_WINDOWS (drives reap-time on the card) must
    never disagree with the ledger's registry."""
    from run_archive import RUN_TTL_WINDOWS
    for (coll, _iname), spec in TTL_REAPER_REGISTRY.items():
        if coll in RUN_TTL_WINDOWS:
            assert RUN_TTL_WINDOWS[coll] == spec["expire_seconds"], coll
    for coll in RUN_TTL_WINDOWS:
        assert any(c == coll for (c, _i) in TTL_REAPER_REGISTRY), (
            f"{coll} has a card window but no registry entry")
