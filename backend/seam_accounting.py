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
    "wall_area_not_derivable":
        "A wall whose width was killed or never read has UNKNOWN body "
        "area, never a silent 0 that shrinks the house. The money walk "
        "sums only the derivable faces and NAMES the missing one here — "
        "a total assembled from a subset of walls says which face it "
        "lost (Howard ruled 2026-08-14: unreadable width is unknown, "
        "not zero; a derived value dies with its source).",
    "dims_nulled_no_evidence":
        "Dims that arrived without a quoted printed string — nulled by "
        "construction (evidence-or-null).",
    "dims_nulled_quote_unverified":
        "Dims whose quoted printed string could NOT be located near the "
        "feature it claimed to dimension — the string MAY be real but "
        "we could not confirm it near its feature. The value nulls on "
        "the raw so it does not feed money, but `_dim_unverified` "
        "carries value+quote+reason so the card shows the number "
        "MARKED unverified (ruled 2026-08-12 send-9 item 3).",
    "dims_nulled_quote_fabricated":
        "Dims whose quoted printed string does NOT appear on the "
        "page's pixels in any orientation — the quote was fabricated. "
        "The value nulls and `_dim_fabricated` carries the killed "
        "value+quote+reason for the card (ruled 2026-08-12 send-9 "
        "item 3: fabricated is a different lie from unverified).",
    "dims_demoted_quote_shared":
        "RETIRED (Howard ruled 2026-08-14 send-13): shared-source is now "
        "a LOUD FLAG, not a kill — the value survives and feeds money, "
        "the sharing rides `_dim_shared_source` (attribution unverified, "
        "conflicting cases flagged louder). This seam no longer fires; "
        "demote-all destroyed legitimately-shared printed dims (58'-0\" "
        "genuinely IS both front and back width) and never caught a real "
        "defect — the fabricated 39s die at EXISTENCE, not here. Kept "
        "registered so any stray firing still names its layer.",
    "dims_misread":
        "Dims whose quoted printed string does NOT appear on the page's "
        "pixels in any orientation, BUT a real OCR run on that page "
        "sits within ONE character-edit of the quote — the class where "
        "the AI transcribed 33'-5 1/2\" as 32'-5 1/2\". Ruled 2026-08-13 "
        "send-11 item 2: a misread is diagnostically distinct from a "
        "fabrication (typo vs invention) even though both kill the "
        "value for money. `_dim_misread` carries value+quote+"
        "misread_of+reason so the card names the real printed string.",
    "pdf_overlay_polygon_write":
        "A pdf_overlay_polygons collection write (upsert/delete) on "
        "any estimate. Ruled 2026-08-13 pro-quotes reply 5: a drawn "
        "or adjusted zone is HUMAN ENTRY — it stamps qty_src=human "
        "on the affected takeoff line and rides above the untouchable "
        "freeze on EST-886440 (built in at MUV birth, not discovered "
        "on the walk). Every write on a protected estimate lands in "
        "protected_estimate_ledger via ledger_human_write. MUV walk-"
        "bar item 5+6 (marked as MY entry, still there after a "
        "rebuild) is delivered by the existing hover.py qty_src=='human' "
        "shield — no new instrument needed for rebuild survival.",
    "protected_ledger_paginated":
        "The /api/estimates/{eid}/protected-ledger endpoint's response "
        "returned fewer entries than the ledger holds. Ruled 2026-08-13 "
        "send-11 item 1 correction: the previous shape read with a "
        "hardcoded .limit(200) and returned ONLY `entries` — the moment "
        "the live ledger grew past 200 it silently dropped the 201st "
        "entry onward, INSIDE the instrument built to make every human "
        "write to a sealed estimate visible. Per the seam rule, any "
        "layer that truncates accounts for what it removed: `total` is "
        "the honest count, `truncated` flips true, `truncation_notice` "
        "says plainly 'showing N of M', pagination via ?page= and "
        "?page_size= (hard cap 1000). The .limit() shape is now a "
        "REPORTED truncation, never a silent one.",
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
    "mark_count_cells_nulled":
        "COUNT-CELL claims OCR cannot find as an isolated integer "
        "token in the mark's row-band on the claimed page — the claim "
        "is preserved in count_by_page_not_located, the working count "
        "is nulled, and qty follows the surviving pages. Same "
        "instrument as mark_size_quotes_nulled, one field over: settles "
        "count disagreements by the print instead of by the pixels "
        "(ruled 2026-08-11 send-3 item d).",
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
    "ttl_reaper":
        "mongod's TTL monitor destroys expired docs with NO code "
        "executing — the removal no AST detector can see (TTL incident "
        "#3, the EST-886440 grading chain). Every live expiring index is "
        "named in TTL_REAPER_REGISTRY; the live-DB census "
        "(tests/test_ttl_index_census.py) fails the build on an "
        "unregistered one. Defusals: archive-on-view, protected-estimate "
        "auto-archive, artifact events, dead-worker boot sweep, boot "
        "backfill (ruled 2026-08-11).",
    "vero_obsolete_boot_purge":
        "Boot-time delete_many of retired Vero products/tiers before the "
        "canonical force-reseed (Iter 78y) — ruled and harmless, but a "
        "per-boot removal, and a ledger with a known hole teaches the "
        "wrong habit (ruled 2026-08-11).",
}


# ── THE REAPER IN THE LEDGER, CLASS-WIDE (ruled 2026-08-11) ──────────
# A TTL index removes data with no code executing, so the AST seam
# detector is structurally blind to it. This registry is the mirror
# instrument on the other substrate: every LIVE index carrying
# expireAfterSeconds must appear here, and tests/test_ttl_index_census.py
# walks the LIVE database (never this file alone) — failing the build on
# any unregistered expiring index, any registry entry missing live, any
# window mismatch, and any capped collection (silent oldest-doc eviction).
TTL_REAPER_REGISTRY = {
    ("ai_blueprint_runs", "created_at_1"): {
        "expire_seconds": 30 * 24 * 60 * 60,
        "why": "blueprint reads — raised 24h→30d 2026-08-11 (incident #3); "
               "defused by archive-on-view / protected auto-archive / "
               "artifact events / dead-worker boot sweep",
    },
    ("ai_measure_runs", "created_at_1"): {
        "expire_seconds": 30 * 24 * 60 * 60,
        "why": "photo reads — 30d since Iter 79j.62 (Red-House graduation "
               "run reaped at 24h); same defusals as blueprint",
    },
    ("hover_import_runs", "created_at_1"): {
        "expire_seconds": 24 * 60 * 60,
        "why": "hover imports — 24h, SHORTEST FUSE in the DB (audit A3, "
               "same anti-pattern as the incident); defused by "
               "archive-on-view / protected auto-archive / "
               "hover-lp-materialize (2nd-instance pin 2026-07-18)",
    },
    ("estimates_trash", "deleted_at_1"): {
        "expire_seconds": 30 * 24 * 60 * 60,
        "why": "ruled soft-delete retention (Iter 112) — 30-day undo "
               "window, then the reaper empties the trash",
    },
}

# Collections that must NEVER carry an expiring index or capped option.
# hover_page_cache is the audit-A5 trap: its 1h TTL index outlived the
# retired code by two weeks in the LIVE database — dropped 2026-08-11,
# pinned to stay gone.
TTL_FORBIDDEN = ("estimates", "fixture_runs", "upload_blobs", "hover_page_cache")


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
