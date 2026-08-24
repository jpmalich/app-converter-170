"""SEND-124 item 3 registry — DISTINCTIVE DRAWN/SEALED FIGURES PER
FIXTURE HOUSE.

THE IN-STEP RULE (Howard ruled 2026-08-24): when a house's ground truth
is sealed — dart next, and any future house — its distinctive figures
JOIN THIS REGISTRY IN THE SAME SEND. The prompt-purity pin scans every
prompt constant against the UNION of all houses here; the coupling pin
fails any house entry that is empty and not explicitly marked
pending_seal, so the set can only grow deliberately, never narrow
silently.

House names here are DATA (registry precedent: capture_sheet_baseline
ESTS map), never operative logic. Attribution per house is best-effort;
the UNION is what the purity pin enforces. Industry-standard shorthand
(3068 door codes, 6'-8" door height, 16'-0" x 8'-0" garage door,
1'-0" overhang/scale strings) stays REVIEWED-GENERIC and does not
belong here.
"""

FIXTURE_FIGURES = {
    "boni": {
        "pending_seal": False,
        "figures": ["8'-1 1/8\"", "8'-1 1/2\"", "20'-0\"", "30'-0\"",
                    "62'-0\"", "9'-11 7/8\""],
    },
    "letrick": {
        "pending_seal": False,
        "figures": ["9'-11 1/8\"", "9'-11\"", "9'-1 1/8\"", "30'-2\"",
                    "2'-11 1/2\"", "4'-11 1/2\"", "33'-5 1/2\"",
                    "32'-5 1/2\""],
    },
    "tanis": {
        "pending_seal": False,
        "figures": ["127'-2\"", "58'-8\"", "10'-1 1/8\"", "97'-0\"",
                    "57'-4\"", "57'-0\""],
    },
    "dart": {
        # Sealed truth OWED BY HOWARD — figures join here in the sealing
        # send. pending_seal is the ONLY way an entry may sit empty.
        "pending_seal": True,
        "figures": [],
    },
}


def all_fixture_figures() -> list[str]:
    out: list[str] = []
    for h in FIXTURE_FIGURES.values():
        out.extend(h.get("figures") or [])
    return sorted(set(out))
