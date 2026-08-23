"""AI Blueprint Reader — pull a takeoff from architectural plans.

Sister endpoint to /api/measure/ai-measure. Where ai-measure looks at a
photo of the house and *estimates* dimensions (±10–30%), this endpoint
*reads* the dimensions printed on a blueprint or plan PDF — so the
output is as accurate as the drawing itself.

Endpoint: POST /api/measure/ai-blueprint  (multipart/form-data)
Form fields:
  file:           one multi-page PDF (preferred — blueprint set)
  files:          OR one or more JPG/PNG image scans of plan sheets
  address:        optional context for Claude's reply
  overhang_in:    soffit overhang for the piece-count formula
  max_pages:      cap on PDF page count to send (default 12, max 20)

Output matches /api/measure/ai-measure exactly:
  { measurements, lines, vero_openings, mezzo_openings, raw_ai, model }

A blueprint set typically has:
  • Cover sheet / title block (scale, project address)
  • Site plan (lot, setbacks — we ignore)
  • Floor plan (perimeter dims, RO callouts at each window — KEY for windows)
  • Elevations: front / rear / left / right (wall heights, gable rises)
  • Roof plan (eave + rake LF)
  • Window / Door Schedule (the table — KEY for exact counts + RO sizes)

Cost: blueprint sheets are PNGs at ~200 DPI → ~3–6 MB each. A typical 6-sheet
set costs ~$0.40–$0.60 in Opus 4.5 vision charges. We surface page-count
in the response so the contractor can see what was billed.
"""
from __future__ import annotations

import base64
import io
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import pypdfium2 as pdfium
from PIL import Image
from emergentintegrations.llm.chat import (
    ImageContent,
    LlmChat,
    UserMessage,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from deps import get_current_user
from db import db
import seam_accounting
from routes.hover import _build_lines, _build_window_openings
import measure_staging as staging
import ocr_geometry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/measure", tags=["measure"])

ACCEPTED_IMG_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ACCEPTED_PDF_MIMES = {"application/pdf"}
MAX_PAGES_HARD = 28   # raised 2026-08-09 (was 20) — construction sets run 15-30 sheets; a total-size budget below keeps the request under Anthropic's cap
DEFAULT_MAX_PAGES = 20  # raised 2026-08-09 (was 12) — Boni is 11 sheets; the old default sat one page from silent truncation
MAX_BYTES_PER_FILE = 16 * 1024 * 1024  # blueprints scan larger than photos
PDF_RENDER_SCALE = 2.0  # pypdfium2 scale factor — ~144 DPI for an 8.5×11
# ⚑ PROVENANCE (Iter 121): VALIDATED 2026-07-15 by the pre-registered
# 6-run controlled comparison (3× Opus 4.5 vs 3× Fable 5, both arms on
# direct transport, sealed Letrick key, Amendment 1 median-vs-span +
# Amendment 2 anchor-integrity rules). Challenger improved 1/4 residual
# lines (needed ≥2) and worsened siding beyond noise → incumbent held.
# The June inherited-default debt is CLOSED. Task-specificity finding on
# file: the photo pipeline needs the frontier model; the blueprint
# pipeline doesn't (6.3× cost, no residual win). Ruling + evidence:
# /app/memory/blueprint_model_comparison_results.md
MODEL_NAME = "claude-opus-4-5-20251101"
MODEL_VALIDATION_STATUS = (
    "validated — 6-run controlled comparison 2026-07-15 "
    "(incumbent held per pre-registered decision rule)"
)


def _blueprint_prompt_hash() -> str:
    import hashlib
    return hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:16]


SYSTEM_PROMPT = """\
You are an expert residential blueprint reader for a vinyl-siding and
window contractor. The user uploads scans / PDF exports of an architectural
plan set. Your job is to READ (not estimate) the printed dimensions and
return a takeoff JSON that drives a quote.

You MUST return JSON only — no prose, no markdown fences.

RESIDENTIAL PLAN NOTATION YOU MUST UNDERSTAND:

1. Window / Door RO sizes are written one of these ways:
     "3-6 5-0"       → 3'-6" wide × 5'-0" tall  → 42" × 60"
     "3'-6\" 5'-0\""  → same
     "3050"          → 3'-0" × 5'-0"  → 36" × 60"  (4-digit shorthand: first 2 digits = feet-inches of width, last 2 = feet-inches of height)
     "3068"          → 3'-0" × 6'-8"  → 36" × 80"  (door shorthand: 6'-8" is standard residential door height)
     "30 X 60"       → 30" wide × 60" tall (inches — already explicit)
     "2868" / "3068" / "6068" → standard door codes (last 2 digits = 6'-8" door height); 6068 = 6'-0" double door
   When you see one of these next to a window/door symbol on the FLOOR PLAN,
   parse it into width_in + height_in. The 4-digit form is the most
   ambiguous — verify by checking that height makes sense (60–84" for
   windows, 78–84" for doors).

2. Floor-plan dimension strings like "24'-0\"" or "24-0" or "24' 0\"" or "24.0'"
   all mean 24 feet. Convert to decimal feet (24.0).

3. Sheet titles to look for:
   • "FLOOR PLAN" / "1ST FLOOR" / "2ND FLOOR" → for perimeter + RO callouts
   • "FRONT ELEVATION" / "REAR" / "LEFT" / "RIGHT" / "SIDE" → for wall heights + gable rises
   • "ROOF PLAN" → for eave / rake linear feet
   • "WINDOW SCHEDULE" / "DOOR SCHEDULE" → THE most accurate source for
     window/door counts and RO sizes. If a schedule is present, USE IT —
     it overrides whatever you counted on the floor plan.

4. Scale callouts: "1/4\" = 1'-0\"" or "SCALE 1/4 IN = 1 FT" → only
   needed if dimensions are missing; you should rely on the printed
   dim strings, not on measuring pixels.

EXTRACTION SCHEMA — return EXACTLY this shape:

EVIDENCE-OR-NULL, STRUCTURAL (ruled 2026-08-08): every field marked DIM
below is an OBJECT {"v": number, "page": <1-based sheet number>, "from":
"<the printed dimension string VERBATIM you read it from>"} — or null.
If you cannot QUOTE a printed string for a dimension, return null. A
bare number, or an object without its "from" quote, is DROPPED BY THE
PIPELINE and flagged — an unevidenced dimension is unrepresentable.
"I do not know" is a first-class answer: null + the flag is CORRECT
behaviour; a guessed number is the only wrong one.

VISUAL AUDIT (same ruling, same schema): each DIM should ALSO carry
"loc": {"x_pct": n, "y_pct": n, "w_pct": n, "h_pct": n} — the bounding
box of the printed string ON THAT PAGE IMAGE, in PERCENT (0-100) of the
page's width/height measured from the TOP-LEFT corner. Best effort — an
honest approximate box beats an omitted one, but NEVER invent a "from"
quote to justify a box. Omit "loc" when you cannot place the string.
DERIVED VALUES: when a value stacks from SEVERAL printed dims (a corner
height summed from plate dimensions; a footprint = first floor +
garage), return {"v": number, "calc": "<the arithmetic with its inputs,
verbatim>", "srcs": [{"page": n, "from": "<printed string>", "loc":
{...}}, ...]} — one src per printed input. A derived value with no srcs
is as unrepresentable as a bare number.
IF A VALUE IS COMPUTED, IT IS DERIVED (ruled 2026-08-08): a wall or
corner height you obtain by ADDING printed components (plate heights +
floor thickness + upper plate, e.g. 9'-11 1/8" + 1'-0" + 8'-1 1/8" +
11 1/2") MUST use the derived form above — each component carrying its
own printed quote. NEVER present a computed total as a single read with
a fabricated quote (e.g. "20'-0\"") when no such string is printed on
the sheet: A COMPUTED NUMBER WEARING A QUOTE IS A LIE WITH A CITATION.
"from" may only hold a string that is PRINTED AS SUCH on the page — a
local text-read cross-checks every quote against the page pixels, and
an unfindable quote is flagged as a contradiction.
{
  "sheets_identified": [
    {"page": 1, "sheet_title": "<best guess>", "useful_for": "elevation|floor_plan|schedule|roof|cover|other"}
  ],
  "scale_confidence": "high" | "medium" | "low",
  "story_count": 1 | 1.5 | 2 | 2.5 | 3,
  "avg_wall_height_ft": number,           // EAVE height, read from elevation
  "walls": [
    {"label": "front" | "back" | "left" | "right",
     "width_ft": DIM,                     // {"v","page","from"} — read from floor plan or elevation
     "height_ft": DIM,                    // EAVE height of the TALLEST section (not roof peak). When the wall STEPS, the truth lives in height_segments below.
     // PER-WALL HEIGHT VARIATION (ruled 2026-08-07):
     // A HOUSE IS NOT A UNIFORM BOX. When an elevation shows the wall stepping between
     // heights (2-story main body dropping to a 1-story garage wing or
     // porch section), report EACH horizontal section at ITS OWN eave
     // height. Segment widths MUST sum to width_ft. Siding a 10-foot
     // garage wall at the main body's height over-orders every low
     // section on the house. A section whose height is NOT dimensioned
     // on the drawing returns "height_ft": null — FLAG, never a guess
     // (first ruled on an undimensioned back garage wall, 2026-08-08).
     // Return [] ONLY when the elevation truly
     // shows one uniform eave height across the whole wall.
     "height_segments": [
       {"label": "<e.g. 'main body', 'garage wing', 'porch section'>",
        "width_ft": DIM,
        "height_ft": DIM}                 // NO printed height for a section → "height_ft": null — FLAG, never a guess
     ],
     "gable_triangle_height_ft": number,  // 0 unless this wall is a gable end. If a roof PITCH callout is printed (e.g. "7/12"), COMPUTE this as (width_ft ÷ 2) × (pitch_rise ÷ 12) — the printed pitch is the authority; scaling the drawing under-reads the rise.
     "dormer_face_sqft": number,          // 0 unless dormer shown on this elevation
     "siding_pct_this_wall": 100,         // INTEGER percent; default 100 unless plan notes brick/stone
     // Iter 78z — Profile callouts read from the elevation drawing itself.
     // Construction prints almost always print the siding type in plain
     // text on or near the surface (e.g. "LAP 4\"", "DUTCH LAP", "SHAKER",
     // "B&B", "STONE WATERTABLE"). Capture them verbatim — the catalog
     // mapper splits the line by callout so mixed-material houses
     // (Campbell-style) produce SEPARATE SHAKE / B&B / LAP quote lines
     // instead of collapsing into a single inflated lap number.
     "wall_body_profile_callout": "<verbatim text from the elevation showing the wall body siding (e.g. 'LAP 4\"', 'DUTCH LAP 5\"', 'VINYL'); leave empty if not labelled>",
     "gable_profile_callout":     "<verbatim text for the gable triangle's siding (e.g. 'SHAKER', 'SHAKE', 'B&B', 'BOARD AND BATTEN'); empty if gable matches the wall body or wall isn't a gable end>",
     "dormer_profile_callout":    "<verbatim text for any dormer face siding (e.g. 'SHAKER', 'B&B'); empty if no dormer or dormer matches body>",
     "stone_callout":             "<'STONE WATERTABLE' or similar if the elevation shows a masonry watertable / wainscot below the siding line; empty if all siding>",
     // Iter 78z+ — ACCENT PANELS. A single wall can carry SMALL accent
     // areas with a different profile from the body — these are easy to
     // miss because they don't fit the "body / gable / dormer" buckets.
     // Examples seen on Howard's jobs: B&B on a porch face, shake on
     // column wraps, vertical siding on a bay-window cheek, fish-scale
     // on an entry gable above the porch. Capture every accent you can
     // see on THIS wall. Leave empty if the wall is uniform.
     "accent_profiles": [
       {"location": "<short description, e.g. 'porch face', 'column wrap', 'bay window cheek', 'entry gable', 'kneewall'>",
        "profile_callout": "<verbatim text or pattern (e.g. 'B&B', 'BOARD AND BATTEN', 'SHAKE', 'VERTICAL')>",
        "approx_sqft": number}
     ]
    }
  ],
  "windows": [
    // Each row in the Window Schedule (or each callout on the floor plan).
    // If both are present, prefer the schedule and dedupe by mark.
    // PRINTED DIMENSIONS ARE SACRED (ruled 2026-08-07): parse the printed
    // size string EXACTLY — 3-0x5-0 means 36×60, NEVER a "standard" catalog
    // size like 38×54. NEVER snap a printed dimension to a catalog size.
    // THE SIZE COLUMN GOVERNS (ruled 2026-08-08): when the schedule prints
    // BOTH a product/unit code (e.g. "SH 3-0_5-0") AND a SIZE column
    // (e.g. 2'-11 1/2" x 4'-11 1/2"), the SIZE column IS the dimension —
    // width_in/height_in parse the SIZE column, NEVER the code. Units
    // commonly print a half inch under the code's nominal; converting the
    // code (36×60) while 35.5×59.5 sits in the next column violates
    // printed-dims-sacred. The code is a FAMILY LABEL — use it to
    // identify the unit, never to compute one. Only when NO size column
    // exists may the code string be parsed as the size.
    // SUM MARKS ACROSS SHEETS (ruled 2026-08-08): schedules repeat across
    // floors (first-floor sheet AND second-floor sheet each carry one).
    // Read EVERY schedule sheet. The SAME mark on multiple sheets is ONE
    // mark — one row, counts SUMMED (A: 2 on one sheet + 7 on another =
    // one row, qty 9), pages listed in schedule_pages. NEVER attach one
    // mark's dimensions to another mark's letter — re-read the row's own
    // SIZE cell on each sheet before summing.
    // If the schedule separately prints a catalog/order size, report it in
    // catalog_size — BOTH get printed downstream, never one replacing the
    // other. TYPE ABBREVIATIONS: SH = single_hung, DH = double_hung —
    // NEVER retype one as the other.
    {"id": "<mark like 'W1' or 'A' or blank>",
     "product_code": "<the schedule's product/unit CODE column VERBATIM (e.g. 'SH 3-0_5-0'); empty if none — a FAMILY LABEL, never a dimension source>",
     "printed_size": "<the schedule's SIZE column VERBATIM (e.g. 2'-11 1/2\" x 4'-11 1/2\") when one exists; otherwise the code-style size string ('3-0x5-0'/'3050'); empty if only drawn>",
     "catalog_size": "<a SEPARATELY-printed catalog/order size if the schedule prints one (e.g. '38x54'); empty otherwise — NEVER derived>",
     "width_in": number,                  // exact parse of printed_size: 2'-11 1/2" → 35.5; 3-6 → 42; 3050 → 36×60 — the SIZE column when printed, the code only when it is all there is
     "height_in": number,
     "qty": 1,                            // THE COUNT COLUMN GOVERNS COUNTS (ruled 2026-08-08): the schedule PRINTS a COUNT — read it. qty = the printed COUNT summed across every schedule sheet that lists this mark. NEVER count window symbols on a floor plan, NEVER infer quantity from elevations or anything else. If a sheet's schedule prints no count for a mark, that sheet contributes nothing — flag it, don't estimate.
     "count_by_page": {"<sheet>": n},     // the COUNT column value per schedule sheet, verbatim (e.g. {"6": 2, "7": 7}) — qty must equal their sum
     "schedule_pages": [<1-based sheet numbers whose schedule lists this mark>],
     "type_hint": "single_hung|double_hung|casement|slider|picture|fixed|awning|unknown",
     "elevation": "front|back|left|right|unknown"  // WHICH elevation sheet shows this opening — match the schedule mark (W1, A…) to the elevation drawings. When qty > 1 spans multiple elevations, split into separate rows per elevation. "unknown" ONLY if the mark appears on no elevation.
    }
  ],
  "doors": [
    // Same shape as windows, but for EXTERIOR doors only (front entry,
    // patio sliders, garage). INTERIOR doors are NEVER returned.
    // THE PRODUCT-CODE COLUMN IS THE EXCLUSION SIGNAL (ruled 2026-08-08):
    // read the schedule's product/description column — "HOLLOW CORE",
    // "H DWL CORE", "Garage to House", closet/bifold/pocket wording =
    // INTERIOR, dropped, regardless of what the mark prefix looks like.
    // NEVER infer interior/exterior from the mark alone. A door is
    // EXTERIOR only when its row says an exterior product (entry/6-panel
    // front, sliding glass, garage SONOMA…), it appears on an ELEVATION
    // drawing, or its floor-plan wall sits on the building's outside
    // line. Name your evidence — rows with exterior_evidence "none" are
    // dropped and flagged.
    // DOOR SIZES COME FROM PRINT (ruled 2026-08-08): transcribe the
    // schedule's printed size VERBATIM into printed_size and parse it
    // into width_in/height_in. "Appears to be 16x7" is an ADMISSION OF
    // NO SOURCE — if no schedule row and no printed dim gives the size,
    // set width_in/height_in null. A guessed door size must never reach
    // the takeoff (garage doors print 8'-0" tall more often than the 7'
    // a guess reaches for).
    {"id": "<mark>",
     "printed_size": "<the door schedule's printed size VERBATIM (e.g. 16'-0\" x 8'-0\"); empty if the drawing prints none>",
     "width_in": number,
     "height_in": number,
     "qty": 1,
     "count_by_page": {"<sheet>": n},     // same COUNT COLUMN rule as windows — the printed COUNT cell per schedule sheet, verbatim; qty must equal their sum. NEVER count door symbols on a floor plan.
     "schedule_pages": [<1-based sheet numbers whose schedule lists this mark>],
ROW IDENTITY (ruled 2026-08-09): sibling schedule rows share a code prefix (SH 3-0_5-0 / SH 3-0_4-0 / SH 3-0_5-6) — the TRAILING digits ARE the row's identity. Transcribe each row's code, size and count from ITS OWN CELLS, glyph by glyph; NEVER reconstruct a row from its family and NEVER copy a sibling row's cells. Two marks NEVER share a product code on a real schedule — if your read gives two marks the same code, you have merged rows: go back and re-read the trailing digits of both.
     "type_hint": "entry|patio_slider|patio_french|garage|unknown",
     "exterior_evidence": "elevation|floor_plan_exterior_wall|none",
     "elevation": "front|back|left|right|unknown"  // which elevation sheet shows this door
    }
  ],
  "eaves_lf": number,          // sum of widths of EAVE walls only (i.e. walls where gable_triangle_height_ft == 0). For a typical gable-roof house with gables on front + back, this = left wall width + right wall width — NOT the full perimeter. Only equals the full perimeter when the roof is a hip (every wall has gable_triangle_height_ft = 0).
  "rakes_lf": number,          // sum of sloped roof edges = 2 × √((wall_width/2)² + gable_triangle_height_ft²) summed over each gable wall. This is the MAIN-BODY read only — secondary gabled planes (garage wing, cross-gables) carry their own rake_lf inside roof_planes[] and the app sums the planes when they exist.
  "roof_planes": [
    // EVERY roof plane that carries its own eave (gutter/fascia) line —
    // read the ROOF PLAN sheet FIRST, corroborate against the elevations.
    // Include the MAIN roof, the ATTACHED GARAGE roof, PORCH / PORTICO
    // roofs, and any secondary cross-gable. Do NOT collapse the house
    // into one rectangle: a projecting garage or covered porch has eave
    // runs the four-wall model cannot see. Report [] ONLY when the roof
    // plan truly shows a single plane pair.
    // SELF-CHECK before returning roof_planes: (1) Does the floor plan
    // or area table show an ATTACHED GARAGE (e.g. "3 CAR GARAGE",
    // "GARAGE 795 sq ft")? Does the ROOF PLAN show a second ridge /
    // separate truss field over the garage block? Then roof_planes MUST
    // contain a "garage" entry with its own eave_lf (the garage block's
    // gutter-carrying sides) — and if any elevation shows the garage
    // block ending in its own gable (an intersecting / double gable),
    // its rake_lf and gable_ends must be non-zero. (2) Does any
    // elevation/floor plan show a COVERED PORCH? Then a "porch" entry
    // with is_porch=true and its ceiling ft² (prefer the PRINTED porch
    // area from the area table; include EVERY porch, front and rear,
    // not just the one in the table). A missing plane is a missing
    // gutter run downstream — the four-wall rectangle CANNOT recover it.
    {"label": "main" | "garage" | "porch" | "entry" | "<other, verbatim from plan>",
     "eave_lf": DIM | null,            // horizontal eave (gutter) run this plane contributes, all sides summed — EVIDENCED ({"v","page","from"} quoting the printed dim string(s); a figure SUMMED from several printed dims uses the derived form {"v","calc","srcs":[...]}). null when the roof plan prints no dimension for it — NEVER a guess (bare numbers are DROPPED by the pipeline, ruled 2026-08-09)
     "rake_lf": DIM | null,            // TOTAL sloped rake edge on this plane — EVIDENCED the same way (derived form when computed from width + pitch: calc names the arithmetic, srcs quote the printed width and pitch). A plane with a GABLE END has rakes — NEVER 0 for a gabled plane. Per gable end: 2 × √((gable_width/2)² + ((gable_width/2) × pitch_rise/12)²). READ THE ELEVATIONS: an attached garage wing with ITS OWN gable — including an intersecting / double gable where the garage roof meets the main roof — contributes rake edges the main-rectangle walk cannot see. If any elevation shows a separate garage gable, that plane's rake_lf MUST come back non-null.
     "gable_ends": number,          // how many gable ends (triangular end faces) this plane carries: 0 for a hip or shed plane, 1 per gable end. The app reports the total across planes. THIS IS AN OWN COUNT — never inflate a plane's gable_ends with a triangle that belongs to another plane. If a front-facing ENTRY GABLE sits above the front door, it is ITS OWN plane (label:"entry") with gable_ends:1 — NEVER lumped into the garage or main count.
     "gable_end_faces": ["front"|"back"|"left"|"right"|"<other verbatim>"],  // REQUIRED when gable_ends > 0. List of length == gable_ends. Each entry names the ELEVATION FACE (front/back/left/right) the triangular gable end POINTS AT — i.e. the wall you see the triangle on when you look at that elevation sheet. The main body's two ends face L+R when the main gables are L+R; a garage wing that gables to the FRONT lists ["front"]; a garage that gables to BOTH front and back lists ["front","back"]. This is EVIDENCE for the app's attribution — an orphan gable end (no face named) is never silently distributed onto a wall (ruled 2026-08-11 send-6).
     "pitch": "<n/12 or empty>",       // THIS PLANE'S own printed pitch, e.g. "10/12" on an entry gable, "7/12" on the main body. PITCH-TRIANGLE NOTATION: RUN always 12, RISE is the other leg. Empty string when this plane has no printed pitch — NEVER inherit the main body pitch (ruled 2026-08-11 send-6: a gable at 10/12 against a main at 7/12 computes the wrong rise if forced to share).
     "is_porch": true | false,
     "porch_ceiling_sqft": number,  // porch planes only: ceiling area under the roof (soffit material, read porch depth × length from the floor plan); 0 otherwise
     "porch_width_ft": DIM | null,     // porch planes only: {"v","page","from"} — the porch's PRINTED floor-plan width (the side along the house wall). null when not dimensioned — NEVER derived from the area (an area does not determine a shape, ruled 2026-08-07)
     "porch_depth_ft": DIM | null,     // porch planes only: {"v","page","from"} — PRINTED depth (out from the wall). null when not dimensioned — NEVER √area, never a guess
     "overhang_in": DIM | null,        // PER-PLANE printed eave overhang depth in inches — e.g. 12 at main eaves, 0 at "FASCIA ONLY NO OVERHANG". null when this plane's overhang is not dimensioned — NEVER inherit from another plane (ruled 2026-08-11 send-6: overhang is per-location, one default does not cover a house that varies).
     "wall_height_ft": DIM | null      // OPTIONAL: printed wall (siding) height under this plane's eave — e.g. a garage wall printed 9'-11 7/8" is this plane's siding height. null when not dimensioned. The main-body wall heights ride walls[]; use this ONLY for planes whose walls are not in the four-wall list (garage/wing/porch faces).
    }
  ],
  // SELF-CHECK before returning roof_planes: (S1) EMIT-ONE-PER-END —
  // count every triangular gable end you can see across ALL elevations
  // AND the roof plan; the sum of gable_ends across roof_planes MUST
  // equal that count. If your count is 4 but only 3 planes are named
  // (main, garage, porch), you are missing a plane — probably an
  // ENTRY gable over the front door. Add it as its own plane with
  // label:"entry" (or a verbatim label from the plan) rather than
  // silently inflating garage.gable_ends. (S2) FACES-PER-END —
  // every plane with gable_ends > 0 lists gable_end_faces of the
  // same length; an orphan end (no face named) is refused by the
  // app's attribution — the miss is loud, never silently misfiled.
  // (S3) PITCH-PER-PLANE — a plane with printed pitch on its face
  // fills pitch; a plane with no printed pitch leaves pitch empty
  // (the app flags rather than inheriting).
  "starter_lf": number,        // full floor-plan PERIMETER in LF — report the RAW perimeter; the app deducts entry-door widths downstream per convention (sliders/patio doors sit on the starter). NOT eaves-only.
  "roof_pitch": "<the MAIN HOUSE BODY's printed pitch. PITCH-TRIANGLE NOTATION: the triangle marks print the RUN (always 12) on one leg and the RISE on the other — a triangle marked 12 and 7 means 7/12, NEVER 12/12 (only read 12/12 when BOTH legs print 12). Cross-gable houses print SEVERAL pitches (main body, garage/bonus wing, porch mono-truss shed) — report the pitch marked on the MAIN roof planes and name the others in notes. Corroborate against the drawn slope: a 12/12 draws at 45°, a 7/12 visibly shallower. Empty string if no pitch is printed anywhere>",
  "appendages": [
    // Siding-wrapped attached structures: chimney chases, bump-outs,
    // cantilevered boxes. Read from floor plan + elevations. These are
    // SEPARATE from walls[] — do NOT fold their area into any wall.
    {"wall": "front" | "back" | "left" | "right",
     "kind": "chimney_chase" | "bump_out" | "cantilever",
     "width_ft": number,
     "depth_ft": number,
     "height_ft": number,             // total vertical extent of the siding wrap (chimney chases often run past the eave — read the elevation)
     "extends_above_roofline": true | false,
     "position_frac": number,           // 0..1 — the appendage's CENTER along its wall, measured from the wall's LEFT edge as drawn on that elevation; null if not resolvable
     "faces_sqft": number}            // TOTAL siding-wrapped face area: outer face + both side returns
  ],
  "outside_corner_count": number, // INTEGER. Number of OUTSIDE corner locations on the FULL building outline. See "CORNER COUNTING" rule below.
  "outside_corner_lf": number, // SUM over outside corners of EACH CORNER'S OWN trim height. A 1-story garage-wing corner runs the GARAGE eave height; a 2-story main-body corner runs the FULL height. NEVER count × average height — a material-governing dimension is never averaged (261 Haugh doctrine: the average hides tall corners AND inflates short ones).
  "outside_corner_heights_ft": [DIM | null], // PER-CORNER trim heights as EVIDENCED DIMS ({"v","page","from"} in FEET), ONE entry per outside corner in walk order (ruled 2026-08-06). A corner joins TWO walls — report the TALLER wall's height, run to the EAVE the corner trim dies into. READ A PRINTED DIMENSION (ruled 2026-08-07): NEVER derive a corner height by stacking ceiling heights + floor structure — if your only basis is a calculation rather than a printed dim, return null for that corner and say so in notes. On a GABLE END the corner runs to the EAVE — never an area÷width figure, which lands between eave and ridge. null for a corner no printed dimension resolves — NEVER average or guess it.
  "gutter_runs": [ // GUTTER RUN INVENTORY (ruled 2026-08-06) — each CONTINUOUS eave run that carries gutter, walked along the FACADES. ONE entry per continuous run: where a lower roof's eave (garage bump-out) is flush and continuous with the run beside it, that is ONE run counted ONCE — never re-list a segment inside a run already listed. A porch lists only the eave sides that actually carry gutter. [] when the drawings don't resolve the runs — NEVER invent.
    {"label": "<front|back|left|right|porch|...>", "lf": DIM | null}  // EVIDENCED ({"v","page","from"} or the derived form when summed) — the run's length quotes the printed facade/eave dims it walks. null when no printed dim resolves it — NEVER a guess (ruled 2026-08-09)
  ],
  "inside_corner_count": number,  // INTEGER. Number of INSIDE corner locations on the floor plan. Default is NOT 0 — walk the perimeter and count.
  "inside_corner_lf": number,  // = inside_corner_count × avg_wall_height_ft.
  "soffit_sqft": number | null,        // PRINTED soffit/overhang area if the plans state it (eave detail sections, "SOFFIT" callouts, roof plan overhang dims × eave run). null if not printed — do NOT estimate.
  "eave_overhang_in": DIM | null,      // {"v","page","from"} — PRINTED eave overhang depth (soffit width) in INCHES from an eave detail/section or roof plan dim (e.g. 16). null when the drawings don't dimension it — NEVER a guess, NEVER a typical value. The app flags an undimensioned overhang instead of silently defaulting (ruled 2026-08-07).
  "fascia_width_in": DIM | null,       // {"v","page","from"} — PRINTED fascia board width in INCHES (e.g. a "1x6 FASCIA" callout → 6). null when not printed — same rule: flag, never default.
  "level_frieze_lf": number | null,    // PRINTED level frieze-board run if the elevations/details call it out. null if not printed.
  "sloped_frieze_lf": number | null,   // PRINTED sloped (rake) frieze-board run. null if not printed.
  "drip_edge_lf": number | null,       // PRINTED drip-edge / roof-edge perimeter from the roof plan. null if not printed.
  "total_trim_sqft": number | null,    // PRINTED trim area if a trim schedule/table states it. null if not printed.
  "footprint_area_sqft": number | null, // GROUND-FLOOR FOOTPRINT ONLY: first-floor area + attached garage, read from the floor plan or the labelled area rows. NEVER the "TOTAL FINISHED" / living-area figure — that SUMS STOREYS and is not a footprint (category error ruled 2026-08-08). null if not printed.
  "area_table": {                       // The printed AREA table, each row read AS LABELLED — never one quantity read as another (ruled 2026-08-08).
    "total_finished_sqft": number | null,
    "first_floor_sqft": number | null,
    "second_floor_sqft": number | null,
    "garage_sqft": number | null,
    "porch_sqft": number | null
  },
  "soffit_finish": {                    // Soffit finish ANNOTATIONS (e.g. "VENTED SOFFIT (EAVES) (TYP)", "SOLID SOFFIT (RAKE) (TYP)"). This is the vented-vs-solid steer STATED ON THE DRAWING — read it, never default it (ruled 2026-08-08). null when the drawings don't state it.
    "eaves": "vented" | "solid" | null,
    "rakes": "vented" | "solid" | null,
    "source_note": "<the annotation text verbatim; empty if none>"
  },
  "overhang_notes": [                   // Overhang is PER-LOCATION: report EVERY dimensioned overhang and every no-overhang annotation (e.g. 12 at the garage eave; "FASCIA ONLY NO OVERHANG" on an elevation → overhang_in 0). One default cannot cover a house that varies (ruled 2026-08-08).
    {"where": "<elevation/section, e.g. 'garage eave'>", "overhang_in": number, "text": "<annotation verbatim>"}
  ],
  "address": "<project address from the title block, verbatim; empty string if none printed>",
  "vent_unit_count": number,      // individual gable/roof VENT UNITS drawn on the elevations (one louver = 1 unit); 0 when none are drawn — count UNITS, never windows, never pairs (Q7 ruled 2026-07-27: vents ride the blueprint read; renamed 2026-08-10 so the field cannot be read two ways)
  "shutter_panel_count": number,  // individual shutter PANELS drawn on the elevations — a shuttered window carries 2 panels; count PANELS, never windows, never pairs; 0 when none are drawn (renamed 2026-08-10: the ordering unit is PAIRS and the app computes pairs = ceil(panels ÷ 2) — an ambiguous count here halves the order)
  "opening_facade_assignments": [      // ONLY if the plans EXPLICITLY assign an opening to a facade MATERIAL (e.g. a window drawn inside a hatched BRICK/STONE region with a material callout): {"id": "<mark>", "facade": "siding|stucco|brick|stone|metal|other"}. NEVER infer from elevation, type, or height — if the plans do not state it, return []. (Class C — R6 sealed 2026-07-28)
  ],
  "notes": "<2-3 sentences flagging anything to verify — missing dims, illegible numbers, etc.>"
}

CORNER COUNTING (read this carefully — this is where most readers
get the takeoff wrong):

Walk the floor-plan perimeter CLOCKWISE starting from any corner. At
every change of direction, classify the corner:

  • OUTSIDE corner (convex / 90° projecting outward) — the wall turns
    AWAY from the interior. From inside the house this corner looks
    like a 90° bend pointing OUT toward the yard. A simple rectangular
    house has exactly 4 outside corners. An L-shape has 5 outside
    corners. A T-shape has 6.

  • INSIDE corner (concave / 270° receding inward) — the wall turns
    TOWARD the interior. From inside the house this corner looks like
    a notch / armpit pointing IN. A simple rectangle has 0 inside
    corners. An L-shape has 1 inside corner. A T-shape has 2.

INVARIANT — verify this before returning:
  (outside_corner_count − inside_corner_count) MUST equal 4 for any
  closed building footprint. If your counts don't satisfy this,
  RE-WALK the perimeter — you mis-classified at least one corner.

Examples:
  • Pure rectangle:           4 outside, 0 inside  → 4 − 0 = 4 ✓
  • L-shape (one wing):       5 outside, 1 inside  → 5 − 1 = 4 ✓
  • T-shape (two wings):      6 outside, 2 inside  → 6 − 2 = 4 ✓
  • U-shape:                  6 outside, 2 inside  → 6 − 2 = 4 ✓
  • Cross / plus footprint:   8 outside, 4 inside  → 8 − 4 = 4 ✓
  • Footprint with bump-out:  6 outside, 2 inside  → 6 − 2 = 4 ✓

DO NOT default inside_corner_count to 0 unless you have walked the
perimeter and confirmed the footprint is a pure rectangle. Bump-outs,
breakfast nooks, mudroom additions, garage bumpouts, and L-wings ALL
create inside corners.

THE WALK COVERS THE FULL BUILDING OUTLINE — not the main living-space
rectangle. An ATTACHED GARAGE WING that projects from the body is part
of the footprint: its projecting corners are OUTSIDE corners and the
armpits where it returns to the body are INSIDE corners. A covered
PORCH with siding-wrapped posts/corners on the dimensioned floor plan
counts the same way. Trace the complete dimensioned outline off the
floor plan (garage wing + porch projection included) — a walk that
stops at the main rectangle under-counts every winged house.

WALK SELF-CHECK: compare the printed footprint area against your main
rectangle (front width × side width). If the footprint area is LARGER,
the building has a projecting wing — and a walk returning only the
rectangle's corner pattern missed it. Re-walk including the wing: a
projecting garage adds 2 outside corners at the GARAGE's own wall
height (armpit returns go to inside corners).

CHASE / APPENDAGE EDGES: a siding-wrapped chimney chase or bump-out adds
its own corner-trim edges. Report the chase itself via appendages[]
(width/depth/height/extends_above_roofline — the app pools its edges as
a separate corner feature downstream). Keep outside_corner_count /
outside_corner_lf to the HOUSE footprint walk only — do NOT fold chase
edges into them (double-count). DO include the 2 INSIDE corners where a
chase's sides return to the wall in inside_corner_count.

CRITICAL RULES:

A. PREFER PRINTED DIMS OVER ESTIMATION. If the floor plan shows "32'-0\""
   along the front wall, the front wall width is 32.0 ft — never round
   it to 30 or 35. If a dim is missing or illegible, set the wall to
   the best inferred value and FLAG IT in notes.

B. WINDOW / DOOR SCHEDULE WINS. If a schedule sheet is present, the
   `windows` and `doors` arrays must reflect THE SCHEDULE exactly — same
   quantities, same RO sizes. The floor-plan callouts are only the
   tie-breaker when the schedule omits a mark. Schedules SPAN SHEETS:
   each floor's plan sheet may carry its own schedule — read them ALL
   and sum counts BY MARK across sheets (one row per mark, total qty);
   a per-sheet mark is not a distinct mark.

C. PARSE "3-6 5-0" AS WIDTH-HEIGHT IN FEET-INCHES. The first pair is
   ALWAYS width, the second pair is ALWAYS height. Convert each pair to
   inches: e.g. 3-6 → 3*12 + 6 = 42, 5-0 → 5*12 = 60. NEVER swap them.
   The 4-digit form "3050" is the SAME pattern: first 2 digits → 3-0,
   last 2 digits → 5-0. Confirm by sanity-checking the result:
     - Window heights are 36–84" (most are 48–72")
     - Door heights are 78–84"
   If your parse gives a window 96" tall, you parsed it wrong.

D. STORY COUNT IS DETERMINED BY THE ELEVATIONS, NOT THE FLOOR PLAN. If
   you see a 2nd-floor plan sheet, the house is 2-story (or 1.5). If
   the elevation shows one row of windows under the eave, it's 1-story.

E. SIDING vs MASONRY: Plans often callout "BRICK VENEER" or "STONE
   WAINSCOT TO 36\"". Reflect these by reducing siding_pct_this_wall
   (e.g. brick wainscot to 36" on a 9 ft wall → ~67% siding above).
   When in doubt, assume 100% siding and flag in notes.

F. PROFILE CALLOUTS PER ELEVATION (Iter 78z — REQUIRED):
   Construction prints almost always print the siding profile in plain
   text directly on (or near) the siding surface — common labels are
   "LAP 4\"", "DUTCH LAP", "VINYL", "SHAKER", "SHAKE", "B&B",
   "BOARD AND BATTEN", "VERTICAL", "NICKEL GAP", "STONE WATERTABLE".
   For every elevation page, capture FOUR distinct callouts:
     1. `wall_body_profile_callout` — the main field of the wall
     2. `gable_profile_callout`     — only if there's a visible gable
                                        triangle on this elevation
     3. `dormer_profile_callout`    — only if there's a dormer
     4. `accent_profiles[]`         — SMALL accent zones with a
                                        DIFFERENT profile from the body
                                        (porch face B&B, column wrap
                                        shake, bay-window cheek
                                        vertical, kneewall B&B, entry-
                                        roof gable shake). Estimate the
                                        approx ft² for each accent.
   ACCENT ZONES ARE THE #1 SOURCE OF UNDER-QUOTING on Howard's mixed-
   material houses. A single 24"-wide B&B porch face costs ~$80 in
   material — miss it on 20% of jobs and you lose real money. Look
   for any printed text or any visible texture/pattern that differs
   from the main wall body. Always include accents you suspect, even
   if you're uncertain.

F. ROUNDING:
     - Wall widths to nearest 0.5 ft
     - Wall heights to nearest 0.5 ft
     - Window/door RO sizes to the nearest inch (parsed exactly from plan)
     - Eaves/rakes to nearest 1 ft

G. IF A SHEET IS NOT USEFUL (cover, site plan, foundation plan, electrical),
   list it in sheets_identified with useful_for="other" and ignore it.

H. NEVER FABRICATE. If you can't find a window schedule and the floor
   plan callouts are illegible, return windows=[] and flag it in notes —
   do NOT invent placeholder windows.

Return ONLY the JSON object. No explanation, no code fences."""


