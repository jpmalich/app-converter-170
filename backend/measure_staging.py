"""ONE MEASUREMENT STAGING — the single shared aggregation layer (Howard ruled
2026-08-01, Three Doors build step 1: "three aggregation copies collapse to one").

Every door (HOVER / BLUEPRINT / PHOTO) stages measurements through the helpers
here. Door-specific SOURCE ADAPTERS (photo clamps/dedupe/snap, blueprint
printed-dims trust and pitch-computed rise) stay in their routes — but the MATH
(gable factor, wall-area walk, opening bucketing, door-count roll-up, the
window-openings builder, the no-intake-rounding policy) has exactly one copy.
A fix here reaches all three doors; a second copy anywhere is a regression.

RULING 1 — GABLE FACTOR = 0.70, one sealed constant, all doors, all families
(C4 angle-cut coverage convention, ruled 2026-07-13; sealed across doors
2026-08-01. The blueprint door's pre-C4 0.5 true-triangle retired).

RULING 7 — ROUND ONCE, AT THE ORDER LAYER. Full-precision measurements carried
end to end; no door rounds on the way in. Rounding happens exactly once, where
a number becomes an orderable quantity (the _build_lines extract formulas and
_order_whole_units).
"""
import uuid

GABLE_FACTOR = 0.70
# RULING X (Howard sealed send-23): 0.70 is a TRADE CONVENTION (≈1.4× the
# geometric ½·width·rise — it encodes an allowance), NOT an invented
# constant. It stays for a DERIVED gable and must be LABELLED wherever it is
# applied so a reader can tell an allowanced gable from a measured one. A
# DRAWN/traced gable replaces it entirely (Law A) — that binding is a build,
# see the send-23 report.
GABLE_CONVENTION_LABEL = "0.70 gable convention (trade allowance, ≈1.4× geometric ½·width·rise)"
# SEND-74 (Howard, 2026-08-21) — GABLE BASIS, a strict BINARY. Every
# gable quantity carries exactly ONE of two bases, never both, never a
# third:
#   TRACED      → the drawn triangle's true area, NO factor.
#   NOT TRACED  → area × 0.70 field factor (safety margin for an
#                 approximate gable measurement).
# The label rides the quantity to the sheet, the read-back card and the
# money line — two gables on one house priced on different bases must
# be tellable apart by the reader.
GABLE_BASIS_TRACED = "traced"
GABLE_BASIS_FIELD_FACTOR = "field_factor_0_70"
GABLE_BASES = frozenset({GABLE_BASIS_TRACED, GABLE_BASIS_FIELD_FACTOR})


def gable_basis_label(basis: str, sqft=None) -> str:
    """The SEND-74 mandated sentences, verbatim."""
    if basis == GABLE_BASIS_TRACED:
        if sqft is not None:
            return (f"gable traced from the drawing — {sqft} ft², "
                    "no field factor")
        return ("gable traced from the drawing — no field factor "
                "(no evidence scale on this view for the ft² figure)")
    if basis == GABLE_BASIS_FIELD_FACTOR:
        return ("gable not traced — 0.70 field factor applied (safety "
                "margin for an approximate gable measurement)")
    raise ValueError(f"unknown gable basis: {basis!r}")


def eaves_from_walls(walls: list, raw_eaves) -> float:
    """THE defensive eaves rule (one copy — Iter 57w, extended to photo per
    ruled fix-it 10a, 2026-08-01). Models historically return the full
    floor-plan perimeter as eaves_lf — only correct for hip roofs. When any
    wall is a gable end, gutters run the NON-gable walls only: recompute
    eaves as the sum of non-gable wall widths. Falls back to the raw read
    when no gables or no usable widths.

    SUBSET-AWARE (Howard ruled 2026-08-14 send-15 H): a NON-gable wall
    whose width was killed cannot silently drop out of the sum — that is
    the silent under-count Report 2 named. If any contributing width is
    NOT derivable, the correction is refused and the raw read stands (the
    honest fallback), never a silently-short corrected number."""
    any_gable = any(float(w.get("gable_triangle_height_ft") or 0) > 0 for w in walls)
    if any_gable:
        contributors = [w for w in walls
                        if float(w.get("gable_triangle_height_ft") or 0) <= 0]
        widths = [wall_width_for_pricing(w) for w in contributors]
        if any(not ok for (_v, ok, _s, _m) in widths):
            return float(raw_eaves or 0)   # a killed width — refuse to short
        corrected = sum(v for (v, _ok, _s, _m) in widths)
        if corrected > 0:
            return corrected
    return float(raw_eaves or 0)


