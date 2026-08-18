"""SEND-48 read-only probes.
1) Ruling YY structural test on the second FRONT ELEVATION title (Boni p3):
   does its band hold FIRST FLOOR + TOP OF PLATE datums and vertical rails?
2) Rail inventory: every vertical rail admitted into a datum gap across
   both houses, its value, and what structural context exists to
   distinguish a wall rail from an opening rail. NO value-based filters."""
import json
import os
import re
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('/app/backend/.env')
sys.path.insert(0, '/app/backend')
from height_read import (elevation_page_faces, furniture_index, datum_lines,
                         vertical_rails, gap_bind, face_bands)
from ocr_geometry import merge_positions

db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
HOUSES = {'boni': '65bcb89d-8291-4b84-920c-7b503273f332',
          'letrick': '264b6230-5d0f-49ea-b07d-8d33a537f293'}


def load(eid):
    r = db.ai_blueprint_runs.find_one({'estimate_id': eid, 'status': 'done'},
                                      sort=[('created_at', -1)])
    return r['result']['raw_ai']['_ocr_text_by_page']


report = {'ruling_yy_test': {}, 'rail_inventory': {}}
for house, eid in HOUSES.items():
    ot = load(eid)
    pages = elevation_page_faces(ot)
    furn = furniture_index(ot, set(pages))
    inv = []
    yy = {}
    for pg, bands in pages.items():
        raw_runs = ot[pg].get('runs') or []
        merged = merge_positions(raw_runs)
        for face, (y0, y1) in bands.items():
            lines = datum_lines(raw_runs, y0, y1, furn)
            rails = vertical_rails(merged, y0, y1)
            gaps = gap_bind(lines, rails)
            has_plate = any(L['name'] == 'TOP_OF_PLATE' for L in lines)
            has_floor = any(L['name'] == 'FIRST_FLOOR' for L in lines)
            yy[f'{face} p{pg}'] = {
                'band': [round(y0, 1), round(y1, 1)],
                'has_TOP_OF_PLATE': has_plate,
                'has_FIRST_FLOOR': has_floor,
                'vertical_rail_count': len(rails),
                'qualifies_as_height_source': bool(has_plate and has_floor and rails)}
            # rail inventory: every rail admitted into a datum gap
            for g in gaps:
                for r in g['rails']:
                    # structural context: nearby size-mark / opening
                    # strings within the rail's y-extent (text only —
                    # opening SYMBOLS are not text and are invisible here)
                    full = next((rr for rr in rails if rr['raw'] == r['raw']
                                 and rr['b0'] is not None), None)
                    inv.append({
                        'face': face, 'page': pg,
                        'gap': f"{g['from']} → {g['to']}",
                        'gap_status': g['status'],
                        'raw': r['raw'], 'inches': r['in']})
    report['ruling_yy_test'][house] = yy
    report['rail_inventory'][house] = inv

# structural-context survey: what text exists near admitted rails that
# could mark an opening (window size marks like 3050 / 2830, or letters)
for house, eid in HOUSES.items():
    ot = load(eid)
    pages = elevation_page_faces(ot)
    marks = []
    for pg in pages:
        for run in merge_positions(ot[pg].get('runs') or []):
            raw = (run.get('raw') or '').strip()
            if re.fullmatch(r'[2-9]0[2-8]0|[2-9][0-9][2-9][0-9]', raw.replace(' ', '')):
                marks.append({'page': pg, 'raw': raw,
                              'x': round(run['loc']['x_pct'], 1),
                              'y': round(run['loc']['y_pct'], 1)})
    report.setdefault('opening_mark_survey', {})[house] = marks

with open('/app/memory/send48_reports.json', 'w') as f:
    json.dump(report, f, indent=1)
print(json.dumps(report['ruling_yy_test'], indent=1))
print('--- rail inventory counts:',
      {h: len(v) for h, v in report['rail_inventory'].items()})
print('--- opening-mark survey counts:',
      {h: len(v) for h, v in report['opening_mark_survey'].items()})