def _resolve_blueprint_key() -> tuple[str, str]:
    """Transport cutover (2026-07-14, Howard's ruling): blueprint extraction
    rides the SAME direct-Anthropic transport as the photo pipeline —
    single-source doctrine. The Emergent proxy is a fallback only when no
    direct key is configured (logged loudly, stamped on the run doc)."""
    direct = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if direct:
        return direct, "anthropic_direct"
    proxy = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if proxy:
        logger.warning("[ai-blueprint] ANTHROPIC_API_KEY absent — falling back to Emergent proxy transport")
        return proxy, "emergent_proxy"
    raise HTTPException(status_code=500, detail="No AI key configured (ANTHROPIC_API_KEY / EMERGENT_LLM_KEY)")


def _media_type(img_bytes: bytes) -> str:
    return "image/png" if img_bytes.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg"


async def _claude_direct_blueprint(
    *,
    api_key: str,
    model_name: str,
    image_payloads: list[bytes],
    user_text: str,
    timeout_s: int = 240,
    system_text: str | None = None,
) -> tuple[str, dict | None, str | None]:
    """One multi-image messages.create against api.anthropic.com. Mirrors
    the photo pipeline's direct transport (SDK max_retries=0, explicit
    httpx timeouts, outer asyncio cap). Returns (reply_text, usage, stop_reason).
    Claude 4.5+ interleaves thinking blocks on the direct API — only
    visible text blocks are concatenated (same parsing as ai_measure)."""
    from anthropic import AsyncAnthropic
    import httpx as _httpx
    client = AsyncAnthropic(
        api_key=api_key,
        max_retries=0,
        timeout=_httpx.Timeout(timeout_s, connect=10.0, read=timeout_s - 15, write=45.0),
    )
    content: list[dict] = [
        {"type": "image", "source": {
            "type": "base64",
            "media_type": _media_type(p),
            "data": base64.b64encode(p).decode("ascii"),
        }}
        for p in image_payloads
    ]
    content.append({"type": "text", "text": user_text})
    response = await asyncio.wait_for(
        client.messages.create(
            model=model_name,
            max_tokens=16000,
            # Ruled 2026-08-07: temperature=0 pinned on extraction runs —
            # cuts sampling noise. It does NOT satisfy the determinism
            # gate and NEVER claims correctness: agreement between reads
            # is not the same claim as matching a printed dimension.
            temperature=0.0,
            system=system_text or SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        ),
        timeout=timeout_s,
    )
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
        if btype == "text":
            parts.append(getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else "") or "")
    reply_text = "".join(parts)
    stop_reason = getattr(response, "stop_reason", None)
    if stop_reason == "max_tokens":
        raise RuntimeError("direct reply truncated at max_tokens — JSON incomplete")
    usage = getattr(response, "usage", None)
    usage_stamp = None
    if usage is not None:
        usage_stamp = {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        }
    return reply_text, usage_stamp, stop_reason


def _json_from_reply(text: str) -> dict:
    """Pull the first {...} JSON object out of Claude's reply."""
    text = (text or "").strip()
    fence = re.match(r"^```(?:json)?\s*(\{.*\})\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise HTTPException(status_code=502, detail="AI did not return JSON")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}")


# ---------------------------------------------------------------------------
# INT-KEY WRITE GUARD (Howard sealed 2026-08-14 send-25). A non-string dict
# key reaching a BSON write crashed a whole read once (run 2, page-index key
# 11). The str() fix for _ocr_page_coverage_chars was FIELD-BY-FIELD and the
# class survived it — Ruling GG adds another page-indexed dict, so the guard
# is now mandatory and lives at THE single write boundary, recursively.
# RIDER: it RECORDS every fire on the doc (_int_key_coercions) so the
# upstream source stays visible rather than being laundered at the boundary.
_OCR_ONDOC_MAX_BYTES = 8 * 1024 * 1024   # >8MB OCR blob ⇒ move off the run doc
_OCR_HARD_MAX_BYTES = 15 * 1024 * 1024   # a single OCR doc must clear BSON's ceiling


def _coerce_bson_keys(obj, path, fired):
    """Recursively coerce every non-string dict key to str at the write
    boundary. Appends '<path>.<key>' to `fired` for each coercion so the
    int-keyed source is named, never silently normalised. Lists/scalars
    pass through; only dict keys are touched."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ck = k if isinstance(k, str) else str(k)
            if ck is not k and not isinstance(k, str):
                fired.append(f"{path}.{ck}")
            out[ck] = _coerce_bson_keys(v, f"{path}.{ck}", fired)
        return out
    if isinstance(obj, list):
        return [_coerce_bson_keys(v, f"{path}[{i}]", fired)
                for i, v in enumerate(obj)]
    return obj


def _bson_len(doc) -> int:
    try:
        import bson
        return len(bson.BSON.encode(doc))
    except Exception:
        return 0


async def _persist_ocr_text(run_id, raw) -> None:
    """RULING GG (send-25): persist the per-page OCR. DEFAULT is onto the run
    doc; when the blob would push the run doc toward BSON's ceiling it moves
    to its OWN collection (ai_blueprint_ocr) keyed by run_id — Howard's escape
    hatch over truncation. `_ocr_text_ref` ALWAYS names where the OCR lives so
    a lookup can find it. Truncation fires only if even a standalone OCR doc
    would bust the hard ceiling; it is loud and specific (page → dropped
    count) so a later lookup that could have hit a dropped run resolves to
    UNVERIFIED, never NOT LOCATED."""
    blob = raw.get("_ocr_text_by_page")
    if not blob:
        return
    size = _bson_len({"by_page": blob})
    if size <= _OCR_ONDOC_MAX_BYTES:
        raw["_ocr_text_ref"] = {"where": "run_doc", "approx_bytes": size,
                                "pages": sorted(blob.keys())}
        return
    # Move off the run doc into its own collection.
    raw.pop("_ocr_text_by_page", None)
    truncated: dict = {}
    if size > _OCR_HARD_MAX_BYTES:
        # LAST RESORT: halve the largest run lists until under the ceiling,
        # recording exactly which pages lost how many runs.
        for pg in sorted(blob, key=lambda p: -len(blob[p].get("runs") or [])):
            runs = blob[pg].get("runs") or []
            keep = max(1, len(runs) // 2)
            if keep >= len(runs):
                continue
            truncated[pg] = len(runs) - keep
            blob[pg]["runs"] = runs[:keep]
            blob[pg]["_truncated_dropped"] = len(runs) - keep
            if _bson_len({"by_page": blob}) <= _OCR_HARD_MAX_BYTES:
                break
    fired: list = []
    doc = _coerce_bson_keys(
        {"run_id": run_id, "by_page": blob, "truncated": truncated or None},
        "ocr", fired)
    doc["_int_key_coercions"] = fired
    if truncated:
        logger.warning("[ai-blueprint] OCR truncation (LAST RESORT) run=%s dropped=%s",
                       run_id, truncated)
    await db.ai_blueprint_ocr.replace_one({"run_id": run_id}, doc, upsert=True)
    raw["_ocr_text_ref"] = {"where": "ai_blueprint_ocr", "run_id": run_id,
                            "approx_bytes": size, "pages": sorted(blob.keys()),
                            "truncated": truncated or None}



# =========================================================================
# ROOF GEOMETRY PASS (Boni second send, Howard 2026-08-05). The single
# 11-sheet read repeatedly dropped the garage roof plane and the garage-
# wing corners (3 consecutive reads) — attention dilution across dense
# sheets. When the main read shows GARAGE EVIDENCE (garage doors) but no
# garage plane, a SECOND focused call gets ONLY the roof plan +
# elevations + floor plan and does exactly two jobs: the roof-plane
# census and the full-outline corner walk. Merge is CONSERVATIVE and
# pure (`_merge_roof_pass`, pinned): planes accepted only when they add
# the garage entry; corners only when the walk invariant (out − in = 4)
# holds and the count did not shrink; pitch only in N/12 form.
# =========================================================================
ROOF_PASS_PROMPT = """You are a construction-print ROOF & FOOTPRINT reader. You receive ONLY the roof plan, elevation, and floor-plan sheets of one house. IGNORE windows, doors, siding profiles — you have exactly two jobs.

JOB 1 — ROOF PLANE CENSUS. List EVERY roof plane pair that carries its own eave (gutter/fascia) line: the MAIN roof, the ATTACHED GARAGE roof (the area table and a second ridge/truss field on the roof plan prove it exists — a "3 CAR GARAGE" on the floor plan ALWAYS has a roof over it), the ENTRY / PORTICO gable if the front elevation shows a triangular gable over the front door (its own plane, its own rise), PORCH roofs (mono/shed count too), and any secondary cross-gable. A plane with a GABLE END has rake_lf — per gable end: 2 × √((gable_width/2)² + ((gable_width/2) × rise/12)²). An attached garage ending in its own gable (including an intersecting/double gable where the garage roof meets the main roof) MUST come back with non-zero rake_lf and gable_ends. EMIT-ONE-PER-END: sum of gable_ends across planes MUST equal the total number of triangular gable ends visible on the elevations — if you count 4 ends and only have 3 planes, you are missing a plane (probably ENTRY) — add it rather than lumping the end into garage.
PITCH-TRIANGLE NOTATION: the triangle marks print the RUN (always 12) on one leg and the RISE on the other — a mark showing 12 and 7 means 7/12, NEVER 12/12 (only 12/12 when BOTH legs print 12). Report the MAIN body pitch in roof_pitch AND each plane's own pitch in its `pitch` field — a cross-gable house prints SEVERAL pitches (main 7/12, entry 10/12, garage its own) and the app flags rather than inheriting when a plane's pitch is not printed.

JOB 2 — FULL-OUTLINE CORNER WALK. Walk the COMPLETE dimensioned floor-plan outline clockwise — garage wing and porch projection INCLUDED, never just the main rectangle. At every direction change: OUTSIDE corner (turns away from interior) or INSIDE corner (notch/armpit). INVARIANT: outside − inside MUST equal 4; re-walk if not. outside_corner_lf = SUM of each corner's OWN trim height (1-story garage-wing corners run the garage eave height; 2-story corners the full height — NEVER count × average height). ALSO return outside_corner_heights_ft: one entry PER corner in walk order — the corner joins TWO walls, report the TALLER wall's height, run to the EAVE the corner trim dies into (on a gable end the corner runs to the EAVE, never an area÷width figure); null when no printed dimension resolves that corner — never average or guess.

JOB 3 — GUTTER RUN INVENTORY. List each CONTINUOUS eave run that carries gutter, walked along the FACADES (front/back/left/right/porch). ONE entry per continuous run: where a lower roof's eave (garage bump-out) is flush and continuous with the run beside it, that is ONE run counted ONCE — never re-list a segment inside a run already listed. A porch lists only the eave sides that actually carry gutter. [] when the drawings don't resolve the runs.

