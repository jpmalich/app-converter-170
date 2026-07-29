import fitz, json, re, sys
from collections import defaultdict

run_id, pdf = sys.argv[1], sys.argv[2]
r = json.load(open(f'/app/memory/evidence/s2_report_{run_id}.json'))
doc = fitz.open(pdf)
full = '\n'.join(doc.load_page(i).get_text('text') for i in range(doc.page_count))
universe = set(re.findall(r'\b[A-Z]{1,4}\d?-\d+\b', full))
real = {i for i in universe if re.match(r'^(W|D|SGD)-', i)}
regions = {i for i in universe if re.match(r'^(WR|BR|STC|UNK)-', i)}

print('pages_read:', r['pages_read'], '| warnings:', len(r['warnings']))
for w in r['warnings']: print('  ', w)
print()
print('FACADES read (%d):' % len(r['facades']))
for f in r['facades']:
    print('  %-8s view %-6s W %-8s H %-12s %s' % (f['label'], f['view'],
          f.get('width_text') or '-', (f.get('height_text') or '-'), f['read']))
read_fac = {f['label'] for f in r['facades']}
print()
print('REGION COVERAGE: read', len(read_fac & regions), 'of', len(regions),
      '| UNREAD:', sorted(regions - read_fac, key=lambda s: (s.split('-')[0], int(s.split('-')[1]))))
print()
placed_ids = {p['id'] for p in r['openings_placed'] if p['id'] in real}
print('OPENINGS: placed %d unique of %d real | missed: %s' % (
    len(placed_ids), len(real), sorted(real - placed_ids)))
invented = sorted({p['id'] for p in r['openings_placed']} - real - regions)
print('invented IDs:', invented)
per_fac = defaultdict(set)
for p in r['openings_placed']:
    if p['id'] in real:
        per_fac[p['on_facade']].add(p['id'])
print()
print('PER-FACADE placements:')
for lab in sorted(per_fac, key=lambda s: (s.split('-')[0], int(s.split('-')[1]) if s.split('-')[-1].isdigit() else 0)):
    print('  %-8s %d %s' % (lab, len(per_fac[lab]), sorted(per_fac[lab])))
print()
print('CORNERS (%d):' % len(r['corner_heights_ft']))
for c in r['corner_heights_ft']:
    print('  near %-8s %-7s view %s' % (c.get('near_facade'), c.get('text'), c['view']))
