"""QUOTE GATE vs ORDER GATE — the two-tier flag doctrine (Howard, ruled
2026-07-29, refining the 2026-07-28 lists).

QUOTE GATE — blocks the customer surfaces (quote email, Accept page at
token mint, PDF, material-list freeze, QR):
  facade_scope unresolved-zero · area_conservation breach ·
  siding_family_conflict · no_siding_on_siding_job ·
  labor_pending_contractor (moved to QUOTE by ruling d).

ORDER GATE — blocks material release / PO / truck (the FINAL-JOB
SURFACE is where these clear; taped fields SUPERSEDE derived values):
  batten_wall_heights · corner_locators · opening_schedule ·
  opening_facade_attribution (placed in ORDER by ruling d) ·
  porch_ceiling_implied (moved from informational to ORDER by ruling d).

EVERY flag is assigned to exactly ONE tier at creation — an unassigned
flag FAILS the suite (tests/test_quote_order_gates.py scans every
literal code/kind emission and refuses any without a registry row).
"""

# code → tier. Every flag code emitted anywhere lands here.
GATE_TIERS: dict[str, str] = {
    # ── QUOTE tier ──
    "facade_scope": "quote",                 # informational; blocking variant below
    "facade_scope_unresolved_zero": "quote",  # BLOCKING
    "facade_scope_composed": "quote",        # info-level door composition note
    "area_conservation": "quote",            # BLOCKING when residue breaches
    "area_conservation_breach": "quote",     # BLOCKING (explicit variant)
    "siding_family_conflict": "quote",       # BLOCKING
    "no_siding_on_siding_job": "quote",      # BLOCKING
    "labor_pending_contractor": "quote",     # BLOCKING (ruling d)
    "photo_fillin_unset": "quote",           # BLOCKING (ruled 2026-08-02):
                                             # an unset photo fill-in box is
                                             # SCOPE NOT SET, never $0 —
                                             # blocks like an open intake flag
    "vision_zero_pages": "quote",            # informational, LOUD, never blocks —
                                             # silent-zero-verification class
                                             # (Howard 2026-07-29): a verification
                                             # step that finds nothing must not
                                             # render as a pass
    # ── ORDER tier ──
    "batten_wall_heights": "order",          # BLOCKING (taped at the house)
    "corner_locators": "order",              # BLOCKING (taped/walked)
    "opening_schedule": "order",             # BLOCKING
    "opening_facade_attribution": "order",   # BLOCKING (ruling d)
    "porch_ceiling_implied": "order",        # BLOCKING (ruling d — was informational)
    "ceiling_dedup": "order",                # assigned at creation (soffit qty)
}

# readiness-item KIND fallback for dynamic codes (row names etc.)
KIND_TIERS: dict[str, str] = {
    "family_conflict": "quote",
    "labor_pending": "quote",
    "unpriced_row": "quote",      # BLOCKING (Howard re-ruled 2026-08-04): an
                                  # unpriced money-surface row must never reach
                                  # a homeowner as $0 — "the PRINT-BLOCK
                                  # working, not a bug. Keep the rule."
    "labor_pending_row": "quote",  # BLOCKING (Howard ruled 2026-08-04): a labor
                                   # row with NO price at all is the CONTRACTOR'S
                                   # to fill — reads LABOR PENDING, stays visible,
                                   # and blocks the customer quote until priced
                                   # (never supplier-defaulted, never hidden)
    "qty_pending": "quote",       # informational (Q1 rows are the contractor's)
    "pending_price": "quote",     # informational
    "open_flag": "order",         # mapping-contract flags default ORDER unless coded
    "field_verify": "order",      # amber corners — verify before ordering
}

QUOTE_BLOCKING = frozenset({
    "facade_scope_unresolved_zero", "area_conservation_breach",
    "siding_family_conflict", "no_siding_on_siding_job",
    "photo_fillin_unset",  # ruled 2026-08-02 — silent-zero class, hard block
    # labor_pending_contractor REMOVED from blocking (Howard re-ruled
    # 2026-07-29): labor is N/A or >$0; anything else is UNDECIDED —
    # ONE line with a count, never a block.
})
ORDER_BLOCKING = frozenset({
    "batten_wall_heights", "corner_locators", "opening_schedule",
    "opening_facade_attribution", "porch_ceiling_implied",
})

_SIDING_KINDS = ("siding", "lp_smart")
_SIDING_MARKERS = ("series lap", "4' x 10' panel", "shake", "nickel gap",
                   "dutch lap", "charter oak standard color",
                   "ascend composite")


def tier_for(code: str | None, kind: str | None = None) -> str:
    if code and code in GATE_TIERS:
        return GATE_TIERS[code]
    if kind and kind in KIND_TIERS:
        return KIND_TIERS[kind]
    raise KeyError(
        f"UNASSIGNED FLAG (ruled 2026-07-29): code={code!r} kind={kind!r} "
        "— every flag is assigned to exactly one gate tier at creation")


