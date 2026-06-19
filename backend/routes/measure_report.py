"""HOVER-style Measurement Report PDF.

Generates a 1–2 page branded measurement report from a finished AI Measure
session. The PDF is intended for two audiences:

1. **The contractor** — a portable, double-checkable record of what Claude
   measured (per-wall table with confidence chips, openings schedule,
   thumbnail of each photo with its elevation tag and confidence). Far
   more useful than a screen-grab when comparing AI numbers to field
   reality.
2. **The homeowner** — when bundled into the Customer Quote PDF, signals
   that the contractor took real measurements (with confidence scores,
   not just a guess), which lifts close rates on premium siding/window
   jobs by adding professionalism.

Layout (inline HTML → WeasyPrint, same pipeline as customer quotes):
  • Header: address + supplier branding + Claude Opus 4.5 attribution
  • Summary grid: siding ft², openings, eaves/rakes LF, story count
  • Per-wall breakdown table with colored confidence chips
  • Openings schedule (grouped by elevation × size)
  • Photo thumbnails grid (4-up, each tagged with elevation + confidence)
  • Notes section (double-count check + Claude's verification notes)

Endpoint: POST /api/measure/report-pdf  (cookie auth)
Body JSON: {
    "estimate_id": "<uuid>",  // pulls session + estimate for address/branding
}
Returns: application/pdf attachment
"""
from __future__ import annotations

import base64
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from config import UPLOAD_DIR
from db import db
from deps import get_current_user
from pdf import render_pdf, safe_filename
from services import get_branding

router = APIRouter(prefix="/measure", tags=["measure"])


class ReportRequest(BaseModel):
    estimate_id: str


def _conf_chip_color(score: float) -> tuple[str, str]:
    """Return (bg-hex, label) for a 0-100 confidence score."""
    if score >= 80:
        return ("#16A34A", "HIGH")
    if score >= 60:
        return ("#CA8A04", "MED")
    if score >= 30:
        return ("#EA580C", "LOW")
    return ("#DC2626", "GUESS")