def wall_body_gross_sqft(w: dict) -> tuple[float, list, dict]:
    """PER-WALL HEIGHT VARIATION + SEGMENT-LEVEL PARTIAL DERIVABILITY
    (Howard ruled 2026-08-07; partial-derivability ruled earlier and
    BUILT 2026-08-14 send-13).

    A facade is SEGMENTS at their own eave heights — the garage half of a
    front wall sides at ~10', never at the main body's height. When a wall
    carries height_segments, EACH segment derives on its OWN width×height:
      * derivable segments (w>0 AND h>0) sum into the gross;
      * a KILLED segment is NAMED not-derivable and its area is simply
        ABSENT. It is NEVER covered by falling back to the top-level
        width×height rectangle — that fallback is the silent inflation
        Howard ruled against on the front-segment question (it would
        credit a dead segment's area at the full wall width). The wall
        total becomes a SUBSET and says so.
    A wall with NO segments derives from its own width×height — there the
    rectangle is the PRIMARY measurement, not a fallback.

    Returns (gross, segs_used, deriv):
      deriv = {has_segments, derivable, subset, not_derivable:[{label,
      reason}]}. ONE COPY — walk_walls and the profile breakdown both
      consume this, so the siding line and the Field Verify table can
      never hold different answers about the same wall."""
    width = float(w.get("width_ft") or 0)
    eave_h = float(w.get("height_ft") or 0)
    segs = [s for s in (w.get("height_segments") or []) if isinstance(s, dict)]
    if segs:
        gross = 0.0
        used: list[tuple[float, float]] = []
        not_deriv: list[dict] = []
        for s in segs:
            try:
                sw = float(s.get("width_ft") or 0)
                sh = float(s.get("height_ft") or 0)
            except (TypeError, ValueError):
                sw = sh = 0.0
            if sw > 0 and sh > 0:
                gross += sw * sh
                used.append((sw, sh))
            else:
                reason = ("segment width not read — area not derivable"
                          if not sw > 0
                          else (w.get("height_refusal_reason")
                                or "segment height not read — area not derivable"))
                not_deriv.append({"label": s.get("label"), "reason": reason})
        derivable = len(used) > 0
        return gross, used, {
            "has_segments": True, "derivable": derivable,
            "subset": derivable and bool(not_deriv),
            "not_derivable": not_deriv,
        }
    # No segments — the top-level rectangle is the PRIMARY measurement.
    if width > 0 and eave_h > 0:
        return width * eave_h, [], {
            "has_segments": False, "derivable": True,
            "subset": False, "not_derivable": []}
    reason = ("wall width not read — area not derivable" if not width > 0
              else (w.get("height_refusal_reason")
                    or "wall height not read — area not derivable"))
    return 0.0, [], {
        "has_segments": False, "derivable": False, "subset": False,
        "not_derivable": [{"label": w.get("label"), "reason": reason}]}


def wall_width_for_pricing(w: dict):
    """THE subset-aware wall footprint width for any priced reader
    (Howard ruled 2026-08-14 send-15 H). Segments govern: width = Σ
    DERIVABLE segment widths; else the top-level width. Returns
    (width, derivable, subset, missing) — a killed width returns
    (0.0, False, ...) so a caller can NEVER read a silent 0 and price it.
    ONE COPY so eaves / base / gable / batten cannot each re-derive a
    silent zero (the five-hats defect, Report 2)."""
    segs = [s for s in (w.get("height_segments") or []) if isinstance(s, dict)]
    if segs:
        widths, missing = [], []
        for s in segs:
            try:
                sw = float(s.get("width_ft") or 0)
            except (TypeError, ValueError):
                sw = 0.0
            if sw > 0:
                widths.append(sw)
            else:
                missing.append(s.get("label"))
        return (sum(widths), len(widths) > 0, bool(missing and widths),
                missing)
    try:
        width = float(w.get("width_ft") or 0)
    except (TypeError, ValueError):
        width = 0.0
    return (width, width > 0, False,
            [] if width > 0 else [w.get("label")])


def wall_height_for_pricing(w: dict):
    """THE subset-aware wall eave height for any priced reader (send-15 H).
    Returns (height, derivable). A killed height returns (0.0, False) so a
    reader (batten run, corner) cannot silently price a substitute."""
    try:
        h = float(w.get("height_ft") or 0)
    except (TypeError, ValueError):
        h = 0.0
    return h, h > 0


