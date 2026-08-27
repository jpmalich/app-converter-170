# SEND-132 — RECTIFICATION REPORT (report only, no build, no correction factor)

Howard's question: a two-tap anchor gives a LINEAR scale valid along one
line at one depth. Area from a perspective photo needs a homography. The
×4 result proved the ruler drives the quantity; it did not prove the area
is right. Below is what the shipped ft² math actually assumes, and what
can and cannot be established from what is in frame today.

---

## 1. WHAT THE ft² COMPUTATION ASSUMES ABOUT THE PHOTO'S GEOMETRY

The code is four lines (`routes/photo_takeoff.py`):

```
ipp        = inches / span_px            # from the two-tap anchor or the tape
sq_ft_px   = (ipp * ipp) / 144
area_ft2   = shoelace_area_px(points) * sq_ft_px
```

Every one of the following is ASSUMED, and none of it is measured:

1. **ONE SCALE FOR THE WHOLE PHOTO.** `ipp` is a single number applied to
   every pixel in the frame. The anchor was taped along ONE line at ONE
   depth; the math extends it to the entire image.
2. **NO PERSPECTIVE (SCALED ORTHOGRAPHIC PROJECTION).** `ipp²` for area
   is only valid if the image is an orthographic projection of a single
   plane — i.e. the camera is infinitely far away or the wall is exactly
   fronto-parallel. In a real photo, scale falls off with depth, so a
   wall receding from the camera reads SMALLER per foot at its far end.
3. **THE ZONE LIES IN THE SAME PLANE AS THE ANCHOR, AT THE SAME DEPTH.**
   A zone traced on a wall that turns away from the anchor's plane is
   measured with the anchor's plane's scale.
4. **ISOTROPY** — the same inches-per-pixel horizontally and vertically.
   A two-tap anchor along a horizontal course says nothing about the
   vertical rate under perspective or lens tilt.
5. **NO LENS DISTORTION.** Phone wide-angle barrel distortion is not
   modelled; straight walls bow, and a traced polygon inherits the bow.
6. **THE POLYGON IS PLANAR AND SIMPLE.** The shoelace formula measures
   the polygon's area in the IMAGE PLANE — the wall's PROJECTION, not
   the wall.

**Consequence, stated plainly.** On a fronto-parallel photo the figure is
sound within the anchor's own error. On an oblique photo the figure is
the projected area, which is systematically SMALLER than the true wall,
by roughly cos(θ) for a simple rotation of angle θ about a vertical axis
(≈13% low at 30°, ≈29% at 45°, ≈50% at 60°), and the error is NOT
uniform across the zone because near and far ends carry different
scales. **The linear tape is the right ruler; the area is only as right
as the assumption that the wall faces the camera.** Today nothing in the
system tests that assumption, and nothing in the payload says so.

---

## 2. CAN A HOMOGRAPHY BE ESTABLISHED FROM ANYTHING IN FRAME?

A plane-to-plane homography needs **4 point correspondences on ONE plane
with known metric positions** (or equivalent constraints: two vanishing
points plus one known length, or one rectangle of known aspect ratio).

What is already available on a photo TODAY:

