"""SEND-45 read-only probe. Height Build draft dry run. NO BINDING, NO WRITES.
Evaluates the DRAFT mechanism (face->drawing band via sub-titles, datum labels,
vertical rails, grade labels) against stored OCR for Boni + Letrick."""
import os, re, json, sys
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
sys.path.insert(0, '/app/backend')
from ocr_geometry import normalize_marks, is_dimension_like, axis_class, glyph_count, merge_positions

db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
HOUSES = {'boni': '65bcb89d-8291-4b84-920c-7b503273f332',
          'letrick': '264b6230-5d0f-49ea-b07d-8d33a537f293'}

def load_ocr(eid):
    r = db.ai_blueprint_runs.find_one({'estimate_id': eid, 'status': 'done'}, sort=[('created_at', -1)])
    raw = r['result']['raw_ai']
    ot = raw.get('_ocr_text_by_page')
    if not ot and raw.get('_ocr_text_ref'):
        ot = db.ai_blueprint_ocr.find_one({'run_id': raw['_ocr_text_ref']})['pages']
    return r['run_id'], ot

def squash(s):
    return re.sub(r'[^A-Z]', '', (s or '').upper())

SUBTITLES = {'front': 'FRONTELEVATION', 'rear': 'REARELEVATION',
             'left': 'LEFTELEVATION', 'right': 'RIGHTELEVATION'}
DATUM = ['TOPOFPLATE', 'FIRSTFLOOR', 'SECONDFLOOR', 'PTPLATE', 'TOPOFWALKOUTFOOTER',
         'TOPOFFOOTER', 'TOPOFFOUNDATION', 'BASEMENTFLOOR', 'GARAGEFLOOR', 'TOPOFSUBFLOOR']
GRADE_LINE = ['APPROXGRADE', 'GRADE@', 'FINISHGRADE', 'FINISHEDGRADE']

def cy(r): return r['loc']['y_pct'] + r['loc']['h_pct'] / 2
def cx(r): return r['loc']['x_pct'] + r['loc']['w_pct'] / 2

report = {}
for house, eid in HOUSES.items():
    run_id, ot = load_ocr(eid)
    hrep = {'run_id': run_id, 'pages': {}}
    for pg in ('1', '2'):
        runs = merge_positions(ot[pg]['runs'])
        prep = {'subtitles': [], 'datums': [], 'grade_labels': [], 'vertical_dims': []}
        for r in runs:
            sq = squash(r['raw'])
            sqg = re.sub(r'[^A-Z@]', '', (r['raw'] or '').upper())
            for face, st in SUBTITLES.items():
                if st in sq:
                    prep['subtitles'].append({'face': face, 'raw': r['raw'], 'y': round(cy(r), 1), 'x': round(cx(r), 1)})
            for d in DATUM:
                if d in sq:
                    prep['datums'].append({'label': d, 'raw': r['raw'], 'y': round(cy(r), 1), 'x': round(cx(r), 1)})
                    break
            for g in GRADE_LINE:
                if g in sqg and 'NOTES' not in sq and 'BEAM' not in sq:
                    prep['grade_labels'].append({'label': g, 'raw': r['raw'], 'y': round(cy(r), 1), 'x': round(cx(r), 1)})
                    break
            norm = normalize_marks(r['raw'])
            if is_dimension_like(norm):
                ax = axis_class(r['loc'], glyph_count(r['raw']))
                if ax == 'VERTICAL':
                    prep['vertical_dims'].append({'raw': r['raw'], 'y': round(cy(r), 1), 'x': round(cx(r), 1),
                                                  'y0': round(r['loc']['y_pct'], 1),
                                                  'y1': round(r['loc']['y_pct'] + r['loc']['h_pct'], 1)})
        for k in prep:
            if isinstance(prep[k], list):
                prep[k].sort(key=lambda d: (d.get('y', 0), d.get('x', 0)))
        hrep['pages'][pg] = prep
    report[house] = hrep

print(json.dumps(report, indent=1))
