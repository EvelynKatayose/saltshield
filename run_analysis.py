"""Rebuild the SaltShield pilot from the bundled official GeoJSON extracts.

All measured lengths use EPSG:26986. Equipment, costs, and salt application
parameters are illustrative simulations, never observed maintenance records.
"""
from __future__ import annotations
import csv
import hashlib
import itertools
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely import make_valid, normalize
from shapely.geometry import shape, mapping
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'results'
PROCESSED = ROOT / 'data' / 'processed'
TOWNS = ['HOLDEN', 'STERLING', 'WEST BOYLSTON']
SOURCE_ID = '6000000-01S'
TO_M = Transformer.from_crs(4326, 26986, always_xy=True).transform
TO_LL = Transformer.from_crs(26986, 4326, always_xy=True).transform
PARAMS = {
    'total_budget_usd': 75000,
    'independent_budget_usd_per_town': 25000,
    'baseline_tonnes_per_centerline_km_per_season': 5.0,
    'objective': 'maximize_simulated_avoided_salt_application_on_Zone_A_municipal_paved_roads',
    'baseline_status': 'SIMULATED uniform application intensity, not observed usage',
    'project_coverage': 'all mapped municipal paved road sections in the selected town and watershed',
    'scope_limit': 'Three-town subset, not the entire Wachusett watershed',
    'cost_horizon': 'one-time capital budget; operating costs and equipment life not modeled',
    'safety': 'Investment screening only; no treatment rates or road-safety performance recommendations',
}
OFFICIAL_PAGES = {
    'roads': 'https://www.mass.gov/info-details/massgis-data-massgis-massdot-roads',
    'towns': 'https://www.mass.gov/info-details/massgis-data-municipalities',
    'watershed': 'https://www.mass.gov/info-details/massgis-data-surface-water-supply-watersheds',
    'protection_zones': 'https://www.mass.gov/info-details/massgis-data-surface-water-supply-protection-areas-zone-a-b-c',
}


def load(name):
    return json.loads((RAW / name).read_text())


def project(geom):
    g = shape(geom)
    if not g.is_valid:
        g = make_valid(g)
    return transform(TO_M, g)


def feature(geom, props):
    return {'type': 'Feature', 'geometry': mapping(transform(TO_LL, geom)), 'properties': props}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def write_fc(path, features):
    write_json(path, {'type': 'FeatureCollection', 'features': features})


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def line_parts(g):
    if g.is_empty:
        return []
    if g.geom_type == 'LineString':
        return [g]
    if hasattr(g, 'geoms'):
        return [p for child in g.geoms for p in line_parts(child)]
    return []


def solve(projects, budget, local_caps=None):
    """Exact enumeration: at most one of two alternatives per town (27 cases)."""
    options = [[None] + [p for p in projects if p['town'] == t] for t in TOWNS]
    feasible = []
    for choice in itertools.product(*options):
        chosen = [p for p in choice if p]
        spent = sum(p['capital_cost_usd'] for p in chosen)
        if spent > budget + 1e-8:
            continue
        if local_caps and any(sum(p['capital_cost_usd'] for p in chosen if p['town'] == t) > local_caps[t] + 1e-8 for t in TOWNS):
            continue
        benefit = sum(p['avoided_zone_a_tonnes_simulated'] for p in chosen)
        total = sum(p['avoided_all_zones_tonnes_simulated'] for p in chosen)
        feasible.append((benefit, total, -spent, tuple(p['project_id'] for p in chosen), chosen))
    best = max(feasible, key=lambda a: (a[0], a[1], a[2]))
    return {
        'budget_cap_usd': budget,
        'spent_usd': -best[2],
        'unspent_usd': budget + best[2],
        'avoided_zone_a_tonnes_simulated': best[0],
        'avoided_all_zones_tonnes_simulated': best[1],
        'selected_project_ids': list(best[3]),
        'allocations_usd': {t: sum(p['capital_cost_usd'] for p in best[4] if p['town'] == t) for t in TOWNS},
        'feasible_combinations': len(feasible),
        'optimizer': 'exact enumeration of all 27 mutually exclusive project combinations',
    }