def _img_to_data_uri(filename: str) -> str | None:
    """Return a data: URI for an upload filename so WeasyPrint can embed
    it inline (avoids fetching back through the network)."""
    path: Path = UPLOAD_DIR / filename
    if not path.exists():
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _build_html(
    *,
    address: str,
    estimate_number: str,
    customer_name: str,
    company_name: str,
    company_logo_url: str | None,
    photo_urls: list[str],
    photo_meta: list[dict],   # [{index, elevation, elevation_confidence, ...}]
    walls: list[dict],
    measurements: dict,
    openings_schedule: list[dict],
    missing_elevations: list[str],
    double_count_check: str,
    notes: str,
) -> str:
    # --- summary tiles ---------------------------------------------------
    m = measurements or {}
    tiles = [
        ("Siding", f"{int(round(float(m.get('siding_sqft') or 0))):,} ft²"),
        ("Eaves", f"{int(round(float(m.get('eaves_lf') or 0))):,} LF"),
        ("Rakes", f"{int(round(float(m.get('rakes_lf') or 0))):,} LF"),
        ("Openings", f"{int(m.get('opening_count') or 0)}"),
        ("Story count", str(m.get('_ai_story_count') or '—')),
        ("Avg wall ht", f"{m.get('_ai_avg_wall_height_ft') or '—'} ft"),
    ]

    tiles_html = "".join(
        f'<div style="border:1px solid #E4E4E7;padding:8px 10px;">'
        f'<div style="font-size:8px;color:#71717A;text-transform:uppercase;letter-spacing:1px;font-weight:700;">{label}</div>'
        f'<div style="font-family:Menlo,Consolas,monospace;font-weight:700;font-size:16px;color:#09090B;margin-top:2px;">{value}</div>'
        f"</div>"
        for label, value in tiles
    )

    # --- wall table with confidence chips --------------------------------
    wall_rows = []
    for w in walls:
        width = float(w.get("width_ft") or 0)
        eave = float(w.get("height_ft") or 0)
        gable = float(w.get("gable_triangle_height_ft") or 0)
        dormer = float(w.get("dormer_face_sqft") or 0)
        pct = float(w.get("siding_pct_this_wall") or 100)
        # match aggregator clamp logic
        if 0 < pct < 1:
            pct = pct * 100
        pct = max(0, min(100, pct))
        siding = (width * eave) * (pct / 100.0) + 0.5 * width * gable + dormer
        conf = float(w.get("confidence") or 0)
        chip_bg, chip_label = _conf_chip_color(conf)
        chip_html = (
            f'<span style="display:inline-block;background:{chip_bg};color:#FFF;'
            f'padding:2px 6px;font-size:9px;font-weight:700;letter-spacing:0.5px;'
            f'border-radius:2px;">{chip_label} {int(conf)}</span>'
        )
        reason = (w.get("confidence_reasoning") or "").strip()
        wall_rows.append(
            f"<tr>"
            f'<td style="padding:6px 8px;font-weight:700;text-transform:uppercase;font-size:10px;letter-spacing:1px;color:#52525B;">{(w.get("label") or "—")}</td>'
            f'<td style="padding:6px 8px;font-family:Menlo,monospace;text-align:right;">{width:.1f}</td>'
            f'<td style="padding:6px 8px;font-family:Menlo,monospace;text-align:right;">{eave:.1f}</td>'
            f'<td style="padding:6px 8px;font-family:Menlo,monospace;text-align:right;">{(0.5*width*gable):.0f}</td>'
            f'<td style="padding:6px 8px;font-family:Menlo,monospace;text-align:right;">{dormer:.0f}</td>'
            f'<td style="padding:6px 8px;font-family:Menlo,monospace;text-align:right;font-weight:700;">{siding:.0f}</td>'
            f'<td style="padding:6px 8px;text-align:center;">{chip_html}<div style="font-size:9px;color:#71717A;margin-top:2px;">{reason[:80]}</div></td>'
            f"</tr>"
        )
    wall_table_html = "".join(wall_rows) or '<tr><td colspan="7" style="padding:12px;text-align:center;color:#A1A1AA;">No walls measured</td></tr>'

    # --- openings schedule (grouped by elevation, color-coded) --------
    # Mirrors the on-screen Option B layout: one colored header bar per
    # elevation with total count, then indented rows showing size + count.
    ELEV_COLORS = {
        "front": ("#3B82F6", "#EFF6FF"),
        "back":  ("#16A34A", "#F0FDF4"),
        "left":  ("#EA580C", "#FFF7ED"),
        "right": ("#7C3AED", "#FAF5FF"),
        "other": ("#52525B", "#FAFAFA"),
    }
    ELEV_ORDER = ["front", "back", "left", "right", "other"]
    groups: dict[str, list[dict]] = {}
    for o in openings_schedule or []:
        elev = (o.get("elevation") or "other").lower()
        if elev not in ELEV_COLORS:
            elev = "other"
        groups.setdefault(elev, []).append(o)
    grouped_blocks = []
    for elev in ELEV_ORDER:
        items = groups.get(elev) or []
        if not items:
            continue
        bg, soft = ELEV_COLORS[elev]
        total_count = sum(int(o.get("count") or 0) for o in items)
        rows = []
        for o in items:
            size_label = o.get("size_label")
            if not size_label:
                wi = int(float(o.get("width_in") or 0))
                hi = int(float(o.get("height_in") or 0))
                size_label = f"{wi}×{hi} in"
            otype = (o.get("type") or "—").replace("_", " ")
            rows.append(
                f'<tr>'
                f'<td style="padding:4px 8px 4px 24px;text-transform:capitalize;color:#52525B;width:45%;">{otype}</td>'
                f'<td style="padding:4px 8px;font-family:Menlo,monospace;color:#27272A;width:35%;">{size_label}</td>'
                f'<td style="padding:4px 8px;font-family:Menlo,monospace;font-weight:700;text-align:right;">×{int(o.get("count") or 0)}</td>'
                f'</tr>'
            )
        grouped_blocks.append(
            f'<div style="margin-bottom:6px;">'
            f'<div style="background:{soft};border-left:4px solid {bg};padding:4px 8px;display:flex;align-items:center;gap:8px;">'
            f'<span style="background:{bg};color:#FFF;font-size:9px;font-weight:700;letter-spacing:1px;padding:2px 8px;text-transform:uppercase;">{elev}</span>'
            f'<span style="font-size:11px;font-weight:700;color:{bg};">{total_count} opening{"s" if total_count != 1 else ""}</span>'
            f'</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:11px;">'
            f'<tbody>{"".join(rows)}</tbody>'
            f'</table>'
            f'</div>'
        )
    sched_html = "".join(grouped_blocks) or '<div style="padding:12px;text-align:center;color:#A1A1AA;font-size:11px;">No openings detected</div>'

    # --- photo strip -----------------------------------------------------
    photo_cells = []
    for i, fname in enumerate(photo_urls or []):
        data_uri = _img_to_data_uri(fname)
        if not data_uri:
            continue
        meta = next((p for p in (photo_meta or []) if int(p.get("index", -1)) == i), {})
        elev = (meta.get("elevation") or "untagged").upper()
        ec = int(float(meta.get("elevation_confidence") or 0))
        chip_bg, _ = _conf_chip_color(ec)
        ec_chip = ""
        if ec:
            ec_chip = (
                f'<div style="position:absolute;bottom:4px;right:4px;'
                f'background:{chip_bg};color:#FFF;font-size:9px;font-weight:700;'
                f'padding:2px 6px;letter-spacing:0.5px;">{ec}%</div>'
            )
        photo_cells.append(
            f'<div style="width:48%;display:inline-block;vertical-align:top;margin:0 1% 12px 1%;">'
            f'<div style="position:relative;">'
            f'<img src="{data_uri}" style="width:100%;height:auto;display:block;border:1px solid #E4E4E7;" />'
            f'<div style="position:absolute;top:4px;left:4px;background:#7C3AED;color:#FFF;font-size:9px;font-weight:700;padding:2px 6px;letter-spacing:0.5px;">{elev}</div>'
            f"{ec_chip}"
            f"</div></div>"
        )
    photos_html = "".join(photo_cells) or '<div style="padding:24px;text-align:center;color:#A1A1AA;">No photos saved on session</div>'

    # --- branding header -------------------------------------------------
    logo_html = ""
    if company_logo_url:
        # Try to inline the company logo too (lives under UPLOAD_DIR or
        # under /api/uploads/<file>)
        if company_logo_url.startswith("/api/uploads/"):
            fname = company_logo_url.rsplit("/", 1)[-1]
            data_uri = _img_to_data_uri(fname)
            if data_uri:
                logo_html = f'<img src="{data_uri}" style="height:48px;" />'

    missing_html = ""
    if missing_elevations:
        missing_html = (
            f'<div style="background:#FEF3C7;border:1px solid #F59E0B;padding:8px 10px;margin:12px 0;font-size:11px;">'
            f"<strong>⚠ Heads-up:</strong> Claude couldn't see these elevations — "
            f"add photos to capture them: {', '.join(missing_elevations)}.</div>"
        )

    return f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  @page {{ size: Letter; margin: 0.4in; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; color:#09090B; font-size:12px; line-height:1.4; }}
  h1 {{ font-size:22px; margin:0 0 4px 0; font-weight:800; letter-spacing:-0.5px; }}
  h2 {{ font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#71717A; margin:18px 0 8px 0; font-weight:700; border-bottom:2px solid #09090B; padding-bottom:4px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; font-size:9px; text-transform:uppercase; letter-spacing:1px; color:#A1A1AA; padding:6px 8px; border-bottom:1px solid #09090B; font-weight:700; }}
  td {{ border-bottom:1px solid #F4F4F5; font-size:11px; }}
  .grid-tiles {{ display:grid; grid-template-columns:repeat(6,1fr); gap:6px; }}
</style></head>
<body>
  <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #09090B;padding-bottom:10px;">
    <div>
      <div style="font-size:9px;text-transform:uppercase;letter-spacing:2px;color:#71717A;font-weight:700;">AI Measurement Report</div>
      <h1>{(customer_name or "Untitled")} · {estimate_number}</h1>
      <div style="font-size:11px;color:#52525B;">{address or "Address not set"}</div>
    </div>
    <div style="text-align:right;">{logo_html}<div style="font-size:9px;color:#71717A;margin-top:4px;">{company_name}</div></div>
  </div>

  <h2>Summary</h2>
  <div class="grid-tiles">{tiles_html}</div>

  {missing_html}

  <h2>Per-wall breakdown · confidence chips</h2>
  <table>
    <thead><tr>
      <th>Wall</th>
      <th style="text-align:right;">W (ft)</th>
      <th style="text-align:right;">H eave (ft)</th>
      <th style="text-align:right;">Gable ft²</th>
      <th style="text-align:right;">Dormer ft²</th>
      <th style="text-align:right;">Siding ft²</th>
      <th style="text-align:center;">Confidence · why</th>
    </tr></thead>
    <tbody>{wall_table_html}</tbody>
  </table>

  <h2>Openings schedule</h2>
  <div>{sched_html}</div>

  <h2>Photos</h2>
  <div>{photos_html}</div>

  {f'<h2>Cross-reference check</h2><div style="font-size:11px;color:#52525B;font-style:italic;border-left:3px solid #7C3AED;padding-left:8px;">{double_count_check}</div>' if double_count_check else ""}
  {f'<h2>Notes</h2><div style="font-size:11px;color:#52525B;font-style:italic;border-left:3px solid #7C3AED;padding-left:8px;">{notes}</div>' if notes else ""}

  <div style="margin-top:18px;padding-top:8px;border-top:1px solid #E4E4E7;font-size:9px;color:#A1A1AA;text-align:center;">
    Generated by Claude Opus 4.5 vision · AI photo measurement is an estimate, not a survey · Verify in field before ordering.
  </div>
</body></html>
"""


@router.post("/report-pdf")
async def measurement_report_pdf(
    body: ReportRequest, user: dict = Depends(get_current_user)
):
    company_id = user.get("company_id")
    estimate = await db.estimates.find_one(
        {"id": body.estimate_id, "company_id": company_id}, {"_id": 0}
    )
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    session = await db.ai_measure_sessions.find_one(
        {"estimate_id": body.estimate_id, "company_id": company_id}, {"_id": 0}
    )
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No AI Measure session yet — run AI Measure first, then download the report",
        )

    preview = session.get("preview") or {}
    measurements = preview.get("measurements") or {}
    raw_ai = preview.get("raw_ai") or {}
    photo_urls = session.get("photo_urls") or []

    branding = await get_branding()
    customer = estimate.get("customer") or {}

    html = _build_html(
        address=estimate.get("address") or customer.get("address") or "",
        estimate_number=estimate.get("number") or estimate.get("id", "")[:8],
        customer_name=customer.get("name") or "",
        company_name=branding.get("supplier_name") or "Pro-Quote Estimating Tool",
        company_logo_url=branding.get("supplier_logo_url"),
        photo_urls=photo_urls,
        photo_meta=measurements.get("_ai_photos") or raw_ai.get("photos") or [],
        walls=raw_ai.get("walls") or [],
        measurements=measurements,
        openings_schedule=measurements.get("_ai_openings_schedule") or raw_ai.get("openings_schedule") or [],
        missing_elevations=measurements.get("_ai_missing_elevations") or raw_ai.get("missing_elevations") or [],
        double_count_check=measurements.get("_ai_double_count_check") or raw_ai.get("double_count_check") or "",
        notes=measurements.get("_ai_notes") or "",
    )
    pdf_bytes = render_pdf(html)
    filename = safe_filename(estimate.get("number"), (customer.get("name") or "").strip())
    filename = filename.rsplit(".pdf", 1)[0] + "-measurement.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