def walk_walls(walls: list, gable_rise_fn=None, refused_faces=None,
               unattributed_faces=None) -> dict:
    """THE wall-area walk (one copy, ruled). For each wall:
    gross = width × eave height, credited at siding_pct (fraction/percent
    defense shared), plus GABLE_FACTOR × width × rise for gable ends, plus
    dormer face ft². `gable_rise_fn(width_ft, read_rise_ft) -> rise_ft` lets
    the blueprint door substitute its pitch-computed rise (printed pitch is
    the authority over drawing-scaled reads); default uses the read value.
    Walls are consumed AS ADAPTED by the door (photo's clamps run upstream).

    RULING EE (send-25): `refused_faces` {label(lower) → reason} forces a
    face that FAILED footprint closure to NOT DERIVABLE — its body AND
    gable contribute nothing to the totals and it is NAMED on
    faces_not_derivable with the failing relation verbatim. The wall's
    read width is NEVER nulled here (that would erase the failing
    relation's own evidence and mislabel it "width not read"); the value
    stays on the wall record and the refusal names the real relation.

    EVIDENCE-AND-ATTRIBUTION-OR-NULL (Howard ruled 2026-08-25 send-127):
    `unattributed_faces` {label(lower) → reason} is the same shape for a
    face whose width LOCATED but whose ATTRIBUTION is unestablished (one
    printed quote claimed by two different faces). Display keeps the
    figure; NO quantity rides it — body AND gable refuse, because the
    gable needs no height and would otherwise carry the whole face.
    Returns full-precision totals + per-wall detail for provenance."""
    siding_sqft = 0.0
    gable_sqft = 0.0
    dormer_sqft = 0.0
    detail = []
    faces_not_derivable = []
    refused_faces = {str(k).lower(): v for k, v in (refused_faces or {}).items()}
    unattributed_faces = {str(k).lower(): v
                          for k, v in (unattributed_faces or {}).items()}
    for w in walls:
        _label_lc = str(w.get("label") or "").lower()
        if _label_lc in unattributed_faces:
            # SEND-127: located but unattributed — quantity refuses, the
            # read width stays on the record for display.
            faces_not_derivable.append({
                "label": w.get("label"), "surface": "width_attribution",
                "reason": unattributed_faces[_label_lc]})
            detail.append({"label": w.get("label"), "refused": True,
                           "width_ft": float(w.get("width_ft") or 0),
                           "reason": unattributed_faces[_label_lc]})
            continue
        if _label_lc in refused_faces:
            # RULING EE: footprint closure refuses this face. NOT DERIVABLE,
            # named with the failing relation; no area (body or gable) rides.
            faces_not_derivable.append({
                "label": w.get("label"), "surface": "footprint_closure",
                "reason": refused_faces[_label_lc]})
            detail.append({"label": w.get("label"), "refused": True,
                           "reason": refused_faces[_label_lc]})
            continue
        raw_w = w.get("width_ft")
        width_ft = float(raw_w or 0)
        eave_h = float(w.get("height_ft") or 0)
        # Per-wall height variation + SEGMENT-LEVEL PARTIAL (send-13):
        # segments govern; a killed segment is named, its area absent,
        # never covered by the top-level rectangle. The walk sums the
        # DERIVABLE gross (a subset when a segment is killed) and NAMES
        # the missing piece so a total from a subset says so.
        gross, segs_used, deriv = wall_body_gross_sqft(w)
        if not deriv["derivable"]:
            _nd = deriv["not_derivable"] or [{
                "label": w.get("label"),
                "reason": "wall width not read — area not derivable"}]
            for nd in _nd:
                faces_not_derivable.append({
                    "label": w.get("label"), "surface": "body",
                    "segment": (nd.get("label") if deriv["has_segments"]
                                else None),
                    "reason": nd.get("reason")})
        elif deriv["subset"]:
            for nd in deriv["not_derivable"]:
                faces_not_derivable.append({
                    "label": w.get("label"), "surface": "body_segment",
                    "segment": nd.get("label"), "reason": nd.get("reason"),
                    "partial": True})
        pct = float(w.get("siding_pct_this_wall") or 100.0)
        # Shared fraction-vs-percent defense: 0<x<1 is a fraction.
        if 0 < pct < 1:
            pct = pct * 100.0
        if pct <= 0:
            pct = 100.0
        pct = min(pct, 100.0)
        siding_sqft += gross * (pct / 100.0)
        rise_read = float(w.get("gable_triangle_height_ft") or 0)
        rise = gable_rise_fn(width_ft, rise_read) if gable_rise_fn else rise_read
        wall_gable = 0.0
        # GABLE — subset-aware (send-15 H). A gable triangle spans the
        # WHOLE wall width, so a killed/unread width makes the gable NOT
        # DERIVABLE — never a silent 0. Canonical honesty matches
        # profile_callouts' gable (that disagreement is now resolved: the
        # DISCLOSING path is canonical). rise>0 with no derivable width is
        # named, not zeroed.
        g_width, g_width_ok, _g_subset, _g_missing = wall_width_for_pricing(w)
        # RULING Y (Howard sealed send-23): gable width gates on WIDTH
        # derivability, NOT height. A segment with a real horizontal width
        # contributes to the gable even if its HEIGHT is dead — the gable
        # above it physically exists, and shrinking the gable for a height
        # reason would exclude a real width and improve the number by
        # accident (tuning, forbidden). Instead: the gable and body each
        # report which segments they span; where they DIFFER, BOTH go
        # PARTIAL and the difference is NAMED. The gable stays as wide as
        # its real widths — a high right gable STAYS high.
        _segs = [s for s in (w.get("height_segments") or []) if isinstance(s, dict)]
        _body_span = [str(s.get("label") or "segment") for s in _segs
                      if float(s.get("width_ft") or 0) > 0
                      and float(s.get("height_ft") or 0) > 0]
        _gable_span = [str(s.get("label") or "segment") for s in _segs
                       if float(s.get("width_ft") or 0) > 0]
        if rise > 0 and g_width_ok:
            wall_gable = GABLE_FACTOR * g_width * rise
            gable_sqft += wall_gable
            if _segs and set(_gable_span) != set(_body_span):
                _only_gable = [n for n in _gable_span if n not in _body_span]
                faces_not_derivable.append({
                    "label": w.get("label"), "surface": "gable_segment",
                    "partial": True,
                    "gable_spans": _gable_span, "body_spans": _body_span,
                    "convention": GABLE_CONVENTION_LABEL,
                    "reason": ("gable spans " + " + ".join(_gable_span)
                               + "; body spans " + " + ".join(_body_span)
                               + " — " + ", ".join(_only_gable)
                               + " height not read (gable width gates on "
                               "WIDTH not height — Ruling Y; gable NOT shrunk "
                               "to match)")})
        elif rise > 0 and not g_width_ok:
            faces_not_derivable.append({
                "label": w.get("label"), "surface": "gable",
                "reason": "wall width not read — gable area not derivable"})
            wall_gable = None
        dormer_sqft += float(w.get("dormer_face_sqft") or 0)
        detail.append({"label": w.get("label"), "width_ft": width_ft,
                       "eave_h": eave_h, "pct": pct,
                       "segments": segs_used,
                       # SEND-48 zone binding: per-surface derived numbers
                       # (or their refusals) so a zone can supersede ONE
                       # surface, never the whole house.
                       "body_sqft": round(gross * (pct / 100.0), 2),
                       "body_refusal": (None if deriv["derivable"]
                                        else (deriv["not_derivable"][0].get("reason")
                                              if deriv["not_derivable"] else
                                              "wall area not derivable")),
                       "gable_refusal": ("wall width not read — gable area "
                                         "not derivable"
                                         if wall_gable is None else None),
                       "rise_read": rise_read, "rise_used": rise,
                       "gable_sqft": wall_gable,
                       # SEND-74: the derived path never traces — every
                       # derived gable quantity carries the FIELD FACTOR
                       # basis; a refusal is not a quantity and carries
                       # no basis. (Tracing lives on the overlay/proposal
                       # layer and carries the TRACED basis there.)
                       "gable_basis": (GABLE_BASIS_FIELD_FACTOR
                                       if wall_gable else None),
                       "gable_basis_label": (
                           gable_basis_label(GABLE_BASIS_FIELD_FACTOR)
                           if wall_gable else None),
                       "gable_convention": (GABLE_CONVENTION_LABEL
                                            if wall_gable else None)})
    return {"siding_sqft": siding_sqft, "gable_sqft": gable_sqft,
            "dormer_sqft": dormer_sqft, "detail": detail,
            "faces_not_derivable": faces_not_derivable}


