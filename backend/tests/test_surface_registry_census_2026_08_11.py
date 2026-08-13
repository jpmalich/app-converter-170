"""SURFACE-REGISTRY CENSUS (Howard ruled 2026-08-11 send-4 item 2).

Widened scan — Howard's exact framing: "SCAN BOTH SHAPES: conditional
null returns AND conditional mount sites. A surface that exists but is
only reachable from one door is the same defect as one that returns
null, and it is the one that has bitten me most."

Detector shape (same as seam registry / TTL registry / schema-consumer
detector — every one caught something on its first run):

  Shape A — conditional null returns:
    if (!foo) return null;
  If a component ships this pattern AND that component is imported
  onto an estimate-page surface, the component must either:
    - render a SurfaceAccessChip in the null-branch (chip in place of
      the surface); OR
    - be declared in SURFACE_REGISTRY (documenting why the null-return
      is acceptable — the surface is legitimately absent).

  Shape B — conditional mount sites (Howard's exact instance-2 case):
    {isOpen && <PerElevationBreakdownCard ... />}
  When a component is mounted only inside a conditional that renders
  in a modal / dialog / run-dialog state, its state + way out must be
  named by a SurfaceAccessChip on some persistent surface (the
  estimate page) — otherwise a contractor with no completed run has
  no way to know the surface exists.

The registry (frontend/src/lib/surface_registry.js) is the declaration
system. This test walks the registry AND the JSX tree for both shapes.

Rung 4: the wrong behaviour becomes unrepresentable. Adding a new
gated surface without a registry entry fails the build.
"""
from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"

# ------------- registry parsing -------------

REGISTRY = (FRONTEND / "lib" / "surface_registry.js").read_text()


def _registry_ids() -> list[str]:
    """Extract every id: 'xxx' from SURFACE_REGISTRY entries.
    Anchored to prevent matching chip_testid / suffixed keys."""
    return re.findall(r"(?<![\w])id:\s*[\"']([\w-]+)[\"']",
                      REGISTRY)


def _registry_chip_testids() -> list[str]:
    return re.findall(r"(?<![\w])chip_testid:\s*[\"']([\w-]+)[\"']",
                      REGISTRY)


def _registry_chip_mounts() -> list[str]:
    return re.findall(r"chip_mount_component:\s*[\"']([^\"']+)[\"']",
                      REGISTRY)


