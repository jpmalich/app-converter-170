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
from routes.hover import _build_lines, _build_window_openings
import measure_staging as staging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/measure", tags=["measure"])

ACCEPTED_IMG_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ACCEPTED_PDF_MIMES = {"application/pdf"}
MAX_PAGES_HARD = 20
DEFAULT_MAX_PAGES = 12
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
     "qty": 1,                            // TOTAL across ALL schedule sheets for this mark
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
    {"label": "main" | "garage" | "porch" | "<other, verbatim from plan>",
     "eave_lf": number,            // horizontal eave (gutter) run this plane contributes, all sides summed
     "rake_lf": number,            // TOTAL sloped rake edge on this plane. A plane with a GABLE END has rakes — NEVER 0 for a gabled plane. Per gable end: 2 × √((gable_width/2)² + ((gable_width/2) × pitch_rise/12)²). READ THE ELEVATIONS: an attached garage wing with ITS OWN gable — including an intersecting / double gable where the garage roof meets the main roof — contributes rake edges the main-rectangle walk cannot see. If any elevation shows a separate garage gable, that plane's rake_lf MUST come back non-zero.
     "gable_ends": number,          // how many gable ends (triangular end faces) this plane carries: 0 for a hip or shed plane, 1 per gable end. The app reports the total across planes.
     "is_porch": true | false,
     "porch_ceiling_sqft": number,  // porch planes only: ceiling area under the roof (soffit material, read porch depth × length from the floor plan); 0 otherwise
     "porch_width_ft": DIM | null,     // porch planes only: {"v","page","from"} — the porch's PRINTED floor-plan width (the side along the house wall). null when not dimensioned — NEVER derived from the area (an area does not determine a shape, ruled 2026-08-07)
     "porch_depth_ft": DIM | null      // porch planes only: {"v","page","from"} — PRINTED depth (out from the wall). null when not dimensioned — NEVER √area, never a guess
    }
  ],
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
    {"label": "<front|back|left|right|porch|...>", "lf": number}
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

JOB 1 — ROOF PLANE CENSUS. List EVERY roof plane pair that carries its own eave (gutter/fascia) line: the MAIN roof, the ATTACHED GARAGE roof (the area table and a second ridge/truss field on the roof plan prove it exists — a "3 CAR GARAGE" on the floor plan ALWAYS has a roof over it), PORCH roofs (mono/shed count too), and any secondary cross-gable. A plane with a GABLE END has rake_lf — per gable end: 2 × √((gable_width/2)² + ((gable_width/2) × rise/12)²). An attached garage ending in its own gable (including an intersecting/double gable where the garage roof meets the main roof) MUST come back with non-zero rake_lf and gable_ends.
PITCH-TRIANGLE NOTATION: the triangle marks print the RUN (always 12) on one leg and the RISE on the other — a mark showing 12 and 7 means 7/12, NEVER 12/12 (only 12/12 when BOTH legs print 12). Report the MAIN body pitch in roof_pitch; name secondary pitches in notes.

JOB 2 — FULL-OUTLINE CORNER WALK. Walk the COMPLETE dimensioned floor-plan outline clockwise — garage wing and porch projection INCLUDED, never just the main rectangle. At every direction change: OUTSIDE corner (turns away from interior) or INSIDE corner (notch/armpit). INVARIANT: outside − inside MUST equal 4; re-walk if not. outside_corner_lf = SUM of each corner's OWN trim height (1-story garage-wing corners run the garage eave height; 2-story corners the full height — NEVER count × average height). ALSO return outside_corner_heights_ft: one entry PER corner in walk order — the corner joins TWO walls, report the TALLER wall's height, run to the EAVE the corner trim dies into (on a gable end the corner runs to the EAVE, never an area÷width figure); null when no printed dimension resolves that corner — never average or guess.

JOB 3 — GUTTER RUN INVENTORY. List each CONTINUOUS eave run that carries gutter, walked along the FACADES (front/back/left/right/porch). ONE entry per continuous run: where a lower roof's eave (garage bump-out) is flush and continuous with the run beside it, that is ONE run counted ONCE — never re-list a segment inside a run already listed. A porch lists only the eave sides that actually carry gutter. [] when the drawings don't resolve the runs.

