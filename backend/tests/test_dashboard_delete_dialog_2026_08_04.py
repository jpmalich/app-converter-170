"""DASHBOARD DELETE — ONE DIALOG, BOTH PATHS (sweep finding 2026-08-04,
iteration 53). The unlinked-delete path used the native window.confirm:
invisible to automation (auto-dismissed headlessly — read as 'confirm
does nothing'), untestable, unstyled, and English-only while the linked
path had a proper guard dialog. Ruled: ONE AlertDialog for both paths,
chrome through t() in both languages.
"""
from pathlib import Path

FE = Path("/app/frontend/src")


def test_no_native_confirm_in_dashboard_delete():
    src = (FE / "pages" / "Dashboard.jsx").read_text()
    assert "window.confirm" not in src, \
        "native confirm is back — the delete flow must use the ONE guard dialog"
    assert 'data-testid="delete-guard-confirm"' in src
    assert 'data-testid="delete-guard-cancel"' in src
    assert "doDelete(delConfirm.id)" in src


def test_delete_dialog_chrome_is_bilingual():
    src = (FE / "pages" / "Dashboard.jsx").read_text()
    for key in ("dash.deleteTitle", "dash.trashNote", "dash.cancel", "dash.deleteConfirm"):
        assert f'"{key}"' in src, f"delete dialog no longer routes '{key}' through t()"
    dicts = (FE / "lib" / "dictionaries.js").read_text()
    for key in ("dash.deleteTitle", "dash.itsLinked", "dash.trashNote", "dash.deleteConfirm"):
        assert dicts.count(f'"{key}"') >= 2, f"'{key}' missing from one dictionary"
