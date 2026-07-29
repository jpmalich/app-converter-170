import json, math, sys
sys.path.insert(0, '/app/backend')
from lp_smartside_formulas import bb_batten_pieces_hard

r = json.load(open('/app/memory/evidence/s2_report_a425e75577844733bb512e9fa4959782.json'))

corners = r['corner_heights_ft']
by_fac = {}
for c in corners:
    by_fac.setdefault(c['near_facade'], []).append(c['height_ft'])
view_heights = {}
for c in corners:
    view_heights.setdefault(c['view'], []).append(c['height_ft'])

def median(v):
    v = sorted(v); n = len(v)
    return v[n//2] if n % 2 else (v[n//2-1]+v[n//2])/2

segs = []
rows = []
for f in r['facades']:
    lab, w = f['label'], f.get('width_ft')
    if not w or not lab.startswith('WR'):
        continue
    if f.get('height_min_ft'):
        h, src = f['height_min_ft'], 'facade callout'
    elif lab in by_fac:
        h, src = max(by_fac[lab]), 'bounding corner (max)'
    else:
        vh = view_heights.get(f['view'])
        h, src = (median(vh), 'view median corner') if vh else (9.0, 'DEFAULT 9 ft — NO READ')
    n_stories = max(1, math.ceil(h / 9.0 - 1e-9))
    stories = [h / n_stories] * n_stories
    segs.append((w, stories))
    rows.append((lab, w, round(h,2), src, n_stories))

for row in rows:
    print('%-7s W %6.2f  H %6.2f  (%s, %d stories)' % row)

total_w = sum(s[0] for s in segs)
area = sum(w * sum(st) for w, st in segs)
print()
print('segments with extracted width:', len(segs), '| total width', round(total_w,1), 'ft')
print('area from extracted dims:', round(area), 'ft2  (Hover-printed siding facades total: 4504 ft2)')
for spacing, stick in ((12, 10), (12, 16), (8, 10)):
    b = bb_batten_pieces_hard(segs, spacing, stick)
    print(f'HARD BATTEN {spacing}\" o.c., {stick}\' sticks: {b} pcs   (shipped: 465)')
panels = math.ceil(area / 40.0 * 1.30 - 1e-9)
print('PANELS ceil(area/40 x 1.30):', panels, 'pcs   (shipped: 155)')
print('PANELS off Hover-printed 4504:', math.ceil(4504/40*1.30 - 1e-9))
