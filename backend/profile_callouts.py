"""Profile callout normalizer (Iter 78z).

Construction blueprints and AI vision passes return raw siding-profile
callout text (e.g. "LAP 4\"", "DUTCH LAP", "SHAKER", "B&B"). The catalog
SKU names are different and inconsistent across product lines, so we
need a translation layer.

This module owns the single source of truth for "raw text → canonical
profile family" mapping. It's used by:
  - routes/ai_measure.py   to interpret photo-based callouts
  - routes/ai_blueprint.py to interpret printed-plan callouts
  - the catalog mapper     to pick the right SKU for each line

Canonical profile families:
  "lap"          — horizontal lap siding (any width)
  "dutch_lap"    — horizontal dutch lap (notched profile)
  "shake"        — cedar shake / shaker / hand-split look
  "board_batten" — wide vertical board with batten strips
  "vertical"     — plain vertical (no batten)
  "nickel_gap"   — narrow V-groove vertical
  "stone"        — masonry watertable / wainscot (NOT siding)
  "brick"        — masonry brick (NOT siding)
  "stucco"       — stucco / EIFS (NOT siding)
  "unknown"      — text was present but couldn't be classified
  ""             — empty / not provided

Howard's directive (Iter 78z, 2026-02-13): mixed-material houses like
the Campbell job (lap on body + shaker on gables + B&B on dormers)
must produce SEPARATE quote lines per profile. This module enables
that classification.
"""
from __future__ import annotations
import re
from typing import Optional


# Each tuple: (regex pattern, canonical family). Order matters — first
# match wins, so put the more specific patterns first (e.g. "dutch lap"
# before bare "lap").
_PROFILE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # NOT-siding masonry — checked first so a "STONE WATERTABLE" callout
    # never accidentally maps to anything else.
    (re.compile(r"\b(stone|stonework|watertable|water\s*table)\b", re.I), "stone"),
    (re.compile(r"\bbrick\b", re.I), "brick"),
    (re.compile(r"\b(stucco|eifs)\b", re.I), "stucco"),

    # Shake / Shaker family
    # Iter 78z (2026-02-13) — Claude often returns "SHINGLES" instead of
    # "SHAKE/SHAKER" because that's how blueprints colloquially label
    # cedar shake panels (e.g. Campbell's left + right gables read
    # "SHINGLES" verbatim on the print). Treat them as shake.
    (re.compile(r"\b(shake|shaker|shingle|shingles|hand[\s-]?split|scallop|fish[\s-]?scale)\b", re.I), "shake"),

    # Board & Batten variants (B&B / BNB / batt + vertical context)
    (re.compile(r"\bboard\s*(?:and|&|\+|n)?\s*batten\b", re.I), "board_batten"),
    (re.compile(r"\bbnb\b", re.I), "board_batten"),
    (re.compile(r"\bb\s*&\s*b\b", re.I), "board_batten"),
    (re.compile(r"\bbb\b", re.I), "board_batten"),
    (re.compile(r"\bbatt(?:en)?(?:ed)?\b", re.I), "board_batten"),

    # Nickel Gap (vertical with tight V-groove)
    (re.compile(r"\bnickel\s*gap\b", re.I), "nickel_gap"),
    (re.compile(r"\bng\b", re.I), "nickel_gap"),

    # Plain vertical (no batten) — must come AFTER board_batten so B&B wins
    (re.compile(r"\bvertical\b", re.I), "vertical"),
    (re.compile(r"\bv/?\s*s(?:dg)?\b", re.I), "vertical"),  # V/S, V SDG

    # Dutch Lap — checked BEFORE plain "lap"
    (re.compile(r"\bdutch\s*lap\b", re.I), "dutch_lap"),
    (re.compile(r"\bdl\b", re.I), "dutch_lap"),
    (re.compile(r"\bd\s*4(?:\.5)?\"?\b", re.I), "dutch_lap"),  # "D4.5" / "D 4"
    (re.compile(r"\bd\s*5\"?\b", re.I), "dutch_lap"),

    # Horizontal Lap (plain "lap" or "clapboard")
    (re.compile(r"\b(clap(?:board)?|lap)\b", re.I), "lap"),

    # Just "vinyl" — assume horizontal lap (no profile hint)
    (re.compile(r"\bvinyl\b", re.I), "lap"),

    # Iter 78z (2026-02-13) — Generic "SIDING" callout. Construction
    # prints often label the wall body as just "SIDING" or "EXT SIDING"
    # without specifying the profile (Campbell's blueprint does this on
    # all 4 walls). Default to horizontal lap — the safe assumption
    # because ~80% of new builds in Howard's market are lap. Contractor
    # can override per-elevation when the visible photo says otherwise.
    (re.compile(r"\b(ext|exterior)?\s*siding\b", re.I), "lap"),
]


def classify_profile(callout_text: Optional[str]) -> str:
    """Map raw callout text to a canonical profile family.

    Returns one of: "lap", "dutch_lap", "shake", "board_batten",
    "vertical", "nickel_gap", "stone", "brick", "stucco", "unknown",
    or "" (empty input).
    """
    if not callout_text:
        return ""
    text = str(callout_text).strip()
    if not text:
        return ""
    for pattern, family in _PROFILE_PATTERNS:
        if pattern.search(text):
            return family
    return "unknown"


def is_non_siding_family(family: str) -> bool:
    """True for families that are NOT siding (masonry, stucco). These
    should NOT generate a siding line item in the catalog mapper, but
    they DO reduce the siding ft² on that elevation."""
    return family in {"stone", "brick", "stucco"}


def is_siding_family(family: str) -> bool:
    """True for canonical siding profiles (lap, shake, B&B, etc.).
    `unknown` returns False so an unclassifiable callout doesn't
    silently produce a wrong SKU line."""
    return family in {
        "lap", "dutch_lap", "shake", "board_batten",
        "vertical", "nickel_gap",
    }


