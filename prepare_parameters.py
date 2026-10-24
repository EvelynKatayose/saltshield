"""Create the initial, explicitly illustrative input tables from the frozen pilot.

This initializer does not overwrite existing parameter files. Subsequent edits
are made in the tables, then evaluated by planning_v1.py.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIRECTORY = ROOT/'data/parameters'
FILES = ['operations_baseline.csv', 'project_options.csv', 'scenario_config.json']


def write_rows(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(k for row in rows for k in row)), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def initialize():
    DIRECTORY.mkdir(exist_ok=True)
    if any((DIRECTORY/name).exists() for name in FILES):
        if not all((DIRECTORY/name).exists() for name in FILES):
            raise ValueError('Parameter tables are incomplete; restore the missing file before evaluation.')
        print('Existing parameter tables retained. Run planning_v1.py to evaluate them.')
        return
    a = json.loads((ROOT/'results/analysis.json').read_text())
    operations=[]; projects=[]
    for s in a['summary']:
        operations.append({'town_id':s['town'],'road_group_id':s['town'].replace(' ','_')+'_MUNICIPAL_PAVED',
                           'watershed_id':'6000000-01S','unit_basis':'CENTERLINE_KM_PER_WINTER',
                           'baseline_t_per_centerline_km_per_winter':5,
                           'application_rate_kg_per_lane_km':None,'applications_per_season':None,
                           'material_type':'ILLUSTRATIVE_SALT_EQUIVALENT','data_status':'SIMULATED',
                           'source':'Demonstration input; no town salt log or lane allocation verified'})
    for p in a['projects']:
        projects.append({'project_id':p['project_id'],'town_id':p['town'],'project_type':p['project_type'],
                         'capital_cost_usd':p['capital_cost_usd'],'annual_cost_change_usd':None,
                         'reduction_low':p['reduction_low'],'reduction_mid':p['reduction_fraction'],'reduction_high':p['reduction_high'],
                         'coverage_group_id':p['town'].replace(' ','_')+'_MUNICIPAL_PAVED',
                         'coverage_fraction':1,'exclusive_group':p['town'],'enabled':'true',
                         'data_status':'SIMULATED','source':'Demonstration package; not a vendor quote or measured effect'})
    write_rows(DIRECTORY/FILES[0], operations); write_rows(DIRECTORY/FILES[1], projects)
    config={'schema_version':1,'watershed_id':'6000000-01S','towns':[s['town'] for s in a['summary']],
            'total_budget_usd':75000,'local_budget_usd':{s['town']:25000 for s in a['summary']},
            'effect':'central','objective':'zoneA','unit_basis':'CENTERLINE_KM_PER_WINTER',
            'base_analysis_sha256':hashlib.sha256((ROOT/'results/analysis.json').read_bytes()).hexdigest(),
            'fairness_rule':'One selected project per town in the participation case; not a social-equity guarantee',
            'sensitivity':{'cost_multipliers':[.75,1,1.25],'baseline_multipliers':[.75,1,1.25],'effects':['low','central','high']},
            'cost_scope':'One-time capital only; unknown annual operating costs remain blank and are not assumed zero',
            'coverage_rule':'One mutually exclusive package per town; covered municipal paved road groups are disjoint by town',
            'limitation':'No verified lane-km, event-level salt logs, vendor prices, installed capacity, hydrologic response or shared-equipment dispatch'}
    (DIRECTORY/FILES[2]).write_text(json.dumps(config,indent=2))
    print('Created three illustrative input tables in data/parameters.')


if __name__=='__main__':initialize()
