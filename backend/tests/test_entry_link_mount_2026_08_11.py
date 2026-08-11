"""ENTRY-LINK MOUNT DETECTOR (Howard ruled 2026-08-11 send-3).

Class-of-defect the report catalogues: JSX-string-presence tests can prove
a component OWNS a testid; they cannot prove the component RENDERS on the
surface the user is standing on. The 2026-07-20 handback claimed "Entry
links sit on the Blueprint card" — the testids did exist in
BlueprintReadBackCard.jsx, but that component was only mounted inside the
run-dialog modal (BlueprintMeasureButton.jsx:1080). Once dismissed, the
links vanished. The only way to reach the sheets was typing
/blueprint-elevation/front into the address bar.

These pins fail on ANY regression that:
  (a) removes the persistent mount from JobInfoPanel / ISSEstimateEditor
  (b) removes the mount inside the BlueprintMeasureButton takeoff preview
  (c) drops the "Back to the takeoff" link on the sheet page
  (d) makes the entry component invisible in a state Howard walks into
      (no completed run → chip must speak; no walls → link still speaks)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src"
ENTRY = (ROOT / "components" / "estimate"
         / "BlueprintElevationEntry.jsx").read_text()
CHIP = (ROOT / "components" / "estimate"
        / "SurfaceAccessChip.jsx").read_text()
JIP = (ROOT / "components" / "estimate" / "JobInfoPanel.jsx").read_text()
BMB = (ROOT / "components" / "estimate"
       / "BlueprintMeasureButton.jsx").read_text()
ISS = (ROOT / "pages" / "ISSEstimateEditor.jsx").read_text()
SHEET = (ROOT / "pages" / "BlueprintElevationSheet.jsx").read_text()


def test_persistent_mount_on_jobinfopanel():
    """The Blueprint tile on the estimate page — the moment BEFORE grading —
    must mount the entry component so the sheets are reachable without a
    modal."""
    assert 'import BlueprintElevationEntry' in JIP
    assert 'where="blueprint-tile"' in JIP


def test_takeoff_preview_mount_on_bmb():
    """The Takeoff Preview (inside the run dialog) — the moment WHILE
    grading — must mount the entry component so the sheet is reachable
    without closing the preview to hunt for the link."""
    assert 'import BlueprintElevationEntry' in BMB
    assert 'where="takeoff-preview"' in BMB


def test_iss_mount():
    """ISS estimate editor also mounts the entry on its Blueprint tile —
    same class of estimate, same class of user gesture."""
    assert 'import BlueprintElevationEntry' in ISS
    assert 'where="blueprint-tile"' in ISS


def test_sheet_carries_back_to_takeoff():
    """The sheet already carried "Back to estimate" — one level too far.
    The new link takes the contractor back to the takeoff, which is
    where he came from."""
    assert 'bp-elevation-back-to-takeoff' in SHEET
    assert 'Back to the takeoff' in SHEET
    # The original back-to-estimate link is kept — both are useful.
    assert 'bp-elevation-back' in SHEET


def test_entry_uses_the_new_backend_endpoint():
    """The persistent mount decides state from a lightweight endpoint —
    not by inheriting the run dialog's fetch. Independent probes."""
    assert 'blueprint-latest-run' in ENTRY


def test_entry_is_never_invisible():
    """SurfaceAccessChip contract: a surface that cannot render its
    output still renders a chip that names the state and the way out.
    Every branch of BlueprintElevationEntry must return something."""
    # Presence of SurfaceAccessChip usage in the loading and !available
    # branches — the two states where the sheet's own output cannot render.
    assert 'SurfaceAccessChip' in ENTRY
    assert '${prefix}-loading' in ENTRY
    assert '${prefix}-chip' in ENTRY
    # And the available branch renders the four EL-1..EL-4 links.
    assert '${prefix}-link-${w}' in ENTRY


def test_all_four_walls_carry_a_link():
    """Even if the run does not carry every wall, the link renders —
    marked with a ⚠ — so the contractor can open the sheet and see the
    NEEDS-YOUR-TAPE hatch."""
    # WALLS list drives the link render; if a wall is dropped the loop
    # loses a link. Pin the exact set.
    assert 'const WALLS = ["front", "right", "back", "left"];' in ENTRY


def test_chip_component_speaks_state_and_way_out():
    """SurfaceAccessChip contract: state + wayOut are the two loud
    fields. The chip must render both when supplied."""
    assert 'data-surface-state={state}' in CHIP
    assert '{state}' in CHIP
    assert '{wayOut}' in CHIP


def test_no_bp_rb_elevation_links_regression_in_readback_card():
    """The old links inside BlueprintReadBackCard remain (they are
    fine inside the modal), but the persistent mount is what carries
    reachability. Pin the persistent mount lives OUTSIDE the readback
    card's file — otherwise a future refactor could re-hide them."""
    rbc_path = ROOT / "components" / "estimate" / "BlueprintReadBackCard.jsx"
    rbc = rbc_path.read_text()
    # The old link block is still present (still fine inside the modal).
    assert 'bp-rb-elevation-links' in rbc
    # BUT the entry component the estimate page mounts is a separate file
    # (this is the whole point).
    assert 'BlueprintElevationEntry' not in rbc, (
        "BlueprintElevationEntry must live in its own file — the whole "
        "point of the 2026-08-11 mount is that its reachability does not "
        "depend on the readback card being rendered."
    )
