"""SEND-113 probe — openings/schedule evidence, both houses. READ-ONLY."""
import os
import re
import sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

HOUSES = [("BONI", "65bcb89d-8291-4b84-920c-7b503273f332"),
          ("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293")]


def ocr_for(db, eid):
    run = db.ai_blueprint_runs.find_one(
        {"estimate_id": eid, "status": "done"}, sort=[("created_at", -1)])
    raw = (run.get("result") or {}).get("raw_ai") or {}
    ot = raw.get("_ocr_text_by_page")
    if not ot and raw.get("_ocr_text_ref"):
        ot = (db.ai_blueprint_ocr.find_one(
            {"run_id": raw["_ocr_text_ref"]}, {"pages": 1}) or {}).get("pages")
    return ot


def main():
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    hdr = re.compile(r"SCHEDULE|^MARK$|^COUNT$|^QTY$|^SIZE$|ROUGHOPEN", re.I)
    plc = re.compile(r"^G-?1$|^G-?2$|GARAGE|16'-0|9'-2|OVERHEAD", re.I)
    elv = re.compile(r"ELEVATION", re.I)
    for house, eid in HOUSES:
        ot = ocr_for(db, eid)
        print(f"\n######## {house} ########")
        for pg in sorted(ot.keys(), key=int):
            runs = ot[pg].get("runs") or []
            hh = [(u["raw"], round(u["loc"]["x_pct"], 1),
                   round(u["loc"]["y_pct"], 1)) for u in runs
                  if hdr.search(u.get("norm") or "")]
            ph = [(u["raw"], round(u["loc"]["x_pct"], 1),
                   round(u["loc"]["y_pct"], 1)) for u in runs
                  if plc.search(u.get("norm") or "")
                  or plc.search(u.get("raw") or "")]
            eh = [(u["raw"], round(u["loc"]["x_pct"], 1),
                   round(u["loc"]["y_pct"], 1)) for u in runs
                  if elv.search(u.get("raw") or "")]
            if hh:
                print(f"  p{pg} HEADERS: {hh[:8]}")
            if eh:
                print(f"  p{pg} ELEV LABELS: {eh[:6]}")
            if ph:
                print(f"  p{pg} GARAGE/G1/G2/SIZES: {ph[:12]}")
        # row recovery around any SCHEDULE header: band runs by y and
        # print reconstructed rows (text left→right)
        for pg in sorted(ot.keys(), key=int):
            runs = ot[pg].get("runs") or []
            heads = [u for u in runs if "SCHEDULE" in (u.get("norm") or "")]
            for h in heads:
                hx, hy = h["loc"]["x_pct"], h["loc"]["y_pct"]
                print(f"\n  == p{pg} table under '{h['raw']}' @({hx:.1f},{hy:.1f}) ==")
                near = [u for u in runs
                        if hy - 1 <= u["loc"]["y_pct"] <= hy + 25
                        and abs(u["loc"]["x_pct"] - hx) <= 25]
                near.sort(key=lambda u: u["loc"]["y_pct"])
                rows, cur, cy = [], [], None
                for u in near:
                    y = u["loc"]["y_pct"]
                    if cy is None or y - cy <= 0.45:
                        cur.append(u)
                        cy = y if cy is None else max(cy, y)
                    else:
                        rows.append(cur)
                        cur, cy = [u], y
                if cur:
                    rows.append(cur)
                for row in rows[:18]:
                    row.sort(key=lambda u: u["loc"]["x_pct"])
                    txt = " | ".join((u["raw"] or "?") for u in row)
                    print(f"    {txt[:150]}")


main()
