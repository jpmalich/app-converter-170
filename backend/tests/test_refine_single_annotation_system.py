"""ONE ANNOTATION SYSTEM pins (ruled 2026-07-26) — RE-CUT BY SEND-139
(Howard ruled 2026-08-27).

WHAT THIS FILE HELD: "Refine on Photo" had to open the SAME guided 7-step
PhotoAnnotateModal — never a second independent annotation model.

WHAT CHANGED: the gable and dormer tools MOVED into PhotoTakeoffEditor, so
Refine on Photo (and the tile's Annotate button, and the refine photo
picker) were RETIRED. The rule they served is not weakened, it is
completed: there is now ONE drawing surface on this screen instead of two
that had to be kept identical. The annotator survives as the GUIDED
CAPTURE step and as an IMPORT SOURCE — never as a drawing UI here.

The guided-capture merge and the modal's own step 6/7 gable and dormer
flows are UNTOUCHED and still pinned below.
"""
from pathlib import Path

FE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
AIBTN = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
MODAL = (FE / "components" / "estimate" / "PhotoAnnotateModal.jsx").read_text()
WIZARD = (FE / "components" / "estimate" / "GuidedCaptureWizard.jsx").read_text()
EDITOR = (FE / "components" / "estimate" / "PhotoTakeoffEditor.jsx").read_text()

# comments may record history; only live code is judged
CODE = "\n".join(ln for ln in AIBTN.splitlines()
                 if not ln.lstrip().startswith(("//", "/*", "*")))


def test_photomeasure_path_retired():
    assert "PhotoMeasureButton" not in CODE, (
        "AIMeasureButton must not use the separate PhotoMeasureButton "
        "tap-measure UI — there is ONE drawing surface on this screen"
    )
    assert "refineMergeMode" not in CODE, (
        "Refine merge-mode picker belonged to the retired second model"
    )


def test_the_refine_door_is_retired_and_the_editor_is_the_drawing_surface():
    """NAMED PIN UPDATE (SEND-139): the door this test used to require is
    GONE, and its job moved. Two annotation UIs became one."""
    for gone in ('data-testid="ai-measure-refine-btn"',
                 "setAnnotateGuided(true)",
                 'data-testid="refine-photo-picker"',
                 "data-testid={`refine-photo-pick-${i}`}",
                 "guidedFlow={annotateGuided ? {",
                 "onFinish: () => setRefineOpen(true)"):
        assert gone not in CODE, gone
    # the drawing surface that replaced it, with the moved tools on it
    assert "PhotoTakeoffEditor" in CODE
    assert 'from "@/lib/gableMath"' in EDITOR
    assert '{ key: "gable", label: "Gable"' in EDITOR
    assert '{ key: "dormer", label: "Dormer"' in EDITOR


def test_wizard_merge_carries_gables_dormers_imagedims():
    assert "merged.gables = annotations.gables" in AIBTN
    assert "merged.dormers = annotations.dormers" in AIBTN
    assert "merged.imageDims = annotations.imageDims" in AIBTN
    # Guided Capture is NOT an Annotate door and keeps its own mount
    assert "PhotoAnnotateModal" in WIZARD
    assert "<GuidedCaptureWizard" in AIBTN


def test_guided_steps_6_and_7_are_default_flow():
    assert '{ key: "gable", mode: MODE_GABLE' in MODAL
    assert '{ key: "dormer", mode: MODE_DORMER' in MODAL
    assert "Skip – no gables on this wall" in MODAL
    assert "Skip – no dormers on this wall" in MODAL
