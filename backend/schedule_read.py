"""SEND-114 — THE SCHEDULE ROW PARSER (Howard ruled 2026-08-14).

ROWS, NOT STRINGS: a mark, its size and its count belong to one another
because they share a row — THE ROW IS THE EVIDENCE. A count cell that
will not OCR can still be LOCATED BY ITS ROW; where a count cannot be
established from its row, the mark REFUSES (named) — it NEVER collapses
to 1: a floor that looks like a count is what produced the 4, and
honoring unverified claims is what produced the 20.

Deterministic text over the existing OCR store (upright pass); no
graphics, no model. Doors and windows stay separate throughout.
Mark + size are NOT rebuilt here — the parser exists for the count cell
and for row association (plus deterministic recovery of exterior door
rows the model missed — the E3 class).

JURISDICTION: the parser governs a kind's counts ONLY where a table of
that kind carries a located COUNT column. A schedule with no count
column lists one opening per row — that convention is not this
parser's to overrule, so those rows stand untouched.
"""
import re

MARK_RE = re.compile(r"^[A-Z]{1,2}\d{0,2}$")
COUNT_RE = re.compile(r"^\d{1,2}$")
_HDR = {"mark": ("OPENINGID", "MARK"), "product": ("PRODUCTCODE",),
        "size": ("SIZE",), "count": ("COUNT", "QTY"),
        "type": ("LIBRARYNAME", "TYPE")}
_STOPS = ("WINDOWSCHEDULE", "DOORSCHEDULE", "FINALCONSTRUCTIONPRINTS",
          "LEGACYFEATURES")


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _cy(u: dict) -> float:
    return u["loc"]["y_pct"] + u["loc"].get("h_pct", 0) / 2.0


def _in_col(t: dict, key: str, u: dict, pad: float = 1.2) -> bool:
    """True when the token sits in the named column strip. A column the
    header scan never located imposes NO constraint for anchor keys
    (mark/product/size — matched by exact text), but the COUNT column
    must be located for count cells (a count is position, not text)."""
    c = t["cols"].get(key)
    if not c:
        if key == "count":
            return False
        cc = t["cols"].get("count")
        if cc and u["loc"]["x_pct"] >= cc[0] - 0.5:
            return False        # anchors always sit left of the counts
        return True
    mid = u["loc"]["x_pct"] + u["loc"].get("w_pct", 0) / 2.0
    return c[0] - pad <= mid <= c[1] + pad


def parse_tables(ot: dict) -> list[dict]:
    tables = []
    for pg in sorted((ot or {}).keys(), key=lambda x: int(x)):
        runs = [u for u in (ot[pg].get("runs") or [])
                if u.get("src") == "upright" and u.get("loc")]
        anchors, seen = [], []
        for u in runs:
            if _norm(u.get("raw")) not in ("WINDOWSCHEDULE",
                                           "DOORSCHEDULE"):
                continue
            if any(abs(u["loc"]["x_pct"] - b[0]) < 1.5
                   and abs(u["loc"]["y_pct"] - b[1]) < 1.0 for b in seen):
                continue
            seen.append((u["loc"]["x_pct"], u["loc"]["y_pct"]))
            anchors.append(u)
        for a in anchors:
            kind = "window" if "WINDOW" in _norm(a["raw"]) else "door"
            ax, ay = a["loc"]["x_pct"], a["loc"]["y_pct"]
            cols = {}
            for u in runs:
                x, y = u["loc"]["x_pct"], u["loc"]["y_pct"]
                if not (ay - 0.5 < y <= ay + 8 and ax - 12 <= x <= ax + 55):
                    continue
                n = _norm(u.get("raw"))
                for key, names in _HDR.items():
                    if n in names and key not in cols:
                        cols[key] = (x, x + u["loc"].get("w_pct", 0), y)
            t = {"page": int(pg), "kind": kind,
                 "count_column": "count" in cols, "cols": cols}
            hy = (max(c[2] for c in cols.values()) if cols else ay)
            x_lo = min([c[0] for c in cols.values()] + [ax]) - 6.0
            x_hi = max([c[1] for c in cols.values()] + [ax]) + 35.0
            stops = [u["loc"]["y_pct"] for u in runs
                     if u["loc"]["y_pct"] > hy + 0.4
                     and _norm(u.get("raw")) in _STOPS]
            stop = min(stops + [hy + 22.0])
            t["body"] = [u for u in runs
                         if hy + 0.35 < u["loc"]["y_pct"] < stop
                         and x_lo <= u["loc"]["x_pct"] <= x_hi]
            tables.append(t)
    return tables


