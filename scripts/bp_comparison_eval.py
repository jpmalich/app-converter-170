import json, glob, statistics

KEY = {"siding": 2098.5, "chase": 145.5, "osc": 4, "windows": 10}

for f in sorted(glob.glob("/app/memory/bp_comparison_runs/run*.json")):
    d = json.load(open(f))
    m = d["measurements"]; raw = d["raw_ai"]
    walls = {str(w.get("label","?")).lower(): w for w in (raw.get("walls") or [])}
    anchors = {k: (w.get("width_ft"), w.get("height_ft"), w.get("gable_triangle_height_ft")) for k, w in walls.items()}
    chase = sum(float(a.get("faces_sqft") or 0) for a in (raw.get("appendages") or []))
    ap_kinds = [(a.get("wall"), a.get("kind"), a.get("width_ft"), a.get("depth_ft"), a.get("height_ft"), a.get("faces_sqft"), a.get("extends_above_roofline")) for a in (raw.get("appendages") or [])]
    doors = [(x.get("id"), x.get("type_hint"), x.get("qty"), x.get("width_in"), x.get("height_in"), x.get("elevation")) for x in (raw.get("doors") or [])]
    wins = [(x.get("id"), x.get("qty"), x.get("elevation")) for x in (raw.get("windows") or [])]
    gpp = m.get("_gable_pitch_provenance")
    print("="*30, d["tag"], d["model"])
    print(" wall_s=%ss cost=$%s tokens=%s" % (d["wall_clock_s"], d["cost_usd"], d["token_usage"]))
    print(" siding=%s (key 2098.5, %+.1f%%)" % (m["siding_sqft"], 100*(m["siding_sqft"]-KEY["siding"])/KEY["siding"]))
    print(" chase_faces=%s (key 145.5, %+.1f%%)" % (chase, 100*(chase-KEY["chase"])/KEY["chase"] if chase else -100))
    print(" appendages:", ap_kinds)
    print(" osc=%s isc=%s (key 4 / 2)" % (m.get("outside_corner_count"), m.get("inside_corner_count")))
    print(" windows=%s (key 10) placement_defaulted=%s" % (m.get("window_count"), m.get("_opening_placement_defaulted")))
    print(" win rows:", wins)
    print(" doors: entry=%s patio=%s garage=%s" % (m.get("entry_door_count"), m.get("patio_door_count"), m.get("garage_door_count")))
    print(" door rows:", doors)
    print(" pitch=%r starter=%s basis=%r" % (raw.get("roof_pitch"), m.get("starter_lf"), m.get("_starter_basis")))
    print(" gable_prov:", gpp)
    print(" anchors:", anchors)
    print(" recon_warn:", m.get("_source_reconciliation_warning"))
    print(" notes:", (m.get("_ai_notes") or "")[:200])
