"""AI Photo Measure — Claude vision-based house measurement.

Contractor uploads 2–8 photos of the property from their phone. We base64-
encode each photo and send them all in one Claude Sonnet 4.5 vision call,
asking for raw WxH per wall and opening. We aggregate Claude's reply into
the same `measurements` dict shape that `/api/estimates/hover-import`
returns, so the existing HOVER preview modal on the frontend can render
the result without changes.

Accuracy notes (surface these in the UI):
  • Without a reference object (door, brick course, tape) AI vision is
    ±10–30% off. Contractors must verify before quoting.
  • The contractor may pass `reference_dim` (e.g., "front door = 80 in"
    or "house width = 36 ft") to anchor Claude's scale.
  • Best results: 4 elevation photos (front/back/left/right) + close-ups
    of any tricky openings.

Endpoint: POST /api/measure/ai-measure  (multipart/form-data)
Form fields:
  files:           one or more JPG/PNG/WEBP photos (max 8)
  reference_dim:   optional string, e.g. "front door = 80 inches"
  address:         optional, surfaces in Claude's reply as context
  kind:            one of "siding" | "windows" | "iss"  (default: siding)
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import time
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from emergentintegrations.llm.chat import (
    ImageContent,
    LlmChat,
    UserMessage,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image

from deps import get_current_user
from db import db
from routes.hover import _build_lines  # reuse the same measurement→line mapper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/measure", tags=["measure"])

ACCEPTED_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
# Iter 57b: bumped from 8 → 9 so contractors can add the free Google
# Maps aerial alongside the 8 standard elevation shots from the Guided
# Capture wizard. The aerial is a small ~400 KB tile; total payload
# stays under Claude Opus's 100 MB request limit by a wide margin.
MAX_FILES = 9
MAX_BYTES_PER_FILE = 12 * 1024 * 1024  # 12 MB pre-base64 (Iter 56b: bumped from 8 MB to accommodate modern phone photos + annotated re-renders)
# Iter 49: bumped from claude-sonnet-4-5-20250929 to claude-opus-4-5
# at Howard's request — ~3× cost per measure but materially better at
# distinguishing dormers / gables / 2nd-story walls on residential
# exteriors. The image schema and `_aggregate_to_hover_shape` math
# are unchanged.
MODEL_NAME = "claude-opus-4-5-20251101"

# Iter 79j.15 — A/B model registry. The main AI-measure Claude call can
# now run against any of these models per-run (see `model_choice`
# parameter on POST /measure/ai-measure). Contractors flip between them
# from the AI Measure modal to compare accuracy + cost on the same
# house. The default stays Opus 4.5 until we have field data proving a
# swap is worth it. The provider string maps to emergentintegrations'
# `.with_model(provider, model_name)` call.
_MODEL_CHOICES: dict[str, tuple[str, str]] = {
    # key                    -> (provider,   model_name)
    "claude-opus-4-5":         ("anthropic", "claude-opus-4-5-20251101"),
    "claude-opus-4-8":         ("anthropic", "claude-opus-4-8"),
    "claude-sonnet-4-6":       ("anthropic", "claude-sonnet-4-6"),
    "claude-fable-5":          ("anthropic", "claude-fable-5"),
    "gemini-3.5-flash":        ("gemini",    "gemini-3.5-flash"),
    "gemini-3.1-pro":          ("gemini",    "gemini-3.1-pro-preview"),
    "gpt-5.5":                 ("openai",    "gpt-5.5"),
    "gpt-5.4":                 ("openai",    "gpt-5.4"),
}
_DEFAULT_MODEL_KEY = "claude-opus-4-5"


def _resolve_model(choice: str | None) -> tuple[str, str, str]:
    """Return (key, provider, model_name) for the given contractor
    choice, falling back to the default. Unknown keys log a warning
    but don't fail the run — we still want a measurement even if the
    contractor typed something weird into a URL param."""
    key = (choice or _DEFAULT_MODEL_KEY).strip()
    if key not in _MODEL_CHOICES:
        logger.warning("Unknown ai-measure model_choice %r, falling back to %s", key, _DEFAULT_MODEL_KEY)
        key = _DEFAULT_MODEL_KEY
    provider, model_name = _MODEL_CHOICES[key]
    return key, provider, model_name


def _pick_llm_api_key(provider: str) -> tuple[str | None, str]:
    """Iter 79j.44 — DIRECT-KEY ROUTING EXPLICITLY DISABLED.

    Every provider now uses the Emergent Universal Key via the LiteLLM
    proxy. The direct-Anthropic bypass introduced in Iter 79j.42 is
    turned off until a standalone `api.anthropic.com` test call is
    proven green in isolation. If `ANTHROPIC_API_KEY` is present on
    the .env, this function IGNORES it and logs a warning so the
    operator knows the direct path did not activate.

    Returns (api_key, source). `source` is always `"emergent_proxy"`.
    `api_key` may be None if `EMERGENT_LLM_KEY` is missing — the
    caller raises a 500 in that case.
    """
    if provider == "anthropic":
        direct = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if direct:
            logger.warning(
                "[AI_MEASURE key-routing] ANTHROPIC_API_KEY is set but direct-key "
                "routing is currently disabled. Using EMERGENT_LLM_KEY (proxy) instead."
            )
    return (os.environ.get("EMERGENT_LLM_KEY") or None), "emergent_proxy"


# Startup log — operators can grep `AI_MEASURE key-routing` to confirm
# which key each provider will use without decoding the .env by hand.
# Iter 79j.44 — Direct-key routing is DISABLED regardless of .env, so
# the summary is now a single hard statement.
_LLM_ROUTING_SUMMARY = (
    "anthropic=EMERGENT_LLM_KEY (proxy) [direct-key DISABLED], "
    "gemini/openai=EMERGENT_LLM_KEY (proxy)"
)
logger.info("[AI_MEASURE key-routing] %s", _LLM_ROUTING_SUMMARY)


def _compress_for_claude(img_bytes: bytes, max_raw_bytes: int = 5_500_000) -> bytes:
    """Ensure a single image fits under Anthropic's 10 MB base64 cap.
    Anthropic measures the base64-encoded payload (~1.33× raw), so
    targeting raw bytes < ~5.5 MB keeps base64 < ~7.3 MB with headroom.

    Strategy: JPEG-encode at q=88; if still too large iteratively
    downscale by 0.85× and drop quality. Falls back to original on
    PIL failure. Skips small JPEGs untouched.
    """
    if len(img_bytes) <= max_raw_bytes and img_bytes[:3] == b"\xff\xd8\xff":
        return img_bytes
    try:
        with Image.open(io.BytesIO(img_bytes)) as im:
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            qualities = [88, 85, 78, 70, 60]
            scales = [1.0, 0.85, 0.72, 0.6, 0.5, 0.42]
            data = img_bytes
            for scale in scales:
                if scale < 1.0:
                    new_w = max(800, int(im.width * scale))
                    new_h = max(800, int(im.height * scale))
                    work = im.resize((new_w, new_h), Image.LANCZOS)
                else:
                    work = im
                for q in qualities:
                    buf = io.BytesIO()
                    work.save(buf, format="JPEG", quality=q, optimize=True)
                    data = buf.getvalue()
                    if len(data) <= max_raw_bytes:
                        return data
            return data
    except Exception:
        logger.exception("[ai-measure] image compression failed; sending original")
        return img_bytes


def _shrink_for_phase_a(img_bytes: bytes, max_dim: int = 1600, jpeg_q: int = 80) -> tuple[bytes, dict]:
    """Iter 79j.50 — Aggressive per-photo downscale for Phase A vision.

    Empirical finding (2026-02-28): the LiteLLM proxy serializes
    concurrent `LlmChat.send_message` calls when payloads are large
    (documented in prompts.md Iter79j.50). Small payloads parallelize
    fine. Attack the root cause by shrinking each photo BEFORE dispatch:
    max long-edge 1600px, JPEG quality 80. Contractor phone photos are
    typically 3000-4500px and 3-5MB → this gets them under ~400KB.

    The reconciler (Phase B) is text-only and unaffected. `_compress_for_claude`
    (5.5MB cap) is retained for other flows that need higher fidelity.

    Returns (shrunk_bytes, stats) where stats has original/final size +
    dimensions for diagnostic logging.
    """
    stats = {"original_bytes": len(img_bytes)}
    try:
        with Image.open(io.BytesIO(img_bytes)) as im:
            stats["original_dim"] = f"{im.width}x{im.height}"
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            longest = max(im.width, im.height)
            if longest > max_dim:
                scale = max_dim / longest
                new_w = max(1, int(im.width * scale))
                new_h = max(1, int(im.height * scale))
                im = im.resize((new_w, new_h), Image.LANCZOS)
            stats["final_dim"] = f"{im.width}x{im.height}"
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=jpeg_q, optimize=True)
            data = buf.getvalue()
            stats["final_bytes"] = len(data)
            stats["ratio"] = round(stats["final_bytes"] / max(1, stats["original_bytes"]), 3)
            return data, stats
    except Exception:
        logger.exception("[ai-measure] shrink-for-phase-a failed; using compress fallback")
        fallback = _compress_for_claude(img_bytes)
        stats["final_bytes"] = len(fallback)
        stats["final_dim"] = "compress-fallback"
        stats["ratio"] = round(stats["final_bytes"] / max(1, stats["original_bytes"]), 3)
        return fallback, stats



SYSTEM_PROMPT = """\
You are a residential exterior measurement assistant for a vinyl-siding and
window contractor. The user will upload 2–8 photos of a house. Your job is
to estimate the rough exterior measurements needed for a siding + windows
quote. You MUST return JSON only — no prose, no markdown fences.

Schema:
{
  "scale_confidence": "high" | "medium" | "low",
  "reference_used": "<short description of the reference you anchored scale on, or 'none'>",
  "story_count": 1 | 1.5 | 2 | 2.5 | 3,
  "story_count_reasoning": "<1 sentence — what visual cue told you the story count>",
  "avg_wall_height_ft": number,           // average EAVE height (floor to where the roof starts), NOT roof peak
  "siding_coverage_pct": number,          // 0-100, % of gross wall area actually clad in siding (NOT brick, stone, etc.)
  // Iter 79j.26 — roof-type classification. Drives the 3D viewer and
  // the estimator's siding takeoff:
  //   gable              → 2-plane pitched roof, gable triangles at both ends
  //   hip                → 4-plane pitched roof, NO gable triangles (all 4 walls end flat at eave)
  //   gable-shed-dormer  → gable roof + a shed dormer on one slope with a vertical
  //                        face wall that carries additional siding area + windows
  // Classification cues:
  //   • Gable ends visible (triangular wall peaks above the eave line)         → "gable"
  //   • Roof slopes downward on ALL FOUR sides, no triangular walls anywhere   → "hip"
  //   • A rectangular vertical wall (usually with windows) rises ABOVE the
  //     main eave line and steps back INTO the roof slope                      → "gable-shed-dormer"
  // Set roof_type_confidence to 0.0–1.0. Below 0.8 the app defaults to
  // "gable" and flags this field as estimated for the contractor to review.
  "roof_type": "gable" | "hip" | "gable-shed-dormer",
  "roof_type_confidence": number,         // 0.0-1.0
  "roof_type_reasoning": "<1 sentence — what visual cue drove your call>",
  // Iter 79j.28 — Dominant flat colors per material family, sampled
  // from the photos. Return a 6-digit hex (#RRGGBB) for each. Sample
  // the AVERAGE color of a large clean patch — ignore shadows, glare,
  // and small trim/accent details. These populate the 3D viewer walls,
  // trim, roof, and doors. Leave any field null if no clean sample is
  // possible.
  "dominant_colors": {
     "siding_hex": "#RRGGBB" | null,   // main field siding color
     "trim_hex": "#RRGGBB" | null,     // window/door trim, corners, fascia
     "roof_hex": "#RRGGBB" | null,     // shingles or metal
     "door_hex": "#RRGGBB" | null      // primary entry door — often distinct from siding
  },
  // Fill only when roof_type === "gable-shed-dormer". `face` = which
  // slope carries the dormer, `width_ft` = its X-extent across the roof,
  // `knee_wall_height_ft` = how tall the vertical face wall stands above
  // where the main roof would be at that Z position, `offset_x_ft` =
  // horizontal offset from the wall center (0 = centered).
  "dormers": [
    // Iter 79j.41 — ARRAY, one entry per PHYSICAL dormer. A house may
    // have shed dormers on BOTH front and rear slopes, or gable
    // dormers on each side of a hip roof — never collapse them.
    {"face": "front" | "rear" | "left" | "right",
     "width_ft": number,
     "knee_wall_height_ft": number,
     "offset_x_ft": number}
  ],
  // Iter 79j.41 — legacy singular field kept for back-compat with
  // older parsers. If you emit `dormers[]` above, MIRROR the first
  // entry here or leave null. New code should ignore this field.
  "dormer": {"face": "front" | "rear", "width_ft": number, "knee_wall_height_ft": number, "offset_x_ft": number} | null,
  // Iter 79j.36 — TOP-LEVEL RECONCILIATION NOTES. One short sentence
  // per aggregate field explaining how you got there when a value
  // could reasonably vary between photos. The contractor uses these
  // to diagnose whether variance between runs comes from Claude
  // reading the same photos differently (a model problem) or from
  // reconciling multiple readings inconsistently (a merge problem).
  // Leave a value empty if it wasn't reconciled from multiple sources.
  "_reconciliation_notes": {
    "avg_wall_height_ft": "<e.g. 'averaged 3 valid observations 8.5, 8.7, 9.0 → 8.7 → snapped to 9' | ''>",
    "roof_type":          "<e.g. 'gable-shed-dormer — photo 0 showed 1 dormer, photos 2 and 3 confirmed from side' | ''>",
    "dormer":             "<e.g. 'width read from photo 0 bbox → 12 ft, offset centered' | ''>",
    "story_count":        "<e.g. 'photos 0 and 1 both showed 2 rows of windows → 2 stories' | ''>",
    "siding_coverage_pct": "<e.g. 'brick wainscot on front and left reduces field siding by ~15% overall' | ''>",
    "dominant_colors":    "<e.g. 'sampled from photo 0 sunlit patch; other photos in shade' | ''>"
  },
  "photos": [
    // ONE entry per photo IN THE EXACT ORDER they were sent to you.
    // photos[0] = the first attached image, photos[1] = the second, etc.
    // Use this to auto-tag elevations (saves the contractor from manually
    // labelling each thumb in the UI).
    {"index": number,                     // 0-based index matching the order the photos were attached
     "elevation": "front" | "front-left" | "left" | "rear-left" | "back" | "rear-right" | "right" | "front-right" | "aerial" | "detail" | "other",
     // 4 cardinals = a centered shot of that wall. 4 corners = a 45° corner
     // shot showing TWO walls. Tag corners as their specific corner name
     // (front-left, rear-left, etc.) so the contractor's photo grid
     // shows distinct badges instead of "FRONT, FRONT, FRONT".
     "elevation_confidence": number,      // 0-100, how confident are you in the elevation tag
     "elevation_reasoning": "<1 short sentence — what told you which side this is>",
     // Iter 79j.36 — PER-PHOTO RAW OBSERVATIONS. Fill these fields
     // with what YOU SAW IN THIS SINGLE PHOTO before merging across
     // photos. The contractor uses them to diagnose whether variance
     // in the final result is a detection problem (different photos
     // disagree) or a reconciliation problem (photos agree but the
     // merged number drifts). Leave a number null (not 0) if the
     // measurement isn't visible in this photo — 0 means "measured
     // and it truly is 0". Leave arrays [] if nothing to report.
     "walls_visible": ["front" | "back" | "left" | "right"],   // which of walls[] labels are captured in this photo (a corner shot sees 2)
     "eave_height_ft_observed": number | null,                  // eave height as measured from THIS photo, null if not measurable
     "eave_reasoning": "<1 short sentence — HOW you measured this photo's eave (e.g. 'counted 12 lap courses × 8.5 in exposure = 8.5 ft')>",
     "pitch_ratio_observed": "<e.g. '6/12' | '8/12'>" | null,  // pitch estimate from THIS photo if a gable is visible; else null
     "gable_triangle_height_ft_observed": number | null,        // 0 if this photo shows an eave-only wall; null if not visible; >0 if a gable is visible in THIS photo
     "dormers_observed_count": number,                          // count of dormers visible in THIS photo (0 if none)
     "openings_this_photo": [                                   // openings VISIBLE IN THIS PHOTO (bbox coords are pixel-space of the compressed image we sent you)
       {"opening_id": "<stable id you assign, e.g. 'front-w1' — reuse the SAME id on any matching entry in the top-level openings[] array so we can trace provenance>",
        "type": "window" | "entry_door" | "patio_door" | "garage_door" | "vent" | "other",
        "width_in": number,
        "height_in": number,
        "bbox": [x, y, w, h]}                                    // pixel bbox in this photo — omit if you can't localize
     ],
     "notes": "<optional: anything unusual about this photo (obstruction, corner shot, telephoto compression, lighting, etc.)>"
    }
  ],
  "walls": [
    {"label": "front" | "back" | "left" | "right" | "other",
     "width_ft": number,
     "height_ft": number,                 // EAVE height ONLY — measure from floor up to the soffit/gutter line. NEVER include the gable triangle, NEVER include a dormer.
     "gable_triangle_height_ft": number,  // 0 if this wall ends in an eave; >0 ONLY if this wall is a gable-end (you can see the triangular peak above the eave). Triangle area is auto-computed as 0.5 × width × this value.
     "dormer_face_sqft": number,          // 0 unless a true dormer (small box poking out of the roof) is on this elevation. Estimate the visible vertical face area in ft² — typically 20-60 ft² each.
     "siding_pct_this_wall": number,      // INTEGER 0-100 (percent), NOT a fraction. Use 85 to mean 85% siding — NEVER 0.85. Siding only, not brick / garage door / etc.
     // Iter 79j.36 — RECONCILIATION PROVENANCE. Even though we ask
     // for one merged number here, tell us how you got it: which
     // photos contributed, what each one read, and how you combined
     // them. When 3 runs on the same house return eave heights of
     // 7, 8.5, and 12 ft, this trace tells the contractor whether
     // the photos disagreed (detection failure) or you merged
     // inconsistently (reconciliation failure).
     "_source_photo_indices": [number],       // photo indices you drew this wall's dimensions from (e.g. [0, 3])
     "_per_photo_readings": [                  // one row per contributing photo — what each photo read BEFORE merging
       {"photo_idx": number,
        "eave_ft":  number | null,
        "gable_triangle_ft": number | null,
        "notes": "<optional per-photo note (e.g. 'front-right corner — foreshortening'>"}
     ],
     "_reconciliation_note": "<short sentence: e.g. 'averaged 2 readings 8.5 and 8.7 → 8.6, snapped to 9' or 'photo 0 read 12 ft but discarded — aerial view compresses foreshortening'>",
     // Iter 78z — Profile callouts per elevation. Capture the raw text or
     // visible siding pattern so the catalog mapper can split LAP / SHAKE /
     // B&B / DUTCH LAP into SEPARATE quote lines. Without these, mixed
     // material houses (lap on body + shake on gable + B&B on dormer)
     // collapse into a single inflated lap number. Howard's Campbell
     // house had all 3 profiles and we missed shake + B&B entirely.
     "wall_body_profile_callout": "<raw text from photo IF visible (e.g. 'LAP 4\"', 'DUTCH LAP', 'VINYL'); OR the pattern you can see ('horizontal lap', 'dutch lap', 'board and batten', 'shake', 'nickel gap', 'vertical'); OR empty if you can't tell>",
     "gable_profile_callout": "<MANDATORY when gable_triangle_height_ft > 0. CRITICAL: gables OFTEN carry a DIFFERENT profile than the wall body — most commonly SHAKE (cedar shake / scallop / fishscale) or BOARD AND BATTEN (vertical battens) for visual accent. Even when the gable LOOKS like it might match the body, look CAREFULLY for: scalloped bottom edges, vertical seams between panels, staggered courses, decorative cuts. If you see ANY visual difference from the body, call it out — 'shake', 'board and batten', 'vertical', 'fishscale', etc. ONLY leave empty if you can clearly see the EXACT same horizontal lap pattern continuing into the triangle without interruption.>",
     "dormer_profile_callout": "<MANDATORY when dormer_face_sqft > 0. Same logic as gable_profile_callout — dormers commonly carry SHAKE / BOARD AND BATTEN as an accent. Look for vertical battens, scalloped edges, or staggered cedar courses. Only leave empty when the dormer clearly continues the body's exact horizontal lap.>",
     // Iter 78z+ — ACCENT PANELS. A single wall can carry SMALL accent
     // areas with a different profile from the body — easy to miss
     // because they don't fit the "body / gable / dormer" buckets.
     // Examples seen on Howard's jobs: B&B on a porch face, shake on
     // column wraps, vertical siding on a bay-window cheek, fish-scale
     // on an entry gable above the porch. Capture every accent you
     // can see on THIS wall in the photo. Leave [] if uniform.
     "accent_profiles": [
       {"location": "<short description, e.g. 'porch face', 'column wrap', 'bay window cheek', 'entry gable', 'kneewall'>",
        "profile_callout": "<raw text or visible pattern (e.g. 'B&B', 'BOARD AND BATTEN', 'SHAKE', 'VERTICAL')>",
        "approx_sqft": number}
     ],
     "confidence": number,                // 0-100, how confident are you in THIS wall's measurements. <50 = barely visible / inferred. 50-79 = visible but obstructed or angled. 80-100 = clear straight-on shot with reference.
     "confidence_reasoning": "<1 short sentence — what reduces or supports confidence on THIS wall>"
    }
  ],
  // Iter 79j.32 — REQUIRED classification: EVERY trimmed penetration
  // (window, entry door, patio door, garage door, large vent) MUST be
  // emitted as a row in `openings[]`. Never bury a door or window in
  // the masked/stone/siding_pct math — openings drive J-channel and
  // surround trim takeoff downstream, and missing them under-quotes
  // the job. Garage doors especially: a single 16 ft double garage
  // door is ~112 ft² AND ~40 lf of J-channel — always emit it here
  // with type=garage_door, never fold it into siding_pct_this_wall.
  "openings": [
    {"type": "window" | "entry_door" | "patio_door" | "garage_door" | "vent" | "other",
     "style": "Double Hung" | "Single Hung" | "Casement" | "Twin Casement" | "Awning" | "Hopper" | "2-Lite Slider" | "3-Lite Slider" | "Picture" | "Twin Double Hung" | "Twin Single Hung" | "Triple Double Hung" | "Bay Window" | "Bow Window" | "Half-Round" | "Quarter-Round" | "Arch" | "Octagon" | "Hexagon" | "Garden Window" | "Other Shape" | "",
     "style_confidence": number,         // 0-100 — required when `style` is filled
     "width_in": number, "height_in": number, "wall": "front"|"back"|"left"|"right"|"other",
     // Iter 57n — per-opening photo location. Helps us draw labeled
     // arrows on the photo AND place each opening at its TRUE
     // x-position on the 2D wall diagram instead of guessing.
     "photo_idx": number,                // 0-based index of the photo this opening is visible in (matching the order you were given). If you can't pinpoint, omit.
     "bbox": {"x": number, "y": number, "w": number, "h": number},  // normalized 0.0–1.0 bounding box of the opening on photo_idx. Origin top-left. Omit if you're not confident enough to draw the box.
     // Iter 79j.27 — dormer classification. Set to true ONLY when the
     // opening sits ABOVE the main eave line (on a shed-dormer face,
     // gable-triangle, or upper cross-gable). These openings belong to
     // the dormer face wall — their siding-cutout area is deducted from
     // dormer_face_sqft, not from the main wall, and they anchor the
     // dormer width. When roof_type is not "gable-shed-dormer", leave
     // this field false or omit it.
     "on_dormer": boolean,
     // Iter 79j.36 — Opening provenance. Reuse the same `opening_id`
     // string you assigned in photos[i].openings_this_photo so the
     // debug view can hyperlink final openings back to the photo(s)
     // they were extracted from.
     "opening_id": "<optional stable id — matches photos[i].openings_this_photo[].opening_id>",
     "_source_photo_indices": [number],   // photo indices this opening was seen in (usually 1, sometimes 2 on corner shots)
     "_reconciliation_note": "<optional — only fill when you merged multiple photo readings or discarded some (e.g. 'photos 0 and 3 both showed this window at 36×60; consistent — no adjustment')>"
    }
  ],
  "openings_schedule": [
    // GROUPED roll-up of `openings` above — collapses duplicate sizes
    // into a single row per (elevation × type × size × style). Lets the
    // contractor verify counts at a glance ("4 × 36×60 Double Hung
    // windows on front" is easier to spot-check than 4 individual entries).
    {"elevation": "front" | "back" | "left" | "right" | "other",
     "type": "window" | "entry_door" | "patio_door" | "garage_door" | "vent" | "other",
     "style": "Double Hung" | "Casement" | "Picture" | etc. | "",  // SAME set as `openings[].style` above
     "width_in": number, "height_in": number,
     "count": number,                     // how many of this size on this elevation
     "size_label": "<e.g. '36\\"×60\\"' or 'Patio 72\\"×80\\"'>",
     // Iter 57n — array of {photo_idx, bbox} entries — ONE per
     // physical opening in this row. Length must equal `count` when
     // you're confident. Omit individual entries you can't pinpoint.
     "locations": [{"photo_idx": number, "bbox": {"x": number, "y": number, "w": number, "h": number}}]
    }
  ],
  "eaves_lf": number,          // sum of horizontal soffit/gutter run, linear feet
  "rakes_lf": number,          // sum of sloped roof edges, linear feet (= the rake legs of every gable triangle)
  "starter_lf": number,        // linear feet of starter strip at the base of the siding (typically ≈ eaves_lf for a basic 1-story; can differ on porches, walk-outs, or multi-section homes)
  "outside_corner_lf": number, // linear feet of OUTSIDE corner posts visible across all elevations (typically 4 corners × wall height on a simple rectangular house)
  "inside_corner_lf": number,  // linear feet of INSIDE corner posts (L-shaped wing additions, dormers, returns — often 0 for a basic rectangle)
  "missing_elevations": ["front" | "back" | "left" | "right"],  // any elevations NOT visible in any photo
  "double_count_check": "<1 sentence: did you cross-reference openings/walls visible from multiple angles to avoid double-counting? E.g. 'Front-right corner window is the same window seen in photo #2's left view — counted once.'>",
  "notes": "<1-2 sentences flagging anything the contractor should verify>"
}

