"""Iter 79j.93 — LP package preview endpoint (September package assembly, Phase 1).
Iter 79j.94 — truck-list reconciliation endpoint (pre-±3% acceptance harness).
Iter 79j.96 — confidential cost layer + tiered sell pricing. Contractor-facing
preview is ALWAYS redacted (sell only); the unredacted cost view exists only
behind the supplier-admin token."""
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
        q_est, {"_id": 0, "id": 1, "estimate_number": 1, "lp_pricing_tier": 1, "lp_field_verify": 1,
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

_DIM_FIELDS = ("height_ft", "depth_ft", "door_offset_ft")

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


def _apply_chase_ratification(measurements, est):
    """ITEM-3 RATIFIED (Howard, ruled 2026-07-19) — area gate OPEN for
    this ratification only (journey-logged): the TAPED chase faces
    supersede the AI-attributed appendage area in siding_sqft (a SWAP —
    same physical surface, better basis, no double count). Gated to the
    sealed-key estimate + machinery-entered dims; every other estimate's
    area story is untouched until its own ratification lands."""
    if est.get("estimate_number") != "EST-373526":
        return measurements
    dims = (est.get("lp_appendage_dims") or {}).get("appendage:back") or {}
    h = dims.get("height_ft") or {}
    d = dims.get("depth_ft") or {}
    if h.get("status") not in _DIM_STATUSES or d.get("status") not in _DIM_STATUSES:
        return measurements
    if not ((h.get("value") or 0) > 0 and (d.get("value") or 0) > 0):
        return measurements
    from letrick_hand_takeoff_key import LETRICK_HAND_TAKEOFF_KEY as KEY
    from routes.demo import LETRICK_TAPE_WALLS  # constant import only
    if "chase_width_in" not in KEY["inputs"]:
        return measurements
    from lp_package import chase_face_sqft
    wall_h = float(LETRICK_TAPE_WALLS["back"]["segments"][0]["height_ft"])
    faces = chase_face_sqft(float(KEY["inputs"]["chase_width_in"]) / 12.0,
                            float(d["value"]), float(h["value"]), wall_h)
    ai_sqft = float(measurements.get("_ai_appendage_sqft") or 0)
    delta = faces["total_sqft"] - ai_sqft
    new_sqft = round(float(measurements.get("siding_sqft") or 0) + delta, 1)
    swo = measurements.get("siding_with_openings_sqft")
    return {**measurements, "siding_sqft": new_sqft,
            **({"siding_with_openings_sqft": round(float(swo) + delta, 1)}
               if swo is not None else {}),
            "_chase_face_ratification": {
                "ai_sqft": ai_sqft, **faces,
                "delta_sqft": round(delta, 2),
                "siding_sqft_effective": new_sqft,
                "ruled": ("item-3 ratified 2026-07-19 — TAPED faces supersede "
                          "AI attribution (swap); gate open for this ratification only")}}


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
    measurements = _apply_chase_ratification(measurements, est)
    pkg = assemble_lp_package(measurements, corners_eff, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"))
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
      • waste — ruled 10% default / explicit override, never silently 0%
    """
    passthrough = (
        "siding_sqft", "siding_with_openings_sqft",
        "outside_corner_count", "outside_corner_lf",
        "inside_corner_count", "inside_corner_lf",
        "eaves_lf", "rakes_lf", "starter_lf",
        "window_count", "entry_door_count", "patio_door_count",
        "garage_door_count", "door_count", "opening_perimeter_lf",
        "stories", "overhang_in",
    )
    m = {k: hover_meas[k] for k in passthrough if k in hover_meas}
    m["_hover_source"] = True
    m["_waste_pct"] = 0.10 if waste_pct is None else float(waste_pct)
    # WRAP-DEFAULT enforcement (ruled 2026-07-18): when the report carries
    # a facade_breakdown and no explicit scope was chosen, only the Siding
    # row composes — other materials are named + excluded, never silently
    # summed. Explicit facade_scope (the picker) always overrides.
    fb = hover_meas.get("facade_breakdown") or {}
    if not facade_scope and isinstance(fb, dict):
        sid = float(fb.get("siding_sqft") or 0)
        others = {k[:-5]: float(v) for k, v in fb.items()
                  if k != "siding_sqft" and k.endswith("_sqft")
                  and isinstance(v, (int, float)) and v > 0}
        if sid > 0 and others:
            facade_scope = {"mode": "wrap_only", "wrap_sqft": sid,
                            "excluded": others}
    if facade_scope and (facade_scope.get("wrap_sqft") or 0) > 0:
        measured_total = float(hover_meas.get("siding_sqft") or 0)
        wrap = float(facade_scope["wrap_sqft"])
        m["siding_sqft"] = wrap
        m["_facade_scope"] = {
            "mode": facade_scope.get("mode") or "wrap_only",
            "wrap_sqft": wrap,
            "measured_total": measured_total,
            "excluded": facade_scope.get("excluded") or {},
        }
    if soffit_breakdown:
        eaves = float(soffit_breakdown.get("eaves_sqft") or 0)
        rakes = float(soffit_breakdown.get("rakes_sqft") or 0)
        ceilings = float(soffit_breakdown.get("ceilings_sqft") or 0)
        if eaves + rakes + ceilings > 0:
            m["_soffit_vented_sqft"] = eaves
            m["_soffit_closed_sqft"] = rakes + ceilings
            m["_soffit_ceiling_sqft"] = ceilings
    m = _force_profile_measurements(m, profile)
    flags = [{
        "code": "corner_locators",
        "label": "corner sticks on measured corner-LF basis (Hover has counts/LF, no per-corner locators)",
        "verify": "Walk the corners on site — confirm OSC/ISC counts match the report",
    }]
    fs = m.get("_facade_scope")
    if fs and fs.get("excluded"):
        excl = ", ".join(f"{k} {v:g} ft²" for k, v in fs["excluded"].items())
        flags.append({
            "code": "facade_scope",
            "label": (f"facade scope {fs['mode']}: {fs['wrap_sqft']:g} ft² composes; "
                      f"excluded: {excl} (never silently summed)"),
            "verify": "Confirm the excluded facade materials stay out of the siding scope — re-import with them included if the job wraps them",
        })
    if profile in ("board_batten", "vertical"):
        flags.append({
            "code": "batten_wall_heights",
            "label": "batten +height term = 0 (Hover carries no per-wall heights) — PENDING field verify",
            "verify": "Tape each wall height — closing re-derives batten LF live (+1 run × height per wall)",
        })
    flags.append({
        "code": "opening_schedule",
        "label": "opening schedule not itemized (Hover counts only) — starter deduction + wrap use per-count constants",
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
    await db.estimates.update_one(
        {"id": est_id}, {"$set": {"default_siding_profile": profile,
                                  "default_siding_profile_change": change}})
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
_FLAG_CODES = ("corner_locators", "batten_wall_heights", "opening_schedule")


def _apply_flag_checklist(measurements: dict, est: dict, run: dict) -> dict:
    """Fold CLOSED checklist values into the derivation basis (live)."""
    if run.get("source") != "hover":
        return measurements
    bb = (est.get("lp_flag_checklist") or {}).get("batten_wall_heights") or {}
    if bb.get("status") == "closed":
        heights = (bb.get("values") or {}).get("wall_heights_ft") or []
        try:
            total = float(sum(float(h) for h in heights))
        except (TypeError, ValueError):
            total = 0.0
        if total > 0:
            m = dict(measurements)
            m["_bb_wall_height_ft"] = total
            return m
    return measurements


def _checklist_flags(run: dict, est: dict) -> list:
    """Mapping-contract flags merged with checklist state — closed items
    retire from the amber list but stay visible (struck, by/at named)."""
    checklist = est.get("lp_flag_checklist") or {}
    out = []
    for f in run.get("hover_mapping_flags") or []:
        item = dict(f) if isinstance(f, dict) else {"code": "", "label": str(f)}
        entry = checklist.get(item.get("code")) or {}
        item["status"] = "closed" if entry.get("status") == "closed" else "open"
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
    measurements = _apply_chase_ratification(measurements, est)
    cfg = await load_margin_cfg()
    basis = _geometry_basis(est, run, binding)

    def _derive(m):
        pkg = assemble_lp_package(m, corners_eff, wall_heights,
                                  colors=(payload or {}).get("colors"))
        price_package(pkg, cfg, est.get("lp_pricing_tier"))
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
    measurements = _apply_chase_ratification(measurements, est)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, (payload or {}).get("tier") or est.get("lp_pricing_tier"))
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
    measurements = _apply_chase_ratification(measurements, est)
    full_est = await db.estimates.find_one(
        {"id": est_id}, {"_id": 0, "lp_colors": 1, "lp_pricing_tier": 1,
                         "estimate_number": 1, "customer_name": 1,
                         "address": 1, "estimate_date": 1})
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              colors=(full_est or {}).get("lp_colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"))
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
    measurements, corner_locations, wall_heights = _extract(run)
    # openings + corner reviews apply on EVERY derivation surface
    # (coherence) — the frozen snapshot must match what the panel showed.
    measurements, _ = _apply_openings_review(
        measurements, _openings_items(run, est.get("lp_openings_review")))
    corner_locations = _apply_corner_review(corner_locations, est.get("lp_field_verify"))
    corner_locations = _apply_appendage_dims(corner_locations, est.get("lp_appendage_dims"))
    measurements = _apply_default_profile(measurements, est)
    measurements = _apply_flag_checklist(measurements, est, run)
    measurements = _apply_chase_ratification(measurements, est)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"))
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
        "frozen": snap["snapshot"], "meta": snap.get("meta") or {},
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