def _count_tokens(t: dict) -> list[dict]:
    return [u for u in t.get("body") or []
            if _in_col(t, "count", u)
            and COUNT_RE.fullmatch((u.get("raw") or "").strip())]


def _size_wh(s: str):
    """Tolerant feet-inch pair extractor for size TEXT matching only
    (fractions dropped): "2'-11½\" x 4'-11½\"" → (35.0, 59.0)."""
    m = re.findall(r"(\d)\s*['′]?\s*-\s*(\d{1,2})", s or "")
    if len(m) >= 2:
        return (int(m[0][0]) * 12 + int(m[0][1]),
                int(m[1][0]) * 12 + int(m[1][1]))
    return None


def locate_row_y(t: dict, mark: str, product_code: str,
                 size_text: str = None):
    """Row anchor for a mark in this table: its mark token, else its
    (unique) product-code token, else its (unique) printed-size row —
    the size is used as LOCATING TEXT only, never as a value.
    Ambiguity refuses, never guesses."""
    mk = _norm(mark)
    if mk:
        hits = [u for u in t.get("body") or []
                if _in_col(t, "mark", u) and _norm(u.get("raw")) == mk]
        ys = sorted({round(_cy(h), 1) for h in hits})
        if len(ys) == 1:
            return _cy(hits[0]), "mark"
        if len(ys) > 1:
            return None, "mark token ambiguous in the table"
    pc = _norm(product_code)
    if len(pc) >= 5:
        hits = []
        for u in t.get("body") or []:
            if not _in_col(t, "product", u, pad=2.0):
                continue
            n = _norm(u.get("raw"))
            if len(n) >= 5 and (n == pc or pc.startswith(n)
                                or n.startswith(pc)):
                hits.append(u)
        ys = sorted({round(_cy(h), 1) for h in hits})
        if len(ys) == 1:
            return _cy(hits[0]), "product_code"
        if len(ys) > 1:
            return None, "product code repeats — row ambiguous"
    want = _size_wh(size_text)
    if want:
        hits = [u for u in t.get("body") or []
                if _in_col(t, "size", u)
                and _size_wh(u.get("raw")) is not None
                and abs(_size_wh(u.get("raw"))[0] - want[0]) <= 1.5
                and abs(_size_wh(u.get("raw"))[1] - want[1]) <= 1.5]
        ys = sorted({round(_cy(h), 1) for h in hits})
        if len(ys) == 1:
            return _cy(hits[0]), "printed_size"
        if len(ys) > 1:
            return None, "printed size repeats — row ambiguous"
    return None, "row not locatable (no mark or product token in OCR)"


def count_at(t: dict, y: float):
    toks = [u for u in _count_tokens(t) if abs(_cy(u) - y) <= 0.55]
    if len(toks) == 1:
        return int(toks[0]["raw"].strip()), None
    if len(toks) > 1:
        return None, ("count cell ambiguous (multiple integers in the "
                      "row band)")
    return None, "count cell empty in OCR at the located row"


def _drift_of(a: str, b: str) -> bool:
    """OCR drift guard: same digits, letter part one glyph off (F2~E2).
    A DIGIT difference (E3 vs E2) is a legitimate sibling mark."""
    if a == b:
        return True
    sa = re.match(r"^([A-Z]{1,2})(\d{0,2})$", a or "")
    sb = re.match(r"^([A-Z]{1,2})(\d{0,2})$", b or "")
    if not (sa and sb):
        return False
    return (sa.group(2) == sb.group(2)
            and len(sa.group(1)) == len(sb.group(1))
            and sum(1 for x, y in zip(sa.group(1), sb.group(1))
                    if x != y) == 1)


def _one_glyph(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) == 1
    return False


