"""Iter 79j.93 — LP package preview endpoint (September package assembly, Phase 1).
Iter 79j.94 — truck-list reconciliation endpoint (pre-±3% acceptance harness).
Iter 79j.96 — confidential cost layer + tiered sell pricing. Contractor-facing
preview is ALWAYS redacted (sell only); the unredacted cost view exists only
behind the supplier-admin token."""
import re

from fastapi import APIRouter, Depends, HTTPException, Request

from datetime import datetime, timezone

from db import db
from deps import check_admin_token, get_current_user
from estimate_events import log_estimate_event
from lp_costs import price_package, redact_external
from lp_package import assemble_lp_package
from lp_truck_reconcile import reconcile_letrick_truck
from routes.lp_admin import load_margin_cfg
from run_archive import archive_run_for_artifact, find_archived_run

router = APIRouter()


async def _load_run(est_id: str, company_id=None, run_id=None):
    """company_id=None is the supplier-admin path (token-checked upstream).
    Falls back to the PAIRED estimate's runs — a paired LP estimate's AI
    Measure run lives on its siding source (pair-lp flow)."""
    q_est: dict = {"id": est_id}
    if company_id is not None:
        q_est["company_id"] = company_id
    est = await db.estimates.find_one(
        q_est, {"_id": 0, "id": 1, "estimate_number": 1, "sealed_key": 1, "waste_pct": 1, "lp_pricing_tier": 1, "lp_field_verify": 1,
                "lp_openings_review": 1, "lp_appendage_dims": 1, "lp_source_run_id": 1,
                "default_siding_profile": 1, "lp_flag_checklist": 1,
                "paired_lp_estimate_id": 1, "paired_estimate_id": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    q: dict = {"estimate_id": est_id, "status": "done"}
    if run_id:
        q["run_id"] = run_id

    async def _find_run(query):
        # THE CUT (ruled 2026-07-14): blueprint-applied LP takeoffs derive
        # through the SAME engine. Source governance: an APPLIED source
        # stamp (lp_source_run_id) outranks everything; otherwise the
        # latest done PHOTO run governs, blueprint runs only when no
        # photo run exists — a merely-PREVIEWED blueprint shakedown must
        # never silently switch a demo estimate's composition source.
        if not run_id:
            stamped = str(est.get("lp_source_run_id") or "").strip()
            if stamped:
                sq = dict(query)
                sq["run_id"] = stamped
                for coll in (db.ai_measure_runs, db.ai_blueprint_runs):
                    r = await coll.find_one(sq, {"_id": 0})
                    if r:
                        return r
                r = await find_archived_run(sq)
                if r:
                    return r
        r = await db.ai_measure_runs.find_one(query, sort=[("created_at", -1)])
        if r is None:
            r = await db.ai_blueprint_runs.find_one(query, {"_id": 0}, sort=[("created_at", -1)])
        if r is None:
            # Ruled 2026-07-14 — artifact-referenced runs outlive their
            # TTL in fixture_runs; serve them so a November callback
            # still gets its Material List panel + 3D.
            r = await find_archived_run(query)
        return r

    run = await _find_run(q)
    # STANDING RULE (Howard, 2026-07-16): geometry-source naming. Track HOW
    # the run was bound so every derivation surface can state its basis
    # visibly — no derivation silently binds to a latest-run.
    stamped = str(est.get("lp_source_run_id") or "").strip()
    if run_id:
        binding = "explicit-run"
    elif run is not None and stamped and str(run.get("run_id") or "") == stamped:
        binding = "applied-stamp"
    else:
        binding = "latest-run"
    paired_id = est.get("paired_lp_estimate_id") or est.get("paired_estimate_id")
    if run is None and paired_id and not run_id:
        paired_q: dict = {"id": paired_id}
        if company_id is not None:
            paired_q["company_id"] = company_id
        paired = await db.estimates.find_one(paired_q, {"_id": 0, "id": 1})
        if paired:
            run = await _find_run({"estimate_id": paired["id"], "status": "done"})
            if run is not None:
                binding = "paired-latest"
    if run is None:
        raise HTTPException(status_code=404, detail="No completed AI Measure run for this estimate")
    return est, run, binding


_BINDING_LABEL = {
    "applied-stamp": "pinned (applied)",
    "explicit-run": "explicit run",
    "latest-run": "latest run — unpinned",
    "paired-latest": "paired estimate, latest run — unpinned",
}

# Profiles with a ruled LP composition (LP SmartSide only, slice 1).
_DEFAULT_PROFILES = ("lap", "board_batten", "shake", "nickel_gap")
_PROFILE_LABEL = {
    "lap": "Lap",
    "board_batten": "Board & Batten",
    "shake": "Shake",
    "nickel_gap": "Nickel Gap",
}


def _geometry_basis(est: dict, run: dict, binding: str) -> dict:
    """Geometry-source naming (standing rule 2026-07-16): a structured,
    contractor-visible statement of the geometry basis behind a derivation
    — extraction run + run_id + binding mode + tape/field overlays."""
    rid8 = str(run.get("run_id") or "")[:8]
    if run.get("source") == "hover":
        kind = "hover"
    elif run.get("page_paths"):
        kind = "blueprint"
    else:
        kind = "photo"
    taped = 0
    for fields in (est.get("lp_appendage_dims") or {}).values():
        for f in ("height_ft", "depth_ft"):
            e = (fields or {}).get(f) or {}
            if e.get("status") in _DIM_STATUSES and (e.get("value") or 0) > 0:
                taped += 1
    confirmed = sum(
        1 for v in (est.get("lp_field_verify") or {}).values()
        if (v or {}).get("status") in ("verified", "user_relocated")
    )
    if kind == "hover":
        report = run.get("hover_report_id") or rid8
        label = f"Hover import — report {report} — {_BINDING_LABEL.get(binding, binding)}"
        ms = ((run.get("result") or {}).get("measurements")) or {}
        fs = ms.get("_facade_scope")
        if fs:
            excl = ", ".join(f"{k} {v:g}" for k, v in (fs.get("excluded") or {}).items())
            label += (f" · wrap-only scope {fs['wrap_sqft']:g} of {fs['measured_total']:g} ft²"
                      + (f" ({excl} excluded)" if excl else ""))
        label += " · openings: Hover net"
    else:
        label = f"{kind} extraction run {rid8} — {_BINDING_LABEL.get(binding, binding)}"
    profile = est.get("default_siding_profile")
    if profile:
        label += f" · profile: {_PROFILE_LABEL.get(profile, profile)}"
    overlays = []
    if taped:
        overlays.append(f"{taped} taped dim{'s' if taped != 1 else ''}")
    if confirmed:
        overlays.append(f"{confirmed} field-confirmed")
    if overlays:
        label += " · " + " · ".join(overlays)
    return {
        "source": kind,
        "kind": kind,
        "run_id": run.get("run_id"),
        "binding": binding,
        "pinned": binding == "applied-stamp",
        "profile": profile,
        "taped_dims": taped,
        "confirmed_locations": confirmed,
        "label": label,
    }


def _extract(run: dict):
    result = run.get("result") or {}
    measurements = result.get("measurements") or {}
    raw_ai = result.get("raw_ai") or {}
    corner_locations = raw_ai.get("corner_locations") or []
    wall_heights = {}
    for w in raw_ai.get("walls") or []:
        lbl = str(w.get("label") or "").strip().lower()
        try:
            h = float(w.get("height_ft") or 0)
        except (TypeError, ValueError):
            h = 0
        if lbl and h > 0:
            wall_heights[lbl] = h
    return measurements, corner_locations, wall_heights


def _corner_key(c, i=0):
    import re
    locator = str(c.get("locator") or "").strip() or f"corner {i + 1}"
    kind = "isc" if str(c.get("type") or "") == "inside" else "osc"
    slug = re.sub(r"[^a-z0-9]+", "-", locator.lower()).strip("-")[:60]
    return f"corner:{kind}:{slug}", locator, kind.upper()


_WALLS = ("front", "back", "left", "right")


_APPENDAGE_KEYWORDS = ("chase", "chimney", "bump", "cantilever")

_DIM_FIELDS = ("height_ft", "depth_ft", "door_offset_ft", "width_ft")

_DIM_STATUSES = ("user_measured", "user_confirmed_from_blueprint")


def _has_appendage_keyword(s):
    t = str(s or "").lower()
    return any(k in t for k in _APPENDAGE_KEYWORDS)


def _apply_appendage_dims(corner_locations, dims_state):
    """Dimension-editing ruling (2026-07-15): the render-only rule's
    second half. A user_measured (or blueprint-confirmed) appendage
    height becomes a legitimate derivation input — set as
    height_override_ft on that wall's appendage-keyword OSC corners so
    540 OSC stick LF re-derives. Assumed dims never set the override
    (pin unchanged). Keys: appendage:{original wall}."""
    if not dims_state:
        return corner_locations
    heights = {}
    for key, fields in dims_state.items():
        if not str(key).startswith("appendage:"):
            continue
        wall = str(key).split(":", 1)[1]
        h = (fields or {}).get("height_ft") or {}
        if h.get("status") in _DIM_STATUSES and (h.get("value") or 0) > 0:
            heights[wall] = float(h["value"])
    if not heights:
        return corner_locations
    # Feature-scoped application (C4 doctrine): entering THE CHASE height
    # raises ALL of that chase's OSC edges — including the edge that sits
    # on the adjacent wall (e.g. letrick's "chase right outer edge" lives
    # on the back wall while the box keys to the right wall).
    from lp_package import APPENDAGE_MARKERS
    out = list(corner_locations or [])
    groups = {}
    for idx, c in enumerate(out):
        if str(c.get("type")) != "outside":
            continue
        text = f"{c.get('locator') or ''} {' '.join(str(w) for w in c.get('walls') or [])}".lower()
        marker = next((m for m in APPENDAGE_MARKERS if m in text), None)
        if marker:
            groups.setdefault(marker, []).append(idx)
    for idxs in groups.values():
        hit = None
        for i2 in idxs:
            walls = [str(w).lower() for w in (out[i2].get("walls") or [])]
            hit = next((heights[w] for w in walls if w in heights), None)
            if hit:
                break
        if hit:
            for i2 in idxs:
                out[i2] = {**out[i2], "height_override_ft": hit, "height_source": "user_measured"}
    return out


def _apply_key_bound_areas(measurements, est):
    """GEOMETRY-SOURCE RULE EXTENDED TO MATERIALS (Howard, ruled
    2026-07-19; generalizes the item-3 gate): material-list area
    derivation BINDS the sealed key's taped/TAPED-DERIVED dims wherever
    they exist; AI-run values are the NAMED FALLBACK only where no key
    value exists. Every area line names its basis. Letrick: 54' eaves,
    taped heights, stepped sides, book gables (w×h×0.7, sealed), composed
    chase faces (item-3 ratified) → key raw_sqft governs siding area.
    Gate: portable `sealed_key` doc flag (ruled 2026-07-26) — no runtime
    match on estimate numbers; values stay in letrick_hand_takeoff_key.py."""
    if est.get("sealed_key") != "letrick_v3":
        return measurements  # no sealed key — AI values are the named fallback
    dims = (est.get("lp_appendage_dims") or {}).get("appendage:back") or {}
    h = dims.get("height_ft") or {}
    d = dims.get("depth_ft") or {}
    if h.get("status") not in _DIM_STATUSES or d.get("status") not in _DIM_STATUSES:
        return measurements
    from letrick_hand_takeoff_key import LETRICK_HAND_TAKEOFF_KEY as KEY
    inp = KEY["inputs"]
    if not inp.get("raw_sqft"):
        return measurements
    ai_sqft = float(measurements.get("siding_sqft") or 0)
    ai_gables = float(measurements.get("_ai_gable_sqft") or 0)
    key_sqft = float(inp["raw_sqft"])
    chase_total = round(float(inp["chase_outer_sqft"]) + float(inp["chase_sides_sqft"]), 2)
    basis = [
        {"component": "front wall", "sqft": 478.1, "basis": "TAPED-DERIVED — sealed key (54' × 8.85')"},
        {"component": "back wall", "sqft": 535.7, "basis": "TAPED-DERIVED — sealed key (54' × 9.92')"},
        {"component": "stepped side walls", "sqft": 566.4, "basis": "TAPED-DERIVED — sealed key (taped segments)"},
        {"component": "gables", "sqft": 367.5,
         "basis": (f"BOOK w×h×0.7 — sealed 2026-07-19 (AI true-triangle {ai_gables:g} on record, "
                   f"Δ {round(367.5 - ai_gables, 1):+g} flagged)")},
        {"component": "chase faces", "sqft": chase_total,
         "basis": "TAPED — item-3 ratified 2026-07-19 (outboard 51.37 + sides 101.02)"},
    ]
    return {**measurements,
            "siding_sqft": key_sqft,
            "siding_with_openings_sqft": key_sqft,
            "_area_basis": basis,
            "_area_basis_ai_comparison": {
                "siding_sqft": ai_sqft,
                "note": ("AI-frame reads — named fallback only where no key value exists "
                         "(geometry-source rule extended to materials, ruled 2026-07-19)")},
            "_chase_face_ratification": {
                "ai_sqft": float(measurements.get("_ai_appendage_sqft") or 0),
                "outboard_sqft": float(inp["chase_outer_sqft"]),
                "sides_sqft": float(inp["chase_sides_sqft"]),
                "total_sqft": chase_total,
                "delta_sqft": round(chase_total - float(measurements.get("_ai_appendage_sqft") or 0), 2),
                "siding_sqft_effective": key_sqft,
                "ruled": ("item-3 ratified 2026-07-19 — TAPED faces supersede "
                          "AI attribution (swap); key-bound area per lap unification ruling")}}


def _apply_contractor_waste(measurements, est):
    """WASTE IS THE CONTRACTOR'S (Howard, ruled 2026-07-19): the estimate
    page's WASTE FACTOR field is the only waste applied to LP lap —
    default 0, per-estimate, surfaced. Hover unification (ruled
    2026-07-20): new Hover imports write 10.0 into that field and no
    longer carry a silent _waste_pct — this fallback reads the field for
    Hover too. An explicit per-run _waste_pct override still wins.
    SHAKE REVEAL (register #4 ruled 2026-07-28): the estimate's
    shake_reveal_in field (bounded 7–10, default 7) rides along here."""
    out = measurements
    if out.get("_waste_pct") is None:
        out = {**out, "_waste_pct": float(est.get("waste_pct") or 0.0) / 100.0}
    if out.get("_shake_reveal_in") is None and est.get("shake_reveal_in") is not None:
        out = {**out, "_shake_reveal_in": float(est["shake_reveal_in"])}
    return out


def _appendage_dim_flags(measurements, dims_state):
    """Cross-check doctrine (ruled 2026-07-15): a user-measured chase
    height is checked against the AI-attributed face area — disagreement
    is FLAGGED, never averaged."""
    flags = []
    try:
        area = float(measurements.get("_ai_appendage_sqft") or 0)
    except (TypeError, ValueError):
        area = 0
    if area <= 0:
        return flags
    for key, fields in (dims_state or {}).items():
        h_entry = (fields or {}).get("height_ft") or {}
        if h_entry.get("status") not in _DIM_STATUSES:
            continue
        h = float(h_entry.get("value") or 0)
        if h <= 0:
            continue
        d_entry = (fields or {}).get("depth_ft") or {}
        d = float(d_entry.get("value") or 0) if d_entry.get("status") in _DIM_STATUSES else 2.0
        implied_girth = area / h
        floor_girth = 2 * d + 1.0  # two return faces + 1' minimum front face
        if implied_girth < floor_girth:
            flags.append(
                f"{key}: entered height {h:g}' disagrees with the AI-attributed face area "
                f"({area:.0f} ft² implies {implied_girth:.1f}' girth < {floor_girth:.1f}' floor) "
                "— flagged, not averaged")
    return flags


async def _blueprint_dim_offers(est_id):
    """Offer-and-confirm only (ruled 2026-07-15): where a blueprint run
    exists on the estimate, the panel may OFFER the print-derived
    dimension. Never auto-applied."""
    doc = await db.ai_blueprint_runs.find_one(
        {"estimate_id": est_id, "status": "done"},
        {"_id": 0, "run_id": 1, "result.raw_ai.appendages": 1},
        sort=[("created_at", -1)])
    if not doc:
        # Artifact pin read-side: archived blueprint runs (24h TTL defusal)
        doc = await find_archived_run(
            {"estimate_id": est_id, "status": "done",
             "result.raw_ai.appendages": {"$exists": True}})
    if not doc:
        return []
    offers = []
    for ap in ((doc.get("result") or {}).get("raw_ai") or {}).get("appendages") or []:
        wall = str(ap.get("wall") or "").lower()
        if wall not in _WALLS:
            continue
        offers.append({
            "key": f"appendage:{wall}",
            "kind": ap.get("kind"),
            "height_ft": ap.get("height_ft"),
            "depth_ft": ap.get("depth_ft"),
            "width_ft": ap.get("width_ft"),
            "run_id": doc.get("run_id"),
        })
    return offers


def _amber_items(corner_locations, verify_state):
    """Amber field-verify checklist (approved post-C4): the presence-
    guarantee doctrine surfaced to the user. Unconfirmed (amber) corner
    locations are INCLUDED in stick counts and flagged. Full verb set
    (ruled 2026-07-15): verify (ratification) / relocate (wrong wall →
    correct wall) / not-present — provenance-carried, revertible."""
    items = []
    for i, c in enumerate(corner_locations):
        if str(c.get("tier") or "confirmed") == "confirmed":
            continue
        key, locator, kind = _corner_key(c, i)
        st = (verify_state or {}).get(key) or {}
        items.append({
            "key": key, "kind": kind, "locator": locator,
            "walls": c.get("walls") or [],
            "status": st.get("status") or "unverified",
            "relocated_to": st.get("to"),
            "position_frac": st.get("position_frac"),
            "verified_at": st.get("at"), "verified_by": st.get("by"),
        })
    return items


def _apply_corner_review(corner_locations, verify_state):
    """Relocation ruling (2026-07-15): user_removed corners leave the
    assembly inputs (stick counts re-derive); user_relocated corners
    carry their corrected wall downstream (3D placement, stick
    anchoring). Detected features MOVE — geometry is never invented;
    dimensions remain run-measured. Keys derive from the ORIGINAL
    locator so state stays stable."""
    out = []
    for i, c in enumerate(corner_locations or []):
        key, _, _ = _corner_key(c, i)
        st = (verify_state or {}).get(key) or {}
        s = st.get("status")
        if s == "user_removed":
            continue
        if s == "user_relocated" and st.get("to") in _WALLS:
            c = {**c, "walls": [st["to"]], "relocated_to": st["to"]}
            if isinstance(st.get("position_frac"), (int, float)):
                c = {**c, "position_frac": float(st["position_frac"])}
        out.append(c)
    return out


def _color_matrix(lines):
    """Per-group availability of EVERY palette color against the group's
    actual items (picker badging, approved with the honest constraint:
    the matrix INFORMS, never forbids — flagged combos stay selectable)."""
    from lp_colors import ALL_COLORS, group_for_line
    from lp_expertfinish_matrix import check_combo
    rank = {"available": 0, "gap": 1, "unsupported": 2}
    by_group: dict = {}
    for l in lines:
        g = l.get("component_group") or group_for_line(l)
        if g:
            by_group.setdefault(g, set()).add(str(l.get("name") or ""))
    if not by_group:
        return {}
    entries = list(by_group.items())
    entries.append(("all", set().union(*by_group.values())))
    out = {}
    for g, names in entries:
        gm = {}
        for c in ALL_COLORS:
            worst = {"status": "available", "note": ""}
            flagged = 0
            for n in names:
                r = check_combo(n, c)
                if r["status"] != "available":
                    flagged += 1
                if rank[r["status"]] > rank[worst["status"]]:
                    worst = r
            gm[c] = {"status": worst["status"], "note": worst["note"],
                     "flagged_items": flagged, "item_count": len(names)}
        out[g] = gm
    return out


# ───────────── Confirm-openings review (approved post-C4) ─────────────
# One-tap ratification of detected openings BEFORE package derivation.
# user_confirmed promotes to verified standing; user_corrected shifts the
# derived counts with provenance; skippable — unconfirmed flags persist.
_OPENING_COUNT_FIELD = {
    "window": "window_count", "entry_door": "entry_door_count",
    "patio_door": "patio_door_count", "garage_door": "garage_door_count",
}
_OPENING_TYPES = ("window", "entry_door", "patio_door", "garage_door", "vent")

# Delete-guard doctrine (ruled 2026-07-15): what each opening type feeds
# downstream — surfaced on the item so the card can warn before removal.
_REMOVE_CARRIES = {
    "window":      "540 wrap trim (windows 4-side, 14 LF each)",
    "entry_door":  "540 wrap trim (18 LF head+legs) + starter-course entry-width deduction",
    "patio_door":  "540 wrap trim (19 LF head+legs)",
    "garage_door": "540 wrap trim (32 LF)",
}


def _openings_items(run, review_state):
    res = run.get("result") or {}
    sched = (res.get("measurements") or {}).get("_ai_openings_schedule") or []
    # Blueprint runs carry `page_paths` (plan sheets) instead of
    # `photo_paths` — the review card links the governing sheet image
    # in place of a photo crop (ruling 2026-07-15).
    paths = [p for p in str(run.get("photo_paths") or run.get("page_paths") or "").split(",") if p]
    rid = str(run.get("run_id") or "")[:8]
    items = []
    for i, s in enumerate(sched):
        key = f"open:{rid}:{i}"  # run-scoped — a fresh extraction resets review
        locs = s.get("locations") or []
        pi = locs[0].get("photo_idx") if locs else None
        photo_url = None
        if isinstance(pi, int) and 0 <= pi < len(paths):
            photo_url = f"/api/uploads/{paths[pi]}"
        st = (review_state or {}).get(key) or {}
        eff_type = st.get("corrected_type") or s.get("type")
        carries = [_REMOVE_CARRIES[eff_type]] if eff_type in _REMOVE_CARRIES else []
        items.append({
            "key": key, "index": i,
            "elevation": s.get("elevation"), "type": s.get("type"),
            "style": s.get("style") or "", "size_label": s.get("size_label") or "",
            "count": int(s.get("count") or 1),
            "photo_url": photo_url,
            "bbox": (locs[0].get("bbox") if locs else None),
            "carries": carries,
            "status": st.get("status") or "unconfirmed",
            "corrected_type": st.get("corrected_type"),
            "at": st.get("at"), "by": st.get("by"),
        })
    return items


def _apply_openings_review(measurements, items):
    """user_corrected type changes shift derived counts (provenance-
    carried). user_removed rows leave counts AND the schedule (the
    schedule feeds trim math directly — starter entry-width deduction).
    Pin (ruled 2026-07-15): a removed opening appears nowhere in counts,
    trim math, or quote surfaces; revertible via reset."""
    adj = dict(measurements)
    corrections = []
    removals = []
    removed_idx = set()
    retyped = {}
    for it in items:
        new_t = it.get("corrected_type")
        if it["status"] == "user_removed":
            n = it["count"]
            f_old = _OPENING_COUNT_FIELD.get(it["type"])
            if f_old:
                adj[f_old] = max(int(adj.get(f_old) or 0) - n, 0)
            removed_idx.add(it["index"])
            removals.append(
                f"{it['elevation']} {it['type']} ×{n} removed — not present (user_removed)")
        elif it["status"] == "user_corrected" and new_t and new_t != it["type"]:
            n = it["count"]
            f_old = _OPENING_COUNT_FIELD.get(it["type"])
            f_new = _OPENING_COUNT_FIELD.get(new_t)
            if f_old:
                adj[f_old] = max(int(adj.get(f_old) or 0) - n, 0)
            if f_new:
                adj[f_new] = int(adj.get(f_new) or 0) + n
            retyped[it["index"]] = new_t
            corrections.append(
                f"{it['elevation']} {it['type']} → {new_t} ×{n} (user_corrected)")
    # Schedule coherence: removed rows drop out, corrected rows carry
    # their new type — downstream consumers (starter deduction) iterate
    # the schedule directly.
    sched = adj.get("_ai_openings_schedule")
    if sched and (removed_idx or retyped):
        adj["_ai_openings_schedule"] = [
            ({**row, "type": retyped[i]} if i in retyped else row)
            for i, row in enumerate(sched)
            if i not in removed_idx
        ]
    summary = {
        "total": len(items),
        "confirmed": sum(1 for i in items if i["status"] == "user_confirmed"),
        "corrected": sum(1 for i in items if i["status"] == "user_corrected"),
        "removed": sum(1 for i in items if i["status"] == "user_removed"),
        "unconfirmed": sum(1 for i in items if i["status"] == "unconfirmed"),
        "corrections": corrections,
        "removals": removals,
    }
    return adj, summary


@router.post("/estimates/{est_id}/lp-package/blueprint-applied")
async def lp_blueprint_applied(est_id: str, body: dict | None = None,
                               user: dict = Depends(get_current_user)):
    """THE CUT (ruled 2026-07-14): applying a blueprint takeoff to an
    LP estimate makes the estimate a persistent artifact of that run —
    archive it (blueprint runs carry a 24h TTL that would otherwise
    reap the Material List panel's source by morning)."""
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0, "id": 1})
    if not est:
        raise HTTPException(status_code=404, detail="Not found")
    rid = str((body or {}).get("run_id") or "").strip() or None
    if not rid:
        latest = await db.ai_blueprint_runs.find_one(
            {"estimate_id": est_id, "status": "done"},
            {"_id": 0, "run_id": 1}, sort=[("created_at", -1)])
        rid = (latest or {}).get("run_id")
    archived = await archive_run_for_artifact(run_id=rid, reason="blueprint-apply") if rid else None
    if archived:
        # Source-governance stamp: the APPLIED run governs the panel —
        # previewed-but-unapplied runs never switch the composition source.
        # (lp_-prefixed only: fork-boundary field tagging.)
        await db.estimates.update_one(
            {"id": est_id, "company_id": user["company_id"]},
            {"$set": {"lp_source_run_id": archived}})
    return {"ok": True, "archived_run_id": archived}


