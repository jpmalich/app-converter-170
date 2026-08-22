"""SEND-104 (still-owed) — THE SILENT-STRIP SWEEP, sealed by census.
Three members were each found by accident (notes 2026-07-31, hover
rebuild SEND-79, chase rows SEND-100). This census makes the class
structural: EVERY write that puts `lines` onto an estimate must either
re-run the overlay law on the value it writes (reapply_overlay_law —
what the law recomputes it cannot lose) or sit on the register below
with a reason a reviewer can check. A NEW lines-writing door fails this
test until it does one or the other — no fourth accidental member."""
import ast
import os

ROUTES = "/app/backend/routes"

# (file, why this door may write lines without re-running the law)
REGISTER = {
    "demo.py": ("provision-time seed of a FRESHLY-CREATED demo estimate "
                "from the catalog — no overlay zones can exist yet on an "
                "estimate that did not exist a moment ago"),
    "lp_admin.py": ("in-place tier reprice of the STORED rows "
                    "(reprice_lp_engine_lines maps over est['lines']); "
                    "nothing is rebuilt or merged — non-LP rows, chase "
                    "rows included, pass through object-identical"),
    "pdf_overlay.py": ("the overlay law's own write sites — "
                       "reapply/apply_overlay_to_takeoff output"),
}


def _lines_writes(path):
    src = open(path).read()
    tree = ast.parse(src)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute)
                and fn.attr in ("update_one", "update_many",
                                "insert_one", "replace_one")):
            continue
        if "estimates" not in ast.dump(fn.value):
            continue
        keys = [k.value for kw in ast.walk(node)
                for k in [kw] if isinstance(k, ast.Constant)]
        if "lines" in keys:
            hits.append(node.lineno)
    return src, hits


def test_every_lines_door_reruns_the_law_or_is_registered():
    offenders = []
    for fname in sorted(os.listdir(ROUTES)):
        if not fname.endswith(".py"):
            continue
        src, hits = _lines_writes(os.path.join(ROUTES, fname))
        if not hits:
            continue
        lines = src.split("\n")
        for ln in hits:
            if fname in REGISTER:
                continue
            window = "\n".join(lines[max(0, ln - 60):ln])
            if "reapply_overlay_law" not in window:
                offenders.append(f"{fname}:{ln}")
    assert not offenders, (
        "lines-writing door(s) neither re-run the overlay law nor sit "
        f"on the register: {offenders} — a client-shaped or rebuilt "
        "`lines` write that skips reapply_overlay_law is how chase rows "
        "(and every future law-owned row) get silently stripped "
        "(SEND-100 finding 2)")


def test_register_reasons_still_hold():
    """The register is not a mute list — each entry's reason is checked
    against the code it excuses."""
    # demo.py: the seed writes to an estimate created in the same
    # function (fresh — no zones can exist yet)
    demo = open(os.path.join(ROUTES, "demo.py")).read()
    assert "insert_one" in demo and '"lines": seeded' in demo
    # lp_admin.py: the write stores reprice_lp_engine_lines output of
    # the STORED lines — an in-place map, not a rebuild
    lpa = open(os.path.join(ROUTES, "lp_admin.py")).read()
    assert "reprice_lp_engine_lines(est.get(\"lines\")" in lpa
    # estimates.py PUT and PATCH both re-run the law (SEND-100)
    est = open(os.path.join(ROUTES, "estimates.py")).read()
    assert est.count("reapply_overlay_law") >= 2
    # hover.py rebuild re-runs the law (SEND-79 item 1)
    hov = open(os.path.join(ROUTES, "hover.py")).read()
    assert "tab_lines = await reapply_overlay_law" in hov
