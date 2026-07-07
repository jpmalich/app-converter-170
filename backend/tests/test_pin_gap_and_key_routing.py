"""Iter 79j.59 — Unit tests for the two new gates that landed today:

1) `_pick_llm_api_key` — orthogonal per-phase flags + legacy
   auto-migration. This is the router that decides whether an
   Anthropic call goes through the Emergent proxy or direct to
   api.anthropic.com. We want to lock the behaviour down BEFORE
   flipping `ANTHROPIC_DIRECT_A=1` in production.

2) `_derive_pin_gap_hints` — the pin-gap-signal that Howard flagged
   this morning: when contractor pins tag a feature on an unmeasured
   or empty-photo elevation, we surface it so the UI can prompt a
   re-shoot instead of letting the mismatch live only in the trace.

Both functions are pure — no LLM, no DB, no HTTP — so they're
regression-friendly.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from dotenv import load_dotenv

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))


@pytest.fixture
def ai_measure(monkeypatch):
    """`_pick_llm_api_key` reads env each call, so the fixture just
    imports the module (already cached after first use) and clears
    the relevant env vars. Cleanup ordering matters: `from routes
    import ai_measure` cascades a load_dotenv call the first time it
    runs, so we delenv AFTER the import to guarantee a clean slate."""
    from routes import ai_measure as m
    # Delete AFTER import — the routes package's hover.load_dotenv()
    # runs during the first import and would otherwise refill env.
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_DIRECT_A",
              "ANTHROPIC_DIRECT_B", "ANTHROPIC_DIRECT_ROUTE",
              "EMERGENT_LLM_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "test-emergent-key")
    return m


class TestPickLlmApiKey:
    """Every branch of the phase-aware router. Anthropic-only bypass
    means every non-anthropic provider MUST stay on the proxy no
    matter what the flags say."""

    def test_no_flags_no_key_proxy(self, ai_measure):
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="A")
        assert source == "emergent_proxy"
        assert key == "test-emergent-key"
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="B")
        assert source == "emergent_proxy"

    def test_direct_a_only(self, ai_measure, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        monkeypatch.setenv("ANTHROPIC_DIRECT_A", "1")
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="A")
        assert source == "anthropic_direct"
        assert key == "sk-ant-xyz"
        # Phase B still on proxy because ANTHROPIC_DIRECT_B is unset.
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="B")
        assert source == "emergent_proxy"

    def test_direct_b_only(self, ai_measure, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        monkeypatch.setenv("ANTHROPIC_DIRECT_B", "1")
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="B")
        assert source == "anthropic_direct"
        assert key == "sk-ant-xyz"
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="A")
        assert source == "emergent_proxy"

    def test_direct_both(self, ai_measure, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        monkeypatch.setenv("ANTHROPIC_DIRECT_A", "1")
        monkeypatch.setenv("ANTHROPIC_DIRECT_B", "1")
        for phase in ("A", "B"):
            key, source = ai_measure._pick_llm_api_key("anthropic", phase=phase)
            assert source == "anthropic_direct"

    def test_legacy_auto_migration_phase_b_only(self, ai_measure, monkeypatch):
        """The legacy `ANTHROPIC_DIRECT_ROUTE=phase_b_only` MUST still
        route Phase B direct — Howard's pod runs on this value. New
        flags take precedence when set, but silence = auto-migration."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        monkeypatch.setenv("ANTHROPIC_DIRECT_ROUTE", "phase_b_only")
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="B")
        assert source == "anthropic_direct"
        # But Phase A still on proxy.
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="A")
        assert source == "emergent_proxy"

    def test_explicit_flag_overrides_legacy(self, ai_measure, monkeypatch):
        """New flag beats legacy when they disagree. Legacy said B,
        new flag says A — direct on A, proxy on B."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        monkeypatch.setenv("ANTHROPIC_DIRECT_A", "1")
        monkeypatch.setenv("ANTHROPIC_DIRECT_ROUTE", "phase_b_only")
        # Because ANTHROPIC_DIRECT_A is set, legacy auto-migration
        # does NOT fire (guard: only when both new flags are empty).
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="A")
        assert source == "anthropic_direct"
        key, source = ai_measure._pick_llm_api_key("anthropic", phase="B")
        assert source == "emergent_proxy"

    def test_non_anthropic_provider_never_direct(self, ai_measure, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        monkeypatch.setenv("ANTHROPIC_DIRECT_A", "1")
        monkeypatch.setenv("ANTHROPIC_DIRECT_B", "1")
        for provider in ("openai", "gemini", "azure"):
            for phase in ("A", "B"):
                key, source = ai_measure._pick_llm_api_key(provider, phase=phase)
                assert source == "emergent_proxy", f"{provider}/{phase}"

    def test_direct_key_absent_falls_back_to_proxy(self, ai_measure, monkeypatch):
        """Flag says direct, but ANTHROPIC_API_KEY is empty — proxy
        is the correct fallback so we don't blow up with a 401."""
        monkeypatch.setenv("ANTHROPIC_DIRECT_A", "1")
        monkeypatch.setenv("ANTHROPIC_DIRECT_B", "1")
        # ANTHROPIC_API_KEY intentionally unset
        for phase in ("A", "B"):
            key, source = ai_measure._pick_llm_api_key("anthropic", phase=phase)
            assert source == "emergent_proxy"

    def test_truthy_values(self, ai_measure, monkeypatch):
        """`1`, `true`, `yes`, `on` all enable — matches env-flag
        conventions elsewhere in the codebase."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        for val in ("1", "true", "yes", "on", "TRUE", "Yes"):
            monkeypatch.setenv("ANTHROPIC_DIRECT_A", val)
            _, source = ai_measure._pick_llm_api_key("anthropic", phase="A")
            assert source == "anthropic_direct", f"val={val!r}"

    def test_falsey_values(self, ai_measure, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")
        for val in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("ANTHROPIC_DIRECT_A", val)
            _, source = ai_measure._pick_llm_api_key("anthropic", phase="A")
            assert source == "emergent_proxy", f"val={val!r}"


class TestDerivePinGapHints:
    """Rule-by-rule coverage. Every hint MUST carry an actionable
    `re_shoot_elevation` — a bare warning without a next step is
    what Howard called out as insufficient this morning."""

    def _walls(self, labels):
        return [{"label": lb} for lb in labels]

    def _annot(self, photo_idx, elevation, callout=""):
        return {
            str(photo_idx): [{
                "elevation_label": elevation,
                "callout": callout,
                "profile": "lap",
                "sqft": 200,
            }],
        }

    def test_no_annotations_no_hints(self, ai_measure):
        assert ai_measure._derive_pin_gap_hints(
            annotations=None,
            walls=self._walls(["front"]),
            dormers=[],
            orphaned_walls=["back"],
            empty_photos=[],
        ) == []

    def test_pin_on_orphaned_elevation(self, ai_measure):
        """Rule 1 — the primary case from this morning's run: pin
        on `right`, right elevation orphaned (no photo covered)."""
        hints = ai_measure._derive_pin_gap_hints(
            annotations=self._annot(3, "right"),
            walls=self._walls(["front", "back", "left"]),
            dormers=[],
            orphaned_walls=["right"],
            empty_photos=[],
        )
        assert len(hints) == 1
        assert hints[0]["kind"] == "orphaned_elevation_with_pin"
        assert hints[0]["elevation"] == "right"
        assert hints[0]["re_shoot_elevation"] == "right"
        assert "right" in hints[0]["message"].lower()
        assert 3 in hints[0]["source_photo_idxs"]

    def test_pin_indicates_missing_dormer(self, ai_measure):
        """Rule 2 — pin with callout=dormer on right, no dormer face
        emitted for right. THIS is exactly the copy Howard specified:
        'possible dormer on the right slope; re-shoot'."""
        hints = ai_measure._derive_pin_gap_hints(
            annotations=self._annot(2, "right", callout="dormer"),
            walls=self._walls(["front", "back", "left", "right"]),
            dormers=[{"face": "left", "width_ft": 15}],
            orphaned_walls=[],
            empty_photos=[],
        )
        # This case triggers Rule 2 only (right wall exists so Rule 1
        # doesn't fire).
        kinds = {h["kind"] for h in hints}
        assert "missing_dormer_from_pin" in kinds
        dormer_hint = next(h for h in hints if h["kind"] == "missing_dormer_from_pin")
        assert dormer_hint["elevation"] == "right"
        assert "dormer" in dormer_hint["message"].lower()
        assert "right" in dormer_hint["message"].lower()
        assert "re-shoot" in dormer_hint["message"].lower()

    def test_pin_on_empty_photo(self, ai_measure):
        """Rule 3 — the photo's own extraction failed. Contractor
        needs to know THIS photo is the gap, not just the wall."""
        hints = ai_measure._derive_pin_gap_hints(
            annotations=self._annot(4, "left"),
            walls=self._walls(["front", "back", "right"]),
            dormers=[],
            orphaned_walls=["left"],   # implied by empty photo #4 being the only left photo
            empty_photos=[{"photo_idx": 4, "reason": "timed_out"}],
        )
        kinds = {h["kind"] for h in hints}
        # Both Rule 1 (orphaned) AND Rule 3 (empty photo) fire —
        # the frontend renders both; Rule 3 is per-photo specific.
        assert "orphaned_elevation_with_pin" in kinds
        assert "empty_photo_with_pin" in kinds
        empty_hint = next(h for h in hints if h["kind"] == "empty_photo_with_pin")
        assert 4 in empty_hint["source_photo_idxs"]

    def test_pin_on_measured_wall_no_hint(self, ai_measure):
        """The happy path — pin on a wall that DID extract. No hint,
        no noise."""
        hints = ai_measure._derive_pin_gap_hints(
            annotations=self._annot(0, "front"),
            walls=self._walls(["front", "back", "left", "right"]),
            dormers=[],
            orphaned_walls=[],
            empty_photos=[],
        )
        assert hints == []

    def test_dedupe_by_kind_and_elevation(self, ai_measure):
        """Six pins on the right elevation should produce ONE right-
        elevation hint (not six identical banners)."""
        multi = {
            "0": [{"elevation_label": "right", "callout": ""}],
            "1": [{"elevation_label": "right", "callout": ""}],
            "2": [{"elevation_label": "right", "callout": ""}],
            "3": [{"elevation_label": "right", "callout": ""}],
        }
        hints = ai_measure._derive_pin_gap_hints(
            annotations=multi,
            walls=self._walls(["front", "back", "left"]),
            dormers=[],
            orphaned_walls=["right"],
            empty_photos=[],
        )
        right_hints = [h for h in hints if h["elevation"] == "right"]
        assert len(right_hints) == 1
        # But all 4 source photos should be tracked.
        assert sorted(right_hints[0]["source_photo_idxs"]) == [0, 1, 2, 3]

    def test_stable_ordering(self, ai_measure):
        """Frontend polls repeatedly; hint list order must not jitter
        between polls or the UI will re-flow. Sorted by (kind, elev)."""
        annot = {
            "0": [
                {"elevation_label": "right", "callout": "dormer"},
                {"elevation_label": "back", "callout": ""},
            ],
        }
        hints_1 = ai_measure._derive_pin_gap_hints(
            annotations=annot,
            walls=self._walls(["front"]),
            dormers=[],
            orphaned_walls=["back", "left", "right"],
            empty_photos=[],
        )
        hints_2 = ai_measure._derive_pin_gap_hints(
            annotations=annot,
            walls=self._walls(["front"]),
            dormers=[],
            orphaned_walls=["back", "left", "right"],
            empty_photos=[],
        )
        assert [(h["kind"], h["elevation"]) for h in hints_1] == \
               [(h["kind"], h["elevation"]) for h in hints_2]

    def test_ignores_other_and_unknown_elevations(self, ai_measure):
        """Pin tagged `other`/`unknown` — we can't emit a re-shoot
        prompt for a non-cardinal elevation, so ignore."""
        annot = {
            "0": [
                {"elevation_label": "other", "callout": ""},
                {"elevation_label": "unknown", "callout": ""},
                {"elevation_label": "", "callout": ""},
            ],
        }
        hints = ai_measure._derive_pin_gap_hints(
            annotations=annot,
            walls=self._walls(["front"]),
            dormers=[],
            orphaned_walls=["back", "left", "right"],
            empty_photos=[],
        )
        assert hints == []


class TestRule4UnanchoredDormer:
    """Iter 79j.60 — Rule 4: any dormer whose width was derived
    without a scale anchor gets amber-flagged. This is the primary
    countermeasure against the 19/28 ft vs taped 15/15 drift Howard
    documented in the 2026-07-07 afternoon run."""

    def _walls(self, labels):
        return [{"label": lb} for lb in labels]

    def test_dormer_width_no_anchor_no_scale_ref(self, ai_measure):
        """The exact afternoon-run scenario: dormers report widths
        via `direct_single_reading` (no marker cited) AND no
        `_scale_refs` entry exists for the dormer's source photo."""
        dormers = [
            {"face": "left", "width_ft": 19, "width_source": "direct_single_reading",
             "width_reasoning": "estimated from vertical extent"},
            {"face": "right", "width_ft": 28, "width_source": "direct_single_reading",
             "width_reasoning": ""},
        ]
        hints = ai_measure._derive_pin_gap_hints(
            annotations={},
            walls=self._walls(["front", "back", "left", "right"]),
            dormers=dormers,
            orphaned_walls=[],
            empty_photos=[],
        )
        kinds = {(h["kind"], h["elevation"]) for h in hints}
        assert ("unanchored_dormer_width", "left") in kinds
        assert ("unanchored_dormer_width", "right") in kinds
        # Actionable copy — re-shoot elevation surfaced, drift range cited
        left = next(h for h in hints if h["elevation"] == "left")
        assert "19.0 ft" in left["message"]
        assert "reference marker" in left["message"].lower() or "wall_ref" in left["message"].lower() or "win_ref" in left["message"].lower()
        assert "25-90%" in left["message"]
        assert left["re_shoot_elevation"] == "left"

    def test_dormer_width_cited_anchor_no_flag(self, ai_measure):
        """When `width_reasoning` cites a WALL_REF / WIN_REF / any
        anchor keyword, we TRUST it — no amber flag. This is what a
        healthy graduated Red-House run looks like."""
        dormers = [{
            "face": "left", "width_ft": 15.5,
            "width_source": "direct_measurement",
            "width_reasoning": "aligned with the 180-inch WALL_REF bar on photo 2",
        }]
        hints = ai_measure._derive_pin_gap_hints(
            annotations={},
            walls=self._walls(["front", "back", "left", "right"]),
            dormers=dormers,
            orphaned_walls=[],
            empty_photos=[],
        )
        assert not any(h["kind"] == "unanchored_dormer_width" for h in hints)

    def test_dormer_with_scale_ref_on_source_photo_no_flag(self, ai_measure):
        """Even if width_reasoning doesn't cite the anchor by name,
        if the SOURCE PHOTO carries a `_scale_refs` entry we assume
        the AI silently used it — no flag."""
        dormers = [{
            "face": "left", "width_ft": 15.5,
            "width_source": "direct_single_reading",
            "width_reasoning": "",
            "source_photos": [2, 3],
        }]
        annotations = {
            "_scale_refs": {
                "2": {"inches": 180, "p1_x_norm": 0, "p1_y_norm": 0, "p2_x_norm": 1, "p2_y_norm": 0},
            },
        }
        hints = ai_measure._derive_pin_gap_hints(
            annotations=annotations,
            walls=self._walls(["front", "back", "left", "right"]),
            dormers=dormers,
            orphaned_walls=[],
            empty_photos=[],
        )
        assert not any(h["kind"] == "unanchored_dormer_width" for h in hints)

    def test_rule4_fires_without_any_annotations(self, ai_measure):
        """Contractor may not draw ANY pins — Rule 4 must still fire
        so unanchored widths never sneak through unflagged."""
        hints = ai_measure._derive_pin_gap_hints(
            annotations=None,
            walls=self._walls(["front", "back", "left", "right"]),
            dormers=[{"face": "left", "width_ft": 19, "width_source": "direct_single_reading"}],
            orphaned_walls=[],
            empty_photos=[],
        )
        assert any(h["kind"] == "unanchored_dormer_width" for h in hints)

    def test_rule4_no_width_no_flag(self, ai_measure):
        """A dormer with `width_ft` missing/zero can't be flagged
        for drift — the flag would be meaningless copy."""
        dormers = [{"face": "left", "width_source": "direct_single_reading"}]
        hints = ai_measure._derive_pin_gap_hints(
            annotations={},
            walls=self._walls(["front"]),
            dormers=dormers,
            orphaned_walls=[],
            empty_photos=[],
        )
        assert not any(h["kind"] == "unanchored_dormer_width" for h in hints)