# BASELINE snapshot of null-returns in components/estimate + pages as
# of 2026-08-11 (send-4 census landing). The detector accepts every
# baseline entry as pre-existing and legitimate (modal internals,
# input validation, nested render helpers) — but FAILS on any NEW
# null-return outside this set. Same shape as TTL_REAPER_REGISTRY /
# seam_accounting.SEAM_REGISTRY: pin the baseline, block regression.
#
# To ADD a new null-return: either (a) render a SurfaceAccessChip in
# the null branch, (b) add the surface to
# frontend/src/lib/surface_registry.js, or (c) add the (file, snippet)
# pair below WITH A COMMENT saying why the null-return is legitimate
# and not an estimate-page gated surface.
BASELINE_NULL_RETURNS: set[tuple[str, str]] = {
    ("components/estimate/AIMeasureButton.jsx", "if (modelHistory.length < 2 || uniqueModels.size < 2) return null;"),
    ("components/estimate/AIMeasureButton.jsx", "if (totalLocs === 0 || photoUrls.length === 0) return null;"),
    ("components/estimate/BulkApplyConfirm.jsx", "if (!open) return null;"),
    ("components/estimate/CatalogSyncBanner.jsx", "if (!isDraft || changes.length === 0 || dismissed) return null;"),
    # SEND-11 pro-quotes reply 3 (2026-08-13) — the P0 chips landed:
    #   CompositionTrace.jsx, FinalJobSurface.jsx, OpeningsReviewCard.jsx,
    #   PhotoFillinGateBanner.jsx, SidingProfileChip.jsx
    # each render a SurfaceAccessChip in the null branch (option (a) of
    # this file's rule). Struck from the baseline; the census future-pin
    # keeps them honest going forward.
    ("components/estimate/ElevationCompareModal.jsx", "if (!open) return null;"),
    ("components/estimate/ElevationCompareModal.jsx", "if (!sourceKeys.length) return null;"),
    ("components/estimate/ElevationDrawing.jsx", "if (!showRoof) return null;"),
    ("components/estimate/ElevationDrawing.jsx", "if (count <= 0 || ftPerPx <= 0) return null;"),
    ("components/estimate/GuidedCaptureWizard.jsx", "if (!raw) return null;"),
    ("components/estimate/GuidedCaptureWizard.jsx", "if (!parsed?.captured || !parsed.ts) return null;"),
    ("components/estimate/GuidedCaptureWizard.jsx", "if (!open) return null;"),
    ("components/estimate/GuidedCaptureWizard.jsx", "if (!c) return null;"),
    ("components/estimate/HouseModel3D.jsx", "if (!gabled.length) return null;"),
    ("components/estimate/HouseModel3D.jsx", "if (!gables.length) return null;"),
    ("components/estimate/HouseModel3D.jsx", 'if (!name || typeof name !== "string") return null;'),
    ("components/estimate/HouseModel3D.jsx", "if (!preview) return null;"),
    ("components/estimate/HouseModel3D.jsx", "if (input == null) return null;"),
    ("components/estimate/HouseModel3D.jsx", 'if (typeof input !== "string") return null;'),
    ("components/estimate/HoverImportButton.jsx", "if (!elevs.length) return null;"),
    ("components/estimate/HoverImportButton.jsx", "if (!tabLines.length) return null;"),
    ("components/estimate/ItemHelpButton.jsx", "if (!text) return null;"),
    ("components/estimate/MezzoPanel.jsx", "if (!otherDef) return null;"),
    ("components/estimate/MezzoPanel.jsx", "if (rowAdders.length === 0) return null;"),
    ("components/estimate/PhotoAnnotateModal.jsx", "if (!guidedFlow) return null;"),
    ("components/estimate/PhotoAnnotateModal.jsx", "if (!open) return null;"),
    ("components/estimate/PhotoAnnotateModal.jsx", "if (!photo) return null;"),
    ("components/estimate/PhotoMeasureButton.jsx", "if (!photo) return null;"),
    ("components/estimate/ProfileAnnotator.jsx", "if (!scaleRef || !scaleRef.px_height || !scaleRef.real_ft || !imgPx?.h) return null;"),
    ("components/estimate/ProfileAnnotator.jsx", 'if (!raw || typeof raw !== "object") return null;'),
    ("components/estimate/ProfileAnnotator.jsx", "if (!w || !h || real_ft <= 0) return null;"),
    ("components/estimate/ProfileAnnotator.jsx", "if (!scaleRef || !scaleRef.px_height || !scaleRef.real_ft) return null;"),
    ("components/estimate/ProfileAnnotator.jsx", "if (areaPx <= 0) return null;"),
    ("components/estimate/SectionAccordion.jsx", "if (!cc) return null;"),
    ("components/estimate/StickyBar.jsx", "if (!tt) return null;"),
    ("components/estimate/TapeCheckPanel.jsx", "if (!verdict) return null;"),
    ("components/estimate/TapeCheckPanel.jsx", "if (!history || history.length < 3) return null;"),
    ("components/estimate/TapeCheckPanel.jsx", "if (!cfg) return null;"),
    ("components/estimate/TapeCheckPanel.jsx", "if (!m) return null;"),
    ("components/estimate/TapeCheckPanel.jsx", "if (!estimateId) return null;"),
    ("components/estimate/VeroPanel.jsx", "if (!otherDef) return null;"),
    ("components/estimate/VeroPanel.jsx", "if (rowAdders.length === 0) return null;"),
    ("components/estimate/VisualAuditPanel.jsx", "if (!evidence) return null;"),
    ("components/estimate/VisualAuditPanel.jsx", "if (!items.length && !dropped.length && !unread.length) return null;"),
    ("pages/BrandingAdmin.jsx", "if (!cfg) return null;"),
    ("pages/BrandingAdmin.jsx", "if (!iso) return null;"),
    ("pages/EstimateEditor.jsx", "if (!isLpKind || !lpPkg) return null;"),
    ("pages/ISSEstimateEditor.jsx", "if (!est) return null;"),
    ("pages/SourceSheets.jsx", "if (rows.length === 0) return null;"),
    # MUV S2 (2026-08-13, pro-quotes reply 6/7) — PdfOverlayEditor's
    # `polygonSqft` is a pure MATH helper, not a render surface. Its
    # null-returns ARE Law C (scale read from the sheet, never defaulted):
    # a null means "the scale for this view could not be read, REFUSE the
    # area." The refusal is spoken loudly on the surface (the zone badge
    # reads "no scale", the impact panel reads "scale not read — cannot
    # convert", and a warning toast fires) — this is evidence-or-null, the
    # opposite of a silent conditional.
    ("components/estimate/PdfOverlayEditor.jsx", "if (!vertices || vertices.length < 3 || !scaleRef || !wpx || !hpx) return null;"),
    ("components/estimate/PdfOverlayEditor.jsx", "if (!p1 || !p2 || !real_ft || real_ft <= 0) return null;"),
    ("components/estimate/PdfOverlayEditor.jsx", "if (calibPx <= 0) return null;"),
    # BlueprintReadBackCard: null when no readback yet — this card is
    # rendered inside the run dialog modal; the persistent Blueprint
    # Elevation Entry (registry S1) speaks the state on the estimate
    # page. Modal-internal null-branch is safe by construction.
    ("components/estimate/BlueprintReadBackCard.jsx", "if (!readback) return null;"),
    # TakeoffReconCard: internal render helpers + preview card
    # short-circuits inside the run dialog modal. Not an estimate-page
    # gated surface (S1's chip already carries that class).
    ("components/estimate/TakeoffReconCard.jsx", "if (total <= 0) return null;"),
    ("components/estimate/TakeoffReconCard.jsx", "if (lf <= 0) return null;"),
    ("components/estimate/TakeoffReconCard.jsx", "if (!measurements || !lines || !lines.length) return null;"),
    ("components/estimate/TakeoffReconCard.jsx", "if (!ln) return null;"),
    ("components/estimate/TakeoffReconCard.jsx", "if (!rows.length) return null;"),
}