# Human-readable label for UI badges / debug logs.
PROFILE_LABELS = {
    "lap":          "Lap",
    "dutch_lap":    "Dutch Lap",
    "shake":        "Shake",
    "board_batten": "Board & Batten",
    "vertical":     "Vertical",
    "nickel_gap":   "Nickel Gap",
    "stone":        "Stone",
    "brick":        "Brick",
    "stucco":       "Stucco",
    "unknown":      "Unknown profile",
    "":             "",
}


def label_for(family: str) -> str:
    return PROFILE_LABELS.get(family, family)


# Iter 78z — Per-elevation siding breakdown from Claude's walls[] output.
# This is the canonical structure consumed by the takeoff UI card and the
# catalog mapper that splits siding into per-profile quote lines.

def _safe_float(v, default=0.0):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return default


def breakdown_walls_by_profile(walls: list, default_body_profile: str = "lap") -> dict:
    """Aggregate Claude's per-wall callouts into a structured rollup.

    Returns a dict with two top-level keys:
        per_elevation: [{label, wall_body_sqft, wall_body_profile,
                         gable_sqft, gable_profile,
                         dormer_sqft, dormer_profile,
                         accents: [{location, profile, sqft}],
                         stone_sqft}, ...]
        per_profile_sqft: {profile_family: total_sqft}

    Conventions:
      - Wall body ft² = width × eave_height × (siding_pct / 100). Stone /
        masonry watertable is captured in stone_sqft separately so the
        contractor sees how much area is NOT siding.
      - Gable triangle ft² = 0.5 × width × gable_triangle_height_ft. Only
        when gable_triangle_height_ft > 0. Profile inherits from body
        when gable_profile_callout is empty.
      - Dormer ft² = Claude's dormer_face_sqft verbatim. Profile inherits
        from body when dormer_profile_callout is empty.
      - Accents are summed into per_profile_sqft but kept as separate
        rows in per_elevation so the UI can show their location.
      - default_body_profile is what we fall back to when Claude returns
        empty / unknown for wall_body_profile_callout. "lap" is the safe
        default (80% of new builds in Howard's market).
    """
    per_elevation = []
    per_profile = {}

    def _add(family: str, sqft: float):
        if sqft <= 0 or family in ("", "unknown") or is_non_siding_family(family):
            return
        per_profile[family] = per_profile.get(family, 0.0) + sqft

    for w in walls or []:
        label = str(w.get("label") or "").lower() or "unknown"
        width = _safe_float(w.get("width_ft"))
        eave_h = _safe_float(w.get("height_ft"))
        gable_h = _safe_float(w.get("gable_triangle_height_ft"))
        pct = _safe_float(w.get("siding_pct_this_wall"), 100.0)
        # Same fraction-vs-percent clamp as in ai_measure.py
        if 0 < pct < 1:
            pct *= 100.0
        if pct <= 0:
            pct = 100.0
        pct = min(pct, 100.0)

        # Wall body ft² (siding only — stone area excluded via pct)
        gross = width * eave_h
        wall_body_sqft = gross * (pct / 100.0)
        body_family = classify_profile(w.get("wall_body_profile_callout"))
        if not body_family or body_family == "unknown":
            body_family = default_body_profile
        _add(body_family, wall_body_sqft)

        # Stone area = gross × (1 - pct/100). Surfaced for traceability;
        # NEVER counted as siding.
        stone_sqft = gross * (1.0 - pct / 100.0)

        # Gable triangle
        gable_sqft = 0.0
        gable_family = ""
        if gable_h > 0 and width > 0:
            gable_sqft = 0.5 * width * gable_h
            gable_family = classify_profile(w.get("gable_profile_callout")) or body_family
            _add(gable_family, gable_sqft)

        # Dormer face
        dormer_sqft = _safe_float(w.get("dormer_face_sqft"))
        dormer_family = ""
        if dormer_sqft > 0:
            dormer_family = classify_profile(w.get("dormer_profile_callout")) or body_family
            _add(dormer_family, dormer_sqft)

        # Accents (B&B porch face, shake column wrap, etc.)
        accents = []
        for a in (w.get("accent_profiles") or []):
            a_sqft = _safe_float(a.get("approx_sqft"))
            if a_sqft <= 0:
                continue
            a_family = classify_profile(a.get("profile_callout"))
            if not a_family or a_family == "unknown":
                a_family = body_family
            accents.append({
                "location":  str(a.get("location") or "").strip(),
                "profile":   a_family,
                "callout":   a.get("profile_callout") or "",
                "sqft":      round(a_sqft, 1),
            })
            _add(a_family, a_sqft)

        per_elevation.append({
            "label":              label,
            "wall_body_sqft":     round(wall_body_sqft, 1),
            "wall_body_profile":  body_family,
            "wall_body_callout":  w.get("wall_body_profile_callout") or "",
            "gable_sqft":         round(gable_sqft, 1),
            "gable_profile":      gable_family,
            "gable_callout":      w.get("gable_profile_callout") or "",
            "dormer_sqft":        round(dormer_sqft, 1),
            "dormer_profile":     dormer_family,
            "dormer_callout":     w.get("dormer_profile_callout") or "",
            "accents":            accents,
            "stone_sqft":         round(stone_sqft, 1),
            "stone_callout":      w.get("stone_callout") or "",
        })

    # Round per_profile to 1 decimal for clean rendering
    per_profile_rounded = {fam: round(sq, 1) for fam, sq in per_profile.items()}

    return {
        "per_elevation":      per_elevation,
        "per_profile_sqft":   per_profile_rounded,
    }