CRITICAL accuracy rules (read every time):

0a. PRE-AI PHOTO ANNOTATIONS (highest-priority signal):
   The user may have added overlays to the photos BEFORE you saw them.
   When present, treat them as AUTHORITATIVE — they override anything
   you'd otherwise infer from pixels:

   • PURPLE "ELEVATION" badge top-left → photo is that exact wall
   • RED line + "WALL REF = N in" → known scale for whole-wall geometry; anchor wall measurements to it
   • BLUE line + "WIN REF = N in" → known scale specifically across a window edge (Iter 57k); use it as a TIGHTER per-window calibration for ALL window measurements on that photo. Whole-wall measurements still anchor to the wall ref; openings (windows, doors) should be sized using the blue WIN REF when it's present (±5% accuracy instead of ±15%).
   • GREEN "TARGET HOUSE" rectangle → measure only what's inside it (aerial)
   • RED hatched zone marked "NO SIDING" → exclude that area from siding %
   • YELLOW circle pin + brown badge with a style abbreviation
     ("DH", "CA", "PIC", "BAY", etc.) → CONTRACTOR-TAGGED WINDOW STYLE.
     Each yellow pin marks ONE window. The brown badge tells you the
     EXACT style (decoded: DH=Double Hung, SH=Single Hung, CA=Casement,
     2CA=Twin Casement, AW=Awning, HP=Hopper, 2SL=2-Lite Slider,
     3SL=3-Lite Slider, PIC=Picture, 2DH=Twin Double Hung, 2SH=Twin
     Single Hung, 3DH=Triple Double Hung, BAY=Bay Window, BOW=Bow
     Window, 1/2=Half-Round, 1/4=Quarter-Round, ARC=Arch, OCT=Octagon,
     HEX=Hexagon, GDN=Garden Window, OTH=Other Shape). Use the tagged
     STYLE as ground truth (style_confidence=100). YOU still measure
     width_in and height_in from the photo using your scale reference
     — the contractor is locking only the operation style, not the
     size. Add untagged windows you also see (with normal confidence).
     Never demote a tagged window's style — contractor's eyes beat
     a JPEG.


   The contractor may have marked up some photos BEFORE sending them.
   Look for these visual marks — they are ground truth, NOT guesses:
   • Purple corner badge "FRONT/BACK/LEFT/RIGHT ELEVATION" — this is the
     authoritative elevation tag for that photo. Use it to label the
     `walls[]` entry. If a badge says "FRONT ELEVATION", the wall in
     that photo IS the front wall — do not relabel it as "other".
   • Purple corner badge "AERIAL ELEVATION" — this is a top-down
     satellite view of the property from Esri World Imagery. There is
     a RED CROSSHAIR + RING in the exact center of the image with a
     "TARGET" label — that ring marks the geocoded address. ⚠ The
     geocoder often misses on rural / multi-building lots, so look for
     an OVERRIDE: a GREEN RECTANGLE labeled "TARGET HOUSE". If a green
     "TARGET HOUSE" box is present, IT IS AUTHORITATIVE — ignore the
     red auto-crosshair and measure ONLY the structure INSIDE the green
     box. Other buildings in frame — even adjacent ones 1–2 ft away
     (common in city lots) — are NEIGHBORS, IGNORE them entirely. If
     only the red crosshair is present, use it as your best guess. Any
     other houses visible in the frame are NEIGHBORS — IGNORE them. Use this aerial ONLY to measure the roof
     outline of the targeted structure: `eaves_lf` (total horizontal
     roof edges) and `rakes_lf` (total sloped gable-edge legs). DO NOT
     use it for wall heights, story count, openings, or siding %.
     Those must come from the ground-level elevation photos.
   • EAVES vs RAKES — IMPORTANT (Iter 57p): the "eave" is the
     HORIZONTAL roof edge running parallel to the ground (where the
     gutter hangs). The "rake" is the SLOPED roof edge climbing the
     side of a gable. ONLY set `eaves_lf > 0` when you can DIRECTLY
     observe a horizontal roof edge in the supplied photos (either
     from an aerial, OR from a ground photo that frames the soffit
     line). If every ground photo shows only the gable-end view (you
     see rakes but no horizontal eave line), set `eaves_lf = 0` and
     add "eaves not visible — verify in field" to `notes`. DO NOT
     infer/guess eave length from front-wall width when no eave is
     observed — that would falsely produce gutter line items on a
     side-elevation-only quote.
   • Red line with red endpoints + red label like 'WALL REF = 80"' — this is
     a contractor-confirmed WALL scale anchor. The red line spans a real-world
     distance of exactly that many inches in the photo. Use it to lock
     scale for whole-wall geometry (widths, heights, eave-to-ground) on
     that ENTIRE photo with high confidence. Set
     scale_confidence to "high" and reference_used to "contractor red-line ref".
   • Blue line with blue endpoints + blue label like 'WIN REF = 36"' — this
     is a contractor-confirmed WINDOW scale anchor (Iter 57k). The blue
     line spans a real-world window edge of exactly that many inches.
     When present, use it as the AUTHORITATIVE scale for ALL window/door
     measurements on that photo (width_in, height_in of every opening).
     Window sizes anchored to the blue WIN REF should land within ±5% of
     real values — far tighter than estimating from the red wall ref.
     The wall ref still governs the rest of the geometry; the two refs
     are complementary, not exclusive.
   • Colored hatched zones with a black label like "NO SIDING · Brick"
     or "NO SIDING · Stone" — masonry areas that are NOT clad in siding.
     They must be EXCLUDED from siding_pct_this_wall calculations for
     the wall they appear on.
     Example: a wall is 32×9 = 288 ft² gross, with a "NO SIDING · Brick"
     hatched zone covering the lower 3 ft (≈96 ft²) → the remaining
     siding is 192 ft² → siding_pct_this_wall = round(192 / 288 * 100) = 67.
     NOTE (Iter 79j.32): A "NO SIDING · Garage door" or "NO SIDING · Entry
     door" annotation, if drawn, is a HINT that a door exists at that
     location — but doors are OPENINGS, not masked masonry. Emit the
     door as an entry in `openings[]` with the correct type
     (garage_door / entry_door / patio_door) and DO NOT reduce
     siding_pct_this_wall for it. Only genuine masonry (brick, stone,
     stucco, CMU) reduces siding_pct_this_wall.
   Trust the annotations OVER your own visual judgment of the same photo.
   If a photo has a red ref line you must use it; if it has a NO SIDING
   zone you must subtract it. These were placed deliberately by the
   contractor — they know the house.

0. ONLY COUNT WHAT YOU SEE. If the contractor uploaded 2 photos (e.g. side
   + back), do NOT mirror-extrapolate the front or other side. Return walls
   ONLY for the elevations clearly visible in the supplied photos. In notes
   say which elevations are MISSING so the contractor knows to add them.
   Never inflate `walls[]` by guessing unseen sides.

1. SCALE: If the contractor provided ANY reference dimension (door width,
   wall width, garage height, brick course), anchor scale to it and set
   scale_confidence to "high". When you compute wall area, use the
   contractor-provided width VERBATIM — do not round it.

2. STORY COUNT vs WALL HEIGHT — read carefully, this is the #1 source
   of inflated quotes:
   • "Story count" = number of FULL floors of rectangular wall, floor to
     the eave line where the roof starts. A gable peak is NOT a story.
     A dormer is NOT a story.
   • `height_ft` on each wall is the EAVE height, NOT the roof peak.
     If you see a triangular gable end on the back of the house, the
     wall is STILL 1-story tall (e.g. 9 ft); the triangle on top goes
     into `gable_triangle_height_ft`, NOT height_ft.
   • A dormer is a small box-shaped projection out of the roof slope,
     usually with one window and 2-4 ft of vertical face. A dormer DOES
     NOT change the underlying wall height. Record dormer face area in
     `dormer_face_sqft` on the elevation the dormer faces.
   • Cues that signal a TRUE second story (not a dormer / not a gable):
       - Continuous horizontal row of windows ABOVE the first-floor windows,
         spanning most of the wall width
       - The eave line itself is high (~18 ft) — you can see the soffit
         well above the first-floor window heads
       - The 2nd floor windows are the same size as the 1st floor windows
   • Cues that mean it's a DORMER (not a 2nd story):
       - Only 1 or 2 small windows poking out of the roof slope
       - The roof slope is clearly visible on either side of the window box
       - The window is set back from the main wall face
   • Cues that mean it's a GABLE (not a 2nd story):
       - The wall ends in a triangle that meets a peak
       - There are NO windows above the eave line (or only a single
         small vent/gable window)
   Default story heights:
     1 story:    9 ft eave height
     1.5 story: 12 ft (with kneewall) — used for Cape Cod / story-and-a-half
     2 story:  18 ft
   Use these ONLY when the photos clearly show that story count. If
   uncertain between 1-story-with-gable and true 2-story, ALWAYS bias
   to 1-story-with-gable and flag it in notes.

3. GABLE TRIANGLES vs WALL HEIGHT: When a wall is a gable-end (you can
   see the triangle), the rectangular wall area is `width × eave_height`
   and the triangle area is auto-computed downstream as
   `0.5 × width × gable_triangle_height`. NEVER bake the triangle into
   `height_ft`. Typical residential gable_triangle_height_ft is 4-8 ft
   for a 6/12 to 9/12 pitch on a 24-32 ft wide house.

4. DORMERS (REQUIRED — SCAN EVERY ROOFLINE):
   BEFORE finalizing each elevation, trace the roofline in the photo
   from end to end looking for projections breaking the smooth slope.
   Common dormer signatures (look for ALL of these, not just one):
     • Small box-shaped projection out of the roof slope with its own
       mini-roof (gable, shed, or eyebrow shape)
     • One or two windows set INTO the roof slope (not on the main
       wall plane) — the window is recessed behind a visible roof slope
       on either side
     • A horizontal eave line ABOVE the main eave at a noticeably
       smaller width than the wall below
     • Shed dormers run wide and low (common on 1.5-story Capes / capes)
     • Gable dormers are narrow and triangular-topped
     • Eyebrow dormers are curved/arched and very subtle
   For EACH dormer found, estimate `dormer_face_sqft` (typical residential
   range: 20-60 ft² per dormer face — a 4 ft wide × 4 ft tall gable dormer
   = 16 ft²; a 12 ft wide × 6 ft tall shed dormer = 72 ft²) and record
   the total sum on the wall it FACES (front / back / left / right).
   Do NOT add dormer height to `height_ft` — that breaks the gable math.
   If a wall has 2 dormers, sum their face areas into one `dormer_face_sqft`
   value on that wall. If you see dormers ANYWHERE in any photo, you
   MUST record them — missing dormers is a top-3 source of under-quoting.
   In `notes`, briefly call out each dormer you found: e.g. "Shed dormer
   on left elevation, ~12 ft × 6 ft = 72 ft² face; gable dormer on right,
   ~4 ft × 4 ft = 16 ft² face."

5. SIDING COVERAGE — MASKED vs OPENINGS (READ CAREFULLY, THIS IS A
   HIGH-COST MISCLASSIFICATION):

   There are TWO DIFFERENT categories of "not-siding" area on a wall,
   and Claude has historically confused them. GET THIS RIGHT:

   (a) MASKED / NON-SIDING (drives `siding_pct_this_wall` DOWN):
       ONLY genuine, unframed, non-trimmed masonry / cladding that
       replaces the siding field. Examples:
         • Brick or stone wainscot / watertable
         • Full-wall brick, stone, or CMU masonry
         • Stucco / EIFS panel sections
         • Attached structures with their own cladding (a stone chimney
           face, an attached brick porch column wrap)
       These areas get NO siding, NO J-channel, NO trim — they are
       excluded from the siding takeoff entirely.

   (b) OPENINGS (belong in `openings[]`, DO NOT reduce siding_pct):
       Every trimmed penetration in the wall is an OPENING, not a
       masked area. These MUST be emitted as rows in `openings[]`
       with the correct `type`:
         • Windows (all styles)                → type=window
         • Entry doors / front doors / side    → type=entry_door
           doors / mudroom doors
         • Sliding / French / patio doors      → type=patio_door
         • Garage doors (single OR double,     → type=garage_door
           overhead OR carriage-style)
         • Wall vents / attic vents / gable    → type=vent
           vents / dryer vents (only when
           large enough to require trim, ≥12")
       Openings receive J-channel / surround trim in the takeoff.
       Leaving them out of `openings[]` (or dumping them into masked
       area via a low siding_pct_this_wall) DROPS the J-channel and
       under-quotes the job. GARAGE DOORS ARE ESPECIALLY EASY TO GET
       WRONG — a 16 ft double garage door is ~112 ft² of "not-siding",
       and if you bake that into siding_pct_this_wall instead of
       emitting it as `openings[]` type=garage_door, the trim/J-channel
       takeoff loses ~40 lf of surround per door. ALWAYS emit garage
       doors as openings.

   Decision tree per non-siding region:
     - Is there a rectangular framed hole with a trimmed edge?           → OPENING
     - Is there a door slab (any type — walk, patio, garage)?            → OPENING
     - Is it stone / brick / CMU / stucco with no trim boundary?         → MASKED (reduce siding_pct)
     - Is it an attached masonry structure (chimney, brick column)?      → MASKED (reduce siding_pct)
     - Everything else                                                   → SIDING

   For each wall, set siding_pct_this_wall to the visible fraction of
   the wall body that IS siding — i.e., after subtracting ONLY the
   masked (masonry/stucco) region, NOT the openings. Openings are
   subtracted separately downstream via the `openings[]` list, so
   including them in siding_pct_this_wall would double-count.

   Compute the global siding_coverage_pct as a weighted average. If a
   house is 100% siding (with normal doors + windows but no masonry),
   siding_coverage_pct should be 100 — the doors/windows come out of
   the openings list, not the coverage pct.

5b. SIDING PROFILE PER ELEVATION (Iter 78z — REQUIRED):
   Even on a single house, different SURFACES often use different
   siding profiles. Almost always seen:
     • Body of the wall = horizontal LAP or DUTCH LAP (most common)
     • Gable triangles  = SHAKE / SHAKER / scallop accent
     • Dormer faces     = SHAKE or BOARD & BATTEN accent
     • SMALL ACCENT AREAS = B&B / shake / vertical on porch faces,
       column wraps, bay-window cheeks, kneewalls, entry-roof gables.
       These are the EASIEST to miss and the #1 cause of an under-quote
       on Howard's mixed-material houses. Always look for vertical
       texture or "different from the rest of the wall" areas.
   Capture four separate callouts per wall:
     - `wall_body_profile_callout`  → the main wall body's profile
     - `gable_profile_callout`      → only when gable_triangle_height_ft > 0
     - `dormer_profile_callout`     → only when dormer_face_sqft > 0
     - `accent_profiles[]`          → small accent zones (B&B porch face,
                                       shake column wrap, vertical bay
                                       cheek, etc.). Estimate ft² each.
   What to look for:
     (a) Text labels visible IN the photo. Architects on construction
         drawings write things like "LAP 4\"", "DUTCH LAP 5\"", "SHAKER",
         "SHAKE", "B&B", "BOARD AND BATTEN", "VERTICAL", "NICKEL GAP",
         "VINYL". Use the literal text when visible.
     (b) The visible pattern in the photo. Even without text labels,
         the look of the surface tells you the profile:
           - Tight horizontal lines, ~4-5\" apart = LAP
           - Same but with a "step" notch in each lap = DUTCH LAP
           - Irregular textured slats stacked vertically with visible
             gaps = SHAKE / SHAKER (cedar-shake look)
           - Wide vertical boards with thin batten strips on top =
             BOARD & BATTEN (a.k.a. B&B / vertical siding)
           - Smooth wide vertical boards with tight V-grooves between
             them = NICKEL GAP
   Output the most specific callout you can. If the wall body and the
   gable look identical, set `gable_profile_callout = ""` and the
   downstream code will inherit from the body. Leaving these empty is
   fine — but a WRONG profile is worse than an empty one (the catalog
   mapper will split the line by profile and produce wrong SKUs).
   For `accent_profiles`, err on the side of including small accents
   even when unsure — under-counting B&B is the most expensive
   mistake we've seen on real jobs.

6. CONSERVATIVE BIAS: When in doubt, under-estimate. Contractors over-buy
   to cover waste; you don't need to add buffer. If your math gives a
   range, return the LOW end and flag it in notes.

7. SHOW YOUR WORK: In notes, briefly explain:
   "Back wall: 28 × 9 = 252 ft² rectangle + 28 × 6 / 2 = 84 ft² gable
   triangle. Right wall: 36 × 9 = 324 ft² with a 32 ft² dormer face."
   This forces you to keep the geometry honest.

8. ROUNDING: Walls to nearest 0.5 ft. Openings to nearest 2 in. Final
   siding area to nearest 10 ft².

9. WHAT TO RETURN as siding_sqft (computed downstream from your walls):
   ONLY the portion of wall area that's actually siding (after applying
   siding_pct_this_wall per wall). Gable triangles + dormer faces are
   added on top at 100% siding (unless you flag them as masonry).
   Do not include brick/garage/etc.

10. SATELLITE FUSION — when an "aerial" elevation photo is present (look
   for the "AERIAL ELEVATION" purple badge), TREAT THE AERIAL AS THE
   AUTHORITATIVE SOURCE for roof-outline measurements:
   • `eaves_lf` (total horizontal roof edges) — read from the aerial's
     top-down view of the soffit line. Far more accurate than inferring
     from oblique ground photos.
   • `rakes_lf` (sloped gable-edge legs) — read from the aerial's roof
     ridge → eave segments at gable ends.
   • House footprint width × depth — anchor these with the aerial.
   The ground-level photos still drive `height_ft`, `gable_triangle_height_ft`,
   `dormer_face_sqft`, openings, story count, and siding coverage —
   things you cannot see from above. Don't try to read wall heights or
   window counts off the aerial.

11. DOUBLE-COUNT CHECK (REQUIRED — DEDUPE BEFORE RETURNING):
   When the same window/door/wall corner is visible from two angles
   (very common: a front-elevation photo AND a corner photo both show
   the same front-right window), you MUST count it EXACTLY ONCE.

   Iter 79j.40 — CRITICAL: twins and triples MUST survive. Two 36×60
   double-hungs on the same bedroom wall are TWINS, not one window
   seen twice. Never dedupe on (wall, type, size) alone — that
   heuristic under-counts real twin/triple/quad configurations by 50-
   75% and silently drops the J-channel takeoff for the lost units.

   Rules for cross-photo dedupe:
     a) Two openings collapse to ONE if AND ONLY IF: same wall, same
        type, size within ±3", AND their POSITION ALONG THE WALL
        (distance from the LEFT corner viewing the wall from outside)
        agrees within ±2 ft.
     b) Two openings on the same wall with matching (wall, type, size)
        but position gap > 2 ft are TWINS or a MATCHED PAIR — keep
        both. Common examples:
          • Twin double-hungs mulled together (bedroom windows)
          • Triple casements over a kitchen sink
          • Matched pair flanking a fireplace
          • 4-unit sunroom bank
          • Two garage doors side-by-side
     c) If you can't estimate the position along the wall for one of
        them (foreshortened corner shot, obstruction, dormer opening),
        KEEP BOTH. False duplicates cost less than lost twins.
     d) Outside corner posts at any rectangular-house corner appear
        in two photos. Count each unique corner ONCE in
        `outside_corner_lf`.
     e) The front wall visible in both the front-elevation photo and
        a front-corner photo is the SAME wall. One row in `walls[]`,
        not two.
   In `double_count_check`, explicitly list which openings/walls you
   deduplicated and which photos showed them, INCLUDING the position
   evidence that justified the dedupe (or the position gap that saved
   a twin). Example:
   "Front wall has 4 windows (36×60). Photo #1 shows all 4 at
   positions 4ft, 10ft, 16ft, 22ft. Photo #2 (front-right corner)
   shows 2 windows at positions 16ft, 22ft — SAME PHYSICAL WINDOWS
   as photo #1's right two (positions match within ±0.5 ft). Counted
   the 4 unique windows once each, not 6. Kept the twin at 4ft/10ft
   separately from the twin at 16ft/22ft because both pairs have a
   >2 ft position gap."

12. PER-WALL CONFIDENCE (required) — emit a `confidence` (0-100) on each
   wall reflecting how well you can actually measure THAT specific wall:
   • 85-100: clear, straight-on photo with a reference object (door,
     brick course, contractor red ref line). Minimal perspective skew.
   • 60-84: visible but at an angle, or partial obstruction (tree, fence,
     vehicle), or no reference object.
   • 30-59: heavily obstructed, deep perspective, or inferred from an
     adjacent photo.
   • 0-29: not visible — measurement is a guess from the opposite side
     or symmetry assumption. Surface these clearly in `notes`.
   Briefly justify in `confidence_reasoning`. The frontend paints a
   colored chip per wall so the contractor knows which to verify in the
   field — be honest, do not inflate.

13. PHOTOS ARRAY — emit ONE entry in `photos[]` PER attached image, in
   the exact attachment order (photos[0] = first image you saw,
   photos[1] = second, ...). For each, infer the elevation so the
   frontend can auto-tag thumbnails. Use one of these 11 values:
     • front / back / left / right — centered shot of ONE wall
     • front-left / rear-left / rear-right / front-right — 45° CORNER
       shot showing TWO walls. Pick the corner whose two walls are
       both visible in the frame. A photo taken from the SE corner
       looking NW shows front + right → "front-right".
     • aerial — top-down satellite/drone
     • detail — close-up of a single feature (window, dormer, corner
       post). Use this for the "Scale ✓" reference shot.
     • other — none of the above (rare).
   The purple "ELEVATION" annotation badge — when present —
   is always authoritative; otherwise lean on entry-door cues (front),
   driveway+garage (front or side), backyard cues (back), and footprint
   geometry. `elevation_confidence` 0-100 mirrors your certainty.
   Tag corner shots as their corner (not as one of the two walls) so
   the contractor sees distinct badges in the photo grid.