@router.post("/estimates/{est_id}/lp-package/materialize")
async def lp_package_materialize(est_id: str, payload: dict | None = None,
                                 user: dict = Depends(get_current_user)):
    """APPLY GATE for photo/blueprint-sourced LP estimates (ruled
    2026-07-25 — Apply Measurements regression). Materializes the derived
    LP composition into the group tab lines through the SAME rebuild
    machinery hover-lp-run uses (rebuild_lp_tab_lines: price inheritance,
    family zeroing, human-qty survival, v3 labor binding). THE CUT stands:
    the frontend still merges NO composition lines — this is the
    server-side engine path. Idempotent: re-applying re-derives on the
    same governing run. The governing run is archived (persistent
    artifact) and stamped as lp_source_run_id."""
    est_meta, run, binding = await _load_run(
        est_id, user["company_id"], (payload or {}).get("run_id"))
    full_est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "kind": 1, "waste_pct": 1, "porch_ceilings": 1,
         "overhang_in": 1, "default_siding_profile": 1, "color_tier": 1,
         "shake_reveal_in": 1, "lp_colors": 1, "lp_flag_checklist": 1})
    if (full_est or {}).get("kind") != "lp_smart":
        raise HTTPException(status_code=400,
                            detail="LP materialize is lp_smart-kind only")
    # Same measurement gates the preview composes through — the tab lines
    # must speak the exact numbers the Material List panel shows.
    measurements, corner_locations, wall_heights = _extract(run)
    op_items = _openings_items(run, est_meta.get("lp_openings_review"))
    measurements, _op_summary = _apply_openings_review(measurements, op_items)
    measurements = _apply_default_profile(measurements, est_meta)
    measurements = _apply_flag_checklist(measurements, est_meta, run)
    measurements = _apply_key_bound_areas(measurements, est_meta)
    # WASTE IS THE CONTRACTOR'S (ruled 2026-07-19): the visible field is
    # the only waste applied — never a silent engine default.
    waste_field = float((full_est or {}).get("waste_pct") or 0)
    from routes.hover import rebuild_lp_tab_lines
    # profile=None: default-profile inheritance already applied above via
    # _apply_default_profile (annotations beat the default — pinned).
    tab_lines, _scoped = await rebuild_lp_tab_lines(
        est_id=est_id, company_id=user["company_id"],
        base_measurements=measurements, est=full_est or {},
        profile=None, waste_field=waste_field)
    est_set: dict = {"lines": tab_lines}
    rid = str(run.get("run_id") or "").strip() or None
    archived = await archive_run_for_artifact(
        run_id=rid, reason="lp-materialize") if rid else None
    if archived:
        est_set["lp_source_run_id"] = archived
    await db.estimates.update_one(
        {"id": est_id, "company_id": user["company_id"]}, {"$set": est_set})
    await log_estimate_event(est_id, "lp.tab_lines.materialized", {
        "run_id": rid, "binding": binding,
        "default_profile": est_meta.get("default_siding_profile"),
        "waste_pct": waste_field, "line_count": len(tab_lines),
        "by": user.get("email"),
    })
    return {"ok": True, "run_id": rid, "binding": binding,
            "line_count": len(tab_lines)}