Return ONLY this JSON, no explanation:
{
  "roof_pitch": "<main body pitch, e.g. '7/12'>",
  "roof_planes": [
    {"label": "main" | "garage" | "porch" | "entry" | "<other>",
     "eave_lf": {"v": number, "page": n, "from": "<printed dim VERBATIM>"} | null,
     "rake_lf": {"v": number, "page": n, "from": "<printed dim VERBATIM>"} | null,  // derived form {"v","calc","srcs":[...]} when computed from width + pitch
     "gable_ends": number,
     "gable_end_faces": ["front"|"back"|"left"|"right"|"<other>"],  // REQUIRED when gable_ends > 0; length == gable_ends; names the elevation face each triangle points at (the wall you see the triangle on)
     "pitch": "<n/12 or empty>",  // THIS plane's own printed pitch; empty when not printed — NEVER inherit main
     "is_porch": true | false, "porch_ceiling_sqft": number,
     "overhang_in": {"v": number, "page": n, "from": "<printed dim VERBATIM>"} | null,  // per-plane printed overhang, null when not dimensioned
     "wall_height_ft": {"v": number, "page": n, "from": "<printed dim VERBATIM>"} | null}  // printed wall height under this plane's eave when the wall is not in the four-wall main list (e.g. garage wing wall)
  ],
  "outside_corner_count": number, "outside_corner_lf": number,
  "outside_corner_heights_ft": [{"v": number, "page": n, "from": "<printed dim VERBATIM>"} | null],  // ONE entry per outside corner in walk order — null when no printed dimension resolves that corner, NEVER a guess or an average (bare numbers are DROPPED by the pipeline)
  "inside_corner_count": number, "inside_corner_lf": number,
  "gutter_runs": [{"label": "<front|back|left|right|porch|...>", "lf": {"v": number, "page": n, "from": "<printed dim VERBATIM>"} | null}],
  "notes": "<secondary pitches, anything illegible>"
}"""

_PITCH_RE = re.compile(r"^\d{1,2}(\.\d+)?/12$")


def _dim_v(x) -> float:
    """Numeric view of a value that may still be a DIM object ({'v',...})
    — pre-enforcement code paths (roof-pass merge) compare magnitudes
    without touching the evidence."""
    if isinstance(x, dict):
        x = x.get("v")
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _carries_ev(x) -> bool:
    """True when a value carries printed evidence (a 'from' quote, or a
    derived form whose srcs quote print)."""
    if not isinstance(x, dict):
        return False
    if str(x.get("from") or "").strip():
        return True
    srcs = x.get("srcs")
    return isinstance(srcs, list) and any(
        isinstance(s, dict) and str(s.get("from") or "").strip() for s in srcs)


def _merge_roof_pass(raw: dict, rp: dict) -> dict:
    """Pure, conservative merge of the focused roof pass into the main
    read. Mutates and returns `raw`. Provenance lands in raw['_roof_pass'].
    REGISTERED SEAM (Howard ruled 2026-08-09 send 7, after the register
    audit found this merge unregistered): every geometry overwrite is
    ledgered old→new (roof_pass_overwrite), and the merge MAY NEVER
    replace an EVIDENCED value with an unevidenced one — a rejected
    overwrite is NAMED on the rail, never silent."""
    if not isinstance(rp, dict):
        return raw
    accepted: dict = {}
    rejected: dict = {}
    overwrites: list[str] = []
    old_planes = [p for p in (raw.get("roof_planes") or []) if isinstance(p, dict)]
    new_planes = [p for p in (rp.get("roof_planes") or []) if isinstance(p, dict)]

    def _garage_of(planes):
        for p in planes:
            if "garage" in str(p.get("label") or "").lower():
                return p
        return None

    old_g, new_g = _garage_of(old_planes), _garage_of(new_planes)
    if new_g and not old_g and old_planes:
        # Whole plane missing → append it (a missing plane is a missing
        # gutter run; the focused read is the only source).
        raw["roof_planes"] = old_planes + [new_g]
        accepted["garage_plane_appended"] = new_g
    elif new_g and old_g and _dim_v(new_g.get("rake_lf")) > 0 \
            and _dim_v(old_g.get("rake_lf")) == 0 \
            and int(old_g.get("gable_ends") or 0) == 0:
        # SURGICAL: the full-context read keeps its eave figure; the
        # focused read (which actually looked at the gable) supplies
        # ONLY the rake edges + gable-end census it missed. The DIM
        # object rides whole — evidence is never stripped in a merge.
        old_g["rake_lf"] = new_g.get("rake_lf")
        old_g["gable_ends"] = int(new_g.get("gable_ends") or 0)
        accepted["garage_rakes"] = {"rake_lf": _dim_v(old_g["rake_lf"]),
                                    "gable_ends": old_g["gable_ends"]}
    pitch = str(rp.get("roof_pitch") or "").strip()
    _old_pitch = str(raw.get("roof_pitch") or "").strip()
    if pitch and _PITCH_RE.match(pitch) and pitch != _old_pitch:
        raw["roof_pitch"] = pitch
        accepted["roof_pitch"] = pitch
        overwrites.append(
            f"roof_pitch {_old_pitch or '(unread)'}→{pitch}"
            " (+gable triangles recomputed at the new pitch)")
        # The schema's own formula, printed-pitch authority: a corrected
        # pitch recomputes each gable wall's triangle (and with it the
        # gable siding area downstream).
        try:
            rise = float(pitch.split("/")[0])
            for w in raw.get("walls") or []:
                if isinstance(w, dict) and float(w.get("gable_triangle_height_ft") or 0) > 0:
                    w["gable_triangle_height_ft"] = round(
                        (float(w.get("width_ft") or 0) / 2) * rise / 12, 2)
        except (TypeError, ValueError):
            pass
    try:
        oc = int(rp.get("outside_corner_count") or 0)
        ic = int(rp.get("inside_corner_count") or 0)
        oclf = float(rp.get("outside_corner_lf") or 0)
        old_oc = int(raw.get("outside_corner_count") or 0)
        old_ic = int(raw.get("inside_corner_count") or 0)
        old_oclf = float(raw.get("outside_corner_lf") or 0)
    except (TypeError, ValueError):
        oc = ic = 0
        oclf = 0.0
        old_oc = old_ic = 0
        old_oclf = 0.0
    agree = oc > 0 and old_oc > 0 and (oc, ic) == (old_oc, old_ic)
    filled = False
    if oc > 0 and old_oc > 0 and not agree:
        # AGREEMENT-OR-FLAG (Howard ruled 2026-08-10): disagreement KEEPS
        # THE PRIMARY and fires a loud corner_walk_conflict PRINTING BOTH
        # NUMBERS. Max-wins acceptance is dead — a bigger number winning
        # by default systematically over-orders.
        raw["_corner_walk_conflict"] = {
            "primary": {"out": old_oc, "in": old_ic, "lf": old_oclf},
            "roof_pass": {"out": oc, "in": ic, "lf": oclf}}
        rejected["corners"] = (
            f"walks disagree — primary read {old_oc} outside/{old_ic} "
            f"inside, roof pass {oc} outside/{ic} inside; the primary "
            "stands, neither is adopted as truth")
    elif oc > 0 and old_oc <= 0 and (oc - ic) == 4 and oclf > 0:
        # FILL — the primary read carried no corner walk at all.
        raw["outside_corner_count"] = oc
        raw["outside_corner_lf"] = oclf
        raw["inside_corner_count"] = ic
        if rp.get("inside_corner_lf"):
            raw["inside_corner_lf"] = float(rp["inside_corner_lf"])
        accepted["corners"] = {"outside": oc, "inside": ic, "outside_lf": oclf}
        filled = True
    if agree or filled:
        # PER-CORNER HEIGHTS (ruled 2026-08-06): ride ONLY with an agreed
        # or filled walk and only when one entry per counted corner came
        # back. NEVER-TOUCH RULE (ruled 2026-08-09 send 7): a primary read
        # whose heights carry printed quotes is NEVER overwritten by a
        # roof pass returning bare numbers — that replacement destroyed
        # the evidence AND the value.
        hs = rp.get("outside_corner_heights_ft")
        if isinstance(hs, list) and len(hs) == oc:
            old_hs = raw.get("outside_corner_heights_ft")
            old_has_ev = isinstance(old_hs, list) and any(
                _carries_ev(h) for h in old_hs)
            new_has_ev = any(_carries_ev(h) for h in hs)
            if old_has_ev and not new_has_ev:
                rejected["corner_heights"] = (
                    "primary heights carry printed quotes; the roof pass "
                    "returned bare numbers — an evidenced value is never "
                    "replaced by an unevidenced one")
            else:
                if isinstance(old_hs, list) and any(
                        h is not None for h in old_hs):
                    overwrites.append(
                        f"corner_heights {len(old_hs)} entr"
                        f"{'y' if len(old_hs) == 1 else 'ies'} replaced "
                        f"({len(hs)} from the roof pass)")
                raw["outside_corner_heights_ft"] = hs
                accepted["corner_heights"] = [
                    _dim_v(h) if h is not None else None for h in hs]
    # GUTTER RUN INVENTORY (ruled 2026-08-06): conservative — only fills
    # a read that has none.
    runs = [r for r in (rp.get("gutter_runs") or []) if isinstance(r, dict)]
    if runs and not raw.get("gutter_runs"):
        raw["gutter_runs"] = runs
        accepted["gutter_runs"] = runs
    raw["_roof_pass"] = {"accepted": accepted, "rejected": rejected,
                         "notes": rp.get("notes") or ""}
    if overwrites:
        seam_accounting.account(raw, "roof_pass_overwrite", overwrites)
    return raw


def _roof_pass_sheet_indexes(raw: dict, page_count: int) -> list[int]:
    """Roof plan + elevations + floor plans from the main read's own sheet
    census, capped at 5 images (roof sheets first)."""
    picked: list[tuple[int, int]] = []  # (priority, index)
    prio = {"roof": 0, "elevation": 1, "floor_plan": 2}
    for s in raw.get("sheets_identified") or []:
        if not isinstance(s, dict):
            continue
        use = str(s.get("useful_for") or "")
        if use not in prio:
            continue
        idx = int(s.get("page") or 0) - 1
        if 0 <= idx < page_count:
            picked.append((prio[use], idx))
    picked.sort()
    return [i for _, i in picked[:5]]


def _roof_pass_needed(raw: dict) -> bool:
    planes = [p for p in (raw.get("roof_planes") or []) if isinstance(p, dict)]
    garage = [p for p in planes
              if "garage" in str(p.get("label") or "").lower()]
    garage_evidence = (
        any(str(d.get("type_hint") or "") == "garage" for d in raw.get("doors") or [])
        or any("garage" in str(w.get("label") or "").lower() for w in raw.get("walls") or [])
    )
    if not garage_evidence:
        return False
    if not garage:
        return True
    # Garage plane present but gable-blind (rake 0 AND no gable ends) —
    # the focused read verifies the elevation's gable.
    return all(_dim_v(p.get("rake_lf")) == 0
               and int(p.get("gable_ends") or 0) == 0 for p in garage)


# =========================================================================
# BLUEPRINT READ-BACK CARD (Howard authorized 2026-08-06 — first build off
# demo-lock). DISPLAY-ONLY: this function reads the run's raw extraction
# and returns visibility flags. It RECOMPUTES NOTHING about derivation,
# WRITES NOTHING (computed on read in the status/latest endpoints, never
# persisted), and touches no quantity, price, or money surface. Purpose:
# every Boni geometry miss (dropped garage gable, phantom porch, missing
# wing corners) was invisible in the material list — this card makes the
# READ itself visible so Howard verifies geometry by looking.
# =========================================================================
def _parse_printed_size(s: str) -> tuple[float, float] | None:
    """Parse a schedule size string to (w_in, h_in). Handles 3-0x5-0,
    3050, 3'-0\" x 5'-0\", 2-4_5-4 and SIZE-column feet-inch-fraction
    strings (2'-11 1/2\" x 4'-11 1/2\" → 35.5×59.5 — ruled 2026-08-08:
    the SIZE column governs, so its format must parse). Returns None
    when unparseable — NEVER guesses (a bad parse is worse than no
    check)."""
    txt = str(s or "").strip().upper()
    if not txt:
        return None
    txt = txt.replace("×", "X")
    # Strip letter runs (SH, DH prefixes) but KEEP the standalone X
    # separator — stripping it first would shred "2'-11 1/2\" x 4'-11 1/2\"".
    txt = re.sub(r"\b(?!X\b)[A-Z]+\b", " ", txt).strip()
    m = re.match(r"^(\d{2})(\d{2})$", txt.replace(" ", ""))
    if m:
        return (float(m.group(1)[0]) * 12 + float(m.group(1)[1]),
                float(m.group(2)[0]) * 12 + float(m.group(2)[1]))

    def _part_to_inches(p: str) -> float | None:
        pm = re.match(r"^\s*(\d+)\s*['\-]+\s*(\d+)(?:\s+(\d+)\s*/\s*(\d+))?\s*[\"”]?\s*$", p)
        if pm:
            v = float(pm.group(1)) * 12 + float(pm.group(2))
            if pm.group(3):
                v += float(pm.group(3)) / float(pm.group(4))
            return v
        pm = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[\"”]?\s*$", p)
        if pm:
            v = float(pm.group(1))
            return v * 12 if v < 12 else v
        return None

    # Explicit separators first — whitespace splitting would shred a
    # fraction like 2'-11 1/2".
    parts = [p for p in re.split(r"\s*[X_]\s*", txt) if p.strip()]
    if len(parts) != 2:
        parts = [p for p in re.split(r"\s+", txt) if p]
    if len(parts) != 2:
        return None
    dims = [_part_to_inches(p) for p in parts]
    if None in dims:
        return None
    return (dims[0], dims[1])


# ---------------------------------------------------------------------------
# EVIDENCE-OR-NULL (Howard ruled 2026-08-08, STRUCTURAL — top item):
# "Abstention must not be something the model chooses. It must be
# something the schema enforces." Every registered dimension arrives as
# {"v": number, "page": n, "from": "<printed string verbatim>"}. A bare
# number — or an object without a quoted source string — is NULL BY
# CONSTRUCTION: the pipeline drops it, the flag fires, and the card says
# the drawing does not dimension it. Same shape as source retention:
# don't ask the model to behave, make the wrong behaviour unrepresentable.
_EVIDENCE_SCALARS = ("eave_overhang_in", "fascia_width_in")


def _norm_loc(loc):
    """Validates a vision-returned percent box {x_pct,y_pct,w_pct,h_pct}
    (top-left origin, 0-100). Junk never rides — an invalid box is None,
    and a box NEVER rescues a missing quote."""
    if not isinstance(loc, dict):
        return None
    out = {}
    for k in ("x_pct", "y_pct", "w_pct", "h_pct"):
        try:
            v = float(loc.get(k))
        except (TypeError, ValueError):
            return None
        if not (0 <= v <= 100):
            return None
        out[k] = round(v, 2)
    if out["w_pct"] <= 0 or out["h_pct"] <= 0:
        return None
    return out


def _ev_extract(x):
    """Returns (value|None, evidence|None, had_unevidenced_number).
    Single-source evidence: {"v","page","from","loc"}. Derived (Visual
    Audit design req 2, ruled 2026-08-08 — many highlights plus the
    arithmetic, never one box per number): {"v","calc","srcs":[...]}."""
    if isinstance(x, dict):
        v = x.get("v")
        try:
            v = float(v) if v is not None else None
        except (TypeError, ValueError):
            v = None
        srcs_in = x.get("srcs")
        if v is not None and isinstance(srcs_in, list):
            srcs = []
            for s in srcs_in:
                if not isinstance(s, dict):
                    continue
                frm = str(s.get("from") or "").strip()
                if not frm:
                    continue
                try:
                    page = int(s.get("page")) if s.get("page") is not None else None
                except (TypeError, ValueError):
                    page = None
                srcs.append({"page": page, "from": frm,
                             "loc": _norm_loc(s.get("loc"))})
            if srcs:
                calc = str(x.get("calc") or "").strip() or None
                return v, {"v": v, "calc": calc, "srcs": srcs}, False
            return None, None, True
        frm = str(x.get("from") or "").strip()
        if v is not None and frm:
            page = x.get("page")
            try:
                page = int(page) if page is not None else None
            except (TypeError, ValueError):
                page = None
            return v, {"v": v, "page": page, "from": frm,
                       "loc": _norm_loc(x.get("loc"))}, False
        return None, None, v is not None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return None, None, True
    return None, None, False


def _enforce_evidence_or_null(raw: dict) -> dict:
    """Normalizes evidence-bearing dims back to plain numbers for the
    whole downstream (aggregation, readback, checker untouched), stamps
    `_dim_evidence` {path: {page, from}}, and NULLS anything that arrived
    without a quoted printed string — recorded in `_nulled_no_evidence`."""
    if not isinstance(raw, dict):
        return raw
    evidence: dict = {}
    nulled: list[str] = []
    unread: list[str] = []

    def _norm(container, key, path):
        if key not in container:
            return
        val, ev, bare = _ev_extract(container.get(key))
        if ev:
            evidence[path] = ev
            container[key] = val
        else:
            container[key] = None
            if bare:
                nulled.append(path)
            else:
                unread.append(path)

    for k in _EVIDENCE_SCALARS:
        _norm(raw, k, k)
    for i, w in enumerate(raw.get("walls") or []):
        if not isinstance(w, dict):
            continue
        label = str(w.get("label") or i)
        for k in ("width_ft", "height_ft"):
            _norm(w, k, f"walls.{label}.{k}")
        for j, s in enumerate(w.get("height_segments") or []):
            if isinstance(s, dict):
                seg = str(s.get("label") or j)
                for k in ("width_ft", "height_ft"):
                    _norm(s, k, f"walls.{label}.segments.{seg}.{k}")
    for p in (raw.get("roof_planes") or []):
        if isinstance(p, dict) and p.get("is_porch"):
            for k in ("porch_width_ft", "porch_depth_ft"):
                _norm(p, k, f"porch.{k}")
    # BARE-NUMBER EVIDENCE (Howard ruled 2026-08-09): the instability
    # that remained lived exactly in the unguarded family — roof-plane
    # eave/rake figures and gutter runs join the evidence discipline.
    # SEND-6 EXTENSION (Howard ruled 2026-08-12 send-8 mechanism report):
    # the send-6 per-plane wall_height_ft and overhang_in joined the
    # evidence discipline TOO — they were emitted as {v,page,from}
    # dicts but bypassed _normalize_evidence, which meant the locator
    # never saw them and a hallucinated "9'-6\" garage wall" reached
    # the readback verbatim. Closed here.
    for i, p in enumerate(raw.get("roof_planes") or []):
        if not isinstance(p, dict):
            continue
        label = str(p.get("label") or i)
        for k in ("eave_lf", "rake_lf", "overhang_in", "wall_height_ft"):
            _norm(p, k, f"roof_planes.{label}.{k}")
    for i, g in enumerate(raw.get("gutter_runs") or []):
        if isinstance(g, dict):
            _norm(g, "lf", f"gutter_runs.{str(g.get('label') or i)}.lf")
    hs = raw.get("outside_corner_heights_ft")
    if isinstance(hs, list):
        out = []
        for i, h in enumerate(hs):
            val, ev, bare = _ev_extract(h)
            if ev:
                evidence[f"corner_heights.{i}"] = ev
                out.append(val)
            else:
                out.append(None)
                if bare:
                    nulled.append(f"corner_heights.{i}")
                else:
                    unread.append(f"corner_heights.{i}")
        raw["outside_corner_heights_ft"] = out
    if evidence:
        raw["_dim_evidence"] = evidence
    if nulled:
        raw["_nulled_no_evidence"] = nulled
        seam_accounting.account(raw, "dims_nulled_no_evidence", nulled)
    if unread:
        # NO-SOURCE IS A FIRST-CLASS STATE (Visual Audit design req 3,
        # ruled 2026-08-08): dims the read abstained on are NAMED, not
        # omitted — "no source on the drawing" renders as clearly as a
        # highlight.
        raw["_dim_unread"] = unread
    return raw


def _enforce_count_column(raw: dict) -> dict:
    """THE COUNT COLUMN GOVERNS COUNTS (Howard ruled 2026-08-08, enforced
    at the seam 2026-08-09 — the prompt rule alone left the rerun at 23
    vs the printed 16). Both halves of the ruling, plainly:
      DO NOT count symbols on floor plans, ever.
      DO sum the printed COUNT COLUMN across sheets for the same mark
      (A: 2 on sheet 6 + 7 on sheet 7 = 9 — a per-sheet mark row is not
      a distinct mark).
    A mark the schedule prints no count for CONTRIBUTES NOTHING — it is
    flagged, never estimated. Nothing here invents a number: every qty
    written is the sum of printed cells; every removal is accounted."""
    if not isinstance(raw, dict):
        return raw
    governed: list[dict] = []
    unread: list[dict] = []
    conflicts: list[dict] = []
    merges: list[str] = []
    for coll in ("windows", "doors"):
        rows = [r for r in (raw.get(coll) or []) if isinstance(r, dict)]
        if not rows:
            continue

        def _cells(r):
            c = r.get("count_by_page")
            return c if isinstance(c, dict) and c else None

        # ---- per-sheet mark rows merge into ONE mark (counts summed) ----
        # Merge only when count cells exist for the mark — a same-mark
        # split WITHOUT cells is the elevation split the prompt asks for
        # and stays untouched. Rows whose printed sizes disagree are NOT
        # merged (the Mark-B sin: one mark wearing another's dimensions);
        # mark_size_conflict names them for a human.
        by_mark: dict[str, dict] = {}
        out: list[dict] = []
        for r in rows:
            mk = str(r.get("id") or "").strip().upper()
            base = by_mark.get(mk) if mk else None
            can_merge = (
                base is not None
                and (_cells(base) or _cells(r))
                and not (str(base.get("printed_size") or "").strip()
                         and str(r.get("printed_size") or "").strip()
                         and str(base.get("printed_size")).strip()
                         != str(r.get("printed_size")).strip()))
            if not can_merge:
                if mk and mk not in by_mark:
                    by_mark[mk] = r
                out.append(r)
                continue
            merges.append(f"{coll}:{mk}")
            rc = _cells(r)
            if rc:
                bc = base.get("count_by_page")
                if not isinstance(bc, dict):
                    bc = {}
                    base["count_by_page"] = bc
                for k, v in rc.items():
                    k = str(k)
                    if k in bc and bc[k] != v:
                        conflicts.append({"mark": mk, "sheet": k,
                                          "cells": f"{bc[k]} vs {v}"})
                    else:
                        bc[k] = v
            sp = {*(base.get("schedule_pages") or []),
                  *(r.get("schedule_pages") or [])}
            if sp:
                base["schedule_pages"] = sorted(sp)
            if not str(base.get("printed_size") or "").strip():
                base["printed_size"] = r.get("printed_size")
            try:
                base["qty"] = int(base.get("qty") or 0) + int(r.get("qty") or 0)
            except (TypeError, ValueError):
                pass

        # ---- the printed COUNT cells govern qty ----
        any_cells = any(_cells(r) for r in out)
        for r in out:
            mk = str(r.get("id") or "").strip().upper() or "?"
            cbp = _cells(r)
            if cbp:
                try:
                    total = sum(int(v) for v in cbp.values())
                except (TypeError, ValueError):
                    unread.append({"kind": coll, "mark": mk})
                    r["qty"] = 0
                    r["_count_unread"] = True
                    continue
                try:
                    carried = int(r.get("qty") or 0)
                except (TypeError, ValueError):
                    carried = 0
                if carried != total:
                    governed.append({
                        "kind": coll, "mark": mk,
                        "carried": carried, "governed": total,
                        "cells": ", ".join(f"sheet {k}: {v}"
                                           for k, v in sorted(cbp.items()))})
                r["qty"] = total
            elif any_cells:
                # The schedule prints counts — a mark row with no cell
                # contributes NOTHING (flagged, never estimated).
                unread.append({"kind": coll, "mark": mk})
                r["qty"] = 0
                r["_count_unread"] = True
        if coll == "windows" and out and not any_cells:
            raw.setdefault("_count_column_absent", []).append(coll)
        raw[coll] = out
    if merges:
        raw["_mark_rows_merged"] = merges
        seam_accounting.account(raw, "mark_rows_merged", merges)
    if governed:
        raw["_count_column_governed"] = governed
        seam_accounting.account(
            raw, "count_column_governed",
            [f"{g['kind']}:{g['mark']} {g['carried']}→{g['governed']}"
             for g in governed])
    if unread:
        raw["_count_cells_unread"] = unread
        seam_accounting.account(
            raw, "count_cells_unread",
            [f"{u['kind']}:{u['mark']}" for u in unread])
    if conflicts:
        raw["_count_cell_conflicts"] = conflicts
    return raw


def _pdf_rect_to_pct(rect, page_w, page_h):
    """PDF-space rect (l, b, r, t — bottom-left origin, points) → top-left
    percent box matching the rendered page image."""
    l, b, r, t = rect
    if page_w <= 0 or page_h <= 0:
        return None
    return {"x_pct": round(l / page_w * 100, 2),
            "y_pct": round((1 - t / page_h) * 100, 2),
            "w_pct": round((r - l) / page_w * 100, 2),
            "h_pct": round((t - b) / page_h * 100, 2)}


def _exact_locate_evidence(evidence: dict, source_files: list,
                           source_probe: dict | None) -> None:
    """VISUAL AUDIT precision labelling (design req 1, ruled 2026-08-08):
    on a scan the box is vision-returned pixels — APPROXIMATE, labelled
    so; never a tight box implying precision we do not have. On a native
    PDF the quoted string is searched in the text layer — a hit yields an
    EXACT box. A miss never invents one; precision None = quote only."""
    if not isinstance(evidence, dict) or not evidence:
        return

    def _entries():
        for ev in evidence.values():
            if not isinstance(ev, dict):
                continue
            for s in (ev.get("srcs") or [ev]):
                if isinstance(s, dict):
                    yield s

    for s in _entries():
        s["precision"] = "approximate" if s.get("loc") else None

    kind = str((source_probe or {}).get("kind") or "")
    if kind not in ("native_text", "mixed"):
        return
    pdf_name = next((f.get("name") for f in (source_files or [])
                     if isinstance(f, dict) and f.get("kind") == "pdf"), None)
    if not pdf_name:
        return
    from config import UPLOAD_DIR
    target = UPLOAD_DIR / pdf_name
    if not target.exists():
        return
    try:
        doc = pdfium.PdfDocument(target.read_bytes())
    except Exception:
        return
    try:
        n_pages = len(doc)
        for s in _entries():
            frm = str(s.get("from") or "").strip()
            page_no = s.get("page")
            if not frm or not isinstance(page_no, int) or not (1 <= page_no <= n_pages):
                continue
            try:
                page = doc[page_no - 1]
                tp = page.get_textpage()
                found = tp.search(frm, match_case=False).get_next()
                if found is not None:
                    idx, count = found
                    boxes = [tp.get_charbox(i) for i in range(idx, idx + count)]
                    rect = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                            max(b[2] for b in boxes), max(b[3] for b in boxes))
                    w, h = page.get_size()
                    loc = _pdf_rect_to_pct(rect, w, h)
                    if loc:
                        s["loc"] = loc
                        s["precision"] = "exact"
                tp.close()
                page.close()
            except Exception:
                continue
    finally:
        doc.close()


_OCR_ENGINE = None


def _get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def _ocr_norm(s: str) -> str:
    """Print-vs-OCR glyph noise (58'-0\" reads back as 58-0°) dies under
    alphanumeric-only normalisation."""
    return re.sub(r"[^0-9A-Za-z]", "", str(s or "")).upper()


# OMISSION CHECK + DOOR SIGNAL vocab (Howard ruled 2026-08-09).
_SCHED_CODE_RE = re.compile(r"^(SH|DH|CSMT|CS|AWN|SLD|SL)\d{3,4}$")
_DOOR_MARK_RE = re.compile(r"^[A-Z]{1,2}\d{1,2}$")
_INTERIOR_MARKERS = ("HOLLOWCORE", "HDWLCORE", "GARAGETOHOUSE")


def _del1(a: str, b: str) -> bool:
    """True when `a` is `b` with exactly one character deleted (the
    SH340-vs-SH3040 OCR glyph-drop class)."""
    if len(a) + 1 != len(b):
        return False
    i = j = skips = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
        else:
            skips += 1
            if skips > 1:
                return False
        j += 1
    return True


def _ocr_runs(arr):
    """OCR one raster array → [(norm, raw, (x0,y0,x1,y1))] in that
    array's own coordinates."""
    res, _elapse = _get_ocr_engine()(arr)
    runs = []
    for box, text, _score in (res or []):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        nt = _ocr_norm(text)
        if nt:
            runs.append((nt, str(text), (min(xs), min(ys), max(xs), max(ys))))
    return runs


def _map_rot_box(rect, k, w, h):
    """Map a box from np.rot90(arr, k) coordinates back to upright page
    coordinates (w, h are the UPRIGHT page dims)."""
    x0r, y0r, x1r, y1r = rect
    if k == 1:      # CCW: upright x = W-1-yr, y = xr
        return (w - 1 - y1r, x0r, w - 1 - y0r, x1r)
    return (y0r, h - 1 - x1r, y1r, h - 1 - x0r)  # k == 3, CW


def _ocr_match(runs, nq):
    """The model's normalised quote against the OCR run index. Exact
    beats containment; the tightest run wins."""
    cands = [r for r in runs if r[0] == nq]
    if not cands:
        cands = [r for r in runs if nq in r[0] and len(r[0]) <= len(nq) + 6]
    if not cands:
        return None
    cands.sort(key=lambda r: len(r[0]))
    return cands[0][2]


# FRACTION SKELETON (Howard ruled 2026-08-09, lifted to module level and
# INTO the EXISTENCE test 2026-08-14 send-12). The OCR engine cannot read
# the stacked ½ / ¼ glyphs at all, so a printed-and-true 24'-0 1/2" misses
# on its full norm and dies at existence though it is on the page. Its
# fraction-STRIPPED skeleton (24'-0") is tried as a fallback: "the
# fractions rest on the read's transcription".
#
# HARD BOUND (ruled, pinned — never a comment alone): the strip removes
# ONLY a fraction-of-an-inch token (\d+/\d+, optional trailing "), NEVER a
# whole digit. So 24'-0" carries no fraction ⇒ produces NO skeleton ⇒ can
# never skeleton-match 2'-0" (a 12× error wearing a located chip). The
# stripped part is always a fraction of an inch, so the magnitude risk
# stays bounded.
_FRACTION_TOKEN_RE = re.compile(r"\s*\d+/\d+\s*\"?")


def _fraction_skeleton(q: str):
    """The quote with every fraction-of-an-inch token stripped, or None
    when the quote carries NO fraction (nothing to strip — a whole-inch
    quote produces no skeleton and can never skeleton-match anything)."""
    s = str(q or "")
    stripped = _FRACTION_TOKEN_RE.sub("", s)
    if stripped == s:
        return None
    return stripped


def _skeleton_locate_unique(pool, skel_nq):
    """Locate a fraction skeleton in the OCR run pool, REFUSING an
    ambiguous hit (Howard ruled 2026-08-14 send-12: an ambiguous skeleton
    never locates). Returns (rect, ambiguous):
      * exactly one DISTINCT run rect matches → (rect, False)
      * more than one distinct run rect matches → (None, True)
        (24'-0 1/2" and 24'-0 1/4" both skeleton to 24'-0"; a hit against
        two printed 24'-0" runs cannot tell which it found)
      * no match → (None, False)."""
    cands = [r for r in pool if r[0] == skel_nq]
    if not cands:
        cands = [r for r in pool
                 if skel_nq in r[0] and len(r[0]) <= len(skel_nq) + 6]
    if not cands:
        return None, False
    distinct = {tuple(round(c, 1) for c in r[2]) for r in cands}
    if len(distinct) > 1:
        return None, True
    cands.sort(key=lambda r: len(r[0]))
    return cands[0][2], False


# --------- FEATURE-PROXIMITY GATE (Howard ruled 2026-08-12 send-8) ---------
# "A LOCATING MATCH MUST SIT NEAR THE FEATURE IT CLAIMS TO DIMENSION,
# not merely somewhere on the same page." The pre-send-8 OCR locator
# accepted any run whose norm equalled/contained the quote's norm at
# ANY pixel position — so a real "9'-6"" printed anywhere on the page
# could satisfy a "garage wall" quote (the E1 "30" bug one field
# over). This gate requires the located rect's centre to sit within
# radius of a feature-anchor run's bbox on the same page. No feature
# anchor visible ⇒ refuse the locate.
#
# SEND-9 CALIBRATION (Howard ruled 2026-08-12 send-9 item 1): a
# WALL WIDTH has no printed text label — 58'-0" sits under the drawing
# with no word nearby. Refusing "walls.front.width_ft" for lack of a
# nearby FRONT token nulled a printed and true dimension. The right
# anchor for a wall-direction path is the ELEVATION SHEET REGION IT
# BELONGS TO, not a text token. When the page CARRIES a cardinal
# direction word anywhere (in the sheet title or as an OCR run on the
# page), the WHOLE PAGE is the feature — any match on that page
# qualifies. Label-bound paths (GARAGE, PORCH, ENTRY, MAIN BODY, etc.)
# keep the tighter proximity radius so a run somewhere else on the
# page cannot masquerade as the labelled feature's dim.

# Path segments that are structural, not features (skipped for anchoring).
_ANCHOR_SKIP = {
    "walls", "segments", "roof_planes", "gutter_runs",
    "corner_heights", "porch", "openings", "windows", "doors",
    "outside_corner_heights_ft", "eave_lf", "rake_lf",
    "width_ft", "height_ft", "porch_width_ft", "porch_depth_ft",
    "overhang_in", "wall_height_ft", "lf",
}

# Cardinal wall-direction anchors: no printed text on the drawing
# itself — the elevation SHEET is the feature.
_CARDINAL_ANCHORS = {"FRONT", "BACK", "REAR", "LEFT", "RIGHT",
                     "SIDE", "SOUTH", "NORTH", "EAST", "WEST"}

# SEND-9 addendum: cardinal synonyms — plan sets commonly print
# "REAR" where the app model asks for BACK, and either can name the
# same elevation. Kept intentionally narrow; SIDE is NOT a synonym
# for LEFT/RIGHT because "SIDE ELEVATION" is ambiguous.
_CARDINAL_SYNONYMS = {
    "BACK": {"BACK", "REAR"},
    "REAR": {"BACK", "REAR"},
    "FRONT": {"FRONT"},
    "LEFT": {"LEFT"},
    "RIGHT": {"RIGHT"},
}

# DRAWN-GEOMETRY CLASSIFICATION (Howard ruled 2026-08-14 send-12).
# A sheet that carries drawn geometry prints its dimensions AS geometry,
# never beside a text label — so the tight label-bound proximity radius is
# a BROKEN INSTRUMENT on it and presence-only must apply. The four drawing
# kinds the model emits are elevation, floor_plan, roof and OTHER: a joist
# plan / detail / mech / elec page types as "other" (never a named drawing
# kind), and page 9's genuinely-printed dims died at existence precisely
# because "other" was excluded by the old enumerated {elevation,
# floor_plan} list. Only SCHEDULE (table) and COVER (title page) keep the
# tight radius. An UNCLASSIFIED sheet ("" — the model omitted the field)
# also stays strict rather than loosen an unknown that might be a mistyped
# table; the model's enum always emits one of the six on a real read.
#
# NOTE (override HELD — ruling 3 part 2): a page mistyped as schedule/cover
# that actually carries drawn geometry would still over-kill through a
# different door. The content-based override (re-check schedule/cover pages
# against their own feet-inch dimension-token count) is NOT wired: it needs
# a REAL plan set with schedule/cover pages to pick a non-invented
# threshold, and Boni carries no such page. See
# scripts/drawn_geometry_token_report.py.
_DRAWING_SHEET_KINDS = {"elevation", "floor_plan", "roof", "other"}
# Back-compat alias (kept for any external reference).
_WALL_DIM_SHEET_KINDS = _DRAWING_SHEET_KINDS


def _sheet_carries_geometry(useful_for: str) -> bool:
    """True when the sheet carries drawn geometry (presence-only applies)."""
    return useful_for in _DRAWING_SHEET_KINDS


# PROPOSED drawn-geometry SIGNAL for the schedule/cover content override
# (Howard ruled 2026-08-14 send-12, ruling 3 part 2 — THRESHOLD HELD).
# A page mistyped schedule/cover but actually carrying geometry would
# over-kill through a different door; the fix is to re-check such a page
# against its own feet-inch dimension-token count. This counter is the
# ONE definition of that signal, shared by the report; it is NOT wired to
# the live gate because a non-invented threshold needs a REAL plan set
# with schedule/cover pages, and Boni carries none. See
# scripts/drawn_geometry_token_report.py.
_FEET_INCH_RE = re.compile(r"\d+\s*['\u2019]\s*-?\s*\d+|\d+\s*-\s*\d+")


def _feet_inch_dim_tokens(runs) -> int:
    """Count OCR runs whose RAW text reads as a feet-inch dimension
    (24'-0, 24-0, 12' 6). Report-only proposed signal; never a live gate."""
    n = 0
    for r in runs:
        raw = r[1] if len(r) > 1 else ""
        if _FEET_INCH_RE.search(str(raw)):
            n += 1
    return n


def _feature_anchors_for_path(path: str) -> list[str]:
    """Return normalised feature-anchor tokens derived from the
    evidence path. Empty when the path names no locatable feature
    (e.g. a bare scalar like `eave_overhang_in`)."""
    if not path or "." not in path:
        # Bare scalar top-level dim (eave_overhang_in, fascia_width_in,
        # etc.) — no feature anchor. Gate does not apply; legacy
        # locator decides.
        return []
    parts = [p for p in path.split(".")
             if p and p.lower() not in _ANCHOR_SKIP]
    if not parts:
        return []
    # Each part may contain spaces / slashes — split those too.
    anchors = []
    for p in parts:
        for tok in re.split(r"[\s/]+", p):
            n = _ocr_norm(tok)
            if len(n) >= 3:
                anchors.append(n)
    return anchors


def _path_is_sheet_scoped(path: str) -> bool:
    """SEND-9: a wall-direction (cardinal) path with no non-cardinal
    label is sheet-scoped — the ELEVATION SHEET IS THE FEATURE.
    Examples: walls.front.width_ft, gutter_runs.back.lf. Segment
    paths (walls.front.segments.<seg>.*) are NOT sheet-scoped: they
    carry a labelled sub-feature and keep the tighter radius."""
    anchors = _feature_anchors_for_path(path)
    if not anchors:
        return False
    # Any non-cardinal anchor → labelled feature → tight radius.
    return all(a in _CARDINAL_ANCHORS for a in anchors)


def _sheet_scoped_for(path: str, sheet_useful_for: str) -> bool:
    """SEND-9 COMPLETION (Howard ruled 2026-08-14, widened same day).

    The locator gate runs two tests: does the quote EXIST in OCR (catches
    FABRICATION), and does it sit NEAR its feature (catches
    MISATTRIBUTION). On a DRAWING sheet (elevation / floor plan) the
    second test is a BROKEN INSTRUMENT for EVERY dimension on the page —
    a drawing prints dimensions as geometry, never beside a text label
    reading 'MAIN BODY 2-STORY'. Cardinal-vs-non-cardinal is an accident
    of path naming, not a property of the sheet, so the loosening applies
    to the WHOLE drawing sheet: presence-only for every dim on it. The
    existence test still stands, so fabricated quotes (the 39'-0" sides,
    absent from OCR) still die.

    The tight label-bound radius survives ONLY on SCHEDULE / TABLE sheets,
    where text labels are real and proximity earns its keep (the E1 '30'
    match came off a schedule, not an elevation)."""
    if _path_is_sheet_scoped(path):
        return True
    return _sheet_carries_geometry(sheet_useful_for)


def _rect_center(rect):
    x0, y0, x1, y1 = rect
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _within_radius(rect_a, rect_b, radius: float) -> bool:
    ax, ay = _rect_center(rect_a)
    bx, by = _rect_center(rect_b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 <= radius


def _anchor_runs_on_page(runs, anchors: list[str]) -> list:
    """Runs whose norm contains ANY anchor token. Long labels win
    (a run of just 'GARAGE' anchors tighter than an area-table row
    that includes 'GARAGE' among many words)."""
    hits = []
    for r in runs:
        norm = r[0]
        if any(a in norm for a in anchors):
            hits.append(r)
    hits.sort(key=lambda r: len(r[0]))
    return hits


def _proximity_ok(match_rect, anchor_runs, radius: float) -> bool:
    if not anchor_runs:
        return False
    return any(_within_radius(match_rect, a[2], radius)
               for a in anchor_runs)


def _ocr_match_near_feature(runs, joined_runs, nq, anchors, radius,
                             *, sheet_scoped: bool = False,
                             sheet_title: str = "",
                             sheet_useful_for: str = ""):
    """Same rule as _ocr_match — but every candidate must sit within
    radius of a feature-anchor run on this page. Empty `anchors` ⇒
    the gate does not apply and we fall back to _ocr_match.

    SEND-9: when `sheet_scoped=True` (a wall-direction / cardinal
    path), the whole page IS the feature when ANY of:
      (a) OCR runs on the page carry the cardinal token (or its
          synonym — BACK ↔ REAR)
      (b) the sheet's own title carries the cardinal (or synonym)
      (c) the sheet's `useful_for` is `elevation` or `floor_plan`
          (floor plans show all four walls with no per-direction
          label — sheet TYPE is enough anchor).
    In that case ANY match on the page passes."""
    if not anchors:
        return _ocr_match(runs + joined_runs, nq), None
    pool = runs + joined_runs
    if sheet_scoped:
        # Expand each cardinal anchor with its synonyms.
        expanded: set[str] = set()
        for a in anchors:
            expanded.update(_CARDINAL_SYNONYMS.get(a, {a}))
        title_norm = _ocr_norm(sheet_title)
        anchor_hits = _anchor_runs_on_page(pool, list(expanded))
        title_has_it = any(a in title_norm for a in expanded)
        sheet_kind_ok = _sheet_carries_geometry(sheet_useful_for)
        if not anchor_hits and not title_has_it and not sheet_kind_ok:
            return None, (f"cardinal anchor {sorted(expanded)!r} not on sheet "
                          "(no OCR run, no sheet title match, sheet class "
                          f"{sheet_useful_for!r} does not carry wall dims)")
        # Sheet-scoped: legacy locator decides among candidates on this page.
        rect = _ocr_match(pool, nq)
        if rect is None:
            return None, "quote norm not present in OCR on page"
        return rect, None
    # Label-bound: tighter radius rule stands.
    anchor_hits = _anchor_runs_on_page(pool, anchors)
    if not anchor_hits:
        return None, f"no feature anchor {anchors!r} on page"
    exact = [r for r in pool if r[0] == nq
             and _proximity_ok(r[2], anchor_hits, radius)]
    contain = [r for r in pool
               if nq in r[0] and len(r[0]) <= len(nq) + 6
               and _proximity_ok(r[2], anchor_hits, radius)]
    cands = exact or contain
    if not cands:
        return None, (f"quote matched but no candidate within {int(radius)}px "
                      f"of feature anchor {anchors!r}")
    cands.sort(key=lambda r: len(r[0]))
    return cands[0][2], None


def _join_adjacent_runs(runs, max_window=8):
    """ADJACENT-RUN JOINING (Howard ruled 2026-08-09): OCR fragments
    fraction-heavy cells — 2'-11 1/2" x 4'-11 1/2" comes back as separate
    runs and a CORRECT quote was killed by tokenization ("an instrument
    that kills good data is a defect, not a virtue"). Runs sharing a text
    line join into synthetic runs (norms concatenated, boxes unioned) so
    a multi-token quote can locate. Originals are never replaced."""
    lines = []
    for r in sorted(runs, key=lambda r: ((r[2][1] + r[2][3]) / 2, r[2][0])):
        _, _, (x0, y0, x1, y1) = r
        placed = False
        for ln in lines:
            ov = min(y1, ln["y1"]) - max(y0, ln["y0"])
            if ov > 0.5 * max(1, min(y1 - y0, ln["y1"] - ln["y0"])):
                ln["runs"].append(r)
                ln["y0"], ln["y1"] = min(ln["y0"], y0), max(ln["y1"], y1)
                placed = True
                break
        if not placed:
            lines.append({"y0": y0, "y1": y1, "runs": [r]})
    joined = []
    for ln in lines:
        rs = sorted(ln["runs"], key=lambda r: r[2][0])
        for i in range(len(rs)):
            norm, rawtxt = rs[i][0], rs[i][1]
            x0, y0, x1, y1 = rs[i][2]
            for j in range(i + 1, min(i + max_window, len(rs))):
                jx0, jy0, jx1, jy1 = rs[j][2]
                h = max(y1 - y0, jy1 - jy0, 1)
                if jx0 - x1 > 3.0 * h:
                    break
                norm += rs[j][0]
                rawtxt += " " + rs[j][1]
                x1 = max(x1, jx1)
                y0, y1 = min(y0, jy0), max(y1, jy1)
                joined.append((norm, rawtxt, (x0, y0, x1, y1)))
    return joined


def _ocr_locate_evidence(evidence: dict, image_payloads: list, raw: dict) -> None:
    """OCR-FOR-COORDINATES (Howard ruled 2026-08-08, live-fire item 2
    PARTIAL — 1 box in 22): local OCR over the retained page rasters,
    every text run indexed with its box, the model's VERBATIM quote
    matched to the OCR box. HARD SEPARATION, THE RULING: OCR SUPPLIES
    LOCATION, NEVER VALUE. It is never promoted to ground truth (the
    three-class probe rule stands); the model still does the reading —
    this function touches loc/precision ONLY, never v or from.
    ROTATED PASS (ruled 2026-08-08 send 5): plan dims print vertically;
    until rotation is covered, "OCR missed it" and "the model invented
    it" are indistinguishable — and that distinction decides whether the
    evidence layer can be trusted at all. Pages whose quotes miss the
    upright pass are re-read at 90° CCW and CW with boxes mapped back to
    upright page coordinates.
    FREE SECOND READ: a quote no pass can find is a NAMED contradiction
    (_ocr_quote_misses) — two independent reads of the same pixels
    disagreeing, resolved toward neither."""
    if not isinstance(evidence, dict):
        # SEND-30 item 2 (Howard sealed 2026-08-16): OCR is COVERAGE now,
        # not just quote-location. It reads EVERY page — not "every plan
        # and elevation page" decided by a classifier, every page — even
        # when the model quoted nothing. Which pages get OCR'd must never
        # again be a function of what the model happened to say.
        evidence = {}
    if not image_payloads:
        return
    # SEND-9: sheet-title AND useful_for lookup by page — for cardinal
    # wall paths (walls.front.*, gutter_runs.back.lf) the sheet IS the
    # feature. A page typed as elevation or floor_plan carries wall
    # dimensions of any direction (floor plans show all four walls at
    # once with no per-direction label).
    _sheets_by_page: dict[int, dict] = {}
    for _s in (raw.get("sheets_identified") or []):
        if isinstance(_s, dict) and isinstance(_s.get("page"), int):
            _sheets_by_page[_s["page"]] = {
                "title": str(_s.get("sheet_title") or ""),
                "useful_for": str(_s.get("useful_for") or ""),
            }
    wanted: dict[int, list] = {}
    for path, ev in evidence.items():
        if not isinstance(ev, dict):
            continue
        for s in (ev.get("srcs") or [ev]):
            if not isinstance(s, dict) or s.get("precision") == "exact":
                continue
            page = s.get("page")
            nq = _ocr_norm(s.get("from"))
            if isinstance(page, int) and 1 <= page <= len(image_payloads) and len(nq) >= 3:
                wanted.setdefault(page, []).append((path, s, nq))
    import numpy as np
    misses = []
    # FRACTION-SKELETON LOCATES (2026-08-14 send-12): quotes rescued at
    # the existence test by their fraction-stripped skeleton — NAMED, not
    # counted as located-clean and never as fabricated/unverified.
    _skeleton_located: list[dict] = []
    # SEND-11 item 3: page-level OCR-coverage tracking. When a quote
    # miss lands, the page's total OCR character count decides whether
    # a fabrication verdict is STRONG evidence (a densely-read page
    # with no hit ⇒ the string genuinely is not there) or WEAK evidence
    # (a page OCR barely read — stacked-fraction cells, low contrast —
    # ⇒ "not found" may be OCR's fault, not the model's).
    page_ocr_chars: dict[int, int] = {}
    # SEND-11 item 2: rotated + upright OCR norms per page fuel the
    # MISREAD scanner — a quote no pass could locate, but sitting one
    # character-edit from a real run on the same page's pixels, is a
    # TRANSCRIPTION error, not a fabrication.
    page_run_norms: dict[int, list[str]] = {}
    # RULING GG (Howard sealed 2026-08-14 send-25): PERSIST the OCR text
    # with page + per-string position. The (norm, raw, bbox) tuple already
    # computed for matching is discarded today; keep ALL of it (no per-page
    # cap — an arbitrary N drops the one dimension that matters). Positions
    # are PERCENT-of-page (resolution-independent — absolute pixels die on a
    # re-raster at a different DPI); the page's own dims ride alongside so a
    # highlight renders back. raw is what a contractor sees printed and is
    # the only version worth quoting; norm is what matching uses — both persist.
    ocr_text_by_page: dict[str, dict] = {}
    for page in range(1, len(image_payloads) + 1):
        entries = wanted.get(page, [])
        try:
            with Image.open(io.BytesIO(image_payloads[page - 1])) as im:
                w, h = im.size
                arr = np.array(im.convert("RGB"))
            runs = _ocr_runs(arr)
            joined = _join_adjacent_runs(runs)
        except Exception:
            logger.exception("[ai-blueprint] OCR failed on page %s — quote anchors stand", page)
            continue
        # SEND-30 item 1 (Howard sealed 2026-08-16): rotated passes run on
        # EVERY page. Depth dimensions are rotated by definition; the old
        # trigger filter (rotate only on quote-misses) plus upright-only
        # persistence made every depth on every plan sheet structurally
        # invisible to the persisted store — side faces were never able to
        # derive on any house.
        rot_passes: dict[int, tuple] = {}
        for _k in (1, 3):
            try:
                _rr = _ocr_runs(np.rot90(arr, _k))
                rot_passes[_k] = (_rr, _join_adjacent_runs(_rr))
            except Exception:
                logger.exception("[ai-blueprint] rotated OCR (k=%s) failed on page %s", _k, page)
        # RULING GG + SEND-30: persist EVERY run from EVERY pass with its
        # percent-box, the pass that read it (src) and its glyph-normalized
        # axis class. Rotated boxes map back to upright page coordinates.
        _pw, _ph = max(w, 1), max(h, 1)

        def _run_doc(_r, _src, _rect):
            _loc = {"x_pct": round(_rect[0] / _pw * 100, 2),
                    "y_pct": round(_rect[1] / _ph * 100, 2),
                    "w_pct": round(max(_rect[2] - _rect[0], 1) / _pw * 100, 2),
                    "h_pct": round(max(_rect[3] - _rect[1], 1) / _ph * 100, 2)}
            return {"norm": _r[0], "raw": _r[1], "loc": _loc, "src": _src,
                    "axis": ocr_geometry.axis_class(
                        _loc, ocr_geometry.glyph_count(_r[1]))}

        _persisted = [_run_doc(_r, "upright", _r[2]) for _r in runs]
        for _k, (_rr, _rj) in rot_passes.items():
            _src = "rot90" if _k == 1 else "rot270"
            _persisted.extend(
                _run_doc(_r, _src, _map_rot_box(_r[2], _k, w, h))
                for _r in _rr)
        ocr_text_by_page[str(page)] = {
            "page_w": int(w), "page_h": int(h), "runs": _persisted,
        }
        # Coverage = summed length of every distinct normalised token
        # across ALL passes (upright + joined + rotated 90°/270°) —
        # recorded for every page so the coverage is visible.
        _norms_seen: set[str] = {r[0] for r in runs} | {j[0] for j in joined}
        for _rr, _rj in rot_passes.values():
            _norms_seen.update(r[0] for r in _rr)
            _norms_seen.update(j[0] for j in _rj)
        page_ocr_chars[page] = sum(len(n) for n in _norms_seen)
        page_run_norms[page] = sorted(_norms_seen)
        if not entries:
            continue
        # FEATURE-PROXIMITY RADIUS (Howard ruled 2026-08-12 send-8):
        # the located rect's centre must sit within this radius of a
        # feature-anchor run on the same page. 30% of the longer page
        # side allows a labelled section on a large plan sheet to fit
        # without covering the whole page.
        radius = 0.30 * max(w, h)
        sheet = _sheets_by_page.get(page, {})
        sheet_title = sheet.get("title", "")
        sheet_useful_for = sheet.get("useful_for", "")
        # FRACTION-SKELETON AMBIGUITY GUARD (Howard ruled 2026-08-14
        # send-12): a skeleton is only usable when it is UNSHARED on this
        # page. If two DISTINCT full quotes strip to the same skeleton
        # (24'-0 1/2" and 24'-0 1/4" → 24'-0"), a skeleton hit cannot tell
        # which it found, so NEITHER may locate by skeleton. Map
        # skeleton-norm → the set of distinct full-quote norms carrying it.
        skel_owners: dict[str, set] = {}
        for _p2, _s2, _nq2 in entries:
            _sk2 = _fraction_skeleton(str(_s2.get("from") or ""))
            if _sk2:
                _skn2 = _ocr_norm(_sk2)
                if len(_skn2) >= 3:
                    skel_owners.setdefault(_skn2, set()).add(_nq2)

        def _try_skeleton(pool, s, sheet_scoped, anchors):
            """Rescue a MISSED quote by its fraction skeleton, or None.
            Refuses a shared skeleton (page ambiguity) and an ambiguous
            run match (multiple distinct rects). Respects the same
            feature gate as the primary locate. Returns (rect, skel_norm)."""
            sk = _fraction_skeleton(str(s.get("from") or ""))
            if not sk:
                return None
            skn = _ocr_norm(sk)
            if len(skn) < 3:
                return None
            if len(skel_owners.get(skn, set())) > 1:
                return None  # shared skeleton on this page — cannot crown one
            if sheet_scoped:
                cand_pool = pool
            elif anchors:
                anchor_hits = _anchor_runs_on_page(pool, anchors)
                if not anchor_hits:
                    return None
                cand_pool = [r for r in pool
                             if _proximity_ok(r[2], anchor_hits, radius)]
            else:
                cand_pool = pool
            rect, _ambig = _skeleton_locate_unique(cand_pool, skn)
            if rect is None:
                return None  # absent OR ambiguous — never a locate
            return rect, skn

        pending = []
        for path, s, nq in entries:
            anchors = _feature_anchors_for_path(path)
            sheet_scoped = _sheet_scoped_for(path, sheet_useful_for)
            rect, why = _ocr_match_near_feature(
                runs, joined, nq, anchors, radius,
                sheet_scoped=sheet_scoped, sheet_title=sheet_title,
                sheet_useful_for=sheet_useful_for)
            via_skel_norm = None
            if not rect:
                _skres = _try_skeleton(runs + joined, s, sheet_scoped, anchors)
                if _skres:
                    rect, via_skel_norm = _skres
            if rect:
                x0, y0, x1, y1 = rect
                s["loc"] = {"x_pct": round(x0 / w * 100, 2),
                            "y_pct": round(y0 / h * 100, 2),
                            "w_pct": round(max(x1 - x0, 1) / w * 100, 2),
                            "h_pct": round(max(y1 - y0, 1) / h * 100, 2)}
                s["precision"] = "ocr"
                if via_skel_norm is not None:
                    s["located_via"] = "fraction_skeleton"
                    _skeleton_located.append(
                        {"path": path, "page": page,
                         "from": str(s.get("from") or ""),
                         "skeleton": via_skel_norm})
            else:
                s["_gate_reason"] = why
                pending.append((path, s, nq))
        # Rotated passes for LOCATES — the reads themselves already ran on
        # every page above (SEND-30); here they only locate the quotes the
        # upright pass missed.
        for k in (1, 3):
            if not pending:
                break
            if k not in rot_passes:
                continue
            rruns, rjoined = rot_passes[k]
            still = []
            for path, s, nq in pending:
                anchors = _feature_anchors_for_path(path)
                sheet_scoped = _sheet_scoped_for(path, sheet_useful_for)
                rect, why = _ocr_match_near_feature(
                    rruns, rjoined, nq, anchors, radius,
                    sheet_scoped=sheet_scoped, sheet_title=sheet_title,
                    sheet_useful_for=sheet_useful_for)
                via_skel_norm = None
                if not rect:
                    _skres = _try_skeleton(rruns + rjoined, s, sheet_scoped,
                                           anchors)
                    if _skres:
                        rect, via_skel_norm = _skres
                if rect:
                    x0, y0, x1, y1 = _map_rot_box(rect, k, w, h)
                    s["loc"] = {"x_pct": round(x0 / w * 100, 2),
                                "y_pct": round(y0 / h * 100, 2),
                                "w_pct": round(max(x1 - x0, 1) / w * 100, 2),
                                "h_pct": round(max(y1 - y0, 1) / h * 100, 2)}
                    s["precision"] = "ocr"
                    s.pop("_gate_reason", None)
                    if via_skel_norm is not None:
                        s["located_via"] = "fraction_skeleton"
                        _skeleton_located.append(
                            {"path": path, "page": page,
                             "from": str(s.get("from") or ""),
                             "skeleton": via_skel_norm})
                else:
                    s["_gate_reason"] = why or s.get("_gate_reason")
                    still.append((path, s, nq))
            pending = still
        # SEND-11 items 2+3: finalise coverage on this page and
        # scan every remaining miss for a MISREAD neighbour — an
        # OCR run one character-edit away from the quoted string.
        # The scan uses the same _del1 helper that pins the SH340-vs-
        # SH3040 glyph-drop class; _sub1 catches single-char substs
        # (32'-5 1/2" vs 33'-5 1/2"). A hit tags the miss with
        # `misread_of` and downstream nulling lands it on `_dim_misread`
        # instead of `_dim_fabricated`. Coverage rides on every miss
        # so the fabricated-vs-weak distinction can be made downstream.
        _page_chars = page_ocr_chars[page]

        def _sub1(a: str, b: str) -> bool:
            if len(a) != len(b) or len(a) < 2:
                return False
            diffs = sum(1 for x, y in zip(a, b) if x != y)
            return diffs == 1

        for path, s, nq in pending:
            misread_of = None
            for rn in _norms_seen:
                if not rn or abs(len(rn) - len(nq)) > 1:
                    continue
                if rn == nq:  # shouldn't happen (we're in miss branch) but guard
                    continue
                if _del1(nq, rn) or _del1(rn, nq) or _sub1(nq, rn):
                    misread_of = rn
                    break
            miss_rec = {"path": path, "page": page,
                        "from": str(s.get("from") or ""),
                        "rotations_checked": True,
                        "page_ocr_chars": _page_chars,
                        "reason": s.get("_gate_reason")
                                  or "quote not found on page"}
            if misread_of is not None:
                miss_rec["misread_of"] = misread_of
            misses.append(miss_rec)
            s.pop("_gate_reason", None)
    if misses:
        raw["_ocr_quote_misses"] = misses
    if _skeleton_located:
        raw["_skeleton_located"] = _skeleton_located
    if page_ocr_chars:
        # MONGO KEYS MUST BE STRINGS (regression fix 2026-08-14): this
        # per-page coverage breadcrumb is keyed by page NUMBER. Left as
        # ints it fails the run's persist write ("documents must have
        # only string keys, key was N") on ANY multi-page read — the
        # SEND-11 coverage work never crossed the persistence boundary
        # in a test, so it shipped broken. Stringify at the write edge.
        raw["_ocr_page_coverage_chars"] = {str(p): n for p, n in page_ocr_chars.items()}
    if ocr_text_by_page:
        # RULING GG: hand the per-page OCR to the worker. Whether it rides
        # on the run doc or moves to its own collection (size guard) is
        # decided at the persist boundary — never truncated silently here.
        raw["_ocr_text_by_page"] = ocr_text_by_page


def _null_unverified_quotes(raw: dict) -> None:
    """Walk `_ocr_quote_misses` and NULL every value whose evidence
    has no locating source. A locate that could not find the quote
    near its feature means the quote was fabricated — evidence-or-null
    (ruled 2026-08-08, extended 2026-08-12 send-8). The seam accounts
    for what it removed.

    SEND-9 (Howard ruled 2026-08-12 send-9 item 3): REFUSED and
    FABRICATED are DIFFERENT states and must reach the card
    differently:
      FABRICATED — the quote's normalised string does not appear in
      OCR anywhere on the page. Kill it and say so.
      REFUSED / UNVERIFIED — the string may be real but we could not
      confirm it near its feature. Value nulls on the raw so it does
      not feed money, but the value + quote + reason ride
      `_dim_unverified` so the card shows the number MARKED unverified
      instead of pretending we do not know.

    'An instrument that kills good data is a defect, not a virtue' —
    the same ruling that landed on the fraction skeleton (2026-08-09)
    applies here: showing 58'-0" as absent when it is printed and
    true is a different lie from the one we are fixing.
    """
    misses = raw.get("_ocr_quote_misses") or []
    if not misses:
        return
    ev = raw.get("_dim_evidence") or {}

    # Group miss reasons by path AND collect misread_of / coverage
    # metadata for the SEND-11 tiers. `misread_of` on any miss for a
    # path routes that path to `_dim_misread` instead of
    # `_dim_fabricated`; `page_ocr_chars` seeds fabricated evidence
    # strength (SEND-11 item 3).
    reasons_by_path: dict[str, list[str]] = {}
    misread_by_path: dict[str, str] = {}
    page_by_path: dict[str, int] = {}
    coverage_by_path: dict[str, int] = {}
    for m in misses:
        p = m.get("path")
        r = str(m.get("reason") or "").lower()
        if not p:
            continue
        reasons_by_path.setdefault(p, []).append(r)
        _mo = m.get("misread_of")
        if _mo and p not in misread_by_path:
            misread_by_path[p] = str(_mo)
        _pg = m.get("page")
        if isinstance(_pg, int) and p not in page_by_path:
            page_by_path[p] = _pg
        _cov = m.get("page_ocr_chars")
        if isinstance(_cov, int) and p not in coverage_by_path:
            coverage_by_path[p] = _cov

    # A path is fully unverified when EVERY src on its evidence has
    # no `loc` after the locator ran. A path with even one located
    # src stays — the value has partial evidence.
    fully_unverified: list[tuple[str, str]] = []  # (path, category)
    for path in reasons_by_path.keys():
        entry = ev.get(path)
        if not isinstance(entry, dict):
            continue
        srcs = entry.get("srcs") or [entry]
        if all(not (isinstance(s, dict) and s.get("loc")) for s in srcs):
            reasons = reasons_by_path[path]
            # FABRICATED base class: every refusal reason is "quote
            # not found / not present in OCR" — the string literally
            # does not appear on the page's pixels in any orientation.
            fabricated = all(
                ("not found" in r or "not present" in r) for r in reasons)
            if fabricated and path in misread_by_path:
                # SEND-11 item 2: MISREAD is a third tier — the quote
                # is absent BUT a real OCR run sits one character-edit
                # away. Diagnose as a transcription typo, not an
                # invention. Value still nulls for money.
                category = "misread"
            elif fabricated:
                category = "fabricated"
            else:
                category = "unverified"
            fully_unverified.append((path, category))

    if not fully_unverified:
        return

    def _read_value(p: str):
        """Return the value+quote pair sitting at this path BEFORE
        we null. Used to preserve the display side for UNVERIFIED
        paths (Howard's send-9: show the number marked unverified,
        never as absent)."""
        entry = ev.get(p) or {}
        srcs = entry.get("srcs") or [entry]
        quotes = [s.get("from") for s in srcs
                  if isinstance(s, dict) and s.get("from")]
        return entry.get("v"), quotes

    def _null_path(p: str) -> bool:
        """Walk raw down the dotted path and set the leaf to None.
        Handles paths like `walls.front.width_ft`,
        `walls.front.segments.<seg>.height_ft`,
        `roof_planes.<label>.wall_height_ft`, `porch.porch_width_ft`,
        `corner_heights.<i>`, and bare scalars."""
        parts = p.split(".")
        if len(parts) == 1 and parts[0] in raw:
            raw[parts[0]] = None
            ev.pop(p, None)
            return True
        if parts[0] == "walls" and len(parts) >= 3:
            label = parts[1]
            for w in (raw.get("walls") or []):
                if str(w.get("label") or "") != label:
                    continue
                if len(parts) == 3:
                    w[parts[2]] = None
                    ev.pop(p, None)
                    return True
                if len(parts) >= 5 and parts[2] == "segments":
                    seg_label = parts[3]
                    for s in (w.get("height_segments") or []):
                        if str(s.get("label") or "") == seg_label:
                            s[parts[4]] = None
                            ev.pop(p, None)
                            return True
            return False
        if parts[0] == "roof_planes" and len(parts) >= 3:
            label = parts[1]
            for pl in (raw.get("roof_planes") or []):
                if str(pl.get("label") or "") == label:
                    pl[parts[2]] = None
                    ev.pop(p, None)
                    return True
            return False
        if parts[0] == "porch" and len(parts) == 2:
            for pl in (raw.get("roof_planes") or []):
                if pl.get("is_porch"):
                    pl[parts[1]] = None
                    ev.pop(p, None)
                    return True
            return False
        if parts[0] == "gutter_runs" and len(parts) == 3:
            for g in (raw.get("gutter_runs") or []):
                if str(g.get("label") or "") == parts[1]:
                    g[parts[2]] = None
                    ev.pop(p, None)
                    return True
            return False
        if parts[0] == "corner_heights" and len(parts) == 2:
            try:
                i = int(parts[1])
                hs = raw.get("outside_corner_heights_ft")
                if isinstance(hs, list) and 0 <= i < len(hs):
                    hs[i] = None
                    ev.pop(p, None)
                    return True
            except (TypeError, ValueError):
                pass
        return False

    # SEND-11 item 3: fabricated evidence strength — a densely-read
    # page with no hit is STRONG evidence of fabrication; a barely-read
    # page (low OCR coverage — stacked fractions, poor contrast) is
    # WEAK evidence and the card must say so. Threshold is deliberately
    # generous: only ~<300 char-normalised tokens on the whole page is
    # "weak" (a typical plan sheet OCR yields thousands of chars).
    _WEAK_COVERAGE_MAX = 300

    def _strength_for(p: str) -> tuple[str, int]:
        cov = coverage_by_path.get(p, 0)
        return ("strong" if cov > _WEAK_COVERAGE_MAX else "weak"), cov

    nulled_fab: list[dict] = []
    nulled_unv: list[dict] = []
    nulled_misread: list[dict] = []
    for path, category in fully_unverified:
        value, quotes = _read_value(path)
        reason = reasons_by_path[path][-1] if reasons_by_path.get(path) else ""
        if _null_path(path):
            record = {"path": path, "value": value,
                      "quotes": quotes, "reason": reason}
            if category == "fabricated":
                strength, cov = _strength_for(path)
                record["evidence_strength"] = strength
                record["page_ocr_chars"] = cov
                nulled_fab.append(record)
            elif category == "misread":
                strength, cov = _strength_for(path)
                record["misread_of"] = misread_by_path.get(path)
                record["evidence_strength"] = strength
                record["page_ocr_chars"] = cov
                nulled_misread.append(record)
            else:
                nulled_unv.append(record)

    if nulled_fab:
        raw.setdefault("_dim_fabricated", []).extend(nulled_fab)
        seam_accounting.account(
            raw, "dims_nulled_quote_fabricated",
            [r["path"] for r in nulled_fab])
    if nulled_misread:
        raw.setdefault("_dim_misread", []).extend(nulled_misread)
        seam_accounting.account(
            raw, "dims_misread",
            [r["path"] for r in nulled_misread])
    if nulled_unv:
        raw.setdefault("_dim_unverified", []).extend(nulled_unv)
        seam_accounting.account(
            raw, "dims_nulled_quote_unverified",
            [r["path"] for r in nulled_unv])


# AXIS DECLARATION CATALOG (Howard ruled 2026-08-14 send-15 E — INVERTED
# from the enumerated `_leaf_is_vertical` predicate). Every dimension leaf
# DECLARES its axis; a leaf NOT in this catalog is UNKNOWN, never inferred
# from its name. A share touching an UNKNOWN-axis leaf fires the conflict
# rail so the next added field announces itself the first time it is
# shared — a quiet mis-classification here is invisible forever.
_LEAF_AXIS = {
    # HORIZONTAL — a span along the ground or across a surface run
    "width_ft": "H", "porch_width_ft": "H", "depth_ft": "H",
    "length_ft": "H", "lf": "H", "eave_lf": "H", "rake_lf": "H",
    "perimeter_ft": "H", "run_ft": "H", "offset_x_ft": "H",
    "outside_corner_lf": "H", "inside_corner_lf": "H",
    # VERTICAL — a height or a rise
    "height_ft": "V", "wall_height_ft": "V", "knee_wall_height_ft": "V",
    "gable_triangle_height_ft": "V", "eave_height_ft": "V",
    "plate_height_ft": "V", "rise_ft": "V", "story_height_ft": "V",
    "dormer_height_ft": "V",
}


def _leaf_axis(leaf: str) -> str:
    """VERTICAL 'V' / HORIZONTAL 'H' / UNKNOWN 'U'. Undeclared is U — the
    field name is NEVER used to infer an axis (send-15 E)."""
    return _LEAF_AXIS.get(str(leaf or ""), "U")


def _unknown_axis_leaves(paths) -> list[str]:
    """The leaves in a share whose axis is undeclared — named on the
    conflict rail so a new field announces itself the first time it is
    shared."""
    out = []
    for p in paths:
        leaf = str(p).split(".")[-1]
        if _leaf_axis(leaf) == "U":
            out.append(leaf)
    return out


def _shared_attribution_conflict(paths) -> bool:
    """PHYSICAL IMPOSSIBILITY (Howard ruled 2026-08-14 send-14 D;
    axis-declared send-15 E). The louder conflict rail fires when the
    shared consumers CANNOT both hold the value:
      * an UNKNOWN-axis leaf is present — fail loud, we cannot prove the
        share is possible (send-15 E); OR
      * a VERTICAL span (a height) shares with a HORIZONTAL span (a width
        / length / LF) — a width is not a height; OR
      * two or more VERTICAL spans on DIFFERENT named features share it —
        two walls' heights, or a wall's and a dormer's height, cannot be
        assumed equal.
    An overall HORIZONTAL dimension serving two opposing facades
    (58'-0" front + back width) is NOT impossible — it IS the house — so
    it stays on the PLAIN rail with its consumers named."""
    vertical_features = set()
    horizontal = False
    vertical = False
    for p in paths:
        parts = str(p).split(".")
        ax = _leaf_axis(parts[-1])
        if ax == "U":
            return True
        if ax == "V":
            vertical = True
            vertical_features.add(".".join(parts[:-1]))
        else:
            horizontal = True
    if vertical and horizontal:
        return True
    return len(vertical_features) >= 2


def _one_source_one_path_guard(raw: dict) -> None:
    """SHARED-SOURCE IS A LOUD FLAG, NOT A KILL (Howard ruled 2026-08-14
    send-13, AMENDING the send-10/11 demote-all).

    A quote consumed by more than one path (same page + same 'from') is a
    REAL, LOCATED quote — EXISTENCE already passed — and the sharing is
    OFTEN CORRECT: a printed 58'-0" overall genuinely IS the front width
    AND the back width; the model citing it four times is the model being
    right four times. The uncertainty is about ATTRIBUTION, which is
    WEAKER evidence than existence. Demote-all treated it as stronger and
    destroyed legitimately-shared printed dimensions; it never caught a
    real defect — the fabricated 39s die at EXISTENCE (misread_of), not
    here.

    SO: the value SURVIVES and feeds money. Every shared quote lands a
    LOUD flag on `_dim_shared_source` naming the quote, page and all
    consumers. When two paths that CANNOT independently share a value —
    the same leaf field on two different named features, e.g. two walls'
    width_ft — draw from one quote, the flag is LOUDER (attribution
    conflict): still NOT a kill, because we cannot tell which consumer is
    wrong and the standing rule is to REPORT the disagreement, not resolve
    it. Keep the ledger, keep the rail. Drop the null.
    """
    ev = raw.get("_dim_evidence") or {}
    if not ev:
        return

    # Index paths by (page, from). A quote fully identifies itself
    # only when both page AND 'from' string match — a bare number
    # can legitimately print twice on different pages and mean
    # different things.
    by_quote: dict[tuple, list[str]] = {}
    for path, entry in ev.items():
        if not isinstance(entry, dict):
            continue
        for s in (entry.get("srcs") or [entry]):
            if not isinstance(s, dict):
                continue
            page = s.get("page")
            frm = s.get("from")
            if page is None or not frm:
                continue
            by_quote.setdefault((int(page), str(frm)), []).append(path)

    shared_records: list[dict] = []
    for (page, frm), paths in by_quote.items():
        unique_paths = sorted(set(paths))
        if len(unique_paths) < 2:
            continue
        shared_records.append({
            "quote": frm, "page": page,
            "consumers": unique_paths,
            "conflicting": _shared_attribution_conflict(unique_paths),
            # The value SURVIVES and feeds money — NOTHING demoted.
            "kept": list(unique_paths),
            "demoted": [],
        })

    if shared_records:
        raw.setdefault("_dim_shared_source", []).extend(shared_records)


def _ocr_verify_marks(raw: dict, image_payloads: list,
                      runs_for_page=None) -> None:
    """MARKS FACE THE LOCATOR TOO (Howard ruled 2026-08-08/09 — 'an E1
    exterior entry appears that the sheet does not hold; G2 carries
    9'-2" where the sheet prints 9'-0"'). Every schedule row's quotes —
    the mark letter, the printed size, the product code — are searched
    on the row's own schedule sheets, upright and both rotations.
    A row NONE of whose quotes locate is a fabrication: DROPPED,
    accounted, loud. A located row whose printed size cannot be found
    has that quote KILLED — dims null, the parse of a fabricated quote
    never reaches the takeoff. OCR supplies existence, never value
    (the hard separation stands); an OCR engine failure changes
    nothing — rows stand."""
    rows = [(k, r) for k in ("windows", "doors")
            for r in (raw.get(k) or []) if isinstance(r, dict)]
    if not rows or not image_payloads:
        return
    n = len(image_payloads)
    if runs_for_page is None:
        import numpy as np
        _cache: dict[int, object] = {}

        def runs_for_page(page: int):
            if page not in _cache:
                try:
                    with Image.open(io.BytesIO(image_payloads[page - 1])) as im:
                        arr = np.array(im.convert("RGB"))
                    up = _ocr_runs(arr)
                    boxed = [(r[0], r[2]) for r in up + _join_adjacent_runs(up)]
                    norms = [b[0] for b in boxed]
                    for k_rot in (1, 3):
                        rr = _ocr_runs(np.rot90(arr, k_rot))
                        norms.extend(r[0] for r in rr + _join_adjacent_runs(rr))
                    _cache[page] = {"norms": norms, "boxed": boxed}
                except Exception:
                    logger.exception(
                        "[ai-blueprint] mark OCR failed on page %s — rows stand", page)
                    _cache[page] = None
            return _cache[page]

    def _page_data(page):
        got = runs_for_page(page)
        if got is None:
            return None
        if isinstance(got, dict):
            return got
        return {"norms": list(got), "boxed": []}

    def _pages_for(r):
        pages = set()
        for p in (r.get("schedule_pages") or []):
            try:
                pages.add(int(p))
            except (TypeError, ValueError):
                continue
        cbp = r.get("count_by_page")
        if isinstance(cbp, dict):
            for p in cbp:
                try:
                    pages.add(int(p))
                except (TypeError, ValueError):
                    continue
        pages = sorted(p for p in pages if 1 <= p <= n)
        return pages or list(range(1, n + 1))

    def _found(norms, nq, mark_mode=False, relax_cap=False):
        for run in norms:
            if run == nq:
                return True
            if mark_mode:
                if run.startswith(nq):
                    return True
            elif len(nq) >= 3 and nq in run and (
                    relax_cap or len(run) <= len(nq) + 6):
                return True
        return False

    def _quote_variants(q: str) -> list[str]:
        """FRACTION SKELETON (2026-08-09, from the live re-kill): the OCR
        engine cannot read the stacked ½ glyphs at all — joining cannot
        restore glyphs never read. A size quote also tries its
        fraction-stripped skeleton (and the x-less digit skeleton); a
        skeleton match LOCATES the quote and is NAMED as such. The
        skeleton still kills a wrong quote — 5'-0 does not match a
        printed 5'-5."""
        out = [q]
        stripped = re.sub(r"\s*\d/\d\s*\"?", "", q)
        if stripped != q:
            out.append(stripped)
            out.append(re.sub(r"[xX\u00d7]", " ", stripped))
        return out

    all_sched_pages: set[int] = set()
    read_marks: set[str] = set()
    read_codes: set[str] = set()
    for _, r in rows:
        all_sched_pages.update(_pages_for(r) if (r.get("schedule_pages")
                                                 or r.get("count_by_page")) else [])
        mk = _ocr_norm(r.get("id"))
        cd = _ocr_norm(r.get("product_code"))
        if mk:
            read_marks.add(mk)
        if cd:
            read_codes.add(cd)
    read_tokens = read_marks | read_codes

    # MARK-MERGE DETECTION (Howard ruled 2026-08-09 send 4 — "three of
    # your findings are one defect"): the model collapses sibling rows
    # that share a code prefix, copying the survivor's trailing cells
    # (C wore A's code, A's size, and once A's count; B and D before it).
    # Two marks NEVER share a product code on a real schedule — sharers
    # are SUSPECTED MERGES: flagged loud, and suspicion revokes the
    # region-relaxed matching leniency below (a merged row's quote is
    # its sibling's print — leniency would resurrect the wrong dims).
    _by_code: dict[str, list[str]] = {}
    for kind, r in rows:
        cd = _ocr_norm(r.get("product_code"))
        mk = str(r.get("id") or "").strip().upper()
        if cd and mk:
            _by_code.setdefault(cd, [])
            if mk not in _by_code[cd]:
                _by_code[cd].append(mk)
    merge_suspects = {cd: mks for cd, mks in _by_code.items() if len(mks) > 1}
    suspected_marks = {m for mks in merge_suspects.values() for m in mks}

    # TABLE REGIONS (PROXIMITY RULE, ruled 2026-08-09 send 4 — "class
    # over instance"): a schedule row's locating match must sit inside
    # that schedule's table region. Anchored by the read's own located
    # tokens; <2 anchors = no region = page-wide fallback, NAMED
    # (upright-only coverage — schedule text is upright; a partial
    # instrument that names its own blind spot beats none).
    _regions: dict[int, tuple] = {}

    def _region_for(page):
        if page not in _regions:
            got = _page_data(page)
            reg = None
            if got and got["boxed"]:
                anchors = [b for nrm, b in got["boxed"] if nrm in read_tokens]
                if len(anchors) >= 2:
                    ax0 = min(b[0] for b in anchors)
                    ay0 = min(b[1] for b in anchors)
                    ax1 = max(b[2] for b in anchors)
                    ay1 = max(b[3] for b in anchors)
                    heights = sorted(b[3] - b[1] for b in anchors)
                    row_h = max(1, heights[len(heights) // 2])
                    reg = (ax0 - 0.5 * max(ax1 - ax0, 1) - 4 * row_h,
                           ay0 - (ay1 - ay0) - 10 * row_h,
                           ax1 + 0.5 * max(ax1 - ax0, 1) + 4 * row_h,
                           ay1 + (ay1 - ay0) + 10 * row_h)
            _regions[page] = reg
        return _regions[page]

    def _in_region(b, reg):
        return (reg[0] <= b[0] and b[2] <= reg[2]
                and reg[1] <= b[1] and b[3] <= reg[3])

    def _overlaps_region(b, reg):
        # Verification pool membership: a joined row run extends past
        # the anchor-derived region — intersection is the right test.
        # (Omission CANDIDATES stay fully-contained: short tokens.)
        return not (b[2] < reg[0] or b[0] > reg[2]
                    or b[3] < reg[1] or b[1] > reg[3])

    dropped, misses, interior_sig, skeletons = [], [], [], []
    for kind, r in rows:
        quotes = [("id", str(r.get("id") or "").strip(), True),
                  ("printed_size", str(r.get("printed_size") or "").strip(), False),
                  ("product_code", str(r.get("product_code") or "").strip(), False)]
        checks = {}
        pages = _pages_for(r)
        norms_all: list[str] = []
        ocr_ok = False
        gated = False
        for p in pages:
            got = _page_data(p)
            if got is None:
                continue
            ocr_ok = True
            reg = _region_for(p)
            if reg is not None:
                # PROXIMITY: inside the table region only (upright).
                norms_all.extend(nrm for nrm, b in got["boxed"]
                                 if _overlaps_region(b, reg))
                gated = True
            else:
                norms_all.extend(got["norms"])
        if not ocr_ok:
            continue  # engine failure is never evidence of fabrication
        mark = str(r.get("id") or "").strip() or "?"
        # Region-gated matching may relax the containment cap (the region
        # is the constraint; joined schedule rows run long) — EXCEPT for
        # suspected merge rows, whose quotes are their sibling's print.
        relax = gated and mark.upper() not in suspected_marks
        for field, q, mm in quotes:
            nq = _ocr_norm(q)
            if not nq:
                continue
            ok = _found(norms_all, nq, mark_mode=mm, relax_cap=relax)
            skeleton = False
            if not ok and not mm:
                for v in _quote_variants(q)[1:]:
                    nv = _ocr_norm(v)
                    if len(nv) >= 3 and _found(norms_all, nv,
                                               relax_cap=relax):
                        ok = True
                        skeleton = True
                        skeletons.append({"kind": kind,
                                          "mark": str(r.get("id") or "?"),
                                          "field": field, "from": q})
                        break
            checks[field] = (ok, q, nq)
        if not checks:
            continue
        # SHORT-QUOTE VETO (Howard ruled 2026-08-09): a quote of two
        # characters or less carries NO SURVIVAL WEIGHT — E1 survived its
        # own fabrication because "3'-0\"" → "30" trivially matched a
        # dimension run elsewhere on the sheet. The mark (the row's
        # identity, matched exact-or-prefix) keeps its weight.
        survives = any(ok for field, (ok, q, nq) in checks.items()
                       if ok and (field == "id" or len(nq) >= 3))
        if not survives:
            dropped.append({"kind": kind, "mark": mark,
                            "quotes": [q for _, q, _n in checks.values()],
                            "pages": pages, "rotations_checked": True})
            r["_drop_not_located"] = True
            continue
        # INTERIOR SIGNAL BY MACHINE (Howard ruled 2026-08-09): the
        # product-code column is read from the pixels — a schedule line
        # carrying the row's mark AND an interior marker is INTERIOR,
        # regardless of the model's own exterior label.
        if kind == "doors":
            mknorm = _ocr_norm(r.get("id"))
            if mknorm:
                for p in pages:
                    got = _page_data(p)
                    if not got:
                        continue
                    hit = next(
                        (run for run in got["norms"]
                         if run.startswith(mknorm)
                         and any(m in run for m in _INTERIOR_MARKERS)), None)
                    if hit:
                        interior_sig.append({
                            "mark": mark, "page": p,
                            "marker": next(m for m in _INTERIOR_MARKERS
                                           if m in hit)})
                        r["_drop_interior_signal"] = True
                        break
            if r.get("_drop_interior_signal"):
                continue
        for field, (ok, q, nq) in checks.items():
            if ok:
                continue
            misses.append({"kind": kind, "mark": mark, "field": field,
                           "from": q, "pages": pages,
                           "rotations_checked": True})
            if field == "printed_size":
                # The quote is killed — its parse never reaches the
                # takeoff; the claimed string survives in the register.
                r["printed_size_not_located"] = q
                r["printed_size"] = ""
                r["width_in"] = None
                r["height_in"] = None

    # OMISSION CHECK (Howard ruled 2026-08-09): the evidence layer was
    # ONE-DIRECTIONAL — it caught fabrication, never omission ("E2 DOES
    # print and is absent from the read"). Schedule-code and door-mark
    # tokens found INSIDE the schedule's table region (anchored by the
    # rows we did read) with no counterpart in the read are OMISSIONS —
    # loud, named, resolved by a human. Fewer than two anchors on a page
    # leaves the region undecidable — skipped, never guessed.
    omissions: list[dict] = []
    # Door-mark omission candidates are restricted to the initial letters
    # the read's own door marks carry (E, G on a sheet reading E*/G*) —
    # grid bubbles and section tags (RR1, X17, K40) are not door rows.
    # NAMED LIMIT: a door family whose letter never appears in the read
    # at all is beyond this instrument — the human census owns it.
    _door_letters = {m[0] for m in read_marks if _DOOR_MARK_RE.match(m)}
    for p in sorted(all_sched_pages):
        got = _page_data(p)
        if not got or not got["boxed"]:
            continue
        reg = _region_for(p)
        if reg is None:
            continue
        seen: set[str] = set()
        for nrm, b in got["boxed"]:
            if not _in_region(b, reg):
                continue
            if not (_SCHED_CODE_RE.match(nrm)
                    or (_DOOR_MARK_RE.match(nrm)
                        and nrm[0] in _door_letters)):
                continue
            if nrm in seen or nrm in read_tokens:
                continue
            if any(_del1(nrm, t) or _del1(t, nrm) for t in read_tokens):
                continue  # one-glyph OCR drift of a row we DID read
            seen.add(nrm)
            omissions.append({"page": p, "token": nrm})

    # MARK-MERGE register: name the sharers, and when an omitted code
    # sits one glyph from the shared one, name the likely true row
    # ("C duplicates A's SH3050 while SH3056 prints unread").
    if merge_suspects:
        def _sub1(a, b):
            return (len(a) == len(b)
                    and sum(1 for x, y in zip(a, b) if x != y) == 1)
        reg_ent = []
        for cd, mks in merge_suspects.items():
            likely = [o["token"] for o in omissions
                      if _sub1(o["token"], cd) or _del1(cd, o["token"])
                      or _del1(o["token"], cd)]
            reg_ent.append({"code": cd, "marks": mks,
                            "likely_unread": likely})
        raw["_mark_merge_suspected"] = reg_ent

    # CALLOUT CENSUS (Howard ruled 2026-08-09 send 4): a real detector
    # behind "one profile — but this house has gables". Profile keywords
    # printed on the ELEVATION sheets with no counterpart family in the
    # read flag LOUD. No elevation sheets identified = no census — named
    # by absence, never guessed.
    try:
        from profile_callouts import classify_profile
        elev_pages = sorted({int(s.get("page")) for s in
                             (raw.get("sheets_identified") or [])
                             if isinstance(s, dict)
                             and str(s.get("useful_for")) == "elevation"
                             and 1 <= int(s.get("page") or 0) <= n})
        if elev_pages:
            have: set[str] = set()
            for w in raw.get("walls") or []:
                if not isinstance(w, dict):
                    continue
                for f in ("wall_body_profile_callout",
                          "gable_profile_callout",
                          "dormer_profile_callout"):
                    fam = classify_profile(w.get(f))
                    if fam and fam != "unknown":
                        have.add(fam)
                for a in (w.get("accent_profiles") or []):
                    if isinstance(a, dict):
                        fam = classify_profile(a.get("profile_callout"))
                        if fam and fam != "unknown":
                            have.add(fam)
            _KEYWORDS = (("SHAKE", "shake"),
                         ("BATTEN", "board_and_batten"),
                         ("DUTCHLAP", "dutch_lap"),
                         ("SCALLOP", "scallop"))
            cal: list[dict] = []
            flagged: set[str] = set()
            for p in elev_pages:
                got = _page_data(p)
                if not got:
                    continue
                for nrm in got["norms"]:
                    for kw, fam in _KEYWORDS:
                        if kw in nrm and fam not in have \
                                and fam not in flagged:
                            flagged.add(fam)
                            cal.append({"family": fam, "page": p,
                                        "run": nrm[:40]})
            if cal:
                raw["_callout_omissions"] = cal
    except Exception:
        logger.exception("[ai-blueprint] callout census failed — no census")

    for k in ("windows", "doors"):
        arr = raw.get(k)
        if isinstance(arr, list):
            kept = [r for r in arr
                    if not (isinstance(r, dict)
                            and (r.get("_drop_not_located")
                                 or r.get("_drop_interior_signal")))]
            if len(kept) != len(arr):
                raw[k] = kept
    if dropped:
        raw["_marks_dropped_not_located"] = dropped
        seam_accounting.account(
            raw, "marks_dropped_not_located",
            [f"{d['kind']}:{d['mark']}" for d in dropped])
    if interior_sig:
        raw["_interior_signal_dropped"] = interior_sig
        seam_accounting.account(
            raw, "interior_signal_dropped",
            [f"doors:{d['mark']}" for d in interior_sig])
    if omissions:
        raw["_schedule_omissions"] = omissions
    if skeletons:
        raw["_skeleton_matches"] = skeletons
    if misses:
        raw["_mark_quote_misses"] = misses
        _nulled_sizes = [f"{m['kind']}:{m['mark']}" for m in misses
                         if m["field"] == "printed_size"]
        if _nulled_sizes:
            seam_accounting.account(raw, "mark_size_quotes_nulled",
                                    _nulled_sizes)

    # COUNT-CELL LOCATOR (Howard ruled 2026-08-11 send-3 item d):
    # "A COUNT-CELL QUOTE FACES THE LOCATOR LIKE A SIZE QUOTE. Located,
    # or killed and the count nulled with the claim preserved."
    # For every row carrying count_by_page {sheet: n}, we require the
    # claimed integer to appear as an isolated numeric token inside the
    # mark's row-band on that page. A misread cell — the exact class
    # that landed 9 on Boni mark C when the print says 5 — cannot ride
    # through the count-column seam because the seam trusts the read.
    # The locator settles the disagreement by the print.
    #
    # Refuse-to-guess: unless the mark's location AND at least one
    # boxed token band on the page are found, the check ABSTAINS on
    # that page (no null) — the count survives on the seam. A partial
    # instrument that names its blind spot beats one that hallucinates.
    count_cell_misses: list[dict] = []
    for kind, r in rows:
        cbp = r.get("count_by_page")
        if not isinstance(cbp, dict) or not cbp:
            continue
        if r.get("_drop_not_located") or r.get("_drop_interior_signal"):
            continue
        mark = str(r.get("id") or "").strip()
        mknorm = _ocr_norm(mark)
        if not mknorm:
            continue
        surviving: dict[str, int] = {}
        for page_s, claimed in list(cbp.items()):
            try:
                page = int(page_s)
                claim = int(claimed)
            except (TypeError, ValueError):
                continue
            if claim <= 0:
                # A zero count is not a claim — leave the row alone.
                surviving[str(page)] = claim
                continue
            got = _page_data(page)
            if not got or not got.get("boxed"):
                # Abstain: no boxed data on this page, cannot check.
                surviving[str(page)] = claim
                continue
            # Locate the mark box on this page (exact-or-prefix match,
            # same rule the mark_mode locator uses).
            mark_box = next(
                (b for nrm, b in got["boxed"]
                 if nrm == mknorm or nrm.startswith(mknorm)), None)
            if mark_box is None:
                # Abstain: mark itself not on this page → cannot check.
                surviving[str(page)] = claim
                continue
            # Row-band: y-center of the mark ± half its height, generous
            # by a row's worth on each side (schedule rows can be
            # slightly staggered vertically vs the mark cell). x >= mark
            # right edge (count column sits to the right of the mark).
            mx0, my0, mx1, my1 = mark_box
            row_h = max(4.0, my1 - my0)
            y_band = (my0 - 0.6 * row_h, my1 + 0.6 * row_h)
            claim_str = str(claim)
            # An isolated integer token in the row-band, past the mark
            # column. We look at every boxed token on the page and take
            # the ones whose center-y sits inside the band and whose
            # left edge sits past the mark's right edge.
            hit = False
            for nrm, b in got["boxed"]:
                cy = 0.5 * (b[1] + b[3])
                if not (y_band[0] <= cy <= y_band[1]):
                    continue
                if b[0] <= mx1:  # inside or left of the mark column
                    continue
                # nrm is OCR-normalized already; a lone integer token
                # matches when the norm equals the claim string or when
                # it prefixes/contains it in the count-column context.
                # Isolate-or-equal keeps "19" from matching "9".
                if nrm == claim_str:
                    hit = True
                    break
            if hit:
                surviving[str(page)] = claim
            else:
                count_cell_misses.append({
                    "kind": kind, "mark": mark, "page": page,
                    "claimed": claim,
                    "reason": ("no isolated integer token equal to the "
                               f"claimed count '{claim_str}' in the row-"
                               f"band right of the mark on page {page}"),
                })
        if surviving != cbp:
            # The claim survives in a separate register; the working
            # count column carries only the survivors.
            r["count_by_page_not_located"] = {
                k: v for k, v in cbp.items() if k not in surviving
            }
            r["count_by_page"] = surviving
            # qty follows the surviving count column (or is nulled
            # entirely when nothing survives — the row still stands,
            # just without a count claim).
            new_qty = sum(surviving.values())
            if new_qty > 0:
                r["qty"] = new_qty
            else:
                r["qty"] = None
    if count_cell_misses:
        raw["_count_cell_not_located"] = count_cell_misses
        seam_accounting.account(
            raw, "mark_count_cells_nulled",
            [f"{m['kind']}:{m['mark']}:p{m['page']}"
             for m in count_cell_misses])

    # SEND-114 — THE SCHEDULE ROW PARSER (Howard ruled 2026-08-14).
    # Rows, not strings: a count cell that will not OCR can still be
    # located BY ITS ROW. Where a count cannot be established from its
    # row it REFUSES naming the mark — never a collapse to 1 (a floor
    # that looks like a count produced the 4; honoring unverified
    # claims produced the 20). Doors and windows stay separate;
    # exterior door rows the model missed (the E3 class) are recovered
    # from the printed row itself.
    try:
        from schedule_read import read_schedule_counts
        read_schedule_counts(raw)
        if raw.get("_schedule_row_counts"):
            seam_accounting.account(
                raw, "schedule_row_counts",
                [f"{c['kind']}:{c['mark']}:p{c['page']}={c['count']}"
                 for c in raw["_schedule_row_counts"]])
        if raw.get("_schedule_count_unread"):
            seam_accounting.account(
                raw, "schedule_count_unread",
                [f"{u['kind']}:{u['mark']}"
                 for u in raw["_schedule_count_unread"]])
        if raw.get("_schedule_rows_recovered"):
            seam_accounting.account(
                raw, "schedule_rows_recovered",
                [f"{m['mark']}:p{m['page']}"
                 for m in raw["_schedule_rows_recovered"]])
    except Exception:
        logger.exception("[schedule-read] row parser failed — the read "
                         "stands unmodified")


def compute_read_stability(prev_raw: dict, raw: dict) -> dict:
    """DETERMINISM GATE (Howard ruled 2026-08-08): REPORTS STABILITY,
    NEVER CORRECTNESS. Greedy sampling makes an error repeatable, not
    right — on the Boni house this gate would flag the corner count
    (10 → 6 at temperature 0) while passing a height that could still be
    wrong. Counts must match EXACTLY; dims agree within tolerance
    (0.5 or 2%). Under evidence-or-null the gate separates STABLY READ
    from STABLY ABSTAINED: two nulls agree the drawing was not read
    there — that is NOT agreement on a number and never prints as one;
    a value meeting a null is a DISAGREEMENT. The card wording never
    lets agreement print as a correctness claim."""
    def _f(d, k):
        v = d.get(k)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _wins(d):
        return sum(int(w.get("qty") or 1) for w in (d.get("windows") or [])
                   if isinstance(w, dict))

    def _doors(d):
        return sum(int(x.get("qty") or 1) for x in (d.get("doors") or [])
                   if isinstance(x, dict))

    def _gables(d):
        return sum(int(p.get("gable_ends") or 0)
                   for p in (d.get("roof_planes") or []) if isinstance(p, dict))

    counts = []
    for name, fn in (
        ("outside corners", lambda d: int(d.get("outside_corner_count") or 0)),
        ("inside corners", lambda d: int(d.get("inside_corner_count") or 0)),
        ("windows", _wins),
        ("exterior doors", _doors),
        ("roof planes", lambda d: len(d.get("roof_planes") or [])),
        ("gable ends", _gables),
        ("gutter runs", lambda d: len(d.get("gutter_runs") or [])),
    ):
        a, b = fn(prev_raw), fn(raw)
        counts.append({"name": name, "a": a, "b": b, "match": a == b})

    def _tol_ok(a, b):
        tol = max(0.5, 0.02 * max(abs(a), abs(b)))
        return abs(a - b) <= tol

    dims = []
    abstained: list[str] = []
    for key, name in (("eaves_lf", "eaves LF"), ("rakes_lf", "rakes LF"),
                      ("starter_lf", "starter LF"),
                      ("outside_corner_lf", "corner LF"),
                      ("avg_wall_height_ft", "avg wall height ft")):
        a, b = _f(prev_raw, key), _f(raw, key)
        if a is None and b is None:
            abstained.append(name)
            continue
        dims.append({"name": name, "a": a, "b": b,
                     "within": (a is not None and b is not None
                                and _tol_ok(a, b))})

    # Evidenced dims — the per-path register where the guesses used to
    # live. A path evidenced in one read and abstained in the other is a
    # disagreement, never a silent drop. COMPARABILITY (live-fire finding
    # 2026-08-08): a run from BEFORE the evidence register carries no
    # per-path values at all — comparing against it would print dozens of
    # false "disagreements" that are really schema vintage. That gap is
    # NAMED, never miscounted as instability.
    ev_a = prev_raw.get("_dim_evidence") or {}
    ev_b = raw.get("_dim_evidence") or {}
    un_a_l = (prev_raw.get("_dim_unread") or []) + (prev_raw.get("_nulled_no_evidence") or [])
    un_b_l = (raw.get("_dim_unread") or []) + (raw.get("_nulled_no_evidence") or [])
    prev_has_register = bool(ev_a or un_a_l)
    curr_has_register = bool(ev_b or un_b_l)
    evidenced = []
    if prev_has_register and curr_has_register:
        for path in sorted(set(ev_a) | set(ev_b)):
            a = (ev_a.get(path) or {}).get("v") if isinstance(ev_a.get(path), dict) else None
            b = (ev_b.get(path) or {}).get("v") if isinstance(ev_b.get(path), dict) else None
            if a is None and b is None:
                continue
            evidenced.append({"name": path, "a": a, "b": b,
                              "within": (a is not None and b is not None
                                         and _tol_ok(float(a), float(b)))})
        # Stably abstained — both reads returned null on the same path.
        abstained += sorted((set(un_a_l) & set(un_b_l)) - set(ev_a) - set(ev_b))

    return {"counts": counts, "dims": dims, "evidenced": evidenced,
            "abstained": abstained,
            "evidenced_not_comparable": not (prev_has_register and curr_has_register),
            "stable": (all(c["match"] for c in counts)
                       and all(d["within"] for d in dims)
                       and all(e["within"] for e in evidenced))}


def _read_footprint_sqft(raw: dict) -> float:
    """CATEGORY DISCIPLINE (Howard's correction 3, ruled 2026-08-08): the
    wing check compared 2351 — TOTAL FINISHED LIVING, storeys summed —
    against a wall rectangle. Labelled quantities read as labelled:
    footprint = first floor + attached garage when the area table holds
    them; the flat footprint field only otherwise."""
    at = raw.get("area_table") or {}

    def _f(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0
    ff = _f(at.get("first_floor_sqft"))
    if ff > 0:
        return ff + _f(at.get("garage_sqft"))
    return _f(raw.get("footprint_area_sqft"))


def _opposing_pairs(widths: dict) -> tuple[float, float, list]:
    """WING FLAG GUARD (Howard ruled 2026-08-10 send 2): opposing walls
    that disagree FLAG LOUD, and the box-model rect takes the SHORTER of
    the pair. A max() here could inflate the rect and silently SUPPRESS
    the wing detector — a number too big costs money; a body that is
    missing costs the job."""
    disags: list = []

    def _side(a_key: str, b_key: str) -> float:
        a = float(widths.get(a_key) or 0)
        b = float(widths.get(b_key) or 0)
        if a > 0 and b > 0 and abs(a - b) > max(1.0, 0.02 * max(a, b)):
            disags.append((f"{a_key}/{b_key}", a, b))
            return min(a, b)
        return max(a, b)

    return _side("front", "back"), _side("left", "right"), disags


def check_read_consistency(raw: dict) -> list[dict]:
    """INTERNAL CONSISTENCY CHECKER (Howard ruled 2026-08-07): the card
    arrives already clean — contradictions the app can catch itself never
    reach the contractor's grade. A CHECKER TESTS CONSISTENCY, NOT
    CORRECTNESS (Howard's condition, same as temperature=0 one layer up):
    every flag NAMES both disagreeing sources and resolves toward
    NEITHER — a taped or contractor-entered height outranks every read.
    Compares numbers against OTHER FACTS in the same read, never a target.
    Codes: corner_taller_than_wall · corner_lf_not_sum ·
    gable_census_mismatch · box_model · footprint_missing (absence named)
    · run_exceeds_facade · wall_segments_mismatch · porch_run_vs_width ·
    porch_dims_vs_area · window_size_parse_mismatch."""
    flags: list[dict] = []
    if not isinstance(raw, dict):
        return flags
    walls = [w for w in (raw.get("walls") or []) if isinstance(w, dict)]

    def _f(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    wall_heights = [_f(w.get("height_ft")) for w in walls if _f(w.get("height_ft")) > 0]
    for w in walls:
        for s in (w.get("height_segments") or []):
            if isinstance(s, dict) and _f(s.get("height_ft")) > 0:
                wall_heights.append(_f(s.get("height_ft")))
    tallest = max(wall_heights) if wall_heights else 0.0

    # OPENINGS SUM vs WALL WIDTH (Howard ruled 2026-08-12 send-10
    # item 2): pure arithmetic. The sum of opening widths on a wall
    # may not exceed that wall's printed width. Free, structural,
    # would have caught the Boni case (two garage doors 16'+9' = 25
    # feet placed on a 23'-8 1/2" wall — cannot fit; belong on the
    # 33'-0" side wall). Depends on numbers we already hold.
    windows = raw.get("windows") or []
    doors = raw.get("doors") or []
    for w in walls:
        lbl = str(w.get("label") or "").strip().lower()
        wall_w_ft = _f(w.get("width_ft"))
        if wall_w_ft <= 0 or lbl not in {"front", "back", "left", "right"}:
            continue
        placed = []
        for src, kind in ((windows, "window"), (doors, "door")):
            for o in src:
                if not isinstance(o, dict):
                    continue
                elev = str(o.get("elevation") or "").strip().lower()
                if elev != lbl:
                    continue
                try:
                    qty = max(1, int(o.get("qty") or 1))
                except (TypeError, ValueError):
                    qty = 1
                width_in = _f(o.get("width_in"))
                if width_in <= 0:
                    continue
                placed.append({
                    "kind": kind,
                    "code": o.get("mark") or o.get("code") or "",
                    "type": o.get("type_hint") or "",
                    "qty": qty,
                    "width_in": width_in,
                })
        if not placed:
            continue
        sum_ft = sum(p["qty"] * p["width_in"] / 12.0 for p in placed)
        if sum_ft > wall_w_ft + 0.01:
            flags.append({
                "code": "openings_exceed_wall_width", "level": "loud",
                "vars": {
                    "wall": lbl,
                    "wall_width_ft": round(wall_w_ft, 3),
                    "openings_sum_ft": round(sum_ft, 3),
                    "excess_ft": round(sum_ft - wall_w_ft, 3),
                    "openings": ", ".join(
                        f"{p['code'] or p['type']}×{p['qty']}={p['width_in']:g}\""
                        for p in placed),
                }})


    for w in walls:
        segs = [s for s in (w.get("height_segments") or []) if isinstance(s, dict)]
        undim_segs = [s for s in segs
                      if _f(s.get("width_ft")) > 0 and _f(s.get("height_ft")) <= 0]
        if undim_segs:
            flags.append({
                "code": "wall_segment_undimensioned", "level": "warn",
                "vars": {"label": str(w.get("label") or "?"),
                         "section": str(undim_segs[0].get("label") or "?"),
                         "n": len(undim_segs)}})
            continue
        sw = sum(_f(s.get("width_ft")) for s in segs
                 if _f(s.get("width_ft")) > 0 and _f(s.get("height_ft")) > 0)
        ww = _f(w.get("width_ft"))
        if segs and sw > 0 and ww > 0 and abs(sw - ww) > max(0.5, 0.02 * ww):
            flags.append({
                "code": "wall_segments_mismatch", "level": "loud",
                "vars": {"label": str(w.get("label") or "?"),
                         "sum": f"{sw:g}", "width": f"{ww:g}"}})

    heights = [h for h in (raw.get("outside_corner_heights_ft") or [])
               if isinstance(h, (int, float)) and h and h > 0]
    if heights and tallest > 0:
        over = [h for h in heights if h > tallest + 0.5]
        if over:
            flags.append({
                "code": "corner_taller_than_wall", "level": "loud",
                "vars": {"h": f"{max(over):g}", "wall": f"{tallest:g}",
                         "n": len(over)}})

    oclf = _f(raw.get("outside_corner_lf"))
    if heights and oclf > 0:
        hsum = sum(heights)
        if abs(oclf - hsum) > max(2.0, 0.05 * oclf):
            flags.append({
                "code": "corner_lf_not_sum", "level": "loud",
                "vars": {"lf": f"{oclf:g}", "sum": f"{hsum:g}"}})

    planes = [p for p in (raw.get("roof_planes") or []) if isinstance(p, dict)]
    plane_gables = sum(int(p.get("gable_ends") or 0) for p in planes)
    wall_gables = sum(1 for w in walls if _f(w.get("gable_triangle_height_ft")) > 0)
    # ORPHAN GABLE GUARD (Howard ruled 2026-08-11 send-6): an orphan
    # gable end is NEVER distributed onto an unrelated wall. The wing
    # plane's ends attribute ONLY via its own `gable_end_faces` evidence
    # (extraction fix). No faces → orphan → LOUD flag, unattributed.
    from gable_attribution import attribute_secondary_gables
    _attrib = attribute_secondary_gables(walls, planes)
    wall_gables_total = _attrib["wall_gables_attributed"]
    _orphans = _attrib.get("orphans") or []
    _orphan_count = sum(int(o.get("count") or 0) for o in _orphans)
    if planes and walls and (
            plane_gables != wall_gables_total or _orphan_count > 0):
        _vars = {"planes": plane_gables, "walls": wall_gables_total,
                 "primary": wall_gables,
                 "secondary": wall_gables_total - wall_gables}
        if _orphan_count > 0:
            _vars["orphans"] = _orphan_count
            _vars["orphan_planes"] = ", ".join(
                f"{o.get('plane')}×{o.get('count')}" for o in _orphans)
        flags.append({
            "code": "gable_census_mismatch", "level": "loud",
            "vars": _vars})

    by_label = {str(w.get("label") or "").lower(): w for w in walls}
    fb, lr = by_label.get("front"), by_label.get("left")
    bk, rt = by_label.get("back"), by_label.get("right")
    mirrored = (fb and bk and lr and rt
                and _f(fb.get("width_ft")) == _f(bk.get("width_ft"))
                and _f(fb.get("height_ft")) == _f(bk.get("height_ft"))
                and _f(lr.get("width_ft")) == _f(rt.get("width_ft"))
                and _f(lr.get("height_ft")) == _f(rt.get("height_ft")))
    if mirrored:
        fp = _read_footprint_sqft(raw)
        rect = _f(fb.get("width_ft")) * _f(lr.get("width_ft"))
        if fp and rect > 0 and fp > rect * 1.02:
            flags.append({"code": "box_model", "level": "loud", "vars": {}})
    # ABSENCE IS NAMED (Howard's grade 2026-08-07: "the footprint check
    # is absent from this card — why did it stop firing?"): no printed
    # footprint captured → the wing check CANNOT run, and the card says so.
    if walls and not _read_footprint_sqft(raw):
        flags.append({"code": "footprint_missing", "level": "warn", "vars": {}})
    # CATEGORY SELF-CATCH (ruled 2026-08-08): a footprint equal to the
    # TOTAL FINISHED figure while a second storey exists read storeys
    # summed as ground area.
    at = raw.get("area_table") or {}
    tf, sf = _f(at.get("total_finished_sqft")), _f(at.get("second_floor_sqft"))
    fp_flat = _f(raw.get("footprint_area_sqft"))
    if fp_flat > 0 and tf > 0 and sf > 0 and abs(fp_flat - tf) < 1.0:
        flags.append({"code": "footprint_is_total_finished", "level": "loud",
                      "vars": {"fp": f"{fp_flat:g}", "tf": f"{tf:g}"}})

    # PORCH SELF-CONSISTENCY (ruled 2026-08-07): a porch's gutter run
    # must equal its printed width; stated dims must reproduce the
    # stated area (16×6 = 96 against a 99 table is a named delta).
    porch_w = porch_d = porch_sqft = 0.0
    for p in (raw.get("roof_planes") or []):
        if isinstance(p, dict) and p.get("is_porch"):
            porch_w = _f(p.get("porch_width_ft"))
            porch_d = _f(p.get("porch_depth_ft"))
            porch_sqft = _f(p.get("porch_ceiling_sqft"))
            break
    if porch_w > 0:
        for r in (raw.get("gutter_runs") or []):
            if isinstance(r, dict) and "porch" in str(r.get("label") or "").lower():
                if abs(_f(r.get("lf")) - porch_w) > 1.0:
                    flags.append({
                        "code": "porch_run_vs_width", "level": "loud",
                        "vars": {"run": f"{_f(r.get('lf')):g}",
                                 "width": f"{porch_w:g}"}})
                break
    if porch_w > 0 and porch_d > 0 and porch_sqft > 0:
        stated = porch_w * porch_d
        if abs(stated - porch_sqft) > 0.05 * porch_sqft:
            flags.append({
                "code": "porch_dims_vs_area", "level": "loud",
                "vars": {"w": f"{porch_w:g}", "d": f"{porch_d:g}",
                         "product": f"{stated:g}", "area": f"{porch_sqft:g}"}})

    # PRINTED-SIZE TRANSCRIPTION (window mark B class): the verbatim
    # schedule string must reproduce the numeric parse the read carries.
    for win in (raw.get("windows") or []):
        if not isinstance(win, dict):
            continue
        parsed = _parse_printed_size(win.get("printed_size"))
        if not parsed:
            continue
        pw, ph = parsed
        if abs(pw - _f(win.get("width_in"))) >= 2 or abs(ph - _f(win.get("height_in"))) >= 2:
            flags.append({
                "code": "window_size_parse_mismatch", "level": "loud",
                "vars": {"mark": str(win.get("id") or "?"),
                         "printed": str(win.get("printed_size") or ""),
                         "parsed": f"{pw:g}×{ph:g}",
                         "carried": f"{_f(win.get('width_in')):g}×{_f(win.get('height_in')):g}"}})

    # CROSS-SHEET MARK MERGE (Howard's Mark B finding, 2026-08-08): the
    # "SH 2-4_3-4 → 28×40" was D's dimensions attached to B's mark. The
    # signature is one mark carrying two different printed sizes — the
    # flag names it; a human resolves it against the schedule sheets.
    _mark_sizes: dict[str, set] = {}
    for win in (raw.get("windows") or []):
        if not isinstance(win, dict):
            continue
        mk = str(win.get("id") or "").strip().upper()
        ps = str(win.get("printed_size") or "").strip()
        if mk and ps:
            _mark_sizes.setdefault(mk, set()).add(ps)
    for mk, sizes in sorted(_mark_sizes.items()):
        if len(sizes) > 1:
            flags.append({
                "code": "mark_size_conflict", "level": "loud",
                "vars": {"mark": mk, "sizes": " vs ".join(sorted(sizes))}})

    # THE COUNT COLUMN GOVERNS COUNTS (ruled 2026-08-08): when the read
    # names per-sheet COUNT cells, the carried qty must be their sum —
    # a qty that isn't is symbol-counting wearing a schedule's clothes.
    for win in (raw.get("windows") or []):
        if not isinstance(win, dict):
            continue
        cbp = win.get("count_by_page")
        if not isinstance(cbp, dict) or not cbp:
            continue
        try:
            summed = sum(int(v) for v in cbp.values())
        except (TypeError, ValueError):
            continue
        if summed != int(win.get("qty") or 0):
            flags.append({
                "code": "count_column_mismatch", "level": "loud",
                "vars": {"mark": str(win.get("id") or "?"),
                         "cells": ", ".join(f"sheet {k}: {v}" for k, v in sorted(cbp.items())),
                         "summed": str(summed),
                         "carried": str(win.get("qty") or 0)}})

    # SEND-114 — the schedule row parser discloses. Refused counts and
    # recovered rows are LOUD; schedule-derived openings ride the NAMED
    # UNPLACED BUCKET (a schedule is silent on location by design).
    for u in (raw.get("_schedule_count_unread") or []):
        flags.append({
            "code": "schedule_count_unread", "level": "loud",
            "vars": {"kind": ("door" if u.get("kind") == "doors"
                              else "window"),
                     "mark": str(u.get("mark") or "?"),
                     "reason": str(u.get("reason") or "")}})
    for m in (raw.get("_schedule_rows_recovered") or []):
        flags.append({
            "code": "schedule_row_recovered", "level": "loud",
            "vars": {"mark": str(m.get("mark") or "?"),
                     "page": str(m.get("page") or "?"),
                     "type": str(m.get("type_hint") or "?")}})
    _row_sourced = (sum(int(c.get("count") or 0)
                        for c in raw.get("_schedule_row_counts") or [])
                    + sum(int(m.get("count") or 0)
                          for m in raw.get("_schedule_rows_recovered") or []))
    if _row_sourced:
        flags.append({
            "code": "openings_unplaced", "level": "loud",
            "vars": {"count": str(_row_sourced)}})

    # DOOR SIZES FROM PRINT (ruled 2026-08-08): "appears to be 16x7" is
    # an admission of no source. When a door row quotes a printed size,
    # the carried numbers must reproduce its parse — same discipline as
    # windows.
    for d in (raw.get("doors") or []):
        if not isinstance(d, dict):
            continue
        parsed = _parse_printed_size(d.get("printed_size"))
        if not parsed:
            continue
        pw, ph = parsed
        if abs(pw - _f(d.get("width_in"))) >= 2 or abs(ph - _f(d.get("height_in"))) >= 2:
            flags.append({
                "code": "door_size_parse_mismatch", "level": "loud",
                "vars": {"mark": str(d.get("id") or "?"),
                         "printed": str(d.get("printed_size") or ""),
                         "parsed": f"{pw:g}×{ph:g}",
                         "carried": f"{_f(d.get('width_in')):g}×{_f(d.get('height_in')):g}"}})

    for r in (raw.get("gutter_runs") or []):
        if not isinstance(r, dict):
            continue
        label = str(r.get("label") or "").lower()
        w = by_label.get(label)
        if w and _f(w.get("width_ft")) > 0 and _f(r.get("lf")) > _f(w.get("width_ft")) + 1.0:
            flags.append({
                "code": "run_exceeds_facade", "level": "loud",
                "vars": {"label": label, "run": f"{_f(r.get('lf')):g}",
                         "wall": f"{_f(w.get('width_ft')):g}"}})

    # CORNER WALK CONFLICT (Howard ruled 2026-08-10): when the primary
    # read and the roof pass disagree on the corner walk, the primary
    # STANDS and the card prints BOTH NUMBERS — one number teaches
    # nothing; two show at a glance when neither is right.
    _cwc = raw.get("_corner_walk_conflict")
    if isinstance(_cwc, dict):
        flags.append({
            "code": "corner_walk_conflict", "level": "loud",
            "vars": {"p_out": _cwc["primary"]["out"],
                     "p_in": _cwc["primary"]["in"],
                     "r_out": _cwc["roof_pass"]["out"],
                     "r_in": _cwc["roof_pass"]["in"]}})

    # WING FLAG GUARD (Howard ruled 2026-08-10 send 2): opposing walls
    # that disagree print BOTH widths — the rect stops silently
    # absorbing the difference (it takes the shorter of the pair).
    _w_widths = {str(w.get("label") or ""): _dim_v(w.get("width_ft"))
                 for w in walls}
    for _pair, _a, _b in _opposing_pairs(_w_widths)[2]:
        flags.append({
            "code": "opposing_walls_disagree", "level": "loud",
            "vars": {"pair": _pair, "a": f"{_a:g}", "b": f"{_b:g}"}})

    # EAVE/RAKE ORIENTATION (Howard ordered 2026-08-10, the EST-040221
    # instrument): on a simple gable roof, eaves and rakes sit on
    # OPPOSITE wall pairs, always. An eave figure that matches the GABLE
    # pair better than the eave pair is a rotated house, not a wrong
    # number.
    g_sum = sum(_dim_v(w.get("width_ft")) for w in walls
                if _dim_v(w.get("gable_triangle_height_ft")) > 0)
    e_sum = sum(_dim_v(w.get("width_ft")) for w in walls
                if _dim_v(w.get("gable_triangle_height_ft")) <= 0)
    ev = sum(_dim_v(p.get("eave_lf"))
             for p in (raw.get("roof_planes") or []) if isinstance(p, dict))
    if ev <= 0:
        ev = _dim_v(raw.get("eaves_lf"))
    if (ev > 0 and g_sum > 0 and e_sum > 0
            and abs(g_sum - e_sum) > 0.15 * max(g_sum, e_sum)
            and abs(ev - g_sum) < abs(ev - e_sum)):
        flags.append({
            "code": "eave_rake_orientation", "level": "loud",
            "vars": {"eaves": f"{ev:g}", "gsum": f"{g_sum:g}",
                     "esum": f"{e_sum:g}"}})
    return flags


def build_blueprint_readback(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict) or not raw:
        return None
    walls = [w for w in (raw.get("walls") or []) if isinstance(w, dict)]
    planes = [p for p in (raw.get("roof_planes") or []) if isinstance(p, dict)]
    plane_rows = []
    for p in planes:
        rake = float(p.get("rake_lf") or 0)
        is_porch = bool(p.get("is_porch"))
        plane_rows.append({
            "label": str(p.get("label") or "?"),
            "eave_lf": float(p.get("eave_lf") or 0),
            "rake_lf": rake,
            "gable_ends": int(p.get("gable_ends") or 0),
            "is_porch": is_porch,
            "porch_ceiling_sqft": float(p.get("porch_ceiling_sqft") or 0),
            # PER-PLANE pitch/overhang/wall-height (Howard ruled 2026-08-11
            # send-6): each plane's own reads ride the readback so the
            # rail names WHERE overhang is unread, WHERE pitch differs
            # from the main, and WHERE a garage wall printed its own
            # siding height. Values fall through when unread.
            "pitch": str(p.get("pitch") or "").strip(),
            "overhang_in": (float(p["overhang_in"]["v"])
                            if isinstance(p.get("overhang_in"), dict)
                            and p["overhang_in"].get("v") is not None
                            else (float(p["overhang_in"])
                                  if isinstance(p.get("overhang_in"),
                                                (int, float))
                                  and p.get("overhang_in") is not None
                                  else None)),
            "wall_height_ft": (float(p["wall_height_ft"]["v"])
                               if isinstance(p.get("wall_height_ft"), dict)
                               and p["wall_height_ft"].get("v") is not None
                               else (float(p["wall_height_ft"])
                                     if isinstance(p.get("wall_height_ft"),
                                                   (int, float))
                                     and p.get("wall_height_ft") is not None
                                     else None)),
            "gable_end_faces": [str(f) for f in (
                p.get("gable_end_faces") or [])
                if isinstance(f, str)],
            # THE BONI CATCH: a non-porch plane reading rake 0 is exactly
            # how the garage gable went invisible — flag LOUDLY.
            "gable_blind": (not is_porch) and rake == 0,
        })
    garage_banner = _roof_pass_needed(raw)

    # ---- corner ledger ----
    oc = int(raw.get("outside_corner_count") or 0)
    ic = int(raw.get("inside_corner_count") or 0)
    oclf = float(raw.get("outside_corner_lf") or 0)
    iclf = float(raw.get("inside_corner_lf") or 0)
    avg_h = float(raw.get("avg_wall_height_ft") or 0)
    if oc <= 0 or oclf <= 0:
        basis = "missing"
    elif avg_h > 0 and abs(oclf - oc * avg_h) <= max(1.0, 0.02 * oclf):
        # count × avg height — the 261 Haugh smell: averaging blurs tall
        # 2-story corners with short garage-wing corners.
        basis = "averaged"
    else:
        basis = "per_corner"
    widths = {str(w.get("label") or ""): float(w.get("width_ft") or 0) for w in walls}
    # WING FLAG GUARD (ruled 2026-08-10 send 2): the rect takes the
    # SHORTER of a disagreeing pair — max() could inflate it and
    # silently suppress the wing flag below.
    _fb, _lr, _wall_disags = _opposing_pairs(widths)
    rect = _fb * _lr
    # Correction 3 (ruled 2026-08-08): labelled quantities read as
    # labelled — the footprint is ground-floor + garage, never TOTAL
    # FINISHED with storeys summed.
    fp = _read_footprint_sqft(raw) or None
    wing_flag = bool(fp and rect > 0 and float(fp) > rect * 1.02)

    # ---- per-corner heights (ruled 2026-08-06 — grade before apply) ----
    hs_raw = raw.get("outside_corner_heights_ft")
    heights = None
    undim = 0
    if isinstance(hs_raw, list) and hs_raw:
        heights = []
        for h in hs_raw:
            try:
                v = float(h) if h is not None else 0.0
            except (TypeError, ValueError):
                v = 0.0
            heights.append(v if v > 0 else None)
        undim = sum(1 for v in heights if not v)
        if not any(v for v in heights if v):
            heights, undim = None, 0

    # ---- gutter run inventory (ruled 2026-08-06) ----
    gutter_runs = []
    for r in (raw.get("gutter_runs") or []):
        if isinstance(r, dict):
            try:
                lf = float(r.get("lf") or 0)
            except (TypeError, ValueError):
                lf = 0.0
            if lf > 0:
                gutter_runs.append({"label": str(r.get("label") or "run"),
                                    "lf": lf})

    # ---- porch tag ----
    porch_planes = [r for r in plane_rows if r["is_porch"]]
    ceiling = sum(r["porch_ceiling_sqft"] for r in porch_planes)
    top_ceiling = float(raw.get("porch_ceiling_sqft") or 0)
    if porch_planes and ceiling > 0:
        porch_status = "plane_read"
    elif porch_planes:
        porch_status = "plane_without_ceiling"
    elif top_ceiling > 0:
        # a ceiling figure with NO porch plane = a tag over nothing
        porch_status = "phantom_ceiling"
        ceiling = top_ceiling
    else:
        porch_status = "absent"

    # ---- honesty-flag rail ----
    rail: list[dict] = []
    if not planes:
        rail.append({"level": "loud", "code": "no_planes"})
    pitch = str(raw.get("roof_pitch") or "").strip()
    if pitch:
        rail.append({"level": "info", "code": "pitch", "text": pitch})
    else:
        rail.append({"level": "warn", "code": "no_pitch"})
    # PITCH PER PLANE (Howard ruled 2026-08-11 send-6): a plane with no
    # printed pitch FLAGS by name rather than inheriting the house
    # value. Planes whose pitch DIFFERS from the main pitch are named
    # (so a 10/12 entry gable against a 7/12 main is visible).
    _no_pitch = [r["label"] for r in plane_rows if not r.get("pitch")]
    _diff_pitch = [(r["label"], r["pitch"]) for r in plane_rows
                   if r.get("pitch") and pitch
                   and r["pitch"] != pitch]
    if _no_pitch:
        rail.append({"level": "warn", "code": "pitch_missing_on_planes",
                     "text": ", ".join(_no_pitch)})
    if _diff_pitch:
        rail.append({"level": "info", "code": "pitch_varies_by_plane",
                     "text": "; ".join(f"{lbl}={p}"
                                        for lbl, p in _diff_pitch)})
    sc = str(raw.get("scale_confidence") or "")
    if sc and sc != "high":
        rail.append({"level": "warn", "code": "scale_confidence", "text": sc})
    rp = raw.get("_roof_pass") or {}
    for key in sorted((rp.get("accepted") or {}).keys()):
        rail.append({"level": "info", "code": "roof_pass_merge", "text": key})
    # NEVER-TOUCH RULE (ruled 2026-08-09 send 7): a refused overwrite is
    # NAMED — the roof pass tried to replace an evidenced value with an
    # unevidenced one and was stopped at the seam.
    for key, why in sorted((rp.get("rejected") or {}).items()):
        rail.append({"level": "warn", "code": "roof_pass_rejected",
                     "text": f"{key}: {why}"})
    # PAGE TRUNCATION SAYS SO (ruled 2026-08-09 send 7): dropped pages
    # are invisible to the read, the locator, and every census — LOUD.
    _pt = raw.get("_pages_truncated") or {}
    if _pt:
        rail.append({"level": "loud", "code": "pages_truncated",
                     "text": f"{_pt.get('total')} → {_pt.get('read')}"})
    notes = str(raw.get("notes") or "").strip()
    if notes:
        rail.append({"level": "info", "code": "read_notes", "text": notes})
    # TRADE-SPEC FIELDS (ruled 2026-08-07): the read fills them or FLAGS
    # them — a silently-held default never passes as a read value.
    def _num(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0
    _ov = _num(raw.get("eave_overhang_in"))
    if _ov > 0:
        rail.append({"level": "info", "code": "overhang_printed", "text": f"{_ov:g}"})
    else:
        rail.append({"level": "warn", "code": "overhang_default"})
    # OVERHANG PER PLANE (Howard ruled 2026-08-11 send-6): the flag
    # names WHERE overhang is unread — never a blanket "not dimensioned
    # anywhere" when only some planes are missing it.
    _plane_ov_read = [(r["label"], r["overhang_in"]) for r in plane_rows
                      if r.get("overhang_in") is not None]
    _plane_ov_miss = [r["label"] for r in plane_rows
                      if r.get("overhang_in") is None
                      and not r.get("is_porch")]
    if _plane_ov_read:
        rail.append({"level": "info", "code": "overhang_by_plane",
                     "text": "; ".join(f"{lbl}={v:g}\""
                                        for lbl, v in _plane_ov_read)})
    if _plane_ov_miss:
        rail.append({"level": "warn", "code": "overhang_missing_on_planes",
                     "text": ", ".join(_plane_ov_miss)})
    # WALL HEIGHT PER PLANE (Howard ruled 2026-08-11 send-6, garage wall
    # unread class): a plane carrying a printed wall_height_ft (e.g. a
    # garage wing where the 9'-11 7/8" is drawn) surfaces here so
    # the sheet renderer can pull the printed value instead of
    # silently tuning from the avg fallback.
    _plane_wh = [(r["label"], r["wall_height_ft"]) for r in plane_rows
                 if r.get("wall_height_ft") is not None]
    if _plane_wh:
        rail.append({"level": "info", "code": "wall_height_by_plane",
                     "text": "; ".join(f"{lbl}={v:g} ft"
                                        for lbl, v in _plane_wh)})
    # SEND-9 (Howard ruled 2026-08-12): unverified and fabricated
    # dims surface on the rail as distinct claims — an unverified
    # dim MAY be real (kept for the card, marked); a fabricated dim
    # is a lie (killed). "Refused is not fabricated, and the card
    # must say which."
    _unv = raw.get("_dim_unverified") or []
    _fab = raw.get("_dim_fabricated") or []
    _misread = raw.get("_dim_misread") or []
    if _unv:
        rail.append({"level": "warn", "code": "dims_unverified",
                     "text": ", ".join(r.get("path", "?") for r in _unv)})
    if _fab:
        # SEND-11 item 3: fabricated rail names each path with its
        # evidence-strength badge. `strong` = densely-read page, no
        # hit ⇒ real fabrication. `weak` = poorly-read page ⇒ the
        # miss may be OCR's fault, treat with lower confidence.
        rail.append({"level": "loud", "code": "dims_fabricated",
                     "text": ", ".join(
                         f"{r.get('path','?')}[{r.get('evidence_strength','?')}]"
                         for r in _fab)})
    if _misread:
        # SEND-11 item 2: MISREAD is diagnostically distinct from
        # fabrication — the quote is absent but a real OCR run sits
        # one character-edit away. Card names the real printed string.
        rail.append({"level": "loud", "code": "dims_misread",
                     "text": "; ".join(
                         f"{r.get('path','?')} said {r.get('quotes') or '?'} "
                         f"→ OCR has {r.get('misread_of')!r}"
                         for r in _misread)})
    # SEND-10 (Howard ruled 2026-08-12): the one-source-one-path
    # guard's demoted list rides its own rail code so the card can
    # separate a shared-source demotion from a lonely unverified.
    _shared = raw.get("_dim_shared_source") or []
    _shared_plain = [r for r in _shared if not r.get("conflicting")]
    _shared_conf = [r for r in _shared if r.get("conflicting")]
    if _shared_plain:
        rail.append({"level": "loud", "code": "dims_shared_source",
                     "text": "; ".join(
                         f"{r.get('quote')} p{r.get('page')} → "
                         f"{','.join(r.get('consumers') or [])} "
                         f"(cited for {len(r.get('consumers') or [])} paths "
                         "— attribution unverified, value kept)"
                         for r in _shared_plain)})
    if _shared_conf:
        _unk = sorted({lf for r in _shared_conf
                       for lf in _unknown_axis_leaves(r.get("consumers") or [])})
        _unk_note = (f" [undeclared-axis leaf: {', '.join(_unk)}]"
                     if _unk else "")
        rail.append({"level": "loud", "code": "dims_shared_source_conflict",
                     "text": "ATTRIBUTION CONFLICT — one quote feeds the "
                             "same field on two named features; cannot tell "
                             "which is wrong, value kept, reported not "
                             "resolved: " + "; ".join(
                                 f"{r.get('quote')} p{r.get('page')} → "
                                 f"{','.join(r.get('consumers') or [])}"
                                 for r in _shared_conf) + _unk_note})
    _fw = _num(raw.get("fascia_width_in"))
    if _fw > 0:
        rail.append({"level": "info", "code": "fascia_printed", "text": f"{_fw:g}"})
    else:
        rail.append({"level": "warn", "code": "fascia_default"})
    _idd = raw.get("_interior_doors_dropped")
    if _idd:
        rail.append({"level": "warn", "code": "interior_doors_dropped",
                     "text": str(_idd)})
    # THE COUNT COLUMN GOVERNS COUNTS (ruled 2026-08-08, enforced
    # 2026-08-09): every rewrite, unread cell, conflict, and merge the
    # enforcement pass performed is NAMED here — nothing silent.
    _ccg = raw.get("_count_column_governed") or []
    if _ccg:
        rail.append({"level": "loud", "code": "count_column_governed",
                     "text": "; ".join(
                         f"{g.get('mark')}: carried {g.get('carried')} → "
                         f"printed {g.get('governed')} ({g.get('cells')})"
                         for g in _ccg[:8])})
    _ccu = raw.get("_count_cells_unread") or []
    if _ccu:
        rail.append({"level": "loud", "code": "count_cells_unread",
                     "text": ", ".join(str(u.get("mark")) for u in _ccu[:12])})
    _ccc = raw.get("_count_cell_conflicts") or []
    if _ccc:
        rail.append({"level": "loud", "code": "count_cell_conflict",
                     "text": "; ".join(
                         f"{c.get('mark')} sheet {c.get('sheet')}: {c.get('cells')}"
                         for c in _ccc[:8])})
    if "windows" in (raw.get("_count_column_absent") or []):
        rail.append({"level": "warn", "code": "count_column_absent"})
    _mrm = raw.get("_mark_rows_merged") or []
    if _mrm:
        rail.append({"level": "info", "code": "mark_rows_merged",
                     "text": ", ".join(_mrm[:12])})
    # MARKS FACE THE LOCATOR TOO (ruled 2026-08-09): fabricated rows and
    # killed size quotes are named, never silent.
    _mdn = raw.get("_marks_dropped_not_located") or []
    if _mdn:
        rail.append({"level": "loud", "code": "mark_not_located",
                     "text": "; ".join(
                         f"{d.get('mark')} ({d.get('kind')})"
                         for d in _mdn[:8])})
    _mqm = raw.get("_mark_quote_misses") or []
    if _mqm:
        rail.append({"level": "loud", "code": "mark_quote_miss",
                     "text": "; ".join(
                         f"{m.get('mark')}.{m.get('field')} \u201c{m.get('from')}\u201d"
                         for m in _mqm[:8])})
    # OMISSION CHECK (ruled 2026-08-09): rows the page prints that the
    # read never carried — the one-directional evidence layer's blind
    # side, now instrumented.
    _som = raw.get("_schedule_omissions") or []
    if _som:
        rail.append({"level": "loud", "code": "schedule_row_omitted",
                     "text": "; ".join(
                         f"{o.get('token')} (sheet {o.get('page')})"
                         for o in _som[:10])})
    # INTERIOR SIGNAL BY MACHINE (ruled 2026-08-09): HOLLOW CORE cannot
    # wear an exterior label.
    _isd = raw.get("_interior_signal_dropped") or []
    if _isd:
        rail.append({"level": "loud", "code": "interior_signal_machine",
                     "text": "; ".join(
                         f"{d.get('mark')} ({d.get('marker')}, sheet {d.get('page')})"
                         for d in _isd[:8])})
    # FRACTION SKELETON (2026-08-09): the OCR engine cannot read stacked
    # ½ glyphs — quotes located on their whole-inch skeleton are NAMED.
    _skm = raw.get("_skeleton_matches") or []
    if _skm:
        rail.append({"level": "info", "code": "skeleton_match",
                     "text": "; ".join(
                         f"{s.get('mark')}.{s.get('field')} \u201c{s.get('from')}\u201d"
                         for s in _skm[:8])})
    # DIM LOCATED BY SKELETON (2026-08-14 send-12): a wall/segment
    # dimension whose stacked fraction OCR could not read located on its
    # fraction-stripped skeleton — "the fractions rest on the read's
    # transcription". NAMED so the card shows the leniency, never silent.
    _skl = raw.get("_skeleton_located") or []
    if _skl:
        rail.append({"level": "info", "code": "dim_located_by_skeleton",
                     "text": "the fractions rest on the read's transcription: "
                             + "; ".join(
                                 f"{d.get('path')} \u201c{d.get('from')}\u201d "
                                 f"(sheet {d.get('page')})"
                                 for d in _skl[:8])})
    # MARK-MERGE (ruled 2026-08-09 send 4): two marks never share a code
    # on a real schedule — sharers are a suspected row merge, named with
    # the likely unread sibling.
    _mms = raw.get("_mark_merge_suspected") or []
    if _mms:
        rail.append({"level": "loud", "code": "mark_merge_suspected",
                     "text": "; ".join(
                         f"{' + '.join(m.get('marks') or [])} share {m.get('code')}"
                         + (f" while {'/'.join(m['likely_unread'])} prints unread"
                            if m.get("likely_unread") else "")
                         for m in _mms[:6])})
    # CALLOUT CENSUS (ruled 2026-08-09 send 4): a profile printed on the
    # elevations that the read never carried.
    _cal = raw.get("_callout_omissions") or []
    if _cal:
        rail.append({"level": "loud", "code": "callout_omitted",
                     "text": "; ".join(
                         f"{c.get('family')} (sheet {c.get('page')}, \u201c{c.get('run')}\u201d)"
                         for c in _cal[:6])})
    # EVIDENCE-OR-NULL (ruled 2026-08-08): dims that arrived without a
    # quoted printed string were NULLED BY CONSTRUCTION — named here.
    _nulled = raw.get("_nulled_no_evidence") or []
    if _nulled:
        _shown = ", ".join(str(p) for p in _nulled[:8])
        if len(_nulled) > 8:
            _shown += f" +{len(_nulled) - 8} more"
        rail.append({"level": "loud", "code": "dims_nulled_no_evidence",
                     "text": _shown})
    # OCR CONTRADICTION (ruled 2026-08-08 — the free second read): the
    # model quotes a printed string; a machine text-read of the same
    # page cannot find it. Two independent reads of the same pixels
    # disagree — NAMED, resolved toward neither.
    _om = raw.get("_ocr_quote_misses") or []
    if _om:
        _shown_om = "; ".join(f"\u201c{m.get('from')}\u201d (sheet {m.get('page')})"
                              for m in _om[:8])
        if len(_om) > 8:
            _shown_om += f" (+{len(_om) - 8} more)"
        rail.append({"level": "warn", "code": "ocr_quote_miss",
                     "text": _shown_om})
    # SOFFIT FINISH IS STATED ON THE DRAWING (ruled 2026-08-08): the
    # vented-vs-solid steer reads or flags — never a silent default.
    _sf = raw.get("soffit_finish") or {}
    _sfe = str(_sf.get("eaves") or "").strip().lower()
    _sfr = str(_sf.get("rakes") or "").strip().lower()
    if _sfe or _sfr:
        rail.append({"level": "info", "code": "soffit_finish_printed",
                     "text": " · ".join(x for x in (
                         f"eaves {_sfe}" if _sfe else "",
                         f"rakes {_sfr}" if _sfr else "") if x)})
    else:
        rail.append({"level": "warn", "code": "soffit_finish_default"})
    # OVERHANG IS PER-LOCATION (ruled 2026-08-08): distinct values —
    # including a printed NO-OVERHANG — mean one default can't cover
    # the house.
    _onotes = [n for n in (raw.get("overhang_notes") or []) if isinstance(n, dict)]
    _ovals = set()
    for n in _onotes:
        try:
            _ovals.add(float(n.get("overhang_in") if n.get("overhang_in") is not None else -1))
        except (TypeError, ValueError):
            continue
    _ovals.discard(-1.0)
    if len(_ovals) > 1 or (_ovals and 0.0 in _ovals):
        rail.append({"level": "warn", "code": "overhang_varies",
                     "text": "; ".join(
                         f"{str(n.get('where') or '?')}: "
                         + (f"{float(n.get('overhang_in')):g}\""
                            if n.get('overhang_in') not in (None, "") else "?")
                         + (f" ({n.get('text')})" if n.get("text") else "")
                         for n in _onotes)})

    return {
        "planes": plane_rows,
        "no_planes": len(plane_rows) == 0,
        "plane_totals": ({
            "eaves_lf": sum(r["eave_lf"] for r in plane_rows),
            "rakes_lf": sum(r["rake_lf"] for r in plane_rows),
            "gable_ends": sum(r["gable_ends"] for r in plane_rows),
        } if plane_rows else None),
        "garage_banner": garage_banner,
        "corners": {
            "outside": oc, "inside": ic,
            "outside_lf": oclf, "inside_lf": iclf,
            "invariant_ok": (oc - ic) == 4 if (oc or ic) else None,
            "basis": basis, "avg_wall_height_ft": avg_h,
            "heights_ft": heights, "undimensioned": undim,
        },
        "wing_check": {
            "footprint_area_sqft": float(fp) if fp else None,
            "rectangle_area_sqft": round(rect, 1) if rect else None,
            "flag": wing_flag,
        },
        "porch": {"status": porch_status, "ceiling_sqft": ceiling,
                  "planes": [r["label"] for r in porch_planes]},
        # GABLE ATTRIBUTION LEDGER (Howard ruled 2026-08-11 send-3 item c):
        # every plane's gable ends attributed to a wall, so the front-
        # facing wing gable is now visible on the readback (readback
        # only — Phase 2 draws them onto the sheet).
        "gable_attribution": (lambda w, p: __import__(
            "gable_attribution").attribute_secondary_gables(w, p))(
            walls, planes),
        "gutter_runs": gutter_runs or None,
        "gutter_runs_total": (round(sum(r["lf"] for r in gutter_runs), 1)
                              if gutter_runs else None),
        # INTERNAL CONSISTENCY CHECKER (ruled 2026-08-07) — the card
        # arrives already clean; contradictions are caught HERE.
        "consistency": check_read_consistency(raw),
        # VISUAL AUDIT (ruled 2026-08-08 — one schema, one renderer):
        # every evidenced dim with its page/quote/box; dropped and unread
        # paths are FIRST-CLASS no-source states, not omissions.
        "evidence": {
            "items": [{"path": p, **(v if isinstance(v, dict) else {})}
                      for p, v in sorted((raw.get("_dim_evidence") or {}).items())],
            "dropped": list(raw.get("_nulled_no_evidence") or []),
            "unread": list(raw.get("_dim_unread") or []),
        },
        # SEND-9: FABRICATED vs UNVERIFIED are DIFFERENT states — the
        # card must show WHICH. Fabricated (quote norm not present in
        # OCR anywhere) rides `dim_fabricated`. Unverified (real string
        # unconfirmed near its feature) rides `dim_unverified`. Money
        # never sees either (the values are nulled on raw); the card
        # shows both with distinct badges (ruled 2026-08-12 send-9
        # item 3: showing a printed dim as absent is a different lie
        # from the one we are fixing).
        "dim_unverified": list(raw.get("_dim_unverified") or []),
        "dim_fabricated": list(raw.get("_dim_fabricated") or []),
        "dim_misread": list(raw.get("_dim_misread") or []),
        "dim_shared_source": list(raw.get("_dim_shared_source") or []),
        # SEAM ACCOUNTING (ruled 2026-08-09): the ledger of everything
        # any layer removed — visible, never silent.
        "seams": raw.get("_seam_ledger") or None,
        "rail": rail,
    }


def _with_readback(result, source_probe=None, stability=None):
    """Read-time enrichment for the status/latest responses — computed on
    the fly, never persisted, never fed to any derivation."""
    if isinstance(result, dict) and result.get("raw_ai"):
        try:
            rb = build_blueprint_readback(result["raw_ai"])
            if rb is not None and source_probe:
                rb["source"] = {k: source_probe.get(k) for k in
                                ("kind", "text_pages", "page_count")}
            # DETERMINISM GATE (ruled 2026-08-08): stability rides the
            # readback so the card can chip agreement — as stability,
            # never as correctness.
            if rb is not None and stability is not None:
                rb["stability"] = stability
            return {**result, "readback": rb}
        except Exception:
            logger.exception("[ai-blueprint] readback build failed — served without")
    return result



def _compress_for_claude(img_bytes: bytes, max_raw_bytes: int = 5_500_000) -> bytes:
    """Ensure a single image fits comfortably under Anthropic's 10 MB
    base64 limit. Anthropic measures the base64 string (~1.33× raw),
    so we target raw bytes < ~5.5 MB → base64 < ~7.3 MB with headroom.

    Strategy: JPEG-encode at q=88, then if still too large iteratively
    downscale by 0.85× and re-encode (q=85 → q=78 → q=70). Returns the
    smallest viable JPEG bytes. Falls back to the original bytes if PIL
    fails or the image is already small enough.
    """
    if len(img_bytes) <= max_raw_bytes and img_bytes[:3] == b"\xff\xd8\xff":
        # Already a small JPEG, no work needed.
        return img_bytes
    try:
        with Image.open(io.BytesIO(img_bytes)) as im:
            # Convert anything alpha/palette-mode into RGB so JPEG works.
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            qualities = [88, 85, 78, 70, 60]
            scales = [1.0, 0.85, 0.72, 0.6, 0.5, 0.42]
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
            # Last resort — return whatever the lowest-quality smallest
            # scale produced (still better than the original PNG).
            return data  # noqa: F821 — defined inside the loop
    except Exception:
        logger.exception("[ai-blueprint] image compression failed; sending original")
        return img_bytes


def _render_pdf_to_pngs(raw_pdf: bytes, max_pages: int) -> tuple[list[bytes], int]:
    """Rasterize a PDF into a list of PNG byte-strings, one per page,
    capped at `max_pages`. Returns (pages, total_page_count) — the caller
    accounts for any page the cap removed (a removal with no accounting
    is the recurring failure class, ruled 2026-08-09)."""
    out: list[bytes] = []
    try:
        doc = pdfium.PdfDocument(raw_pdf)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {e}") from e
    total_pages = len(doc)
    page_count = min(total_pages, max_pages)
    for i in range(page_count):
        page = doc[i]
        try:
            pil_image = page.render(scale=PDF_RENDER_SCALE).to_pil()
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG", optimize=True)
            # Compress to fit under Anthropic's 10 MB base64 cap. Blueprints
            # rendered at scale=2.0 routinely produce 8–15 MB PNGs that
            # explode past the limit once base64-encoded.
            out.append(_compress_for_claude(buf.getvalue()))
        finally:
            page.close()
    doc.close()
    return out, total_pages


def _probe_pdf_source(raw_pdf: bytes, max_pages: int = 40) -> tuple[dict, list[str]]:
    """SOURCE-RETENTION RULING (Howard, 2026-08-07): a derived artifact
    never replaces its source. Answers native-vs-scan from the PDF's own
    text layer (pdfium textpage char census) — no vision involved. Returns
    (probe_summary, per_page_text). Text is the extraction ground truth;
    the vision read never overrules a printed character."""
    pages: list[dict] = []
    texts: list[str] = []
    try:
        doc = pdfium.PdfDocument(raw_pdf)
    except Exception:
        return {"kind": "unreadable", "pages": [], "text_pages": 0, "page_count": 0}, []
    n = min(len(doc), max_pages)
    for i in range(n):
        page = doc[i]
        txt = ""
        try:
            tp = page.get_textpage()
            txt = (tp.get_text_range() or "").strip()
            tp.close()
        except Exception:
            txt = ""
        finally:
            page.close()
        pages.append({"index": i, "chars": len(txt)})
        texts.append(txt[:20000])
    doc.close()
    # A true scan extracts ZERO characters — any real extractable text
    # (≥20 chars) marks the page as carrying a native text layer.
    text_pages_n = sum(1 for p in pages if p["chars"] >= 20)
    if not pages:
        kind = "unreadable"
    elif text_pages_n == 0:
        kind = "scan"
    elif text_pages_n == len(pages):
        kind = "native_text"
    else:
        kind = "mixed"
    return {
        "kind": kind,
        "pages": pages,
        "text_pages": text_pages_n,
        "page_count": len(pages),
    }, texts


def _aggregate_to_hover_shape(raw: dict, annotations: dict | None = None) -> dict:
    """Roll Claude's blueprint extraction into the same measurements dict
    the rest of the app speaks. Mirrors the photo-measure aggregator but
    uses the printed dims at face value (no defensive clamps — the
    contractor can see the raw Claude JSON in the preview to verify)."""
    walls = raw.get("walls") or []
    windows = raw.get("windows") or []
    doors = raw.get("doors") or []
    # INTERIOR-DOOR GUARD (Howard ruled 2026-08-07): a door with no
    # exterior evidence never pollutes the entry-door count — doors drive
    # J-channel and coil. Dropped rows are COUNTED and FLAGGED, never silent.
    _interior = [d for d in doors if isinstance(d, dict)
                 and str(d.get("exterior_evidence") or "").lower() == "none"]
    if _interior:
        doors = [d for d in doors if d not in _interior]
        raw["_interior_doors_dropped"] = len(_interior)
        seam_accounting.account(
            raw, "interior_doors_dropped",
            [str(d.get("id") or "?") for d in _interior])

    # SEND-47 HEIGHT BUILD (Howard authorized 2026-08-18) — sealed DP-1:
    # a face's height derives from ITS OWN elevation drawing (FIRST FLOOR
    # → plate/soffit) or the face REFUSES with the exact gap named. Model
    # heights are DEMOTED TO HYPOTHESIS (census finding SEND-46: Boni's
    # 20.0 is unreconstructable from its own cited evidence; Letrick's
    # model copied one string across faces) — shown on the record, never
    # feeding a quantity. Standing Prohibition is structural: a rail
    # outside the face's own band can never enter. A run with no
    # persisted OCR is DISCLOSED via the seam ledger, never silently
    # model-fed.
    from height_read import apply_height_build
    _hb = apply_height_build(raw, walls)
    if _hb.get("status") == "APPLIED":
        seam_accounting.account(
            raw, "height_build",
            [f"{f}: {r.get('status')}"
             + (f" {r.get('ft')} ft" if r.get("ft") else "")
             for f, r in (_hb.get("faces") or {}).items()])
    else:
        seam_accounting.account(raw, "height_build_not_run",
                                [_hb.get("reason") or "no OCR text"])

    # Shakedown fix (2026-07-14) — pitch-computed gable rise. Printed
    # pitch is the authority; drawing-scaled reads under-state the rise
    # (June finding: 8.5' scaled vs 8.75' at 7/12 on a 30' end).
    _pitch_m = re.match(r"^(\d+(?:\.\d+)?)\s*[/:]\s*12$", str(raw.get("roof_pitch") or "").strip())
    pitch_rise = float(_pitch_m.group(1)) if _pitch_m else None

    def _gable_rise(width_ft, printed_gh):
        if pitch_rise and printed_gh > 0 and width_ft > 0:
            return (width_ft / 2.0) * (pitch_rise / 12.0)
        return printed_gh

    gable_pitch_provenance = []
    # RULINGS CC + DD + EE (send-24/25): compute footprint closure BEFORE
    # the walk so a face that fails closure is refused THROUGH the
    # derivation (Ruling EE) — NOT DERIVABLE, blocking the gate — while its
    # read width stays on the record as the failing input. `refused_faces`
    # maps face → "footprint does not close: <failing relation verbatim>".
    try:
        from footprint_checks import garage_side_verdict, footprint_closure
        _fp_src = {"walls": walls, "doors": doors,
                   "roof_planes": raw.get("roof_planes") or [],
                   "elevation_labels": raw.get("sheets_identified") or []}
        _garage_verdict = garage_side_verdict(_fp_src)
        _closure = footprint_closure(_fp_src)
        _refused_faces = _closure.get("refused_faces") or {}
    except Exception:
        _garage_verdict, _closure, _refused_faces = None, None, {}
    # ONE WALL WALK (ruled 2026-08-01, step 1): shared math in
    # measure_staging.walk_walls — GABLE FACTOR 0.70 sealed across doors
    # (the pre-C4 0.5 true-triangle retired). Blueprint's source adapter
    # keeps the pitch-computed rise (printed pitch beats drawing-scaled).
    _walk = staging.walk_walls(walls, gable_rise_fn=_gable_rise,
                               refused_faces=_refused_faces)
    siding_sqft = _walk["siding_sqft"]
    gable_sqft = _walk["gable_sqft"]
    dormer_sqft = _walk["dormer_sqft"]
    for d in _walk["detail"]:
        if d.get("refused"):
            continue  # RULING EE: a closure-refused face carries no rise
        if d["rise_used"] != d["rise_read"]:
            gable_pitch_provenance.append({
                "wall": (d["label"] or "?"),
                "scaled_ft": round(d["rise_read"], 2),
                "computed_ft": round(d["rise_used"], 2),
                "pitch": str(raw.get("roof_pitch") or ""),
            })
    siding_sqft += gable_sqft + dormer_sqft
    # DERIVE-OR-DISCLOSE (Howard ruled 2026-08-14): the aggregate never
    # silently sums a subset — a wall whose width/height was killed or
    # never read is NAMED on the run so the card and the seam ledger
    # both disclose the missing face. Evidence-or-null: a derived value
    # dies with its source, and the total says which face it lost.
    _walk_faces_nd = _walk.get("faces_not_derivable") or []
    if _walk_faces_nd:
        raw["_faces_not_derivable"] = _walk_faces_nd
        seam_accounting.account(
            raw, "wall_area_not_derivable",
            [f"{(f.get('label') or '?')} {(f.get('surface') or 'body')} — {f.get('reason')}"
             for f in _walk_faces_nd])

    # Shakedown fix (2026-07-14) — chase/appendage faces belong in the
    # siding area (C4-fix analogue of the photo path's attributed faces).
    # walls[] excludes them by schema; appendages[] is the sole carrier.
    appendage_sqft = 0.0
    appendage_faces = []
    for ap in (raw.get("appendages") or []):
        try:
            fs = float(ap.get("faces_sqft") or 0)
        except (TypeError, ValueError):
            fs = 0.0
        if fs > 0:
            appendage_sqft += fs
            appendage_faces.append(
                f"{(ap.get('wall') or '?')} {(ap.get('kind') or 'appendage').replace('_', ' ')} ({fs:.0f} ft²)")
    siding_sqft += appendage_sqft

    # ONE OPENING BUCKETING (ruled 2026-08-01, step 1): door adapter
    # normalizes rows; the math (buckets, door_count TOTAL, ft², perimeter)
    # is measure_staging.bucket_openings — one copy, all doors.
    _rows = []
    for win in windows:
        if win.get("_count_unread"):
            continue  # schedule printed no COUNT — contributes nothing (ruled)
        try:
            qty = max(1, int(win.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        _rows.append({"type": "window", "count": qty,
                      "width_in": win.get("width_in"), "height_in": win.get("height_in")})
    for d in doors:
        if d.get("_count_unread"):
            continue  # schedule printed no COUNT — contributes nothing (ruled)
        t = (d.get("type_hint") or "").lower()
        if "garage" in t:
            bucket = "garage_door"
        elif "patio" in t:
            bucket = "patio_door"
        else:
            bucket = "entry_door"
        try:
            qty = max(1, int(d.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        _rows.append({"type": bucket, "count": qty,
                      "width_in": d.get("width_in"), "height_in": d.get("height_in")})
    _bk = staging.bucket_openings(_rows)
    counts = _bk["counts"]
    opening_sqft = _bk["opening_sqft"]
    perimeter_lf = _bk["opening_perimeter_lf"]
    # SEND-114 — no floor that looks like a count: when every window
    # mark's count REFUSED, window_count is REFUSED (None), never a 0
    # posing as a survey and never marks-as-1.
    _sched_unread = raw.get("_schedule_count_unread") or []
    _win_unread = [u for u in _sched_unread if u.get("kind") == "windows"]

    # SEND-115 RULING 1 (2026-08-23): DEDUCT OPENINGS, SHOW THE DEDUCTION.
    # Full area, no threshold. The deduction lands at AGGREGATE until a
    # placement read exists (openings_unplaced) — never attributed per
    # face. What refused is NAMED for the takeoff line — a refused count
    # or size contributes 0 ft², never a guess.
    _ded_refused = [{"kind": u.get("kind"), "mark": str(u.get("mark") or "?"),
                     "why": "count cell unreadable"} for u in _sched_unread]
    for _r in windows:
        if isinstance(_r, dict) and not _r.get("_count_unread") \
                and not (_r.get("width_in") and _r.get("height_in")):
            _ded_refused.append({"kind": "windows",
                                 "mark": str(_r.get("id") or "?"),
                                 "why": "size refused — contributes 0 ft²"})
    for _r in doors:
        if isinstance(_r, dict) and not _r.get("_count_unread") \
                and not (_r.get("width_in") and _r.get("height_in")):
            _ded_refused.append({"kind": "doors",
                                 "mark": str(_r.get("id") or "?"),
                                 "why": "size refused — contributes 0 ft²"})
    _openings_deduction = None
    if opening_sqft > 0 or _ded_refused:
        # SEND-116 ITEM 1 (Howard ruled 2026-08-23): AN OPENING MAY ONLY
        # DEDUCT FROM A GROSS THAT INCLUDES THE FACE IT SITS ON. Without
        # placement an opening's face is unknown, so the deduction needs
        # EVERY face in the gross — when any face refused, the DEDUCTION
        # REFUSES, naming both the openings and the faces. A partial
        # gross minus a whole-house deduction is a different quantity
        # wearing the same label (Boni: net 1.5 ft² on a 33-square
        # house). NO FLOOR: openings meeting/exceeding a fully-derived
        # gross is a read inconsistency and refuses too — a floor at 0
        # is a silent zero (dart hid behind one).
        _ded_faces_refused = sorted({
            str(f.get("label") or f.get("elevation") or "?")
            for f in _walk_faces_nd})
        _net = siding_sqft - opening_sqft
        if _ded_faces_refused:
            _openings_deduction = {
                "deduction_refused": True,
                "refusal_class": "faces_refused",
                "openings_sqft_read": opening_sqft,
                "gross_sqft": siding_sqft,
                "faces_refused": _ded_faces_refused,
                "refused": _ded_refused,
            }
        elif opening_sqft > 0 and _net <= 0:
            _openings_deduction = {
                "deduction_refused": True,
                "refusal_class": "openings_exceed_gross",
                "openings_sqft_read": opening_sqft,
                "gross_sqft": siding_sqft,
                "faces_refused": [],
                "refused": _ded_refused,
            }
        else:
            # RULING 7 holds: full precision on the way in — no intake
            # rounding on engine keys; the note rounds at DISPLAY.
            _openings_deduction = {
                "deducted_sqft": opening_sqft,
                "gross_sqft": siding_sqft,
                "net_sqft": _net,
                "refused": _ded_refused,
                "complete": not _ded_refused,
            }

    # Expand schedule rows into a per-opening list (qty=1 each) so
    # _build_window_openings sees one row per physical window. Matches
    # the HOVER importer's contract.
    expanded_windows = []
    for win in windows:
        if win.get("_count_unread"):
            continue
        try:
            qty = max(1, int(win.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        for n in range(qty):
            mark = str(win.get("id") or "").strip()
            label = f"{mark}-{n + 1}" if (qty > 1 and mark) else (mark or f"W-{uuid.uuid4().hex[:4]}")
            expanded_windows.append({
                "id": label,
                "width_in": float(win.get("width_in") or 0),
                "height_in": float(win.get("height_in") or 0),
            })

    # Iter 57w — Defensive eaves_lf override. Claude historically returns
    # the full floor-plan perimeter as eaves_lf, which is only correct
    # for hip roofs. On a typical gable-roof house gutters run only on
    # the non-gable walls (eave walls). When any wall is flagged as a
    # gable (`gable_triangle_height_ft > 0`), recompute eaves_lf as the
    # sum of widths of NON-gable walls. This drops the gable ends from
    # the gutter coil + downspout count + elbow count downstream.
    # BONI RULING 1 (Howard, 2026-08-05) — EAVES ACROSS ALL ROOF PLANES.
    # The four-wall model reads the main rectangle only; a projecting
    # garage or covered porch carries eave runs it cannot see (Boni:
    # 116 read vs 167 installed). When the model returns roof_planes,
    # the plane sum IS the eave figure and the Iter-57w wall-derived
    # override STANDS DOWN. The porch plane rides the same read: its
    # ceiling ft² feeds the soffit derivation (one structure, two
    # consequences — the dropped porch hid both its eave and ceiling).
    planes = [p for p in (raw.get("roof_planes") or []) if isinstance(p, dict)]
    plane_eaves = sum(float(p.get("eave_lf") or 0) for p in planes)
    any_gable = any(float(w.get("gable_triangle_height_ft") or 0) > 0 for w in walls)
    if plane_eaves > 0:
        raw["eaves_lf"] = plane_eaves
        raw["_eaves_plane_summed"] = True
        # BONI SECOND SEND (Howard, 2026-08-05) — gable-end census for the
        # multiple-gable report: how many triangular ends the plane read
        # carries (the rectangle walk sees exactly the main pair).
        gable_ends = sum(int(p.get("gable_ends") or 0) for p in planes)
        if gable_ends > 0:
            raw["_gable_ends_plane_read"] = gable_ends
        porch_sqft = sum(float(p.get("porch_ceiling_sqft") or 0)
                         for p in planes if p.get("is_porch"))
        if porch_sqft > 0 and not raw.get("porch_ceiling_sqft"):
            raw["porch_ceiling_sqft"] = porch_sqft
    # RAKES — THE PLANE SUM GOVERNS WHENEVER PLANES CARRY RAKE FIGURES
    # (Howard ruled 2026-08-10, exact mirror of the eaves rule).
    # Larger-wins is dead here: a bare top-level number must never beat
    # evidenced planes.
    plane_rakes = sum(float(p.get("rake_lf") or 0) for p in planes)
    if plane_rakes > 0:
        raw["rakes_lf"] = plane_rakes
        raw["_rakes_plane_summed"] = True
    else:
        if any_gable:
            # ONE COPY (step 6): the recompute lives in measure_staging.
            raw["eaves_lf"] = staging.eaves_from_walls(walls, raw.get("eaves_lf"))

    # Shakedown fix (2026-07-14) — START-COURSE CONTRACT: the aggregator
    # reports the RAW floor-plan perimeter; the ENGINE owns the entry-door
    # deduction (single-source convention — pre-deducting here would
    # double-deduct downstream in lp_package.assemble_lp_package).
    _perimeter_lf = sum(float(w.get("width_ft") or 0) for w in walls)
    _printed_starter = float(raw.get("starter_lf") or raw.get("eaves_lf") or 0)
    if _perimeter_lf > 0:
        _starter_lf = _perimeter_lf
        _starter_basis = (
            f"perimeter {_perimeter_lf:.0f} LF — engine deducts entry-door widths "
            f"per convention (printed read {_printed_starter:.0f})")
    else:
        _starter_lf = _printed_starter
        _starter_basis = "printed read (no wall widths extracted)"

    # Feature-pooled OSC basis for the engine's no-C3 fallback: chase
    # edges pool per feature (2 full-height + 2 above-roofline edges),
    # separate from the house-corner walk.
    _osc_features = []
    _avg_eave = float(raw.get("avg_wall_height_ft") or 0) or 9.5
    for ap in (raw.get("appendages") or []):
        try:
            _h = float(ap.get("height_ft") or 0)
        except (TypeError, ValueError):
            _h = 0.0
        if _h <= 0:
            continue
        _above = max(0.0, _h - _avg_eave) if ap.get("extends_above_roofline") else 0.0
        _osc_features.append({
            "label": f"{(ap.get('wall') or '?')} {(ap.get('kind') or 'appendage').replace('_', ' ')}",
            "lf": round(2 * _h + 2 * _above, 1),
        })

    # PER-CORNER HEIGHTS + GUTTER RUNS (ruled 2026-08-06): scope the
    # door's own reads through — nulls kept (an undimensioned corner
    # keeps its flag downstream, never averaged or defaulted).
    _osc_heights: list = []
    _h_raw = raw.get("outside_corner_heights_ft")
    if isinstance(_h_raw, list) and _h_raw:
        for _h in _h_raw:
            try:
                _v = float(_h) if _h is not None else 0.0
            except (TypeError, ValueError):
                _v = 0.0
            _osc_heights.append(_v if _v > 0 else None)
        if not any(v for v in _osc_heights if v):
            _osc_heights = []
    _agg_gutter_runs: list = []
    for _r in (raw.get("gutter_runs") or []):
        if isinstance(_r, dict):
            try:
                _lf = float(_r.get("lf") or 0)
            except (TypeError, ValueError):
                _lf = 0.0
            if _lf > 0:
                _agg_gutter_runs.append(
                    {"label": str(_r.get("label") or "run"), "lf": _lf})

    measurements = {
        # RULING 7 (2026-08-01): full precision on the way in — no door
        # rounds at intake; the ORDER layer is the one rounding point.
        "siding_sqft": siding_sqft,
        # SEND-115 RULING 1 + SEND-116 ITEM 1: openings DEDUCT — full
        # area, no threshold — and this field carries the NET, but ONLY
        # from a gross that includes every face (an opening may only
        # deduct from a gross that includes the face it sits on; without
        # placement that means ALL faces). A refused deduction leaves the
        # field None and the line names the refusal. Nothing deducted →
        # None (the 08-08 no-alias pin holds: no gross number ever poses
        # as a +10% HOVER basis).
        "siding_with_openings_sqft": (
            _openings_deduction["net_sqft"]
            if _openings_deduction
            and not _openings_deduction.get("deduction_refused")
            and _openings_deduction.get("deducted_sqft") else None),
        **({"_openings_deduction": _openings_deduction}
           if _openings_deduction else {}),
        "opening_sqft": opening_sqft,
        "eaves_lf": float(raw.get("eaves_lf") or 0),
        "rakes_lf": float(raw.get("rakes_lf") or 0),
        # Boni ruling 1: porch plane ceiling feeds soffit; plane marker
        # tells the engine (and future overrides) the eave figure is a
        # roof-plane sum, not a wall derivation.
        **({"porch_ceiling_sqft": float(raw["porch_ceiling_sqft"])}
           if raw.get("porch_ceiling_sqft") else {}),
        **({"_eaves_plane_summed": True, "_roof_planes": raw.get("roof_planes")}
           if raw.get("_eaves_plane_summed") else {}),
        **({"_osc_corner_heights_ft": _osc_heights,
            "_osc_heights_source": "blueprint_dimensioned"}
           if _osc_heights else {}),
        **({"_gutter_runs": _agg_gutter_runs} if _agg_gutter_runs else {}),
        # TRADE-SPEC FIELDS FROM THE READ (ruled 2026-08-07): printed
        # values land; absent values are FLAGGED on the rail — the app
        # never silently holds a default as if it were read.
        **({"_overhang_in_printed": float(raw["eave_overhang_in"])}
           if raw.get("eave_overhang_in") else {}),
        **({"fascia_width_in": float(raw["fascia_width_in"]),
            "_fascia_src": "printed"} if raw.get("fascia_width_in") else {}),
        **({"_interior_doors_dropped": int(raw["_interior_doors_dropped"])}
           if raw.get("_interior_doors_dropped") else {}),
        **({"_gable_ends_plane_read": int(raw["_gable_ends_plane_read"])}
           if raw.get("_gable_ends_plane_read") else {}),
        "starter_lf": _starter_lf,
        "outside_corner_lf": float(
            raw.get("outside_corner_lf")
            or 4 * float(raw.get("avg_wall_height_ft") or 0)
        ),
        "inside_corner_lf": float(raw.get("inside_corner_lf") or 0),
        "opening_perimeter_lf": perimeter_lf,
        "opening_count": _bk["opening_count"],
        "window_count": (counts["window"]
                         if (counts["window"] or not _win_unread)
                         else None),
        **({"opening_marks_unread": _sched_unread}
           if _sched_unread else {}),
        "entry_door_count": counts["entry_door"],
        "patio_door_count": counts["patio_door"],
        "garage_door_count": counts["garage_door"],
        # Finding 6 (ruled 2026-08-01): door_count TOTAL lands on every
        # door — caulk-per-color + J-blocks read it.
        "door_count": _bk["door_count"],
        # Q7 (ruled 2026-07-27): vents/shutters wired on the blueprint door.
        "vent_count": int(raw.get("vent_unit_count") or 0),
        "shutter_count": int(raw.get("shutter_panel_count") or 0),
        # Q6 (ruled 2026-07-27): story-fee key aligned across all doors.
        **({"stories": str(raw.get("story_count"))} if raw.get("story_count") else {}),
        # Feed the Windows-workspace populator. Same shape HOVER produces.
        "windows": expanded_windows,
        # Surfaced fields for the preview UI
        "_ai_scale_confidence": raw.get("scale_confidence") or "low",
        "_ai_reference_used": "blueprint dimensions",
        "_ai_story_count": raw.get("story_count"),
        "_ai_avg_wall_height_ft": raw.get("avg_wall_height_ft"),
        "_ai_gable_sqft": round(gable_sqft, 1),
        "_ai_dormer_sqft": round(dormer_sqft, 1),
        "_ai_notes": raw.get("notes") or "",
        "_blueprint_sheets": raw.get("sheets_identified") or [],
        # Iter 79j.34 — Second producer of the 3D house JSON. Every
        # field below is READ from stated blueprint dimensions rather
        # than inferred from a photo, so the frontend renders the
        # source badges as "BLUEPRINT" (green/verified) instead of
        # "AI-derived" (amber). See HouseModel3D.buildHouseJson.
        "_source_kind": "blueprint",
    }
    # Shakedown provenance fields (2026-07-14)
    measurements["_starter_basis"] = _starter_basis
    measurements["_perimeter_lf"] = _perimeter_lf
    # STEP 2 (Howard ruled 2026-08-01): SOURCE PROVIDES IT → ENGINE CONSUMES
    # IT. Every figure the plans PRINT lands under the key the engine reads.
    # FOOTPRINT-PERIMETER KEY FIX (named item): the batten stacked-height
    # machinery reads `footprint_perimeter_ft`; the old `_perimeter_lf`-only
    # write was a silent key mismatch (writer-key == reader-key, pinned).
    if _perimeter_lf > 0:
        measurements["footprint_perimeter_ft"] = _perimeter_lf
    for _k in ("soffit_sqft", "level_frieze_lf", "sloped_frieze_lf",
               "drip_edge_lf", "total_trim_sqft", "footprint_area_sqft"):
        try:
            _v = float(raw.get(_k)) if raw.get(_k) is not None else None
        except (TypeError, ValueError):
            _v = None
        if _v and _v > 0:
            measurements[_k] = _v
    if raw.get("address"):
        measurements["address"] = str(raw["address"]).strip()[:200]
    # Class C (R6 sealed): read from explicit assignment, never inferred.
    measurements["opening_facade_assignments"] = raw.get("opening_facade_assignments") or []
    # wbw — measured sum of window bottom (sill) widths off the schedule.
    _wbw = sum(max(1, int(w.get("qty") or 1)) * float(w.get("width_in") or 0) / 12.0
               for w in windows)
    if _wbw > 0:
        measurements["window_bottom_width_total_lf"] = _wbw
    measurements["outside_corner_count"] = int(raw.get("outside_corner_count") or 0)
    measurements["inside_corner_count"] = int(raw.get("inside_corner_count") or 0)
    measurements["inside_corner_lf"] = float(raw.get("inside_corner_lf") or 0)
    if _osc_features:
        measurements["_ai_osc_features"] = _osc_features
    if gable_pitch_provenance:
        measurements["_gable_pitch_provenance"] = gable_pitch_provenance
    if appendage_faces:
        measurements["_ai_appendage_faces"] = appendage_faces
    # Known door-class residual (Phase 3 §4 analogue): 2+ entries and no
    # patio door usually means a slider was read as an entry.
    if counts["entry_door"] >= 2 and counts["patio_door"] == 0:
        measurements["_door_class_residual"] = True
        measurements["_ai_notes"] = (
            (str(raw.get("notes") or "") + " ").strip() + " "
            + "[class residual] 2+ entry doors and no patio door read — "
            "verify slider classification against the door schedule."
        ).strip()

    # Iter 79j.34 — Roof type + dormer payload for the 3D viewer.
    # A wall with printed gable_triangle_height_ft > 0 → gable end.
    # Any wall with dormer_face_sqft > 0 → gable-shed-dormer.
    # Otherwise → hip (all four walls end flat at the eave).
    has_dormer = any(float(w.get("dormer_face_sqft") or 0) > 0 for w in walls)
    inferred_roof_type = "hip"
    if any_gable:
        inferred_roof_type = "gable-shed-dormer" if has_dormer else "gable"
    measurements["_ai_roof_type"] = inferred_roof_type
    measurements["_ai_roof_type_confidence"] = 1.0
    measurements["_ai_roof_type_reasoning"] = (
        "gable-end walls (gable_triangle_height_ft > 0) read directly from elevation sheets"
        if any_gable
        else "no gable triangles printed on any elevation → hip roof"
    )
    if has_dormer:
        # Pick the wall carrying the largest dormer area as the face.
        # Back-solve width from face_sqft / knee assuming a 4 ft
        # standard knee (matches HouseModel3D's default). Contractors
        # can override in the 3D panel.
        _dormer_wall = max(
            walls, key=lambda w: float(w.get("dormer_face_sqft") or 0),
        )
        _face_sqft = float(_dormer_wall.get("dormer_face_sqft") or 0)
        _knee = 4.0
        _width = max(6.0, _face_sqft / _knee) if _face_sqft > 0 else 12.0
        measurements["_ai_dormer"] = {
            "face": (_dormer_wall.get("label") or "front").lower(),
            "width_ft": round(_width, 1),
            "knee_wall_height_ft": _knee,
            "offset_x_ft": 0.0,
        }
    else:
        measurements["_ai_dormer"] = None

    # Iter 79j.34 — Materialize a `raw.openings[]` list in the same
    # shape the AI Photo Measure emits, so HouseModel3D can consume
    # both producers without a schema fork. Blueprint schedules
    # don't record per-wall assignment for each mark, so we default
    # every opening to the front elevation — contractors can move
    # them in the AI Measure modal's wall dropdown. Style is derived
    # from `type_hint`.
    _hint_to_style = {
        "single_hung":  "Single Hung",
        "double_hung": "Double Hung",
        "casement":    "Casement",
        "slider":      "2-Lite Slider",
        "picture":     "Picture",
        "fixed":       "Picture",
        "awning":      "Awning",
    }
    _hint_to_door_type = {
        "entry":          "entry_door",
        "patio_slider":   "patio_door",
        "patio_french":   "patio_door",
        "garage":         "garage_door",
    }
    derived_openings = []
    _valid_walls = {"front", "back", "left", "right"}
    _placement_defaulted = 0

    def _opening_wall(row):
        # Shakedown addendum fix (7): per-elevation placement from the
        # elevation sheets; defaulting to front is FLAGGED, never silent.
        elev = str(row.get("elevation") or "").strip().lower()
        return (elev, True) if elev in _valid_walls else ("front", False)

    for win in windows:
        try:
            qty = max(1, int(win.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        style = _hint_to_style.get((win.get("type_hint") or "").lower(), "")
        _wall, _placed = _opening_wall(win)
        for _ in range(qty):
            if not _placed:
                _placement_defaulted += 1
            derived_openings.append({
                "type": "window",
                "style": style,
                "style_confidence": 100 if style else 0,
                "width_in": float(win.get("width_in") or 0),
                "height_in": float(win.get("height_in") or 0),
                "wall": _wall,
                "placement_source": "elevation" if _placed else "default",
                "on_dormer": False,
            })
    for d in doors:
        try:
            qty = max(1, int(d.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        door_type = _hint_to_door_type.get((d.get("type_hint") or "").lower(), "entry_door")
        _wall, _placed = _opening_wall(d)
        for _ in range(qty):
            if not _placed:
                _placement_defaulted += 1
            derived_openings.append({
                "type": door_type,
                "style": "",
                "style_confidence": 0,
                "width_in": float(d.get("width_in") or 0),
                "height_in": float(d.get("height_in") or 0),
                "wall": _wall,
                "placement_source": "elevation" if _placed else "default",
                "on_dormer": False,
            })
    # Mutate `raw` in place so the caller emits `raw_ai.openings` to
    # the frontend without a second code path.
    raw["openings"] = derived_openings
    measurements["_opening_placement_defaulted"] = _placement_defaulted

    # Ruling (2026-07-15, window-regression disposition): blueprint-sourced
    # openings ride the SAME confirm-openings ratification card the photo
    # path uses — sheet references stand in for photo crops. One row per
    # schedule mark row; `photo_idx` points at the schedule (or floor-plan)
    # sheet so the card links the governing sheet image.
    _sheets = raw.get("sheets_identified") or []

    def _first_page_idx(kind, skip_foundation=False):
        for s in _sheets:
            try:
                pg = int(s.get("page"))
            except (TypeError, ValueError):
                continue
            if str(s.get("useful_for") or "") != kind or pg < 1:
                continue
            if skip_foundation and "foundation" in str(s.get("sheet_title") or "").lower():
                continue
            return pg - 1  # pages are 1-based; page_paths are 0-based
        return None

    _sheet_idx = _first_page_idx("schedule")
    if _sheet_idx is None:
        # The first-floor plan carries the window/door schedules on
        # residential sets — the foundation plan does not.
        _sheet_idx = _first_page_idx("floor_plan", skip_foundation=True)
    if _sheet_idx is None:
        _sheet_idx = _first_page_idx("floor_plan")

    def _sched_row(row, rtype, style):
        try:
            qty = max(1, int(row.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        w_in = float(row.get("width_in") or 0)
        h_in = float(row.get("height_in") or 0)
        mark = str(row.get("id") or "").strip()
        elev = str(row.get("elevation") or "").strip().lower()
        # PRINT BOTH (ruled 2026-08-07): the printed schedule string is
        # the authority; a catalog size prints BESIDE it, never over it.
        printed = str(row.get("printed_size") or "").strip()
        catalog = str(row.get("catalog_size") or "").strip()
        label = (f"{mark} · " if mark else "")
        label += f"{printed} = {w_in:g}×{h_in:g} in" if printed else f"{w_in:g}×{h_in:g} in"
        if catalog:
            label += f" · catalog {catalog}"
        return {
            "elevation": elev if elev in _valid_walls else "unknown",
            "type": rtype,
            "style": style,
            "width_in": w_in,
            "height_in": h_in,
            "count": qty,
            "size_label": label,
            **({"printed_size": printed} if printed else {}),
            **({"catalog_size": catalog} if catalog else {}),
            "locations": ([{"photo_idx": _sheet_idx, "bbox": None}] if _sheet_idx is not None else []),
            "mark": mark,
            "source": "blueprint_schedule",
        }

    measurements["_ai_openings_schedule"] = [
        _sched_row(win, "window", _hint_to_style.get((win.get("type_hint") or "").lower(), ""))
        for win in windows
    ] + [
        _sched_row(d, _hint_to_door_type.get((d.get("type_hint") or "").lower(), "entry_door"), "")
        for d in doors
    ]

    # Iter 79j.34 sanity reconciliation — REWIRED (ruled 2026-08-01, step 1,
    # no-fourth-copy): the old block re-walked walls[] with its OWN copy of
    # the formula (0.5 gable, its own pct clamp) — the drift detector had
    # itself drifted. It now recomputes through the ONE shared walk; a
    # >2% delta can only mean someone forked the aggregation math again.
    _sanity = staging.walk_walls(walls, gable_rise_fn=_gable_rise,
                                 refused_faces=_refused_faces)
    threed_sqft = (_sanity["siding_sqft"] + _sanity["gable_sqft"]
                   + _sanity["dormer_sqft"] + appendage_sqft)
    if siding_sqft > 0:
        _delta_pct = 100.0 * abs(threed_sqft - siding_sqft) / siding_sqft
        if _delta_pct > 2.0:
            measurements["_source_reconciliation_warning"] = (
                f"3D-derived siding {threed_sqft:.0f} ft² vs blueprint takeoff "
                f"{siding_sqft:.0f} ft² ({_delta_pct:.1f}% delta) — extraction "
                f"disagrees with itself, verify walls[] before quoting."
            )
    # Iter 78z (P1.2) — Per-elevation profile breakdown so the catalog
    # mapper can split siding into per-profile SKU lines AND so the
    # frontend can render a per-elevation breakdown card. Mirrors the
    # AI Measure aggregator (see routes/ai_measure.py).
    try:
        from profile_callouts import breakdown_walls_by_profile, apply_annotations_to_breakdown
        breakdown = breakdown_walls_by_profile(walls, refused_faces=_refused_faces)
        breakdown = apply_annotations_to_breakdown(breakdown, annotations)
        measurements["_per_elevation_breakdown"] = breakdown["per_elevation"]
        measurements["_per_profile_sqft"] = breakdown["per_profile_sqft"]
        measurements["_faces_not_derivable"] = breakdown.get("faces_not_derivable") or []
    except Exception:
        measurements["_per_elevation_breakdown"] = []
        measurements["_per_profile_sqft"] = {}
        measurements["_faces_not_derivable"] = []
    # RULINGS CC + DD + EE (send-24/25): garage-side contradiction detector
    # and footprint closure. DD now WIRED — refused faces above go NOT
    # DERIVABLE through the derivation and the report field drives the
    # quote-gate blocker (gates.footprint_does_not_close).
    measurements["_garage_side_verdict"] = _garage_verdict
    measurements["_footprint_closure"] = _closure
    # SEND-48 zone binding: the per-face walk detail rides the
    # measurements so a zone write can capture the ONE surface it
    # supersedes (body or gable, derived value or named refusal).
    measurements["_wall_walk_detail"] = _walk["detail"]
    return measurements


@router.post("/ai-blueprint")
async def ai_blueprint(
    file: Optional[UploadFile] = File(None),
    files: list[UploadFile] = File(default=[]),
    address: Optional[str] = Form(None),
    overhang_in: float = Form(12.0),
    max_pages: int = Form(DEFAULT_MAX_PAGES),
    # Iter 57r — Resume support
    estimate_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """Read a blueprint set and return a takeoff in the same shape AI Measure
    produces. Accepts either a multi-page PDF (`file`) or several scanned
    image sheets (`files`). At least one of the two must be present."""
    if max_pages <= 0 or max_pages > MAX_PAGES_HARD:
        max_pages = DEFAULT_MAX_PAGES

    image_payloads: list[bytes] = []

    # Iter 78z+ (Blueprint annotator) — also persist each rendered page
    # to UPLOAD_DIR so the frontend ProfileAnnotator can display them
    # back to the contractor. Same pattern as AI Measure's photo_paths.
    from config import UPLOAD_DIR  # local import to dodge cycle
    from upload_store import save_blob  # Iter 78z+++ — durable backing store
    page_paths: list[str] = []
    # MUV S2 (2026-08-13) — record the render DPI as EVIDENCE, not an
    # assumption. PDF pages are rasterised at PDF_RENDER_SCALE × 72 DPI
    # (deterministic); image scans have no knowable DPI. The Material
    # Zone editor reads this to convert a printed scale fraction
    # (3/16"=1'-0") to feet-per-pixel; when it is None the printed-scale
    # path REFUSES and the user must trace a calibration by hand.
    _render_dpi: Optional[int] = None
    # SOURCE-RETENTION RULING (Howard, 2026-08-07): the original upload is
    # retained — always, every door, every file type. A derived artifact
    # never replaces its source.
    source_files: list[dict] = []
    source_probe: dict | None = None
    source_text_pages: list[str] = []
    _total_input_pages = 0  # every page the upload holds, pre-cap

    async def _retain_source(raw_bytes: bytes, ext: str, ctype: str,
                             kind: str, uploaded_as: str) -> None:
        src_name = f"bpsrc_{uuid.uuid4().hex}.{ext}"
        try:
            (UPLOAD_DIR / src_name).write_bytes(raw_bytes)
        except Exception:
            logger.exception("[ai-blueprint] source disk write failed for %s", src_name)
        await save_blob(src_name, raw_bytes, ctype)
        source_files.append({
            "name": src_name, "kind": kind,
            "bytes": len(raw_bytes), "uploaded_as": uploaded_as or "",
        })

    async def _persist_page_image(img_bytes: bytes) -> str:
        # Sniff magic bytes to pick the correct extension. PDF pages
        # come out as PNG (pypdfium2). Image-sheet uploads pass through
        # `_compress_for_claude` which JPEG-encodes. /api/uploads
        # serves raw bytes — extension matters for browser display.
        is_png = img_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        ext = "png" if is_png else "jpg"
        name = f"bp_{uuid.uuid4().hex}.{ext}"
        target = UPLOAD_DIR / name
        target.write_bytes(img_bytes)
        # Iter 78z+++ — Mirror into MongoDB so the page survives any
        # disk wipe. Non-fatal on failure (disk is still primary).
        await save_blob(name, img_bytes, f"image/{ext}")
        return name

    # PDF path — render to PNGs
    if file is not None:
        ctype = (file.content_type or "").lower()
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty PDF upload")
        # Some browsers send application/octet-stream; sniff by header too.
        is_pdf = ctype in ACCEPTED_PDF_MIMES or raw[:5] == b"%PDF-"
        if not is_pdf:
            raise HTTPException(
                status_code=400,
                detail=f"Expected PDF for `file`, got {ctype!r}",
            )
        if len(raw) > MAX_BYTES_PER_FILE * 4:
            raise HTTPException(status_code=413, detail="PDF exceeds 64 MB limit")
        await _retain_source(raw, "pdf", "application/pdf", "pdf", file.filename)
        source_probe, source_text_pages = _probe_pdf_source(raw)
        page_pngs, _pdf_total_pages = _render_pdf_to_pngs(raw, max_pages)
        _render_dpi = round(72 * PDF_RENDER_SCALE)
        _total_input_pages += _pdf_total_pages
        for png in page_pngs:
            try:
                page_paths.append(await _persist_page_image(png))
            except Exception:
                # If disk write fails we still want Claude to see the
                # page — we just lose the annotator preview for it.
                page_paths.append("")
        image_payloads.extend(page_pngs)

    # Image-scan path
    if files:
        for f in files:
            ctype = (f.content_type or "").lower()
            if ctype not in ACCEPTED_IMG_MIMES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type {ctype!r} for `files` — use JPG, PNG, or WEBP",
                )
            raw = await f.read()
            if not raw:
                continue
            if len(raw) > MAX_BYTES_PER_FILE:
                raise HTTPException(status_code=413, detail="Plan sheet exceeds 16 MB limit")
            _img_ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(ctype, "bin")
            await _retain_source(raw, _img_ext, ctype, "image", f.filename)
            _total_input_pages += 1
            # Same Anthropic 10 MB base64 cap — compress before queuing.
            compressed = _compress_for_claude(raw)
            image_payloads.append(compressed)
            # Persist a copy for the annotator UI. We save the COMPRESSED
            # version since that's what Claude sees — keeps box coords
            # aligned with what was analyzed.
            try:
                page_paths.append(await _persist_page_image(compressed))
            except Exception:
                page_paths.append("")

    if not image_payloads:
        raise HTTPException(
            status_code=400,
            detail="Provide either a PDF blueprint (`file`) or one or more image scans (`files`)",
        )
    if source_probe is None and any(s["kind"] == "image" for s in source_files):
        source_probe = {
            "kind": "image_scans", "pages": [], "text_pages": 0,
            "page_count": sum(1 for s in source_files if s["kind"] == "image"),
        }
    if len(image_payloads) > MAX_PAGES_HARD:
        # Already capped on the PDF side, but guard against image overflow too.
        image_payloads = image_payloads[:MAX_PAGES_HARD]
    # PAGE TRUNCATION IS A REGISTERED SEAM (ruled 2026-08-09 send 7): any
    # page the caps removed is COUNTED here and flagged LOUD on the card —
    # a dropped page is invisible to the read, the locator, and the census.
    if _total_input_pages > len(image_payloads):
        if source_probe is None:
            source_probe = {"kind": "unknown", "pages": [], "text_pages": 0,
                            "page_count": len(image_payloads)}
        source_probe["pages_truncated"] = {
            "total": _total_input_pages, "read": len(image_payloads)}
    # TOTAL-SIZE BUDGET (2026-08-09, with the raised page caps): keep the
    # whole request under Anthropic's limit. Percent-based loc boxes are
    # scale-invariant, so a tighter recompress never breaks the overlay.
    _TOTAL_RAW_BUDGET = 24_000_000
    _total_bytes = sum(len(b) for b in image_payloads)
    if _total_bytes > _TOTAL_RAW_BUDGET:
        _per = max(900_000, _TOTAL_RAW_BUDGET // max(len(image_payloads), 1))
        logger.info("[ai-blueprint] recompressing %d pages (%d bytes) to ~%d/page",
                    len(image_payloads), _total_bytes, _per)
        image_payloads = [_compress_for_claude(b, max_raw_bytes=_per)
                          for b in image_payloads]

    api_key, transport = _resolve_blueprint_key()

    user_id = user["id"]
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    # Iter 57q-bp — async launcher pattern. Same fix as the AI Measure
    # route: synchronous Claude calls on big blueprint sets were
    # exceeding the Kubernetes ingress timeout (~100 s) and triggering
    # the Cloudflare 524 error. Now the route persists a `running` doc
    # and returns a run_id immediately; the worker writes the result
    # back when Claude finishes (no time cap).
    await db.ai_blueprint_runs.insert_one({
        "run_id": run_id,
        "user_id": user_id,
        "estimate_id": estimate_id,
        "status": "running",
        "stage": "starting",
        "page_count": len(image_payloads),
        # Iter 78z+ — persisted page filenames (one per rendered/uploaded
        # blueprint page) so the ProfileAnnotator UI can display them
        # for box-tagging. Order matches `image_payloads` (and therefore
        # photos[*].index in Claude's output).
        "page_paths": ",".join(p for p in page_paths if p),
        "render_dpi": _render_dpi,
        # SOURCE-RETENTION RULING (2026-08-07) — originals + native-text probe.
        "source_files": source_files,
        "source_probe": source_probe,
        "source_text_pages": source_text_pages,
        "address": address,
        "transport": transport,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "result": None,
        "error": None,
    })
    asyncio.create_task(_execute_ai_blueprint_worker(
        run_id=run_id,
        image_payloads=image_payloads,
        api_key=api_key,
        user_id=user_id,
        address=address,
        overhang_in=overhang_in,
        estimate_id=estimate_id,
        transport=transport,
    ))
    return {
        "run_id": run_id,
        "status": "running",
        "stage": "starting",
        "pages_queued": len(image_payloads),
        # Iter 78z+ — return the persisted page filenames so the
        # frontend can hand them to the ProfileAnnotator immediately
        # (no need to wait for the worker to finish).
        "page_paths": ",".join(p for p in page_paths if p),
        "source_probe": source_probe,
    }


# Iter 78z+ — Re-run a previous blueprint launch using the CACHED page
# bytes. Lets the contractor save profile annotations and immediately
# kick off a fresh Claude pass without re-uploading the PDF. New
# run_id is returned (history of previous runs is preserved on the
# original doc).
@router.post("/ai-blueprint/rerun/{prev_run_id}")
async def ai_blueprint_rerun(
    prev_run_id: str,
    body: dict | None = None,
    user: dict = Depends(get_current_user),
):
    prev = await db.ai_blueprint_runs.find_one({"run_id": prev_run_id})
    if not prev:
        raise HTTPException(status_code=404, detail="Previous run not found")
    user_id = user["id"]
    if prev.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your run")

    page_paths_str = prev.get("page_paths") or ""
    paths = [p.strip() for p in page_paths_str.split(",") if p.strip()]
    if not paths:
        raise HTTPException(
            status_code=400,
            detail="No cached blueprint pages on this run — re-upload to use rerun",
        )
    from config import UPLOAD_DIR  # local import to dodge cycle
    image_payloads: list[bytes] = []
    new_page_paths: list[str] = []
    for name in paths:
        target = UPLOAD_DIR / name
        if not target.exists():
            continue
        image_payloads.append(target.read_bytes())
        new_page_paths.append(name)
    if not image_payloads:
        raise HTTPException(
            status_code=400,
            detail="Cached blueprint pages are no longer on disk — re-upload",
        )

    api_key, transport = _resolve_blueprint_key()

    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    # Comparison harness (Howard's ruling 2026-07-15: KEEP, admin-gated
    # permanently — future comparison rounds are inevitable and the
    # harness stays one config away from firing). INTERNAL-ONLY, owner
    # role, allowlisted candidates — never a user-facing dropdown
    # (model-dropdown policy ruling stands).
    _COMPARISON_MODELS = {"claude-opus-4-5-20251101", "claude-fable-5"}
    model_name = MODEL_NAME
    requested = str((body or {}).get("model_key") or "").strip()
    if requested:
        if user.get("role") != "owner" or requested not in _COMPARISON_MODELS:
            raise HTTPException(status_code=403, detail="Model override not permitted")
        model_name = requested
    address = prev.get("address")
    estimate_id = prev.get("estimate_id")
    # Default overhang we surfaced on the previous worker call. Stored on
    # the result doc; fall back to the schema default (12 in) when absent.
    prev_overhang = 12.0
    try:
        prev_result_meas = ((prev.get("result") or {}).get("measurements") or {})
        if prev_result_meas.get("overhang_in") is not None:
            prev_overhang = float(prev_result_meas["overhang_in"])
    except Exception:
        prev_overhang = 12.0

    await db.ai_blueprint_runs.insert_one({
        "run_id":      run_id,
        "user_id":     user_id,
        "estimate_id": estimate_id,
        "status":      "running",
        "stage":       "starting",
        "page_count":  len(image_payloads),
        "page_paths":  ",".join(new_page_paths),
        "render_dpi":  prev.get("render_dpi"),
        "address":     address,
        "rerun_of":    prev_run_id,
        "source_files": prev.get("source_files") or [],
        "source_probe": prev.get("source_probe"),
        "source_text_pages": prev.get("source_text_pages") or [],
        "model_requested": model_name,
        "transport":   transport,
        "created_at":  now,
        "updated_at":  now,
        "completed_at": None,
        "result":      None,
        "error":       None,
    })
    asyncio.create_task(_execute_ai_blueprint_worker(
        run_id=run_id,
        image_payloads=image_payloads,
        api_key=api_key,
        user_id=user_id,
        address=address,
        overhang_in=prev_overhang,
        estimate_id=estimate_id,
        model_name=model_name,
        transport=transport,
    ))
    return {
        "run_id":       run_id,
        "status":       "running",
        "stage":        "starting",
        "pages_queued": len(image_payloads),
        "page_paths":   ",".join(new_page_paths),
        "rerun_of":     prev_run_id,
    }


@router.get("/ai-blueprint/status/{run_id}")
async def ai_blueprint_status(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """Poll the status of an async blueprint-read run. Mirrors the
    `/measure/ai-measure/status/{run_id}` shape."""
    doc = await db.ai_blueprint_runs.find_one({"run_id": run_id})
    _from_archive = False
    if not doc:
        # Artifact pin read-side: archived blueprint runs outlive the
        # TTL — serve them here too (fixture_runs, no TTL).
        from run_archive import find_archived_run
        doc = await find_archived_run({"run_id": run_id})
        _from_archive = doc is not None
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if doc.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your run")
    # ARCHIVE-ON-VIEW (ruled 2026-08-11, TTL incident #3): a run a human
    # has opened is a run someone is evaluating — it must not be reapable.
    from run_archive import archive_run_on_view, reap_time_for
    archived = _from_archive
    if not archived:
        archived = bool(await archive_run_on_view(
            doc, reason="view:blueprint-status"))
    from routes.ai_measure import strip_cost_keys
    created = doc.get("created_at")
    completed = doc.get("completed_at") or doc.get("updated_at")
    elapsed_ms = None
    if isinstance(created, datetime):
        ref = completed if isinstance(completed, datetime) else datetime.now(timezone.utc)
        elapsed_ms = int((ref - created).total_seconds() * 1000)
    reaped_at = reap_time_for("ai_blueprint_runs", created, archived=archived)
    result_payload = _with_readback(strip_cost_keys(doc.get("result")),
                                    source_probe=doc.get("source_probe"),
                                    stability=doc.get("stability"))
    # RUN IDENTITY ON THE CARD (Howard ruled 2026-08-09 send 6: "I cannot
    # see a4cbce91 anywhere in the UI — every walk instruction costs a
    # round trip"). The readback header prints run id + fired-at, and
    # (ruled 2026-08-11) the run's exact reap time unless archived.
    if isinstance(result_payload, dict) and isinstance(result_payload.get("readback"), dict):
        result_payload["readback"]["run"] = {
            "id": run_id,
            "at": created.isoformat() if isinstance(created, datetime) else created,
            "archived": archived,
            "reaped_at": reaped_at,
        }
    return {
        "run_id": run_id,
        "status": doc.get("status"),
        "stage": doc.get("stage"),
        "result": result_payload,
        "error": doc.get("error"),
        "elapsed_ms": elapsed_ms,
        "archived": archived,
        "reaped_at": reaped_at,
        "source_probe": doc.get("source_probe"),
        "source_files": doc.get("source_files"),
    }


@router.get("/ai-blueprint/diagnostics/{run_id}")
async def ai_blueprint_diagnostics(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """SEND-27 Item 3 — the plain diagnostic (GG / FF inputs / EE reasons)
    so Howard can verify in the browser without a database view. READ ONLY."""
    doc = await db.ai_blueprint_runs.find_one({"run_id": run_id})
    if not doc:
        from run_archive import find_archived_run
        doc = await find_archived_run({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if doc.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your run")
    result = doc.get("result") or {}
    # OCR may have moved off the run doc (Ruling GG size guard).
    ocr_by_page = None
    ref = ((result.get("raw_ai") or {}).get("_ocr_text_ref") or {})
    if ref.get("where") == "ai_blueprint_ocr":
        ocr = await db.ai_blueprint_ocr.find_one({"run_id": run_id}, {"_id": 0})
        ocr_by_page = (ocr or {}).get("by_page")
    from blueprint_diagnostics import build_blueprint_diagnostics, render_plain
    diag = build_blueprint_diagnostics(result, ocr_by_page)
    return {"run_id": run_id, "diagnostics": diag,
            "plain_text": render_plain(diag)}



@router.get("/ai-blueprint/latest-for-estimate/{estimate_id}")
async def ai_blueprint_latest_for_estimate(
    estimate_id: str,
    user: dict = Depends(get_current_user),
):
    """Iter 57r — same Resume support as the AI Measure endpoint.
    Returns the most recent blueprint run for this user+estimate."""
    user_id = user["id"]
    doc = await db.ai_blueprint_runs.find_one(
        {"user_id": user_id, "estimate_id": estimate_id},
        sort=[("created_at", -1)],
    )
    # Artifact pin read-side (24h TTL defusal — ruled 2026-07-20, same
    # pattern as _blueprint_dim_offers): when the live doc has reaped,
    # serve the CUT-archived copy from fixture_runs (no TTL). READ path
    # only — no writes, no new archival triggers.
    archived = False
    if not doc:
        from run_archive import find_archived_run
        doc = await find_archived_run(
            {"user_id": user_id, "estimate_id": estimate_id,
             "substrate": "ai_blueprint_runs"})
        archived = doc is not None
    if not doc:
        return {"run": None}
    # ARCHIVE-ON-VIEW (ruled 2026-08-11, TTL incident #3): opening the
    # estimate's latest run is a human view — archive it.
    from run_archive import archive_run_on_view, reap_time_for
    if not archived:
        archived = bool(await archive_run_on_view(
            doc, reason="view:blueprint-latest"))
    # Iter 57x — same offset-aware safety fix that ai_measure has.
    # Mongo returns naive datetimes by default which breaks the
    # subtraction against `datetime.now(timezone.utc)`.
    def _as_aware_utc(dt):
        if not isinstance(dt, datetime):
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    created = _as_aware_utc(doc.get("created_at"))
    completed = _as_aware_utc(doc.get("completed_at") or doc.get("updated_at"))
    from routes.ai_measure import strip_cost_keys
    now = datetime.now(timezone.utc)
    elapsed_ms = None
    age_seconds = None
    if created is not None:
        ref = completed if completed is not None else now
        elapsed_ms = int((ref - created).total_seconds() * 1000)
        age_seconds = int((now - created).total_seconds())
    reaped_at = reap_time_for("ai_blueprint_runs", created, archived=archived)
    result_payload = _with_readback(strip_cost_keys(doc.get("result")),
                                    source_probe=doc.get("source_probe"),
                                    stability=doc.get("stability"))
    # Run identity + reap time on the resume payload too (ruled
    # 2026-08-11) — the card must print expiry whichever door loaded it.
    if isinstance(result_payload, dict) and isinstance(result_payload.get("readback"), dict):
        result_payload["readback"]["run"] = {
            "id": doc.get("run_id"),
            "at": created.isoformat() if created is not None else None,
            "archived": archived,
            "reaped_at": reaped_at,
        }
    return {
        "run": {
            "run_id": doc.get("run_id"),
            "status": doc.get("status"),
            "stage": doc.get("stage"),
            "page_count": doc.get("page_count"),
            # Iter 78z+ — persisted page filenames so the frontend can
            # render them in the ProfileAnnotator on a resume.
            "page_paths": doc.get("page_paths") or "",
            # MUV S2 (2026-08-13) — render DPI evidence for the Material
            # Zone editor's printed-scale conversion (None ⇒ scan, no
            # knowable DPI ⇒ printed-scale path refuses, user traces).
            "render_dpi": doc.get("render_dpi"),
            # Read-side provenance (ruled 2026-07-20): True when served
            # from the CUT archive, or (2026-08-11) just archived on view.
            "archived": archived,
            # Exact reap time (ruled 2026-08-11) — None once archived.
            "reaped_at": reaped_at,
            "result": result_payload,
            "error": doc.get("error"),
            "elapsed_ms": elapsed_ms,
            "age_seconds": age_seconds,
            "source_probe": doc.get("source_probe"),
            "source_files": doc.get("source_files"),
        },
    }


async def sweep_orphaned_blueprint_runs() -> dict:
    """Boot-time dead-worker sweep (audit finding B1, ruled 2026-08-11).
    asyncio workers never survive their process — a status='running' doc
    at boot is a corpse. The old gap COMPOUNDED: the doc sat 'running'
    forever and the TTL then destroyed the evidence of the crash. The
    sweep flips to a class-5 error AND ARCHIVES the dead run into
    fixture_runs — a failed run is worth more than a successful one."""
    out = {"archived_dead": 0}
    from run_archive import archive_run_for_artifact
    async for doc in db.ai_blueprint_runs.find(
            {"status": "running"}, {"_id": 0, "run_id": 1}):
        now = datetime.now(timezone.utc)
        await db.ai_blueprint_runs.update_one(
            {"run_id": doc["run_id"]},
            {"$set": {
                "status": "error",
                "stage": "dead-worker",
                "error": ("The blueprint read worker died with the server "
                          "process (restart/crash) before finishing — "
                          "retry the run."),
                "error_kind": "dead_worker_boot_sweep",
                "completed_at": now,
                "updated_at": now,
            }})
        await archive_run_for_artifact(
            run_id=doc["run_id"], reason="dead-worker:boot-sweep")
        out["archived_dead"] += 1
    if out["archived_dead"]:
        logger.warning(
            "[ai-blueprint class-5] boot sweep flipped+archived %d dead run(s)",
            out["archived_dead"])
    return out


async def _execute_ai_blueprint_worker(
    *,
    run_id: str,
    image_payloads: list[bytes],
    api_key: str,
    user_id: str,
    address: Optional[str],
    overhang_in: float,
    estimate_id: Optional[str] = None,
    model_name: str = MODEL_NAME,
    transport: str = "emergent_proxy",
):
    """Background worker — runs the Claude blueprint read, aggregates,
    maps to lines + Vero/Mezzo openings, and writes the final result
    back to the run doc."""
    async def _set_stage(stage: str):
        await db.ai_blueprint_runs.update_one(
            {"run_id": run_id},
            {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc)}},
        )
    try:
        await _set_stage("claude")
        # Iter 78z+ (Annotations as Claude hints) — load + format
        # user-drawn boxes so Claude can use them as ground truth.
        annotations: dict | None = None
        if estimate_id:
            est_doc = await db.estimates.find_one(
                {"id": estimate_id},
                {"_id": 0, "profile_annotations": 1},
            )
            if est_doc:
                annotations = est_doc.get("profile_annotations") or None
        # Reuse the AI Measure hint formatter — single source of truth.
        from routes.ai_measure import _build_annotation_hint
        annotation_hint = _build_annotation_hint(annotations)

        image_contents = [
            ImageContent(image_base64=base64.b64encode(p).decode("ascii"))
            for p in image_payloads
        ] if transport != "anthropic_direct" else []
        session_id = f"ai-blueprint-{user_id}-{uuid.uuid4().hex[:8]}"

        prompt_parts: list[str] = [
            f"You are receiving {len(image_payloads)} plan sheet(s) as images.",
        ]
        if address:
            prompt_parts.append(f"Project address: {address}")
        prompt_parts.append(
            "Read the printed dimensions on the elevations + floor plan, "
            "and extract the window/door schedule if one is present. "
            "Return the JSON takeoff object now."
        )
        if annotation_hint:
            prompt_parts.append(annotation_hint)
        user_text = "\n".join(prompt_parts)
        # Iter 79e — same 4-min Claude wall-clock cap as the HOVER + AI
        # Measure workers. Stops the run doc from getting stuck at
        # `status: "running"` if Claude stalls on a big plan-sheet set.
        token_usage: dict | None = None
        if transport == "anthropic_direct":
            reply_text, token_usage, _stop = await _claude_direct_blueprint(
                api_key=api_key,
                model_name=model_name,
                image_payloads=image_payloads,
                user_text=user_text,
                timeout_s=240,
            )
        else:
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,
                system_message=SYSTEM_PROMPT,
            ).with_model("anthropic", model_name)
            reply_text = await asyncio.wait_for(
                chat.send_message(
                    UserMessage(text=user_text, file_contents=image_contents),
                ),
                timeout=240,
            )

        await _set_stage("aggregating")
        raw = _json_from_reply(reply_text or "")
        # ROOF GEOMETRY PASS (Boni second send): fire the focused read
        # only when garage evidence exists without a garage roof plane.
        # Failure never sinks the run — the main read stands.
        try:
            if _roof_pass_needed(raw):
                await _set_stage("roof_pass")
                idxs = _roof_pass_sheet_indexes(raw, len(image_payloads))
                pass_imgs = [image_payloads[i] for i in idxs] or image_payloads[:5]
                if transport == "anthropic_direct":
                    rp_text, rp_usage, _ = await _claude_direct_blueprint(
                        api_key=api_key, model_name=model_name,
                        image_payloads=pass_imgs,
                        user_text="Run the roof plane census and the full-outline corner walk on these sheets. Return the JSON now.",
                        timeout_s=180, system_text=ROOF_PASS_PROMPT,
                    )
                    if rp_usage and token_usage:
                        token_usage = {
                            "input_tokens": token_usage["input_tokens"] + rp_usage["input_tokens"],
                            "output_tokens": token_usage["output_tokens"] + rp_usage["output_tokens"],
                        }
                else:
                    rp_chat = LlmChat(
                        api_key=api_key,
                        session_id=f"{session_id}-roofpass",
                        system_message=ROOF_PASS_PROMPT,
                    ).with_model("anthropic", model_name)
                    rp_imgs = [ImageContent(image_base64=base64.b64encode(p).decode("ascii"))
                               for p in pass_imgs]
                    rp_text = await asyncio.wait_for(
                        rp_chat.send_message(UserMessage(
                            text="Run the roof plane census and the full-outline corner walk on these sheets. Return the JSON now.",
                            file_contents=rp_imgs)),
                        timeout=180,
                    )
                raw = _merge_roof_pass(raw, _json_from_reply(rp_text or ""))
        except Exception:
            logger.exception("[ai-blueprint] roof pass failed — main read stands")
        # Annotations already loaded above — pass through to the
        # breakdown overlay so the catalog mapper emits per-profile lines.
        # EVIDENCE-OR-NULL (ruled 2026-08-08, structural): enforced at the
        # seam — nothing downstream ever sees an unevidenced dimension.
        raw = _enforce_evidence_or_null(raw)
        # THE COUNT COLUMN GOVERNS COUNTS (ruled 2026-08-08, enforced
        # 2026-08-09): the prompt rule alone left the rerun symbol-
        # counting — now enforced at the seam. Per-sheet mark rows merge,
        # printed COUNT cells sum, an unread count contributes nothing.
        raw = _enforce_count_column(raw)
        # VISUAL AUDIT (same ruling, same build — one schema, one
        # renderer): precision labelling. Native text layer gives EXACT
        # boxes; vision boxes stay APPROXIMATE; failure never sinks the run.
        run_meta = None
        try:
            run_meta = await db.ai_blueprint_runs.find_one(
                {"run_id": run_id},
                {"_id": 0, "source_files": 1, "source_probe": 1, "rerun_of": 1})
            _exact_locate_evidence(raw.get("_dim_evidence") or {},
                                   (run_meta or {}).get("source_files") or [],
                                   (run_meta or {}).get("source_probe"))
        except Exception:
            logger.exception("[ai-blueprint] exact-locate failed — approximate boxes stand")
        # PAGE TRUNCATION RIDES THE READ (ruled 2026-08-09 send 7): the
        # endpoint counted what the caps removed; the ledger and the rail
        # carry it — never silent.
        try:
            _pt = ((run_meta or {}).get("source_probe") or {}).get("pages_truncated")
            if _pt and int(_pt.get("total") or 0) > int(_pt.get("read") or 0):
                raw["_pages_truncated"] = _pt
                seam_accounting.account(
                    raw, "pages_truncated",
                    [f"pages {int(_pt['read']) + 1}-{int(_pt['total'])} never rendered"],
                    kept=int(_pt["read"]))
        except Exception:
            logger.exception("[ai-blueprint] page-truncation accounting failed")
        # OCR-FOR-COORDINATES (ruled 2026-08-08): deterministic, local,
        # no extra model call. LOCATION ONLY — never value. Runs off the
        # event loop; failure never sinks the run.
        try:
            if raw.get("_dim_evidence"):
                # honest stage: this local OCR pass runs minutes on a
                # 10-page set — say so instead of sitting on "aggregating"
                await _set_stage("ocr_locate")
                await asyncio.to_thread(_ocr_locate_evidence,
                                        raw["_dim_evidence"],
                                        image_payloads, raw)
        except Exception:
            logger.exception("[ai-blueprint] ocr-locate failed — quote-only anchors stand")
        # UNVERIFIED EVIDENCE NULLS THE VALUE (Howard ruled 2026-08-12
        # send-8): "A LOCATING MATCH MUST SIT NEAR THE FEATURE IT CLAIMS
        # TO DIMENSION." A quote no locator can find near its feature
        # was FABRICATED — the value nulls. Evidence-or-null, extended
        # from "the number without a quote" to "the number whose quote
        # cannot locate near what it claims to dim." The seam books it.
        try:
            _null_unverified_quotes(raw)
        except Exception:
            logger.exception("[ai-blueprint] unverified-null pass failed")
        try:
            _one_source_one_path_guard(raw)
        except Exception:
            logger.exception("[ai-blueprint] one-source-one-path guard failed")
        # MARKS FACE THE LOCATOR TOO (ruled 2026-08-09): schedule-row
        # quotes searched on their own sheets; a row no quote of which
        # locates is dropped as fabricated; a fabricated size quote is
        # killed. Failure never sinks the run.
        try:
            await _set_stage("mark_locate")
            await asyncio.to_thread(_ocr_verify_marks, raw, image_payloads)
        except Exception:
            logger.exception("[ai-blueprint] mark-locate failed — rows stand")
        await _set_stage("aggregating")
        measurements = _aggregate_to_hover_shape(raw, annotations=annotations)
        # SPEC-FIELD PRECEDENCE (ruled 2026-08-07): a PRINTED overhang
        # beats the form default; the source is named either way.
        _printed_ov = measurements.get("_overhang_in_printed")
        if _printed_ov:
            measurements["overhang_in"] = float(_printed_ov)
            measurements["_overhang_src"] = "printed"
        else:
            measurements["overhang_in"] = float(overhang_in)
            measurements["_overhang_src"] = "form_default"

        await _set_stage("mapping")
        try:
            # THE CUT (ruled 2026-07-14, shakedown findings): lp_smart-tab
            # rows are ENGINE-OWNED — raw _build_lines output bypasses the
            # composition guard / per-system table / whole-piece rounding.
            # Blueprint results carry NO lp_smart lines; LP estimates
            # derive through assemble_lp_package via /lp-package/preview.
            _built = _build_lines(measurements)
            lines = [l for l in _built
                     if (l.get("tab") or "vinyl") != "lp_smart"]
            if len(lines) != len(_built):
                # SEAM ACCOUNTING (ruled 2026-08-09): THE CUT accounts
                # for what it removed.
                seam_accounting.account(
                    measurements, "lp_smart_lines_cut",
                    [str(l.get("name") or "?") for l in _built
                     if (l.get("tab") or "vinyl") == "lp_smart"])
        except Exception:
            lines = []
        try:
            vero_openings, mezzo_openings = _build_window_openings(measurements)
        except Exception:
            vero_openings, mezzo_openings = [], []

        cost_usd = None
        if token_usage:
            try:
                from routes.ai_measure import _price_for_model_id
                price = _price_for_model_id(model_name)
                if price:
                    cost_usd = round(
                        (token_usage["input_tokens"] / 1_000_000) * price["input"]
                        + (token_usage["output_tokens"] / 1_000_000) * price["output"],
                        4,
                    )
            except Exception:
                cost_usd = None

        result = {
            "measurements": {**measurements, "_run_id": run_id},
            "lines": lines,
            "vero_openings": vero_openings,
            "mezzo_openings": mezzo_openings,
            "raw_ai": raw,
            "model": model_name,
            "transport": transport,
            "token_usage": token_usage,
            "cost_usd": cost_usd,
            "model_config": {
                "model": model_name,
                "validation_status": (
                    MODEL_VALIDATION_STATUS if model_name == MODEL_NAME
                    else "controlled-comparison override (pre-registered 2026-07-14)"
                ),
                "prompt_hash": _blueprint_prompt_hash(),
                "transport": transport,
            },
            "session_id": session_id,
            "pages_processed": len(image_payloads),
        }
        # DETERMINISM GATE (ruled 2026-08-08): a rerun is compared to the
        # run it re-read. STABILITY ONLY — agreement is never correctness,
        # and a compare failure never sinks the run.
        stability = None
        try:
            prev_id = (run_meta or {}).get("rerun_of")
            if prev_id:
                prev = await db.ai_blueprint_runs.find_one({"run_id": prev_id})
                if not prev:
                    from run_archive import find_archived_run
                    prev = await find_archived_run({"run_id": prev_id})
                prev_raw = ((prev or {}).get("result") or {}).get("raw_ai")
                if isinstance(prev_raw, dict):
                    stability = compute_read_stability(prev_raw, raw)
        except Exception:
            logger.exception("[ai-blueprint] stability compare failed — served without")
        # RULING GG (send-25) — persist OCR text. Default: onto the run doc.
        # SIZE GUARD (Howard: separate collection over truncation): when the
        # OCR blob would push the run doc toward BSON's 16MB ceiling it moves
        # to its own collection keyed by run_id; a pointer stays on the run
        # doc. Truncation is a LAST RESORT — loud and specific (names pages +
        # dropped counts) so a later lookup that could have hit a dropped run
        # returns UNVERIFIED, never NOT LOCATED ("not stored" ≠ "not on the
        # sheet").
        try:
            await _persist_ocr_text(run_id, raw)
        except Exception:
            logger.exception("[ai-blueprint] OCR-text persist failed — read stands without it")
        # INT-KEY WRITE GUARD (send-25): recursive key coercion at THE single
        # write boundary; every fire recorded on the doc so an int-keyed
        # source stays visible instead of being laundered.
        _key_fired: list = []
        result = _coerce_bson_keys(result, "result", _key_fired)
        if _key_fired:
            result.setdefault("measurements", {})["_int_key_coercions"] = _key_fired
            logger.warning("[ai-blueprint] int-key coercion fired at write boundary: %s",
                           _key_fired)
        await db.ai_blueprint_runs.update_one(
            {"run_id": run_id},
            {"$set": {
                "status": "done",
                "stage": "done",
                "stability": stability,
                "result": result,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        # AUTO-ARCHIVE ON PROTECTED ESTIMATES (ruled 2026-08-11, TTL
        # incident #3): a run on a protected estimate is never reapable.
        from run_archive import maybe_archive_protected
        await maybe_archive_protected(run_id)
    except Exception as e:
        logger.exception("[ai-blueprint] worker failed for run_id=%s", run_id)
        await db.ai_blueprint_runs.update_one(
            {"run_id": run_id},
            {"$set": {
                "status": "error",
                "stage": "error",
                "error": f"AI blueprint read failed: {e}",
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        # A FAILED run on a protected estimate is worth more than a
        # successful one — archive it too (ruled 2026-08-11).
        from run_archive import maybe_archive_protected
        await maybe_archive_protected(run_id)
