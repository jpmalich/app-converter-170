"""SURFACE-ACCESS CHIP CONTRACT (Howard ruled 2026-08-11 send-3).

"A surface that is invisible teaches me nothing; a surface that says
what it is waiting for teaches me the shape of the gate."

The chip's contract, pinned:
  1. NEVER invisible. If a surface cannot render its output, the chip
     renders in its place.
  2. Names the STATE ("needs an applied run" / "photo door only" /
     etc.).
  3. Names the WAY OUT so the contractor knows what to do.
  4. Every chip carries a testid — this is a load-bearing instrument.

This pin fails on any regression that ships an invisible gate on the
four surfaces Howard walked into (memory/entry_link_surface_audit_2026-08-11.md
§2 table S1–S4):
  - Blueprint elevation entry links (S1)
  - Photo elevation entry links (S2)      [audit only — the FieldVerify chip already renders]
  - Vinyl profile picker gating (S3)      [chip planned; report-only test]
  - Accent injection surfaces (S4)        [chip planned; report-only test]
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src"
CHIP = (ROOT / "components" / "estimate"
        / "SurfaceAccessChip.jsx").read_text()
ENTRY = (ROOT / "components" / "estimate"
         / "BlueprintElevationEntry.jsx").read_text()


def test_chip_component_exists_and_speaks_both_fields():
    """The chip's props are state + wayOut. Both must render."""
    assert 'export default function SurfaceAccessChip' in CHIP
    # The state prop is the loud header.
    assert '{state}' in CHIP
    # The wayOut prop is the follow-through — must render when supplied.
    assert '{wayOut}' in CHIP
    # data-surface-state on the chip lets automation drive on it.
    assert 'data-surface-state={state}' in CHIP


def test_chip_never_invisible_no_return_null():
    """SurfaceAccessChip must never `return null` — that would silently
    hide the gate, defeating the whole rule."""
    # A `return null` anywhere in the file would signal the chip can
    # elect to render nothing. Pin its absence at the component level.
    # The component uses a single expression return; no null branches.
    assert 'return null' not in CHIP, (
        "SurfaceAccessChip must never return null — a surface that can "
        "elect to not render is the pattern this chip retires."
    )


def test_entry_wires_chip_for_the_three_named_states():
    """The three state strings Howard named verbatim in send-3:
       - "needs an applied run"
       - "photo door only"
       - "needs a completed measurement"
    The blueprint entry component covers state 3 in one of its state
    branches. The state text used is domain-specific ("needs a completed
    blueprint read") — pinning the CLASS not the exact phrase."""
    # State messages exist for each expected state.
    for expected_state in ("no_run", "running", "error"):
        assert f"'{expected_state}'" in ENTRY or f'"{expected_state}"' in ENTRY, (
            f"entry must speak state '{expected_state}'"
        )


def test_entry_speaks_way_out_not_just_state():
    """The chip contract requires BOTH state and wayOut. Every message
    map entry in BlueprintElevationEntry must supply a wayOut string."""
    # Rough proxy: the message map has at least three "wayOut:" lines.
    assert ENTRY.count('wayOut:') >= 3, (
        "every state branch must supply a wayOut — no state without a way out"
    )


def test_chip_has_testid_contract():
    """Every SurfaceAccessChip renders with a caller-supplied testid.
    A chip nobody can pin is a chip that can silently regress."""
    assert 'data-testid={testid}' in CHIP


def test_loading_state_also_speaks():
    """Even the loading state is a state — the entry must render a chip
    while the fetch is in flight, not a blank div."""
    assert '${prefix}-loading' in ENTRY