Return ONLY this JSON, no explanation:
{
  "roof_pitch": "<main body pitch, e.g. '7/12'>",
  "roof_planes": [
    {"label": "main" | "garage" | "porch" | "<other>",
     "eave_lf": number, "rake_lf": number, "gable_ends": number,
     "is_porch": true | false, "porch_ceiling_sqft": number}
  ],
  "outside_corner_count": number, "outside_corner_lf": number,
  "outside_corner_heights_ft": [number | null],
  "inside_corner_count": number, "inside_corner_lf": number,
  "gutter_runs": [{"label": "<front|back|left|right|porch|...>", "lf": number}],
  "notes": "<secondary pitches, anything illegible>"
}"""

_PITCH_RE = re.compile(r"^\d{1,2}(\.\d+)?/12$")


def _merge_roof_pass(raw: dict, rp: dict) -> dict:
    """Pure, conservative merge of the focused roof pass into the main
    read. Mutates and returns `raw`. Provenance lands in raw['_roof_pass']."""
    if not isinstance(rp, dict):
        return raw
    accepted: dict = {}
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
    elif new_g and old_g and float(new_g.get("rake_lf") or 0) > 0 \
            and float(old_g.get("rake_lf") or 0) == 0 \
            and int(old_g.get("gable_ends") or 0) == 0:
        # SURGICAL: the full-context read keeps its eave figure; the
        # focused read (which actually looked at the gable) supplies
        # ONLY the rake edges + gable-end census it missed.
        old_g["rake_lf"] = float(new_g["rake_lf"])
        old_g["gable_ends"] = int(new_g.get("gable_ends") or 0)
        accepted["garage_rakes"] = {"rake_lf": old_g["rake_lf"],
                                    "gable_ends": old_g["gable_ends"]}
    pitch = str(rp.get("roof_pitch") or "").strip()
    if pitch and _PITCH_RE.match(pitch) and pitch != str(raw.get("roof_pitch") or ""):
        raw["roof_pitch"] = pitch
        accepted["roof_pitch"] = pitch
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
    except (TypeError, ValueError):
        oc = ic = 0
        oclf = 0.0
        old_oc = 0
    if oc > 0 and (oc - ic) == 4 and oc >= old_oc and oclf > 0:
        raw["outside_corner_count"] = oc
        raw["outside_corner_lf"] = oclf
        raw["inside_corner_count"] = ic
        if rp.get("inside_corner_lf"):
            raw["inside_corner_lf"] = float(rp["inside_corner_lf"])
        accepted["corners"] = {"outside": oc, "inside": ic, "outside_lf": oclf}
        # PER-CORNER HEIGHTS (ruled 2026-08-06): ride ONLY with an accepted
        # walk and only when one entry per counted corner came back.
        hs = rp.get("outside_corner_heights_ft")
        if isinstance(hs, list) and len(hs) == oc:
            raw["outside_corner_heights_ft"] = hs
            accepted["corner_heights"] = hs
    # GUTTER RUN INVENTORY (ruled 2026-08-06): conservative — only fills
    # a read that has none.
    runs = [r for r in (rp.get("gutter_runs") or []) if isinstance(r, dict)]
    if runs and not raw.get("gutter_runs"):
        raw["gutter_runs"] = runs
        accepted["gutter_runs"] = runs
    raw["_roof_pass"] = {"accepted": accepted, "notes": rp.get("notes") or ""}
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
    return all(float(p.get("rake_lf") or 0) == 0
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
    if unread:
        # NO-SOURCE IS A FIRST-CLASS STATE (Visual Audit design req 3,
        # ruled 2026-08-08): dims the read abstained on are NAMED, not
        # omitted — "no source on the drawing" renders as clearly as a
        # highlight.
        raw["_dim_unread"] = unread
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
    if not isinstance(evidence, dict) or not evidence:
        return
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
    if not wanted:
        return
    import numpy as np
    misses = []
    for page, entries in wanted.items():
        try:
            with Image.open(io.BytesIO(image_payloads[page - 1])) as im:
                w, h = im.size
                arr = np.array(im.convert("RGB"))
            runs = _ocr_runs(arr)
        except Exception:
            logger.exception("[ai-blueprint] OCR failed on page %s — quote anchors stand", page)
            continue
        pending = []
        for path, s, nq in entries:
            rect = _ocr_match(runs, nq)
            if rect:
                x0, y0, x1, y1 = rect
                s["loc"] = {"x_pct": round(x0 / w * 100, 2),
                            "y_pct": round(y0 / h * 100, 2),
                            "w_pct": round(max(x1 - x0, 1) / w * 100, 2),
                            "h_pct": round(max(y1 - y0, 1) / h * 100, 2)}
                s["precision"] = "ocr"
            else:
                pending.append((path, s, nq))
        # Rotated passes — only when the upright pass left misses.
        for k in (1, 3):
            if not pending:
                break
            try:
                rruns = _ocr_runs(np.rot90(arr, k))
            except Exception:
                continue
            still = []
            for path, s, nq in pending:
                rect = _ocr_match(rruns, nq)
                if rect:
                    x0r, y0r, x1r, y1r = rect
                    if k == 1:      # CCW: upright x = W-1-yr, y = xr
                        x0, x1 = w - 1 - y1r, w - 1 - y0r
                        y0, y1 = x0r, x1r
                    else:           # CW:  upright x = yr, y = H-1-xr
                        x0, x1 = y0r, y1r
                        y0, y1 = h - 1 - x1r, h - 1 - x0r
                    s["loc"] = {"x_pct": round(x0 / w * 100, 2),
                                "y_pct": round(y0 / h * 100, 2),
                                "w_pct": round(max(x1 - x0, 1) / w * 100, 2),
                                "h_pct": round(max(y1 - y0, 1) / h * 100, 2)}
                    s["precision"] = "ocr"
                else:
                    still.append((path, s, nq))
            pending = still
        for path, s, nq in pending:
            misses.append({"path": path, "page": page,
                           "from": str(s.get("from") or ""),
                           "rotations_checked": True})
    if misses:
        raw["_ocr_quote_misses"] = misses


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

    # PER-WALL SEGMENTS (ruled 2026-08-07): segment widths must sum to
    # the wall width — a mismatched walk is named, and the siding math
    # falls back to the rectangle rather than consuming corrupt segments.
    # An UNDIMENSIONED section (height null — the drawing holds no
    # number) is a FLAG, never a guess (ruled 2026-08-08).
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
    if planes and walls and plane_gables != wall_gables:
        flags.append({
            "code": "gable_census_mismatch", "level": "loud",
            "vars": {"planes": plane_gables, "walls": wall_gables}})

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
    rect = (max(widths.get("front", 0), widths.get("back", 0))
            * max(widths.get("left", 0), widths.get("right", 0)))
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
    sc = str(raw.get("scale_confidence") or "")
    if sc and sc != "high":
        rail.append({"level": "warn", "code": "scale_confidence", "text": sc})
    rp = raw.get("_roof_pass") or {}
    for key in sorted((rp.get("accepted") or {}).keys()):
        rail.append({"level": "info", "code": "roof_pass_merge", "text": key})
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
    _fw = _num(raw.get("fascia_width_in"))
    if _fw > 0:
        rail.append({"level": "info", "code": "fascia_printed", "text": f"{_fw:g}"})
    else:
        rail.append({"level": "warn", "code": "fascia_default"})
    _idd = raw.get("_interior_doors_dropped")
    if _idd:
        rail.append({"level": "warn", "code": "interior_doors_dropped",
                     "text": str(_idd)})
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


def _render_pdf_to_pngs(raw_pdf: bytes, max_pages: int) -> list[bytes]:
    """Rasterize a PDF into a list of PNG byte-strings, one per page,
    capped at `max_pages`. Each page is rendered at PDF_RENDER_SCALE so
    Claude can read printed dim text clearly."""
    out: list[bytes] = []
    try:
        doc = pdfium.PdfDocument(raw_pdf)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {e}") from e
    page_count = min(len(doc), max_pages)
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
    return out


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
    # ONE WALL WALK (ruled 2026-08-01, step 1): shared math in
    # measure_staging.walk_walls — GABLE FACTOR 0.70 sealed across doors
    # (the pre-C4 0.5 true-triangle retired). Blueprint's source adapter
    # keeps the pitch-computed rise (printed pitch beats drawing-scaled).
    _walk = staging.walk_walls(walls, gable_rise_fn=_gable_rise)
    siding_sqft = _walk["siding_sqft"]
    gable_sqft = _walk["gable_sqft"]
    dormer_sqft = _walk["dormer_sqft"]
    for d in _walk["detail"]:
        if d["rise_used"] != d["rise_read"]:
            gable_pitch_provenance.append({
                "wall": (d["label"] or "?"),
                "scaled_ft": round(d["rise_read"], 2),
                "computed_ft": round(d["rise_used"], 2),
                "pitch": str(raw.get("roof_pitch") or ""),
            })
    siding_sqft += gable_sqft + dormer_sqft

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
        try:
            qty = max(1, int(win.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        _rows.append({"type": "window", "count": qty,
                      "width_in": win.get("width_in"), "height_in": win.get("height_in")})
    for d in doors:
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

    # Expand schedule rows into a per-opening list (qty=1 each) so
    # _build_window_openings sees one row per physical window. Matches
    # the HOVER importer's contract.
    expanded_windows = []
    for win in windows:
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
        plane_rakes = sum(float(p.get("rake_lf") or 0) for p in planes)
        if plane_rakes > float(raw.get("rakes_lf") or 0):
            raw["rakes_lf"] = plane_rakes
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
        # BASIS TRUTH (Howard's open question, answered 2026-08-08): a
        # blueprint read has NO HOVER "+ Openings < 20ft² +10%" row —
        # aliasing the gross area into this field made the Charter Oak
        # note claim a +10% source that was never applied. The field
        # stays None; the line falls back to siding_sqft (same number,
        # ×1.0) and the note names the real basis.
        "siding_with_openings_sqft": None,
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
        "window_count": counts["window"],
        "entry_door_count": counts["entry_door"],
        "patio_door_count": counts["patio_door"],
        "garage_door_count": counts["garage_door"],
        # Finding 6 (ruled 2026-08-01): door_count TOTAL lands on every
        # door — caulk-per-color + J-blocks read it.
        "door_count": _bk["door_count"],
        # Q7 (ruled 2026-07-27): vents/shutters wired on the blueprint door.
        "vent_count": int(raw.get("vent_count") or 0),
        "shutter_count": int(raw.get("shutter_count") or 0),
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
    _sanity = staging.walk_walls(walls, gable_rise_fn=_gable_rise)
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
        breakdown = breakdown_walls_by_profile(walls)
        breakdown = apply_annotations_to_breakdown(breakdown, annotations)
        measurements["_per_elevation_breakdown"] = breakdown["per_elevation"]
        measurements["_per_profile_sqft"] = breakdown["per_profile_sqft"]
    except Exception:
        measurements["_per_elevation_breakdown"] = []
        measurements["_per_profile_sqft"] = {}
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
    # SOURCE-RETENTION RULING (Howard, 2026-08-07): the original upload is
    # retained — always, every door, every file type. A derived artifact
    # never replaces its source.
    source_files: list[dict] = []
    source_probe: dict | None = None
    source_text_pages: list[str] = []

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
        page_pngs = _render_pdf_to_pngs(raw, max_pages)
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
    if not doc:
        # Artifact pin read-side: archived blueprint runs outlive the
        # 24h TTL — serve them here too (fixture_runs, no TTL).
        from run_archive import find_archived_run
        doc = await find_archived_run({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if doc.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your run")
    from routes.ai_measure import strip_cost_keys
    created = doc.get("created_at")
    completed = doc.get("completed_at") or doc.get("updated_at")
    elapsed_ms = None
    if isinstance(created, datetime):
        ref = completed if isinstance(completed, datetime) else datetime.now(timezone.utc)
        elapsed_ms = int((ref - created).total_seconds() * 1000)
    return {
        "run_id": run_id,
        "status": doc.get("status"),
        "stage": doc.get("stage"),
        "result": _with_readback(strip_cost_keys(doc.get("result")),
                                 source_probe=doc.get("source_probe"),
                                 stability=doc.get("stability")),
        "error": doc.get("error"),
        "elapsed_ms": elapsed_ms,
        "source_probe": doc.get("source_probe"),
        "source_files": doc.get("source_files"),
    }


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
    return {
        "run": {
            "run_id": doc.get("run_id"),
            "status": doc.get("status"),
            "stage": doc.get("stage"),
            "page_count": doc.get("page_count"),
            # Iter 78z+ — persisted page filenames so the frontend can
            # render them in the ProfileAnnotator on a resume.
            "page_paths": doc.get("page_paths") or "",
            # Read-side provenance (ruled 2026-07-20): True when served
            # from the CUT archive after the live doc's 24h TTL reaped.
            "archived": archived,
            "result": _with_readback(strip_cost_keys(doc.get("result")),
                                     source_probe=doc.get("source_probe"),
                                     stability=doc.get("stability")),
            "error": doc.get("error"),
            "elapsed_ms": elapsed_ms,
            "age_seconds": age_seconds,
            "source_probe": doc.get("source_probe"),
            "source_files": doc.get("source_files"),
        },
    }


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
        # OCR-FOR-COORDINATES (ruled 2026-08-08): deterministic, local,
        # no extra model call. LOCATION ONLY — never value. Runs off the
        # event loop; failure never sinks the run.
        try:
            if raw.get("_dim_evidence"):
                await asyncio.to_thread(_ocr_locate_evidence,
                                        raw["_dim_evidence"],
                                        image_payloads, raw)
        except Exception:
            logger.exception("[ai-blueprint] ocr-locate failed — quote-only anchors stand")
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
            lines = [l for l in _build_lines(measurements)
                     if (l.get("tab") or "vinyl") != "lp_smart"]
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
