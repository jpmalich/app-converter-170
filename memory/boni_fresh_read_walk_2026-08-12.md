# FRESH BONI RE-READ — SEND-6 ACCEPTANCE WALK

**Reader**: Claude Sonnet 5 via ai-blueprint pipeline (SEND-6 prompt).
**Estimate**: EST-886440 · Boni 8-6-26 4pm · protected: True.
**Prev run** (send-3, 3 planes): `80c10620d87641e4b275dd06ac4f2705`.
**Fresh run** (send-6 prompt): `5df22e6d399c4401a959c83853d3dd04`.
**Completed**: 2026-08-12 20:01 UTC.

Snapshot: `memory/boni_fresh_read_2026-08-12.json`.

I am reporting what the read RETURNED before Howard walks it. Purity
rule (Howard, permanent): every dimension below is EVIDENCE for a
ruling, never a constant, default, fallback, or assertion target. Where
the read disagrees with Howard's stated purity, I NAME THE
DISAGREEMENT and leave the interpretation to the walk.

## Howard's five acceptance checks

### 1. Does a FOURTH PLANE appear? — YES

`roof_planes` returned **four entries** (was three):

| # | label | gable_ends | gable_end_faces | pitch | is_porch |
|---|-------|-----------:|:----------------|:------|:---------|
| 1 | main | 2 | [left, right] | 7/12 | no |
| 2 | bonus room | 2 | [front, back] | 10/12 | no |
| 3 | porch | 0 | [] | (empty) | yes |
| 4 | garage | 2 | [front, back] | 10/12 | no |

The send-3 read carried `garage/bonus` as a single lumped plane with
gable_ends=2. The send-6 read has **split it into two separate
planes**: `bonus room` and `garage`, each with its own gable_ends=2
and its own pitch.

### 2. Entry gable — its own plane at 10/12 with own rake / soffit / area? — DISAGREEMENT

**No plane is labeled `entry`.** The read split the previous
`garage/bonus` into `bonus room` + `garage` — but neither is the entry
gable over the front door.

**Both** `bonus room` and `garage` returned:
- `gable_ends: 2`
- `gable_end_faces: ["front", "back"]`
- `pitch: "10/12"`

**Total gable ends across planes = 2 + 2 + 0 + 2 = 6.** Howard's
purity list implies 4 visible gable ends. The read now **over-counts
by 2**. Reading the shape honestly:
- Both `bonus room` and `garage` claim a gable end on FRONT and a
  gable end on BACK. That is four ends between them, all on the F+B
  axis.
- The main body has two on L+R.
- One F-facing end is very likely the ENTRY gable Howard walked, but
  the read has emitted it as one of `bonus room.front` or
  `garage.front` rather than as its own plane.
- If Howard's four is the truth, then EITHER `bonus room` has no
  gable end at all OR `garage` does — one of them is inflated in this
  read, and the entry plane is still missing its own body.

**The extraction fix took partially.** It stopped hiding an end inside
a lumped plane (`garage/bonus`) but it did not emit a dedicated `entry`
plane. Howard's ruling on this class stands: if this is wrong, the
seam guard now catches nothing because both planes emit
`gable_end_faces` — attribution reconciles, no orphans fire, and
`gable_census_mismatch` goes silent (see #5 below). **The extraction
side has more to say here, if the read is over-counting.**

### 3. Is the ORPHAN BAND gone? — YES

Attribution ran: 6 plane-side gable ends, 6 attributed to walls, **0
orphans**, `census_reconciled: true`. The red `UNATTRIBUTED WING
GABLE(S) — NEEDS YOUR TAPE` band that would have fired otherwise is
absent because every plane emitted its own `gable_end_faces`
evidence. If the read is over-counting (see #2), the census reconciles
FALSELY — the seam guard cannot see that.

### 4. Does the garage wall QUOTE 9'-11 7/8"? — DISAGREEMENT

The garage plane emitted:
```
wall_height_ft: {"v": 9.5, "page": 1, "from": "9'-6\" garage wall"}
```

**The read quoted 9'-6", not 9'-11 7/8".** Both are plausible printed
dimensions on a garage wall (one is likely the interior/plate line and
one the siding line). The read located a printed dim and quoted it
verbatim — the mechanism is correct — but it picked a DIFFERENT
dimension than the one on Howard's purity list. Either:
- The drawing prints both and the model landed on the wrong one, or
- The drawing prints only 9'-6" and Howard's 9'-11 7/8" is the sided
  height built up FROM 9'-6" (plates + foundation).

The rail also fires `wall_height_by_plane: garage=9.5 ft` — so the
disclosure surfaces the value, additions to reach the sided height
named separately (never silently added).

### 5. Has gable_census_mismatch FINALLY GONE SILENT? — YES

`check_read_consistency` returned **no** `gable_census_mismatch` flag.
6 plane ends = 6 attributed ends, 0 orphans. Census reconciles.

**Caveat, per #2:** the census goes silent because the read now
supplies `gable_end_faces` on every plane — the attribution has
evidence for every end. If the read is over-counting (6 vs Howard's
4), the census reconciles on a false total. The instrument works; the
disagreement is now upstream of it, in the extraction.

## Other consistency flags that fired (unrelated to gables)

- `porch_dims_vs_area` (loud): 32.5 × 6 = 195 but printed area 99.
  Roughly 2× disagreement — possibly the read is treating two porches
  as one, or width/depth crossed.
- `corner_walk_conflict` (loud): perimeter walk 12 outside / 8 inside
  vs printed 8 / 4. Roughly 2× disagreement in the other direction.
  Both worth Howard's walk if he cares to look.
- `wall_segment_undimensioned` (warn): back wall's garage/bonus wing
  height segment unread. New warn; not a fresh regression.

## Rail codes fired (send-6 surfaces)

| level | code | text |
|:------|:-----|:-----|
| info | pitch | 7/12 |
| info | pitch_varies_by_plane | bonus room=10/12; garage=10/12 |
| warn | pitch_missing_on_planes | porch |
| warn | overhang_default | (still fires; house-level overhang unread) |
| info | overhang_by_plane | garage=12" |
| warn | overhang_missing_on_planes | main, bonus room |
| info | wall_height_by_plane | garage=9.5 ft |

The send-6 surface is doing what it was built to do: naming WHICH
planes carry pitch, overhang, and wall-height reads — and WHICH ones
don't. The picture below is what a walker sees:
- Main body pitch 7/12 printed; bonus room + garage both 10/12
  (differs from main — surfaced).
- Overhang is 12" on the garage plane only; main + bonus room have no
  printed overhang in this read.
- Garage wall height 9.5 ft printed; every other wall relies on the
  main-wall list.

## Summary (evidence, no rulings)

- Fourth plane: yes.
- Entry as its own plane: NO.
- Gable-end count across planes: 6 (Howard walked 4).
- Garage wall quotation: 9'-6" (Howard's number: 9'-11 7/8").
- Orphan band: absent — evidence provided on every plane.
- gable_census_mismatch: silent — reconciles on the read's 6.

**What I did NOT do:** patch base_ft, hint the prompt harder toward
"entry" as a required label, or shape the read toward Howard's
purity list. The read said what it said; I am reporting it verbatim.

## Handoff

Snapshot: `memory/boni_fresh_read_2026-08-12.json` (full raw_ai,
walls, rail, corner counts, notes). Ready for the walk.