| Source | What it gives | Enough for a homography? |
|---|---|---|
| **A boxed opening with typed width AND height** (Stage 1 typed style/height, or the AI read's `width_in`/`height_in` + normalised bbox) | 4 corners of a rectangle of KNOWN metric size on the wall plane | **YES — this is the one clean source.** One such opening = 4 correspondences = a full homography for that plane |
| **Two or more boxed openings with known sizes** | 8+ correspondences, over a wider baseline | YES, and better conditioned — plus a residual that MEASURES the fit |
| Two-tap anchor + typed tape | 2 correspondences on one line | NO — a line gives scale along itself, never a plane |
| Siding course lines / brick courses (regular spacing, known exposure) | a vanishing point + a metric rate | Partially: with a second direction it gives the plane, but the exposure is a PRODUCT setting, not a measurement of THIS wall — using it as a ruler is the closed brick-course-as-scale question and stays closed |
| Corners of the house, roofline | vanishing directions only | NO metric scale on their own |

**So: yes, a homography is establishable — but ONLY on a photo that
carries at least one opening with a real width AND height, and only for
the plane that opening sits in.** An opening whose height was never typed
and never read gives 4 corners with no metric size: it fixes the shape,
not the scale.

**A further honest note:** a rectangle of known aspect ratio (even
without its size) is enough to RECTIFY (remove perspective), and the
tape then supplies the single missing scale factor. That combination —
one boxed opening for the plane + the tape for the length — is the
strongest ruler available from what a contractor already gives us. It
also produces a **residual**: after rectification, other known openings
on that wall must measure their typed sizes. Where they do not, the
photo tells us the fit is wrong. **That residual is evidence, not a
correction factor.**

---

## 3. CAN A PHOTO BE CLASSIFIED FRONT-ON VERSUS OBLIQUE?

**Yes, and without any new AI.** From marks already on the photo:

1. **From one boxed opening with typed width and height** — compare the
   opening box's pixel aspect ratio against its typed metric aspect
   ratio, corrected for nothing. On a fronto-parallel photo they agree.
   The disagreement is a direct, measured indicator of obliquity. It
   also has a sign: a wall turning away compresses horizontally.
2. **From two boxed openings at different depths on the same wall** —
   compare their inches-per-pixel. Under an orthographic assumption they
   must match. A ratio far from 1.0 means the scale falls off across the
   frame; that IS obliquity, measured in the photo's own evidence.
3. **From the vertical edges** of two or more openings, or the house
   corners, if the contractor traced them: converging verticals /
   horizontals give a vanishing point at finite distance — a
   fronto-parallel plane sends it to infinity.
4. **Weakest, and NOT sufficient alone**: EXIF focal length and
   orientation. It says nothing about where the wall faces.

Where NONE of these is present the honest answer is **UNKNOWN**, and the
right output is a named refusal-grade caveat on the figure, not a
classification guessed from the picture's look. **A "front-on" label the
photo cannot support is the same defect as an invented ruler.**

---

## 4. WHAT AN OBLIQUE PHOTO SHOULD DO

Recommended, in the project's own doctrine (nothing here is built):

1. **NAME IT ON THE FIGURE.** The quantity payload gains a
   `plane_basis` that says which of these the ft² rests on:
   `fronto_parallel_assumed` (today's silent default, made loud),
   `oblique_detected`, or `unknown`. A figure whose plane basis is
   `oblique_detected` or `unknown` is **still reported, but it is
   reported WITH its caveat** — the contractor is told the ruler
   measured the wall's projection.
2. **PREFER THE HOMOGRAPHY WHERE THE PHOTO EARNS ONE.** Where a boxed
   opening with a real width and height exists on the wall, rectify from
   THAT MEASURED evidence and report the residual against every other
   known opening on the plane. Where the residual is bad, refuse the
   area, keep the marks.
3. **REFUSE, DO NOT CORRECT, WHERE OBLIQUITY IS DETECTED AND NO
   HOMOGRAPHY IS AVAILABLE.** An oblique photo with no metric rectangle
   cannot yield an area. Refusing by name ("this photo is oblique and
   carries no opening with a known width and height — no area from this
   photo; retake it square to the wall, or type a window's width and
   height") is worth more than a number nobody can defend.
4. **ASK FOR THE ONE THING THAT FIXES IT.** The cheapest ask in the
   whole system: type ONE window's width and height on the oblique
   photo. That single act converts an unusable photo into a rectifiable
   plane. The editor already has the field (SEND-132 Stage 1).
5. **NEVER A CORRECTION FACTOR.** No cos(θ) from a guessed θ, no
   "typical wall angle", no learned fudge. A perspective correction from
   an unmeasured angle is a fabricated ruler — the same class of defect
   as a width carried in from a blueprint.

## 5. WHAT IS SHIPPED TODAY, SO THE RECORD IS STRAIGHT
- The area math is the scaled-orthographic one above.
- The payload does **not** yet carry a `plane_basis`, so a fronto-parallel
  assumption is currently silent. **That silence is the first thing to
  fix if Howard authorises any of this** — naming the assumption is not
  a perspective correction, it costs nothing, and it takes the figure out
  of the class of numbers that look measured and are not.
- **Nothing in this report is built.** No homography, no classifier, no
  factor, no plane_basis. Report only, per the ruling.
