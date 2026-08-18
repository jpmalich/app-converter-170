"""SEND-45 HEIGHT BUILD DRAFT — READ-ONLY DRY RUN. NO BINDING, NO WRITES,
NO TUNING. Evaluates the drafted mechanism against the stored OCR for both
houses and reports what every face would resolve to. Fraction tails are
dropped by _member_inches (whole-inch report; wiring would parse eighths)."""
import os, re, json, sys
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
sys.path.insert(0, '/app/backend')
from ocr_geometry import (normalize_marks, is_dimension_like, axis_class,
                          glyph_count, merge_positions, _member_inches)

db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
HOUSES = {'boni': '65bcb89d-8291-4b84-920c-7b503273f332',
          'letrick': '264b6230-5d0f-49ea-b07d-8d33a537f293'}
FACES = ('front', 'rear', 'left', 'right')
DATUM_DEFS = [('TOP_OF_PLATE', 'TOPOFPLATE'), ('SECOND_FLOOR', 'SECONDFLOOR'),
              ('FIRST_FLOOR', 'FIRSTFLOOR'), ('TOP_OF_FOUNDATION', 'TOPOFFOUNDATION'),
              ('WALKOUT_FOOTER', 'WALKOUTFOOTER')]
DATUM_EXCLUDE = ('PLAN', 'JOIST', 'ELEC', 'CEILING')  # sheet-index + prose notes
GRADE_TOKENS = ('APPROXGRADE', 'GRADE@', 'FINISHGRADE', 'FINISHEDGRADE')
GRADE_EXCLUDE = ('NOTES', 'BEAM', 'DETERMINED', 'ACHIEVE', 'DRAWN', 'STANDARDS', 'MOVING')


def sq(s):
    return re.sub(r'[^A-Z]', '', (s or '').upper())


def sqa(s):
    return re.sub(r'[^A-Z@]', '', (s or '').upper())


def cy(r):
    return r['loc']['y_pct'] + r['loc']['h_pct'] / 2


def load(eid):
    r = db.ai_blueprint_runs.find_one({'estimate_id': eid, 'status': 'done'},
                                      sort=[('created_at', -1)])
    return r['run_id'], r['result']['raw_ai']['_ocr_text_by_page']


def face_bands(runs, page_faces):
    """Sub-title = squashed string with FACE + ELEVATION tokens (either
    order), never a combined sheet-index title (&/two faces). Title sits
    BELOW its drawing: band = (previous title y, own title y)."""
    subs = []
    for r in runs:
        s = sq(r['raw'])
        if 'ELEVATION' not in s or 'ELEVATIONS' in s:
            continue
        hits = [f for f in FACES if f.upper() in s]
        if len(hits) != 1:
            continue
        subs.append((hits[0], cy(r)))
    best = {}
    for f, y in subs:
        best.setdefault(f, []).append(y)
    titles = sorted((min(ys), f) for f, ys in best.items() if f in page_faces)
    bands, prev = {}, 0.0
    for y, f in titles:
        bands[f] = (prev, y)
        prev = y
    return bands


def furniture_index(ot, elevation_pages):
    """TITLE-BLOCK FURNITURE (parameter-free): a squashed string whose
    box has an identical-string overlapping twin on a NON-ELEVATION page
    is sheet furniture (it rides the title block on every sheet), never
    an elevation datum. Set membership, no thresholds."""
    idx = {}
    for pg in ot:
        if pg in elevation_pages:
            continue
        for run in merge_positions(ot[pg]['runs']):
            l = run['loc']
            idx.setdefault(sq(run['raw']), []).append(
                (l['x_pct'], l['y_pct'], l['x_pct'] + l['w_pct'], l['y_pct'] + l['h_pct']))
    return idx


def is_furniture(run, idx):
    l = run['loc']
    a = (l['x_pct'], l['y_pct'], l['x_pct'] + l['w_pct'], l['y_pct'] + l['h_pct'])
    for b in idx.get(sq(run['raw']), ()):
        if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
            return True
    return False