def quote_gate_blockers(est: dict, measurements: dict | None = None) -> list[dict]:
    """The five QUOTE blockers, evaluated from the estimate's own lines
    (+ run measurements when a run exists). Each item names the count."""
    items: list[dict] = []
    lines = est.get("lines") or []
    kind = est.get("kind") or "siding"

    # siding_family_conflict — exactly ONE family carries derived qty
    fam_markers = {"lap": ("series lap",), "board & batten": ("4' x 10' panel",),
                   "shake": ("shake",)}
    fams_hit: dict[str, list] = {}
    for l in lines:
        if l.get("tab") != "lp_smart" or not (l.get("qty") or 0):
            continue
        if (l.get("qty_src") or "") == "human":
            continue
        nm = str(l.get("name") or "").lower()
        for fam, marks in fam_markers.items():
            if any(mk in nm for mk in marks):
                fams_hit.setdefault(fam, []).append(l.get("name"))
    if len(fams_hit) > 1:
        items.append({
            "code": "siding_family_conflict", "tier": "quote", "blocking": True,
            "label": (f"SIDING FAMILY CONFLICT — {len(fams_hit)} families carry "
                      f"derived quantity ({' + '.join(fams_hit)}). Profile owns its "
                      "family: re-derive before quoting."),
        })

    # no_siding_on_siding_job — a siding-kind estimate quoting zero siding
    # while OTHER rows carry quantity (accessories-only money surface).
    # An estimate with no derived lines at all (package-only workflow,
    # e.g. Letrick) judges on its derived package surface, not here.
    if kind in _SIDING_KINDS and any((l.get("qty") or 0) > 0 for l in lines):
        has_siding = any(
            (l.get("qty") or 0) > 0
            and (str(l.get("section") or "").lower() in
                 ("vinyl siding", "ascend cladding", "lp smart siding")
                 or any(mk in str(l.get("name") or "").lower()
                        for mk in _SIDING_MARKERS))
            for l in lines)
        if not has_siding:
            items.append({
                "code": "no_siding_on_siding_job", "tier": "quote", "blocking": True,
                "label": ("NO SIDING ON A SIDING JOB — zero siding quantity on the "
                          "money surface; the quote would sell accessories only. "
                          "Re-derive or pick the family before quoting."),
            })

    # labor UNDECIDED — one line, a count, never a block (re-ruled 2026-07-29)
    pend = [l for l in lines
            if (l.get("lab_src") or "") == "pending" and (l.get("qty") or 0) > 0]
    if pend:
        items.append({
            "code": "labor_pending_contractor", "tier": "quote", "blocking": False,
            "label": (f"LABOR UNDECIDED on {len(pend)} row(s) — labor is either "
                      "N/A or a value above $0; enter your rates or mark N/A."),
        })

    m = measurements or {}
    # facade_scope unresolved-zero — scope resolved to ZERO sided ft²
    fs = m.get("_facade_scope")
    if fs is not None:
        wrap = float(fs.get("wrap_sqft") or 0)
        total = float(fs.get("measured_total") or 0)
        if wrap <= 0 and total > 0:
            items.append({
                "code": "facade_scope_unresolved_zero", "tier": "quote", "blocking": True,
                "label": (f"FACADE SCOPE UNRESOLVED-ZERO — {total:g} ft² measured, "
                          "0 ft² composes. Resolve the facade picker before quoting."),
            })

    # area_conservation breach — sum in ≠ sum out beyond 0.5 ft²
    ac = m.get("_area_conservation")
    if ac is not None:
        total = float(ac.get("measured_total_sqft") or 0)
        accounted = (float(ac.get("sided_sqft") or 0)
                     + float(ac.get("excluded_sqft") or 0)
                     + float(ac.get("flagged_sqft") or 0))
        if total > 0 and abs(total - accounted) > 0.5:
            items.append({
                "code": "area_conservation_breach", "tier": "quote", "blocking": True,
                "label": (f"AREA CONSERVATION BREACH — measured {total:g} ft² vs "
                          f"accounted {accounted:g} ft² (sided+excluded+flagged): "
                          f"{total - accounted:+.1f} ft² unaccounted. No ft² "
                          "disappears without an exclusion decision."),
            })

    # photo_fillin_unset (Howard ruled 2026-08-02): a photo estimate with
    # empty fill-in boxes at quote time would price soffit/drip edge on a
    # guess or a silent zero. SCOPE NOT SET blocks — an explicit 0 is a
    # decision and clears; the set/unset definition has ONE copy
    # (measure_staging.photo_fillins_unset).
    from measure_staging import photo_fillins_unset
    hm = est.get("hover_measurements") or {}
    blob = hm if hm.get("_source") == "photo" else (
        m if (m or {}).get("_source") == "photo" else {})
    unset = photo_fillins_unset(blob, est)
    if unset:
        items.append({
            "code": "photo_fillin_unset", "tier": "quote", "blocking": True,
            "unset": unset,
            "label": (f"PHOTO FILL-INS NOT SET — {len(unset)} box(es) open: "
                      f"{', '.join(unset)}. SCOPE NOT SET, never $0 — the photos "
                      "cannot see these; type the value (0 is a decision) or "
                      "answer the frieze yes/no before this quote reaches a "
                      "customer."),
        })
    return items
