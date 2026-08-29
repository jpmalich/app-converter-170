# SEND-148 — A START LINE HE JUST MARKED OUTRANKS THE OLD DRAG

Howard ruled 2026-08-29, after SEND-147 protected his FRONT tweak too well:

> *"FRONT's tweaked body should FOLLOW the wall_base tap. A start line he just
> marked outranks the old drag. Do not clear the zone. Do not touch the gable.
> RIGHT stays refused."*

Stamp, verbatim from `scripts/handback_green.sh`:

```
RECORDED: 2026-08-29 12:58 UTC · 85ee83a · CLEAN
RESULT: 3160 passed, 9 skipped, 7 warnings in 437.86s (0:07:17)
CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none); 8 removal(s) logged (see baseline REMOVAL_LOG)
INGRESS SMOKE: 4 passed in 2.05s
```

7 pins in `tests/test_send148_start_line_outranks_the_drag_2026_08_29.py`,
1 SEND-147 pin re-titled BY NAME.

---

## 1. THE RULE, EXACTLY AS RULED

`_bottom_follows_the_line()` in `photo_zone_proposals.py`:

- **THE BODY FOLLOWS, AND ONLY ITS BOTTOM EDGE.** The two LOWEST vertices of
  the box he already moved go to the tapped line's y. **NOT ONE x CHANGES** and
  the top edge does not move.
- **THE ZONE IS NOT CLEARED AND NOT RE-PLACED.** It is one `update_one` on the
  same mark id — no delete, no insert, no new id, and **his own basis survives
  with the new sentence APPENDED**.
- **HIS SIDES AND HIS TOP ARE HIS EVIDENCE**, so the basis says the
  consequence out loud: *"your sides and your top are yours and they stayed,
  which means this box's HEIGHT is now YOURS and not the read's… the ft² still
  comes from the shape you confirm."*
- **A TOUCHED GABLE OR DORMER IS NOT TOUCHED AT ALL** — it is refused by name
  and told what would change it: *"'AI front gable' was not moved: … your hand
  outranks the anchor. Delete it if you want it re-placed on the line you
  tapped."*
- **NO START LINE → NOTHING FOLLOWS.** Deleting a line never drags a
  hand-moved body back; only a FRESH zone reverts to the read's own answer. A
  bottom already sitting on the line is left alone rather than written for the
  sake of writing.
- **A CONFIRMED BODY GOES BACK TO PROVISIONAL** when its bottom moves, with
  the reason stored: *"the bottom moved to the wall_base line you tapped —
  re-confirm the new figure"*. **A confirmation cannot outlive the figure it
  was given for.**
- `ai.anchor` becomes `wall_base_mark`, `ai.anchor_wall_base_y` records the y
  and `ai.bottom_followed_your_line: true` marks how it got there. The read's
  own claim (`run_id`, the measured figures) is not rewritten.
- **RIGHT STAYS REFUSED**, pinned again in this send: a start line is not a
  licence to place a box on a wall nobody measured.

## 2. RUN FOR REAL ON FRONT (EST-176308)

| | x span | y span | anchor |
|---|---|---|---|
| before the tap | 373.9 → 2003.0 | 739.3 → **1386.9** | `first_floor_openings` |
| after a line tapped at y=1448 | **373.9 → 2003.0, unchanged** | **739.3 unchanged → 1448.0** | `wall_base_mark` |
| AI front gable | 373.9 → 2010.7 | 335.9 → 739.3 | **untouched, both before and after** |

Report from the tap: `moved: 1`, and three sentences — the body's move, the
gable's named refusal, and *"A body you had moved by hand keeps its own sides
and top — only its BOTTOM followed the line; a gable or dormer you touched was
not moved at all."*

## 3. SOMETHING I GOT WRONG, AND IT WAS YOURS

**I deleted the wall_base line YOU tapped on LEFT.** At 05:00:12 UTC you
tapped a start line on the LEFT photo and your LEFT body followed it to
**y = 322.706 px** — SEND-147 working exactly as ruled. Six hours later,
testing this send, I cleared "my own test lines" off EST-176308 with a
`delete_many` on `kind: wall_base` and **took yours with mine**. There were 2;
one was mine on FRONT, one was yours on LEFT.

What survives and what does not:
- **YOUR y SURVIVED.** The LEFT body still sits on **322.7 px**, and
  `ai.anchor_wall_base_y = 322.706` on that zone is the record of your tap. I
  did **NOT** move it back to the sill line and I did **NOT** re-base that
  photo.
- **YOUR LINE'S TWO ENDS DID NOT SURVIVE.** Only the mean y was ever recorded
  on the zone, so I cannot put your `a` and `b` back. **I will not
  reconstruct them** — invented endpoints would be exactly the kind of figure
  this app refuses to fabricate. **One tap on LEFT puts the line back**, and
  your body is already on its y.
- **YOUR FRONT BOX IS BACK WHERE YOU LEFT IT**: after the test I restored its
  bottom to **1386.9 px**, stripped my test sentence from its basis and put
  `anchor: first_floor_openings` back. Its sides and top were never touched.
  **Your FRONT gable and your BACK gable were never touched at all.**
- There is **no wall_base mark on any photo of EST-176308 right now** (0 in the
  collection).

**What I will do differently**: a delete of another person's mark on a live
estimate is not a cleanup. From here, a test line gets its id recorded when it
is created and only THAT id is deleted — never a `delete_many` by kind on your
data.

## 4. NOT AUTHORISED, NOT TOUCHED

The zone was not cleared · the gable was not touched · RIGHT refused · no
detector · no corner tick, eave, soffit or fascia · no quote wiring, no
prices · no second finder, no re-OCR · EST-886440 untouched.
