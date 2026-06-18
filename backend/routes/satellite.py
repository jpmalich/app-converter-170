"""Satellite tile fetcher — pulls an aerial view of a property and
saves it as an upload, ready to be passed to AI Measure as an extra
photo.

The chain:
  1. Geocode the address via Nominatim (OpenStreetMap, free, no key)
  2. Fetch an Esri World Imagery export at that lat/lon (free, no key)
  3. Save the JPEG to UPLOAD_DIR and return its filename

The frontend then adds the returned filename to its `photoUrls` list so
the satellite view rides along with the contractor's ground photos when
AI Measure is run. Claude is taught (in ai_measure.py's system prompt)
to use the aerial view for roof outline → eaves_lf / rakes_lf only;
wall heights still come from the ground photos.

No API keys required. Nominatim's usage policy asks for a descriptive
User-Agent + ≤ 1 req/sec; Esri World Imagery is free for non-commercial
use and de-facto used commercially without keys.
"""
from __future__ import annotations

import io
import math
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException
from PIL import Image, ImageDraw, ImageFont

from config import UPLOAD_DIR
from deps import get_current_user

router = APIRouter(prefix="/measure", tags=["measure"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
ESRI_EXPORT_URL = (
    "https://services.arcgisonline.com/arcgis/rest/services/"
    "World_Imagery/MapServer/export"
)
USER_AGENT = "ProQuoteEstimator/1.0 (contractor siding estimator)"

# House-scale bbox at the equator. Earlier testing showed Esri returns
# a 500 "Error: bytes" whenever the bbox is tighter than ~150 m square
# (the imagery service can't synthesize from its top-zoom tiles at that
# scale). Default at 200 m (= 400 m × 400 m view) — first attempt almost
# always succeeds on suburban + rural lots. Back off to 350 m only if
# Esri still errors. One degree of latitude ≈ 111 km. Longitude shrinks
# by cos(lat) toward the poles.
DEFAULT_RADIUS_M = 200
RETRY_RADIUS_M = 350
EARTH_M_PER_DEG_LAT = 111_320

DEFAULT_SIZE_PX = 1600  # 1600×1600 is plenty for Claude to read roof outline


def _bbox_around(lat: float, lon: float, radius_m: int) -> tuple[float, float, float, float]:
    """Return (xmin, ymin, xmax, ymax) in WGS84 degrees centered on lat/lon."""
    dlat = radius_m / EARTH_M_PER_DEG_LAT
    dlon = radius_m / (EARTH_M_PER_DEG_LAT * max(0.01, math.cos(math.radians(lat))))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def _burn_target_marker(jpeg_bytes: bytes, radius_m: int) -> bytes:
    """Draw a red crosshair + ring + "TARGET" label at the center of the
    satellite tile. Critical on rural lots where the radius bbox catches
    several houses — without this marker, neither the contractor nor
    Claude can tell which structure is the address."""
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    cx, cy = w // 2, h // 2
    # Crosshair geometry sized so it stays legible at any radius zoom.
    # At 200 m radius the ring is ~7% of the image (≈ a residential
    # house footprint); at 350 m it stays the same px size, so the
    # outline still pops without obscuring the roof.
    ring_r = max(40, w // 14)
    cross_len = ring_r * 2
    line_w = max(4, w // 240)
    # Outer ring
    draw.ellipse(
        (cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r),
        outline=(220, 38, 38, 255),
        width=line_w,
    )
    # Inner dot
    inner = max(6, w // 200)
    draw.ellipse(
        (cx - inner, cy - inner, cx + inner, cy + inner),
        fill=(220, 38, 38, 255),
    )
    # Crosshair arms (broken at the ring so the structure inside is visible)
    gap = ring_r + line_w * 2
    draw.line([(cx - cross_len, cy), (cx - gap, cy)], fill=(220, 38, 38, 255), width=line_w)
    draw.line([(cx + gap, cy), (cx + cross_len, cy)], fill=(220, 38, 38, 255), width=line_w)
    draw.line([(cx, cy - cross_len), (cx, cy - gap)], fill=(220, 38, 38, 255), width=line_w)
    draw.line([(cx, cy + gap), (cx, cy + cross_len)], fill=(220, 38, 38, 255), width=line_w)
    # TARGET label above the ring
    label = f"TARGET · {radius_m}m view"
    font_px = max(20, w // 50)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_px
        )
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = font_px // 3
    tx = cx - tw // 2
    ty = cy - ring_r - cross_len // 2 - th - pad * 2
    if ty < pad:
        ty = cy + ring_r + cross_len // 2 + pad
    draw.rectangle(
        (tx - pad, ty - pad, tx + tw + pad, ty + th + pad),
        fill=(220, 38, 38, 230),
    )
    draw.text((tx, ty), label, fill=(255, 255, 255, 255), font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


@router.post("/satellite-tile")
async def fetch_satellite_tile(
    address: str = Form(...),
    radius_m: int = Form(DEFAULT_RADIUS_M),
    size_px: int = Form(DEFAULT_SIZE_PX),
    user: dict = Depends(get_current_user),  # noqa: ARG001 — auth gate
):
    """Geocode `address` and return a top-down satellite JPEG saved into
    UPLOAD_DIR. Response shape mirrors `/api/uploads` so the frontend
    can append the returned filename straight into `photoUrls`."""
    if not address.strip():
        raise HTTPException(status_code=400, detail="address is required")
    if radius_m < 30 or radius_m > 500:
        radius_m = DEFAULT_RADIUS_M
    if size_px < 512 or size_px > 2400:
        size_px = DEFAULT_SIZE_PX

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=20.0,
    ) as client:
        # 1) Geocode via Nominatim. We ask for the top hit only.
        try:
            geo = await client.get(
                NOMINATIM_URL,
                params={"q": address, "format": "json", "limit": 1, "addressdetails": 0},
            )
            geo.raise_for_status()
            hits = geo.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Geocode failed: {e}") from e
        if not hits:
            raise HTTPException(
                status_code=404,
                detail=f"Address not found: {address!r}",
            )
        hit = hits[0]
        try:
            lat = float(hit["lat"])
            lon = float(hit["lon"])
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=502, detail=f"Bad geocode reply: {e}") from e
        resolved_label = hit.get("display_name") or address

        # 2) Fetch the satellite tile from Esri ExportMap. Esri returns
        #    a 500 "Error: bytes" when the bbox is too tight — fall back
        #    to a larger radius if the first attempt fails. Tracks
        #    `radius_used_m` so the frontend can show what scale we
        #    actually got.
        radius_used_m = radius_m
        body = b""
        ctype = ""
        last_err = ""
        for attempt_radius in (radius_m, RETRY_RADIUS_M) if radius_m < RETRY_RADIUS_M else (radius_m,):
            bbox = _bbox_around(lat, lon, attempt_radius)
            try:
                img = await client.get(
                    ESRI_EXPORT_URL,
                    params={
                        "bbox": ",".join(str(x) for x in bbox),
                        "bboxSR": "4326",  # WGS84 lat/lon
                        "size": f"{size_px},{size_px}",
                        "format": "jpg",
                        "transparent": "false",
                        "f": "image",
                    },
                )
            except httpx.HTTPError as e:
                last_err = f"network error: {e}"
                continue
            ctype = img.headers.get("content-type", "").lower()
            # Esri responds 200 with text/html when it actually errored,
            # so check content-type too.
            if img.status_code != 200 or "image" not in ctype:
                last_err = (
                    f"esri returned status={img.status_code} ctype={ctype!r} "
                    f"body={img.text[:200]!r} at radius={attempt_radius}m"
                )
                continue
            body = img.content
            radius_used_m = attempt_radius
            break
        if not body:
            raise HTTPException(
                status_code=502,
                detail=f"Esri imagery fetch failed: {last_err}",
            )
        if len(body) < 2048:
            raise HTTPException(
                status_code=502,
                detail=f"Esri returned an unexpectedly small payload ({len(body)} bytes)",
            )

    # 3a) Burn a red target crosshair on the exact geocoded center so
    #     the contractor (and Claude) can instantly identify the right
    #     structure — critical on rural lots where the bbox catches
    #     several houses. The center pixel of the JPEG corresponds 1:1
    #     to the lat/lon we just resolved.
    body = _burn_target_marker(body, radius_used_m)

    # 3) Persist to UPLOAD_DIR (same place /api/uploads writes) so the
    #    AI Measure flow can pick it up via the existing photo_paths
    #    pathway with no extra plumbing.
    ext = "jpg"
    filename = f"satellite-{uuid.uuid4().hex[:10]}.{ext}"
    target: Path = UPLOAD_DIR / filename
    target.write_bytes(body)

    return {
        "filename": filename,
        "url": f"/api/uploads/{filename}",
        "lat": lat,
        "lon": lon,
        "address_resolved": resolved_label,
        "radius_m": radius_used_m,
        "size_px": size_px,
        "bytes": len(body),
    }
