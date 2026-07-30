"""Iteration 48 — Trade-spec dropdown proof for Howard.
Tests panel_size (NEW), wrap_trim_width_in (NEW), fascia_width_in,
batten_spacing_in — PUT bounds, persistence (silent-strip proof),
LP re-derivation on panel size, name-only on wrap trim width.

Uses Jon Casile estimate (lp_smart, B&B family, 68 panels @ 4x10).
"""
import os
import pytest
import requests
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD

BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]
JON = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"  # Jon Casile — LP B&B, 68 4x10 panels
DEG1PM = "f3e7d728-e27d-437a-b257-a898e4afcec8"  # 3 degree 1pm — LP B&B, 138 panels


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    # else: httpOnly cookies already on the session
    return s


def _get(sess, eid):
    r = sess.get(f"{BASE}/api/estimates/{eid}")
    assert r.status_code == 200, r.text
    return r.json()


def _put(sess, eid, patch):
    return sess.put(f"{BASE}/api/estimates/{eid}", json=patch)


def _materialize(sess, eid):
    """Rebuild LP tab lines via server-side engine (same path hover-lp-run
    uses). Returns True on success, False otherwise so tests can report
    the gap plainly instead of masking it."""
    r = sess.post(f"{BASE}/api/estimates/{eid}/lp-package/materialize", json={})
    return r.status_code == 200, r.status_code, r.text[:200]


def _lines(est, name_sub, section=None):
    out = []
    for ln in est.get("lines") or []:
        n = ln.get("name") or ""
        if name_sub in n and (section is None or ln.get("section") == section):
            out.append(ln)
    return out


# ---- PUT BOUNDS ----
class TestPutBounds:
    def test_panel_size_4x12_rejected(self, sess):
        r = _put(sess, JON, {"panel_size": "4x12"})
        assert r.status_code == 422, f"expected 422 got {r.status_code}: {r.text[:200]}"

    def test_wrap_trim_5_rejected(self, sess):
        r = _put(sess, JON, {"wrap_trim_width_in": 5})
        assert r.status_code == 422, f"expected 422 got {r.status_code}: {r.text[:200]}"

    def test_panel_size_4x8_accepted(self, sess):
        r = _put(sess, JON, {"panel_size": "4x8"})
        assert r.status_code == 200, r.text

    def test_wrap_trim_6_accepted(self, sess):
        r = _put(sess, JON, {"wrap_trim_width_in": 6})
        assert r.status_code == 200, r.text


# ---- PERSISTENCE (silent-strip) ----
class TestPersistence:
    def test_four_specs_persist(self, sess):
        patch = {
            "panel_size": "4x8",
            "wrap_trim_width_in": 6,
            "fascia_width_in": 12,
            "batten_spacing_in": 16,
        }
        r = _put(sess, JON, patch)
        assert r.status_code == 200, r.text
        # GET back
        e = _get(sess, JON)
        assert e.get("panel_size") == "4x8"
        assert e.get("wrap_trim_width_in") == 6
        assert e.get("fascia_width_in") == 12
        assert e.get("batten_spacing_in") == 16