def datum_lines(runs, y0, y1, furn_idx):
    """Same-label instances whose glyph boxes y-overlap merge into ONE
    line (positional, parameter-free); non-overlapping instances of the
    same label are SEPARATE lines (two real plate lines exist)."""
    inst = []
    for r in runs:
        s = sq(r['raw'])
        if any(x in s for x in DATUM_EXCLUDE):
            continue
        if is_furniture(r, furn_idx):
            continue
        for name, tok in DATUM_DEFS:
            if tok in s:
                b0, b1 = r['loc']['y_pct'], r['loc']['y_pct'] + r['loc']['h_pct']
                if y0 <= (b0 + b1) / 2 <= y1:
                    inst.append({'name': name, 'raw': r['raw'], 'b0': b0, 'b1': b1})
                break
    lines = []
    for i in sorted(inst, key=lambda d: d['b0']):
        for L in lines:
            if L['name'] == i['name'] and i['b0'] <= L['b1'] and i['b1'] >= L['b0']:
                L['b0'], L['b1'] = min(L['b0'], i['b0']), max(L['b1'], i['b1'])
                L['n'] += 1
                break
        else:
            lines.append({'name': i['name'], 'b0': i['b0'], 'b1': i['b1'], 'n': 1})
    for L in lines:
        L['y'] = round((L['b0'] + L['b1']) / 2, 1)
    return sorted(lines, key=lambda L: L['y'])


def vertical_rails(runs, y0, y1):
    out = []
    for r in runs:
        if not is_dimension_like(normalize_marks(r['raw'])):
            continue
        if axis_class(r['loc'], glyph_count(r['raw'])) != 'VERTICAL':
            continue
        b0, b1 = r['loc']['y_pct'], r['loc']['y_pct'] + r['loc']['h_pct']
        if y0 <= (b0 + b1) / 2 <= y1:
            out.append({'raw': r['raw'], 'in': _member_inches(r['raw']),
                        'b0': b0, 'b1': b1,
                        'x': round(r['loc']['x_pct'] + r['loc']['w_pct'] / 2, 1)})
    return out


def gap_bind(lines, rails):
    """A rail binds to the adjacent datum-line pair whose OPEN interval
    STRICTLY contains its whole glyph box (a box touching either line is
    AT a datum, not between the pair). >1 distinct value in a gap =
    CONTESTED. No rail = UNDIMENSIONED."""
    gaps = []
    for a, b in zip(lines, lines[1:]):
        members = [r for r in rails if r['b0'] > a['b1'] and r['b1'] < b['b0']]
        vals = sorted({r['in'] for r in members if r['in'] is not None})
        if not members:
            status = 'UNDIMENSIONED'
        elif len(vals) == 1:
            status = 'BOUND'
        else:
            status = 'CONTESTED'
        gaps.append({'from': f"{a['name']}@{a['y']}", 'to': f"{b['name']}@{b['y']}",
                     'top': a, 'bottom': b, 'status': status,
                     'value_in': vals[0] if len(vals) == 1 else None,
                     'rails': [{'raw': r['raw'], 'in': r['in'], 'x': r['x']}
                               for r in members]})
    return gaps


def height_path(lines, gaps, bottom_name):
    """Sum of consecutive BOUND gaps from the LOWEST instance of
    bottom_name up to the TOPMOST TOP_OF_PLATE line. Any UNDIMENSIONED or
    CONTESTED gap on the path refuses with the gap named."""
    plates = [L for L in lines if L['name'] == 'TOP_OF_PLATE']
    bottoms = [L for L in lines if L['name'] == bottom_name]
    if not plates:
        return {'status': 'REFUSED', 'reason': 'no TOP OF PLATE datum located'}
    if not bottoms:
        return {'status': 'REFUSED', 'reason': f'no {bottom_name} datum located'}
    top_y, bot_y = plates[0]['y'], bottoms[-1]['y']
    path = [g for g in gaps if g['top']['y'] >= top_y and g['bottom']['y'] <= bot_y]
    total, used = 0, []
    for g in path:
        if g['status'] != 'BOUND':
            who = ', '.join(f"{r['raw']}({r['in']}\")" for r in g['rails']) or 'none'
            return {'status': 'REFUSED',
                    'reason': f"gap {g['from']} → {g['to']} {g['status']}"
                              f" — rails: {who}"}
        total += g['value_in']
        used.append(g)
    return {'status': 'ESTABLISHED', 'inches': total,
            'ft': round(total / 12, 2),
            'chain': [f"{g['from']} → {g['to']} = {g['value_in']}\"" for g in used]}