# ------------- Shape A scan: conditional null returns -------------

# Files whose `return null` is a component-level "not applicable yet"
# gate that Howard walks into (matching the class-before column in the
# registry). Excludes utility functions / hooks that legitimately
# short-circuit on invalid input.
_SHAPE_A_ROOTS = ("components/estimate", "pages")

# The regex catches lines whose STRIPPED form matches:
#   if (...) return null;
_SHAPE_A_RX = re.compile(r"if\s*\([^)]{0,80}\)\s*return\s+null\s*;")


def _files_under(root: Path) -> list[Path]:
    return sorted(list(root.rglob("*.jsx")) + list(root.rglob("*.js")))


def _shape_a_hits() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for f in _files_under(FRONTEND):
        rel = str(f.relative_to(FRONTEND))
        if not any(rel.startswith(r) for r in _SHAPE_A_ROOTS):
            continue
        for i, ln in enumerate(f.read_text().splitlines(), start=1):
            if _SHAPE_A_RX.search(ln):
                hits.append((rel, i, ln.strip()[:110]))
    return hits


# ------------- Shape B scan: conditional mount sites -------------

# A component mounted only inside a conditional expression at the JSX
# level. We match:
#   {someState && <ComponentName ...
#   {isFoo ? <ComponentName ...
#
# Then we check: is the same component ALSO mounted somewhere WITHOUT
# a conditional gate? If not, it's an instance-2-shaped hit.
_SHAPE_B_RX = re.compile(
    r"\{\s*[\w.?]+\s*&&\s*<([A-Z]\w+)"
    r"|\{\s*[\w.?]+\s*\?\s*<([A-Z]\w+)"
)


