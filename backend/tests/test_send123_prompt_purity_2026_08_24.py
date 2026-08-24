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

PROMPT_MODULES = [
    "/app/backend/routes/ai_blueprint.py",
    "/app/backend/routes/ai_measure.py",
    "/app/backend/schedule_read.py",
    "/app/backend/routes/pdf_overlay.py",
    "/app/backend/height_read.py",
    "/app/backend/page_rotation.py",
]

FIXTURE_FIGURES = [
    # Letrick — heights, fan string, side width
    "9'-11 1/8\"", "9'-11\"", "9'-1 1/8\"", "30'-2\"", "62'-0\"",
    # Boni — ceiling notes, fabricated stackup, sealed side
    "8'-1 1/8\"", "8'-1 1/2\"", "20'-0\"", "30'-0\"",
    # real garage wall + real schedule SIZE string (send-6 era examples)
    "9'-11 7/8\"", "2'-11 1/2\"", "4'-11 1/2\"",
    # glyph-drop census pair
    "33'-5 1/2\"", "32'-5 1/2\"",
    # Tanis — sealed + model-claimed
    "127'-2\"", "58'-8\"", "10'-1 1/8\"", "97'-0\"", "57'-4\"",
]


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
            for fig in FIXTURE_FIGURES:
                if fig in text:
                    hits.append(f"{path}:{ln} {name} carries {fig!r}")
    assert not hits, (
        "PROMPT EXPOSURE — fixture figures reachable by the model:\n"
        + "\n".join(hits))


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