def build():
    OUT.mkdir(exist_ok=True)
    PROCESSED.mkdir(exist_ok=True)
    wfeatures = load('watershed.geojson')['features']
    assert len(wfeatures) == 1 and wfeatures[0]['properties']['SOURCE_ID'] == SOURCE_ID
    watershed = project(wfeatures[0]['geometry'])
    towns_features = load('towns.geojson')['features']
    towns = {f['properties']['TOWN']: project(f['geometry']) for f in towns_features}
    masks = {t: towns[t].intersection(watershed) for t in TOWNS}
    study = unary_union(list(masks.values()))
    zones_raw = load('protection_zones.geojson')['features']
    zones = {}
    used = None
    for z in 'ABC':
        selected = [project(f['geometry']) for f in zones_raw if f['properties']['SWPZONE'] == z and f['properties']['SOURCE_ID'] == SOURCE_ID]
        g = unary_union(selected).intersection(watershed)
        zones[z] = g if used is None else g.difference(used)
        used = g if used is None else used.union(g)
    zones['UNZONED'] = watershed.difference(used)
    road_meta = load('roads_metadata.json')
    jurisdiction = next(f for f in road_meta['fields'] if f['name'] == 'JURISDICTN')['domain']['codedValues']
    owner_names = {str(v['code']): v['name'] for v in jurisdiction}
    roads = load('roads.geojson')['features']
    road_ids = load('road_ids.json')
    assert len(roads) == len(road_ids) == len({f['properties']['OBJECTID'] for f in roads})
    geometries = [project(f['geometry']) for f in roads]
    tree = STRtree(geometries)
    full_town_km = {t: sum(geometries[i].intersection(towns[t]).length for i in tree.query(towns[t], predicate='intersects')) / 1000 for t in TOWNS}
    rows, geo_features = [], []
    clipped_expected = 0.0
    candidates = tree.query(study, predicate='intersects')
    for i in sorted(candidates):
        f, g = roads[i], geometries[i]
        p = f['properties']
        inside = g.intersection(study)
        clipped_expected += inside.length / 1000
        remaining = inside
        # On an exact shared municipal boundary, prefer the source's town;
        # remove already-assigned linework so it is never counted twice.
        source_town = p.get('MGIS_TOWN')
        town_order = sorted(TOWNS, key=lambda t: (t != source_town, t))
        for town in town_order:
            town_piece = remaining.intersection(masks[town])
            remaining = remaining.difference(town_piece)
            if town_piece.is_empty:
                continue
            for z, zg in zones.items():
                section = town_piece.intersection(zg)
                for n, part in enumerate(line_parts(section)):
                    km = part.length / 1000
                    if km < 1e-8:
                        continue
                    code = str(p.get('JURISDICTN')) if p.get('JURISDICTN') is not None else 'UNKNOWN'
                    surface = p.get('SURFACE_TP')
                    facility = p.get('FACILITY')
                    eligible = code == '2' and surface in (3, 4, 5, 6, 7, 8, 9) and facility != 12
                    row = {
                        'segment_id': f"{p['OBJECTID']}_{town.replace(' ', '_')}_{z}_{n}",
                        'source_objectid': p['OBJECTID'],
                        'source_road_segment_id': p.get('RD_SEG_ID'),
                        'street_name': p.get('STREET_NAME') or p.get('STREETNAME') or '',
                        'town': town,
                        'source_town_attribute': source_town or '',
                        'jurisdiction_code': code,
                        'jurisdiction_label': owner_names.get(code, 'Unknown or missing jurisdiction'),
                        'zone': z,
                        'centerline_km': km,
                        'surface_code': surface,
                        'facility_code': facility,
                        'source_num_lanes': p.get('NUM_LANES'),
                        'source_opp_lanes': p.get('OPP_LANES'),
                        'eligible_simulated_municipal_project': eligible,
                        'length_status': 'MEASURED_FROM_OFFICIAL_GEOMETRY_EPSG_26986',
                    }
                    rows.append(row)
                    geo_features.append(feature(part, row))
    measured_km = sum(r['centerline_km'] for r in rows)
    grouped = defaultdict(float)
    for r in rows:
        grouped[(r['town'], r['jurisdiction_code'], r['jurisdiction_label'], r['zone'])] += r['centerline_km']
    owner_zone = [{'town': t, 'jurisdiction_code': c, 'jurisdiction_label': l, 'zone': z, 'centerline_km': km} for (t, c, l, z), km in sorted(grouped.items())]
    owner_totals = defaultdict(lambda: {'watershed': 0.0, 'protected': 0.0})
    for r in rows:
        v = owner_totals[(r['town'], r['jurisdiction_code'], r['jurisdiction_label'])]
        v['watershed'] += r['centerline_km']
        if r['zone'] != 'UNZONED':
            v['protected'] += r['centerline_km']
    owner_rows = [{'town': t, 'jurisdiction_code': c, 'jurisdiction_label': l, 'watershed_centerline_km': v['watershed'], 'protected_centerline_km': v['protected']} for (t,c,l),v in sorted(owner_totals.items())]
    summaries = []
    for town in TOWNS:
        rr = [r for r in rows if r['town'] == town]
        eligible = [r for r in rr if r['eligible_simulated_municipal_project']]
        summaries.append({
            'town': town,
            'full_town_mapped_centerline_km': full_town_km[town],
            'within_watershed_centerline_km': sum(r['centerline_km'] for r in rr),
            'protected_centerline_km': sum(r['centerline_km'] for r in rr if r['zone'] != 'UNZONED'),
            **{f'zone_{z.lower()}_centerline_km': sum(r['centerline_km'] for r in rr if r['zone'] == z) for z in ['A','B','C','UNZONED']},
            'municipal_accepted_centerline_km': sum(r['centerline_km'] for r in rr if r['jurisdiction_code'] == '2'),
            'massdot_centerline_km': sum(r['centerline_km'] for r in rr if r['jurisdiction_code'] == '1'),
            'unaccepted_centerline_km': sum(r['centerline_km'] for r in rr if r['jurisdiction_code'] == '0'),
            'unknown_jurisdiction_centerline_km': sum(r['centerline_km'] for r in rr if r['jurisdiction_code'] == 'UNKNOWN'),
            'eligible_municipal_paved_centerline_km': sum(r['centerline_km'] for r in eligible),
            'eligible_municipal_paved_protected_centerline_km': sum(r['centerline_km'] for r in eligible if r['zone'] != 'UNZONED'),
            'eligible_municipal_paved_zone_a_km': sum(r['centerline_km'] for r in eligible if r['zone'] == 'A'),
            'segment_count': len(rr),
        })
    intensity = PARAMS['baseline_tonnes_per_centerline_km_per_season']
    projects = []
    alternatives = [
        ('CAL', 'Illustrative spreader calibration and controls package', 15000, .10, .05, .15),
        ('BRINE', 'Illustrative brine and pre-wetting equipment package', 30000, .25, .15, .35),
    ]
    for s in summaries:
        for typ,label,cost,rate,lo,hi in alternatives:
            projects.append({
                'project_id': s['town'].replace(' ','_') + '_' + typ,
                'town': s['town'], 'project_type': typ, 'label': label,
                'capital_cost_usd': cost, 'reduction_fraction': rate,
                'reduction_low': lo, 'reduction_high': hi,
                'covered_centerline_km_measured': s['eligible_municipal_paved_centerline_km'],
                'covered_protected_km_measured': s['eligible_municipal_paved_protected_centerline_km'],
                'covered_zone_a_km_measured': s['eligible_municipal_paved_zone_a_km'],
                'baseline_tonnes_simulated': s['eligible_municipal_paved_centerline_km'] * intensity,
                'avoided_all_zones_tonnes_simulated': s['eligible_municipal_paved_protected_centerline_km'] * intensity * rate,
                'avoided_zone_a_tonnes_simulated': s['eligible_municipal_paved_zone_a_km'] * intensity * rate,
                'exclusive_group': s['town'],
                'coverage_fraction_assumed': 1.0,
                'parameter_status': 'SIMULATED costs, reduction fraction, salt intensity and full coverage; measured road geometry',
                'evidence_limit': 'Not a vendor quote, fleet capacity assessment, observed savings, or water quality prediction',
            })
    budget = PARAMS['total_budget_usd']
    local = {t: budget/3 for t in TOWNS}
    independent = solve(projects,budget,local)
    pooled = solve(projects,budget)
    comparison = {'independent': independent, 'pooled': pooled}
    a,b = independent['avoided_zone_a_tonnes_simulated'],pooled['avoided_zone_a_tonnes_simulated']
    comparison['difference'] = {
        'additional_avoided_zone_a_tonnes_simulated': b-a,
        'relative_improvement_pct_simulated': (b/a-1)*100 if a else None,
        'additional_spending_usd': pooled['spent_usd']-independent['spent_usd'],
        'interpretation': 'Equal budget ceilings, not equal actual spending. Pooling can use stranded local funds and reallocate them. This is a simulated funding-rule comparison, not causal evidence of field efficacy or algorithm superiority.',
    }
    budget_sensitivity=[]
    for cap in [30000,45000,60000,75000,90000,105000,120000]:
        ii=solve(projects,cap,{t:cap/3 for t in TOWNS})
        pp=solve(projects,cap)
        budget_sensitivity.append({'total_cap_usd':cap,'independent_spent_usd':ii['spent_usd'],'pooled_spent_usd':pp['spent_usd'],'independent_zone_a_avoided_t_simulated':ii['avoided_zone_a_tonnes_simulated'],'pooled_zone_a_avoided_t_simulated':pp['avoided_zone_a_tonnes_simulated']})
    effect_sensitivity=[]
    for name,field in [('low','reduction_low'),('central','reduction_fraction'),('high','reduction_high')]:
        altered=[]
        for p in projects:
            q=p.copy();ratio=p[field]/p['reduction_fraction']
            q['avoided_zone_a_tonnes_simulated']*=ratio
            q['avoided_all_zones_tonnes_simulated']*=ratio
            altered.append(q)
        effect_sensitivity.append({'effect_scenario':name,'independent':solve(altered,budget,local),'pooled':solve(altered,budget)})
    # Equal-actual-spend diagnostic separates the capital-utilization effect.
    equal_spend=solve(projects,independent['spent_usd'])
    comparison['pooled_at_independent_actual_spend'] = equal_spend
    group_ids=[r['segment_id'] for r in rows]
    all_support=unary_union([geometries[i].intersection(study) for i in candidates])
    qa={
        'raw_road_count':len(roads),'road_id_count':len(road_ids),
        'selected_watershed_source_id':SOURCE_ID,
        'watershed_area_km2':watershed.area/1e6,
        'selected_town_watershed_area_km2':study.area/1e6,
        'clipped_input_length_km':clipped_expected,
        'segmented_output_length_km':measured_km,
        'length_conservation_difference_m':(measured_km-clipped_expected)*1000,
        'source_geometric_overlap_length_km':clipped_expected-all_support.length/1000,
        'unassigned_zone_road_length_km':sum(r['centerline_km'] for r in rows if r['zone']=='UNZONED'),
        'unique_segment_ids':len(group_ids)==len(set(group_ids)),
        'projects_per_town':{t:sum(p['town']==t for p in projects) for t in TOWNS},
        'zone_partition_area_difference_m2':sum(g.area for g in zones.values())-watershed.area,
        'pooled_weakly_dominates_independent_on_same_objective':b>=a-1e-8,
        'zero_budget_selects_nothing':solve(projects,0)['selected_project_ids']==[],
        'all_projects_zero_effect_tie_break_prefers_no_spending':None,
        'all_reported_lengths_are_centerline_lengths_not_lane_km':True,
        'jurisdiction_is_source_classification_not_verified_snow_maintenance_contract':True,
    }
    zero=[dict(p,avoided_zone_a_tonnes_simulated=0,avoided_all_zones_tonnes_simulated=0) for p in projects]
    qa['all_projects_zero_effect_tie_break_prefers_no_spending']=solve(zero,budget)['spent_usd']==0
    assert abs(qa['length_conservation_difference_m'])<0.1,qa
    assert abs(qa['zone_partition_area_difference_m2'])<1.0,qa
    assert qa['unique_segment_ids'] and qa['zero_budget_selects_nothing']
    assert qa['pooled_weakly_dominates_independent_on_same_objective']
    assert qa['all_projects_zero_effect_tie_break_prefers_no_spending']
    for plan in [independent,pooled,equal_spend]:
        chosen=[p for p in projects if p['project_id'] in plan['selected_project_ids']]
        assert plan['spent_usd']<=plan['budget_cap_usd']
        assert len({p['town'] for p in chosen})==len(chosen)
    write_csv(OUT/'town_road_summary.csv',summaries)
    write_csv(OUT/'road_length_by_jurisdiction.csv',owner_rows)
    write_csv(OUT/'road_length_by_jurisdiction_and_zone.csv',owner_zone)
    write_csv(PROCESSED/'road_segments.csv',rows)
    write_fc(PROCESSED/'road_segments.geojson',geo_features)
    write_fc(PROCESSED/'study_towns.geojson',[feature(masks[t],{'town':t}) for t in TOWNS])
    write_fc(PROCESSED/'watershed.geojson',[feature(watershed,wfeatures[0]['properties'])])
    write_fc(PROCESSED/'protection_zones.geojson',[feature(g,{'zone':z,'SOURCE_ID':SOURCE_ID}) for z,g in zones.items() if not g.is_empty])
    write_csv(OUT/'simulated_equipment_projects.csv',projects)
    write_csv(OUT/'budget_sensitivity.csv',budget_sensitivity)
    write_json(OUT/'comparison.json',comparison)
    write_json(OUT/'effect_sensitivity.json',effect_sensitivity)
    write_json(OUT/'scenario_parameters.json',PARAMS)
    write_json(OUT/'validation.json',qa)
    write_json(OUT/'official_source_pages.json',OFFICIAL_PAGES)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in RAW.glob('*.geojson')}
    write_json(OUT/'raw_data_sha256.json',hashes)
    package={'parameters':PARAMS,'summary':summaries,'owners':owner_rows,'owner_zone':owner_zone,'projects':projects,'comparison':comparison,'budget_sensitivity':budget_sensitivity,'effect_sensitivity':effect_sensitivity,'qa':qa,'official_sources':OFFICIAL_PAGES}
    write_json(OUT/'analysis.json',package)
    print(json.dumps(package,ensure_ascii=False,indent=2))
    return package


if __name__=='__main__':
    build()
