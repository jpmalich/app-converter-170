"""Satellite tile fetcher — pulls an aerial view of a property and
saves it as an upload, ready to be passed to AI Measure as an extra
photo.

Iter 56h: switched from Nominatim + Esri World Imagery to Google Maps.
Howard hit issues with Nominatim mis-geocoding rural addresses (parcel
center vs structure), and Esri tile pyramid 500-ing on tight bboxes.
Google's Geocoding API is the gold standard for residential addresses,
and Google Maps Static API renders at any zoom (no tile-pyramid gaps).

The chain:
  1. Geocode the address via Google Geocoding API → lat/lon
  2. Fetch a Google Static Maps satellite image at that lat/lon
  3. Burn a red target crosshair on the geocoded center
  4. Save the JPEG to UPLOAD_DIR

The frontend appends the returned filename to its `photoUrls` list so
the satellite ride-alongs with the contractor's ground photos when AI
Measure is run. The contractor can then drag a green "TARGET HOUSE" box
on the aerial via the Annotate modal if the geocoder still missed.

Key required: GOOGLE_MAPS_API_KEY in backend/.env. The key must have
both Geocoding API and Maps Static API enabled in Google Cloud Console.
"""
from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException
from PIL import Image, ImageDraw, ImageFont

from config import UPLOAD_DIR
from deps import get_current_user

router = APIRouter(prefix="/measure", tags=["measure"])

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_STATIC_URL = "https://maps.googleapis.com/maps/api/staticmap"

# Default zoom for a single-house satellite view. Google's zoom scale:
#   18 = a few houses + yards visible
#   19 = single house fills ~30% of the frame  ← suburban sweet spot
#   20 = single house fills most of the frame  ← rural / large-lot sweet spot
#   21 = roof detail only (some areas don't have 21-zoom imagery)
# 20 is the safest universal default — visible roof outline + just
# enough of the lot to see driveways / garages / outbuildings.
DEFAULT_ZOOM = 20
MIN_ZOOM = 17
MAX_ZOOM = 21
# Google's Static Maps cap is 640×640 free, 2× scale gives effective
# 1280×1280 (still single API call). Premium would allow 2048 but the
# free tier ceiling is 640 × scale=2.
DEFAULT_SIZE_PX = 640
DEFAULT_SCALE = 2  # 2× = retina resolution at the same billed cost


