"""S2 — HOVER DRAWN-ELEVATION GEOMETRY READ (authorized 2026-07-29,
S1+S2 only — S3 wiring into flags/derivations is NOT built; Howard sees
the acceptance runs on 261 Haugh + 3 Degree first).

Reads the elevation drawings HOVER PRINTS in its own report (pages
8–15 class: FRONT / FRONT-RIGHT / … / LEFT-FRONT) and extracts what is
PRINTED on them: per-facade width AND height callouts, opening IDs
drawn on their facades, dimensioned corner heights.

PROVENANCE (Howard adopted 2026-07-29): a dimension read off a Hover
drawing is HOVER-DIM — Hover's own published measurement arriving
through a vision read — tagged HOVER-READ ✓ (reconciles) or ⚠ (callout
mis-association risk). NEVER TAPED, never collapsed into Class-C photo
inference. REPORT ONLY: nothing here feeds a flag, a count or a line.
"""
import base64
import logging
import re
from typing import Optional

import fitz

from routes.hover_vision import (MODEL_NAME, _json_from_reply,
                                 _render_pdf_pages)

logger = logging.getLogger(__name__)

# The drawn-view pages in the current Hover report format are titled with a
# bare compass token (FRONT / FRONT-RIGHT / …), NOT "<label> Elevation" —
# the shared _render_pdf_pages regex (Deep Verify's format) misses them.
VIEW_TOKENS = ("FRONT", "FRONT-RIGHT", "RIGHT", "RIGHT-BACK",
               "BACK", "BACK-LEFT", "LEFT", "LEFT-FRONT")


def _find_view_pages(pdf_bytes: bytes, max_pages: int = 8) -> list[dict]:
    """Locate + render the 8 drawn-view pages: a view page carries EXACTLY
    ONE standalone view-token line (the compass/footprint page carries all
    four cardinal tokens at once — excluded by the exactly-one rule)."""
    out: list[dict] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.warning("S2: PyMuPDF could not open HOVER PDF: %s", e)
        return out
    try:
        for page_num in range(doc.page_count):
            if len(out) >= max_pages:
                break
            page = doc.load_page(page_num)
            lines = [ln.strip() for ln in (page.get_text("text") or "").splitlines()]
            toks = [ln for ln in lines if ln in VIEW_TOKENS]
            if len(toks) != 1:
                continue
            try:
                png_bytes = page.get_pixmap(dpi=144).tobytes("png")
            except Exception as e:
                logger.warning("S2: page %d render failed: %s", page_num, e)
                continue
            if len(png_bytes) > 2_500_000:
                logger.info("S2: page %d image too large, skipped", page_num)
                continue
            out.append({"page_num": page_num + 1, "label": toks[0],
                        "png_bytes": png_bytes})
    finally:
        doc.close()
    return out

GEOMETRY_PROMPT = """\
You are reading ONE elevation drawing page from a HOVER measurement report
(FRONT / FRONT-RIGHT / RIGHT / RIGHT-BACK / BACK / BACK-LEFT / LEFT /
LEFT-FRONT view). Extract ONLY what is PRINTED on the drawing — dimension
callouts, wall labels (WR-1, WR-20 …), opening labels (W-206, D-2 …).

Return STRICT JSON, nothing else:
{
  "view": "FRONT|FRONT-RIGHT|RIGHT|RIGHT-BACK|BACK|BACK-LEFT|LEFT|LEFT-FRONT|UNKNOWN",
  "facades": [
    {"label": "WR-20", "width_ft": 29.25, "width_text": "29'3\\"",
     "height_min_ft": 9.25, "height_max_ft": 9.58, "height_text": "9'3\\"-9'7\\""}
  ],
  "openings_placed": [ {"id": "W-206", "on_facade": "WR-2"} ],
  "corner_heights_ft": [ {"near_facade": "WR-17", "height_ft": 18.42, "text": "18'5\\""} ],
  "confidence": "high|medium|low",
  "notes": "anything ambiguous, unreadable, or uncertain"
}

RULES:
- Transcribe dimension callouts EXACTLY, then convert feet-inches to decimal
  feet (18'5" -> 18.42).
- An opening belongs to a facade only when it is DRAWN INSIDE that labeled
  wall region on this page.
- If a callout is unreadable or its association is unclear, OMIT it and say
  so in notes — never guess.
- NEVER estimate a dimension from pixel proportions. Printed callouts only.
- If this page is not an elevation drawing: {"view": "NOT_AN_ELEVATION"}.
"""


async def _read_one_geometry(page: dict, api_key: str, session_id: str) -> Optional[dict]:
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage
    chat = LlmChat(
        api_key=api_key,
        session_id=f"{session_id}-geom-p{page['page_num']}",
        system_message=GEOMETRY_PROMPT,
    ).with_model("anthropic", MODEL_NAME)
    msg = UserMessage(
        text=(f"Hint: this is most likely the '{page['label']} Elevation' page. "
              "Extract per the JSON schema."),
        file_contents=[ImageContent(
            image_base64=base64.b64encode(page["png_bytes"]).decode("ascii"))],
    )
    try:
        reply = await chat.send_message(msg)
    except Exception as e:
        logger.warning("S2 geometry read failed on page %d: %s", page["page_num"], e)
        return None
    parsed = _json_from_reply(reply or "")
    if not parsed or parsed.get("view") == "NOT_AN_ELEVATION":
        return None
    parsed["__page_num"] = page["page_num"]
    parsed["__expected_label"] = page["label"]
    return parsed


