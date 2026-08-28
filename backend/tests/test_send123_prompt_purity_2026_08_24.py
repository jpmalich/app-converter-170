"""SEND-123 pin (Howard ruled 2026-08-24) — NO FIXTURE FIGURE APPEARS
IN ANY PROMPT.

The blueprint prompt's derived-value worked example shipped Letrick's
fan string (9'-11 1/8"), Boni's ceiling note (8'-1 1/8") and the
fabricated stackup total (20'-0") verbatim — prior-house figures in
front of the model on EVERY read since the example was written. That
qualification is registered (ocr_geometry.RULINGS_REGISTER). This pin
is the structural scan, same shape as the no-job-names discipline:
every prompt constant is scanned against the fixture-figure set.

SCOPE: distinctive drawn/sealed figures from the fixture houses.
Industry-standard shorthand (3068 door codes, 6'-8" door height,
16'-0" x 8'-0" garage door, 3'-0" x 5'-0" window, 1'-0" overhang and
scale strings) is REVIEWED-GENERIC — conventions, not house evidence.
"""
import ast

from fixture_figures import FIXTURE_FIGURES, all_fixture_figures

PROMPT_MODULES = [
    "/app/backend/routes/ai_blueprint.py",
    "/app/backend/routes/ai_measure.py",
    "/app/backend/schedule_read.py",
    "/app/backend/routes/pdf_overlay.py",
    "/app/backend/height_read.py",
    "/app/backend/page_rotation.py",
]

# SEND-124 item 3: the figure set lives in fixture_figures.py — the
# registry grows WITH the seals (dart joins when Howard seals it); the
# coupling pins below stop the set narrowing silently.
FIXTURE_FIGURES_UNION = all_fixture_figures()


def _prompt_constants(path):
    try:
        src = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and len(node.value.value) > 400):
            name = (node.targets[0].id
                    if isinstance(node.targets[0], ast.Name) else "?")
            yield name, node.lineno, node.value.value


def test_no_fixture_figure_in_any_prompt():
    hits = []
    for path in PROMPT_MODULES:
        for name, ln, text in _prompt_constants(path) or ():
            for fig in FIXTURE_FIGURES_UNION:
                if fig in text:
                    hits.append(f"{path}:{ln} {name} carries {fig!r}")
    assert not hits, (
        "PROMPT EXPOSURE — fixture figures reachable by the model:\n"
        + "\n".join(hits))


def test_registry_stays_in_step_with_the_seals():
    # SEND-124 item 3 coupling: every fixture house has an entry, and an
    # entry may sit empty ONLY while explicitly pending_seal — sealing a
    # house without adding its figures fails here, so the set can only
    # narrow deliberately, never silently.
    # SEND-143 NAMED PIN UPDATE: no customer name is left in the registry
    # (boni/tanis/dart → sealed_fixture_c/_d/_e, ruled 2026-08-28). FOUR
    # ENTRIES STILL REQUIRED and the union is unchanged — the coupling did
    # not loosen, only the keys are neutral.
    for house in ("sealed_fixture_c", "sealed_hand_takeoff",
                  "sealed_fixture_d", "sealed_fixture_e"):
        assert house in FIXTURE_FIGURES, f"{house} missing from registry"
    for gone in ("letrick", "boni", "tanis", "dart"):
        assert gone not in FIXTURE_FIGURES, f"{gone} is back in the registry"
    for house, entry in FIXTURE_FIGURES.items():
        assert isinstance(entry, dict) and "figures" in entry \
            and "pending_seal" in entry, house
        if not entry["pending_seal"]:
            assert entry["figures"], (
                f"{house} is sealed-class but carries no figures — "
                "the registry narrowed silently")
    assert len(FIXTURE_FIGURES_UNION) >= 19


def test_qualification_is_registered():
    from ocr_geometry import RULINGS_REGISTER
    import json
    blob = json.dumps(RULINGS_REGISTER)
    assert "PRIOR-HOUSE FIGURES WERE IN FRONT OF THE MODEL" in blob


def test_scan_actually_sees_the_prompts():
    # the scan is only worth its assertion if it reads the real prompts
    names = {n for p in PROMPT_MODULES
             for n, _, _ in (_prompt_constants(p) or ())}
    assert "SYSTEM_PROMPT" in names
    assert "ROOF_PASS_PROMPT" in names
