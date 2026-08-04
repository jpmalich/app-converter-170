"""HOVER RESTORE MUST NOT CLOBBER THE WASTE FIELD (ruled 2026-08-04).

Found during the race cleanup on EST-536665 (3 degree rd 8-4-26 4pm):
hover-lp-run materializes a B&B estimate with the FAMILY-DEFAULTED waste
(30) written into the visible field; a later "Restore HOVER lines" apply
wrote the import-time generic 10 prefill (persisted inside cached
measurements) back over it — panels 138 -> 117 on the next rederive, a
penny-moving clobber. Fresh imports self-heal (the materialize branch
re-adopts freshEst.waste_pct); restores skip that branch.

RECONCILED WITH THE SEALED ONE-RULE (2026-07-28, no family exception):
the fix lives in the PREFILL, not a per-kind branch at apply — on a
restore the prefill RESOLVES TO THE ESTIMATE'S OWN FIELD (the governing
spec value per the 2026-08-03 waste ruling), for every kind. The apply
still writes ONE wastePct into the field for all families.
"""
from pathlib import Path

JSX = Path("/app/frontend/src/components/estimate/HoverImportButton.jsx")


def test_restore_prefill_resolves_to_the_estimates_own_field():
    jsx = JSX.read_text()
    assert "(restoredAt ? est?.waste_pct : null)" in jsx, \
        "restore prefill must read the estimate's own governing waste field"
    assert "?? result?.measurements?._waste_field_prefill_pct" in jsx, \
        "fresh imports keep the measurement prefill"


def test_no_per_kind_waste_branch_at_apply():
    """The sealed one-rule holds: ONE wastePct for every family — the
    restore guard lives in the prefill resolution, never a kind branch."""
    jsx = JSX.read_text()
    assert "const wastePct = wasteFieldPrefill" in jsx
    assert 'est?.kind === "lp_smart"\n      ? Number(est?.waste_pct' not in jsx