def read_schedule_counts(raw: dict) -> None:
    """Mutates raw in place. Governs ONLY marks whose counts the
    count-cell locator could not verify (count_by_page absent) and only
    where a COUNT column exists; locator-verified cells stand. Refusals
    set _count_unread — the mark contributes NOTHING, never a 1."""
    ot = raw.get("_ocr_text_by_page") or {}
    tables = parse_tables(ot)
    if not tables:
        return
    raw["_schedule_tables"] = [{"page": t["page"], "kind": t["kind"],
                                "count_column": t["count_column"]}
                               for t in tables]
    unread, row_counts = [], []
    for kind, coll in (("window", "windows"), ("door", "doors")):
        counted = [t for t in tables
                   if t["kind"] == kind and t["count_column"]]
        if not counted:
            continue        # no count column anywhere → no jurisdiction
        for r in raw.get(coll) or []:
            if not isinstance(r, dict):
                continue
            if r.get("count_by_page") or r.get("_count_unread") \
                    or r.get("_row_recovered"):
                continue
            mark = str(r.get("id") or "").strip()
            got, misses = 0, []
            for t in counted:
                y, basis = locate_row_y(
                    t, mark, r.get("product_code"),
                    r.get("printed_size")
                    or r.get("printed_size_not_located"))
                if y is None:
                    misses.append({"page": t["page"], "reason": basis})
                    continue
                n, why = count_at(t, y)
                if n is not None:
                    got += n
                    row_counts.append({"kind": coll, "mark": mark or "?",
                                       "page": t["page"], "count": n,
                                       "row_basis": basis})
                else:
                    misses.append({"page": t["page"], "reason": why})
            if got > 0:
                r["qty"] = got
                r["_row_count"] = got
            else:
                r["qty"] = 0
                r["_count_unread"] = True
                unread.append({"kind": coll, "mark": mark or "?",
                               "reason": "; ".join(
                                   f"p{m['page']}: {m['reason']}"
                                   for m in misses)
                               or "no schedule row located"})
    # ---- exterior door rows the read missed (the E3 class) ----
    recovered = []
    door_norms = {_norm(d.get("id")) for d in raw.get("doors") or []
                  if isinstance(d, dict)}
    for t in (t for t in tables if t["kind"] == "door"):
        for u in t.get("body") or []:
            if not _in_col(t, "mark", u):
                continue
            mk = _norm(u.get("raw"))
            if not (MARK_RE.fullmatch(mk) and mk[:1] in ("E", "G")
                    and any(ch.isdigit() for ch in mk)):
                continue
            if any(_drift_of(mk, x) for x in door_norms if x):
                continue
            y = _cy(u)
            band = [b for b in t["body"] if abs(_cy(b) - y) <= 0.55]
            blob = _norm(" ".join(b.get("raw") or "" for b in band))
            if "HOLLOWCORE" in blob:
                continue                       # interior row
            if "GARAGE" in blob:
                hint = "garage"
            elif "SLID" in blob or ("GLASS" in blob and "DO" in blob):
                hint = "sliding_glass_patio"
            else:
                raw.setdefault("_schedule_rows_unclaimed", []).append(
                    {"page": t["page"], "mark": mk})
                continue           # no exterior evidence — named, never guessed
            try:
                from routes.ai_blueprint import _parse_printed_size
            except Exception:
                _parse_printed_size = lambda s: None  # noqa: E731
            size_txt, parsed = None, None
            for b in band:
                cand = (b.get("raw") or "").strip()
                if _in_col(t, "size", b) and _parse_printed_size(cand):
                    size_txt, parsed = cand, _parse_printed_size(cand)
                    break
            if t["count_column"]:
                n, why = count_at(t, y)
            else:
                n, why = None, "COUNT column not located"
            d = {"id": mk, "printed_size": size_txt, "type_hint": hint,
                 "schedule_pages": [t["page"]], "_row_recovered": True,
                 "exterior_evidence": "schedule_row"}
            if parsed:
                d["width_in"], d["height_in"] = parsed
            if n is not None:
                d["qty"] = n
            else:
                # one mark row = one printed opening; the ROW is the
                # evidence for existence. Count stays the row itself
                # (1) ONLY when the table has no count column at all —
                # a count column whose cell is empty refuses instead.
                if t["count_column"]:
                    d["qty"] = 0
                    d["_count_unread"] = True
                    unread.append({"kind": "doors", "mark": mk,
                                   "reason": f"p{t['page']}: {why} "
                                             f"(row recovered)"})
                else:
                    d["qty"] = 1
                    d["count_basis"] = "one schedule row (no count column)"
            raw["doors"] = (raw.get("doors") or []) + [d]
            door_norms.add(mk)
            recovered.append({"mark": mk, "page": t["page"],
                              "type_hint": hint,
                              "size": size_txt, "count": d.get("qty")})
    if row_counts:
        raw["_schedule_row_counts"] = row_counts
    if unread:
        raw["_schedule_count_unread"] = unread
    if recovered:
        raw["_schedule_rows_recovered"] = recovered
