"""LP DOMAIN MANIFEST (approved 2026-07-13) — machine-readable fork
boundary for the white-label extraction. Enforced continuously by
tests/test_fork_boundary.py (CI drift check): the build FAILS on
cross-domain imports into the LP core or untagged LP data — forkability
stays continuously true, not audit-day true.
Audit of record: /app/memory/forkability_audit_2026-07-13.md
"""

# Pure domain core — may import ONLY stdlib + each other.
LP_CORE_MODULES = [
    "lp_conventions.py",
    "lp_package.py",
    "lp_costs.py",
    "lp_colors.py",
    "lp_smartside_formulas.py",
    "lp_truck_reconcile.py",
    "lp_expertfinish_matrix.py",
    "letrick_hand_takeoff_key.py",
]

# LP HTTP adapter layer — may import app infrastructure (db/deps/config).
LP_ROUTERS = [
    "routes/lp_package_routes.py",
    "routes/lp_admin.py",
]

# Non-LP files ALLOWED to import LP core (enumerated seams, read-only,
# one-way). Anything else importing lp_* fails the drift check.
SEAMS = [
    "routes/catalog.py",        # S1: engine pricing at estimate tier + exceptions frozenset
    "routes/estimates.py",      # S2: tier seed, CSV one-surface derive, shares
    "routes/pricing_admin.py",  # S3: LP section guard
    "routes/hover.py",          # S4: _build_lines LP branches (carve to lp_ingest.py at fork time)
]

# One-time scripts (not runtime dependencies, exempt from seam rules).
MIGRATIONS = [
    "migrate_iter97_lp_cut.py",
    "migrate_iter100_tier_coherence.py",
    "backfill_iter99_est910869L.py",
]

# Frontend LP surface (documentation for the extraction recipe).
LP_FRONTEND_FILES = [
    "frontend/src/lib/lpMaterialList.js",
    "frontend/src/lib/lpColors.js",
    "frontend/src/components/estimate/LpMaterialListPanel.jsx",
    "frontend/src/components/estimate/OpeningsReviewCard.jsx",
    "frontend/src/pages/LpFormulaPreview.jsx",
    "frontend/src/pages/MaterialListShare.jsx",
]
LP_I18N_PREFIX = "lp."  # keys in dictionaries.js extractable by prefix

# Data tagging contract.
LP_COLLECTION_PREFIX = "lp_"          # dedicated collections
LP_SETTINGS_ID_PREFIX = "lp_"         # docs inside shared `settings`
LP_ESTIMATE_FIELD_PREFIX = "lp_"      # LP fields on shared estimate docs
LP_LINE_TAB = "lp_smart"              # line/tab tagging
# Shared collections LP routers may touch (tagged at the field level):
SHARED_COLLECTIONS_ALLOWED = [
    "estimates", "settings", "users", "companies", "ai_measure_runs",
]

ENV_FLAGS = ["LP_AI_FORMULAS_V1"]

# KNOWN DEBT (accepted in the audit, fork-time work): lp_package's
# assemble deferred-imports routes.hover._build_lines (the S4 carve —
# extract lp_ingest.py when the fork is exercised). The drift check
# allows EXACTLY this edge and nothing else.
KNOWN_DEBT_IMPORTS = {
    "lp_package.py": {"routes"},  # routes.hover._build_lines only
}