def _burn_target_marker(jpeg_bytes: bytes, zoom: int) -> bytes:
    """Draw a red crosshair + ring + "TARGET" label at the center of the
    satellite tile. The center pixel corresponds 1:1 to the geocoded
    lat/lon (Google Static Maps centers on the requested point)."""
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    cx, cy = w // 2, h // 2
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
    gap = ring_r + line_w * 2
    draw.line([(cx - cross_len, cy), (cx - gap, cy)], fill=(220, 38, 38, 255), width=line_w)
    draw.line([(cx + gap, cy), (cx + cross_len, cy)], fill=(220, 38, 38, 255), width=line_w)
    draw.line([(cx, cy - cross_len), (cx, cy - gap)], fill=(220, 38, 38, 255), width=line_w)
    draw.line([(cx, cy + gap), (cx, cy + cross_len)], fill=(220, 38, 38, 255), width=line_w)
    label = f"TARGET · z{zoom}"
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
    zoom: int = Form(DEFAULT_ZOOM),
    size_px: int = Form(DEFAULT_SIZE_PX),
    user: dict = Depends(get_current_user),  # noqa: ARG001 — auth gate
):
    """Geocode `address` via Google and return a top-down satellite JPEG
    saved into UPLOAD_DIR. Response shape mirrors `/api/uploads` so the
    frontend can append the returned filename straight into `photoUrls`."""
    if not address.strip():
        raise HTTPException(status_code=400, detail="address is required")
    if zoom < MIN_ZOOM or zoom > MAX_ZOOM:
        zoom = DEFAULT_ZOOM
    if size_px < 256 or size_px > 640:
        size_px = DEFAULT_SIZE_PX

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_MAPS_API_KEY missing on server",
        )

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1) Geocode via Google Geocoding API.
        try:
            geo = await client.get(
                GOOGLE_GEOCODE_URL,
                params={"address": address, "key": api_key},
            )
            geo.raise_for_status()
            payload = geo.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Geocode failed: {e}") from e
        status = payload.get("status", "")
        err_msg = payload.get("error_message") or ""
        if status == "REQUEST_DENIED":
            # Most common reasons: billing not enabled, or Geocoding API
            # not turned on for this key. Surface plain-English guidance
            # using HTTP 400 so the frontend can show it as a toast
            # (502 gets wrapped by Cloudflare into its own error page).
            if "billing" in err_msg.lower():
                guidance = (
                    "Google Cloud billing isn't enabled yet. Open "
                    "console.cloud.google.com/billing, link a credit card "
                    "to the project that owns this API key, then try again. "
                    "Google gives a $200/mo free credit — Maps Static + "
                    "Geocoding are essentially free at our usage volume."
                )
            elif "not authorized" in err_msg.lower() or "not enabled" in err_msg.lower() or "activated" in err_msg.lower():
                guidance = (
                    "The Geocoding API isn't enabled on this Google project. "
                    "Open console.cloud.google.com/apis/library, search for "
                    "'Geocoding API' and click ENABLE, then retry."
                )
            else:
                guidance = (
                    f"Google rejected the geocode request: {err_msg or 'check API key & enabled APIs'}"
                )
            raise HTTPException(status_code=400, detail=guidance)
        if status == "ZERO_RESULTS" or not payload.get("results"):
            raise HTTPException(status_code=404, detail=f"Address not found: {address!r}")
        if status != "OK":
            raise HTTPException(
                status_code=400,
                detail=f"Geocode returned status={status}: {err_msg}",
            )
        top = payload["results"][0]
        loc = top.get("geometry", {}).get("location", {})
        try:
            lat = float(loc["lat"])
            lon = float(loc["lng"])
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=502, detail=f"Bad geocode reply: {e}") from e
        resolved_label = top.get("formatted_address") or address
        # Track the precision Google reports — "ROOFTOP" is the most
        # accurate (great for our use case); RANGE_INTERPOLATED is good;
        # GEOMETRIC_CENTER and APPROXIMATE are looser. We surface this
        # so contractors know when they might need to drag the green
        # TARGET HOUSE box.
        location_type = top.get("geometry", {}).get("location_type", "")

        # 2) Fetch the satellite tile from Google Static Maps.
        try:
            img = await client.get(
                GOOGLE_STATIC_URL,
                params={
                    "center": f"{lat},{lon}",
                    "zoom": str(zoom),
                    "size": f"{size_px}x{size_px}",
                    "scale": str(DEFAULT_SCALE),
                    "maptype": "satellite",
                    "format": "jpg",
                    "key": api_key,
                },
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Google Static Maps fetch failed: {e}",
            ) from e
        if img.status_code != 200:
            body_preview = ""
            try:
                body_preview = img.text[:300]
            except Exception:
                pass
            low = body_preview.lower()
            if "not activated" in low or "not been used" in low or "is disabled" in low:
                guidance = (
                    "The Maps Static API isn't enabled on this Google project. "
                    "Open console.cloud.google.com/apis/library, search for "
                    "'Maps Static API' and click ENABLE, then retry."
                )
                raise HTTPException(status_code=400, detail=guidance)
            if "billing" in low:
                guidance = (
                    "Google Cloud billing isn't enabled yet. Open "
                    "console.cloud.google.com/billing and link a credit card "
                    "to the project that owns this API key, then retry."
                )
                raise HTTPException(status_code=400, detail=guidance)
            raise HTTPException(
                status_code=400,
                detail=f"Static Maps status={img.status_code} body={body_preview!r}",
            )
        ctype = img.headers.get("content-type", "").lower()
        if "image" not in ctype:
            raise HTTPException(
                status_code=502,
                detail=f"Static Maps returned non-image content-type {ctype!r}",
            )
        body = img.content
        if not body or len(body) < 2048:
            raise HTTPException(
                status_code=502,
                detail=f"Static Maps returned tiny payload ({len(body)} bytes)",
            )

    # 3) Burn target crosshair on geocoded center.
    body = _burn_target_marker(body, zoom)

    # 4) Persist to UPLOAD_DIR.
    filename = f"satellite-{uuid.uuid4().hex[:10]}.jpg"
    target: Path = UPLOAD_DIR / filename
    target.write_bytes(body)

    return {
        "filename": filename,
        "url": f"/api/uploads/{filename}",
        "lat": lat,
        "lon": lon,
        "address_resolved": resolved_label,
        "zoom": zoom,
        "size_px": size_px * DEFAULT_SCALE,
        "bytes": len(body),
        "location_type": location_type,
    }