# (est_key, measurement_key, human label) — the four ruled boxes; frieze
# is the toggle and rides its own check.
PHOTO_FILLIN_BOXES = (("photo_soffit_sqft", "soffit_sqft", "soffit ft²"),
                      ("photo_drip_edge_lf", "drip_edge_lf", "drip edge LF"),
                      ("photo_total_trim_sqft", "total_trim_sqft", "total trim ft²"))


def photo_fillins_unset(measurements: dict, est: dict) -> list[str]:
    """QUOTE-GATE feeder (Howard ruled 2026-08-02): on a photo-sourced
    estimate an UNSET fill-in box is SCOPE NOT SET — it blocks the quote
    the way an open intake flag does; it never silently prices $0.
    An explicit 0 is a decision and clears the box; a measured value in
    the blob makes the box inert (source provides it → engine consumes
    it). Frieze clears on an answered yes/no, not a number. ONE copy —
    the gate reads set/unset from here only."""
    if (measurements or {}).get("_source") != "photo":
        return []
    unset = []
    for est_key, meas_key, label in PHOTO_FILLIN_BOXES:
        if est.get(est_key) is None and not float(measurements.get(meas_key) or 0):
            unset.append(label)
    if est.get("photo_frieze_present") is None and not (
            float(measurements.get("level_frieze_lf") or 0)
            or float(measurements.get("sloped_frieze_lf") or 0)):
        unset.append("frieze yes/no")
    return unset


