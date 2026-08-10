"""SEAM ACCOUNTING (Howard ruled 2026-08-09): any layer that filters,
splits, projects, whitelists, or truncates data MUST account for what it
removed. A removal with no accounting is the recurring failure class —
the qty-0 filter that dropped rows, the 'es: {' splitter that truncated
a dictionary — silent, green, wrong. The ledger names every seam and
every removal; the detector test fails the build when a new filtering
seam appears without registration."""
from __future__ import annotations

SEAM_REGISTRY = {
    "interior_doors_dropped":
        "Doors with exterior_evidence 'none' kept OFF the exterior count.",
    "dims_nulled_no_evidence":
        "Dims that arrived without a quoted printed string — nulled by "
        "construction (evidence-or-null).",
    "count_column_governed":
        "Carried qtys replaced by the printed COUNT column's own sum "
        "(the count column governs counts).",
    "count_cells_unread":
        "Marks the schedule prints no COUNT cell for — contribute "
        "nothing, flagged, never estimated.",
    "mark_rows_merged":
        "Per-sheet schedule rows for the same mark merged into one "
        "(counts summed across sheets — a per-sheet row is not a "
        "distinct mark).",
    "marks_dropped_not_located":
        "Schedule rows none of whose quotes (mark, printed size, "
        "product code) locate on their sheets under OCR — fabricated, "
        "dropped.",
    "mark_size_quotes_nulled":
        "Printed-size quotes OCR cannot find on the row's sheets — the "
        "quote is killed, its parse never reaches the takeoff.",
    "lp_smart_lines_cut":
        "Engine-owned lp_smart rows cut from blueprint results (THE CUT, "
        "ruled 2026-07-14) — LP derives through assemble_lp_package.",
    "interior_signal_dropped":
        "Door rows whose schedule line MACHINE-reads an interior product "
        "marker (HOLLOW CORE / H DWL CORE / Garage to House) — dropped "
        "regardless of the model's own exterior label (ruled 2026-08-09).",
    "client_build_stale":
        "A loaded page older than the deployed build — a surface that "
        "silently disagrees with its own backend. Detected client-side "
        "against GET /api/version; the banner reports the client/server "
        "version pair and prompts a refresh (ruled 2026-08-09 after the "
        "stale-page false data-loss report).",
    "roof_pass_overwrite":
        "The conditional second AI read (roof pass) overwrote geometry "
        "on the primary read — pitch or (with an agreed walk) corner "
        "heights. Every overwrite names old→new; an EVIDENCED value is "
        "NEVER replaced by an unevidenced one (ruled 2026-08-09 send 7); "
        "a disagreeing corner walk KEEPS THE PRIMARY and flags "
        "corner_walk_conflict with both numbers (ruled 2026-08-10 — "
        "max-wins acceptance is dead).",
    "pages_truncated":
        "Plan-set pages beyond the read cap were never rendered or read "
        "— invisible to the model, the locator, and every census. The "
        "removal is counted and flagged LOUD on the card (ruled "
        "2026-08-09 send 7: 'this plan set has N pages, the app read M').",
}


def account(carrier: dict, seam: str, removed, kept=None) -> dict:
    """Record a removal against a REGISTERED seam. carrier is any dict
    that persists (raw_ai, measurements); the ledger rides it as
    _seam_ledger. An unregistered seam raises — register it or don't
    remove data."""
    if seam not in SEAM_REGISTRY:
        raise KeyError(
            f"unregistered seam '{seam}' — register it in "
            f"seam_accounting.SEAM_REGISTRY before removing data")
    led = carrier.setdefault("_seam_ledger", {})
    entry = led.setdefault(seam, {"removed": 0, "items": []})
    items = list(removed) if isinstance(removed, (list, tuple)) else [removed]
    entry["removed"] += len(items)
    entry["items"] = (entry["items"] + [str(i) for i in items])[:40]
    if kept is not None:
        entry["kept"] = kept
    return carrier
