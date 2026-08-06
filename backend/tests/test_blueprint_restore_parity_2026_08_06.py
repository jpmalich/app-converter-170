"""RESTORE PARITY pin (Howard, 2026-08-06): the Blueprint door's cached-
read restore must LOOK like the Hover door's "Restore HOVER Lines" —
same button treatment, one look across doors. This pin fails if the two
buttons' class strings drift apart or the blueprint one loses its
i18n'd label / testid.
"""
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"

HOVER = (FRONTEND / "components" / "estimate" / "HoverImportButton.jsx").read_text()
BP = (FRONTEND / "components" / "estimate" / "BlueprintMeasureButton.jsx").read_text()
DICTS = (FRONTEND / "lib" / "dictionaries.js").read_text()

SHARED_CLASSES = ("w-full justify-center px-3 py-1.5 bg-[var(--surface)] "
                  "text-[#0369A1] border border-[#0EA5E9] hover:bg-[#F0F9FF] "
                  "text-xs font-bold uppercase tracking-wider flex items-center "
                  "gap-1.5 disabled:opacity-50")


def test_blueprint_restore_wears_the_hover_button_treatment():
    assert SHARED_CLASSES in HOVER, "Hover restore button classes moved — update the parity pin together"
    assert SHARED_CLASSES in BP, "Blueprint restore lost the Hover button treatment"


def test_blueprint_restore_button_is_wired_and_translated():
    assert 'data-testid="blueprint-resume-btn"' in BP
    assert 'onClick={restoreResume}' in BP
    assert 't("bp.restore")' in BP
    assert DICTS.count('"bp.restore":') == 2, "bp.restore must exist in BOTH en and es"
    assert DICTS.count('"bp.restoreTitle":') == 2


def test_done_state_has_no_plain_text_banner():
    """The old 'PREVIOUS READ · n pg · m min' text-line treatment must not
    come back for done runs — done gets the button, only running/errored
    keep the compact status line."""
    assert "Previous read ·" not in BP


def test_done_blueprint_reads_never_expire():
    """Howard ruled 2026-08-06: a cached blueprint read the contractor
    paid for does NOT expire — 31 minutes later it is exactly as good as
    29. A page reload must never hide RESTORE / TAG PROFILES for a done
    run. Only error/running recovery offers keep the 30-min freshness."""
    assert 'run.status === "done" ||' in BP, \
        "done runs must surface regardless of age"
    assert "ageOk && restorable" not in BP, \
        "the old 30-min hide for done runs came back"


def test_done_photo_reads_never_expire_either():
    """Same ruling applied to the photo door — AIMeasureButton had the
    stale 30-min pattern the blueprint door inherited (Hover never did)."""
    AIM = (FRONTEND / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
    assert 'r.status === "done" || r.status === "running"' in AIM, \
        "done photo runs must surface regardless of age"