def is_fillin(m: dict, key: str) -> bool:
    """Provenance check for printed notes (Howard ruled 2026-08-02): the
    document must not hide how a number got there — a line whose driver
    came from a fill-in box prints TYPED, a measured one prints MEASURED.
    Frieze uses key='frieze' (the toggle stamps _frieze_basis)."""
    return bool(m.get(f"_{key}_basis")) if key != "frieze" \
        else bool(m.get("_frieze_basis"))


def fold_photo_fillins(measurements: dict, est: dict) -> dict:
    """PHOTO FILL-IN BOXES (Howard ruled 2026-08-01, Three Doors step 6):
    four boxes, PHOTO DOOR ONLY — soffit_sqft, drip_edge_lf,
    total_trim_sqft, frieze presence-toggle. The photo genuinely cannot
    see these; Hover measures them and blueprint prints them, so the
    boxes are inert everywhere except a photo-sourced blob (finding 6:
    never ask the contractor to re-type a number the source gave).
    A box only FILLS A HOLE — it never overrides a measured value.
    Frieze is a TOGGLE: its LF derives from the measured eave/rake runs
    (level = eaves, sloped = rakes), no number re-typing. ONE copy —
    both fold points (rebuild_lp_tab_lines + _apply_contractor_waste)
    call here; a second copy anywhere is a regression."""
    if (measurements or {}).get("_source") != "photo":
        return measurements
    out = measurements
    for est_key, meas_key in (("photo_soffit_sqft", "soffit_sqft"),
                              ("photo_drip_edge_lf", "drip_edge_lf"),
                              ("photo_total_trim_sqft", "total_trim_sqft")):
        try:
            v = float(est.get(est_key) or 0)
        except (TypeError, ValueError):
            v = 0.0
        if v > 0 and not float(out.get(meas_key) or 0):
            out = {**out, meas_key: v,
                   f"_{meas_key}_basis": "contractor fill-in (photo door — source cannot see it)"}
    if est.get("photo_frieze_present") and not (
            float(out.get("level_frieze_lf") or 0)
            or float(out.get("sloped_frieze_lf") or 0)):
        eaves = float(out.get("eaves_lf") or 0)
        rakes = float(out.get("rakes_lf") or 0)
        if eaves > 0 or rakes > 0:
            out = {**out,
                   **({"level_frieze_lf": eaves} if eaves > 0 else {}),
                   **({"sloped_frieze_lf": rakes} if rakes > 0 else {}),
                   "_frieze_basis": (
                       f"presence toggle — LF derived from measured runs "
                       f"(level = eaves {eaves:g} LF, sloped = rakes {rakes:g} LF)")}
    return out


_DOOR_BUCKETS = ("entry_door", "patio_door", "garage_door")