@router.get("/lp-package/colors")
async def lp_package_colors(user: dict = Depends(get_current_user)):
    """ExpertFinish palette + component groups for the Material List
    color selector. Names are the backend source of truth; swatch hexes
    are frontend visualization approximations."""
    from lp_colors import (ALL_COLORS, COMPONENT_GROUPS, EXPERTFINISH_CORE_16,
                           NATURALS_COLLECTION, PRIMED)
    return {
        "groups": list(COMPONENT_GROUPS),
        "colors": ALL_COLORS,
        "collections": {"core": EXPERTFINISH_CORE_16,
                        "naturals": NATURALS_COLLECTION, "primed": PRIMED},
    }


@router.post("/estimates/{est_id}/lp-package/preview")
async def lp_package_preview(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Assemble the LP-native package from an AI Measure run. `run_id`
    optional — falls back to the latest terminal run. `substitutions`
    optional {line_name: new_item} — table-limited, re-derived, provenance-
    carried, never remembered. `colors` optional {"all": X, group: Y} —
    per-component line-level colors (Howard's color architecture).
    PRICING: sell prices at the estimate's admin-assigned tier (default
    Tier B/25%) — the payload can NEVER set a tier or margin here; the
    tier picker is admin-side only. Response is ALWAYS redacted:
    cost / margin / tier never leave the server on this surface."""
    est, run, binding = await _load_run(est_id, user["company_id"], (payload or {}).get("run_id"))
    measurements, corner_locations, wall_heights = _extract(run)
    op_items = _openings_items(run, est.get("lp_openings_review"))
    measurements, op_summary = _apply_openings_review(measurements, op_items)
    corners_eff = _apply_corner_review(corner_locations, est.get("lp_field_verify"))
    corners_eff = _apply_appendage_dims(corners_eff, est.get("lp_appendage_dims"))
    measurements = _apply_default_profile(measurements, est)
    measurements = _apply_flag_checklist(measurements, est, run)
    measurements = _apply_key_bound_areas(measurements, est)
    measurements = _apply_contractor_waste(measurements, est)
    pkg = assemble_lp_package(measurements, corners_eff, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"), tier_sheet=await _load_tier_sheet_for(est))
    pkg["run_id"] = run.get("run_id")
    pkg["geometry_basis"] = _geometry_basis(est, run, binding)
    # Source chip (Howard-approved 2026-07-14): presenters answer "where
    # did these numbers come from?" in one glance.
    if run.get("source") == "hover":
        pkg["source_kind"] = "hover"
        pkg["source_label"] = "Hover import"
        pkg["hover_mapping_flags"] = _checklist_flags(run, est)
    elif run.get("page_paths"):
        pkg["source_kind"] = "blueprint"
        pkg["source_label"] = f"Blueprint — {run.get('page_count') or '?'} sheet(s)"
    else:
        pkg["source_kind"] = "photo"
        pkg["source_label"] = "AI Photo Measure"
    pkg["amber_items"] = _amber_items(corner_locations, est.get("lp_field_verify"))
    pkg["appendage_dims"] = est.get("lp_appendage_dims") or {}
    pkg["appendage_dim_flags"] = _appendage_dim_flags(measurements, est.get("lp_appendage_dims"))
    pkg["appendage_dim_offers"] = await _blueprint_dim_offers(est_id)
    pkg["openings_review"] = {**op_summary, "items": op_items}
    pkg["color_matrix"] = _color_matrix(pkg.get("lines") or [])
    return redact_external(pkg)


_COMPARE_FAMILIES = ("lap", "board_batten")


@router.get("/estimates/{est_id}/readiness")
async def estimate_readiness(est_id: str, user: dict = Depends(get_current_user)):
    """ESTIMATE READINESS CHECKLIST (authorized 2026-07-23): one glance at
    everything standing between the contractor and a real number —
    pending prices, open mapping flags, unentered field-verify items,
    unpriced money-surface rows. SOFT surface only (ruled): informational;
    the Customer Quote button NEVER hard-blocks on it."""
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "id": 1, "lines": 1, "kind": 1})
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    items = []
    # FAMILY-CHECK TRIPWIRE (authorized 2026-07-24, Casile lap-leak class):
    # exactly ONE siding family may carry derived qty on the money surface.
    # Human-typed rows (qty_src == "human") are choices, not residue.
    fam_markers = {"lap": ("series lap",), "board & batten": ("4' x 10' panel",),
                   "shake": ("shake",)}
    fams_hit = {}
    for l in est.get("lines") or []:
        if l.get("tab") != "lp_smart" or not (l.get("qty") or 0):
            continue
        if (l.get("qty_src") or "") == "human":
            continue
        nm = str(l.get("name") or "").lower()
        for fam, marks in fam_markers.items():
            if any(mk in nm for mk in marks):
                fams_hit.setdefault(fam, []).append(f"{l.get('name')} (qty {l.get('qty'):g})")
    if len(fams_hit) > 1:
        detail = " + ".join(f"{fam}: {', '.join(rows)}" for fam, rows in fams_hit.items())
        items.append({
            "kind": "family_conflict", "code": "siding_family_conflict",
            "label": (f"SIDING FAMILY CONFLICT — {len(fams_hit)} families carry derived "
                      f"quantity on the money surface ({detail}). Profile owns its family: "
                      "re-derive before quoting."),
        })
    for l in est.get("lines") or []:
        if (l.get("qty") or 0) > 0 and not (l.get("mat") or 0) and not (l.get("lab") or 0):
            items.append({
                "kind": "unpriced_row", "code": l.get("name"),
                "label": (f"Unpriced money-surface row: {l.get('name')} "
                          f"({l.get('tab') or 'vinyl'} tab, qty {l.get('qty'):g})"),
            })
    # Q1 (ruled 2026-07-27): Tear-Off + Dumpster quantity is the
    # contractor's — readiness panel shows them while unset.
    _q1_seen = set()
    for l in est.get("lines") or []:
        nm = (l.get("name") or "")
        if nm in ("Tear-Off", "Dumpster") and not (l.get("qty") or 0) and nm not in _q1_seen:
            _q1_seen.add(nm)
            items.append({
                "kind": "qty_pending", "code": nm,
                "label": (f"QUANTITY PENDING — {nm}: contractor-entered by ruling "
                          "(Q1, 2026-07-27); set the quantity (and labor) before quoting"),
            })
    # LABOR IS THE CONTRACTOR'S — v3 zeroing (sealed 2026-07-24): every
    # labor default is $0 until the contractor fills it. The quote carries
    # this labor-pending statement as one aggregated, always-visible item.
    pend_names = []
    for l in est.get("lines") or []:
        if ((l.get("lab_src") or "") == "pending" and (l.get("qty") or 0) > 0
                and l.get("name") not in pend_names):
            pend_names.append(l.get("name"))
    if pend_names:
        items.append({
            "kind": "labor_pending", "code": "labor_pending_contractor",
            # ONE LINE, a count, never a list (re-ruled 2026-07-29): labor
            # is N/A or >$0 — anything else is UNDECIDED. Does NOT block.
            "label": (f"LABOR UNDECIDED on {len(pend_names)} row(s) — enter "
                      "your rate (above $0) or mark N/A."),
        })
    try:
        pkg = await lp_package_preview(est_id, None, user)
    except HTTPException:
        pkg = None
    if pkg:
        for l in pkg.get("lines") or []:
            if l.get("pricing_status") == "pending" and (l.get("qty") or 0) > 0:
                items.append({"kind": "pending_price", "code": l.get("name"),
                              "label": f"Pending price (escalated by name): {l.get('name')}"})
        for f in pkg.get("hover_mapping_flags") or []:
            if f.get("status") != "closed":
                items.append({"kind": "open_flag", "code": f.get("code"),
                              "label": f"Open flag: {f.get('label')}"})
        for a in pkg.get("amber_items") or []:
            if (a.get("status") or "unverified") == "unverified":
                items.append({"kind": "field_verify", "code": a.get("key"),
                              "label": (f"Field-verify open: {a.get('kind') or 'corner'} "
                                        f"@ {a.get('locator') or '?'}")})
    return {"estimate_id": est_id, "items": items,
            "open_count": len(items), "ready": not items}


# ═══════════ QUOTE GATE vs ORDER GATE (Howard ruled 2026-07-29) ══════════
# Two distinct failure points: QUOTE blocks the customer surfaces (email,
# Accept page at token mint, PDF, freeze, QR); ORDER blocks material
# release / PO / truck. Every flag lives in exactly one tier (gates.py
# registry — an unassigned flag fails the suite). The ORDER side is the
# FINAL-JOB SURFACE: taped fields (batten_wall_heights et al.) live there
# and SUPERSEDE derived values.
async def evaluate_gates(est_id: str, user: dict) -> dict:
    from gates import ORDER_BLOCKING, quote_gate_blockers, tier_for
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "id": 1, "lines": 1, "kind": 1, "order_released": 1,
         "customer_name": 1})
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    measurements = None
    try:
        _, run, _ = await _load_run(est_id, user["company_id"])
        measurements, _, _ = _extract(run)
    except HTTPException:
        run = None
    quote_items = quote_gate_blockers(est, measurements)
    order_items: list[dict] = []
    try:
        pkg = await lp_package_preview(est_id, None, user)
    except HTTPException:
        pkg = None
    if pkg:
        for f in pkg.get("hover_mapping_flags") or []:
            code = f.get("code")
            try:
                tier = tier_for(code, "open_flag")
            except KeyError:
                tier = "order"   # runtime never hard-fails; the SUITE does
            item = {"code": code, "tier": tier,
                    "blocking": tier == "order" and code in ORDER_BLOCKING
                    and f.get("status") != "closed",
                    "status": f.get("status") or "open",
                    "label": f.get("label"), "verify": f.get("verify"),
                    **({"closed_by": f.get("closed_by"),
                        "closed_at": f.get("closed_at"),
                        "values": f.get("values")}
                       if f.get("status") == "closed" else {})}
            (order_items if tier == "order" else quote_items).append(item)
        for a in pkg.get("amber_items") or []:
            if (a.get("status") or "unverified") == "unverified":
                order_items.append({
                    "code": a.get("key"), "tier": "order", "blocking": False,
                    "status": "open",
                    "label": (f"Field-verify open: {a.get('kind') or 'corner'} "
                              f"@ {a.get('locator') or '?'}")})
    quote_blocking = [i for i in quote_items if i.get("blocking", True)
                      and i.get("status", "open") != "closed"]
    order_blocking = [i for i in order_items if i.get("blocking")
                      and i.get("status", "open") != "closed"]
    return {
        "estimate_id": est_id,
        "quote": {"blocked": bool(quote_blocking), "blocking": quote_blocking,
                  "items": quote_items},
        "order": {"blocked": bool(order_blocking), "blocking": order_blocking,
                  "items": order_items},
        "order_released": est.get("order_released"),
    }


@router.get("/estimates/{est_id}/gates")
async def estimate_gates(est_id: str, user: dict = Depends(get_current_user)):
    return await evaluate_gates(est_id, user)


async def assert_quote_gate(est_id: str, user: dict) -> None:
    """HARD block for the customer surfaces (email, PDF, freeze/QR —
    the Accept page blocks at token mint via the email door)."""
    gates = await evaluate_gates(est_id, user)
    if gates["quote"]["blocked"]:
        raise HTTPException(status_code=409, detail={
            "gate": "quote",
            "message": ("QUOTE GATE — this estimate cannot reach a customer "
                        "surface until the blocking items clear (ruled 2026-07-29)"),
            "blocking": [{"code": i.get("code"), "label": i.get("label")}
                         for i in gates["quote"]["blocking"]],
        })


@router.post("/estimates/{est_id}/order-release")
async def order_release(est_id: str, payload: dict | None = None,
                        user: dict = Depends(get_current_user)):
    """MATERIAL RELEASE — the ORDER gate's enforcement point (PO/truck
    surfaces hang off this stamp). Refused while any order-tier blocking
    flag is open; the stamp records the gate snapshot it cleared on."""
    gates = await evaluate_gates(est_id, user)
    if gates["order"]["blocked"]:
        raise HTTPException(status_code=409, detail={
            "gate": "order",
            "message": ("ORDER GATE — material does not leave until the "
                        "taped fields close (ruled 2026-07-29)"),
            "blocking": [{"code": i.get("code"), "label": i.get("label")}
                         for i in gates["order"]["blocking"]],
        })
    now = datetime.now(timezone.utc).isoformat()
    stamp = {"by": user.get("email"), "at": now,
             "order_items_cleared": [i.get("code") for i in gates["order"]["items"]]}
    await db.estimates.update_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"$set": {"order_released": stamp}})
    await log_estimate_event(est_id, "order.released", stamp)
    return {"ok": True, "order_released": stamp}


async def _load_tier_sheet_for(est: dict) -> dict:
    """Master-price-sheet index for sheet-binding (ruled 2026-07-23):
    the sheet the contractor ACTUALLY SEES — company tier baseline merged
    with their per-company catalog overrides, name-normalized → {mat, lab}.
    A dangling tier pointer (tier reseed churn — Casile item-3 root cause)
    falls back to the default tier sheet, the SAME fallback the catalog
    surface applies — an empty sheet unbinds every row and misreports
    'no dealer cost' when the true cause is a broken pointer."""
    from lp_costs import sheet_norm
    cid = est.get("company_id")
    if not cid and est.get("id"):
        doc = await db.estimates.find_one({"id": est["id"]}, {"_id": 0, "company_id": 1})
        cid = (doc or {}).get("company_id")
    comp = await db.companies.find_one({"id": cid}, {"_id": 0, "price_tier_id": 1}) if cid else None
    tier = (await db.price_tiers.find_one({"id": comp["price_tier_id"]}, {"_id": 0, "sections": 1})
            if comp and comp.get("price_tier_id") else None)
    if tier is None:
        from catalog_seed import DEFAULT_TIER_NAME
        tier = await db.price_tiers.find_one({"name": DEFAULT_TIER_NAME}, {"_id": 0, "sections": 1})
    idx = {}
    by_section_key = {}
    for sec in (tier or {}).get("sections") or []:
        for it in sec.get("items") or []:
            if it.get("name"):
                entry = {"mat": float(it.get("mat") or 0),
                         "lab": float(it.get("lab") or 0)}
                idx[sheet_norm(it["name"])] = entry
                by_section_key[f"{sec.get('title')}::{it['name']}"] = entry
    cat = (await db.catalogs.find_one({"company_id": cid}, {"_id": 0, "overrides": 1})
           if cid else None)
    for key, ov in ((cat or {}).get("overrides") or {}).items():
        entry = by_section_key.get(key)
        if entry is not None and isinstance(ov, dict):
            for f in ("mat", "lab"):
                if ov.get(f) is not None:
                    entry[f] = float(ov[f])
    return idx


def _force_profile_measurements(measurements: dict, family: str) -> dict:
    """Re-express the WHOLE siding field as one profile family on the SAME
    geometry (headline siding_sqft, C4 gable basis). B&B panels start on
    the ledge — starter is ruled OFF for that family. Used by compare AND
    by the estimate default-profile inheritance."""
    m = dict(measurements)
    try:
        sqft = float(m.get("siding_sqft") or 0)
    except (TypeError, ValueError):
        sqft = 0.0
    m["_per_profile_sqft"] = {family: sqft}
    m["_force_profile_lines"] = True
    m.pop("_per_profile_composition", None)
    m.pop("_profile_composition_conflicts", None)
    if family in ("board_batten", "vertical"):
        m["starter_lf"] = 0  # RULED + PINNED: no starter on B&B composition
    return m


def _apply_default_profile(measurements: dict, est: dict) -> dict:
    """Estimate default-profile inheritance (slice 1, LP-only).

    Every wall/region composes at the estimate's `default_siding_profile`
    unless the extraction already carries an explicit multi-profile split
    (per-region annotations, accents, mixed jobs) — annotations are the
    exception layer and WIN where present. A single-profile house needs
    zero annotations. Lap is the engine's own default, so we only force
    when a non-lap default is set on an otherwise single-profile job.
    """
    profile = est.get("default_siding_profile")
    # Surface the selected family (rulings A/C, 2026-07-26): conservation
    # residue lands on it; the visible waste field governs ITS split line;
    # other families default by family.
    measurements = dict(measurements)
    measurements["_default_family"] = (
        profile if profile in _DEFAULT_PROFILES else "lap")
    if profile not in _DEFAULT_PROFILES:
        return measurements
    per_profile = measurements.get("_per_profile_sqft") or {}
    positive = {f: s for f, s in per_profile.items()
                if isinstance(s, (int, float)) and s > 0}
    # Annotated / mixed job: keep the extraction's per-region split intact.
    if len(positive) > 1:
        return measurements
    return _force_profile_measurements(measurements, profile)


def _hover_mapping_contract(hover_meas: dict, profile: str,
                            facade_scope: dict | None = None,
                            soffit_breakdown: dict | None = None,
                            waste_pct: float | None = None) -> tuple[dict, list]:
    """Explicit Hover→engine mapping contract (ruled 2026-07-16; scope
    rulings 2026-07-17).

    Hover's report quantities map DELIBERATELY into the engine's expected
    measurement basis; fields the engine needs that Hover cannot supply are
    FLAGGED pending, never approximated.

    Round-two rulings folded in:
      • facade_scope — WRAP-ONLY default: never silently sum all facade
        types; stucco/brick excluded unless explicitly included
      • openings — Hover facades are net-of-openings and compose AS-IS
        (per-source convention, named on the basis line)
      • soffit_breakdown — measured per-surface soffit governs when the
        report supplies it; ceilings type as closed (porch-ceiling
        mechanism); eaves vented / rakes+ceilings closed
      • waste — unified into the estimate's visible waste_pct field
        (ruled 2026-07-20): hover-lp-run writes 10.0 into the field on
        import; _waste_pct is set here ONLY on explicit override —
        otherwise the field governs via _apply_contractor_waste

    CLASS A — MEASURED AREA SILENTLY LOST AT INTAKE (sealed 2026-07-28).
    EVIDENCE #1, verbatim per Howard's rider: "the raw Hover door
    over-composes Haugh by 546 ft² and the only reason my real quote is
    right is my own manual facade-scope custom." 261 Haugh is new
    construction in Tyvek: every Siding column reads 0, the extractor
    folded the FACADES TOTAL (2,610 ft² = wrap 2,064 + stucco 312 +
    brick 234) into top-level siding_sqft, and the old wrap-only guard
    (fb.siding_sqft > 0) could not fire — 546 ft² of block composed
    silently. The machine defaulted wrong and a human caught it. That is
    the whole argument for the class.
    CONSERVATION INVARIANT, at intake: every measured ft² lands in
    exactly one of SIDED · EXPLICITLY EXCLUDED · FLAGGED; sum in = sum
    out (`_area_conservation`, pinned). Any import where area moves
    without an exclusion decision FAILS.

    CLASS C — VISION-GRADE DATA GOVERNING A MONEY LINE (sealed
    2026-07-28). Hover AREAS are MEASURED; Hover MATERIAL LABELS are a
    VISION READ — a label SUGGESTS, never GOVERNS. With a zero/absent
    Siding row the label-suggested wrap row composes ONLY under an OPEN
    amber facade_scope flag, reversible both ways (same machinery as the
    14-vs-20 corner correction). Opening-to-facade attribution is READ
    FROM THE FACADE ASSIGNMENT — never inferred from opening type,
    elevation, or height; where Hover cannot attribute, it FLAGS.
    """
    passthrough = (
        "siding_sqft", "siding_with_openings_sqft",
        "outside_corner_count", "outside_corner_lf",
        "inside_corner_count", "inside_corner_lf",
        "eaves_lf", "rakes_lf", "starter_lf",
        "window_count", "entry_door_count", "patio_door_count",
        "garage_door_count", "door_count", "opening_perimeter_lf",
        "stories", "overhang_in",
        # Q10/Q14 (ruled 2026-07-27): MEASURED DATA NEVER DROPS — the
        # report's soffit total, frieze runs and accessory counts pass
        # through to the engine (3 Degree Rd: dropped soffit 2620 sqft
        # and 683 LF of frieze were the two biggest misses).
        "soffit_sqft", "level_frieze_lf", "sloped_frieze_lf",
        "drip_edge_lf", "total_trim_sqft", "vent_count", "shutter_count",
    )
    m = {k: hover_meas[k] for k in passthrough if k in hover_meas}
    m["_hover_source"] = True
    if waste_pct is not None:
        m["_waste_pct"] = float(waste_pct)
    fb = hover_meas.get("facade_breakdown") or {}
    flags = []
    # SEALED DEFAULT (Howard, 2026-07-28 — production restore): the default
    # COMPOSES at the door — WALL classes side, MASONRY classes exclude
    # with the reason named, an unrecognized label SIDES and flags loudly.
    # FLAGGED MEANS WE MADE A CALL AND TOLD THE USER — no zero is ever
    # produced by an unmade decision. The flag is INFORMATIONAL, never a
    # gate. label_suggested_wrap ("no call made, no material produced")
    # RETIRED — a fourth state Howard never ruled; it zeroed the vinyl
    # door on 2026-07-28 morning. Explicit facade_scope (the picker)
    # always overrides. One emitter: lp_conventions.compose_default_facade_scope.
    from lp_conventions import compose_default_facade_scope, facade_scope_flag_label
    scope_default = compose_default_facade_scope(fb)
    measured_total = (scope_default["measured_total"] if scope_default
                      else float(hover_meas.get("siding_sqft") or 0))
    composed = False
    if not facade_scope and scope_default:
        facade_scope = scope_default
        composed = True
        flags.append({
            "code": "facade_scope",
            "label": facade_scope_flag_label(scope_default),
            "verify": "Informational — change the scope in the facade picker if the walk disagrees (reversible both ways)",
        })
    if facade_scope and (composed or (facade_scope.get("wrap_sqft") or 0) > 0):
        wrap = float(facade_scope["wrap_sqft"])
        m["siding_sqft"] = wrap
        m["_facade_scope"] = {
            "mode": facade_scope.get("mode") or "wrap_only",
            "wrap_sqft": wrap,
            "measured_total": measured_total,
            "excluded": facade_scope.get("excluded") or {},
            **({"sided": facade_scope["sided"],
                "excluded_reasons": facade_scope["excluded_reasons"]}
               if composed else {}),
        }
    # CLASS A CONSERVATION LEDGER (sealed 2026-07-28): sum in = sum out.
    _sided = float(m.get("siding_sqft") or 0)
    _excl = sum(float(v) for v in ((m.get("_facade_scope") or {}).get("excluded") or {}).values())
    _flagged_residue = round(measured_total - _sided - _excl, 1) if measured_total > 0 else 0.0
    m["_area_conservation"] = {
        "measured_total_sqft": round(measured_total, 1),
        "sided_sqft": round(_sided, 1),
        "excluded_sqft": round(_excl, 1),
        "flagged_sqft": max(_flagged_residue, 0.0),
    }
    if _flagged_residue > 0.5:
        flags.append({
            "code": "area_conservation",
            "label": (f"AREA CHECK: {_flagged_residue:g} ft² "
                      f"of measured facade area is neither SIDED nor EXPLICITLY EXCLUDED — "
                      "no ft² disappears without an exclusion decision"),
            "verify": "Attribute the residue in the facade picker (side it or exclude it)",
        })
    # CLASS C — OPENING ATTRIBUTION (R6 sealed 2026-07-28): read from the
    # facade assignment, never inferred. This report carries none → FLAG.
    _opening_total = int(hover_meas.get("opening_count") or 0)
    if (m.get("_facade_scope") and (m["_facade_scope"].get("excluded") or {})
            and _opening_total > 0
            and not hover_meas.get("opening_facade_assignments")):
        flags.append({
            "code": "opening_facade_attribution",
            "label": (f"OPENINGS NOT TIED TO WALLS: {_opening_total} openings are not "
                      "assigned to a wall in this report. Window and door trim is "
                      "figured against ALL openings until you say which sit on the "
                      "siding — close this with the in-scope counts."),
            "verify": "Walk the openings — count which sit in the sided walls vs the excluded area",
        })
    if soffit_breakdown:
        eaves = float(soffit_breakdown.get("eaves_sqft") or 0)
        rakes = float(soffit_breakdown.get("rakes_sqft") or 0)
        ceilings = float(soffit_breakdown.get("ceilings_sqft") or 0)
        if eaves + rakes + ceilings > 0:
            m["_soffit_vented_sqft"] = eaves
            m["_soffit_closed_sqft"] = rakes + ceilings
            m["_soffit_ceiling_sqft"] = ceilings
    m = _force_profile_measurements(m, profile)
    flags.append({
        "code": "corner_locators",
        "label": ("Corner sticks are figured from total corner length — the report "
                  "gives counts and total feet, not each corner's own height, so the "
                  "per-corner figure is an average. An average hides any corner "
                  "taller than one 16' stick (an 18'5\" corner takes 2). Tape tall "
                  "corners on the walk — close with the taped heights."),
        "verify": "Walk the corners — confirm counts AND tape any corner taller than 16'",
    })
    # Q2 (ruled 2026-07-27): porch-ceiling FLAG when implied — flag-only,
    # never auto-invent area. Implied when the measured soffit total reads
    # a much deeper average overhang than the stated one.
    _sof = float(m.get("soffit_sqft") or 0)
    _runs = float(m.get("eaves_lf") or 0) + float(m.get("rakes_lf") or 0)
    _oh_ft = float(m.get("overhang_in") or 12) / 12.0
    if _sof > 0 and _runs > 0 and (_sof / _runs) > 2.0 * max(_oh_ft, 0.5):
        flags.append({
            "code": "porch_ceiling_implied",
            "label": (f"PORCH CEILINGS LIKELY: measured soffit {_sof:g} ft² over "
                      f"{_runs:g} LF of eaves+rakes works out to a {_sof / _runs:.1f}' "
                      f"average overhang vs the stated {_oh_ft:g}' — porch ceilings "
                      "are probably inside that soffit number. Measure them and "
                      "enter porch entries in Job Info."),
            "verify": "Measure porch ceilings on site and enter them in Job Info",
        })
    fs = m.get("_facade_scope")
    if fs and fs.get("excluded") and not any(f.get("code") == "facade_scope" for f in flags):
        # (the composed default already emits its informational flag above)
        excl = ", ".join(f"{k} {v:g} ft²" for k, v in fs["excluded"].items())
        flags.append({
            "code": "facade_scope",
            "label": (f"facade scope {fs['mode']}: {fs['wrap_sqft']:g} ft² composes; "
                      f"excluded: {excl} (never silently summed)"),
            "verify": "Confirm the excluded facade materials stay out of the siding scope — re-import with them included if the job wraps them",
        })
    if profile in ("board_batten", "vertical"):
        # HOVER-SCHEDULE height term (Howard, sealed 2026-07-28): Hover
        # PUBLISHES the footprint perimeter — stacked wall height = sided
        # facade area ÷ footprint perimeter (measured, not guessed).
        # QUOTE GATE: never — the quote is sellable with the field empty.
        # ORDER GATE (B&B): taped heights entered at the house before
        # material leaves; TAPED SUPERSEDES DERIVED, derived preserved as
        # flagged comparison, reversible both ways (14-vs-20 machinery).
        _perim = float(hover_meas.get("footprint_perimeter_ft") or 0)
        _sided = float(m.get("siding_sqft") or 0)
        if _perim > 0 and _sided > 0:
            _stacked = round(_sided / _perim, 1)
            _bwh_label = (
                f"Batten height figured from the report: stacked wall height "
                f"{_stacked:g} ft = sided {_sided:g} ft² ÷ footprint perimeter {_perim:g} ft — "
                "good enough to sell; tape the wall heights at the house before "
                "material orders (taped replaces figured, reversible)")
        else:
            _bwh_label = (
                "Batten height term = 0 — this report carries no footprint "
                "perimeter (older import; re-import to carry it). Good enough to "
                "sell; tape wall heights at the house before material orders")
        flags.append({
            "code": "batten_wall_heights",
            "label": _bwh_label,
            "verify": "On any board-and-batten job: tape the wall heights at the house before ordering — taped replaces figured, battens re-figure live",
        })
    flags.append({
        "code": "opening_schedule",
        "label": ("Opening schedule not itemized (report gives counts only) — "
                  "starter deduction and window/door wrap run on per-count "
                  "standards, not each opening's own size."),
        "verify": "Confirm opening count + entry-door widths on site",
    })
    return m, flags


@router.post("/estimates/{est_id}/default-profile")
async def set_default_profile(
    est_id: str, payload: dict, user: dict = Depends(get_current_user),
):
    """Set (or clear) the estimate-level default siding profile. Slice 1:
    records the choice + provenance (from→to, by/at); the full re-derive /
    color re-validation runs through the normal preview + apply gate."""
    profile = (payload or {}).get("profile")
    if profile is not None and profile not in _DEFAULT_PROFILES:
        raise HTTPException(status_code=422, detail=f"profile must be one of {_DEFAULT_PROFILES} or null")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "kind": 1, "default_siding_profile": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    if est.get("kind") != "lp_smart":
        raise HTTPException(status_code=400, detail="Default profile is LP SmartSide only (slice 1)")
    prev = est.get("default_siding_profile")
    now = datetime.now(timezone.utc).isoformat()
    change = {"from": prev, "to": profile, "by": user.get("email"), "at": now}
    sets = {"default_siding_profile": profile,
            "default_siding_profile_change": change}
    # WASTE IS FAMILY-DEFAULTED (sealed 2026-07-24): profile selection
    # pre-fills the ONE visible waste field with the family default
    # (lap 10 · B&B 30; cleared profile → base 10) — contractor edits it
    # afterwards as ever.
    from lp_conventions import family_waste_default_pct
    sets["waste_pct"] = family_waste_default_pct(profile)
    await db.estimates.update_one({"id": est_id}, {"$set": sets})
    await log_estimate_event(est_id, "lp.default_profile.set", {
        "from": prev, "to": profile, "by": user.get("email"),
    })
    return {"ok": True, "from": prev, "to": profile, "change": change,
            "label": _PROFILE_LABEL.get(profile) if profile else None}


# Field-verify-from-flags (approved 2026-07-17): the checklist is generated
# from OPEN mapping-contract flags; entries ride the user-measured machinery
# (by/at, revertible, journey-logged); per-item retirement as flags close;
# an OFFER, never a gate. Closing batten wall-heights re-derives batten LF
# live (+1 run × wall height per wall).
_FLAG_CODES = ("corner_locators", "batten_wall_heights", "opening_schedule",
               "facade_scope", "area_conservation",
               "opening_facade_attribution", "ceiling_dedup",
               # ORDER-tier close (ruling d 2026-07-29): porch ceilings
               # confirmed on site (entered in Job Info, or none exist).
               "porch_ceiling_implied")


def _apply_flag_checklist(measurements: dict, est: dict, run: dict) -> dict:
    """Fold CLOSED checklist values into the derivation basis (live)."""
    if run.get("source") != "hover":
        return measurements
    m = measurements
    bb = (est.get("lp_flag_checklist") or {}).get("batten_wall_heights") or {}
    if bb.get("status") == "closed":
        heights = (bb.get("values") or {}).get("wall_heights_ft") or []
        try:
            total = float(sum(float(h) for h in heights))
        except (TypeError, ValueError):
            total = 0.0
        if total > 0:
            m = dict(m)
            m["_bb_wall_height_ft"] = total
    # CORNER-COUNT CORRECTION (ruled 2026-07-28): human-provenance walked
    # count GOVERNS the per-corner derivation (Q13); the report's count is
    # preserved on the line as the flagged comparison.
    cc = (est.get("lp_flag_checklist") or {}).get("corner_locators") or {}
    if cc.get("status") == "closed" and not m.get("_corner_count_human"):
        vals = cc.get("values") or {}
        for key, mk in (("outside_corner_count", "_osc_count_hover"),
                        ("inside_corner_count", "_isc_count_hover")):
            v = vals.get(key)
            if isinstance(v, (int, float)) and v > 0:
                if m is measurements:
                    m = dict(m)
                m[mk] = m.get(key)
                m[key] = int(v)
                m["_corner_count_human"] = True
        # TALL CORNERS (never-average rule sealed 2026-07-28): taped
        # heights for corners exceeding one 16' stick — per-corner
        # ceil(h/16), never averaged in.
        tall = vals.get("tall_corners_ft")
        if isinstance(tall, list) and tall:
            if m is measurements:
                m = dict(m)
            m["_osc_tall_corners_ft"] = [float(h) for h in tall]
    # CEILING DEDUP (class sealed 2026-07-28): a hand-entered ceiling and
    # a Hover soffit row never both compose for the same surface — TAPED
    # governs; the Hover-measured area is deducted as a named comparison.
    cd = (est.get("lp_flag_checklist") or {}).get("ceiling_dedup") or {}
    if cd.get("status") == "closed":
        dup = float((cd.get("values") or {}).get("duplicate_sqft") or 0)
        if dup > 0 and float(m.get("soffit_sqft") or 0) > 0:
            if m is measurements:
                m = dict(m)
            m["_soffit_sqft_hover"] = float(m["soffit_sqft"])
            m["soffit_sqft"] = max(float(m["soffit_sqft"]) - dup, 0.0)
            m["_soffit_dedup_sqft"] = dup
    # OPENING ATTRIBUTION (Class C sealed 2026-07-28): walked in-scope
    # counts GOVERN count-driven trim lines; Hover counts preserved.
    oa = (est.get("lp_flag_checklist") or {}).get("opening_facade_attribution") or {}
    if oa.get("status") == "closed":
        vals = oa.get("values") or {}
        for key in ("window_count", "entry_door_count", "patio_door_count",
                    "garage_door_count", "door_count"):
            v = vals.get(key)
            if isinstance(v, (int, float)) and v >= 0:
                if m is measurements:
                    m = dict(m)
                m[f"_{key}_hover"] = m.get(key)
                m[key] = int(v)
                m["_openings_attributed"] = True
    return m


_DOCTRINE_PAREN_RE = re.compile(r"\s*\([^()]*\b(?:sealed|ruled)\b[^()]*20\d\d-\d\d-\d\d[^()]*\)")


def _plain_label(text: str) -> str:
    """PLAIN TRADE LANGUAGE (Howard ruled 2026-07-29): stored flag labels
    written by older imports carry internal doctrine tags and, worse,
    OTHER customers' addresses. Sanitize at the serve-time choke point —
    new emitters already write plain wording."""
    s = str(text or "")
    s = _DOCTRINE_PAREN_RE.sub("", s)
    s = s.replace("OPENING↔FACADE ATTRIBUTION UNAVAILABLE: ",
                  "OPENINGS NOT TIED TO WALLS: ")
    s = s.replace(" — attribution is READ from the facade assignment, never "
                  "inferred from opening type/elevation/height;",
                  ".")
    s = s.replace("porch ceilings IMPLIED", "PORCH CEILINGS LIKELY")
    s = re.sub(r";?\s*261 Haugh[^.;)]*", "", s)
    s = re.sub(r",?\s*P3 precedent", "", s)
    s = s.replace("(stone/brick rule sealed)", "").replace("Class C ", "")
    return re.sub(r"\s{2,}", " ", s).strip()


def _checklist_flags(run: dict, est: dict) -> list:
    """Mapping-contract flags merged with checklist state — closed items
    retire from the amber list but stay visible (struck, by/at named)."""
    checklist = est.get("lp_flag_checklist") or {}
    out = []
    seen = set()
    for f in run.get("hover_mapping_flags") or []:
        item = dict(f) if isinstance(f, dict) else {"code": "", "label": str(f)}
        item["label"] = _plain_label(item.get("label"))
        if item.get("verify"):
            item["verify"] = _plain_label(item.get("verify"))
        entry = checklist.get(item.get("code")) or {}
        item["status"] = "closed" if entry.get("status") == "closed" else "open"
        if item["status"] == "closed":
            item["closed_by"] = entry.get("by")
            item["closed_at"] = entry.get("at")
            item["values"] = entry.get("values")
        out.append(item)
        seen.add(item.get("code"))
    # CEILING DEDUP (class sealed 2026-07-28): dynamic flag whenever a
    # hand-entered ceiling and a Hover-measured soffit total coexist —
    # the same square footage must never compose twice.
    _porch = est.get("porch_ceilings") or []
    _sof = float((((run.get("result") or {}).get("measurements")) or run.get("measurements") or {}).get("soffit_sqft") or 0)
    if _porch and _sof > 0 and "ceiling_dedup" not in seen:
        hand = sum(float(p.get("length_ft") or 0) * float(p.get("width_ft") or 0) for p in _porch)
        entry = checklist.get("ceiling_dedup") or {}
        item = {
            "code": "ceiling_dedup",
            "label": (f"CEILING DOUBLE-COUNT GUARD: hand-entered "
                      f"ceiling(s) {hand:g} ft² + Hover soffit total {_sof:g} ft² may cover the "
                      "same surface — TAPED governs; close with the Hover-measured duplicate area"),
            "verify": "Confirm whether a Hover soffit row is the same ceiling you hand-entered",
            "status": "closed" if entry.get("status") == "closed" else "open",
        }
        if item["status"] == "closed":
            item["closed_by"] = entry.get("by")
            item["closed_at"] = entry.get("at")
            item["values"] = entry.get("values")
        out.append(item)
    return out


@router.post("/estimates/{est_id}/flag-checklist")
async def flag_checklist_act(
    est_id: str, payload: dict, user: dict = Depends(get_current_user),
):
    """Close/reopen a mapping-contract flag with field-verified values."""
    code = (payload or {}).get("code")
    action = (payload or {}).get("action")
    values = (payload or {}).get("values") or {}
    if code not in _FLAG_CODES:
        raise HTTPException(status_code=422, detail=f"code must be one of {_FLAG_CODES}")
    if action not in ("close", "reopen"):
        raise HTTPException(status_code=422, detail="action must be close or reopen")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "lp_flag_checklist": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    if action == "close" and code == "batten_wall_heights":
        heights = values.get("wall_heights_ft")
        if (not isinstance(heights, list) or not heights
                or any(not isinstance(h, (int, float)) or h <= 0 for h in heights)):
            raise HTTPException(status_code=422,
                                detail="wall_heights_ft must be a non-empty list of positive numbers (taped per wall)")
    # CORNER-COUNT CORRECTION (ruled 2026-07-28, Casile re-book-check):
    # closing corner_locators may carry the HUMAN-provenance corner count
    # (walked on site); the report's count is preserved for comparison.
    if action == "close" and code == "corner_locators":
        for k in ("outside_corner_count", "inside_corner_count"):
            v = values.get(k)
            if v is not None and (not isinstance(v, (int, float)) or v <= 0 or int(v) != v):
                raise HTTPException(status_code=422,
                                    detail=f"{k} must be a positive whole number (walked count)")
        # TALL CORNERS (sealed 2026-07-28): heights only for corners
        # EXCEEDING one 16' stick (≤16' corners take exactly 1 by Q13).
        tall = values.get("tall_corners_ft")
        if tall is not None:
            if (not isinstance(tall, list) or not tall
                    or any(not isinstance(h, (int, float)) or not (16.0 < float(h) <= 60.0)
                           for h in tall)):
                raise HTTPException(status_code=422,
                                    detail="tall_corners_ft must list taped heights strictly over 16' "
                                           "(a corner at or under 16' takes exactly one stick — Q13)")
    if action == "close" and code == "ceiling_dedup":
        dup = values.get("duplicate_sqft")
        if not isinstance(dup, (int, float)) or dup <= 0:
            raise HTTPException(status_code=422,
                                detail="duplicate_sqft must be a positive number (the Hover-measured "
                                       "area of the same ceiling the hand entry covers)")
    if action == "close" and code == "opening_facade_attribution":
        ks = ("window_count", "entry_door_count", "patio_door_count", "garage_door_count", "door_count")
        if not any(values.get(k) is not None for k in ks):
            raise HTTPException(status_code=422,
                                detail=f"provide at least one in-scope count from {ks} (read from the "
                                       "facade assignment — never inferred)")
        for k in ks:
            v = values.get(k)
            if v is not None and (not isinstance(v, (int, float)) or v < 0 or int(v) != v):
                raise HTTPException(status_code=422, detail=f"{k} must be a whole number ≥ 0")
    prev = (est.get("lp_flag_checklist") or {}).get(code)
    now = datetime.now(timezone.utc).isoformat()
    entry = ({"status": "closed", "values": values, "by": user.get("email"), "at": now, "prev": prev}
             if action == "close"
             else {"status": "open", "by": user.get("email"), "at": now, "prev": prev})
    await db.estimates.update_one(
        {"id": est_id}, {"$set": {f"lp_flag_checklist.{code}": entry}})
    await log_estimate_event(est_id, f"lp.flag_checklist.{action}", {
        "code": code, "values": values if action == "close" else None, "by": user.get("email"),
    })
    return {"ok": True, "code": code, "entry": entry}


@router.post("/estimates/{est_id}/lp-package/compare")
async def lp_package_compare(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Compare-profiles toggle (approved 2026-07-16, ships under the
    geometry-source standing rule): derive the current composition AND a
    forced-profile alternative from ONE named geometry — same run, same
    engine, derived per request, never cached or persisted."""
    alt = str((payload or {}).get("alt_profile") or "board_batten")
    if alt not in _COMPARE_FAMILIES:
        raise HTTPException(status_code=422, detail=f"alt_profile must be one of {_COMPARE_FAMILIES}")
    est, run, binding = await _load_run(est_id, user["company_id"], (payload or {}).get("run_id"))
    measurements, corner_locations, wall_heights = _extract(run)
    measurements, _ = _apply_openings_review(
        measurements, _openings_items(run, est.get("lp_openings_review")))
    corners_eff = _apply_corner_review(corner_locations, est.get("lp_field_verify"))
    corners_eff = _apply_appendage_dims(corners_eff, est.get("lp_appendage_dims"))
    measurements = _apply_default_profile(measurements, est)
    measurements = _apply_key_bound_areas(measurements, est)
    measurements = _apply_contractor_waste(measurements, est)
    cfg = await load_margin_cfg()
    tier_sheet = await _load_tier_sheet_for(est)
    basis = _geometry_basis(est, run, binding)

    def _derive(m):
        pkg = assemble_lp_package(m, corners_eff, wall_heights,
                                  colors=(payload or {}).get("colors"))
        price_package(pkg, cfg, est.get("lp_pricing_tier"), tier_sheet=tier_sheet)
        pkg = redact_external(pkg)
        pkg["run_id"] = run.get("run_id")
        pkg["geometry_basis"] = basis
        return pkg

    return {
        "geometry_basis": basis,
        "alt_profile": alt,
        "current": _derive(measurements),
        "alternative": _derive(_force_profile_measurements(measurements, alt)),
    }


