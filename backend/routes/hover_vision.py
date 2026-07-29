"""HOVER legacy elevation-page rendering helpers.

RETIRED 2026-07-29 (Howard's ruling): Phase 2 vision-verify and Phase 3
Deep Verify are gone. The old page finder (`_ELEV_RE`) matched only
"<label> Elevation" titles — the current Hover format uses bare compass
tokens, so the stage found ZERO pages on 92 of 92 audited runs and
rendered silence as a pass (SILENT-ZERO-VERIFICATION class,
verification_integrity_register.md). Scale-bar pixel re-derivation was
deliberately NOT carried over: a pixel-derived number arguing with a
printed callout reopens the sealed provenance door.

The straight-on S2 elevation read (routes/hover_elevation_read.py) is the
single verification pass. This module keeps only what it imports:
`MODEL_NAME`, `_json_from_reply`, and `_render_pdf_pages` (the
legacy-format fallback for older "<label> Elevation" reports).
"""
from __future__ import annotations

import json
import logging
import re

import fitz  # PyMuPDF — already imported elsewhere in hover.py

logger = logging.getLogger(__name__)

# Same model as the existing HOVER text extraction + AI Measure flows.
MODEL_NAME = "claude-opus-4-5-20251101"
MAX_ELEVATION_PAGES = 6   # Hard cap on rendered pages (cost control)
RENDER_DPI = 144          # Crisp enough for Claude to read dim callouts,
                          # not so high it blows the token budget

# Legacy elevation page detector — matches the OLD Hover report format
# ("Front Elevation", "Left Elevation", …). Kept ONLY as the S2 read's
# fallback for older reports; the current format is located by
# hover_elevation_read._find_view_pages.
_ELEV_LABELS = ("Front", "Back", "Rear", "Left", "Right",
                "Side A", "Side B", "Side C", "Side D")
_ELEV_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _ELEV_LABELS) + r")\s+Elevation\b",
    re.IGNORECASE,
)


def _render_pdf_pages(pdf_bytes: bytes, max_pages: int = MAX_ELEVATION_PAGES) -> list[dict]:
    """Open the HOVER PDF, locate elevation pages by their on-page text,
    render each one at `RENDER_DPI` as PNG bytes. Returns up to
    `max_pages` page records: `{page_num, label, png_bytes}`."""
    out: list[dict] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.warning("Iter 78p: PyMuPDF could not open HOVER PDF: %s", e)
        return out

    try:
        for page_num in range(doc.page_count):
            if len(out) >= max_pages:
                break
            page = doc.load_page(page_num)
            text = page.get_text("text") or ""
            match = _ELEV_RE.search(text)
            if not match:
                continue
            label = match.group(1).title()
            try:
                pix = page.get_pixmap(dpi=RENDER_DPI)
                png_bytes = pix.tobytes("png")
            except Exception as e:
                logger.warning("Iter 78p: page %d render failed: %s", page_num, e)
                continue
            # Sanity cap on image size — emergentintegrations chokes on
            # very large payloads. ~1.5MB is plenty for a 144-DPI page.
            if len(png_bytes) > 2_500_000:
                logger.info("Iter 78p: page %d image %.1fMB, skipping",
                            page_num, len(png_bytes) / 1e6)
                continue
            out.append({"page_num": page_num + 1, "label": label,
                        "png_bytes": png_bytes})
    finally:
        doc.close()
    return out


def _json_from_reply(reply: str) -> dict:
    """Strip code fences and parse the first JSON object Claude returned.
    Same shape as the helper in `ai_measure.py` but lighter-weight."""
    if not reply:
        return {}
    s = reply.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```\s*$", "", s)
    # Find first {…} object — handles Claude's occasional preface text
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return {}
