"""SEND-114 probe — run the schedule row parser against the STORED runs
of both houses (deep copies, READ-ONLY) and score against the seal."""
import copy
import os
import sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient


def main():
    from schedule_read import read_schedule_counts
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for house, eid in [("BONI", "65bcb89d-8291-4b84-920c-7b503273f332"),
                       ("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293")]:
        run = db.ai_blueprint_runs.find_one(
            {"estimate_id": eid, "status": "done"},
            sort=[("created_at", -1)])
        raw = copy.deepcopy((run.get("result") or {}).get("raw_ai") or {})
        if not raw.get("_ocr_text_by_page") and raw.get("_ocr_text_ref"):
            raw["_ocr_text_by_page"] = (db.ai_blueprint_ocr.find_one(
                {"run_id": raw["_ocr_text_ref"]},
                {"pages": 1}) or {}).get("pages")
        # reset the quarantine-era state the stored run carries so the
        # parser sees the same field shapes a live run would
        read_schedule_counts(raw)
        print(f"\n######## {house} ########")
        print("tables:", raw.get("_schedule_tables"))
        for coll in ("windows", "doors"):
            for r in raw.get(coll) or []:
                print(f"  {coll[:-1]} {r.get('id')}: qty={r.get('qty')} "
                      f"row_count={r.get('_row_count')} "
                      f"unread={r.get('_count_unread')} "
                      f"recovered={r.get('_row_recovered')} "
                      f"w={r.get('width_in')} h={r.get('height_in')}")
        print("row_counts:", raw.get("_schedule_row_counts"))
        print("unread:", raw.get("_schedule_count_unread"))
        print("recovered:", raw.get("_schedule_rows_recovered"))
        print("unclaimed:", raw.get("_schedule_rows_unclaimed"))
        # score: instance counts + deduction area from surviving rows
        tot_area = w_n = d_n = 0
        for coll in ("windows", "doors"):
            for r in raw.get(coll) or []:
                if r.get("_count_unread"):
                    continue
                q = int(r.get("qty") or 0)
                a = (float(r.get("width_in") or 0)
                     * float(r.get("height_in") or 0)) / 144.0
                tot_area += q * a
                if coll == "windows":
                    w_n += q
                else:
                    d_n += q
        print(f"SCORE {house}: windows={w_n} doors={d_n} "
              f"deduction={tot_area:.1f} ft2")


main()
