import asyncio, json, os, sys, time
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient

RUN_ID = sys.argv[1]
OUT = f'/app/memory/evidence/s2_report_{RUN_ID}.json'

async def main():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    for _ in range(120):
        doc = await db.hover_import_runs.find_one({'run_id': RUN_ID}, {'_id': 0, 'status': 1, 'stage': 1, 'pdf_path': 1})
        print('status:', doc.get('status'), doc.get('stage'), flush=True)
        if doc.get('status') in ('done', 'error'):
            break
        await asyncio.sleep(10)
    pdf_path = doc.get('pdf_path')
    assert pdf_path and os.path.exists(pdf_path), f'S1 FAILED: pdf_path missing {pdf_path}'
    print('S1 OK —', pdf_path, os.path.getsize(pdf_path), 'bytes', flush=True)
    raw = open(pdf_path, 'rb').read()
    from routes.hover import _extract_pdf_text
    from routes.hover_elevation_read import read_elevation_geometry
    t0 = time.time()
    report = await read_elevation_geometry(raw, os.environ['EMERGENT_LLM_KEY'],
                                           session_id=f'elevread-cardinal-{RUN_ID}',
                                           schedule_text=_extract_pdf_text(raw))
    print('S2 read done in %.0fs, pages_read=%s' % (time.time() - t0, report.get('pages_read')), flush=True)
    from datetime import datetime, timezone
    await db.hover_import_runs.update_one(
        {'run_id': RUN_ID},
        {'$set': {'elevation_read': report,
                  'elevation_read_at': datetime.now(timezone.utc).isoformat()}})
    os.makedirs('/app/memory/evidence', exist_ok=True)
    json.dump(report, open(OUT, 'w'), indent=1, default=str)
    print('WROTE', OUT, flush=True)

asyncio.run(main())
