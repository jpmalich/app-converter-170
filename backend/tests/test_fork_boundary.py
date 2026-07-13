"""CI DRIFT CHECK (approved 2026-07-13, ships with the domain manifest):
the build FAILS on fork-boundary violations so forkability stays
continuously true — cross-domain imports into the LP core, unauthorized
LP imports outside the enumerated seams, untagged LP data."""
import ast
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import lp_domain_manifest as M  # noqa: E402

STDLIB_ALLOWED = {
    "__future__", "math", "re", "os", "json", "typing", "datetime",
    "dataclasses", "functools", "itertools", "collections", "hashlib",
    "secrets", "copy", "enum",
}
LP_CORE_NAMES = {Path(p).stem for p in M.LP_CORE_MODULES}


def _imports(path: Path):
    tree = ast.parse(path.read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    return mods


def test_lp_core_is_pure():
    # LP core modules: stdlib + intra-LP only — plus the single pinned
    # KNOWN_DEBT edge (lp_package → routes.hover, the S4 carve).
    for rel in M.LP_CORE_MODULES:
        mods = _imports(BACKEND / rel)
        debt = M.KNOWN_DEBT_IMPORTS.get(rel, set())
        illegal = mods - STDLIB_ALLOWED - LP_CORE_NAMES - debt
        assert not illegal, f"{rel} imports outside the fork boundary: {sorted(illegal)}"


def test_no_unauthorized_lp_imports():
    # Any backend file importing lp_* must be LP domain, an enumerated
    # seam, a migration/one-time script, or a test.
    allowed = ({str(BACKEND / p) for p in M.LP_CORE_MODULES}
               | {str(BACKEND / p) for p in M.LP_ROUTERS}
               | {str(BACKEND / p) for p in M.SEAMS}
               | {str(BACKEND / p) for p in M.MIGRATIONS})
    offenders = []
    for py in list(BACKEND.glob("*.py")) + list((BACKEND / "routes").glob("*.py")):
        if str(py) in allowed or py.name.startswith("test_"):
            continue
        try:
            mods = _imports(py)
        except SyntaxError:
            continue
        hit = {m for m in mods if m in LP_CORE_NAMES or m == "lp_domain_manifest"}
        hit -= {"lp_domain_manifest"}
        if hit:
            offenders.append((py.name, sorted(hit)))
    assert not offenders, f"unenumerated LP imports (add a seam deliberately or remove): {offenders}"


def test_lp_routers_data_tagging():
    # LP routers may only touch lp_-prefixed collections or the shared
    # allowlist; settings doc ids used by LP surfaces must be lp_-prefixed.
    coll_re = re.compile(r"db\.([a-z_][a-z0-9_]*)")
    for rel in M.LP_ROUTERS:
        src = (BACKEND / rel).read_text()
        for coll in set(coll_re.findall(src)):
            ok = coll.startswith(M.LP_COLLECTION_PREFIX) or coll in M.SHARED_COLLECTIONS_ALLOWED
            assert ok, f"{rel} touches untagged collection db.{coll}"
    admin = (BACKEND / "routes/lp_admin.py").read_text()
    for m in re.findall(r'(?:TIER_DOC_ID|MODE_DOC_ID)\s*=\s*"([^"]+)"', admin):
        assert m.startswith(M.LP_SETTINGS_ID_PREFIX), f"settings doc id not lp_-tagged: {m}"


def test_lp_estimate_fields_prefixed():
    # LP routers writing to the SHARED estimates collection must use
    # lp_-prefixed field paths ($set/$unset on db.estimates only —
    # lp_-prefixed collections are tagged at the collection level).
    call_re = re.compile(r"db\.estimates\.update_one\((?:.|\n)*?\{\s*\"\$(?:set|unset)\"\s*:\s*\{((?:.|\n)*?)\}", re.M)
    for rel in M.LP_ROUTERS:
        src = (BACKEND / rel).read_text()
        for block in call_re.findall(src):
            for field in re.findall(r'[f]?"([a-zA-Z_][a-zA-Z0-9_.{}]*)"\s*:', block):
                root = field.split(".")[0]
                # "lines" is the shared array — its LP members carry
                # tab="lp_smart" (tagged at the LINE level; tier reprice).
                assert root.startswith("lp_") or root == "lines", (
                    f"{rel} writes untagged estimate field: {field}")


def test_manifest_files_exist():
    for rel in M.LP_CORE_MODULES + M.LP_ROUTERS + M.SEAMS:
        assert (BACKEND / rel).exists(), f"manifest references missing file: {rel}"