# ---- DERIVATION PROOFS ----
class TestDerivation:
    """The review says LP tab rebuilds server-side. So PUT should trigger
    rename/recount on stored lines. Verify by GET after PUT."""

    def test_panel_size_4x8_renames_and_recounts(self, sess):
        # Baseline: put back to 4x10, capture count
        _put(sess, JON, {"panel_size": "4x10"})
        ok, _, _ = _materialize(sess, JON)
        assert ok, "materialize baseline failed"
        e0 = _get(sess, JON)
        base_panels = _lines(e0, "38 Series", section="LP Smart Siding")
        base_4x10 = [l for l in base_panels if "4' x 10' Panel" in (l.get("name") or "")]
        assert base_4x10, f"expected 4x10 panel line at baseline; got names={[l.get('name') for l in base_panels]}"
        q10 = float(base_4x10[0].get("qty") or 0)
        # Flip to 4x8
        _put(sess, JON, {"panel_size": "4x8"})
        _materialize(sess, JON)
        e1 = _get(sess, JON)
        panels = _lines(e1, "38 Series", section="LP Smart Siding")
        four_x_eight = [l for l in panels if "4' x 8' Panel" in (l.get("name") or "")]
        four_x_ten = [l for l in panels if "4' x 10' Panel" in (l.get("name") or "")]
        assert four_x_eight, (
            f"expected 4' x 8' Panel line after PUT+materialize; names={[l.get('name') for l in panels]}"
        )
        assert not four_x_ten, "4x10 line still present after switching to 4x8"
        q8 = float(four_x_eight[0].get("qty") or 0)
        # 40/32 = 1.25 ratio; allow +/- 2 units for rounding
        exp = round(q10 * 40 / 32)
        assert abs(q8 - exp) <= 2, f"panel count 4x8={q8}, expected ~{exp} (base 4x10={q10})"
        print(f"PANEL 4x10={q10} -> 4x8={q8} (expected ~{exp})")

    def test_wrap_trim_width_renames_only(self, sess):
        _put(sess, JON, {"wrap_trim_width_in": 4})
        _materialize(sess, JON)
        e0 = _get(sess, JON)
        base = _lines(e0, '540 Series Trim', section="LP SmartSide Trim")
        base_4 = [l for l in base if '5/4" x 4"' in (l.get("name") or "")]
        assert base_4, f"expected 5/4\" x 4\" 540 line; got {[l.get('name') for l in base]}"
        q0 = float(base_4[0].get("qty") or 0)
        _put(sess, JON, {"wrap_trim_width_in": 6})
        _materialize(sess, JON)
        e1 = _get(sess, JON)
        after = _lines(e1, '540 Series Trim', section="LP SmartSide Trim")
        after_6 = [l for l in after if '5/4" x 6"' in (l.get("name") or "")]
        assert after_6, f"expected 5/4\" x 6\" 540 line after PUT; got {[l.get('name') for l in after]}"
        q1 = float(after_6[0].get("qty") or 0)
        assert q1 == q0, f"wrap trim width should be name-only; qty changed {q0} -> {q1}"
        print(f"WRAP 4\"={q0} -> 6\"={q1} (name-only, qty unchanged)")

    def test_fascia_width_renames_440(self, sess):
        _put(sess, JON, {"fascia_width_in": 8})
        _materialize(sess, JON)
        e0 = _get(sess, JON)
        base = _lines(e0, '440 Series Trim', section="LP SmartSide Trim")
        base_8 = [l for l in base if '4/4" x 8"' in (l.get("name") or "")]
        assert base_8, f"expected 4/4\" x 8\" 440 baseline; got {[l.get('name') for l in base]}"
        _put(sess, JON, {"fascia_width_in": 12})
        _materialize(sess, JON)
        e1 = _get(sess, JON)
        after = _lines(e1, '440 Series Trim', section="LP SmartSide Trim")
        after_12 = [l for l in after if '4/4" x 12"' in (l.get("name") or "")]
        assert after_12, f"expected 4/4\" x 12\" after PUT; got {[l.get('name') for l in after]}"
        print(f"FASCIA renamed to {after_12[0].get('name')} qty={after_12[0].get('qty')}")


# ---- WHOLE UNITS (R3) ----
class TestWholeUnits:
    def test_no_fractional_qty(self, sess):
        e = _get(sess, JON)
        bad = []
        for ln in e.get("lines") or []:
            q = ln.get("qty")
            if q is None:
                continue
            try:
                fq = float(q)
            except Exception:
                continue
            if fq != int(fq):
                bad.append((ln.get("section"), ln.get("name"), q))
        assert not bad, f"fractional qtys present: {bad[:5]}"


# ---- CLEANUP: restore defaults ----
def test_zz_restore_defaults(sess):
    _put(sess, JON, {
        "panel_size": "4x10",
        "wrap_trim_width_in": 4,
        "fascia_width_in": 8,
        "batten_spacing_in": 12,
    })
    _materialize(sess, JON)
    e = _get(sess, JON)
    assert e.get("panel_size") in (None, "4x10")
