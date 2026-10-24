"""Compare GIS coverage allocations, separately from simulated equipment prices."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from pyproj import Transformer
from shapely.geometry import box, mapping, shape
from shapely.ops import transform

from build_weather import write_csv

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/processed'
OUT = ROOT / 'results'
FORWARD = Transformer.from_crs(4326, 26986, always_xy=True).transform
INVERSE = Transformer.from_crs(26986, 4326, always_xy=True).transform
INPUTS = ['road_segments.geojson', 'study_towns.geojson']
FRACTIONS = [.25, .5, .75, 1.0]


def fingerprint():
    return {name: hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in INPUTS}


def build_cells():
    roads = json.loads((DATA/INPUTS[0]).read_text())['features']
    towns = {f['properties']['town']: transform(FORWARD, shape(f['geometry']))
             for f in json.loads((DATA/INPUTS[1]).read_text())['features']}
    cells = {}; expected = {t: {'eligible_km': 0., 'zone_a_km': 0., 'protected_km': 0.} for t in towns}
    max_residual_m = 0.
    for f in roads:
        p = f['properties']
        if not p['eligible_simulated_municipal_project']:
            continue
        g = transform(FORWARD, shape(f['geometry'])); town = p['town']
        expected[town]['eligible_km'] += g.length / 1000
        if p['zone'] == 'A': expected[town]['zone_a_km'] += g.length / 1000
        if p['zone'] in 'ABC': expected[town]['protected_km'] += g.length / 1000
        x0,y0,x1,y1 = g.bounds
        remaining = g
        # Subtract assigned linework: closed grid boundaries cannot duplicate it.
        for ix in range(math.floor(x0/1000), math.floor(x1/1000)+1):
            for iy in range(math.floor(y0/1000), math.floor(y1/1000)+1):
                grid = box(ix*1000, iy*1000, (ix+1)*1000, (iy+1)*1000)
                part = remaining.intersection(grid)
                if part.length <= 1e-10: continue
                key = (town, ix, iy)
                if key not in cells:
                    cells[key] = {'cell_id': town.replace(' ', '_')+f'_{ix}_{iy}', 'town': town,
                                  'grid_x': ix, 'grid_y': iy, 'eligible_km': 0., 'zone_a_km': 0.,
                                  'protected_km': 0., 'geometry': grid.intersection(towns[town])}
                c = cells[key]; km = part.length/1000
                c['eligible_km'] += km
                if p['zone'] == 'A': c['zone_a_km'] += km
                if p['zone'] in 'ABC': c['protected_km'] += km
                remaining = remaining.difference(grid)
        max_residual_m = max(max_residual_m, remaining.length)
    records = sorted(cells.values(), key=lambda c: c['cell_id'])
    for town, totals in expected.items():
        for key, value in totals.items():
            actual = sum(c[key] for c in records if c['town'] == town)
            if abs(actual-value) > 1e-6:
                raise ValueError(f'Grid length conservation failed: {town} {key}')
    if max_residual_m > 1e-6: raise ValueError('Unassigned road length')
    return records, expected, max_residual_m


def allocate(cells, capacity, method):
    if not math.isfinite(capacity) or capacity < 0: raise ValueError('Invalid capacity')
    total = sum(c['eligible_km'] for c in cells)
    if method not in ['uniform', 'greedy', 'integer', 'fractional_bound']: raise ValueError('Unknown method')
    if capacity >= total-1e-9:
        shares = {c['cell_id']: 1. for c in cells}
    elif capacity == 0 or not cells:
        shares = {}
    elif method == 'uniform':
        shares = {c['cell_id']: capacity/total for c in cells}
    else:
        useful = [c for c in cells if c['zone_a_km'] > 1e-12]
        ordered = sorted(useful, key=lambda c: (-c['zone_a_km']/c['eligible_km'], c['cell_id']))
        shares = {}; remaining = capacity
        if method in ['greedy', 'fractional_bound']:
            for c in ordered:
                amount = min(1., remaining/c['eligible_km']) if method == 'fractional_bound' else (1. if c['eligible_km'] <= remaining+1e-10 else 0.)
                if amount > 0:
                    shares[c['cell_id']] = amount; remaining -= amount*c['eligible_km']
                if remaining <= 1e-10: break
        elif useful:
            costs = np.array([c['eligible_km'] for c in useful])
            values = np.array([c['zone_a_km'] for c in useful])
            solved = milp(-values, integrality=np.ones(len(useful)), bounds=Bounds(0,1),
                          constraints=LinearConstraint(costs, -np.inf, capacity),
                          options={'time_limit': 30., 'mip_rel_gap': 0.})
            if solved.status != 0 or solved.x is None:
                raise RuntimeError('Optimal integer solution not certified: '+solved.message)
            shares = {c['cell_id']: 1. for c,x in zip(useful,solved.x) if x > .5}
    used = sum(c['eligible_km']*shares.get(c['cell_id'],0) for c in cells)
    if used > capacity+1e-6: raise ValueError('Coverage exceeds capacity')
    return {'method': method, 'capacity_km': capacity, 'covered_road_km': used,
            'covered_zone_a_km': sum(c['zone_a_km']*shares.get(c['cell_id'],0) for c in cells),
            'covered_protected_km': sum(c['protected_km']*shares.get(c['cell_id'],0) for c in cells),
            'unspent_capacity_km': max(0.,capacity-used), 'cell_shares': shares,
            'status': 'OPTIMAL' if method == 'integer' else ('UPPER_BOUND' if method == 'fractional_bound' else 'BASELINE')}


def build():
    records, totals, residual = build_cells(); features=[]
    for c in records:
        features.append({'type':'Feature', 'properties': {k:v for k,v in c.items() if k!='geometry'},
                         'geometry': mapping(transform(INVERSE,c['geometry']))})
    (DATA/'planning_cells.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
    cases=[]; csv_rows=[]; selected=[]
    for town in sorted(totals):
        subset=[c for c in records if c['town']==town]
        for fraction in FRACTIONS:
            plans={m:allocate(subset,totals[town]['eligible_km']*fraction,m)
                   for m in ['uniform','greedy','integer','fractional_bound']}
            if plans['integer']['covered_zone_a_km']+1e-6 < plans['greedy']['covered_zone_a_km']:
                raise ValueError('Integer solution underperforms feasible greedy solution')
            if plans['integer']['covered_zone_a_km'] > plans['fractional_bound']['covered_zone_a_km']+1e-6:
                raise ValueError('Integer solution exceeds fractional bound')
            cases.append({'town':town,'coverage_fraction':fraction,'plans':plans})
            for method,plan in plans.items():
                csv_rows.append({'town':town,'coverage_fraction':fraction,**{k:v for k,v in plan.items() if k!='cell_shares'}})
                for cid,share in plan['cell_shares'].items():
                    selected.append({'town':town,'coverage_fraction':fraction,'method':method,'cell_id':cid,'covered_share':share})
    result={'source_sha256':fingerprint(),'planning_cells_sha256':hashlib.sha256((DATA/'planning_cells.geojson').read_bytes()).hexdigest(),
            'grid_size_m':1000,'crs':'EPSG:26986','cell_count':len(records),
            'town_totals':totals,'max_unassigned_segment_m':residual,'cases':cases,
            'cells':[{k:v for k,v in c.items() if k!='geometry'} for c in records],
            'interpretation':'Illustrative coverage capacities, not measured equipment capacity. Uniform and fractional cases permit partial cells; integer and greedy select whole planning cells. Grid cells are not validated maintenance routes. Zone A coverage is a spatial proxy, not a calibrated pollution or safety outcome.',
            'source_overlap':'Source-record coincident linework is retained, as in the base inventory; grid splitting introduces no additional length.'}
    (OUT/'spatial_priority.json').write_text(json.dumps(result,indent=2))
    write_csv(OUT/'spatial_policy_comparison.csv',csv_rows)
    write_csv(OUT/'spatial_cell_allocations.csv',selected)
    print(json.dumps({'cells':len(records),'cases':len(cases),'policy_rows':len(csv_rows),'25_percent':[
        {'town':c['town'],'uniform_zone_a_km':c['plans']['uniform']['covered_zone_a_km'],
         'integer_zone_a_km':c['plans']['integer']['covered_zone_a_km']} for c in cases if c['coverage_fraction']==.25]},indent=2))
    return result


if __name__=='__main__':build()