def bucket_openings(rows: list) -> dict:
    """THE opening bucketing (one copy). `rows` are door-adapted:
    [{type, count, width_in, height_in}]. Returns counts per bucket,
    the door_count TOTAL (ruled 2026-08-01 finding 6 — the sum LANDS on
    every door; caulk + J-blocks read it), opening ft² and perimeter LF —
    all full precision."""
    counts = {"window": 0, "entry_door": 0, "patio_door": 0, "garage_door": 0}
    opening_sqft = 0.0
    perimeter_lf = 0.0
    for o in rows:
        t = (o.get("type") or "other").lower()
        try:
            cnt = max(0, int(o.get("count") or 0))
        except (TypeError, ValueError):
            cnt = 0
        if cnt <= 0:
            continue
        w_in = float(o.get("width_in") or 0)
        h_in = float(o.get("height_in") or 0)
        if t in counts:
            counts[t] += cnt
        opening_sqft += cnt * (w_in * h_in) / 144.0
        perimeter_lf += cnt * 2 * ((w_in + h_in) / 12.0)
    return {
        "counts": counts,
        "opening_count": sum(counts.values()),
        "door_count": sum(counts[b] for b in _DOOR_BUCKETS),
        "opening_sqft": opening_sqft,
        "opening_perimeter_lf": perimeter_lf,
    }


def land_door_count(measurements: dict) -> dict:
    """Finding 6 (ruled): door_count = entry + patio + garage lands on every
    door's measurements. Never overwrites a measured total (Hover extracts
    its own)."""
    if not measurements.get("door_count"):
        measurements["door_count"] = (
            int(measurements.get("entry_door_count") or 0)
            + int(measurements.get("patio_door_count") or 0)
            + int(measurements.get("garage_door_count") or 0))
    return measurements


# ---------------------------------------------------------------------------
# Window product-type helpers (moved here from routes so the ONE builder has
# no route imports; routes re-import these names for back-compat).
# ---------------------------------------------------------------------------

def guess_vero_product_type(width_in: float, height_in: float) -> str:
    """Iter 78y heuristic: wide (≥40") landscape → 2-Lite Slider; else DH.
    Patio Door only from explicit upstream classification, never dims."""
    try:
        w = float(width_in or 0)
        h = float(height_in or 0)
    except (TypeError, ValueError):
        return "Vero Double Hung"
    if w <= 0 or h <= 0:
        return "Vero Double Hung"
    if w >= 40 and w > h:
        return "Vero 2-Lite Slider"
    return "Vero Double Hung"


VERO_TO_MEZZO = {
    "Vero Double Hung":      "Mezzo Double Hung",
    "Vero 2-Lite Slider":    "Mezzo 2-Lite Slider",
    # Legacy fallbacks (Vero types no longer offered):
    "Vero 3-Lite Slider":    "Mezzo 2-Lite Slider",
    "Vero Picture":          "Mezzo Double Hung",
    "Vero 1-Lite Casement":  "Mezzo Double Hung",
}


def vero_to_mezzo_product_type(vero_type: str) -> str:
    return VERO_TO_MEZZO.get(vero_type, "Mezzo Double Hung")


# AI style string → (Vero product type, qty multiplier). Multi-unit styles
# become the correct count of rows (Twin DH=2, Bay=3, Bow=5). Iter 57t —
# frozen Vero types reroute to DH / 2-Lite so nothing lands hidden.
STYLE_TO_VERO_PRODUCT_TYPE: dict = {
    "Double Hung":        ("Vero Double Hung",     1),
    "Single Hung":        ("Vero Double Hung",     1),
    "Casement":           ("Vero 1-Lite Casement", 1),
    "Twin Casement":      ("Vero 1-Lite Casement", 2),
    "Awning":             ("Vero 1-Lite Casement", 1),
    "Hopper":             ("Vero 1-Lite Casement", 1),
    "2-Lite Slider":      ("Vero 2-Lite Slider",   1),
    "3-Lite Slider":      ("Vero 2-Lite Slider",   1),  # frozen → reroute to 2-Lite
    "Picture":            ("Vero Double Hung",     1),  # frozen → DH
    "Twin Double Hung":   ("Vero Double Hung",     2),
    "Twin Single Hung":   ("Vero Double Hung",     2),
    "Triple Double Hung": ("Vero Double Hung",     3),
    "Bay Window":         ("Vero Double Hung",     3),  # frozen → DH (3-pane)
    "Bow Window":         ("Vero Double Hung",     5),  # frozen → DH (5-pane)
    "Half-Round":         ("Vero Double Hung",     1),  # frozen → DH
    "Quarter-Round":      ("Vero Double Hung",     1),  # frozen → DH
    "Arch":               ("Vero Double Hung",     1),  # frozen → DH
    "Octagon":            ("Vero Double Hung",     1),  # frozen → DH
    "Hexagon":            ("Vero Double Hung",     1),  # frozen → DH
    "Garden Window":      ("Vero Double Hung",     1),  # frozen → DH
    "Other Shape":        ("Vero Double Hung",     1),  # frozen → DH
}