14. WINDOW STYLE / OPERATION (REQUIRED — emit `style` on EVERY window opening):
   For each `openings[]` row of type=window AND each `openings_schedule[]`
   window row, identify the operation style. Use these visual signatures:
     • **Double Hung** — single window with a HORIZONTAL meeting rail
       cutting the glass in half (top sash + bottom sash). The most
       common residential style by far. Width-to-height ratio is usually
       0.5-0.8 (taller than wide).
     • **Single Hung** — looks identical to double hung from afar (one
       meeting rail). If you cannot tell DH vs SH from a photo, pick
       Double Hung and note uncertainty in `style_confidence` (50-65).
     • **Casement** — single pane of glass with NO meeting rail. Hinged
       on the side, opens with a crank. Crank handle (small lever at the
       bottom or side) visible when present. Often narrow and tall.
     • **Twin Casement** — TWO casements side-by-side sharing a mullion,
       each with its own crank. Common in kitchens.
     • **2-Lite Slider (XO)** — TWO panes of equal size side-by-side
       with a VERTICAL meeting bar. Usually wider than tall. One side
       slides horizontally.
     • **3-Lite Slider (XOX)** — THREE panes side-by-side, fixed +
       sliding + fixed. Very wide landscape orientation.
     • **Picture / Fixed** — single large pane of glass with NO meeting
       rails, NO crank, NO operable hardware. Often square or nearly
       square. Used as a focal window over a sink, fireplace, etc.
     • **Twin Double Hung** — TWO double hungs side-by-side sharing a
       mullion. Each half has its own horizontal meeting rail. Common
       on master bedroom walls.
     • **Triple Double Hung** — three double hungs in a row, often
       above a kitchen sink.
     • **Awning** — horizontal hinge on TOP, opens outward at the
       bottom. Usually WIDE landscape and small (used above doors or
       as transoms).
     • **Hopper** — horizontal hinge on BOTTOM, opens inward at the
       top. Common in basements. Small landscape.
     • **Bay Window** — 3-section bump-out projecting from the wall;
       center is picture, sides are double hung or casement.
     • **Bow Window** — 4-5 section curved bump-out projecting from
       the wall. Smoother arc than a bay.
     • **Half-Round** — semicircle window. Often a transom above a
       picture window or entry door.
     • **Quarter-Round** — quarter circle / pie-slice shape.
     • **Arch** — rectangle with a curved/arched top edge.
     • **Octagon** — 8-sided window. Common as accent in gables.
     • **Hexagon** — 6-sided window.
     • **Garden Window** — small box-shaped bump-out, usually over a
       kitchen sink. Glass on three sides + top.
     • **Other Shape** — specialty/custom that doesn't fit above. Note
       in `notes`.
   Emit `style_confidence` 0-100 reflecting how certain you are:
     • 85-100 — clear view with operating hardware visible (crank,
       meeting rail clearly visible, etc.).
     • 60-84 — visible but oblique or partly obstructed.
     • 30-59 — heavily inferred (e.g. "looks like DH but could be SH").
     • 0-29 — guess. The frontend lets the contractor correct any
       guess with a dropdown — be honest, not overconfident.
   If you genuinely cannot tell the style from the photo (window
   covered by curtains/shutters, deep shadow, etc.), emit "" and
   `style_confidence: 0` so the frontend flags it as needing manual
   selection. Do NOT default everything to Double Hung — under-
   identifying Casement / Picture / Slider causes downstream pricing
   errors of $300-$1200 per opening.
   For entry_door / patio_door / garage_door / vent / other,
   emit `style: ""` and `style_confidence: 0` — style only applies
   to windows.

Return ONLY the JSON object. No explanation, no code fences."""

# Iter 57d — Window style → Vero product_type mapper. Vero only ships 5
# product_types, but the AI's `style` vocabulary is much richer (so the
# customer PDF can say "Twin Double Hung windows 36"×60"" while the
# Vero quote rows fall into one of the 5 buckets). For multi-unit styles
# (Twin DH / Twin Casement / Bay / Bow), the qty is multiplied so a
# single openings row becomes the correct count of Vero opening rows.
#
# Iter 57t — Vero pricing freeze. Styles that historically routed to
# `Vero Picture` or `Vero 3-Lite Slider` (both frozen) now reroute to
# `Vero Double Hung` so the estimator can hand-tag/upgrade them after
# the fact, instead of landing in a hidden section.
_STYLE_TO_VERO_PRODUCT_TYPE: dict[str, tuple[str, int]] = {
    "Double Hung":        ("Vero Double Hung",     1),
    "Single Hung":        ("Vero Double Hung",     1),
    "Casement":           ("Vero 1-Lite Casement", 1),
    "Twin Casement":      ("Vero 1-Lite Casement", 2),
    "Awning":             ("Vero 1-Lite Casement", 1),
    "Hopper":             ("Vero 1-Lite Casement", 1),
    "2-Lite Slider":      ("Vero 2-Lite Slider",   1),
    "3-Lite Slider":      ("Vero 2-Lite Slider",   1),  # frozen → reroute to 2-Lite
    "Picture":            ("Vero Double Hung",     1),  # frozen → DH
    "Twin Double Hung":   ("Vero Double Hung",     2),
    "Twin Single Hung":   ("Vero Double Hung",     2),
    "Triple Double Hung": ("Vero Double Hung",     3),
    "Bay Window":         ("Vero Double Hung",     3),  # frozen → DH (3-pane)
    "Bow Window":         ("Vero Double Hung",     5),  # frozen → DH (5-pane)
    "Half-Round":         ("Vero Double Hung",     1),  # frozen → DH
    "Quarter-Round":      ("Vero Double Hung",     1),  # frozen → DH
    "Arch":               ("Vero Double Hung",     1),  # frozen → DH
    "Octagon":            ("Vero Double Hung",     1),  # frozen → DH
    "Hexagon":            ("Vero Double Hung",     1),  # frozen → DH
    "Garden Window":      ("Vero Double Hung",     1),  # frozen → DH
    "Other Shape":        ("Vero Double Hung",     1),  # frozen → DH
}


def _vero_for_style(style: str, width_in: float, height_in: float) -> tuple[str, int]:
    """Map an AI `style` string to (Vero product_type, qty_multiplier).
    Falls back to the legacy W/H heuristic from hover.py when the style
    is empty/unknown — preserves backwards-compatible behaviour for
    legacy sessions that have no style field."""
    style = (style or "").strip()
    if style in _STYLE_TO_VERO_PRODUCT_TYPE:
        return _STYLE_TO_VERO_PRODUCT_TYPE[style]
    from .hover import _guess_vero_product_type  # local import avoids cycle
    return (_guess_vero_product_type(width_in, height_in), 1)


def apply_roof_type_material_math(raw: dict, walls: list, gable_sqft: float, dormer_sqft: float) -> tuple:
    """Iter 79j.26 + 79j.27 — normalize walls[] based on Claude's roof-type
    classification.

    Behaviour matches the frontend HouseModel3D confidence threshold (0.8):
      * roof_type "hip" ≥0.8   → zero every wall's gable_triangle_height_ft,
                                 zero the gable_sqft summary
      * roof_type "gable-shed-dormer" ≥0.8 + dormer payload
                               → inflate the target facade's dormer_face_sqft
                                 by (face + cheeks − on_dormer opening area)
      * below 0.8 or missing   → no-op (return inputs unchanged)

    Walls are mutated in place. Returns the (possibly adjusted)
    (gable_sqft, dormer_sqft) totals.
    """
    roof_type_raw = raw.get("roof_type")
    roof_type = roof_type_raw if roof_type_raw in ("gable", "hip", "gable-shed-dormer") else None
    conf_raw = raw.get("roof_type_confidence")
    try:
        conf = float(conf_raw) if conf_raw is not None else 0.0
    except (TypeError, ValueError):
        conf = 0.0
    if not roof_type or conf < 0.8:
        return gable_sqft, dormer_sqft

    if roof_type == "hip":
        for w in walls:
            w["gable_triangle_height_ft"] = 0
        return 0.0, dormer_sqft

    if roof_type == "gable-shed-dormer":
        # Iter 79j.41 — Accept `dormers[]` array first (two-phase
        # reconciler emits it), fall back to legacy singular `dormer`
        # wrapped as a 1-element list. Sum face+cheek contributions
        # across every dormer so a house with 2 shed dormers on
        # opposite slopes doesn't silently drop half its material.
        dormers_raw = raw.get("dormers")
        if isinstance(dormers_raw, list):
            _dormers_iter = [d for d in dormers_raw if isinstance(d, dict)]
        else:
            _legacy = raw.get("dormer")
            _dormers_iter = [_legacy] if isinstance(_legacy, dict) else []
        if not _dormers_iter:
            return gable_sqft, dormer_sqft
        openings_by_face: dict[str, float] = {}
        # Iter 79j.41 — Same face-alias table used below on the dormer
        # iteration, hoisted so opening face keys normalize too.
        _face_alias = {"rear": "back", "back": "back", "front": "front",
                       "left": "left", "right": "right",
                       "slope-front": "front", "slope-back": "back",
                       "slope-left": "left", "slope-right": "right"}
        for o in (raw.get("openings") or []):
            if not o.get("on_dormer"):
                continue
            w_in = float(o.get("width_in") or 0)
            h_in = float(o.get("height_in") or 0)
            if w_in <= 0 or h_in <= 0:
                continue
            face_lbl = _face_alias.get(str(o.get("wall") or "front").lower(),
                                       str(o.get("wall") or "front").lower())
            openings_by_face[face_lbl] = openings_by_face.get(face_lbl, 0.0) + (w_in / 12.0) * (h_in / 12.0)
        total_extra = 0.0
        # Iter 79j.41 — Aliases: Claude may emit "rear" for the back
        # wall (natural language) but walls[] labels use "back".
        # Normalise both sides of the match so a rear-slope dormer
        # actually credits the back wall.
        face_alias = _face_alias
        for dormer_raw in _dormers_iter:
            face_raw = str(dormer_raw.get("face") or "front").lower()
            face = face_alias.get(face_raw, face_raw)
            d_w = float(dormer_raw.get("width_ft") or 0)
            d_h = float(dormer_raw.get("knee_wall_height_ft") or 0)
            if d_w <= 0 or d_h <= 0:
                continue
            face_sqft = d_w * d_h
            # 2 cheek triangles, base = knee height, height = knee height —
            # matches the frontend geometry which uses knee for both.
            cheek_sqft = 2 * 0.5 * d_h * d_h
            extra = max(0.0, face_sqft + cheek_sqft - openings_by_face.get(face, 0.0))
            for w in walls:
                if (w.get("label") or "").lower() == face:
                    w["dormer_face_sqft"] = float(w.get("dormer_face_sqft") or 0) + extra
                    break
            total_extra += extra
        return gable_sqft, float(dormer_sqft) + total_extra

    return gable_sqft, dormer_sqft


def _build_vero_openings_from_ai(openings: list, schedule: list | None = None) -> list[dict]:
    """Turn AI-detected windows into the `vero_openings[]` rows the
    Windows workspace expects on Apply.

    Iter 57i — primary source is `openings_schedule` (one row per
    (wall, type, size, style) with `count: N`). Each schedule row
    becomes `count × qty_multiplier` Vero rows. Falls back to the
    deduped `openings[]` list when no schedule is present (legacy
    sessions). The schedule path is correct when a wall has 3 distinct
    identical DH windows — they appear as one schedule row with
    count=3 and produce 3 Vero DH rows. The fallback path would
    produce only 1 (under-count).

    Non-window openings (doors / vents) are skipped — they belong to
    the Siding workspace's accessory rows, not Windows."""
    out: list[dict] = []
    seen: set[str] = set()

    def _emit(*, otype: str, w: float, h: float, wall: str, style: str, count: int = 1):
        if otype != "window" or w <= 0 or h <= 0 or count <= 0:
            return
        product_type, qty_mult = _vero_for_style(style, w, h)
        # `qty_mult` covers multi-unit styles (Twin DH=2, Bay=3, Bow=5);
        # `count` covers physically-distinct identical windows.
        total = count * qty_mult
        label = f"AI · {wall} · {style or 'Window'} · {int(w)}×{int(h)}"
        for _ in range(total):
            out.append({
                "id": str(uuid.uuid4()),
                "hover_id": "",
                "product_type": product_type,
                "label": label,
                "width": w,
                "height": h,
                "qty": 1,
                "sister_color": "White Interior/White Exterior",
                "sizing": "ui_bucket",
                "bucket_label": "",
                "base_mat": 0,
                "adders": [],
                "ai_style": style,
            })

    if schedule:
        for o in schedule:
            try:
                w = float(o.get("width_in") or 0)
                h = float(o.get("height_in") or 0)
            except (TypeError, ValueError):
                continue
            otype = (o.get("type") or "").lower()
            wall = (o.get("elevation") or o.get("wall") or "other").lower()
            style = (o.get("style") or "").strip()
            count = int(o.get("count") or 0)
            seen.add(f"{wall}|{otype}|{int(w)}|{int(h)}|{style.lower()}")
            _emit(otype=otype, w=w, h=h, wall=wall, style=style, count=count)
        return out

    # Legacy fallback — no schedule available, walk the deduped list.
    for o in openings or []:
        try:
            w = float(o.get("width_in") or 0)
            h = float(o.get("height_in") or 0)
        except (TypeError, ValueError):
            continue
        otype = (o.get("type") or "").lower()
        wall = (o.get("wall") or "other").lower()
        style = (o.get("style") or "").strip()
        _emit(otype=otype, w=w, h=h, wall=wall, style=style, count=1)
    return out




def _dedupe_openings(openings: list) -> list:
    """Iter 79j.40 — TWIN-SAFE cross-photo dedupe.

    Rewritten from the old Iter-57b heuristic which grouped by (wall,
    type, size, style) and collapsed every group down to a single
    entry — that MURDERED twins and triples (two 36×60 double-hungs on
    the same bedroom wall silently became one). Under-count cost:
    50-75% of the J-channel takeoff for the lost units.

    New rule: two openings collapse to ONE if AND ONLY IF they match
    on (wall, type, size within 6 in, style) AND their `along_wall_ft`
    positions agree within POSITION_TOL_FT. If `along_wall_ft` is null
    on EITHER opening, we cannot confirm they're the same physical
    window, so KEEP BOTH — false duplicates are far cheaper than lost
    twins.

    Every kept opening's `_source_photo_indices` is unioned across
    the merged rows so provenance is preserved.

    Returns a fresh list — input is not mutated.
    """
    if not openings:
        return openings
    POSITION_TOL_FT = 2.0
    kept: list[dict] = []
    for o in openings:
        try:
            w = float(o.get("width_in") or 0)
            h = float(o.get("height_in") or 0)
        except (TypeError, ValueError):
            continue
        if w <= 0 or h <= 0:
            continue
        wall = (o.get("wall") or "other").lower()
        otype = (o.get("type") or "other").lower()
        style = (o.get("style") or "").strip().lower()
        try:
            pos = o.get("along_wall_ft")
            pos = float(pos) if pos is not None else None
        except (TypeError, ValueError):
            pos = None
        w_bin = round(w / 6) * 6
        h_bin = round(h / 6) * 6

        merged_into: dict | None = None
        for existing in kept:
            if wall != (existing.get("wall") or "other").lower():
                continue
            if otype != (existing.get("type") or "other").lower():
                continue
            e_w = float(existing.get("width_in") or 0)
            e_h = float(existing.get("height_in") or 0)
            if round(e_w / 6) * 6 != w_bin or round(e_h / 6) * 6 != h_bin:
                continue
            if style != (existing.get("style") or "").strip().lower():
                continue
            # Same (wall, type, size, style). Now the twin-safe check.
            try:
                e_pos = existing.get("along_wall_ft")
                e_pos = float(e_pos) if e_pos is not None else None
            except (TypeError, ValueError):
                e_pos = None
            # If EITHER position is null, we cannot prove same-window.
            # Keep both — this is the twin-safety line.
            if pos is None or e_pos is None:
                continue
            # Both positions known — merge only when within tolerance.
            if abs(pos - e_pos) <= POSITION_TOL_FT:
                merged_into = existing
                break

        if merged_into is None:
            kept.append(dict(o))
        else:
            # Union source photo indices so provenance is preserved.
            src = list(merged_into.get("_source_photo_indices") or [])
            for idx in (o.get("_source_photo_indices") or []):
                if idx not in src:
                    src.append(idx)
            if merged_into.get("photo_idx") is not None and merged_into["photo_idx"] not in src:
                src.insert(0, merged_into["photo_idx"])
            if o.get("photo_idx") is not None and o["photo_idx"] not in src:
                src.append(o["photo_idx"])
            merged_into["_source_photo_indices"] = src
    return kept


# Iter 57g — Standard-size window snapping. Residential windows are ~99%
# of the time ONE of a fixed set of widths and heights. Claude's vision
# measurements are usually within ±2 in of the true size — snapping
# them to the nearest standard tightens up Vero SKU matching dramatically
# (a 37×61 becomes a 36×60, hitting the right price bucket).
_STD_WIDTHS_IN = (
    18, 20, 24, 28, 30, 32, 34, 36, 40, 42, 44, 48, 54, 60, 66, 72, 78,
    84, 96, 108, 120, 144, 168, 192,
)
_STD_HEIGHTS_IN = (
    24, 30, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 60, 62, 66, 72, 76,
    80, 84, 90, 96,
)
_SNAP_TOLERANCE_IN = 2.5  # how close a guess must be to a standard to snap


def _snap_to_standard(value: float, ladder: tuple[int, ...]) -> float:
    """Snap `value` to the nearest entry in `ladder` if it's within
    `_SNAP_TOLERANCE_IN` inches; otherwise return the value unchanged.
    Keeps outlier sizes (true custom windows) intact — only the noisy
    ±2-in guesses get cleaned up."""
    if value <= 0:
        return value
    nearest = min(ladder, key=lambda s: abs(s - value))
    if abs(nearest - value) <= _SNAP_TOLERANCE_IN:
        return float(nearest)
    return value


def _snap_window_sizes(openings: list) -> list:
    """Snap every `type=window` opening's W and H to nearest standard
    size within tolerance. Mutates and returns the list for convenience
    — caller can ignore the return."""
    for o in openings or []:
        if (o.get("type") or "").lower() != "window":
            continue
        try:
            w = float(o.get("width_in") or 0)
            h = float(o.get("height_in") or 0)
        except (TypeError, ValueError):
            continue
        o["width_in"] = _snap_to_standard(w, _STD_WIDTHS_IN)
        o["height_in"] = _snap_to_standard(h, _STD_HEIGHTS_IN)
    return openings


def _snap_schedule_sizes(schedule: list) -> list:
    """Same snap pass for the openings_schedule rows so the display
    and the openings[] list stay consistent."""
    for o in schedule or []:
        if (o.get("type") or "").lower() != "window":
            continue
        try:
            w = float(o.get("width_in") or 0)
            h = float(o.get("height_in") or 0)
        except (TypeError, ValueError):
            continue
        o["width_in"] = _snap_to_standard(w, _STD_WIDTHS_IN)
        o["height_in"] = _snap_to_standard(h, _STD_HEIGHTS_IN)
        wi = int(round(o["width_in"]))
        hi = int(round(o["height_in"]))
        # Refresh size_label so the snapped value shows in the schedule.
        o["size_label"] = f'{wi}×{hi} in'
    return schedule