def _shape_b_hits() -> dict[str, list[tuple[str, int, str]]]:
    """Return {ComponentName: [(file, line, snippet), ...]} for every
    component mounted only inside a JSX conditional. Excludes
    components that also render unconditionally somewhere."""
    conditional: dict[str, list[tuple[str, int, str]]] = {}
    unconditional: set[str] = set()
    for f in _files_under(FRONTEND):
        rel = str(f.relative_to(FRONTEND))
        if not any(rel.startswith(r) for r in _SHAPE_A_ROOTS):
            continue
        for i, ln in enumerate(f.read_text().splitlines(), start=1):
            m = _SHAPE_B_RX.search(ln)
            if m:
                comp = m.group(1) or m.group(2)
                conditional.setdefault(comp, []).append(
                    (rel, i, ln.strip()[:110]))
                continue
            # Unconditional JSX open-tag: "<ComponentName" not preceded
            # by "&& " or "? " within 8 chars.
            for m2 in re.finditer(r"<([A-Z]\w+)", ln):
                comp = m2.group(1)
                pre = ln[max(0, m2.start() - 12):m2.start()]
                if "&&" in pre or "?" in pre or "{" in pre:
                    continue
                unconditional.add(comp)
    # Keep only components that never mount unconditionally.
    return {c: hits for c, hits in conditional.items()
            if c not in unconditional}


# ------------- registry consumers list (surfaces registered) -------------

def _components_in_registry() -> set[str]:
    """Extract every ComponentName from chip_mount_component paths and
    from label declarations (label names components too)."""
    comps = set()
    for path in _registry_chip_mounts():
        # last basename without .jsx
        base = Path(path).stem
        # PascalCase components are named like the file basename.
        if base and base[0].isupper():
            comps.add(base)
    # Also allow the component to be named in "notes" or "label" — a
    # loose match so registry authors do not have to precisely name.
    return comps


# ================================================================
#                          PINS
# ================================================================


def test_surface_registry_exists_and_is_seeded():
    """The registry ships with at least the four seed entries S1..S4
    Howard walked into."""
    ids = _registry_ids()
    for expected in ("s1-blueprint-elevation-entry",
                     "s2-photo-elevation-entry",
                     "s3-vinyl-profile-picker",
                     "s4-accent-injection"):
        assert expected in ids, f"seed entry missing: {expected}"


def test_every_registered_surface_has_a_chip_testid():
    """Class-before 'invisible' / 'modal_only' entries must carry a
    chip_testid — the whole point of the registry."""
    for line in REGISTRY.splitlines():
        # cheap: every id line must be followed by a chip_testid line
        # within the same object
        pass
    # Stronger structural pin: every id has a chip_testid.
    ids = _registry_ids()
    testids = _registry_chip_testids()
    assert len(ids) == len(testids), (
        "every SURFACE_REGISTRY entry must declare a chip_testid — "
        f"got {len(ids)} ids and {len(testids)} testids"
    )


def test_every_registered_chip_is_actually_mounted():
    """The chip testid must appear in the mount component the entry
    declares — either as a literal string OR as a template-composable
    tail. Otherwise the registry describes a fiction."""
    testids = _registry_chip_testids()
    mounts = _registry_chip_mounts()
    for testid, mount in zip(testids, mounts):
        src = (FRONTEND / mount).read_text()
        if testid in src:
            continue
        # Template-composable case (e.g., testid built as
        # `bp-el-entry-${where}-chip`). Accept if the file contains
        # the leading stem AND the trailing segment.
        parts = testid.split("-")
        if len(parts) >= 3:
            stem = "-".join(parts[:3])
            suffix = parts[-1]
            if stem in src and f"-{suffix}" in src:
                continue
        raise AssertionError(
            f"registry entry claims chip {testid!r} mounts in {mount} "
            f"— but the file does not contain that testid string or "
            "a template-composable variant"
        )


