"""Baseline capture of elevation-sheet payloads for fixture re-look gating."""
import asyncio, os, sys, json, hashlib
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ESTS = {
    "doug_jones": "db82ec7a-3177-406d-a602-927255e9e10e",
    "letrick": "8f95c9c2-add9-416a-92f3-786a4ea2ce83",
    "haugh": "48231310-3872-4d4e-b657-35ade10c1cb8",
    "red_house": "673707d5-9b7e-4d8f-8eaf-63c86820f611",
    "est_986945": "e3c469df-3b40-442e-88ea-89ad62ff473c",
}


async def main(outfile):
    from routes.elevation_sheets import elevation_sheet
    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    user_doc = await db.users.find_one({"email": "hhunt6677@yahoo.com"}, {"_id": 0})
    out = {}
    for name, eid in ESTS.items():
        for which in ("front", "back", "left", "right"):
            try:
                d = await elevation_sheet(eid, which, user_doc)
            except Exception as e:
                out[f"{name}/{which}"] = f"ERROR {e}"
                continue
            d.pop("generated_date", None)
            s = json.dumps(d, sort_keys=True, default=str)
            out[f"{name}/{which}"] = {
                "hash": hashlib.sha256(s.encode()).hexdigest()[:16],
                "dormer_center": (d.get("dormer") or {}).get("center_ft"),
                "openings": [(o["tag"], o["center_ft"]) for o in d["openings"]],
                "payload": d,
            }
    with open(outfile, "w") as f:
        json.dump(out, f, indent=1, default=str)
    for k, v in out.items():
        if isinstance(v, str):
            print(k, v)
        else:
            print(k, v["hash"], "dormer_center", v["dormer_center"])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
