# Photo-Metadata Report — what survives the upload path (report only) — 2026-07-27

## (a) What actually survives — evidence from the real store (1,210 originals + 435 run photos on disk)

**The server is innocent; the stripping is client-side, at two rungs.**

Server path (verified in code): `/api/uploads` writes the received bytes
VERBATIM to disk and mirrors the same bytes to the Mongo blob store — no
transcode, no re-encode, no EXIF touch. The AI-measure `files=` branch
also persists raw bytes verbatim (`ai_*.jpg`). HEIC is accepted
(magic-byte sniff) and would be stored as-is.

Evidence from real files (PIL EXIF scan of the entire store):
- **Originals (1,210 files):** 135 carry any EXIF at all, and the richest
  payload observed is: `Orientation` + `ExifOffset` + padding tag 0xEA1C
  (127 files) — the signature of **iOS Safari's HEIC→JPEG auto-transcode
  on web file inputs**, which keeps orientation and DROPS the camera IFD.
  **Camera-level EXIF found: ZERO files** — no Make/Model, no FocalLength,
  no FocalLengthIn35mm, no LensModel, **no GPS anywhere**, no
  DateTimeOriginal (1 stray `DateTime`+`Software` file). **HEIC files on
  disk: ZERO** despite server acceptance — iOS never delivers HEIC through
  `<input type="file" capture="environment">` (our capture path,
  GuidedCaptureWizard/AIMeasureButton); it transcodes first.
- **Run photos (`ai_*`, 435 files):** EXIF **None across the board** —
  annotated photos are re-rendered through canvas
  (`photoAnnotate.js: canvas.toBlob("image/jpeg")`), which strips
  everything at re-encode. Both EST-986945 run photos and the 7pm run
  photos confirm: no EXIF.
- **Depth maps:** portrait/LiDAR depth lives in HEIC auxiliary images;
  web file inputs never deliver them. **Not present, not deliverable on
  the current capture path.** Boundary, named.

Summary table:

| field | survives today? | where lost |
|---|---|---|
| Orientation | YES (135 originals) | canvas re-encode drops it on ai_* copies |
| Camera make/model | NO | iOS web-input transcode (before upload) |
| Focal length / 35mm-equiv / lens | NO | same |
| GPS | NO (zero files) | same |
| DateTimeOriginal | NO (1 stray) | same |
| Depth maps | NO | never delivered via web file input |
| HEIC container | NO (zero files) | iOS transcodes before upload |

## (b) Persistence-only slice — sized, zero behavior change

Slice: on `/api/uploads` (+ the ai-measure files branch), parse EXIF
server-side (Pillow — already a dependency) into an additive metadata doc
`{orientation, make, model, focal_length, focal_35mm, lens, gps, datetime_original, image_wh, exif_present}`
stored on the Mongo blob record and echoed (additive field) in the upload
response. No consumer, no behavior change. Pins: pure-function extraction
test, upload contract additive-only, stored bytes byte-identical.
**Size: S (~0.5 day incl. pins).**

**The honest catch (this is the finding):** on the dominant capture path
there is currently NOTHING to persist — camera EXIF is destroyed BEFORE
our server ever sees bytes (iOS transcode), and again at annotation
(canvas). Persistence-only pays off immediately only for Android
Chrome / desktop uploads (which typically keep full EXIF). To actually
capture iPhone focal length, a **client-side capture slice** is the real
prerequisite: read EXIF from the original `File` in JS *before* the
canvas render and ship it as a JSON side-channel with the upload.
**Size: M (~1 day incl. pins).** Recommendation: if (c) is the goal, the
persistence-only slice alone will mostly persist absence; slice (b) +
client capture is the pair that makes the trial in (c) possible.

## (c) Logged — post-September scored trial (model-change rule)

"Extraction USE of focal length / FOV / depth as scale priors" is now on
the PRD backlog as a pre-registered scored-trial item under the
model-change rule — candidate to MERGE with the dormer-taxonomy prompt
trial (same harness: frozen fixture photos, scored deltas, no silent
prompt drift). No build, no wiring, recommendations only.