def grade_verdict(runs, lines, y0, y1):
    labels, walkout = [], False
    for r in runs:
        s, sa = sq(r['raw']), sqa(r['raw'])
        b0, b1 = r['loc']['y_pct'], r['loc']['y_pct'] + r['loc']['h_pct']
        if not (y0 <= (b0 + b1) / 2 <= y1):
            continue
        if 'WALKOUTFOOTER' in s:
            walkout = True
        if any(x in s for x in GRADE_EXCLUDE):
            continue
        if any(t in sa for t in GRADE_TOKENS):
            labels.append({'raw': r['raw'], 'b0': b0, 'b1': b1,
                           'y': round((b0 + b1) / 2, 1)})
    if not labels:
        v = {'verdict': 'UNKNOWN', 'reason': 'grade line not located on this elevation'}
        if walkout:
            v['note'] = 'walkout footer labeled — STEP grade suspected, awaiting ruling'
        return v
    hits = []
    for L in labels:
        for D in lines:
            if L['b0'] <= D['b1'] and L['b1'] >= D['b0']:
                hits.append((L['raw'], f"{D['name']}@{D['y']}"))
    if hits and len(hits) == len(labels):
        v = {'verdict': 'FLAT',
             'basis': [f"grade label {r!r} on datum line {d}" for r, d in hits],
             'label': 'plan-approximate (print: FINAL GRADE TO BE DETERMINED ON SITE)'}
    else:
        v = {'verdict': 'UNKNOWN',
             'reason': 'grade label located but off every datum line — '
                       'single-end read, slope not classifiable',
             'labels': [{'raw': L['raw'], 'y': L['y']} for L in labels]}
    if walkout:
        v['note'] = 'walkout footer labeled — STEP grade suspected, awaiting ruling'
    return v


PAGE_FACES = {'1': ('front', 'rear'), '2': ('left', 'right')}


def main():
    out = {}
    for house, eid in HOUSES.items():
        run_id, ot = load(eid)
        hrep = {'run_id': run_id, 'faces': {}}
        furn_idx = furniture_index(ot, set(PAGE_FACES))
        for pg, pf in PAGE_FACES.items():
            raw_runs = ot[pg]['runs']
            runs = merge_positions(raw_runs)
            bands = face_bands(raw_runs, pf)
            for face in pf:
                if face not in bands:
                    hrep['faces'][face] = {
                        'page': pg, 'status': 'REFUSED',
                        'refusal': f'no {face} elevation drawing located — '
                                   f'height not established — area not derivable'}
                    continue
                y0, y1 = bands[face]
                lines = datum_lines(raw_runs, y0, y1, furn_idx)
                rails = vertical_rails(runs, y0, y1)
                gaps = gap_bind(lines, rails)
                frep = {'page': pg, 'band': [round(y0, 1), round(y1, 1)],
                        'datum_lines': [f"{L['name']}@{L['y']}" for L in lines],
                        'gaps': [{k: g[k] for k in ('from', 'to', 'status', 'value_in', 'rails')}
                                 for g in gaps],
                        'height_A_first_floor_to_plate': height_path(lines, gaps, 'FIRST_FLOOR'),
                        'height_B_foundation_to_plate': height_path(lines, gaps, 'TOP_OF_FOUNDATION'),
                        'grade': grade_verdict(raw_runs, lines, y0, y1)}
                for opt in ('height_A_first_floor_to_plate', 'height_B_foundation_to_plate'):
                    h = frep[opt]
                    if h['status'] == 'REFUSED':
                        h['refusal_surface'] = (f"wall height not established from {face} "
                                                f"elevation — {h['reason']} — area not derivable")
                hrep['faces'][face] = frep
        out[house] = hrep

    with open('/app/memory/send45_height_dryrun.json', 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