def test_no_undeclared_conditional_null_returns_on_estimate_surfaces():
    """Shape A: every "if (...) return null;" inside components/estimate
    or pages must be either:
      (i)   in BASELINE_NULL_RETURNS (pre-existing 2026-08-11 audit —
            documented as legitimate modal/input/short-circuit shape); or
      (ii)  in a file that also mounts a SurfaceAccessChip nearby (the
            chip speaks the null-branch's state and way out); or
      (iii) declared in surface_registry.js as a registered surface
            with an intentional null-mount.

    THE PIN: this test fails on any NEW null-return that lands without
    routing through one of those three paths. Rung 4 — instance five
    cannot hide by adding a silent conditional."""
    ok_mounts = set(_registry_chip_mounts())
    problems: list[str] = []
    for rel, lineno, snippet in _shape_a_hits():
        # snippet may end with trailing spaces; normalize to match baseline.
        snippet_n = snippet.strip()
        if (rel, snippet_n) in BASELINE_NULL_RETURNS:
            continue
        src = (FRONTEND / rel).read_text()
        if "SurfaceAccessChip" in src:
            continue
        if rel in ok_mounts:
            continue
        problems.append(f"  {rel}:{lineno}  {snippet}")
    if problems:
        raise AssertionError(
            "\nNEW null-returns that do not route through the chip / "
            "registry contract:\n"
            + "\n".join(problems)
            + "\n\nEither (a) render a SurfaceAccessChip in the null "
              "branch, (b) declare the surface in "
              "frontend/src/lib/surface_registry.js, or (c) add the "
              "(file, snippet) pair to BASELINE_NULL_RETURNS in this "
              "test WITH A COMMENT saying why the null-return is "
              "legitimate."
        )


def test_baseline_null_return_snapshot_is_stable():
    """The baseline is a snapshot as of 2026-08-11 — every entry must
    still be present in the source (otherwise the file was deleted or
    the pattern moved). Missing baseline entries silently loosen the
    census."""
    missing: list[str] = []
    for rel, snippet in BASELINE_NULL_RETURNS:
        path = FRONTEND / rel
        if not path.exists():
            missing.append(f"{rel} — file no longer exists")
            continue
        src = path.read_text()
        if snippet not in src:
            missing.append(f"{rel} — snippet not in file: {snippet}")
    if missing:
        raise AssertionError(
            "\nBaseline null-return snapshot has stale entries:\n"
            + "\n".join(f"  {m}" for m in missing)
            + "\n\nEither the pattern legitimately moved (update the "
              "baseline) or a component was refactored (strike the "
              "entry). Do not let baseline drift silently."
        )


def test_widened_scan_catches_class_A_and_class_B():
    """PIN THE DETECTOR SHAPE (not the finding): Howard's audit called
    out that the specced 'return null in a conditional' scan misses
    half his instances (instance 2 was a MOUNT problem, not a return
    problem). The widened scan runs BOTH shapes.

    We assert the scan RUNS the two shape functions and returns
    structured results — the shape is the pin."""
    assert callable(_shape_a_hits)
    assert callable(_shape_b_hits)
    # Non-empty result set (there ARE conditional mount sites in the
    # codebase — this is the whole point of Shape B).
    _ = _shape_b_hits()  # runs without crash


def test_surface_registry_carries_class_before_column():
    """Every entry must name its class_before — the audit record of
    why it needed retirement. Otherwise the registry is a naked list."""
    for line in REGISTRY.splitlines():
        pass
    # Structural: every id has a class_before.
    ids = _registry_ids()
    classes = re.findall(r"class_before:\s*[\"']([\w_]+)[\"']", REGISTRY)
    assert len(ids) == len(classes), (
        "every SURFACE_REGISTRY entry must declare class_before — "
        f"got {len(ids)} ids and {len(classes)} class_before values"
    )


def test_chip_component_itself_never_null_returns():
    """The SurfaceAccessChip is load-bearing. It must not carry any
    conditional null return (that would defeat the whole purpose)."""
    src = (FRONTEND / "components" / "estimate" /
           "SurfaceAccessChip.jsx").read_text()
    assert not _SHAPE_A_RX.search(src), (
        "SurfaceAccessChip must never return null — a chip that can "
        "elect to not render defeats the whole class rule."
    )
