"""ONE ANNOTATION SYSTEM pins (ruled 2026-07-26).

Refine on Photo must open the SAME guided 7-step PhotoAnnotateModal
(same data, same tools) — never a second independent annotation model.
The old PhotoMeasureButton tap-measure path is retired from AI Measure.

Also pins the wizard→photoAnnotations merge carrying gables, dormers
and imageDims: annotations drawn in guided capture (incl. steps 6+7)
must survive into the store Refine edits and the AI run reads.
"""
from pathlib import Path

FE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
AIBTN = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
MODAL = (FE / "components" / "estimate" / "PhotoAnnotateModal.jsx").read_text()


def test_photomeasure_path_retired():
    assert "PhotoMeasureButton" not in AIBTN, (
        "AIMeasureButton must not use the separate PhotoMeasureButton "
        "tap-measure UI — Refine on Photo opens the guided annotate modal"
    )
    assert "refineMergeMode" not in AIBTN, (
        "Refine merge-mode picker belonged to the retired second model"
    )


def test_refine_opens_guided_annotate_modal():
    assert 'data-testid="ai-measure-refine-btn"' in AIBTN
    assert "setAnnotateGuided(true)" in AIBTN
    assert 'data-testid="refine-photo-picker"' in AIBTN
    assert 'data-testid={`refine-photo-pick-${i}`}' in AIBTN
    # guidedFlow threaded into the shared modal instance
    assert "guidedFlow={annotateGuided ? {" in AIBTN
    assert "onExit: () => setAnnotateGuided(false)" in AIBTN


def test_wizard_merge_carries_gables_dormers_imagedims():
    assert "merged.gables = annotations.gables" in AIBTN
    assert "merged.dormers = annotations.dormers" in AIBTN
    assert "merged.imageDims = annotations.imageDims" in AIBTN


def test_guided_steps_6_and_7_are_default_flow():
    assert '{ key: "gable", mode: MODE_GABLE' in MODAL
    assert '{ key: "dormer", mode: MODE_DORMER' in MODAL
    assert "Skip – no gables on this wall" in MODAL
    assert "Skip – no dormers on this wall" in MODAL
