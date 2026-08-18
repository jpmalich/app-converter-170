"""SEND-46 READ-ONLY REPORT. Nothing wired, nothing bound.
1) OVERALL-RAIL CENSUS per face, both houses — the deciding fact for
   DP-5 (close the joist band by subtraction: overall rail minus sum of
   bound sub-gaps; strict closure, residual 0 required when all gaps
   are bound; no overall rail -> refuse, named open).
2) DP-1-CLOSED RESOLUTIONS: siding band = FIRST FLOOR -> topmost
   plate/soffit; a face that establishes the band is DERIVED; remaining
   undimensioned strips are NAMED. The foundation -> first-floor strip
   is BELOW the band (sealed DP-1) and is reported as such, not as a
   blocker."""
import json
import sys

sys.path.insert(0, '/app/memory')
from send45_height_dryrun import (HOUSES, PAGE_FACES, load, merge_positions,
                                  face_bands, furniture_index, datum_lines,
                                  vertical_rails, gap_bind)


def span_path(lines, gaps):
    """DP-1 band: lowest FIRST_FLOOR line up to the topmost TOP_OF_PLATE
    line. Returns (top, bottom, path gaps) or a refusal reason."""
    plates = [L for L in lines if L['name'] == 'TOP_OF_PLATE']
    floors = [L for L in lines if L['name'] == 'FIRST_FLOOR']
    if not plates:
        return None, None, None, 'no TOP OF PLATE datum located'
    if not floors:
        return None, None, None, 'no FIRST FLOOR datum located'
    top, bot = plates[0], floors[-1]
    path = [g for g in gaps if g['top']['y'] >= top['y'] and g['bottom']['y'] <= bot['y']]
    return top, bot, path, None


def face_report(lines, gaps, rails):
    top, bot, path, refusal = span_path(lines, gaps)
    rep = {}
    if refusal:
        rep['dp1'] = {'status': 'REFUSED',
                      'reason': refusal,
                      'surface': f'wall height not established — {refusal} '
                                 f'— area not derivable'}
        rep['overall_rail_census'] = {'span': None, 'candidates': [
            {'raw': r['raw'], 'in': r['in'], 'x': r['x']} for r in rails]}
        return rep
    bound = [g for g in path if g['status'] == 'BOUND']
    unbound = [g for g in path if g['status'] != 'BOUND']
    contested = [g for g in path if g['status'] == 'CONTESTED']
    sum_bound = sum(g['value_in'] for g in bound)
    # overall-rail census: every rail whose glyph box lies strictly
    # inside the DP-1 span. Gaps partition the span, so every rail
    # falls inside some sub-gap — arithmetic (not position) is what
    # tells an overall from a sub-rail. A rail that is the sole binder
    # of a BOUND gap is already consumed and cannot double as overall.
    cands = []
    for r in rails:
        if not (r['b0'] > top['b1'] and r['b1'] < bot['b0']):
            continue
        c = {'raw': r['raw'], 'in': r['in'], 'x': r['x']}
        home = next((g for g in path
                     if any(rr['raw'] == r['raw'] and rr['x'] == r['x']
                            for rr in g['rails'])), None)
        if home is not None and home['status'] == 'BOUND':
            c['verdict'] = f"BOUND SUB-RAIL of {home['from']}→{home['to']} — consumed, not overall"
        elif r['in'] is None:
            c['verdict'] = 'UNPARSEABLE'
        elif r['in'] < sum_bound:
            c['verdict'] = f'NOT OVERALL (value {r["in"]}" < bound sum {sum_bound}")'
        elif not unbound:
            c['verdict'] = ('CLOSES_EXACT' if r['in'] == sum_bound
                            else f'FAILS closure (residual {r["in"] - sum_bound}")')
        elif contested:
            c['verdict'] = (f'SUBTRACTION BLOCKED — contested gap(s) in span '
                            f'(elevation segment x-extents named open); '
                            f'residual for the record: {r["in"] - sum_bound}"')
        else:
            c['residual_for_unbound_strips_in'] = r['in'] - sum_bound
            c['verdict'] = (f'SUBTRACTION CANDIDATE — residual {r["in"] - sum_bound}" '
                            f'would close: ' + '; '.join(f"{g['from']}→{g['to']}"
                                                         for g in unbound))
        if home is not None and home['status'] == 'CONTESTED':
            c['note'] = f"contestant in {home['from']}→{home['to']}"
        cands.append(c)
    if not unbound:
        dp5 = 'no overall rail needed — every gap on the span is BOUND'
    elif contested:
        dp5 = ('SUBTRACTION BLOCKED — contested gap(s) present; blocked on '
               'the elevation segment x-extents named open, not on DP-5')
    elif any('SUBTRACTION CANDIDATE' in c['verdict'] for c in cands):
        dp5 = 'subtraction candidate(s) exist — see census; ruling decides admission'
    else:
        dp5 = ('NO OVERALL RAIL EXISTS — DP-5 sealed outcome: refuse; '
               'joist band stays a named open')
    rep['overall_rail_census'] = {
        'span': f"{top['name']}@{top['y']} → {bot['name']}@{bot['y']}",
        'bound_sum_in': sum_bound,
        'bound_gaps': [f"{g['from']}→{g['to']} = {g['value_in']}\"" for g in bound],
        'unbound_gaps': [f"{g['from']}→{g['to']} [{g['status']}]" for g in unbound],
        'dp5_conclusion': dp5,
        'candidates': cands}
    # DP-1 resolution
    if not unbound:
        rep['dp1'] = {'status': 'DERIVED', 'inches': sum_bound,
                      'ft': round(sum_bound / 12, 2),
                      'chain': [f"{g['from']} → {g['to']} = {g['value_in']}\""
                                for g in bound]}
    else:
        g = unbound[0]
        who = ', '.join(f"{r['raw']}({r['in']}\")" for r in g['rails']) or 'none'
        rep['dp1'] = {'status': 'REFUSED',
                      'named_strips': [f"{g['from']}→{g['to']} [{g['status']}]"
                                       for g in unbound],
                      'surface': f"wall height not established — gap {g['from']} → "
                                 f"{g['to']} {g['status']} — rails: {who} — "
                                 f"area not derivable"}
    return rep


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
                    hrep['faces'][face] = {'dp1': {
                        'status': 'REFUSED',
                        'reason': f'no {face} elevation drawing located'}}
                    continue
                y0, y1 = bands[face]
                lines = datum_lines(raw_runs, y0, y1, furn_idx)
                rails = vertical_rails(runs, y0, y1)
                gaps = gap_bind(lines, rails)
                rep = face_report(lines, gaps, rails)
                rep['below_band_note'] = ('foundation → first-floor strip is '
                                          'BELOW the siding band (DP-1 sealed) '
                                          '— not resolved, not a blocker')
                hrep['faces'][face] = rep
        out[house] = hrep
    with open('/app/memory/send46_report.json', 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
