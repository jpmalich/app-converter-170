import os, re, json
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
c = MongoClient(os.environ['MONGO_URL'])
db = c[os.environ['DB_NAME']]
r = db.ai_blueprint_runs.find_one({'estimate_id':'65bcb89d-8291-4b84-920c-7b503273f332','status':'done'}, sort=[('created_at',-1)])
raw = r['result']['raw_ai']
ot = raw['_ocr_text_by_page']

# dimension-like: feet-inches pattern in raw, or norm like digits+optional fraction
DIM_RE = re.compile(r"\d+\s*['`\u2019]\s*-?\s*\d+", )
NORM_DIM_RE = re.compile(r"^\d{2,4}(12|14|34|38|58|18|78)?$")

def is_dim(run):
    raw_s = run['raw']
    if DIM_RE.search(raw_s):
        return True
    return False

def axis(loc):
    w, h = loc['w_pct'], loc['h_pct']
    if w <= 0 or h <= 0:
        return 'INDETERMINATE'
    ratio = w / h
    if ratio >= 1.5:
        return 'HORIZONTAL'
    if ratio <= (1/1.5):
        return 'VERTICAL'
    return 'INDETERMINATE'

print('=== ITEM 1: page 6 dimension strings, box, axis class ===')
p6 = ot.get('6', {})
print('page dims:', p6.get('page_w'), 'x', p6.get('page_h'), ' total runs:', len(p6.get('runs', [])))
dims = [run for run in p6.get('runs', []) if is_dim(run)]
print('dimension-like runs on p6:', len(dims))
for run in dims:
    l = run['loc']
    print(f"  raw={run['raw']!r:30} norm={run['norm']:12} x={l['x_pct']:6.2f} y={l['y_pct']:6.2f} w={l['w_pct']:5.2f} h={l['h_pct']:5.2f} -> {axis(l)}")

print()
print('=== axis class census p6 (dimension-like only) ===')
from collections import Counter
print(Counter(axis(run['loc']) for run in dims))

print()
print('=== ITEM 4: search EVERY persisted page for 30-2 variants and 33-0 ===')
targets = {'302': "30'-2", '3020': "30'-2 0-ish", '330': "33'-0", '3300': "33'-0 variant"}
for pg in sorted(ot, key=int):
    for run in ot[pg]['runs']:
        n = run['norm']
        for t in ('302', '330'):
            if n == t or (t in n and len(n) <= len(t)+2):
                l = run['loc']
                print(f"  page {pg}: raw={run['raw']!r} norm={n} loc={l} axis={axis(l)}")

print()
print('=== also raw-string scan for 30 and 33 with quote marks, all pages ===')
for pg in sorted(ot, key=int):
    for run in ot[pg]['runs']:
        if re.search(r"3[03]\s*['`\u2019]", run['raw']):
            l = run['loc']
            print(f"  page {pg}: raw={run['raw']!r} norm={run['norm']} axis={axis(l)} loc=({l['x_pct']},{l['y_pct']},{l['w_pct']},{l['h_pct']})")

print()
print('=== garage label boxes p6 ===')
for run in p6.get('runs', []):
    if 'GARAGE' in run['norm']:
        l = run['loc']
        print(f"  raw={run['raw']!r} norm={run['norm']} loc=({l['x_pct']},{l['y_pct']},{l['w_pct']},{l['h_pct']})")

print()
print('=== coverage chars per page (upright+rotated norms seen) ===')
print(raw.get('_ocr_page_coverage_chars'))
print()
print('=== ocr quote misses mentioning 30 or 33 ===')
for m in raw.get('_ocr_quote_misses', []):
    if '30' in str(m.get('from','')) or '33' in str(m.get('from','')):
        print(' ', json.dumps(m))
