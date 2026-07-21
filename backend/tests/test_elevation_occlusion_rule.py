"""OCCLUSION RULE (Howard, ruled 2026-07-19 — defect: wall linework
rendered through the chase): no wall-plane line renders through an
occluding appendage. The chase projects 31" proud — wall-plane linework
(top-of-wall, fascia/soffit, course hatch, starter, grade) BREAKS at the
chase's edges; the chase's own outline + lap fill govern inside its
footprint. Mechanism: paint order (same family as the z-order fix) — the
chase glyph is the LAST wall-plane layer, with a full-height opaque fill.
Render-contract pins against the JSX source (the sheet is a live SVG)."""
from pathlib import Path

JSX = (Path(__file__).resolve().parent.parent.parent
       / "frontend" / "src" / "pages" / "ElevationSheet.jsx").read_text()


def test_chase_glyph_paints_after_every_wall_plane_layer():
    """BACK: chase glyph (occluder) renders AFTER wall rect, course
    hatch, fascia band, soffit line, starter and grade — wall lines
    cannot render through it."""
    glyph = JSX.index('data-testid="elevation-chase-glyph"')
    assert glyph > JSX.index('data-testid="elevation-wall-rect"')
    assert glyph > JSX.index("courseLines.map")
    assert glyph > JSX.index("SOFFIT (EAVES ONLY)")
    assert glyph > JSX.index("{S.fasciaLabel}")
    assert glyph > JSX.index("Starter + outside corners + grade")
    assert glyph > JSX.index(">GRADE</text>")


def test_chase_fill_is_full_height_and_opaque():
    """The occluding fill spans cap → grade (not just above-roofline) and
    is opaque — the footprint interior carries ONLY the chase's own lap
    fill (its hatch runs to grade)."""
    body = JSX[JSX.index('data-testid="elevation-chase-glyph"'):]
    body = body[:body.index("</g>\n        )}")]
    assert "height={wallBottom - chaseG.top}" in body
    assert 'fill="#fbfcfe"' in body
    assert "y < wallBottom - 1" in body  # chase lap hatch governs to grade


def test_fascia_label_recenters_clear_of_chase():
    """Annotation legibility rides the occlusion rule: the fascia label
    re-centers on the wider clear span instead of hiding under the
    chase footprint."""
    assert "const fasciaLabelX = chaseG" in JSX
    assert "x={fasciaLabelX} y={wallTop - 29.4}" in JSX


def test_front_cap_occludes_drawn_ridge():
    """FRONT sweep — PIN AMENDED BY RULING 2026-07-21 (P3, C-3): the
    dashed ridge reference band is RETIRED; the ridge is a DRAWN edge
    (elevation-roofline) and the cap box (opaque fill) paints AFTER it —
    the ridge line cannot render through the cap. Same rule covers the
    side profiles vs the new rake lines."""
    roofline = JSX.index('data-testid="elevation-roofline"')
    cap = JSX.index('data-testid="elevation-chase-cap"')
    profile = JSX.index('data-testid="elevation-chase-profile"')
    assert cap > roofline and profile > roofline
    cap_body = JSX[cap:]
    cap_body = cap_body[:cap_body.index("</g>\n        )}")]
    assert "ridgeMaxY" not in cap_body and "strokeDasharray" not in cap_body
    assert "capG.botY" in cap_body  # cap bottom anchors on the drawn ridge


def test_suppressed_chase_paints_nothing():
    """COLLISION GUARD interplay: a suppressed chase draws NO geometry —
    so it occludes nothing (wall linework runs unbroken; only the
    deviation callout + wall-data note carry the record)."""
    assert "chase && !chase.suppressed && chase.center_ft != null" in JSX
