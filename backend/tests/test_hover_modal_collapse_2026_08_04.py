"""HOVER IMPORT MODAL — COLLAPSIBLE SECTIONS (ruled 2026-08-04).

The "VERO WINDOW OPENINGS — STYLE GUESS" list (30 rows on a real report)
made the import modal a wall of rows. Ruled: collapse it BY DEFAULT with a
one-click expand. Same fold applied to the sanity-warnings banner.

PINS (presentation-only guarantee):
  • Collapsed is the DEFAULT STATE for both sections — useState(false).
  • apply() NEVER reads the collapse state — the applied payload is
    byte-identical whether the sections are open or closed.
  • The fold never buries a flag:
      - openings whose style guess didn't resolve surface as an
        "N need review" badge ON the collapsed header;
      - any warning level that isn't info/warn (future blocking levels)
        stays visible even while the banner is collapsed.
  • Expanded keeps FULL function — same per-row style pickers, same
    remove buttons, same edit-before-apply.
"""
from pathlib import Path

JSX = Path("/app/frontend/src/components/estimate/HoverImportButton.jsx")


def _jsx():
    return JSX.read_text()


def test_openings_section_collapsed_by_default():
    jsx = _jsx()
    assert "const [openingsOpen, setOpeningsOpen] = useState(false);" in jsx, \
        "window-openings section must default to COLLAPSED"
    assert 'data-testid="hover-openings-toggle"' in jsx, \
        "collapsed header must be a one-click toggle"
    assert "tap to review styles" in jsx, \
        "collapsed header must invite the contractor in"


def test_warnings_banner_collapsed_by_default():
    jsx = _jsx()
    assert "const [warningsOpen, setWarningsOpen] = useState(false);" in jsx, \
        "sanity-warnings banner must default to COLLAPSED"
    assert 'data-testid="hover-warnings-toggle"' in jsx


def test_collapse_never_buries_a_flag():
    jsx = _jsx()
    # Unresolved style guesses surface ON the collapsed openings header.
    assert 'data-testid="hover-openings-needs-review"' in jsx
    assert "!VERO_PRODUCT_TYPES.includes(op.product_type)" in jsx, \
        "needs-review must mean: style guess didn't resolve to a known Vero type"
    # Any non-heuristic warning level stays visible while collapsed.
    assert 'w.level !== "info" && w.level !== "warn"' in jsx, \
        "future blocking warning levels must stay visible even when folded"
    assert "warningsOpen ? result.warnings : blocking" in jsx


def test_apply_never_reads_collapse_state():
    """THE BYTE-IDENTICAL PIN: the applied payload cannot depend on whether
    the sections are open or closed, because apply() never reads either
    boolean. Slice from apply()'s definition to the render body and assert
    the collapse state names are absent."""
    jsx = _jsx()
    start = jsx.index("const apply = async ()")
    end = jsx.index("setShowWarning(true)")  # first render-body marker after apply
    body = jsx[start:end]
    assert "openingsOpen" not in body, "apply() must not read openings collapse state"
    assert "warningsOpen" not in body, "apply() must not read warnings collapse state"


def test_expanded_openings_keep_full_function():
    jsx = _jsx()
    # Same per-row picker + remove button, gated only by openingsOpen.
    assert "hover-opening-style-" in jsx
    assert "hover-opening-remove-" in jsx
    assert "updateOpeningType(op.id, e.target.value)" in jsx
    assert "{openingsOpen && (" in jsx


def test_collapse_state_resets_on_new_result():
    """A fresh import or restore starts collapsed again — collapsed is the
    default STATE, not a one-time initial value."""
    jsx = _jsx()
    assert jsx.count("setOpeningsOpen(false)") >= 3  # both import branches + restore
    assert jsx.count("setWarningsOpen(false)") >= 3