def _enforce_symmetry(openings: list) -> list:
    """Iter 57g — if 3+ windows on the SAME wall + style are within a
    few inches of each other, force them all to the SAME size (the
    median W and median H of the cluster). Eliminates the "Claude
    returned 36×60, 35×61, 37×59 for the same row of 4 identical
    front windows" inconsistency."""
    if not openings:
        return openings
    # Bucket windows by (wall, style). Type stays = window throughout.
    buckets: dict[tuple, list[dict]] = {}
    for o in openings:
        if (o.get("type") or "").lower() != "window":
            continue
        wall = (o.get("wall") or "other").lower()
        style = (o.get("style") or "").strip().lower()
        buckets.setdefault((wall, style), []).append(o)
    for cluster in buckets.values():
        if len(cluster) < 3:
            continue
        ws = sorted(float(o.get("width_in") or 0) for o in cluster)
        hs = sorted(float(o.get("height_in") or 0) for o in cluster)
        mw = ws[len(ws) // 2]
        mh = hs[len(hs) // 2]
        # Spread check: if any W is more than 4 in away from median,
        # this isn't really a "set of identical windows" — leave them.
        if max(abs(w - mw) for w in ws) > 4 or max(abs(h - mh) for h in hs) > 4:
            continue
        # Force every member to the median, snapped to a standard size.
        mw_snap = _snap_to_standard(mw, _STD_WIDTHS_IN)
        mh_snap = _snap_to_standard(mh, _STD_HEIGHTS_IN)
        for o in cluster:
            o["width_in"] = mw_snap
            o["height_in"] = mh_snap
    return openings




def _json_from_reply(text: str) -> dict:
    """Pull the first {...} JSON object out of Claude's reply, tolerant of
    accidental code fences."""
    text = text.strip()
    # strip ```json ... ``` fences if Claude ignored the instruction
    fence = re.match(r"^```(?:json)?\s*(\{.*\})\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # else: try to find the first balanced { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise HTTPException(status_code=502, detail="AI did not return JSON")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}")


# Iter 78z+ — Format user-drawn profile annotations into a short prompt
# string Claude can read AS GROUND TRUTH. Two roles:
#   1. Tells Claude what the contractor already nailed down — so it
#      doesn't waste detection budget re-classifying those regions.
#   2. Biases Claude toward inferring matching patterns elsewhere. If
#      the user marked the front gable as Shake, the back & right
#      gables PROBABLY are too (houses are symmetrical) — Claude
#      should lean shake on those even when the photo is grainy.
def _build_annotation_hint(annotations: dict | None) -> str:
    if not annotations or not isinstance(annotations, dict):
        return ""
    # Aggregate by (photo_idx, elevation_label, profile) → sqft. The
    # photo_idx maps to the order photos were uploaded; Claude sees
    # them in the same order.
    lines: list[str] = []
    elev_profile_counts: dict[str, list[str]] = {}  # elevation_label → list of profiles
    for key, boxes in annotations.items():
        if key.startswith("_"):
            continue
        if not isinstance(boxes, list):
            continue
        for b in boxes:
            if not isinstance(b, dict):
                continue
            profile = (b.get("profile") or "").strip().lower()
            if not profile:
                continue
            sqft = b.get("sqft") or 0
            try:
                sqft = float(sqft)
            except (TypeError, ValueError):
                sqft = 0
            if sqft <= 0:
                continue
            label = (b.get("elevation_label") or "").strip().lower() or "unknown"
            callout = (b.get("callout") or "").strip()
            note = f" ({callout})" if callout else ""
            lines.append(
                f"  - photo #{int(key) + 1 if key.isdigit() else key}, "
                f"{label}: {profile.upper().replace('_', ' ')} ≈ {sqft:.0f} ft²{note}"
            )
            elev_profile_counts.setdefault(label, []).append(profile)
    if not lines:
        return ""

    # Build "matching pattern" reminder for elevations that have shake/B&B.
    # E.g. "The user marked SHAKE on front. Look CAREFULLY at every other
    # elevation's gable — symmetrical houses repeat the same accent."
    accent_lines = []
    for label, profiles in elev_profile_counts.items():
        unique = {p for p in profiles if p not in ("lap", "dutch_lap")}
        for u in unique:
            accent_lines.append(
                f"  - {u.upper().replace('_', ' ')} appears on {label}; "
                f"look carefully at other elevations for matching {u.upper().replace('_', ' ')} patterns."
            )

    hint = (
        "USER GROUND-TRUTH ANNOTATIONS — the contractor has drawn boxes "
        "on the photos and tagged each region with a profile + sqft. "
        "Use these AS GROUND TRUTH:\n"
        + "\n".join(lines)
    )
    if accent_lines:
        hint += (
            "\n\nMATCHING PATTERN HINTS — siding accents typically "
            "repeat symmetrically on houses. Use the user's tags to "
            "bias your per-elevation profile callouts:\n"
            + "\n".join(accent_lines)
        )
    hint += (
        "\n\nFor any elevation NOT covered by a user annotation, "
        "perform your normal best-effort profile detection. The "
        "annotated regions will land on the materials list "
        "REGARDLESS of what you return — but the more accurately "
        "you reflect them in `per_elevation` walls, the more "
        "useful your output is to the contractor."
    )
    return hint


# =====================================================================
# Iter 79j.44 — REMOVED: Deep-Dormer-Scan subsystem
# =====================================================================
# The legacy roofline-crop scan (DORMER_PROMPT, _crop_top_strip,
# _run_dormer_pass_for_photo, _is_skyline_photo, _merge_dormer_hits)
# has been removed. Two-phase Phase A/B now owns dormer detection
# end-to-end via the `dormers[]` array with per-face + `width_source`
# provenance. The old scan was injecting corrupt data: openings with
# null opening_ids, hits on nonexistent walls (e.g. `rear-left`), and
# face SF credited to the wrong wall for side-slope dormers. The
# `deep_dormer_scan` request flag is still accepted for backward
# compatibility but is now a no-op — see `_execute_ai_measure_worker`.


def _aggregate_to_hover_shape(raw: dict, annotations: dict | None = None) -> dict:
    """Roll up Claude's per-wall / per-opening estimates into the same
    measurements dict that the HOVER PDF importer returns. The frontend
    diff modal is reused 1-for-1.

    Iter 78z — When `annotations` is provided (user-drawn profile boxes
    from the ProfileAnnotator), they're layered on top of Claude's
    auto-detected breakdown as authoritative accent overrides. See
    `apply_annotations_to_breakdown` in profile_callouts.py.

    Each wall now carries:
      - `siding_pct_this_wall` (0-100). If Claude saw brick / garage /
        stucco on part of a wall, that fraction is dropped — otherwise
        the legacy 100% siding behavior holds.
      - `gable_triangle_height_ft` (0+). When non-zero, an additional
        0.5 × width × height triangle is added on top of the eave wall.
      - `dormer_face_sqft` (0+). Vertical face area of any dormers
        projecting from the roof slope — added as an extra to siding.
    """
    walls = raw.get("walls") or []
    # Iter 57b — dedupe openings as a safety net. Even with the
    # strengthened double-count prompt rule, Opus occasionally returns
    # the same window twice when it appears at the edges of two photos.
    raw_openings = raw.get("openings") or []
    # Iter 57g order: 1) dedupe, 2) enforce symmetry on like-windows,
    # 3) snap each window to nearest standard residential size. Doing
    # dedupe first reduces the cluster sizes that symmetry sees.
    openings = _dedupe_openings(raw_openings)
    openings = _enforce_symmetry(openings)
    openings = _snap_window_sizes(openings)
    # Snap the schedule rolls too so the on-screen + PDF tables match.
    if raw.get("openings_schedule"):
        raw["openings_schedule"] = _snap_schedule_sizes(raw["openings_schedule"])
    deduped_count = len(raw_openings) - len(openings)
    if deduped_count > 0:
        # Stash the pre-dedupe list back onto raw so the frontend's
        # raw_ai display matches what the aggregator actually counted,
        # AND surface the dedup tally in notes so the contractor knows
        # the safety net fired.
        raw["openings_raw_before_dedupe"] = list(raw_openings)
        raw["openings"] = openings
        prev_notes = raw.get("notes") or ""
        raw["notes"] = (
            f"Backend deduped {deduped_count} double-counted opening"
            f"{'s' if deduped_count > 1 else ''} (same window seen from two angles). "
            + prev_notes
        ).strip()

    siding_sqft = 0.0
    gable_sqft = 0.0
    dormer_sqft = 0.0
    for w in walls:
        width_ft = float(w.get("width_ft") or 0)
        eave_h = float(w.get("height_ft") or 0)
        # Iter 55: HARD CLAMP — Claude occasionally returns wall heights
        # as story-units (1.0 = 1 story) or stupidly small fractions
        # (0.7 ft) which deflates the whole quote by 10–100×. No real
        # exterior wall is < 7 ft. If we get something nonsensical, fall
        # back to the global avg_wall_height_ft, then the story-default.
        if 0 < eave_h < 7:
            avg = float(raw.get("avg_wall_height_ft") or 0)
            story = float(raw.get("story_count") or 1)
            if avg >= 7:
                eave_h = avg
            elif story >= 2:
                eave_h = 18.0
            elif story >= 1.5:
                eave_h = 12.0
            else:
                eave_h = 9.0
        # Same defensive clamp for width — no real house wall is < 5 ft.
        # Single-digit widths usually mean Claude returned a meaningless
        # fraction. Skip the wall (don't try to guess a width).
        if 0 < width_ft < 5:
            width_ft = 0
        gross = width_ft * eave_h
        pct = float(w.get("siding_pct_this_wall") or 100.0)
        # Defensive parsing: Claude sometimes returns 0.85 meaning "85%"
        # (a fraction) and sometimes returns 85 meaning "85%". Without
        # this clamp a 2000 ft² house can shrink to 17 ft² because 0.85
        # gets read as 0.85%. Heuristic: anything strictly between 0 and
        # 1 is a fraction — multiply by 100 to get a percent. Anything
        # exactly 0 or above 1 is already a percent (or junk).
        if 0 < pct < 1:
            pct = pct * 100.0
        if pct <= 0:
            pct = 100.0
        pct = min(pct, 100.0)
        siding_sqft += gross * (pct / 100.0)
        # Gable triangle (only when Claude flagged this wall as a gable
        # end). The triangle is assumed 100% siding unless the
        # contractor manually overrides on the line item later.
        gable_h = float(w.get("gable_triangle_height_ft") or 0)
        if gable_h > 0 and width_ft > 0:
            gable_sqft += 0.5 * width_ft * gable_h
        # Dormers — already in ft², no width math needed.
        dormer_sqft += float(w.get("dormer_face_sqft") or 0)
    # Add gable + dormer extras on top of the masonry-adjusted siding.
    siding_sqft += gable_sqft + dormer_sqft
    # The HOVER importer also surfaces siding_with_openings_sqft (gross
    # ft² incl. door/window openings). For AI walls we already counted
    # gross wall area, so use the same value.
    siding_with_openings_sqft = siding_sqft

    # Approximate opening areas to deduct (informational).
    opening_sqft = 0.0
    for o in openings:
        opening_sqft += (float(o.get("width_in") or 0)
                         * float(o.get("height_in") or 0)) / 144.0

    # Iter 57i — counts come from the openings_schedule (Claude's
    # grouped roll-up with `count: N` per row) rather than the deduped
    # `openings` list. The dedupe step collapses identical 36×54 DH
    # windows on the same wall into 1 entry, which is correct for the
    # dedupe purpose (eliminating cross-photo duplicates) but
    # under-counts when a wall genuinely has 3 identical-but-distinct
    # windows. The schedule preserves these counts.
    schedule_for_counts = raw.get("openings_schedule") or []
    counts = {"window": 0, "entry_door": 0, "patio_door": 0, "garage_door": 0}
    perimeter_lf = 0.0
    if schedule_for_counts:
        for o in schedule_for_counts:
            t = (o.get("type") or "other").lower()
            cnt = int(o.get("count") or 0)
            if t in counts:
                counts[t] += cnt
            perimeter_lf += cnt * 2 * (
                (float(o.get("width_in") or 0) + float(o.get("height_in") or 0)) / 12.0
            )
    else:
        # Legacy sessions without a schedule fall back to the dedupe
        # list — preserves backwards compatibility.
        for o in openings:
            t = o.get("type", "other")
            if t in counts:
                counts[t] += 1
            perimeter_lf += 2 * (
                (float(o.get("width_in") or 0) + float(o.get("height_in") or 0)) / 12.0
            )

    measurements = {
        "siding_sqft": round(siding_sqft, 1),
        "siding_with_openings_sqft": round(siding_with_openings_sqft, 1),
        "opening_sqft": round(opening_sqft, 1),
        "eaves_lf": round(float(raw.get("eaves_lf") or 0), 1),
        "rakes_lf": round(float(raw.get("rakes_lf") or 0), 1),
        # Starter strip: AI value if Claude gave one, otherwise fall back
        # to eaves_lf since the starter perimeter runs along the same base
        # course as the eaves on a basic 1-story rectangle. The contractor
        # can adjust on the line item if the house has porches / walk-outs.
        "starter_lf": round(float(raw.get("starter_lf") or raw.get("eaves_lf") or 0), 1),
        # Corners — AI estimates from visible elevations. Fall back to a
        # reasonable default for a basic rectangular house (4 outside
        # corners × avg wall height, 0 inside corners).
        "outside_corner_lf": round(float(
            raw.get("outside_corner_lf")
            or 4 * float(raw.get("avg_wall_height_ft") or 0)
        ), 1),
        "inside_corner_lf": round(float(raw.get("inside_corner_lf") or 0), 1),
        "opening_perimeter_lf": round(perimeter_lf, 1),
        "opening_count": sum(counts.values()),
        "window_count": counts["window"],
        "entry_door_count": counts["entry_door"],
        "patio_door_count": counts["patio_door"],
        "garage_door_count": counts["garage_door"],
        # AI-specific surfaced fields
        "_ai_scale_confidence": raw.get("scale_confidence") or "low",
        "_ai_reference_used": raw.get("reference_used") or "none",
        "_ai_story_count": raw.get("story_count"),
        "_ai_story_count_reasoning": raw.get("story_count_reasoning") or "",
        "_ai_avg_wall_height_ft": raw.get("avg_wall_height_ft"),
        "_ai_siding_coverage_pct": raw.get("siding_coverage_pct"),
        # Iter 47: surface gable + dormer breakdown so the preview UI can
        # show "Rect walls: 1,840 ft² · Gables: 168 ft² · Dormers: 60 ft²"
        # and the contractor can sanity-check the geometry before applying.
        "_ai_gable_sqft": round(gable_sqft, 1),
        "_ai_dormer_sqft": round(dormer_sqft, 1),
        # Iter 57: HOVER-like extras — per-wall confidence chips, an
        # openings schedule grouped by elevation/size, double-count
        # check note, missing-elevations flag, and per-photo elevation
        # auto-tags. All optional in the raw_ai payload so older
        # responses degrade gracefully.
        "_ai_missing_elevations": raw.get("missing_elevations") or [],
        "_ai_double_count_check": raw.get("double_count_check") or "",
        "_ai_openings_schedule": raw.get("openings_schedule") or [],
        "_ai_photos": raw.get("photos") or [],
        "_ai_notes": raw.get("notes") or "",
        # Iter 79j.43 — Empty-photo / orphaned-wall warnings from
        # the two-phase orchestrator. Surfaced as-is so the UI can
        # render a persistent banner naming each dead photo and the
        # wall(s) it orphans. Empty lists = healthy run.
        "_ai_empty_photos": raw.get("_empty_photos") or [],
        "_ai_orphaned_walls": raw.get("_orphaned_walls") or [],
    }
    # Iter 79j.26 — Roof type classification. Cascade: valid Claude
    # value → surface; else null. Confidence threshold enforced on the
    # frontend (≥0.8 → apply; below → default to gable + amber flag).
    # Material math post-processing runs BEFORE the breakdown so hip
    # roofs get their gable_triangle_height zeroed and dormers get
    # extra face+cheek sqft added into their facade's dormer_face_sqft.
    roof_type_raw = raw.get("roof_type")
    roof_type = roof_type_raw if roof_type_raw in ("gable", "hip", "gable-shed-dormer") else None
    roof_type_conf = raw.get("roof_type_confidence")
    try:
        roof_type_conf = float(roof_type_conf) if roof_type_conf is not None else None
    except (TypeError, ValueError):
        roof_type_conf = None
    measurements["_ai_roof_type"] = roof_type
    measurements["_ai_roof_type_confidence"] = roof_type_conf
    measurements["_ai_roof_type_reasoning"] = raw.get("roof_type_reasoning") or ""
    # Iter 79j.41 — Dormers as an ARRAY. A house can have a shed
    # dormer on the front slope AND a matching one on the back
    # slope (or gable dormers on left + right). The old `dormer`
    # singular schema silently lost every dormer past the first,
    # which was the root cause of the "missing right dormer" bug on
    # Howard's red house. Two-phase reconciler emits `dormers[]`;
    # legacy single-call runs (and prompts that still emit a lone
    # `dormer` object) get wrapped in a 1-element list so downstream
    # code sees a uniform shape.
    dormers_raw = raw.get("dormers")
    if isinstance(dormers_raw, list):
        _dormers_list = [d for d in dormers_raw if isinstance(d, dict)]
    else:
        _legacy_single = raw.get("dormer")
        _dormers_list = [_legacy_single] if isinstance(_legacy_single, dict) else []
    measurements["_ai_dormers"] = _dormers_list
    # Back-compat: first entry stays available under the old key so
    # any consumer that hasn't been updated to read the array still
    # gets the primary dormer (and the singular-schema bug it had
    # before is at least no worse).
    measurements["_ai_dormer"] = _dormers_list[0] if _dormers_list else None

    # Iter 79j.28 — dominant colors sampled from the photos. Each hex is
    # validated (must match #RRGGBB) before surfacing so we don't feed
    # garbage into the 3D viewer's color parser.
    def _valid_hex(v):
        if not isinstance(v, str):
            return None
        s = v.strip()
        if len(s) == 7 and s[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in s[1:]):
            return s
        return None

    colors_raw = raw.get("dominant_colors") if isinstance(raw.get("dominant_colors"), dict) else {}
    measurements["_ai_siding_color_hex"] = _valid_hex(colors_raw.get("siding_hex"))
    measurements["_ai_trim_color_hex"] = _valid_hex(colors_raw.get("trim_hex"))
    measurements["_ai_roof_color_hex"] = _valid_hex(colors_raw.get("roof_hex"))
    measurements["_ai_door_color_hex"] = _valid_hex(colors_raw.get("door_hex"))

    # Apply material math per roof type (extracted to
    # apply_roof_type_material_math above so it's directly unit-testable).
    gable_sqft, dormer_sqft = apply_roof_type_material_math(raw, walls, gable_sqft, dormer_sqft)
    measurements["_ai_gable_sqft"] = round(gable_sqft, 1)
    measurements["_ai_dormer_sqft"] = round(dormer_sqft, 1)

    # Iter 78z — Per-elevation breakdown (lap / shake / B&B / etc.) so
    # the takeoff card can render a profile-by-elevation table and the
    # catalog mapper can split siding into multiple SKU lines.
    try:
        from profile_callouts import breakdown_walls_by_profile, apply_annotations_to_breakdown
        breakdown = breakdown_walls_by_profile(walls)
        # Iter 78z — apply user annotations as authoritative accent
        # overrides (from the ProfileAnnotator UI). Annotations win
        # within the boxed region; Claude's auto-detect still drives
        # body/gable/dormer outside the box.
        breakdown = apply_annotations_to_breakdown(breakdown, annotations)
        measurements["_per_elevation_breakdown"] = breakdown["per_elevation"]
        measurements["_per_profile_sqft"] = breakdown["per_profile_sqft"]
    except Exception:
        # Never let the breakdown helper block a successful measurement
        # response — Claude's wall data may have unusual shapes from old
        # sessions.
        measurements["_per_elevation_breakdown"] = []
        measurements["_per_profile_sqft"] = {}
    return measurements


@router.post("/ai-measure")
async def ai_measure(
    files: list[UploadFile] = File(default=[]),
    photo_paths: Optional[str] = Form(None),
    reference_dim: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    kind: str = Form("siding"),
    overhang_in: float = Form(12.0),
    # Iter 57g — optional course-counting context. If the contractor
    # tells us the brick course or siding exposure, Claude can size
    # windows by counting visible courses (way more accurate than
    # eyeballing pixel ratios). Defaults are residential standards.
    brick_course_in: Optional[float] = Form(None),       # e.g. 8.0 for standard 3-bricks-per-8"
    siding_exposure_in: Optional[float] = Form(None),    # e.g. 5.0 for D5 lap, 6.0 for D6, 7.0 for Cedar Impressions
    # Iter 57j — Deep Dormer Scan. When True, after the main multi-photo
    # Claude pass we ALSO fan out a parallel pass per ground-level photo
    # that crops the top 38% of the image, 2× upscales it, and asks
    # Claude to look ONLY for dormers / gable windows / eyebrow vents.
    # Catches small dormers that get lost when Claude downsizes
    # full-house photos to 1568 px. Default OFF (~5–10 s slower).
    deep_dormer_scan: bool = Form(False),
    # Comma-aligned list of per-photo elevation tags ("front,back,left,
    # right,aerial,detail,...") matching the order of `photo_paths` then
    # `files`. Used to skip aerial/detail shots in the dormer pass and
    # to seed `wall_hint` so the dormer pass can tag found dormers on
    # the right wall without guessing.
    elevation_tags: Optional[str] = Form(None),
    # Iter 57r — Resume support. When the caller is running this from
    # inside an estimate, pass `estimate_id` so we can persist the run
    # against it. Then `GET /ai-measure/latest-for-estimate/{eid}` can
    # return the most recent in-flight or done run, letting the
    # frontend "Resume" after a page reload / screen lock.
    estimate_id: Optional[str] = Form(None),
    # Iter 79j.15 — A/B model choice. Allowed keys are the keys of
    # `_MODEL_CHOICES` (claude-opus-4-5, claude-opus-4-8, gemini-3.5-flash,
    # gpt-5.5, etc.). Blank / unknown → default (Opus 4.5).
    model_choice: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """Kick off an async AI photo-measure run. Iter 57q: the old
    synchronous flow was hitting Kubernetes ingress timeouts (~100 s)
    on 8-photo houses with Deep Dormer Scan enabled. Now this route
    just validates inputs + spawns a background worker, returning
    `{run_id, status: "running"}` in under a second. The frontend
    polls `/api/measure/ai-measure/status/{run_id}` until the worker
    writes the final result to the `ai_measure_runs` collection.

    `overhang_in` (inches) flows into the soffit piece-count formula so
    the imported qty matches the estimate's current Overhang setting.

    Photos can be passed two ways:
      • Legacy: `files` multipart upload (one per photo).
      • Session-friendly: `photo_paths` — a comma-separated list of
        filenames already uploaded via /api/uploads (lives in UPLOAD_DIR).
        This is how the resumable AI Measure session avoids re-uploading.
    """
    # Resolve raw image bytes from either source.
    image_payloads: list[tuple[str, bytes]] = []  # [(content_type, raw_bytes)]
    # Iter 79j.29 — track ALL photo names so we can persist them on the
    # run doc. Fresh file-uploads used to be discarded (bytes in memory
    # only) — which meant that if the session doc's photo_urls got
    # clobbered, the run was unrecoverable ("Re-run" silently failed
    # with an empty photo grid). Now every file receives a name here
    # AND is written to /api/uploads/ so the frontend can always find
    # it again on Resume / Restore-preview.
    all_photo_names: list[str] = []
    if photo_paths:
        from config import UPLOAD_DIR  # local import to avoid top-level cycle
        for name in [p.strip() for p in photo_paths.split(",") if p.strip()]:
            target = UPLOAD_DIR / name
            if not target.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Uploaded photo {name!r} not found on server",
                )
            data = target.read_bytes()
            ext = name.rsplit(".", 1)[-1].lower()
            ctype = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
            image_payloads.append((ctype, data))
            all_photo_names.append(name)
    if files:
        import uuid as _uuid
        from config import UPLOAD_DIR  # local import to avoid top-level cycle
        for f in files:
            ctype = (f.content_type or "").lower()
            if ctype not in ACCEPTED_MIMES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type {ctype!r} — use JPG, PNG, or WEBP",
                )
            raw = await f.read()
            if len(raw) == 0:
                continue
            image_payloads.append((ctype, raw))
            # Persist to /api/uploads/ so it's addressable + recoverable.
            ext = "jpg" if ctype == "image/jpeg" else ctype.split("/")[-1]
            name = f"ai_{_uuid.uuid4().hex}.{ext}"
            (UPLOAD_DIR / name).write_bytes(raw)
            all_photo_names.append(name)

    if not image_payloads:
        raise HTTPException(status_code=400, detail="At least one photo is required")
    if len(image_payloads) > MAX_FILES:
        raise HTTPException(
            status_code=400, detail=f"Maximum {MAX_FILES} photos per request",
        )
    for _ctype, raw in image_payloads:
        if len(raw) > MAX_BYTES_PER_FILE:
            raise HTTPException(
                status_code=413,
                detail="Photo exceeds 12 MB limit",
            )
    # Compress every photo to fit comfortably under Anthropic's 10 MB
    # base64 cap. Modern phone photos at 8–12 MB explode past the limit
    # once base64-encoded (×1.33). Forces JPEG so we also dodge any
    # PNG-from-screenshot bloat.
    image_payloads = [
        ("image/jpeg", _compress_for_claude(raw)) for _ctype, raw in image_payloads
    ]

    user_id = user["id"]
    # Iter 79j.15 — resolve the A/B model choice up front so the run doc
    # persists it for reporting + the worker can hand it to LlmChat.
    model_key, model_provider, model_name = _resolve_model(model_choice)
    # Iter 79j.42 — Backend-only Anthropic direct route. If the
    # provider is anthropic AND ANTHROPIC_API_KEY is set, use it and
    # bypass the Emergent LiteLLM proxy (and its shared budget cap).
    # Falls back to EMERGENT_LLM_KEY otherwise.
    api_key, _api_key_source = _pick_llm_api_key(model_provider)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "No LLM API key on the server. Set ANTHROPIC_API_KEY (direct) "
                "or EMERGENT_LLM_KEY (Universal Key)."
            ),
        )

    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    # Persist a "running" run doc so the status endpoint can return
    # progress even before the worker writes its first stage update.
    # Image bytes stay in memory in the worker's closure — too large
    # to write into MongoDB (8 photos × 8 MB = 64 MB per run).
    await db.ai_measure_runs.insert_one({
        "run_id": run_id,
        "user_id": user_id,
        "estimate_id": estimate_id,
        "status": "running",
        "stage": "starting",
        "photo_count": len(image_payloads),
        # Iter 57r + 79j.29 — persist ALL photo names, including fresh
        # uploads that came in via `files=`. Prior to 79j.29 fresh files
        # weren't named/persisted, so `photo_paths` could be None on the
        # run doc → resume paths silently failed to rehydrate photoUrls.
        "photo_paths": ",".join(all_photo_names) if all_photo_names else photo_paths,
        "deep_dormer_scan": deep_dormer_scan,
        "kind": kind,
        "address": address,
        # Iter 79j.15 — A/B model tracking
        "model_choice": model_key,
        "model_provider": model_provider,
        "model_name": model_name,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "result": None,
        "error": None,
    })

    # Spawn the worker as a true detached task — outlives the request.
    asyncio.create_task(_execute_ai_measure_worker(
        run_id=run_id,
        image_payloads=image_payloads,
        api_key=api_key,
        user_id=user_id,
        address=address,
        reference_dim=reference_dim,
        kind=kind,
        overhang_in=overhang_in,
        brick_course_in=brick_course_in,
        siding_exposure_in=siding_exposure_in,
        deep_dormer_scan=deep_dormer_scan,
        elevation_tags=elevation_tags,
        estimate_id=estimate_id,
        model_provider=model_provider,
        model_name=model_name,
    ))

    return {
        "run_id": run_id,
        "status": "running",
        "stage": "starting",
        "photo_count": len(image_payloads),
        "deep_dormer_scan": deep_dormer_scan,
    }


# Iter 78z+ — Re-run a previous AI Measure launch using the CACHED
# photo bytes. Mirrors the blueprint rerun: lets the contractor save
# profile annotations and fire a fresh Claude pass without re-uploading
# the photo grid.
@router.post("/ai-measure/rerun/{prev_run_id}")
async def ai_measure_rerun(
    prev_run_id: str,
    payload: Optional[dict] = None,
    user: dict = Depends(get_current_user),
):
    prev = await db.ai_measure_runs.find_one({"run_id": prev_run_id})
    if not prev:
        raise HTTPException(status_code=404, detail="Previous run not found")
    user_id = user["id"]
    if prev.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your run")

    photo_paths_str = prev.get("photo_paths") or ""
    paths = [p.strip() for p in photo_paths_str.split(",") if p.strip()]
    if not paths:
        raise HTTPException(
            status_code=400,
            detail="No cached photos on this run — re-upload to use rerun",
        )
    # Iter 79j.35 — Photos live in TWO places: the ephemeral pod disk
    # (fast path) and MongoDB `upload_blobs` (durable). Ephemeral disk
    # can be wiped by pod restarts / autoscaler churn — a previous
    # bug surfaced as "Cached photos are no longer on disk" even
    # though the user could still SEE the same photos in the UI (they
    # were served via /api/uploads with an implicit rehydrate). Rerun
    # now uses the same self-healing rehydrate path so the two views
    # stay consistent.
    from config import UPLOAD_DIR  # local import to dodge cycle
    from upload_store import rehydrate_to_disk
    image_payloads: list[tuple[str, bytes]] = []
    missing_after_rehydrate: list[str] = []
    for name in paths:
        target = UPLOAD_DIR / name
        if not target.exists():
            restored = await rehydrate_to_disk(name, UPLOAD_DIR)
            if restored and restored.exists():
                target = restored
            else:
                missing_after_rehydrate.append(name)
                continue
        raw = target.read_bytes()
        if not raw:
            missing_after_rehydrate.append(name)
            continue
        # Reuse the same compressor the primary pass uses so the box
        # coordinates from the annotator line up with what Claude sees.
        image_payloads.append((name, _compress_for_claude(raw)))
    if not image_payloads:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cached photos are no longer on disk or in the durable store — "
                "re-upload the photos above and try again."
            ),
        )
    # Non-fatal: some photos rehydrated, others didn't. Log so the
    # frontend can surface a warning banner if it grows a UI for it.
    if missing_after_rehydrate:
        logger.warning(
            "[ai-measure rerun] %d of %d photos unavailable after rehydrate: %s",
            len(missing_after_rehydrate), len(paths), missing_after_rehydrate,
        )

    new_run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    address = prev.get("address")
    estimate_id = prev.get("estimate_id")
    kind = prev.get("kind") or "siding"
    deep_dormer_scan = bool(prev.get("deep_dormer_scan") or False)

    # Iter 79j.35 — Model choice cascade for rerun. The frontend's
    # "Powered by" dropdown now POSTs `{model_choice: "..."}` as an
    # optional JSON body — used so A/B model comparison works from
    # the Re-Run button instead of silently reusing the original
    # run's model. Falls back to the previous run's model_choice if
    # the body is missing (legacy clients).
    model_choice_override = None
    if isinstance(payload, dict):
        _mc = payload.get("model_choice")
        if isinstance(_mc, str) and _mc.strip():
            model_choice_override = _mc.strip()
    model_choice = model_choice_override or prev.get("model_choice") or _DEFAULT_MODEL_KEY
    model_key, model_provider, model_name = _resolve_model(model_choice)

    # Iter 79j.42 — Anthropic-direct routing (backend env only).
    api_key, _api_key_source = _pick_llm_api_key(model_provider)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "No LLM API key on the server. Set ANTHROPIC_API_KEY (direct) "
                "or EMERGENT_LLM_KEY (Universal Key)."
            ),
        )

    # Pull worker params from the previous result's measurements when
    # available; fall back to sane defaults that match the form schema.
    prev_meas = ((prev.get("result") or {}).get("measurements") or {})
    prev_overhang = 12.0
    try:
        if prev_meas.get("overhang_in") is not None:
            prev_overhang = float(prev_meas["overhang_in"])
    except Exception:
        prev_overhang = 12.0

    await db.ai_measure_runs.insert_one({
        "run_id":          new_run_id,
        "user_id":         user_id,
        "estimate_id":     estimate_id,
        "status":          "running",
        "stage":           "starting",
        "photo_count":     len(image_payloads),
        "photo_paths":     ",".join(name for name, _ in image_payloads),
        "deep_dormer_scan": deep_dormer_scan,
        "kind":            kind,
        "address":         address,
        "model_choice":    model_key,
        "rerun_of":        prev_run_id,
        "created_at":      now,
        "updated_at":      now,
        "completed_at":    None,
        "result":          None,
        "error":           None,
    })
    asyncio.create_task(_execute_ai_measure_worker(
        run_id=new_run_id,
        image_payloads=image_payloads,
        api_key=api_key,
        user_id=user_id,
        address=address,
        reference_dim=None,
        kind=kind,
        overhang_in=prev_overhang,
        brick_course_in=None,
        siding_exposure_in=None,
        deep_dormer_scan=deep_dormer_scan,
        elevation_tags=None,
        estimate_id=estimate_id,
        model_provider=model_provider,
        model_name=model_name,
    ))
    return {
        "run_id":           new_run_id,
        "status":           "running",
        "stage":            "starting",
        "photo_count":      len(image_payloads),
        "photos_rehydrated": len(paths) - len(missing_after_rehydrate),
        "photos_missing":   len(missing_after_rehydrate),
        "model_choice":     model_key,
        "deep_dormer_scan": deep_dormer_scan,
        "rerun_of":         prev_run_id,
    }


