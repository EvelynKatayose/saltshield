"""Configurable exact investment planning, with explicit participation constraints."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def number(value, label, low=0, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < low or (high is not None and value > high):
        raise ValueError(f'Invalid {label}')
    return value


def materialize(projects, towns, effect='central', baseline_intensity=5):
    number(baseline_intensity, 'baseline intensity')
    if effect not in ('low', 'central', 'high'):
        raise ValueError('Unknown effect scenario')
    seen = set(); output = []
    field = {'low': 'reduction_low', 'central': 'reduction_fraction', 'high': 'reduction_high'}[effect]
    for p in projects:
        if p['project_id'] in seen or p['town'] not in towns:
            raise ValueError('Duplicate project or unknown town')
        seen.add(p['project_id'])
        q = p.copy()
        q['capital_cost_usd'] = number(q['capital_cost_usd'], 'cost')
        q['coverage_fraction_assumed'] = number(q.get('coverage_fraction_assumed', 1), 'coverage fraction', high=1)
        if not isinstance(q.get('enabled', True), bool):
            raise ValueError('Enabled must be boolean')
        for r in ['reduction_low', 'reduction_fraction', 'reduction_high']:
            number(q[r], r, high=1)
        if not q['reduction_low'] <= q['reduction_fraction'] <= q['reduction_high']:
            raise ValueError('Reduction range must be ordered')
        for k in ['covered_zone_a_km_measured', 'covered_protected_km_measured']:
            number(q[k], k)
        if q['covered_zone_a_km_measured'] > q['covered_protected_km_measured'] + 1e-8:
            raise ValueError('Zone A coverage exceeds all protected roads')
        factor = baseline_intensity * q['coverage_fraction_assumed'] * q[field]
        q['active_reduction'] = q[field]
        q['avoided_zone_a_tonnes_simulated'] = q['covered_zone_a_km_measured'] * factor
        q['avoided_all_zones_tonnes_simulated'] = q['covered_protected_km_measured'] * factor
        output.append(q)
    return output


def plan(projects, budget, towns, local_caps=None, require_each_town=False):
    number(budget, 'budget')
    if len(set(towns)) != len(towns) or not towns:
        raise ValueError('Towns must be unique and nonempty')
    if local_caps is not None:
        for town in towns:
            number(local_caps[town], 'local cap')
    options = [[None] + [p for p in projects if p['town'] == t and p.get('enabled', True)] for t in towns]
    best = None; feasible = 0
    for choices in itertools.product(*options):
        selected = [p for p in choices if p is not None]
        if require_each_town and len(selected) != len(towns):
            continue
        cost = sum(p['capital_cost_usd'] for p in selected)
        if cost > budget + 1e-8:
            continue
        if local_caps is not None and any(sum(p['capital_cost_usd'] for p in selected if p['town'] == t) > local_caps[t] + 1e-8 for t in towns):
            continue
        zone_a = sum(p['avoided_zone_a_tonnes_simulated'] for p in selected)
        all_zones = sum(p['avoided_all_zones_tonnes_simulated'] for p in selected)
        feasible += 1
        key = (zone_a, all_zones, -cost)
        if best is None or key > best[0]:
            best = (key, {'cost': cost, 'zoneA': zone_a, 'all': all_zones, 'selected': selected, 'unspent': budget - cost, 'townsSelected': len(selected)})
    if best is None:
        return None
    return {**best[1], 'feasibleCombinations': feasible}


def compare(projects, budget, towns, effect='central', baseline_intensity=5):
    active = materialize(projects, towns, effect, baseline_intensity)
    independent = plan(active, budget, towns, {t: budget / len(towns) for t in towns})
    pooled = plan(active, budget, towns)
    participation = plan(active, budget, towns, require_each_town=True)
    same_spend = plan(active, independent['cost'], towns)
    same_spend_participation = plan(active, independent['cost'], towns, require_each_town=True)
    return {'independent': independent, 'pooled': pooled, 'participation': participation, 'equalSpend': same_spend, 'equalSpendParticipation': same_spend_participation}


def build():
    a = json.loads((ROOT / 'results/analysis.json').read_text())
    catalog = json.loads((ROOT / 'results/evidence_catalog.json').read_text())
    towns = [s['town'] for s in a['summary']]
    projects = [dict(p, enabled=True) for p in a['projects']]
    cases = []
    for budget in [0, 30000, 45000, 60000, 75000, 90000, 105000, 120000]:
        for effect in ['low', 'central', 'high']:
            result = compare(projects, budget, towns, effect)
            cases.append({'budget': budget, 'effect': effect, 'result': result})
    matrix = []
    for c in cases:
        for mode, result in c['result'].items():
            matrix.append({'budget_cap_usd': c['budget'], 'effect_scenario': c['effect'], 'mode': mode, 'feasible': result is not None,
                           'spent_usd': result['cost'] if result else None,
                           'avoided_zone_a_tonnes_simulated': result['zoneA'] if result else None,
                           'towns_with_selected_project': result['townsSelected'] if result else None,
                           'selected_projects': ';'.join(p['project_id'] for p in result['selected']) if result else ''})
    with (ROOT / 'results/phase2_policy_comparison.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(matrix)
    result = {'version': 2, 'base_analysis_sha256': hashlib.sha256((ROOT / 'results/analysis.json').read_bytes()).hexdigest(), 'evidence': catalog, 'projects': projects, 'towns': towns, 'default': compare(projects, 75000, towns), 'validation_cases': cases,
              'interpretation': 'The participation constraint means one selected project per town, not an equity or water-quality guarantee. Historical award amounts never replace current equipment costs.'}
    (ROOT / 'results/phase2_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'version': 2, 'cases': len(cases), 'policy_rows': len(matrix), 'award_records': len(catalog['records'])}))
    return result


if __name__ == '__main__':
    build()
