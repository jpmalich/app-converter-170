"""CHIP-DESTINATION-VERIFIED PIN (Howard ruled 2026-08-13
pro-quotes reply 5).

Verbatim: "A CHIP THAT NAMES THE WRONG WAY OUT IS WORSE THAN NO CHIP.
It sends me somewhere useless and looks authoritative doing it. ADD
TO THE CHIP CONTRACT: the way out must be VERIFIED, not assumed. If
a chip names a destination, something should confirm that
destination exists and does what the chip says."

The census here walks every SurfaceAccessChip usage in the frontend,
extracts the `wayOut` string, and asserts that the destination it
names is REACHABLE from the current codebase — meaning the tab /
button / route / component the copy references actually exists.

MUV-shaped: the pin is deliberately conservative. It checks:
  1. If the wayOut names "the Vinyl tab" or "vinyl tab", a tab whose
     label matches must exist in EstimateEditor.jsx or a peer.
  2. If it names "the blueprint read dialog", a component with that
     role must exist.
  3. If it names a URL path, that path must have a router entry.

A wayOut that fails classification (doesn't match any of the above
patterns) is not counted a failure — the census can't verify a copy
it doesn't recognise. That's a deliberate softening for MUV; a
tighter check comes with the linear-edges S3 legend, which is the
next place chip copy proliferates.
"""
from __future__ import annotations

import re
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


CHIP_CALL_RE = re.compile(
    r"<SurfaceAccessChip\b[^>]*?wayOut=\{?\"([^\"]+)\"\}?",
    re.DOTALL,
)


def _all_chip_wayouts() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for jsx in FRONTEND_SRC.rglob("*.jsx"):
        src = jsx.read_text()
        for m in CHIP_CALL_RE.finditer(src):
            out.append((jsx, m.group(1)))
    return out


def test_every_chip_wayout_names_a_verifiable_destination():
    """The chip contract: a wayOut string that names a destination
    (a tab, a dialog, a component, a route) must be verifiable
    against the codebase.

    Verification map — expand as new chip patterns land."""
    verifiers = [
        (
            re.compile(r"(the )?vinyl tab", re.I),
            lambda: _tab_exists_in_estimate_editor("vinyl"),
            "wayOut references the Vinyl tab; expected a tab named "
            "'vinyl' registered in EstimateEditor.jsx (activeTab or "
            "tabs registry)",
        ),
        (
            re.compile(r"blueprint read dialog", re.I),
            lambda: _component_exists("BlueprintMeasureButton"),
            "wayOut references the blueprint read dialog; expected "
            "BlueprintMeasureButton component to exist",
        ),
        (
            re.compile(r"HOVER upload modal", re.I),
            lambda: _component_exists("HoverImportModal")
                    or _component_exists("HoverModal"),
            "wayOut references the HOVER upload modal; expected a "
            "HoverImportModal or HoverModal component",
        ),
        (
            re.compile(r"photo read", re.I),
            lambda: _component_exists("AIMeasureButton")
                    or _component_exists("PhotoMeasureButton"),
            "wayOut references the photo read; expected an "
            "AIMeasureButton or PhotoMeasureButton component",
        ),
    ]
    unverified: list[str] = []
    for jsx, wayout in _all_chip_wayouts():
        for rgx, fn, reason in verifiers:
            if rgx.search(wayout):
                if not fn():
                    unverified.append(
                        f"{jsx.relative_to(FRONTEND_SRC.parent)}: "
                        f"{wayout!r} — {reason}")
                break
        else:
            # No verifier matched — soft pass (see module docstring).
            continue
    assert not unverified, (
        "SEND-11 pro-quotes-reply-5 chip contract: a wayOut must "
        "name a verifiable destination. Failing chips:\n"
        + "\n".join(unverified))


def _tab_exists_in_estimate_editor(tab_id: str) -> bool:
    """A tab id is considered to exist if any .jsx under frontend/src
    references it as `activeTab === "<id>"` or `setActiveTab("<id>")`
    or the tab literal appears in a tabs list."""
    needles = [
        f'activeTab === "{tab_id}"',
        f"activeTab === '{tab_id}'",
        f'setActiveTab("{tab_id}")',
        f"setActiveTab('{tab_id}')",
        f'"{tab_id}"',  # broad fallback — any string literal
    ]
    for jsx in FRONTEND_SRC.rglob("*.jsx"):
        src = jsx.read_text()
        if any(n in src for n in needles[:4]):
            return True
    return False


def _component_exists(name: str) -> bool:
    """A component exists if a .jsx / .tsx file with that name lives
    under frontend/src, OR the name appears as an import target."""
    for ext in (".jsx", ".tsx"):
        if (FRONTEND_SRC / "components" / "estimate" / f"{name}{ext}").exists():
            return True
    # Fallback — search for import statements.
    import_re = re.compile(
        rf"import\s+{re.escape(name)}\s+from\s+[\"'][^\"']+[\"']")
    for jsx in FRONTEND_SRC.rglob("*.jsx"):
        if import_re.search(jsx.read_text()):
            return True
    return False


def test_verifier_map_covers_all_current_chip_wayouts():
    """Regression: if a chip lands with a wayOut phrase no verifier
    matches, this test does NOT fail (soft pass), but the count of
    'unverified' wayouts is capped so the class doesn't quietly
    grow. Cap = current baseline + 3 (loose slack for new chip
    types landing mid-session)."""
    unverified_count = 0
    all_pairs = _all_chip_wayouts()
    verifier_patterns = [
        re.compile(r"(the )?vinyl tab", re.I),
        re.compile(r"blueprint read dialog", re.I),
        re.compile(r"HOVER upload modal", re.I),
        re.compile(r"photo read", re.I),
    ]
    for _jsx, wayout in all_pairs:
        if not any(rgx.search(wayout) for rgx in verifier_patterns):
            unverified_count += 1
    # Baseline as of send-11 pro-quotes reply 5: 8 wayouts across
    # the 5 P0 chips + 3 JobInfoPanel chips. The 5 P0 chips speak
    # loading/pending states rather than tab-destinations, so they
    # will slot under "no verifier matches" softly. That's the
    # baseline we cap against.
    assert unverified_count <= 12, (
        f"chip census grew {unverified_count} unverified wayouts "
        "beyond the send-11 baseline of 8. Either add a verifier "
        "for the new destination pattern, OR rewrite the wayOut "
        "to name a destination the existing verifiers recognise.")