# ---------------------------------------------------------------------
# Iter 79j.51 — Reconcile-only retry.
#
# When Phase B fails (proxy 502, hang, timeout) but Phase A's
# `raw_per_photo` is persisted, this endpoint reruns Phase B against
# the saved extractions WITHOUT touching Phase A. Recovers a stranded
# run for pennies instead of forcing a full ~$1-$5 re-run.
#
# Auth-gated to the run's owner (or admin). Idempotent: re-invoking
# on an already-successful run resets its Phase B output and re-runs
# reconciliation — callers should confirm before re-running a
# succeeded run (the frontend surfaces this option only on failure).
# ---------------------------------------------------------------------
@router.post("/ai-measure/reconcile-only/{run_id}")
async def ai_measure_reconcile_only(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    run = await db.ai_measure_runs.find_one({"run_id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("user_id") != user["id"] and (user.get("role") or "").lower() not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not your run")
    raw_per_photo = run.get("raw_per_photo") or []
    if not isinstance(raw_per_photo, list) or not raw_per_photo:
        raise HTTPException(
            status_code=400,
            detail=(
                "No saved per-photo extractions on this run — reconcile-only "
                "requires a Phase A output. Use rerun instead."
            ),
        )
    api_key, _source = _pick_llm_api_key("anthropic")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    model_key = run.get("model_choice") or "claude-opus-4-5"
    _key, model_provider, model_name = _resolve_model(model_key)

    now = datetime.now(timezone.utc)
    await db.ai_measure_runs.update_one(
        {"run_id": run_id},
        {"$set": {
            "status": "running",
            "stage": "reconciling",
            "error": None,
            "error_kind": None,
            "completed_at": None,
            "updated_at": now,
            "reconcile_only_retry_at": now,
        }},
    )
    asyncio.create_task(_execute_reconcile_only_worker(
        run_id=run_id,
        api_key=api_key,
        user_id=user["id"],
        extractions=raw_per_photo,
        model_provider=model_provider,
        model_name=model_name,
        address=run.get("address"),
        reference_dim=run.get("reference_dim"),
        annotation_hint=run.get("annotation_hint") or "",
    ))
    logger.info(
        "[ai-measure phase-B] reconcile-only retry dispatched run_id=%s (%d photos in raw_per_photo)",
        run_id, len(raw_per_photo),
    )
    return {
        "run_id": run_id,
        "status": "running",
        "stage": "reconciling",
        "retry_kind": "reconcile_only",
    }


async def _execute_reconcile_only_worker(
    *,
    run_id: str,
    api_key: str,
    user_id: str,
    extractions: list[dict],
    model_provider: str,
    model_name: str,
    address: Optional[str],
    reference_dim: Optional[str],
    annotation_hint: str,
) -> None:
    """Background worker for reconcile-only retry. Runs Phase B against
    the persisted extractions and writes result + raw_ai back onto the
    same run document.
    """
    try:
        final = await _reconcile_extractions(
            api_key=api_key,
            user_id=user_id,
            model_provider=model_provider,
            model_name=model_name,
            extractions=extractions,
            address=address,
            reference_dim=reference_dim,
            annotation_hint=annotation_hint,
        )
        if final.get("_reconciliation_error"):
            friendly = final.get("_reconciliation_error") or "unknown"
            logger.warning("[ai-measure phase-B] reconcile-only retry FAILED: %s", friendly)
            await db.ai_measure_runs.update_one(
                {"run_id": run_id},
                {"$set": {
                    "status": "error",
                    "stage": "error",
                    "error": f"Reconciliation retry failed: {friendly}",
                    "error_kind": "ReconciliationRetryError",
                    "completed_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            return
        # Rebuild the same `result` shape a full pipeline would produce.
        # Downstream code (frontend, apply-measurements) reads
        # `result.raw_ai` + `result.measurements` — we produce both
        # via the same aggregator the main worker uses.
        measurements = _aggregate_to_hover_shape(final, annotations=[])
        result = {
            "raw_ai": final,
            "measurements": measurements,
            "_pipeline": "two_phase_reconcile_only_retry",
        }
        await db.ai_measure_runs.update_one(
            {"run_id": run_id},
            {"$set": {
                "status": "done",
                "stage": "done",
                "result": result,
                "error": None,
                "error_kind": None,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        # Iter 79j.52 — Repoint the estimate's ai_measure_sessions doc
        # so the UI's Resume path surfaces the reconciled result. The
        # session preview is a client-persisted mirror of the last
        # apply-eligible run output; without this hop the frontend
        # restores the pre-failure preview (which still has
        # `_reconciliation_error` and empty walls/dormers). Stamp the
        # run_id into the preview so the Retry Reconciliation button
        # keeps working on future resumes.
        try:
            src_run = await db.ai_measure_runs.find_one({"run_id": run_id})
            estimate_id = (src_run or {}).get("estimate_id")
            if estimate_id:
                run_user = await db.users.find_one({"id": user_id})
                company_id = (run_user or {}).get("company_id")
                preview_payload = {
                    **result,
                    "run_id": run_id,
                    "model": model_name,
                    "model_provider": model_provider,
                }
                await db.ai_measure_sessions.update_one(
                    {"estimate_id": estimate_id, "company_id": company_id},
                    {"$set": {
                        "preview": preview_payload,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                    upsert=False,
                )
                logger.info(
                    "[ai-measure phase-B] reconcile-only session repointed "
                    "run_id=%s estimate_id=%s", run_id, estimate_id,
                )
        except Exception:
            # Non-fatal: the run doc itself is authoritative; missing
            # session update just means the Resume banner surfaces the
            # older preview until the user re-opens the estimate.
            logger.exception(
                "[ai-measure phase-B] reconcile-only session repoint failed run_id=%s",
                run_id,
            )
        logger.info("[ai-measure phase-B] reconcile-only retry DONE run_id=%s", run_id)
    except Exception as e:
        logger.exception("[ai-measure phase-B] reconcile-only worker crashed for run_id=%s", run_id)
        friendly = str(e).strip() or type(e).__name__
        await db.ai_measure_runs.update_one(
            {"run_id": run_id},
            {"$set": {
                "status": "error",
                "stage": "error",
                "error": f"Reconciliation retry crashed: {friendly}",
                "error_kind": type(e).__name__,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )



def _as_aware_utc(dt):
    """Coerce a datetime to a timezone-aware UTC datetime. MongoDB may
    return naive datetimes depending on the driver/codec settings, which
    breaks arithmetic against `datetime.now(timezone.utc)`."""
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/ai-measure/status/{run_id}")
async def ai_measure_status(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """Poll the status of an async AI measure run.

    Returns:
        {
          status: "running" | "done" | "error",
          stage: "starting"|"claude"|"dormer_scan"|"aggregating"|"mapping",
          result: {...measurements/raw_ai/lines/vero_openings...} | None,
          error: str | None,
          elapsed_ms: int,
        }
    """
    doc = await db.ai_measure_runs.find_one({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if doc.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your run")
    created = _as_aware_utc(doc.get("created_at"))
    completed = _as_aware_utc(doc.get("completed_at") or doc.get("updated_at"))
    elapsed_ms = None
    if created is not None:
        ref = completed if completed is not None else datetime.now(timezone.utc)
        elapsed_ms = int((ref - created).total_seconds() * 1000)
    return {
        "run_id": run_id,
        "status": doc.get("status"),
        "stage": doc.get("stage"),
        "result": doc.get("result"),
        "error": doc.get("error"),
        # Iter 79j.44 — Surface `error_kind` (exception class name) so
        # the frontend banner can render a "Kind: TimeoutError" hint
        # and the health-check UI can distinguish a per-run failure
        # from a systemic outage.
        "error_kind": doc.get("error_kind"),
        "elapsed_ms": elapsed_ms,
        # Iter 79j.37 — per-photo extractions (two-phase pipeline only).
        # Surfaces to the frontend Debug view so it can display what
        # each individual Claude call ACTUALLY saw, not Claude's after-
        # the-fact recollection embedded in the reconciled JSON.
        "raw_per_photo": doc.get("raw_per_photo") or None,
        "pipeline": ((doc.get("result") or {}).get("raw_ai") or {}).get("_pipeline")
                    or ("two_phase" if doc.get("raw_per_photo") else "single_call"),
    }


# ---------------------------------------------------------------------
# Iter 79j.45 — AI Measure health ping.
#
# Contractors were seeing a full ~5 min Phase A hang whenever the
# Emergent LLM Key budget was already exhausted (every LiteLLM request
# retried internally and eventually returned "Budget has been
# exceeded"). This endpoint fires the smallest possible Claude call
# (max_tokens=1, tight 5s deadline) so the frontend can flip the Run
# button to a specific "budget exhausted" / "service unavailable"
# state BEFORE the contractor wastes a full run.
#
# Design rules (per Howard):
#   1. Cache 45s server-side. Never ping on every render.
#   2. Distinguish outcomes: ok | budget_exceeded | unavailable |
#      ambiguous. Do NOT collapse every failure into "budget".
#   3. A broken health check must NEVER hard-lock the Run button —
#      "ambiguous" is a soft warning and the frontend keeps Run enabled.
# ---------------------------------------------------------------------

_AI_HEALTH_CACHE: dict = {"checked_at": 0.0, "payload": None}
_AI_HEALTH_TTL_SEC = 45


def _classify_health_error(err_msg: str) -> tuple[str, str]:
    """Map a raw exception string to (status, detail). Kept ONLY for
    the health endpoint — the main pipeline needs no such heuristics."""
    low = (err_msg or "").lower()
    if "budget has been exceeded" in low or "budget exceeded" in low or "max budget" in low:
        return "budget_exceeded", (
            "Universal Key budget is spent. Open Profile → Universal Key → "
            "Add Balance (or enable Auto Top-up) in the top-right platform menu."
        )
    if "timeout" in low or "timed out" in low or "read timed" in low:
        return "unavailable", "AI service is not responding right now — retry in a minute."
    if "connection" in low or "unreachable" in low or "dns" in low or "network" in low:
        return "unavailable", "Can't reach the AI service — retry in a minute."
    if "unauthor" in low or ("invalid" in low and "key" in low) or "forbidden" in low:
        return "unavailable", "AI service refused the request — the key may be misconfigured."
    # Anything we don't recognise is ambiguous — the frontend keeps
    # Run enabled with a soft warning. NEVER collapse an unknown error
    # into "budget exhausted" or the next diagnosis will be wrong.
    return "ambiguous", f"AI service returned an unexpected response: {err_msg[:180]}"


# ---------------------------------------------------------------------
# Iter 79j.49 — Admin-gated debug log tail.
#
# TEMPORARY. Ship for the current production incident, then REMOVE once
# the LiteLLM latency root cause is understood. The deployed platform's
# log viewer only shows raw HTTP access lines, not application logger
# output, so we surface the last N in-memory log records via a
# curl-friendly endpoint.
#
# Reads from the ring buffer attached to the ROOT logger in server.py
# (see `_RingBufferLogHandler`) — captures every `logger.info/warn/error`
# call across all modules, including the `[ai-measure phase-A] photo N`
# instrumentation.
#
# Auth: admin-only (role in {"owner", "supplier_admin"}). Never expose
# to end users.
# ---------------------------------------------------------------------
_ADMIN_ROLES = {"owner", "supplier_admin", "admin"}


@router.get("/ai-measure/debug-log-tail")
async def ai_measure_debug_log_tail(
    grep: str | None = None,
    lines: int = 300,
    user: dict = Depends(get_current_user),
):
    """Return the last N in-memory log records, optionally filtered by
    a substring match. Admin-only.

    Query params:
        grep:  case-insensitive substring; if provided, only records
               containing it are returned. Multiple terms may be
               separated by `,` — a record matching ANY term is kept.
        lines: cap on returned records (default 300, max 2000).
    """
    role = (user.get("role") or "").lower()
    if role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="admin only")

    # Import lazily to avoid a circular import between server.py and
    # this route module at startup.
    from server import LOG_RING

    all_lines = list(LOG_RING.buffer)
    if grep:
        needles = [t.strip().lower() for t in grep.split(",") if t.strip()]
        if needles:
            all_lines = [ln for ln in all_lines if any(n in ln.lower() for n in needles)]

    cap = max(1, min(lines, 2000))
    tail = all_lines[-cap:]
    return {
        "count": len(tail),
        "total_in_buffer": len(LOG_RING.buffer),
        "grep": grep,
        "lines": tail,
    }


@router.get("/ai-measure/health")
async def ai_measure_health(user: dict = Depends(get_current_user)):
    """Cheap round-trip to the LLM proxy so the UI can flip the Run
    button state before a full Phase A is dispatched. Cached 45s.

    Returns:
        {
          status: "ok" | "budget_exceeded" | "unavailable" | "ambiguous",
          detail: str,
          checked_at: iso-8601,
          cached: bool,          # true if served from the 45s cache
          latency_ms: int | None # None when cached
        }
    """
    now = time.time()
    cached = _AI_HEALTH_CACHE.get("payload")
    if cached and (now - _AI_HEALTH_CACHE.get("checked_at", 0.0) < _AI_HEALTH_TTL_SEC):
        return {**cached, "cached": True, "latency_ms": None}

    api_key, _source = _pick_llm_api_key("anthropic")
    if not api_key:
        payload = {
            "status": "unavailable",
            "detail": "No EMERGENT_LLM_KEY configured on the server — contact your admin.",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        _AI_HEALTH_CACHE["payload"] = payload
        _AI_HEALTH_CACHE["checked_at"] = now
        return {**payload, "cached": False, "latency_ms": 0}

    # Smallest possible ping: 1-token completion, tight 5s deadline.
    # Reuses the AI Measure default model so we're testing the SAME
    # provider path a real run would hit — no risk of a health check
    # succeeding against a cheap model while the expensive model fails.
    # Cost ≈ 1 token out × opus rate ≈ $0.00003 per uncached ping.
    t0 = time.time()
    ping_error: str | None = None
    try:
        chat = (
            LlmChat(
                api_key=api_key,
                session_id=f"ai-measure-health-{uuid.uuid4().hex[:8]}",
                system_message="ok",
            )
            .with_model("anthropic", MODEL_NAME)
            .with_params(max_tokens=1)
        )
        await asyncio.wait_for(
            chat.send_message(UserMessage(text=".")),
            timeout=5,
        )
    except asyncio.TimeoutError:
        ping_error = "timeout after 5s"
    except Exception as e:
        ping_error = str(e) or type(e).__name__
    latency_ms = int((time.time() - t0) * 1000)

    if ping_error is None:
        payload = {
            "status": "ok",
            "detail": "AI service reachable.",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        status, detail = _classify_health_error(ping_error)
        payload = {
            "status": status,
            "detail": detail,
            "raw_error": ping_error[:400],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.warning(
            "[ai-measure health] status=%s latency=%dms raw=%s",
            status, latency_ms, ping_error[:200],
        )

    _AI_HEALTH_CACHE["payload"] = payload
    _AI_HEALTH_CACHE["checked_at"] = now
    return {**payload, "cached": False, "latency_ms": latency_ms}


@router.get("/ai-measure/latest-for-estimate/{estimate_id}")
async def ai_measure_latest_for_estimate(
    estimate_id: str,
    user: dict = Depends(get_current_user),
):
    """Iter 57r — Resume support. Returns the most recent AI Measure
    run for this user+estimate (regardless of status), or `null` if
    none exists. Used by the AI Measure modal to surface a "Resume" or
    "Restore preview" banner after a page reload / screen lock.
    """
    user_id = user.get("id") or "anon"
    # Iter 79j.52 — Sort by updated_at (most recent activity) with
    # created_at as tiebreaker. Prior sort was created_at only, which
    # surfaced the newest RUN rather than the most recently reconciled
    # / updated run. A reconcile-only retry on an older run would
    # succeed silently but the UI would still restore the newer
    # failed run's preview.
    doc = await db.ai_measure_runs.find_one(
        {"user_id": user_id, "estimate_id": estimate_id},
        sort=[("updated_at", -1), ("created_at", -1)],
    )
    if not doc:
        return {"run": None}
    created = _as_aware_utc(doc.get("created_at"))
    completed = _as_aware_utc(doc.get("completed_at") or doc.get("updated_at"))
    now = datetime.now(timezone.utc)
    elapsed_ms = None
    age_seconds = None
    if created is not None:
        ref = completed if completed is not None else now
        elapsed_ms = int((ref - created).total_seconds() * 1000)
        age_seconds = int((now - created).total_seconds())
    return {
        "run": {
            "run_id": doc.get("run_id"),
            "status": doc.get("status"),
            "stage": doc.get("stage"),
            "photo_count": doc.get("photo_count"),
            "photo_paths": doc.get("photo_paths"),
            "deep_dormer_scan": doc.get("deep_dormer_scan"),
            "result": doc.get("result"),
            "error": doc.get("error"),
            "elapsed_ms": elapsed_ms,
            "age_seconds": age_seconds,
            # Iter 79j.37 — carry per-photo extractions on the resume
            # payload too, so the Debug view still works after a page
            # reload without re-running.
            "raw_per_photo": doc.get("raw_per_photo") or None,
            "pipeline": ((doc.get("result") or {}).get("raw_ai") or {}).get("_pipeline")
                        or ("two_phase" if doc.get("raw_per_photo") else "single_call"),
        },
    }


# Iter 79j.16 — Per-run cost estimate for the Model Comparison panel.
# Rough approximation using published Anthropic / OpenAI / Google list
# prices as of Feb 2026. Token counts are estimated from photo count
# (~2 K input tokens per image at Claude's 1568 px downscale, similar
# for the other providers) + fixed system + typical output. Precise
# enough for A/B decision-making — not a billing source of truth.
_MODEL_PRICING_PER_M: dict[str, dict[str, float]] = {
    # provider/model_name lowercase-key -> {input, output}
    "claude-opus-4-5":       {"input": 5.00, "output": 25.00},
    "claude-opus-4-8":       {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6":     {"input": 3.00, "output": 15.00},
    "claude-fable-5":        {"input": 10.00, "output": 50.00},
    "gemini-3.5-flash":      {"input": 1.50, "output": 9.00},
    "gemini-3.1-pro":        {"input": 5.00, "output": 25.00},
    "gpt-5.5":               {"input": 5.00, "output": 30.00},
    "gpt-5.4":               {"input": 5.00, "output": 30.00},
}


def _estimate_run_cost_usd(model_choice: str | None, photo_count: int, deep_dormer: bool) -> float | None:
    """Approximate USD cost for one AI Measure run. Returns None if the
    model isn't in the pricing table (e.g. an old run against a
    now-deprecated model). Fine-grained enough to sort A/B runs, not a
    billing document."""
    if not model_choice:
        return None
    price = _MODEL_PRICING_PER_M.get(model_choice.strip().lower())
    if not price:
        return None
    photos = max(1, int(photo_count or 1))
    # Input: system+user prompt (~4K) + per-photo (~2K)
    input_tokens = 4000 + (2000 * photos)
    # Deep Dormer adds a parallel per-photo pass at ~1500 tok each.
    if deep_dormer:
        input_tokens += 1500 * photos
    output_tokens = 2500
    return round(
        (input_tokens / 1_000_000) * price["input"]
        + (output_tokens / 1_000_000) * price["output"],
        4,
    )


@router.get("/ai-measure/history/{estimate_id}")
async def ai_measure_history(
    estimate_id: str,
    limit: int = 5,
    user: dict = Depends(get_current_user),
):
    """Iter 79j.16 — Model comparison history. Returns the last N
    completed runs for this estimate with just the fields needed to
    A/B compare models side-by-side (model + confidence + counts +
    approximate cost). Used by the Model Comparison panel on the AI
    Measure preview. Only runs with `status == 'done'` are returned so
    the panel never shows in-flight or failed runs."""
    user_id = user.get("id") or "anon"
    limit = max(1, min(int(limit or 5), 20))
    cursor = db.ai_measure_runs.find(
        {"user_id": user_id, "estimate_id": estimate_id, "status": "done"},
        sort=[("completed_at", -1)],
        limit=limit,
    )
    runs = []
    async for doc in cursor:
        result = doc.get("result") or {}
        measurements = result.get("measurements") or {}
        raw_ai = result.get("raw_ai") or {}
        # Confidence: try raw_ai first (0-100), fall back to
        # measurements._ai_overall_confidence, then None.
        conf = raw_ai.get("overall_confidence")
        if conf is None:
            conf = measurements.get("_ai_overall_confidence")
        try:
            conf = int(round(float(conf))) if conf is not None else None
        except (TypeError, ValueError):
            conf = None
        # Wall / opening counts from raw_ai
        walls = raw_ai.get("walls") or []
        openings = raw_ai.get("openings") or []
        window_count = sum(1 for o in openings if (o.get("type") or "").lower() == "window")
        door_count = sum(
            int(o.get("count") or 1)
            for o in openings
            if (o.get("type") or "").lower() in {"entry_door", "patio_door", "garage_door"}
        )
        cost_usd = _estimate_run_cost_usd(
            doc.get("model_choice"),
            int(doc.get("photo_count") or 0),
            bool(doc.get("deep_dormer_scan")),
        )
        completed = _as_aware_utc(doc.get("completed_at"))
        created = _as_aware_utc(doc.get("created_at"))
        elapsed_ms = None
        if created is not None and completed is not None:
            elapsed_ms = int((completed - created).total_seconds() * 1000)
        runs.append({
            "run_id": doc.get("run_id"),
            "model_choice": doc.get("model_choice") or "claude-opus-4-5",
            "model_provider": doc.get("model_provider"),
            "model_name": doc.get("model_name") or result.get("model"),
            "completed_at": completed.isoformat() if completed else None,
            "elapsed_ms": elapsed_ms,
            "photo_count": doc.get("photo_count") or 0,
            "deep_dormer_scan": bool(doc.get("deep_dormer_scan")),
            "confidence": conf,
            "wall_count": len(walls),
            "window_count": window_count,
            "door_count": door_count,
            "siding_sqft": measurements.get("siding_sqft") or 0,
            "eaves_lf": measurements.get("eaves_lf") or 0,
            "cost_estimate_usd": cost_usd,
        })
    return {"runs": runs}


# =====================================================================
# Iter 79j.37 — TWO-PHASE EXTRACT + RECONCILE PIPELINE.
#
# The single-call worker (below, unchanged) sends every photo to Claude
# in ONE call — Claude does extraction and reconciliation as a black
# box. That's opaque: when 3 runs return 7 / 8.5 / 12 ft eaves you can't
# tell whether the photos disagreed (detection failure) or the merge
# drifted (reconciliation failure). The two-phase pipeline splits it:
#
#   Phase A — one focused Claude call PER PHOTO, running in parallel.
#             Returns per-photo raw JSON (walls_visible, eave_observed,
#             pitch, gable Δh, dormers, openings visible in THIS photo,
#             sampled colors). Persisted verbatim on the run doc as
#             `raw_per_photo` — the ACTUAL per-photo observations, not
#             Claude's after-the-fact recollection.
#
#   Phase B — one reconciliation Claude call over the array of Phase A
#             JSONs (no images attached). Prompt asks Claude to MERGE
#             into the same top-level schema `_aggregate_to_hover_shape`
#             consumes (walls[], openings[], dormer, avg_wall_height_ft,
#             etc.) and to emit `_reconciliation_notes` explaining
#             every merge/dedup/discard decision.
#
# Gated behind AI_MEASURE_TWO_PHASE=1 for now so the single-call baseline
# stays available. Falls back automatically if any Phase A call fails
# (per-photo failures are isolated — the rest of the run still
# reconciles from whatever came back).

PER_PHOTO_EXTRACT_PROMPT = """You are a residential exterior measurement expert examining ONE
photograph. Your job is EXTRACTION ONLY — you're one of N parallel
readers, and a separate reconciliation step will merge the readings
across all photos. Do NOT try to guess at values that aren't visible
in THIS specific photo — leave them null and say why.

Return ONLY JSON matching this schema. No prose, no markdown, no
```json fences.

{
  "index":                       number,       // photo index as given by the user prompt
  "elevation":                   "front" | "front-left" | "left" | "rear-left" | "back" | "rear-right" | "right" | "front-right" | "aerial" | "detail" | "other",
  "elevation_confidence":        number,       // 0-100
  "elevation_reasoning":         "<1 sentence — what tells you which side>",

  // WHAT THIS PHOTO SHOWS.
  "walls_visible":               ["front" | "back" | "left" | "right"],   // 1 for a cardinal shot, 2 for a corner shot, 0 for an aerial/detail
  "obstructions":                "<1 sentence — anything blocking measurement (trees, vehicles, foreshortening, telephoto compression, low sun, glare)>",

  // EAVE / STORY / PITCH readings FROM THIS PHOTO.
  // These MUST be measured from what YOU see in the photo. If the
  // eave line is obscured or angled too steeply for a confident read,
  // set the number to null and put the reason in the *_reasoning
  // field. NEVER guess.
  "eave_height_ft_observed":     number | null,
  "eave_reasoning":               "<how you measured — course counting, contractor reference, brick coursing, or 'not measurable because …'>",
  "story_count_observed":         1 | 1.5 | 2 | 2.5 | 3 | null,
  "pitch_ratio_observed":         "4/12" | "6/12" | "8/12" | "10/12" | "12/12" | null,
  "pitch_reasoning":              "<if you saw a gable and measured its rise vs run, say so; else null>",

  // GABLE / DORMER readings — ONLY set >0 if visible in THIS photo.
  "gable_triangle_height_ft_observed": number | null,   // height of the triangular peak above the eave, 0 if this photo shows an eave-only wall, null if not visible
  "gable_wall_label":                 "front" | "back" | "left" | "right" | null,   // which wall the gable belongs to (may equal an elevation in walls_visible)
  "dormers_observed_count":           number,           // count of dormers visible in THIS photo (0 if none)
  "dormer_details": [
    {"face": "front" | "rear" | "left" | "right",
     "approx_width_ft": number,
     "approx_face_sqft": number,
     "bbox": [x, y, w, h] | null}                         // pixel bbox in this photo's compressed frame
  ],

  // OPENINGS visible in THIS photo. `opening_id` must be a STABLE id
  // (e.g. "front-w1", "back-d2") — the reconciliation step will use
  // it to dedup the same physical opening seen in two photos (a
  // corner shot + a cardinal shot commonly overlap by 1–3 openings).
  "openings_this_photo": [
    {"opening_id":    "<stable string id — UNIQUE WITHIN THIS PHOTO. Reconciliation cannot use this to match across photos (each Phase A call is independent) so use position — see `along_wall_ft` below — for cross-photo dedup>",
     "type":          "window" | "entry_door" | "patio_door" | "garage_door" | "vent" | "other",
     "style":         "Double Hung" | "Casement" | "Picture" | "Twin Double Hung" | "Twin Casement" | "2-Lite Slider" | "3-Lite Slider" | "Half-Round" | "Awning" | "Hopper" | "Garden Window" | "Bay Window" | "Bow Window" | "",
     "style_confidence": number,   // 0-100
     "width_in":      number,
     "height_in":     number,
     "wall_hint":     "front" | "back" | "left" | "right" | "on_dormer" | null,
     "bbox":          [x, y, w, h] | null,
     // Iter 79j.40 — Position along the wall, measured from the LEFT
     // corner as viewed from OUTSIDE the house looking at that wall.
     // This is how cross-photo dedup identifies "the same physical
     // window" — (wall, type, size) alone MURDERS twins (two 36×60
     // double-hungs on the same bedroom wall become one). If you
     // can't estimate the position (foreshortened / partial view),
     // set null and the reconciler will KEEP the opening rather
     // than risk a false-positive dedup. Estimate from wall corners
     // or reference dims visible in this photo; use full-wall span
     // as denominator (e.g. window centered in a 32 ft wall →
     // along_wall_ft ≈ 16).
     "along_wall_ft": number | null,
     "on_dormer":     boolean,
     "profile_around_opening": "<lap, dutch_lap, shake, board_and_batten, vertical, brick, stone, stucco, or empty>"}
  ],

  // SIDING PROFILE + COLOR sampling FROM THIS PHOTO.
  // These feed reconciliation across photos (a sunlit sample beats a
  // shaded one for color truth).
  "wall_body_profile_callout":    "<lap 4\\\", dutch lap, shake, board_and_batten, vertical, nickel_gap, or empty>",
  "gable_profile_callout":        "<same vocab; empty if no gable visible>",
  "dormer_profile_callout":       "<same vocab; empty if no dormer visible>",
  "accent_profiles":              [ {"location": "<porch face, column wrap, etc>", "profile_callout": "shake|b&b|vertical|...", "approx_sqft": number} ],
  "colors_sampled": {
    "siding_hex":  "#RRGGBB" | null,   // null if this photo is fully shaded or the sample would be untrustworthy
    "trim_hex":    "#RRGGBB" | null,
    "roof_hex":    "#RRGGBB" | null,
    "door_hex":    "#RRGGBB" | null,
    "sample_quality": "sunlit" | "shaded" | "backlit" | "mixed"
  },
  "no_siding_regions": [   // masonry / stucco / EIFS zones on THIS wall that reduce siding coverage
    {"material": "brick" | "stone" | "cmu" | "stucco" | "eifs",
     "approx_sqft": number,
     "bbox": [x, y, w, h] | null}
  ],

  "confidence": number,   // 0-100 overall confidence in THIS photo's readings
  "notes":       "<optional additional observations>"
}

RULES:
1. NUMBERS ARE HONEST OR NULL. If you can't measure, put null and say
   why in the *_reasoning field. Merging null across 6 photos is far
   more useful than merging 6 confabulated numbers.
2. GARAGE DOORS & ENTRY DOORS ARE OPENINGS, not "no siding" masonry.
   Emit them in `openings_this_photo` with the correct type.
3. IF THIS PHOTO IS AERIAL / DETAIL / OTHER, set walls_visible=[] and
   fill only what the photo actually shows (rooftop shape, dormer
   count from above, etc). Do NOT invent eave heights from an aerial.
4. bbox coordinates are PIXEL space in the compressed image you were
   given (not the original 4K upload). Emit them so we can draw them
   back on the thumbnail in the debug view.
"""


RECONCILE_PROMPT = """You are a residential exterior measurement expert. You are given
N per-photo extractions of the SAME house (each is a JSON blob from a
separate Claude call examining one photo). Your job is RECONCILIATION:
merge them into a single house measurement, dedup openings, average
eave heights sensibly, resolve conflicts, and explain every decision.

Return ONLY JSON matching this schema — the SAME schema the single-
call worker returns, so downstream code doesn't fork.

{
  "scale_confidence":     "high" | "medium" | "low",
  "reference_used":       "<short — reference the extractions leaned on most>",
  "story_count":          1 | 1.5 | 2 | 2.5 | 3,
  "story_count_reasoning": "<1 sentence>",
  "avg_wall_height_ft":   number,        // weighted average of the valid per-photo `eave_height_ft_observed` — see rules below
  "siding_coverage_pct":  number,        // 0-100
  "roof_type":            "gable" | "hip" | "gable-shed-dormer",
  "roof_type_confidence": number,        // 0.0-1.0
  "roof_type_reasoning":  "<1 sentence>",
  "dominant_colors": {"siding_hex": "#RRGGBB" | null, "trim_hex": "#RRGGBB" | null, "roof_hex": "#RRGGBB" | null, "door_hex": "#RRGGBB" | null},
  "dormers": [
    // Iter 79j.41 — ARRAY. A house can carry a dormer on each roof
    // slope (front + rear shed dormers, or 4 gable dormers on a hip
    // roof, etc.). Emit ONE entry PER PHYSICAL DORMER. Do NOT collapse
    // multiple dormers into one — the "missing right dormer" bug on
    // the red house was a singular-schema truncation.
    {
      "face":                "front" | "rear" | "left" | "right",
      "width_ft":            number,
      "knee_wall_height_ft": number,
      "offset_x_ft":         number,          // horizontal offset from wall centerline; 0 = centered
      // width provenance — same values as the eave rule. Drives the
      // frontend badge: direct_consensus=green (2+ direct views agreed);
      // direct_single_reading=amber (only 1 direct view — can't verify);
      // direct_disagreement, back_solved_from_opening,
      // estimated_no_direct_view = amber.
      "width_source":        "direct_consensus" | "direct_single_reading" | "direct_disagreement" | "back_solved_from_opening" | "estimated_no_direct_view",
      "_source_photo_indices": [number],
      "_per_photo_readings":  [ {"photo_idx": number, "approx_width_ft": number|null, "role": "width" | "face" | "count" | "rejected", "notes": "<why kept/rejected>"} ],
      "_reconciliation_note":  "<1 sentence explaining face + width choice for THIS dormer>"
    }
  ],
  "walls": [
    {"label": "front" | "back" | "left" | "right",
     "width_ft":                   number,
     "height_ft":                  number,        // final EAVE height for this wall (see rule 1)
     // Iter 79j.38 — Provenance tag for the eave height. Drives the
     // frontend badge color: `direct_consensus` = green (2+ direct
     // readings agreed); `direct_single_reading` = amber (only 1
     // direct view — can't verify); `direct_disagreement` = amber
     // (one direct reading kept, others rejected);
     // `estimated_no_direct_view` = amber-estimated (no photo ever
     // measured this wall, don't quote off it without capturing a
     // direct side shot).
     "height_ft_source":           "direct_consensus" | "direct_single_reading" | "direct_disagreement" | "estimated_no_direct_view",
     "gable_triangle_height_ft":   number,        // 0 if this wall is eave-only
     "dormer_face_sqft":           number,
     "siding_pct_this_wall":       number,        // integer 0-100
     "wall_body_profile_callout":  "<...>",
     "gable_profile_callout":      "<...>",
     "dormer_profile_callout":     "<...>",
     "accent_profiles":            [ ... ],
     "confidence":                 number,        // 0-100
     "confidence_reasoning":       "<1 sentence>",
     // PROVENANCE — every wall carries these fields.
     "_source_photo_indices":      [number],
     "_per_photo_readings":        [ {"photo_idx": number, "eave_ft": number|null, "gable_triangle_ft": number|null, "notes": "<optional>"} ],
     "_reconciliation_note":       "<1 sentence: how the final numbers were merged/averaged/chosen>"}
  ],
  "openings": [
    {"type":     "window" | "entry_door" | "patio_door" | "garage_door" | "vent" | "other",
     "style":    "Double Hung" | ... | "",
     "style_confidence": number,
     "width_in": number,
     "height_in": number,
     "wall":     "front" | "back" | "left" | "right" | "other",
     "photo_idx": number,                            // the PRIMARY photo for this opening (best bbox)
     "bbox":     {"x": number, "y": number, "w": number, "h": number},   // NORMALIZED 0..1 on photo_idx
     "on_dormer": boolean,
     // Iter 79j.40 — Position along the wall (feet from LEFT corner
     // as viewed from outside). REQUIRED for cross-photo dedup — see
     // rule 3. Null when no Phase A photo could estimate it.
     "along_wall_ft": number | null,
     // PROVENANCE.
     "opening_id":               "<stable id preserved from extractions>",
     "_source_photo_indices":    [number],
     "_reconciliation_note":     "<optional — only when you merged or dedup'd. Cite along_wall_ft values from each source photo so the debug view shows why they collapsed (e.g. 'photo 0 at 8.2 ft, photo 2 at 8.4 ft on front wall → same window'). For twins that DID NOT collapse, cite the separation (e.g. 'photo 0 emitted twins at 6.2 ft and 9.4 ft on the front wall; kept both, delta 3.2 ft > sum-of-widths 3.0 ft')>"}
  ],
  "openings_schedule": [
    {"elevation": "<wall>", "type": "<>", "style": "<>", "width_in": number, "height_in": number, "count": number,
     "size_label": "<e.g. '36\\"×60\\"'>", "locations": [ {"photo_idx": number, "bbox": {"x": number, "y": number, "w": number, "h": number}} ]}
  ],

  "eaves_lf":             number,
  "rakes_lf":             number,
  "starter_lf":           number,
  "outside_corner_lf":    number,
  "inside_corner_lf":     number,

  // TOP-LEVEL RECONCILIATION TRACE — one sentence per aggregate.
  "_reconciliation_notes": {
    "avg_wall_height_ft":  "<e.g. 'averaged 4 valid per-photo eaves (photos 0,1,2,4 = 8.5, 8.4, 8.6, 8.5); discarded photo 3 (aerial) and photo 5 (foreshortened corner)'>",
    "roof_type":           "<how the roof-type call was made from the photo counts>",
    "dormers":             "<how each dormer's face/width/offset was chosen. Include a count sentence (e.g. 'detected 2 shed dormers on front and rear slopes')>",
    "story_count":         "<how the story count was merged>",
    "siding_coverage_pct": "<how coverage was reconciled across photos>",
    "dominant_colors":     "<which photo's colors were used, and why (sample_quality preference)>",
    "openings_dedup":      "<how many raw openings across photos → how many after dedup, key overlaps>"
  }
}

RECONCILIATION RULES:

1. EAVE HEIGHT PER WALL — this is the highest-variance number across
   photos (Howard has seen 7 / 8.5 / 12 ft on the same house across
   3 runs) so the rule is strict:

   a) A photo's `eave_height_ft_observed` is ONLY valid for eave
      measurement when the photo has a DIRECT SIDE VIEW of that
      wall's eave line — the soffit/gutter runs roughly horizontal
      across the frame, not receding into perspective. Signals of a
      valid direct view (look in `eave_reasoning`):
        • course counting on THAT wall's siding or brick
        • contractor's reference dimension visible on THAT wall
        • window head / sill measured on THAT wall
      Signals to REJECT:
        • aerial / roof-only / detail photos
        • gable-end shots (front-gable elevation on a front-gable
          house looking at the triangle) — the "eave" the LLM sees
          there is a foreshortened rake, NOT the eave. Gable-end
          photos inform `gable_triangle_height_ft` and pitch ONLY;
          they NEVER inform eave height.
        • corner shots where THIS wall is at >45° foreshortening
        • telephoto compression or extreme wide-angle distortion

   b) Take the valid direct-view readings for this wall. If any two
      valid readings disagree by MORE THAN 1 ft, do NOT average them —
      averaging incompatible readings hides the problem. Instead:
        • Pick the reading with the strongest `eave_reasoning` (course
          counting > contractor reference > head/sill count > pixel
          ratio) and keep it as `height_ft`.
        • Set `height_ft_source: "direct_disagreement"` on the wall.
        • Note the discarded readings and why in
          `_reconciliation_note` so the contractor can trace them.

   c) If NO direct-view reading exists for this wall (every photo of
      it was an aerial, gable-end, or extreme angle), do NOT
      confabulate from the neighbour walls or the avg. Emit
      `height_ft` = null-safe fallback (use the median of the OTHER
      walls' final heights ONLY as a placeholder — houses are usually
      symmetric) and set `height_ft_source: "estimated_no_direct_view"`
      so the frontend can render the value AMBER / estimated. This
      is the signal that says "we never actually measured this wall,
      don't quote off it."

   d) If TWO OR MORE direct readings agree within ±1 ft, take the
      median. `height_ft_source: "direct_consensus"`. Note the count
      of contributing photos in `_reconciliation_note`.

   e) If EXACTLY ONE direct-view reading exists, use it as the eave
      height but set `height_ft_source: "direct_single_reading"`.
      A single reading is a real observation — better than an
      estimated placeholder — but nothing cross-checks it, so the
      frontend renders it amber. The contractor should capture a
      second angle before quoting.

   For every wall, `_per_photo_readings` must include ALL photos that
   attempted this wall (valid AND rejected) so the debug view shows
   which readings were kept vs discarded. Tag rejected rows with a
   `notes` field explaining the rejection (e.g. "rejected — gable-end
   view; foreshortened rake not eave").

2. `avg_wall_height_ft` = weighted average of the FINAL per-wall
   `height_ft` values across the 4 primary walls. Weight by `confidence`.

3. OPENING DEDUP — twins, triples, and matched pairs are COMMON in
   residential construction; naively deduping by (wall, type, size)
   MURDERS them. Two 36×60 double-hungs on the same bedroom wall are
   NOT one window seen twice — they're twins. Same for triple casements
   over a kitchen sink, mulled pairs flanking a fireplace, or 4-unit
   banks on a sunroom.

   Rules of engagement:

   a) `opening_id` IS NOT a cross-photo match key. Phase A calls are
      independent Claude invocations, so IDs are only unique WITHIN
      a photo — the same physical window will have different IDs in
      different photos. Never dedup on opening_id alone.

   b) The ONLY reliable cross-photo dedup signal is POSITION ALONG
      THE WALL. Two openings collapse to one IF AND ONLY IF ALL of:
        (i)   same `wall_hint` (or same reconciled wall)
        (ii)  same `type`
        (iii) `width_in` within ±3" AND `height_in` within ±3"
        (iv)  `along_wall_ft` present in BOTH photos AND agrees
              within ±2 ft
      Missing any one of these = KEEP BOTH.

   c) If `along_wall_ft` is null on one or both photos (foreshortened
      corner, partial view, dormer opening), DO NOT DEDUP even if
      (wall, type, size) match. Emit both entries. False duplicates
      cost less than lost twins — twin loss silently under-quotes the
      window and J-channel takeoff by 50-75%.

   d) Same physical opening seen in a corner shot AND a cardinal shot
      of the same wall should dedup by rule (b) — the along_wall_ft
      estimates should land within ±2 ft since they measure the same
      physical position.

   e) Twin markers: if a photo returns a style of `Twin Double Hung`,
      `Twin Casement`, or emits two openings on the same wall with
      along_wall_ft values differing by less than the sum of their
      widths (i.e. the two windows share a stud between them), they
      are TWINS and MUST both be preserved. Emit them as two rows in
      openings[] with the correct along_wall_ft each.

   f) `openings[]._source_photo_indices` must list every photo that
      contributed to the entry (both the dominant photo and any
      dedup-matched confirmations). If an entry has only one source
      photo, that's fine — many openings are only visible from one
      angle.

   Provenance: for every merged opening (>1 source photo), fill
   `_reconciliation_note` with the along_wall_ft values from each
   source photo so the debug view can show why they collapsed
   (e.g. "photo 0 at 8.2 ft, photo 2 at 8.4 ft on front wall → same
   window").

4. ROOF TYPE — count photos where a gable triangle was visible vs
   photos where the roof ends flat on all sides. Gables on 2+ walls
   → "gable". Gables on 4 walls → still "gable" (a cross-gable is
   still gabled). No gables on any wall but slopes visible → "hip".
   Any photo with `dormers_observed_count > 0` upgrades to
   "gable-shed-dormer".

5. DORMERS (ARRAY) — a house can carry a dormer on each roof slope
   (a matching pair of shed dormers on front + rear is common on
   cape cods and cross-gabled ranches). Emit ONE ENTRY PER PHYSICAL
   DORMER in `dormers[]`. Naive schemas that collapse to a single
   dormer object silently drop the second, third, or fourth dormer —
   the exact bug that made the red house's right-slope dormer
   disappear.

   For EACH dormer, run the width-source rules below. "Widest reading
   wins" was the old trap because a corner shot or a wide-angle lens
   distorts the dormer's apparent width; picking the max amplifies
   whichever photo had the worst geometry.

   a) A photo's `approx_width_ft` is ONLY valid for dormer WIDTH
      measurement when the photo has a DIRECT VIEW of the dormer
      face — the dormer's face wall runs roughly parallel to the
      camera plane, soffits and window heads are horizontal in-
      frame, and the dormer is centered enough that its bbox isn't
      clipped. Valid signals:
        • window(s) on the dormer face are visible full-front (not
          foreshortened rhomboids)
        • horizontal roof edges of the dormer read straight in the
          image, not tilted by perspective
        • the dormer's bbox in `openings_this_photo` covers its full
          width without hitting the photo edge
      REJECT signals:
        • aerial photos (bird's-eye compression flattens dormer width
          unreliably — aerials CAN inform dormer COUNT and which
          roof-face carries them, but NEVER width)
        • corner shots >45° off-axis (foreshortening compresses OR
          exaggerates width depending on angle)
        • telephoto compression (front-yard shots taken from >100 ft)
        • dormer partially clipped by the photo edge

   b) Take the valid direct-view widths. If any two disagree by
      MORE THAN 1 ft, do NOT average or take the max. Instead:
        • Pick the reading whose photo has the strongest evidence
          (widest bbox at valid angle, visible window fully across
          the face, sharpest horizontals).
        • Set `width_source: "direct_disagreement"` for this dormer.
        • Note the rejected readings in this dormer's
          `_reconciliation_note`.

   c) If NO direct-view width reading exists but at least one photo
      saw a window ON the dormer face (`openings_this_photo[]` has
      an entry with `on_dormer: true` OR `wall_hint: "on_dormer"`),
      BACK-SOLVE the width: dormer_width_ft ≈ max(6, window_width_ft
      + 3 ft trim margin per side). Set `width_source:
      "back_solved_from_opening"`.

   d) If no direct view AND no opening-anchored back-solve, emit
      a placeholder (12 ft is the residential median) and set
      `width_source: "estimated_no_direct_view"` so the
      frontend renders it AMBER — same "don't quote off this until
      a direct shot exists" signal as the eave rule.

   e) If TWO OR MORE direct readings agree within ±1 ft, take the
      median. `width_source: "direct_consensus"`. A SINGLE direct
      reading does NOT constitute consensus — see rule (f).

   f) If EXACTLY ONE direct-view reading exists, use it as the width
      but set `width_source: "direct_single_reading"`. This is a
      down-graded green: the width came from a real photo, but we
      couldn't cross-check it. The frontend renders this amber so
      the contractor knows to capture a second angle before quoting.

   DORMER MATCHING ACROSS PHOTOS — a single physical dormer often
   appears in 2+ photos (a corner shot + a cardinal shot). Match by
   `face` (which roof slope) + approximate position. If two photos
   report a dormer on the SAME face with `approx_width_ft` values
   within ±3 ft AND their bbox centers align when projected to the
   wall, they're the same dormer → one entry in `dormers[]` with
   both photos in `_source_photo_indices`. If the faces differ
   (photo 0 says front, photo 3 says rear) they're TWO DIFFERENT
   dormers → two entries. Never collapse different-face dormers.

   FACE assignment: use the wall of the FIRST photo that captured
   the dormer cardinally (a direct perpendicular shot of the face).
   If no cardinal shot exists, default to `front` for the primary
   and preserve the aerial-reported face for any additional ones.

   The reconciliation trace for EACH dormer MUST list every photo
   that saw it and whether that photo contributed to width, face,
   count, or was rejected — the same `_per_photo_readings`-style
   trace the walls carry.

6. COLOR SAMPLING — prefer photos whose `colors_sampled.sample_quality`
   is `sunlit`, then `mixed`, then `shaded`, then `backlit`. If no
   sunlit sample exists for a field, take the median of the shaded ones.

7. LINEAR FEET — eaves_lf ≈ 2×front.width + 2×back.width for a
   rectangular footprint. rakes_lf ≈ 2 × sqrt((span/2)² + rise²) per
   gable end. outside_corner_lf ≈ 4 × avg_wall_height_ft. Don't over-
   engineer — the aggregator will refine, we just need the ballpark.

8. IF A FIELD CANNOT BE RECONCILED (no photo saw it, all readings
   null), leave it at a sane default and mention "no photo captured
   this" in the reconciliation note. Never confabulate.

Return the JSON now. No prose."""


def _clean_json_reply(reply: str) -> dict:
    """Robust JSON parse — tolerates ```json fences, leading prose,
    trailing commas. Reuses the same extractor the primary path uses."""
    try:
        return _json_from_reply(reply or "")
    except Exception:
        return {}


def _env_int(name: str, default: int) -> int:
    """Iter 79j.44 — Read an int env var, tolerating empty / bad values.
    Used for AI Measure timeout knobs so operators can retune Phase A
    budgets without a code change."""
    try:
        v = os.environ.get(name, "").strip()
        if not v:
            return default
        n = int(v)
        return n if n > 0 else default
    except Exception:
        return default



def _is_empty_extraction(parsed: dict) -> bool:
    """Iter 79j.43 — A Phase A extraction is "empty" when Claude
    returned nothing useful: no walls seen, no openings, no eave
    reading, no pitch, no dormers, no gable. Empty extractions
    silently orphan whichever walls only that photo covered, so
    the orchestrator retries once and (if still empty) flags a
    UI warning."""
    if not isinstance(parsed, dict) or parsed.get("_extraction_error"):
        return True
    walls_visible = parsed.get("walls_visible") or []
    openings = parsed.get("openings_this_photo") or []
    eave = parsed.get("eave_height_ft_observed")
    pitch = parsed.get("pitch_ratio_observed")
    gable_h = parsed.get("gable_triangle_height_ft_observed")
    dormers = parsed.get("dormers_observed_count")
    has_walls = isinstance(walls_visible, list) and any((w or "").strip() for w in walls_visible if isinstance(w, str))
    has_openings = isinstance(openings, list) and len(openings) > 0
    has_eave = eave not in (None, 0, 0.0, "")
    has_pitch = pitch not in (None, 0, 0.0, "")
    has_gable = gable_h not in (None, 0, 0.0, "")
    has_dormers = dormers not in (None, 0, "")
    return not (has_walls or has_openings or has_eave or has_pitch or has_gable or has_dormers)


async def _extract_one_photo(
    *,
    api_key: str,
    user_id: str,
    model_provider: str,
    model_name: str,
    photo_idx: int,
    raw_bytes: bytes,
    address: Optional[str],
    reference_dim: Optional[str],
    brick_course_in: Optional[float],
    siding_exposure_in: Optional[float],
    annotation_hint: str,
) -> dict:
    """Phase A. Run ONE Claude call against a single photo, ask for
    per-photo raw observations only. Returns the parsed JSON tagged
    with `_photo_idx` and `_latency_ms` (persisted verbatim so the
    Debug view can show what Claude actually saw).

    Iter 79j.43 — If the first call returns empty, retry ONCE with a
    stronger nudge. Empty photos silently orphan any wall only they
    covered, so the orchestrator MUST know when this happens."""
    t0 = time.time()
    prompt_lines = [f"This is photo index {photo_idx} of a house being measured for siding."]
    if address:
        prompt_lines.append(f"Property address: {address}")
    if reference_dim:
        prompt_lines.append(
            f"Contractor reference dimension available: {reference_dim}. "
            "If the reference object is visible in THIS photo, anchor scale to it."
        )
    if brick_course_in and brick_course_in > 0:
        prompt_lines.append(
            f"BRICK COURSE = {brick_course_in:.2f} in. Count courses to size windows if brick is visible in this photo."
        )
    if siding_exposure_in and siding_exposure_in > 0:
        prompt_lines.append(
            f"SIDING EXPOSURE = {siding_exposure_in:.2f} in per row. Count rows to size windows on siding-clad walls."
        )
    if annotation_hint:
        prompt_lines.append(annotation_hint)
    prompt_lines.append(
        "Return your per-photo extraction JSON now, with `index` set to "
        f"{photo_idx}. No prose."
    )
    prompt_text = "\n".join(prompt_lines)

    # Iter 79j.44 — Env-configurable per-call timeout (default 120s).
    # Per-call = one LlmChat send. Two calls (initial + empty-retry)
    # give ~240s worst-case per photo, capped further by
    # AI_MEASURE_PER_PHOTO_TIMEOUT (see below).
    per_call_timeout = _env_int("AI_MEASURE_PER_CALL_TIMEOUT", 120)
    logger.info("[ai-measure phase-A] photo %d start", photo_idx)

    async def _one_call(retry_note: str = "") -> dict:
        call_t0 = time.time()
        chat = LlmChat(
            api_key=api_key,
            session_id=f"ai-measure-photo-{user_id}-{photo_idx}-{uuid.uuid4().hex[:6]}",
            system_message=PER_PHOTO_EXTRACT_PROMPT,
        ).with_model(model_provider, model_name)
        text = prompt_text if not retry_note else f"{retry_note}\n\n{prompt_text}"
        user_msg = UserMessage(
            text=text,
            file_contents=[ImageContent(image_base64=base64.b64encode(raw_bytes).decode("ascii"))],
        )
        try:
            reply = await asyncio.wait_for(chat.send_message(user_msg), timeout=per_call_timeout)
        except asyncio.TimeoutError:
            elapsed = int((time.time() - call_t0) * 1000)
            logger.warning("[ai-measure phase-A] photo %d call timed out after %ds", photo_idx, per_call_timeout)
            return {
                "index": photo_idx,
                "_extraction_error": f"per-call timeout after {per_call_timeout}s",
                "_extraction_error_kind": "timeout",
                "_latency_ms": elapsed,
            }
        except Exception as e:
            elapsed = int((time.time() - call_t0) * 1000)
            logger.warning("[ai-measure phase-A] photo %d call failed after %dms: %s", photo_idx, elapsed, e)
            return {
                "index": photo_idx,
                "_extraction_error": str(e) or type(e).__name__,
                "_extraction_error_kind": "exception",
                "_latency_ms": elapsed,
            }
        p = _clean_json_reply(reply or "")
        p["_photo_idx"] = photo_idx
        p.setdefault("index", photo_idx)
        p["_latency_ms"] = int((time.time() - call_t0) * 1000)
        return p

    parsed = await _one_call()
    # Iter 79j.43 — Empty-extraction retry. One additional call with an
    # explicit "look harder" nudge. Still empty → mark and continue.
    if _is_empty_extraction(parsed):
        logger.warning("[ai-measure phase-A] photo %d returned empty; retrying once", photo_idx)
        retry_nudge = (
            "The previous response was empty. This photo DOES show part of "
            "a house — even a partial view of one wall, one window, or one "
            "roof edge is worth extracting. Fill every field you can. Only "
            "if the photo is genuinely NOT a house exterior (e.g. interior, "
            "landscape, blurry) return an empty JSON with `notes` explaining why."
        )
        retry_parsed = await _one_call(retry_note=retry_nudge)
        retry_parsed["_empty_retry_attempted"] = True
        if _is_empty_extraction(retry_parsed):
            retry_parsed["_empty_extraction"] = True
            # Iter 79j.44 — If the retry itself was a timeout/exception,
            # surface that in the reason so the UI can distinguish
            # "photo unusable" from "network flaked".
            if retry_parsed.get("_extraction_error_kind") == "timeout":
                retry_parsed["_empty_reason"] = f"Retry timed out after {per_call_timeout}s — LLM proxy slow or unreachable."
            elif retry_parsed.get("_extraction_error"):
                retry_parsed["_empty_reason"] = f"Retry failed: {retry_parsed.get('_extraction_error')}"
            else:
                retry_parsed["_empty_reason"] = "Two consecutive empty Claude responses — photo may be interior, blurry, or not a house exterior."
            logger.warning("[ai-measure phase-A] photo %d STILL empty after retry — orphan risk", photo_idx)
        # Preserve original _latency_ms behaviour but add total
        retry_parsed["_total_latency_ms"] = int((time.time() - t0) * 1000)
        logger.info(
            "[ai-measure phase-A] photo %d done in %dms (empty=%s, retried=1)",
            photo_idx, retry_parsed["_total_latency_ms"], bool(retry_parsed.get("_empty_extraction")),
        )
        return retry_parsed
    parsed["_total_latency_ms"] = int((time.time() - t0) * 1000)
    logger.info(
        "[ai-measure phase-A] photo %d done in %dms (empty=False, error=%s)",
        photo_idx, parsed["_total_latency_ms"], parsed.get("_extraction_error") or "no",
    )
    return parsed


async def _reconcile_extractions(
    *,
    api_key: str,
    user_id: str,
    model_provider: str,
    model_name: str,
    extractions: list[dict],
    address: Optional[str],
    reference_dim: Optional[str],
    annotation_hint: str,
) -> dict:
    """Phase B. Send the Phase A extractions as TEXT (no images) and
    ask for a single reconciled house JSON matching the aggregator's
    schema. Returns the parsed JSON with `_reconciliation_latency_ms`
    added for observability."""
    t0 = time.time()
    chat = LlmChat(
        api_key=api_key,
        session_id=f"ai-measure-reconcile-{user_id}-{uuid.uuid4().hex[:8]}",
        system_message=RECONCILE_PROMPT,
    ).with_model(model_provider, model_name)
    lines = [
        "You are reconciling the following per-photo extractions into a "
        "single house measurement. Each JSON below is one photo, in "
        "order. Photo indices ARE the array positions.",
        "",
        f"Photos: {len(extractions)}",
    ]
    if address:
        lines.append(f"Property address: {address}")
    if reference_dim:
        lines.append(f"Contractor reference dimension: {reference_dim}")
    if annotation_hint:
        lines.append(annotation_hint)
    lines.append("")
    lines.append("=== PER-PHOTO EXTRACTIONS ===")
    total_slim_bytes = 0
    total_orig_bytes = 0
    for i, ex in enumerate(extractions):
        # Iter 79j.51 — Every KB off the Phase B payload matters given
        # the payload-driven proxy serialization documented in Iter 79j.50.
        # `_slim_extraction_for_reconcile` strips fields the reconciler
        # doesn't consume (per-photo pixel bboxes — the reconciler emits
        # its own normalized bboxes on the primary photo, and doesn't
        # have source-photo dimensions to convert from pixel space anyway).
        # Reasoning strings, confidence, notes, along_wall_ft — all
        # RETAINED because RECONCILE_PROMPT explicitly cites them.
        slim = _slim_extraction_for_reconcile(ex)
        slim_json = json.dumps(slim, ensure_ascii=False, indent=2)
        total_slim_bytes += len(slim_json)
        total_orig_bytes += len(json.dumps(
            {k: v for k, v in ex.items() if not k.startswith("_")},
            ensure_ascii=False, indent=2,
        ))
        lines.append(f"\n-- photo[{i}] --")
        lines.append(slim_json)
    logger.info(
        "[ai-measure phase-B] reconcile payload %d → %d bytes (%.2fx)",
        total_orig_bytes, total_slim_bytes,
        total_orig_bytes / max(1, total_slim_bytes),
    )
    lines.append("")
    lines.append("Return the reconciled house JSON now. No prose.")
    try:
        reply = await asyncio.wait_for(
            chat.send_message(UserMessage(text="\n".join(lines))),
            timeout=180,
        )
    except Exception as e:
        logger.exception("[ai-measure phase-B] reconciliation failed: %s", e)
        return {"_reconciliation_error": str(e), "_reconciliation_latency_ms": int((time.time() - t0) * 1000)}
    parsed = _clean_json_reply(reply or "")
    parsed["_reconciliation_latency_ms"] = int((time.time() - t0) * 1000)
    return parsed


def _slim_extraction_for_reconcile(ex: dict) -> dict:
    """Iter 79j.51 — Return a copy of `ex` with reconciler-unread bulk
    stripped. See docstring comment above for the rationale.

    KEEP:
        - `elevation_reasoning`, `eave_reasoning`, `pitch_reasoning`,
          `obstructions`, `notes`, `confidence_reasoning`, `notes` —
          RECONCILE_PROMPT explicitly cites these for its
          `_reconciliation_note` generation.
        - `along_wall_ft` on openings — required for cross-photo dedup.
        - `style_confidence`, `elevation_confidence`, `confidence`,
          `sample_quality` — used to weight readings.

    DROP:
        - `bbox` on `openings_this_photo`, `dormer_details`,
          `no_siding_regions`. These are pixel-space in the compressed
          image. The reconciler outputs its own NORMALIZED bboxes and
          doesn't have source-photo dimensions in this payload to
          convert accurately from pixel space anyway.
        - Any leading-underscore keys (internal state — already stripped
          by the pre-existing rule).
    """
    slim: dict = {}
    for k, v in ex.items():
        if k.startswith("_"):
            continue
        if k == "openings_this_photo" and isinstance(v, list):
            slim[k] = [{ok: ov for ok, ov in o.items() if ok != "bbox"} for o in v]
            continue
        if k == "dormer_details" and isinstance(v, list):
            slim[k] = [{dk: dv for dk, dv in d.items() if dk != "bbox"} for d in v]
            continue
        if k == "no_siding_regions" and isinstance(v, list):
            slim[k] = [{rk: rv for rk, rv in r.items() if rk != "bbox"} for r in v]
            continue
        slim[k] = v
    return slim


async def _run_two_phase_pipeline(
    *,
    run_id: str,
    api_key: str,
    user_id: str,
    image_payloads: list[tuple[str, bytes]],
    model_provider: str,
    model_name: str,
    address: Optional[str],
    reference_dim: Optional[str],
    brick_course_in: Optional[float],
    siding_exposure_in: Optional[float],
    annotation_hint: str,
    set_stage,   # async callable(str) → None
) -> tuple[dict, list[dict]]:
    """Orchestrator. Returns (final_raw_after_reconcile, per_photo_extractions).
    Callers should feed final_raw into `_aggregate_to_hover_shape` — it's
    already the same shape that the single-call worker returns."""
    await set_stage("extracting_per_photo")
    # Iter 79j.44 — Per-photo hard budget (default 240s = one full call
    # + one empty-retry at 120s each). Wrapping each task in its own
    # wait_for guarantees a single slow photo cannot bleed into the
    # global cap, and — critically — its timeout becomes a per-photo
    # `_extraction_error` instead of a batch-wide CancelledError.
    per_photo_budget = _env_int("AI_MEASURE_PER_PHOTO_TIMEOUT", 240)
    phase_a_total = _env_int("AI_MEASURE_PHASE_A_TIMEOUT", 300)
    phase_a_started = time.time()

    # Iter 79j.50 — Aggressive per-photo shrink before dispatch. The
    # LiteLLM proxy was empirically shown to serialize concurrent
    # large-payload calls (185s wall clock for 3 parallel large calls
    # vs 4.89s for 3 parallel small calls, same model + endpoint).
    # Shrink attacks the root cause — small payloads truly parallelize.
    max_dim = _env_int("AI_MEASURE_PHASE_A_MAX_DIM", 1600)
    jpeg_q = _env_int("AI_MEASURE_PHASE_A_JPEG_Q", 80)
    shrunk_payloads: list[tuple[str, bytes]] = []
    total_before = 0
    total_after = 0
    for idx, (_ct, raw) in enumerate(image_payloads):
        shrunk, stats = _shrink_for_phase_a(raw, max_dim=max_dim, jpeg_q=jpeg_q)
        total_before += stats["original_bytes"]
        total_after += stats["final_bytes"]
        logger.info(
            "[ai-measure phase-A] photo %d shrunk %s → %s (%d → %d bytes, %.2fx)",
            idx,
            stats.get("original_dim", "?"),
            stats.get("final_dim", "?"),
            stats["original_bytes"],
            stats["final_bytes"],
            stats.get("ratio", 1.0),
        )
        shrunk_payloads.append(("image/jpeg", shrunk))
    if total_before > 0:
        logger.info(
            "[ai-measure phase-A] total payload %d → %d bytes (%.1fx reduction)",
            total_before, total_after, total_before / max(1, total_after),
        )

    # Iter 79j.50 — Concurrency limit. Even with shrunk payloads there's
    # residual per-key rate limiting on the proxy. Semaphore caps
    # concurrent Claude calls to N (default 2). 2 keeps us under any
    # proxy throttling while still parallel enough that 8 photos finish
    # in 4×per_photo_latency instead of 8×.
    concurrency = _env_int("AI_MEASURE_PHASE_A_CONCURRENCY", 2)
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _budgeted_extract(idx: int, raw: bytes) -> dict:
        # The semaphore MUST be inside the coroutine (not around
        # create_task) so `asyncio.wait` sees each task as immediately
        # scheduled and its per-photo timer starts only when the sem
        # actually grants entry, not while waiting in the queue.
        async with sem:
            try:
                return await asyncio.wait_for(
                    _extract_one_photo(
                        api_key=api_key,
                        user_id=user_id,
                        model_provider=model_provider,
                        model_name=model_name,
                        photo_idx=idx,
                        raw_bytes=raw,
                        address=address,
                        reference_dim=reference_dim,
                        brick_course_in=brick_course_in,
                        siding_exposure_in=siding_exposure_in,
                        annotation_hint=annotation_hint,
                    ),
                    timeout=per_photo_budget,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[ai-measure phase-A] photo %d exceeded per-photo budget of %ds — flagged empty",
                    idx, per_photo_budget,
                )
                return {
                    "index": idx,
                    "_photo_idx": idx,
                    "_extraction_error": f"per-photo budget exceeded ({per_photo_budget}s)",
                    "_extraction_error_kind": "timeout",
                    "_empty_extraction": True,
                    "_empty_reason": f"Photo timed out after {per_photo_budget}s — LLM proxy slow or unresponsive.",
                    "_latency_ms": per_photo_budget * 1000,
                    "_total_latency_ms": per_photo_budget * 1000,
                }
            except Exception as e:  # never let one photo kill the batch
                logger.exception("[ai-measure phase-A] photo %d unexpected failure", idx)
                return {
                    "index": idx,
                    "_photo_idx": idx,
                    "_extraction_error": str(e) or type(e).__name__,
                    "_extraction_error_kind": "exception",
                    "_empty_extraction": True,
                    "_empty_reason": f"Photo failed with an unexpected error: {e}",
                }

    budgeted_tasks = [
        asyncio.create_task(_budgeted_extract(idx, raw))
        for idx, (_ct, raw) in enumerate(shrunk_payloads)
    ]
    logger.info(
        "[ai-measure phase-A] dispatching %d photos (concurrency=%d, per_photo_budget=%ds, total_cap=%ds)",
        len(budgeted_tasks), concurrency, per_photo_budget, phase_a_total,
    )
    # asyncio.wait DOES NOT cancel-all on timeout — pending tasks stay
    # runnable and we get partial results back. We cancel stragglers
    # ourselves so the whole run doesn't hang past phase_a_total.
    done_tasks, pending_tasks = await asyncio.wait(budgeted_tasks, timeout=phase_a_total)
    phase_a_elapsed = int(time.time() - phase_a_started)
    logger.info(
        "[ai-measure phase-A] total wall clock %ds — %d done, %d pending",
        phase_a_elapsed, len(done_tasks), len(pending_tasks),
    )
    extractions: list[dict] = [None] * len(budgeted_tasks)
    for i, t in enumerate(budgeted_tasks):
        if t in done_tasks:
            try:
                extractions[i] = t.result()
            except Exception as e:  # defensive; _budgeted_extract already traps
                extractions[i] = {
                    "index": i,
                    "_photo_idx": i,
                    "_extraction_error": str(e) or type(e).__name__,
                    "_empty_extraction": True,
                    "_empty_reason": f"Task raised: {e}",
                }
        else:
            # Timed out against the total Phase A cap. Cancel + record.
            logger.warning(
                "[ai-measure phase-A] photo %d NOT done at total cap %ds — cancelling and flagging",
                i, phase_a_total,
            )
            t.cancel()
            extractions[i] = {
                "index": i,
                "_photo_idx": i,
                "_extraction_error": f"phase-A total cap of {phase_a_total}s reached before this photo finished",
                "_extraction_error_kind": "phase_a_cap",
                "_empty_extraction": True,
                "_empty_reason": f"Phase A ran out of time at {phase_a_total}s — this photo did not complete.",
                "_latency_ms": phase_a_total * 1000,
                "_total_latency_ms": phase_a_total * 1000,
            }
    # Drain the cancellations so no orphaned task keeps the loop busy.
    # Iter 79j.44 — CAP the drain at 5s. asyncio.CancelledError only
    # interrupts at `await` boundaries — a task blocked inside a
    # synchronous HTTP send (LlmChat -> LiteLLM -> httpx) will NOT
    # unwind until the underlying request returns. Waiting on it here
    # is what turned a 300s Phase A cap into a 1153s worker hang when
    # LiteLLM was retrying budget-exceeded requests. If the drain does
    # not finish inside 5s, we leave the tasks orphaned (they'll GC
    # when the HTTP call finally returns) and move on to Phase B.
    if pending_tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending_tasks, return_exceptions=True),
                timeout=5,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[ai-measure phase-A] drain of %d cancelled task(s) did not "
                "complete in 5s — leaving orphaned and proceeding to Phase B "
                "(the HTTP calls will finish in the background).",
                len(pending_tasks),
            )
    # Iter 79j.43 — Empty-extraction bookkeeping. After retry, any
    # photo still flagged `_empty_extraction: true` orphans the walls
    # it was the sole cover for. Compute the orphan set BEFORE Phase B
    # so we can surface it on the final raw.
    empty_photos: list[dict] = []
    walls_seen_by_photo: dict[int, set[str]] = {}
    for e in extractions:
        idx = int(e.get("_photo_idx", e.get("index", -1)))
        if e.get("_empty_extraction"):
            empty_photos.append({
                "photo_idx": idx,
                "reason": e.get("_empty_reason") or "empty",
                "extraction_error": e.get("_extraction_error") or None,
            })
            walls_seen_by_photo[idx] = set()
        elif e.get("_extraction_error"):
            empty_photos.append({
                "photo_idx": idx,
                "reason": f"call failed: {e.get('_extraction_error')}",
                "extraction_error": e.get("_extraction_error"),
            })
            walls_seen_by_photo[idx] = set()
        else:
            wv = e.get("walls_visible") or []
            walls_seen_by_photo[idx] = {
                (w or "").strip().lower()
                for w in wv
                if isinstance(w, str) and (w or "").strip()
            }
    all_covered_walls: set[str] = set()
    for wset in walls_seen_by_photo.values():
        all_covered_walls |= wset
    # Any of the 4 cardinal walls that NO non-empty photo saw is orphaned.
    orphaned_walls: list[str] = sorted(
        {"front", "back", "left", "right"} - all_covered_walls
    )

    # Persist Phase A immediately — even if Phase B fails downstream,
    # the Debug view still has the per-photo data to show.
    await db.ai_measure_runs.update_one(
        {"run_id": run_id},
        {"$set": {
            "raw_per_photo": extractions,
            "updated_at": datetime.now(timezone.utc),
        }},
    )

    await set_stage("reconciling")
    final = await _reconcile_extractions(
        api_key=api_key,
        user_id=user_id,
        model_provider=model_provider,
        model_name=model_name,
        extractions=extractions,
        address=address,
        reference_dim=reference_dim,
        annotation_hint=annotation_hint,
    )
    # Preserve the per-photo extractions on the final raw as `photos`
    # if the reconciliation step didn't emit its own (backward-compat
    # with `_aggregate_to_hover_shape` which reads `raw.get("photos")`).
    if not final.get("photos"):
        final["photos"] = [
            {
                "index": e.get("index", i),
                "elevation": e.get("elevation"),
                "elevation_confidence": e.get("elevation_confidence"),
                "elevation_reasoning": e.get("elevation_reasoning"),
                "walls_visible": e.get("walls_visible") or [],
                "eave_height_ft_observed": e.get("eave_height_ft_observed"),
                "eave_reasoning": e.get("eave_reasoning"),
                "pitch_ratio_observed": e.get("pitch_ratio_observed"),
                "gable_triangle_height_ft_observed": e.get("gable_triangle_height_ft_observed"),
                "dormers_observed_count": e.get("dormers_observed_count") or 0,
                "openings_this_photo": e.get("openings_this_photo") or [],
                "notes": e.get("notes") or "",
            }
            for i, e in enumerate(extractions)
        ]
    # Tag telemetry so the Debug view can render "two-phase" vs "single-call".
    final["_pipeline"] = "two_phase"
    # Iter 79j.43 — Surface empty-photo + orphaned-wall metadata so
    # the frontend can render a prominent warning banner and mark
    # affected wall fields amber. Never fail silently on a dead photo.
    if empty_photos or orphaned_walls:
        final["_empty_photos"] = empty_photos
        final["_orphaned_walls"] = orphaned_walls
    return final, extractions




async def _execute_ai_measure_worker(
    *,
    run_id: str,
    image_payloads: list[tuple[str, bytes]],
    api_key: str,
    user_id: str,
    address: Optional[str],
    reference_dim: Optional[str],
    kind: str,
    overhang_in: float,
    brick_course_in: Optional[float],
    siding_exposure_in: Optional[float],
    deep_dormer_scan: bool,
    elevation_tags: Optional[str],
    estimate_id: Optional[str] = None,
    # Iter 79j.15 — A/B model selection. Defaults match the run-doc
    # defaults so the rerun path (which doesn't pass these) still works.
    model_provider: str = "anthropic",
    model_name: str = MODEL_NAME,
):
    """Background worker — runs the Claude call(s), aggregates, maps to
    catalog lines, and writes the final result back to the run doc.
    Errors get written as `status: "error"` with a friendly message
    so the frontend's polling loop can surface them."""
    async def _set_stage(stage: str):
        await db.ai_measure_runs.update_one(
            {"run_id": run_id},
            {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc)}},
        )
    try:
        await _set_stage("claude")
        # Iter 78z+ (Annotations as Claude hints) — Load user-drawn boxes
        # from the estimate BEFORE the primary Claude call so we can
        # surface them in the prompt. Claude uses them as ground truth
        # AND can infer matching profile patterns on other elevations
        # (e.g. user marked the front gable as Shake → Claude is biased
        # toward calling matching scallop patterns on the back/right
        # gables as Shake too instead of defaulting to lap).
        annotations: dict | None = None
        if estimate_id:
            est_doc = await db.estimates.find_one(
                {"id": estimate_id},
                {"_id": 0, "profile_annotations": 1},
            )
            if est_doc:
                annotations = est_doc.get("profile_annotations") or None
        annotation_hint = _build_annotation_hint(annotations)

        # Iter 79j.37 — TWO-PHASE PIPELINE branch. Env-gated so the
        # single-call baseline remains available. When AI_MEASURE_TWO_PHASE=1:
        #   Phase A — parallel per-photo Claude calls (real per-photo data)
        #   Phase B — one reconciliation call over the Phase A JSONs
        # Aggregator/mapper/sanity/vero paths downstream are UNCHANGED —
        # both branches produce the same `raw` shape.
        two_phase = os.environ.get("AI_MEASURE_TWO_PHASE", "").strip() in ("1", "true", "yes")
        raw_per_photo: list[dict] = []
        session_id = f"ai-measure-{user_id}-{uuid.uuid4().hex[:8]}"

        if two_phase:
            raw, raw_per_photo = await _run_two_phase_pipeline(
                run_id=run_id,
                api_key=api_key,
                user_id=user_id,
                image_payloads=image_payloads,
                model_provider=model_provider,
                model_name=model_name,
                address=address,
                reference_dim=reference_dim,
                brick_course_in=brick_course_in,
                siding_exposure_in=siding_exposure_in,
                annotation_hint=annotation_hint,
                set_stage=_set_stage,
            )
        else:
            image_contents = [
                ImageContent(image_base64=base64.b64encode(raw).decode("ascii"))
                for _ct, raw in image_payloads
            ]
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,
                system_message=SYSTEM_PROMPT,
            ).with_model(model_provider, model_name)

            prompt_parts = []
            if address:
                prompt_parts.append(f"Property address: {address}")
            if reference_dim:
                prompt_parts.append(
                    f"Reference dimension provided by contractor: {reference_dim}. "
                    "Anchor all scale to this."
                )
            course_hints = []
            if brick_course_in and brick_course_in > 0:
                course_hints.append(
                    f"BRICK COURSE = {brick_course_in:.2f} inches (one brick + mortar = this height). "
                    f"If brick is visible anywhere in a photo, COUNT THE COURSES "
                    f"between the sill and head of each window to size it: "
                    f"{brick_course_in:.2f} in × course count = window height. "
                    f"This is far more accurate than estimating pixel ratios."
                )
            if siding_exposure_in and siding_exposure_in > 0:
                course_hints.append(
                    f"SIDING EXPOSURE = {siding_exposure_in:.2f} inches (one visible "
                    f"siding row = this height). On siding-clad walls, count visible "
                    f"siding rows between the sill and head: {siding_exposure_in:.2f} in × "
                    f"row count = window height."
                )
            if course_hints:
                prompt_parts.append("\n".join(course_hints))
            prompt_parts.append(
                "STANDARD-SIZE RESIDENTIAL WINDOWS — most windows are one of "
                "these widths: 18, 20, 24, 28, 30, 32, 34, 36, 40, 42, 44, 48, "
                "54, 60, 66, 72 in. Heights: 24, 30, 36, 38, 40, 42, 44, 46, 48, "
                "50, 52, 54, 60, 62, 66, 72 in. If your initial pixel measurement "
                "is within 2-3 inches of a standard, EMIT THE STANDARD (the "
                "backend will snap exact matches anyway, but rounding yourself "
                "first reduces noise). Doors: entry 36×80 (or 32×80, 30×80); "
                "patio 60×80 / 72×80; garage 96×84 (single), 192×84 (double)."
            )
            prompt_parts.append(
                "SYMMETRY / REPETITION — if you see 3+ windows on the same wall "
                "that look identical (same operation style, similar W and H), "
                "they ARE identical (houses don't have 4 windows in a row of "
                "different sizes — that's a builder error). Emit them ALL with "
                "the SAME width_in and height_in. The backend also enforces this "
                "but you doing it cleanly produces fewer dedupe artefacts."
            )
            prompt_parts.append(
                "Photos attached below. Return the JSON measurement object now."
            )
            # Iter 78z+ — Annotation hints (ground-truth boxes from the
            # contractor) inserted right before the schema marker so Claude
            # can use them throughout its analysis.
            if annotation_hint:
                prompt_parts.append(annotation_hint)
            user_text = "\n".join(prompt_parts)

            # Iter 79e — same 4-min Claude wall-clock cap as the HOVER worker.
            # If Claude is unresponsive (rare, but the LLM provider can stall),
            # the asyncio.wait_for raises TimeoutError → outer except flips
            # the run doc to `status: "error"` instead of leaving it orphaned
            # at `status: "running"` indefinitely. Frontend polls a 5-min cap
            # so this aligns to a clean client-side error message.
            reply_text = await asyncio.wait_for(
                chat.send_message(
                    UserMessage(text=user_text, file_contents=image_contents),
                ),
                timeout=240,
            )
            raw = _json_from_reply(reply_text or "")
            raw["_pipeline"] = "single_call"

        # Iter 79j.44 — Removed deep_dormer_scan invocation. Two-phase
        # Phase A/B now owns dormer detection end-to-end (dormers[]
        # array with per-face + width_source provenance). The legacy
        # roofline-crop scan was injecting corrupt data — openings
        # with null opening_ids, hits on nonexistent walls (e.g.
        # 'rear-left'), and face SF credited to the wrong wall for
        # side-slope dormers. The `deep_dormer_scan` request flag is
        # still accepted for backward compat but is now a no-op.
        _ = deep_dormer_scan  # accepted, ignored

        await _set_stage("aggregating")
        # Iter 78z — Annotations were already loaded above (for the
        # Claude hint). Reuse them as the breakdown overlay so the
        # catalog mapper emits per-profile lines.
        measurements = _aggregate_to_hover_shape(raw, annotations=annotations)
        measurements["overhang_in"] = float(overhang_in)

        await _set_stage("mapping")
        try:
            lines = _build_lines(measurements)
        except Exception:
            lines = []
        # Iter 78o — Phase 1 sanity checks on AI-Measure / Blueprint runs.
        try:
            from routes.hover_sanity import run_checks
            warnings = run_checks(measurements)
        except Exception:
            warnings = []

        result = {
            "measurements": measurements,
            "lines": lines,
            "vero_openings": _build_vero_openings_from_ai(
                raw.get("openings") or [],
                raw.get("openings_schedule") or [],
            ),
            "raw_ai": raw,
            "model": model_name,          # Iter 79j.15 — actual model used (may differ from MODEL_NAME default)
            "model_provider": model_provider,
            "session_id": session_id,
            "warnings": warnings,
        }
        await db.ai_measure_runs.update_one(
            {"run_id": run_id},
            {"$set": {
                "status": "done",
                "stage": "done",
                "result": result,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
    except Exception as e:
        # Log & surface a friendly error to the polling client.
        logger.exception("[ai-measure] worker failed for run_id=%s", run_id)
        # Iter 79j.44 — str(TimeoutError()) is '' which shows as a
        # blank toast on the frontend. Always produce a non-empty
        # human message with the exception class name at minimum.
        friendly = str(e).strip() or type(e).__name__
        await db.ai_measure_runs.update_one(
            {"run_id": run_id},
            {"$set": {
                "status": "error",
                "stage": "error",
                "error": f"AI measure failed: {friendly}",
                "error_kind": type(e).__name__,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )


@router.post("/map")
async def map_measurements_to_lines(
    payload: dict,
    user: dict = Depends(get_current_user),
):
    """Convert a HOVER-shaped measurements dict directly into siding/windows
    catalog rows — no AI involved. Used by the Photo Measure tool where
    the contractor produces measurements by tapping on a photo and we
    just need the same line mapping HOVER provides."""
    measurements = payload.get("measurements") or {}
    try:
        lines = _build_lines(measurements)
    except Exception:
        lines = []
    # Iter 78o — Phase 1 sanity checks also run on the cached-measurement
    # restore path so the "Restore HOVER lines" modal shows the same
    # warning banner the fresh-import flow does.
    try:
        from routes.hover_sanity import run_checks
        warnings = run_checks(measurements)
    except Exception:
        warnings = []
    return {"measurements": measurements, "lines": lines, "vero_openings": [], "warnings": warnings}



# =====================================================================
# Iter 78z (Cross-Check) — Reference photo cross-check.
#
# After the primary AI Measure pass, the contractor can fire this
# secondary Claude pass to VERIFY the per-elevation profile callouts
# against the same uploaded photos. The 2nd pass uses a focused prompt
# that biases Claude toward catching:
#   - Small accents the primary pass missed (porch B&B, column shake)
#   - Profile mis-classification (lap vs dutch lap, shake vs B&B)
#   - Stone / brick watertable mis-reads
#
# Returns:
#   conflicts:         [{elev, role, primary, verified, confidence, note}]
#   suggested_accents: [{elev, location, profile, approx_sqft, confidence}]
#   overall_confidence: high/medium/low
#   agreement_pct:     0-100 (% of roles where primary == verified)
# =====================================================================
CROSS_CHECK_PROMPT = """\
You are a SECOND-PASS verification agent for a siding takeoff. You already
analyzed these photos in a first pass; now do a careful re-check ONLY
of the per-elevation siding profile callouts.

Look for these specific failure modes the first pass commonly misses:
1. SMALL ACCENT PANELS — porch face B&B, column wrap shake, small dormer
   scallop, gable-vent surround. These get lost when Claude downsizes
   full-house photos.
2. PROFILE MIS-CLASSIFICATION — lap vs dutch lap (notched bottom edge),
   shake vs board & batten (vertical battens vs staggered courses),
   nickel gap vs plain vertical.
3. MASONRY MIS-READ — stone / brick watertable or wainscot the first
   pass might have missed (would reduce siding ft²).

Canonical profile families (use these exact strings):
  lap | dutch_lap | shake | board_batten | vertical | nickel_gap |
  stone | brick | stucco | unknown

You MUST return JSON only. Schema:
{
  "overall_confidence": "high" | "medium" | "low",
  "per_elevation": [
    {
      "label": "front" | "back" | "left" | "right" | etc,
      "body_profile":  "<one of the canonical families>",
      "gable_profile": "<canonical family or empty>",
      "dormer_profile": "<canonical family or empty>",
      "accents": [
        {
          "location":       "<short, e.g. 'porch face' / 'column wrap' / 'dormer scallop'>",
          "profile":        "<canonical family>",
          "approx_sqft":    number,
          "confidence":     "high" | "medium" | "low",
          "callout":        "<what visually told you, 1 short phrase>"
        }
      ],
      "notes": "<1 sentence on anything unusual, or empty>"
    }
  ]
}

Be CONSERVATIVE on accents — only flag accents you can clearly see in
the photos. Don't invent details. If the photo is too small/blurry,
mark confidence: "low" and note the limitation.
"""


def _normalize_family(s) -> str:
    """Best-effort normalization of a profile string to a canonical
    family. Tolerates the primary breakdown's labels + raw Claude
    output. Returns empty string when unparseable."""
    if not s:
        return ""
    s = str(s).strip().lower().replace("-", "_").replace(" ", "_")
    if s in {"lap", "dutch_lap", "shake", "board_batten", "vertical",
             "nickel_gap", "stone", "brick", "stucco", "unknown"}:
        return s
    # Forgive a few common Claude outputs
    if s in {"clapboard", "horizontal_lap"}:
        return "lap"
    if s in {"dutchlap"}:
        return "dutch_lap"
    if s in {"shaker", "shingle", "shingles", "fish_scale", "scallop"}:
        return "shake"
    if s in {"bnb", "b&b", "batten"}:
        return "board_batten"
    return ""


def _compute_recheck_diff(primary_per_elev: list, verified: dict) -> dict:
    """Compare the primary per_elevation_breakdown vs the verifier's
    output and produce conflicts + suggested_accents. The verifier
    returns its result keyed by `label` (lowercase). Roles compared:
    body / gable / dormer. Accent comparison is by (location, profile)
    fuzzy match — anything in the verifier not seen in primary is a
    suggestion."""
    conflicts = []
    suggested_accents = []
    total_role_comparisons = 0
    matches = 0

    primary_by_label = {
        (e.get("label") or "").strip().lower(): e for e in (primary_per_elev or [])
    }
    verified_per_elev = verified.get("per_elevation") or []

    for v_elev in verified_per_elev:
        v_label = (v_elev.get("label") or "").strip().lower()
        p_elev = primary_by_label.get(v_label) or {}

        # Compare each role
        for role, p_key, v_key in [
            ("body",   "wall_body_profile", "body_profile"),
            ("gable",  "gable_profile",     "gable_profile"),
            ("dormer", "dormer_profile",    "dormer_profile"),
        ]:
            p_fam = _normalize_family(p_elev.get(p_key))
            v_fam = _normalize_family(v_elev.get(v_key))
            # Only compare when verifier produced an opinion AND the
            # primary had a value to compare against.
            if not v_fam:
                continue
            if role == "body" and not p_fam:
                # Primary had no body profile but verifier does — surface
                # as a conflict so the contractor can review.
                conflicts.append({
                    "elev": v_label,
                    "role": role,
                    "primary": "",
                    "verified": v_fam,
                    "confidence": v_elev.get("overall_confidence") or "medium",
                    "note": f"Verifier identified {v_fam} body siding; primary had no callout",
                })
                continue
            if not p_fam:
                continue
            total_role_comparisons += 1
            if p_fam == v_fam:
                matches += 1
            else:
                conflicts.append({
                    "elev": v_label,
                    "role": role,
                    "primary": p_fam,
                    "verified": v_fam,
                    "confidence": v_elev.get("overall_confidence") or "medium",
                    "note": f"Primary said {p_fam}, verifier says {v_fam}",
                })

        # Suggested accents: anything in verifier not already in primary's
        # accents list. Match by (profile, location) approximate.
        p_accents = p_elev.get("accents") or []
        p_keys = {
            (
                _normalize_family(a.get("profile")),
                (a.get("location") or "").strip().lower(),
            )
            for a in p_accents
        }
        for v_acc in (v_elev.get("accents") or []):
            v_fam = _normalize_family(v_acc.get("profile"))
            if not v_fam:
                continue
            v_loc = (v_acc.get("location") or "").strip().lower()
            if (v_fam, v_loc) in p_keys:
                continue  # already on the primary breakdown
            try:
                sqft = float(v_acc.get("approx_sqft") or 0)
            except (TypeError, ValueError):
                sqft = 0
            if sqft <= 0:
                continue
            suggested_accents.append({
                "elev": v_label,
                "location": v_acc.get("location") or "accent",
                "profile": v_fam,
                "approx_sqft": round(sqft, 1),
                "confidence": v_acc.get("confidence") or "medium",
                "callout": v_acc.get("callout") or "",
            })

    agreement_pct = round((matches / total_role_comparisons * 100), 1) if total_role_comparisons > 0 else 100.0
    return {
        "overall_confidence": verified.get("overall_confidence") or "medium",
        "agreement_pct": agreement_pct,
        "conflicts": conflicts,
        "suggested_accents": suggested_accents,
        "verified_per_elevation": verified_per_elev,
    }


@router.post("/ai-cross-check/{run_id}")
async def ai_cross_check(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """Iter 78z — Reference photo cross-check.

    Fires a SECOND Claude vision pass against the same photos the
    primary AI Measure run used, focused exclusively on verifying the
    per-elevation profile callouts. Returns a diff (conflicts +
    suggested accents) the frontend can render inline on the takeoff
    preview. Patches the run document with the recheck result so
    subsequent loads can show it without re-running Claude.
    """
    doc = await db.ai_measure_runs.find_one({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if doc.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your run")
    if doc.get("status") != "done":
        raise HTTPException(
            status_code=409,
            detail="Primary run is not complete yet — wait for it to finish first",
        )

    # Reload the original photo bytes from disk via the cached paths.
    photo_paths_str = doc.get("photo_paths") or ""
    paths = [p.strip() for p in photo_paths_str.split(",") if p.strip()]
    if not paths:
        raise HTTPException(
            status_code=400,
            detail="No cached photos on this run — re-upload to use cross-check",
        )
    from config import UPLOAD_DIR  # local import to dodge cycle
    image_payloads: list[bytes] = []
    for name in paths:
        target = UPLOAD_DIR / name
        if not target.exists():
            continue
        raw = target.read_bytes()
        # Reuse the same compressor the primary pass uses.
        image_payloads.append(_compress_for_claude(raw))
    if not image_payloads:
        raise HTTPException(
            status_code=400,
            detail="None of the cached photos are still on disk — re-upload to use cross-check",
        )

    # Pull the primary breakdown from the saved run.
    result = doc.get("result") or {}
    primary_measurements = result.get("measurements") or {}
    primary_per_elev = primary_measurements.get("_per_elevation_breakdown") or []

    # Build the summary that prefaces the verification prompt so Claude
    # knows what the primary pass already concluded.
    if primary_per_elev:
        summary_lines = ["First-pass conclusions (verify or correct each row):"]
        for e in primary_per_elev:
            label = e.get("label") or "unknown"
            body = e.get("wall_body_profile") or ""
            gable = e.get("gable_profile") or ""
            dormer = e.get("dormer_profile") or ""
            accents = e.get("accents") or []
            acc_str = (
                " | ".join(f"{a.get('profile')}@{a.get('location')}" for a in accents)
                if accents else "none"
            )
            summary_lines.append(
                f"  - {label}: body={body or 'unknown'}, "
                f"gable={gable or 'none'}, dormer={dormer or 'none'}, "
                f"accents=[{acc_str}]"
            )
        summary = "\n".join(summary_lines)
    else:
        summary = "First pass produced no per-elevation breakdown. Build one from scratch."

    # Iter 79j.42 — Cross-check is always Anthropic (Opus). Honor
    # ANTHROPIC_API_KEY when present, else use the Emergent key.
    api_key, _api_key_source = _pick_llm_api_key("anthropic")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "No LLM API key on the server. Set ANTHROPIC_API_KEY (direct) "
                "or EMERGENT_LLM_KEY (Universal Key)."
            ),
        )

    session_id = f"ai-cross-check-{user['id']}-{uuid.uuid4().hex[:8]}"
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=CROSS_CHECK_PROMPT,
    ).with_model("anthropic", MODEL_NAME)

    image_contents = [
        ImageContent(image_base64=base64.b64encode(b).decode("ascii"))
        for b in image_payloads
    ]
    user_text = (
        summary
        + "\n\nNow re-examine the photos and return your verification JSON."
    )
    try:
        reply_text = await chat.send_message(
            UserMessage(text=user_text, file_contents=image_contents),
        )
        verified = _json_from_reply(reply_text or "")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ai-cross-check] Claude call failed for run_id=%s", run_id)
        raise HTTPException(
            status_code=502,
            detail=f"Cross-check pass failed: {e}",
        ) from e

    # Diff vs primary breakdown
    recheck = _compute_recheck_diff(primary_per_elev, verified)

    # Persist on the run so subsequent loads can resurface without re-paying.
    primary_measurements["_ai_profile_recheck"] = recheck
    await db.ai_measure_runs.update_one(
        {"run_id": run_id},
        {"$set": {
            "result.measurements._ai_profile_recheck": recheck,
            "updated_at": datetime.now(timezone.utc),
        }},
    )

    return {"run_id": run_id, "recheck": recheck}



# ---------------------------------------------------------------------------
# Iter 78z+ — OCR Auto-Scale endpoint.
#
# Pointed at a blueprint page (or photo) URL, this endpoint runs a small
# focused Claude vision call to:
#   1. Find a labeled wall dimension on the image (e.g. "30'-0\"" arrow)
#   2. Return the pixel endpoints of that dimension line + the labeled ft
#   3. Optionally surface the scale notation ("SCALE 1/4\" = 1'-0\"")
#
# Frontend uses (px_height, real_ft) to set the ProfileAnnotator's
# scale_ref — same shape as the manual drag UI but zero-click.
# ---------------------------------------------------------------------------
OCR_SCALE_PROMPT = """\
You are an OCR + measurement-extraction assistant for blueprints and
construction photos. Your ONLY job: find a dimension that can be used
to calibrate the image's scale.

PRIORITY 1 — Find a printed wall dimension with an arrow / extension
lines (e.g. '30'-0"' or '40'-6"' marking the length of a wall on the
elevation or floor plan). Return the pixel coordinates of the TWO
endpoints of the dimension line (where the arrow tips sit) PLUS the
labeled real-world value in feet.

PRIORITY 2 — If no labeled dimension is visible, find the scale block
(e.g. 'SCALE: 1/4" = 1'-0"') and return it as a fallback.

The image you receive is RENDERED AT THE NATURAL PIXEL DIMENSIONS you
see. Return pixel coordinates in that same coordinate system (origin
at top-left, x right, y down).

Return JSON ONLY (no prose, no markdown fences). Schema:
{
  "found":           true | false,
  "method":          "dimension_line" | "scale_block" | "none",
  "px_height":       number (Euclidean px distance between endpoints; 0 if not found),
  "real_ft":         number (labeled real-world distance in ft),
  "source":          "<short description of what you found, e.g. '30 ft front wall dimension' or 'SCALE 1/4\\" = 1\\\\'-0\\"' block'>",
  "confidence":      "high" | "medium" | "low",
  "endpoints":       [{"x": number, "y": number}, {"x": number, "y": number}],   // empty array if not found
  "notes":           "<one sentence on anything unusual or empty>"
}

If you can't find ANY reliable dimension, return `{"found": false, "method": "none", "confidence": "low", "notes": "<why>"}`.
"""


@router.post("/ocr-scale")
async def ocr_scale(
    payload: dict,
    user: dict = Depends(get_current_user),
):
    """Iter 78z+ — Auto-detect the scale on a blueprint page or photo.

    Body: `{"upload_name": "bp_xxxxxxxx.png"}` — the filename returned
    from the blueprint launch endpoint (or any /api/uploads/* filename).
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be an object")
    upload_name = (payload.get("upload_name") or "").strip()
    if not upload_name:
        raise HTTPException(status_code=400, detail="missing 'upload_name'")
    # Defense in depth — no path traversal.
    if "/" in upload_name or ".." in upload_name:
        raise HTTPException(status_code=400, detail="invalid upload_name")

    from config import UPLOAD_DIR
    from upload_store import rehydrate_to_disk  # Iter 78z+++ — self-heal
    target = UPLOAD_DIR / upload_name
    if not target.exists():
        # Disk miss — try the MongoDB backing store (durable across
        # container restarts / disk wipes).
        restored = await rehydrate_to_disk(upload_name, UPLOAD_DIR)
        if not (restored and restored.exists()):
            raise HTTPException(status_code=404, detail="upload not found on disk")
        target = restored
    raw = target.read_bytes()
    if not raw:
        raise HTTPException(status_code=400, detail="upload is empty")

    # Iter 79j.42 — OCR-scale is always Anthropic. Honor
    # ANTHROPIC_API_KEY when present, else use the Emergent key.
    api_key, _api_key_source = _pick_llm_api_key("anthropic")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "No LLM API key on the server. Set ANTHROPIC_API_KEY (direct) "
                "or EMERGENT_LLM_KEY (Universal Key)."
            ),
        )

    # Compress through the same pipeline Claude already uses elsewhere.
    img_bytes = _compress_for_claude(raw)
    user_id = user["id"]
    session_id = f"ai-ocr-scale-{user_id}-{uuid.uuid4().hex[:8]}"
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=OCR_SCALE_PROMPT,
    ).with_model("anthropic", MODEL_NAME)
    image_contents = [
        ImageContent(image_base64=base64.b64encode(img_bytes).decode("ascii")),
    ]
    try:
        reply_text = await chat.send_message(
            UserMessage(
                text="Find the calibration dimension on this image and return your JSON.",
                file_contents=image_contents,
            ),
        )
        parsed = _json_from_reply(reply_text or "")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ocr-scale] Claude call failed for %s", upload_name)
        raise HTTPException(status_code=502, detail=f"OCR scale pass failed: {e}") from e

    # Sanity-check the response shape and derive px_height from endpoints
    # when Claude didn't compute it.
    endpoints = parsed.get("endpoints") or []
    px_height = 0.0
    try:
        px_height = float(parsed.get("px_height") or 0)
    except (TypeError, ValueError):
        px_height = 0.0
    if px_height <= 0 and len(endpoints) == 2:
        try:
            import math as _math
            dx = float(endpoints[0]["x"]) - float(endpoints[1]["x"])
            dy = float(endpoints[0]["y"]) - float(endpoints[1]["y"])
            px_height = _math.sqrt(dx * dx + dy * dy)
        except (KeyError, TypeError, ValueError):
            px_height = 0.0

    try:
        real_ft = float(parsed.get("real_ft") or 0)
    except (TypeError, ValueError):
        real_ft = 0.0

    found = bool(parsed.get("found")) and px_height > 0 and real_ft > 0
    return {
        "found":      found,
        "method":     parsed.get("method") or ("none" if not found else "dimension_line"),
        "px_height":  round(px_height, 2),
        "real_ft":    real_ft,
        "source":     parsed.get("source") or "",
        "confidence": parsed.get("confidence") or "low",
        "endpoints":  endpoints,
        "notes":      parsed.get("notes") or "",
    }
