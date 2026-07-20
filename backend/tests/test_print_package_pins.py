"""Print package pins — EL-1..EL-4 one-click print flow (authorized
2026-07-20). Read-only feature: the package page reuses SheetSvg verbatim,
so printed sheets are IDENTICAL to on-screen sheets by construction.
Walls the run can't render get a NAMED block — never silently absent.
Print-scoped CSS lives INSIDE the page component (mount-scoped), so other
print flows (quote, takeoff) keep their own defaults.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FE = ROOT / "frontend" / "src"
PRINT_PAGE = (FE / "pages" / "ElevationSheetsPrint.jsx").read_text()
SHEET_PAGE = (FE / "pages" / "ElevationSheet.jsx").read_text()
FVC = (FE / "components" / "estimate" / "FieldVerifyCard.jsx").read_text()
APP = (FE / "App.js").read_text()


def test_route_registered():
    assert '"/estimate/:id/elevation-sheets/print"' in APP
    assert "ElevationSheetsPrint" in APP


def test_print_page_reuses_sheet_svg_verbatim():
    # single renderer = printed sheets identical to on-screen sheets
    assert "export function SheetSvg({ data })" in SHEET_PAGE
    assert "<SheetSvg data={data} />" in SHEET_PAGE          # on-screen page
    assert "<SheetSvg data={s.data} />" in PRINT_PAGE        # print package
    assert "from \"@/pages/ElevationSheet\"" in PRINT_PAGE


def test_print_page_one_sheet_per_page_and_scoped_css():
    assert "page-break-after: always" in PRINT_PAGE
    assert "@page { size: letter landscape" in PRINT_PAGE
    # app chrome hidden ONLY within this page's mount-scoped style
    assert "header, footer { display: none !important; }" in PRINT_PAGE
    # one-click: auto print after all four fetches settle
    assert "window.print()" in PRINT_PAGE
    assert "Promise.allSettled" in PRINT_PAGE


def test_print_page_named_missing_wall_block():
    assert "print-sheet-missing-" in PRINT_PAGE
    assert "not renderable" in PRINT_PAGE
    assert "elevation-sheets-print-empty" in PRINT_PAGE  # zero-sheet named state
    assert "of 4 elevations render" in PRINT_PAGE        # honest count line


def test_entry_points():
    # Field Verify chooser: Print all chip, INSIDE the sheetWalls-gated block
    assert 'data-testid="field-verify-elevation-sheets-print-all"' in FVC
    gated = FVC.split('data-testid="field-verify-elevation-sheets"')[1]
    assert "field-verify-elevation-sheets-print-all" in gated.split(
        'data-testid="field-verify-elevation-sheets-empty"')[0]
    # single-sheet page: Print all 4 link
    assert 'data-testid="elevation-sheet-print-all"' in SHEET_PAGE