def vero_for_style(style: str, width_in: float, height_in: float) -> tuple:
    style = (style or "").strip()
    if style in STYLE_TO_VERO_PRODUCT_TYPE:
        return STYLE_TO_VERO_PRODUCT_TYPE[style]
    return (guess_vero_product_type(width_in, height_in), 1)


# ---------------------------------------------------------------------------
# THE window-openings builder (ruled 2026-08-01, finding 10b: ONE builder).
# ---------------------------------------------------------------------------

def build_paired_openings(windows: list | None = None,
                          openings: list | None = None,
                          schedule: list | None = None) -> tuple:
    """ONE builder, every door. Returns (vero_rows, mezzo_rows), paired 1:1
    by shared UUID.

    Dims mode (`windows[]` — HOVER + BLUEPRINT): per-opening dims, product
    type from the W×H guess, label = source id.
    Style mode (`schedule`/`openings` — PHOTO): schedule preferred (count=N
    per identical row), AI style drives product type + qty multiplier;
    non-window types skipped (doors/vents belong to siding accessories)."""
    vero_out: list = []
    mezzo_out: list = []

    if windows is not None:
        for w in windows:
            try:
                wid = float(w.get("width_in") or 0)
                hgt = float(w.get("height_in") or 0)
            except (TypeError, ValueError):
                continue
            if wid <= 0 or hgt <= 0:
                continue
            hover_id = str(w.get("id") or "").strip()
            vero_type = guess_vero_product_type(wid, hgt)
            opening_id = str(uuid.uuid4())
            vero_out.append({
                "id": opening_id, "hover_id": hover_id,
                "product_type": vero_type, "label": hover_id,
                "width": wid, "height": hgt, "qty": 1,
                "sister_color": "White Interior/White Exterior",
                "sizing": "ui_bucket", "bucket_label": "",
                "base_mat": 0, "adders": [],
            })
            mezzo_out.append({
                "id": opening_id, "hover_id": hover_id,
                "product_type": vero_to_mezzo_product_type(vero_type),
                "label": hover_id, "width": wid, "height": hgt, "qty": 1,
                "bucket_label": "", "base_mat": 0, "adders": [],
            })
        return vero_out, mezzo_out

    def _emit(*, otype, w, h, wall, style, count=1):
        if otype != "window" or w <= 0 or h <= 0 or count <= 0:
            return
        product_type, qty_mult = vero_for_style(style, w, h)
        label = f"AI · {wall} · {style or 'Window'} · {int(w)}×{int(h)}"
        for _ in range(count * qty_mult):
            row = {
                "id": str(uuid.uuid4()), "hover_id": "",
                "product_type": product_type, "label": label,
                "width": w, "height": h, "qty": 1,
                "sister_color": "White Interior/White Exterior",
                "sizing": "ui_bucket", "bucket_label": "",
                "base_mat": 0, "adders": [], "ai_style": style,
            }
            vero_out.append(row)
            mezzo_out.append({**row, "product_type": vero_to_mezzo_product_type(product_type)})

    if schedule:
        for o in schedule:
            try:
                w = float(o.get("width_in") or 0)
                h = float(o.get("height_in") or 0)
            except (TypeError, ValueError):
                continue
            _emit(otype=(o.get("type") or "").lower(), w=w, h=h,
                  wall=(o.get("elevation") or o.get("wall") or "other").lower(),
                  style=(o.get("style") or "").strip(),
                  count=int(o.get("count") or 0))
        return vero_out, mezzo_out

    for o in openings or []:
        try:
            w = float(o.get("width_in") or 0)
            h = float(o.get("height_in") or 0)
        except (TypeError, ValueError):
            continue
        _emit(otype=(o.get("type") or "").lower(), w=w, h=h,
              wall=(o.get("wall") or "other").lower(),
              style=(o.get("style") or "").strip(), count=1)
    return vero_out, mezzo_out
