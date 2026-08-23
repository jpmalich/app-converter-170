"""SEND-113 — THE EXPOSED-FIELD CARRY PIN (frontend half of the
silent-strip class, made structural).

SEND-111 §2b named 10 derivation-born line fields that survive browser
round-trips ONLY because the client carries them; SEND-111 §6 then
watched one of them (cross_family_flag) strip live. This pin scans
`useEstimate.js` and fails if any exposed-class field is missing from
EITHER the catalog-merge rebuild OR the save whitelist — a future field
regression turns a pin red instead of stripping silently.

The refusal trio is exempt BY LAW, not by carry: reapply_refusal_law
re-seats it server-side at every client-shaped write (SEND-111), so the
client payload is irrelevant to it.
"""

SRC = "/app/frontend/src/lib/useEstimate.js"

# Derivation-born, client-carried, re-derived by nothing at a
# client-shaped write (SEND-111 §2b) — every one must ride BOTH halves.
EXPOSED_FIELDS = [
    "raw_qty", "derived_qty", "note", "viz", "ami_part", "lab_src",
    "pricing_source", "cross_family_flag", "_waste_included", "qty_src",
]
# carried for identity/UX, same class of loss if dropped
ALSO_CARRIED = ["item_id", "qty_pending", "contractor_note"]


def test_every_exposed_field_rides_merge_and_save():
    src = open(SRC).read()
    missing = [f for f in EXPOSED_FIELDS + ALSO_CARRIED
               if src.count(f"{f}:") < 2]  # once in merge + once in save
    assert not missing, (
        f"exposed-class fields missing from the merge and/or save carry "
        f"in useEstimate.js: {missing} — this is the fifth member's "
        f"class; carry them or widen the law, never neither")


def test_trio_is_law_owned_not_carry_dependent():
    # the trio's protection is the server-side refusal law, pinned in
    # test_send111_2026_08_23.py — assert the law is still wired rather
    # than requiring a client carry
    est_src = open("/app/backend/routes/estimates.py").read()
    assert est_src.count("reapply_refusal_law(est_id") == 2