@router.post("/estimates/{est_id}/openings-review")
async def lp_openings_review_act(est_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Per-opening provenance: confirm (user_confirmed — promotes to
    verified standing), correct (user_corrected — corrected_type shifts
    derived counts), remove (user_removed — "not present": leaves counts,
    trim math, and quote surfaces; revertible), or reset. Skippable;
    unconfirmed flags persist."""
    key = str((payload or {}).get("key") or "").strip()
    action = (payload or {}).get("action")
    corrected_type = (payload or {}).get("corrected_type")
    if not key or "." in key or action not in ("confirm", "correct", "remove", "reset"):
        raise HTTPException(status_code=400, detail="key and action (confirm|correct|remove|reset) required")
    if action == "correct" and corrected_type not in _OPENING_TYPES:
        raise HTTPException(status_code=400, detail=f"corrected_type must be one of {_OPENING_TYPES}")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0, "id": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    from datetime import datetime, timezone
    from estimate_events import log_estimate_event
    # Journey-log ratify events (approved 2026-07-15): provenance already
    # logged per-opening, surfaced into the estimate's single event stream
    # alongside the customer-journey entries. Customer-invisibility pins
    # apply unchanged (tracking[] never renders on customer surfaces).
    if action == "reset":
        await db.estimates.update_one(
            {"id": est_id}, {"$unset": {f"lp_openings_review.{key}": ""}})
        await log_estimate_event(est_id, "opening.reset", meta={
            "key": key, "by": user.get("email") or user.get("id")})
        return {"ok": True, "key": key, "status": "unconfirmed"}
    entry = {
        "status": {"confirm": "user_confirmed", "correct": "user_corrected",
                   "remove": "user_removed"}[action],
        "at": datetime.now(timezone.utc).isoformat(),
        "by": user.get("email") or user.get("id"),
    }
    if action == "correct":
        entry["corrected_type"] = corrected_type
    await db.estimates.update_one(
        {"id": est_id}, {"$set": {f"lp_openings_review.{key}": entry}})
    ev_meta = {"key": key, "by": entry["by"]}
    if action == "correct":
        ev_meta["corrected_type"] = corrected_type
    await log_estimate_event(
        est_id,
        {"confirm": "opening.confirmed", "correct": "opening.corrected",
         "remove": "opening.removed"}[action],
        meta=ev_meta,
    )
    return {"ok": True, "key": key, **entry}


@router.get("/estimates/{est_id}/lp-appendage-dims")
async def lp_appendage_dims_get(est_id: str, user: dict = Depends(get_current_user)):
    """Current dimension entries + blueprint offers for the 3D appendage
    panel (offer-and-confirm only — never auto-applied)."""
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "id": 1, "lp_appendage_dims": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "dims": est.get("lp_appendage_dims") or {},
        "offers": await _blueprint_dim_offers(est_id),
    }


@router.post("/estimates/{est_id}/lp-appendage-dims")
async def lp_appendage_dims_set(est_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Appendage dimension editing (ruled 2026-07-15) — the render-only
    rule's second half. A user-entered value re-tags assumed →
    user_measured (by/at, revertible, journey-logged); a print-derived
    offer accepted by the user tags user_confirmed_from_blueprint.
    Assumed dims never enter math; tagged dims re-derive all surfaces."""
    key = str((payload or {}).get("key") or "").strip()
    field = (payload or {}).get("field")
    action = (payload or {}).get("action") or "set"
    if (not key.startswith("appendage:") or key.split(":", 1)[1] not in _WALLS
            or field not in _DIM_FIELDS or action not in ("set", "revert")):
        raise HTTPException(status_code=400, detail="key (appendage:<wall>), field (height_ft|depth_ft|door_offset_ft), action (set|revert) required")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0, "id": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    from datetime import datetime, timezone
    from estimate_events import log_estimate_event
    by = user.get("email") or user.get("id")
    if action == "revert":
        await db.estimates.update_one(
            {"id": est_id}, {"$unset": {f"lp_appendage_dims.{key}.{field}": ""}})
        await log_estimate_event(est_id, "appendage.reset", meta={"key": key, "field": field, "by": by})
        return {"ok": True, "key": key, "field": field, "status": "assumed"}
    try:
        value = float((payload or {}).get("value"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="value must be a number")
    if not (0.5 <= value <= 100.0):
        raise HTTPException(status_code=400, detail="value must be within 0.5..100 ft")
    source = (payload or {}).get("source") or "user"
    if source not in ("user", "blueprint", "photo"):
        raise HTTPException(status_code=400, detail="source must be user|blueprint|photo")
    entry = {
        "value": value,
        "status": ("photo_scaled" if source == "photo"
                   else "user_confirmed_from_blueprint" if source == "blueprint"
                   else "user_measured"),
        "at": datetime.now(timezone.utc).isoformat(),
        "by": by,
    }
    await db.estimates.update_one(
        {"id": est_id}, {"$set": {f"lp_appendage_dims.{key}.{field}": entry}})
    await log_estimate_event(est_id, "appendage.measured", meta={
        "key": key, "field": field, "value": value, "by": by, "source": source})
    return {"ok": True, "key": key, "field": field, **entry}


@router.post("/estimates/{est_id}/lp-field-verify")
async def lp_field_verify(est_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Amber corner verb set (ruled 2026-07-15): verified (ratification),
    relocated (wrong wall → correct wall, optional rough position),
    removed ("not present"), unverified (revert any). Relocation moves
    DETECTED features only — never invents geometry; dimensions remain
    run-measured. All verbs journey-logged with by/at provenance."""
    key = str((payload or {}).get("key") or "").strip()
    status = (payload or {}).get("status")
    if not key or "." in key or status not in ("verified", "unverified", "relocated", "removed"):
        raise HTTPException(status_code=400, detail="key and status (verified|unverified|relocated|removed) required")
    to_wall = str((payload or {}).get("to_wall") or "").strip().lower()
    if status == "relocated" and to_wall not in _WALLS:
        raise HTTPException(status_code=400, detail=f"to_wall must be one of {_WALLS}")
    position_frac = (payload or {}).get("position_frac")
    if position_frac is not None:
        try:
            position_frac = float(position_frac)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="position_frac must be a number")
        if not (0.0 <= position_frac <= 1.0):
            raise HTTPException(status_code=400, detail="position_frac must be within 0..1")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0, "id": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    from datetime import datetime, timezone
    from estimate_events import log_estimate_event
    by = user.get("email") or user.get("id")
    if status == "unverified":
        await db.estimates.update_one(
            {"id": est_id}, {"$unset": {f"lp_field_verify.{key}": ""}})
        await log_estimate_event(est_id, "corner.reset", meta={"key": key, "by": by})
        return {"ok": True, "key": key, "status": "unverified"}
    entry = {
        "status": {"verified": "verified", "relocated": "user_relocated",
                   "removed": "user_removed"}[status],
        "at": datetime.now(timezone.utc).isoformat(),
        "by": by,
    }
    if status == "relocated":
        entry["to"] = to_wall
        from_walls = (payload or {}).get("from_walls")
        if isinstance(from_walls, list):
            entry["from"] = [str(w).lower() for w in from_walls if str(w).lower() in _WALLS]
        if position_frac is not None:
            entry["position_frac"] = position_frac
    await db.estimates.update_one(
        {"id": est_id}, {"$set": {f"lp_field_verify.{key}": entry}})
    ev_meta = {"key": key, "by": by}
    if entry.get("from"):
        ev_meta["from"] = entry["from"]
    if entry.get("to"):
        ev_meta["to"] = entry["to"]
    await log_estimate_event(
        est_id,
        {"verified": "corner.verified", "relocated": "corner.relocated",
         "removed": "corner.removed"}[status],
        meta=ev_meta,
    )
    return {"ok": True, "key": key, **entry}


@router.post("/admin/estimates/{est_id}/lp-package/cost-preview")
async def lp_package_cost_preview(est_id: str, request: Request, payload: dict | None = None):
    """SUPPLIER-ADMIN ONLY (X-Admin-Token): the unredacted package with
    the confidential cost layer — dealer cost, margin, tier resolution.
    This payload must never be proxied to a contractor surface."""
    check_admin_token(request)
    est, run, binding = await _load_run(est_id, None, (payload or {}).get("run_id"))
    measurements, corner_locations, wall_heights = _extract(run)
    measurements, _ = _apply_openings_review(
        measurements, _openings_items(run, est.get("lp_openings_review")))
    corner_locations = _apply_corner_review(corner_locations, est.get("lp_field_verify"))
    corner_locations = _apply_appendage_dims(corner_locations, est.get("lp_appendage_dims"))
    measurements = _apply_key_bound_areas(measurements, est)
    measurements = _apply_contractor_waste(measurements, est)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, (payload or {}).get("tier") or est.get("lp_pricing_tier"), tier_sheet=await _load_tier_sheet_for(est))
    pkg["run_id"] = run.get("run_id")
    pkg["geometry_basis"] = _geometry_basis(est, run, binding)
    return pkg


def _pkg_content_hash(pkg: dict) -> str:
    """Canonical content hash for version comparison (frozen vs current)."""
    import hashlib
    import json as _json
    canon = {
        "lines": [[l.get("name"), l.get("qty"), l.get("unit"), l.get("color"),
                   l.get("unit_sell"), l.get("line_sell"), l.get("pricing_status")]
                  for l in pkg.get("lines") or []],
        "total_sell": (pkg.get("summary") or {}).get("pricing", {}).get("total_sell"),
    }
    return hashlib.sha256(_json.dumps(canon, sort_keys=True).encode()).hexdigest()


async def _derive_current(est_id: str, company_id=None):
    est, run, binding = await _load_run(est_id, company_id)
    measurements, corner_locations, wall_heights = _extract(run)
    # openings corrections apply on EVERY derivation surface (coherence);
    # the review payload itself is contractor-only and never attaches here.
    measurements, _ = _apply_openings_review(
        measurements, _openings_items(run, est.get("lp_openings_review")))
    corner_locations = _apply_corner_review(corner_locations, est.get("lp_field_verify"))
    corner_locations = _apply_appendage_dims(corner_locations, est.get("lp_appendage_dims"))
    corner_locations = _apply_appendage_dims(corner_locations, est.get("lp_appendage_dims"))
    measurements = _apply_default_profile(measurements, est)
    measurements = _apply_flag_checklist(measurements, est, run)
    measurements = _apply_key_bound_areas(measurements, est)
    measurements = _apply_contractor_waste(measurements, est)
    full_est = await db.estimates.find_one(
        {"id": est_id}, {"_id": 0, "lp_colors": 1, "lp_pricing_tier": 1,
                         "estimate_number": 1, "customer_name": 1,
                         "address": 1, "estimate_date": 1})
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              colors=(full_est or {}).get("lp_colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"), tier_sheet=await _load_tier_sheet_for(est))
    pkg = redact_external(pkg)
    pkg["run_id"] = run.get("run_id")
    pkg["geometry_basis"] = _geometry_basis(est, run, binding)
    return pkg, (full_est or {})


@router.post("/estimates/{est_id}/lp-material-list/freeze")
async def lp_material_list_freeze(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Iter 100 — QR share (ruled, document doctrine): freeze the EXACT
    printed composition (colors + session substitutions) server-side and
    mint a tokenized, contractor-redacted, expiring read-only link. The
    link always resolves to THIS frozen version; the public view banners
    when a newer derivation exists — never a silent live view."""
    import secrets
    from datetime import datetime, timedelta, timezone

    est, run, binding = await _load_run(est_id, user["company_id"], (payload or {}).get("run_id"))
    # TEST-ESTIMATE DOCTRINE (sealed 2026-07-28): TEST_ estimates never
    # mint QR shares — evidence for a run only, never a customer surface.
    if str(est.get("customer_name") or "").startswith("TEST_"):
        raise HTTPException(status_code=409,
                            detail="TEST_ estimate — QR minting refused (test-estimate doctrine sealed 2026-07-28)")
    # QUOTE GATE (ruled 2026-07-29): the frozen QR list is a customer
    # surface — blocked while any quote-tier blocker stands.
    await assert_quote_gate(est_id, user)
    measurements, corner_locations, wall_heights = _extract(run)
    # openings + corner reviews apply on EVERY derivation surface
    # (coherence) — the frozen snapshot must match what the panel showed.
    measurements, _ = _apply_openings_review(
        measurements, _openings_items(run, est.get("lp_openings_review")))
    corner_locations = _apply_corner_review(corner_locations, est.get("lp_field_verify"))
    corner_locations = _apply_appendage_dims(corner_locations, est.get("lp_appendage_dims"))
    measurements = _apply_default_profile(measurements, est)
    measurements = _apply_flag_checklist(measurements, est, run)
    measurements = _apply_key_bound_areas(measurements, est)
    measurements = _apply_contractor_waste(measurements, est)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"), tier_sheet=await _load_tier_sheet_for(est))
    pkg = redact_external(pkg)  # frozen snapshot is ALWAYS the redacted view
    pkg["run_id"] = run.get("run_id")
    pkg["geometry_basis"] = _geometry_basis(est, run, binding)
    meta = await db.estimates.find_one(
        {"id": est_id}, {"_id": 0, "estimate_number": 1, "customer_name": 1,
                         "address": 1, "estimate_date": 1})
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(24)
    await db.lp_material_list_snapshots.insert_one({
        "token": token, "estimate_id": est_id, "company_id": user["company_id"],
        "snapshot": pkg, "meta": meta or {},
        "content_hash": _pkg_content_hash(pkg),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=90)).isoformat(),
        "revoked": False,
    })
    # Ruled 2026-07-14 — the frozen /m/ artifact embeds THIS run's package:
    # archive the exact run beyond the 30-day TTL.
    await archive_run_for_artifact(
        estimate_id=est_id, run_id=run.get("run_id"), reason="m-freeze")
    return {"token": token, "share_path": f"/m/{token}",
            "expires_at": (now + timedelta(days=90)).isoformat()}


@router.get("/public/lp-material-list/{token}")
async def lp_material_list_public(token: str):
    """Public, read-only, redacted. Frozen version + newer-available flag."""
    from datetime import datetime, timezone

    snap = await db.lp_material_list_snapshots.find_one({"token": token}, {"_id": 0})
    if not snap or snap.get("revoked"):
        raise HTTPException(status_code=404, detail="Link not found or revoked")
    # Split ruling 2026-07-14 — QR scan logged (expired scans included:
    # callback intel). Response never reveals tracking exists.
    expired = bool(snap.get("expires_at") and snap["expires_at"] < datetime.now(timezone.utc).isoformat())
    await log_estimate_event(
        snap.get("estimate_id"), "qr.scanned",
        {"surface": "material_list", "token": token[:8], **({"expired": True} if expired else {})})
    if expired:
        raise HTTPException(status_code=410, detail="Link expired")
    newer_available = False
    current = None
    try:
        current, _meta = await _derive_current(snap["estimate_id"])
        newer_available = _pkg_content_hash(current) != snap.get("content_hash")
    except HTTPException:
        current = None
    return {
        # Legacy snapshots were frozen WITH prices — ONE MONEY SURFACE
        # (ruled 2026-07-23) de-prices them at read time.
        "frozen": redact_external(snap["snapshot"]), "meta": snap.get("meta") or {},
        "printed_at": snap.get("created_at"),
        "newer_available": newer_available,
        "current": current if newer_available else None,
    }


@router.post("/public/lp-material-list/{token}/request-update")
async def lp_material_list_request_update(token: str, request: Request):
    """Ruled scope: notifies the estimate's OWNER (the contractor) only,
    with version context attached — no other recipients, no marketing."""
    import asyncio
    from datetime import datetime, timezone

    from config import RESEND_API_KEY, SENDER_EMAIL

    snap = await db.lp_material_list_snapshots.find_one({"token": token}, {"_id": 0})
    if not snap or snap.get("revoked"):
        raise HTTPException(status_code=404, detail="Link not found or revoked")
    now = datetime.now(timezone.utc)
    last = snap.get("last_update_request_at")
    if last and (now - datetime.fromisoformat(last)).total_seconds() < 900:
        return {"ok": True, "throttled": True}
    if not RESEND_API_KEY:
        raise HTTPException(status_code=503, detail="Email is not configured")

    owner = await db.users.find_one(
        {"company_id": snap["company_id"], "role": "owner"},
        {"_id": 0, "email": 1, "name": 1})
    if not owner or not owner.get("email"):
        raise HTTPException(status_code=404, detail="Contractor contact not found")

    newer_available = False
    try:
        current, _m = await _derive_current(snap["estimate_id"])
        newer_available = _pkg_content_hash(current) != snap.get("content_hash")
    except HTTPException:
        pass

    meta = snap.get("meta") or {}
    est_num = meta.get("estimate_number") or "(no number)"
    printed = str(snap.get("created_at") or "")[:10]
    version_line = (
        "The estimate HAS CHANGED since this list was printed — the frozen printout is outdated."
        if newer_available else
        "The frozen printout still matches the current derivation — no drift detected."
    )
    origin = f"{request.url.scheme}://{request.url.netloc}"
    html = f"""<!doctype html>
<html><body style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#09090B;background:#F4F4F5;margin:0;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#FFFFFF;border:1px solid #09090B;padding:32px;">
    <div style="font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#F97316;margin-bottom:8px;">Material List — Update Requested</div>
    <h1 style="font-size:22px;margin:0 0 16px 0;color:#09090B;">Updated list requested for {est_num}</h1>
    <p style="font-size:15px;color:#52525B;line-height:1.6;">
      Someone viewing the printed material list (QR link) asked for the latest version.<br><br>
      <b style="color:#09090B;">Estimate:</b> {est_num} — {meta.get('customer_name') or ''}<br>
      <b style="color:#09090B;">Printed version:</b> {printed}<br>
      <b style="color:#09090B;">Version status:</b> {version_line}
    </p>
    <p style="font-size:14px;color:#52525B;">Open the estimate and print a fresh material list to issue a new frozen link:<br>
      <a href="{origin}/estimate/{snap['estimate_id']}" style="color:#C2410C;">{origin}/estimate/{snap['estimate_id']}</a></p>
  </div>
</body></html>"""
    import resend
    resend.api_key = RESEND_API_KEY
    await asyncio.to_thread(resend.Emails.send, {
        "from": SENDER_EMAIL,
        "to": [owner["email"]],
        "subject": f"Updated material list requested — {est_num}",
        "html": html,
    })
    await db.lp_material_list_snapshots.update_one(
        {"token": token}, {"$set": {"last_update_request_at": now.isoformat()}})
    return {"ok": True, "newer_available": newer_available}


@router.post("/estimates/{est_id}/lp-material-list/revoke")
async def lp_material_list_revoke(
    est_id: str, payload: dict, user: dict = Depends(get_current_user),
):
    token = str(payload.get("token") or "")
    res = await db.lp_material_list_snapshots.update_one(
        {"token": token, "estimate_id": est_id, "company_id": user["company_id"]},
        {"$set": {"revoked": True}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"revoked": True}


@router.post("/estimates/{est_id}/lp-package/truck-reconcile")
async def lp_truck_reconcile_endpoint(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Letrick truck-list acceptance harness — derives each delivered
    line from the conventions layer + validated geometry, deviations
    itemized per line with cause. Runs BEFORE the ±3% acceptance test."""
    _est, run, binding = await _load_run(est_id, user["company_id"], (payload or {}).get("run_id"))
    measurements, corner_locations, _ = _extract(run)
    raw_ai = (run.get("result") or {}).get("raw_ai") or {}
    window_widths = [float(o.get("width_in") or 0) / 12.0
                     for o in raw_ai.get("openings") or []
                     if str(o.get("type")) == "window" and o.get("width_in")]
    out = reconcile_letrick_truck(measurements, corner_locations, window_widths)
    out["run_id"] = run.get("run_id")
    out["geometry_basis"] = _geometry_basis(_est, run, binding)
    return out