# Full Hover ID vocabulary: W-101 D-2 (openings) · SGD-1 (sliding glass
# door) · WR/BR/STC (wall/brick/stucco regions) — a REAL printed ID must
# never be flagged as unknown just because the regex was too narrow.
_ID_RE = re.compile(r"\b([A-Z]{1,4}\d?-\d+)\b")


def aggregate_geometry(pages: list[dict], schedule_text: str = "") -> dict:
    """Merge per-page reads + build the ⚠ list. Every extracted item is
    tagged HOVER-READ ✓ or ⚠ — Howard wants EVERY ⚠ named, not a summary."""
    known_ids = {m.upper().replace("W-", "W-").strip()
                 for m in _ID_RE.findall(schedule_text or "")}
    facades: dict[str, dict] = {}
    placements: list[dict] = []
    corners: list[dict] = []
    warnings: list[str] = []
    placed_by_id: dict[str, set] = {}

    for p in pages or []:
        view = p.get("view") or p.get("__expected_label") or "UNKNOWN"
        for f in p.get("facades") or []:
            lab = str(f.get("label") or "").upper()
            if not lab:
                warnings.append(f"⚠ {view}: facade dimension with NO label "
                                f"({f.get('width_text')}/{f.get('height_text')}) — dropped")
                continue
            entry = {**f, "label": lab, "view": view, "read": "✓"}
            if known_ids and lab not in known_ids:
                warnings.append(f"⚠ {view}: facade label {lab} is not printed "
                                "anywhere in the report — misread label ⚠")
                entry["read"] = "⚠"
            prev = facades.get(lab)
            if prev and prev.get("width_ft") and f.get("width_ft") and \
                    abs(prev["width_ft"] - f["width_ft"]) > 0.6:
                warnings.append(
                    f"⚠ {lab}: width disagrees across views — "
                    f"{prev['view']} read {prev['width_ft']:g}' vs {view} "
                    f"{f['width_ft']:g}' — callout mis-association risk, both kept ⚠")
                entry["read"] = prev["read"] = "⚠"
            facades.setdefault(lab, entry)
        for o in p.get("openings_placed") or []:
            oid = str(o.get("id") or "").upper()
            fac = str(o.get("on_facade") or "").upper()
            if not oid or not fac:
                continue
            read = "✓"
            if re.match(r"^(WR|BR|STC)-", oid):
                warnings.append(f"⚠ {view}: {oid} is a facade-region label but "
                                f"was read as an OPENING on {fac} — wrong bucket ⚠")
                read = "⚠"
            elif known_ids and oid not in known_ids:
                warnings.append(f"⚠ {view}: opening {oid} placed on {fac} but the "
                                "ID is not in the report's schedule text — ⚠")
                read = "⚠"
            placed_by_id.setdefault(oid, set()).add(fac)
            placements.append({"id": oid, "on_facade": fac, "view": view, "read": read})
        for c in p.get("corner_heights_ft") or []:
            if c.get("height_ft"):
                corners.append({**c, "view": view, "read": "✓"})
        if (p.get("confidence") or "high") == "low":
            warnings.append(f"⚠ {view}: page read confidence LOW — {p.get('notes') or 'no notes'}")

    for oid, facs in placed_by_id.items():
        if len(facs) > 1:
            warnings.append(f"⚠ opening {oid} drawn on {len(facs)} different walls "
                            f"({' + '.join(sorted(facs))}) — corner window or "
                            "mis-association, resolve by eye ⚠")
    # dedupe placements (same id+facade seen from two views is agreement)
    seen = set()
    unique_placements = []
    for pl in placements:
        key = (pl["id"], pl["on_facade"])
        if key not in seen:
            seen.add(key)
            unique_placements.append(pl)

    return {
        "provenance": "HOVER-DIM (HOVER-READ ✓/⚠) — Hover's printed measurement via vision read; never TAPED, never photo-inference",
        "facades": sorted(facades.values(), key=lambda x: x["label"]),
        "openings_placed": unique_placements,
        "corner_heights_ft": corners,
        "warnings": warnings,
        "pages_read": len(pages or []),
    }


async def read_elevation_geometry(pdf_bytes: bytes, api_key: str,
                                  session_id: str, schedule_text: str = "",
                                  max_pages: int = 8) -> dict:
    pages = _find_view_pages(pdf_bytes, max_pages=max_pages)
    if not pages:
        # older "<label> Elevation" report format
        pages = _render_pdf_pages(pdf_bytes, max_pages=max_pages)
    if not pages:
        return {"error": "no elevation pages found in the PDF",
                "facades": [], "openings_placed": [],
                "corner_heights_ft": [], "warnings": [], "pages_read": 0}
    reads = []
    for pg in pages:
        parsed = await _read_one_geometry(pg, api_key, session_id)
        if parsed:
            reads.append(parsed)
    return aggregate_geometry(reads, schedule_text)
