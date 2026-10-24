"""Capacity-linked project and whole-road-cell planning.

The offline browser uses a conservative 10 m capacity grid. SciPy supplies an
unrounded primary-objective benchmark for the frozen input tables only.
"""
import csv
import hashlib
import json
import math
import warnings
from pathlib import Path

from phase2_model import number, plan
from planning_v1 import active_projects, empty_plan, greedy_plan, load_inputs
from prepare_parameters import write_rows

ROOT=Path(__file__).resolve().parent
CAPACITY_FILE=ROOT/'data/parameters/project_capacity.csv'
QUANTUM_KM=.01
EPS=1e-10
POLICIES=['statusQuo','independent','greedy','pooled','participation','equalSpend','equalSpendParticipation']


def initialize_capacities(projects):
    if CAPACITY_FILE.exists():return
    rows=[{'project_id':p['project_id'],'town_id':p['town'],
           'max_road_km_per_winter':25 if p['project_type']=='CAL' else 50,
           'unit_basis':'CENTERLINE_KM_PER_WINTER','data_status':'SIMULATED',
           'source':'Illustrative road reach only; not a measured fleet capacity or verified service route'} for p in projects]
    write_rows(CAPACITY_FILE,rows)


def load_capacities(projects):
    with CAPACITY_FILE.open(encoding='utf-8-sig',newline='') as handle:rows=list(csv.DictReader(handle))
    original={p['project_id']:p for p in projects}
    if len(rows)!=len(original) or {r['project_id'] for r in rows}!=set(original):raise ValueError('Capacity IDs must match the project table exactly')
    for row in rows:
        if row['town_id']!=original[row['project_id']]['town'] or row['unit_basis']!='CENTERLINE_KM_PER_WINTER' or row['data_status']!='SIMULATED' or not row['source']:
            raise ValueError('Invalid capacity scope, units, status or source')
        row['max_road_km_per_winter']=number(float(row['max_road_km_per_winter']),'service reach')
    return rows


def validate_cells(cells,projects,towns):
    seen=set();totals={t:{'eligible_km':0.,'protected_km':0.,'zone_a_km':0.} for t in towns}
    for c in cells:
        if c['cell_id'] in seen or c['town'] not in totals:raise ValueError('Duplicate cell or unknown town')
        seen.add(c['cell_id'])
        for key in ['eligible_km','protected_km','zone_a_km']:
            number(c[key],'cell length');totals[c['town']][key]+=c[key]
        if c['eligible_km']<=0 or c['zone_a_km']>c['protected_km']+1e-8 or c['protected_km']>c['eligible_km']+1e-8:
            raise ValueError('Invalid nested cell lengths')
    for p in projects:
        t=totals[p['town']]
        for measured,key in [('covered_centerline_km_measured','eligible_km'),('covered_protected_km_measured','protected_km'),('covered_zone_a_km_measured','zone_a_km')]:
            if abs(p[measured]-t[key])>1e-6:raise ValueError('Project coverage does not match the frozen road cells')
    return totals


def allocation_result(cells,selected_ids,capacity,method):
    ids=set(selected_ids);selected=[c for c in cells if c['cell_id'] in ids]
    used=sum(c['eligible_km'] for c in selected)
    if used>capacity+1e-6:raise ValueError(f'Road coverage {used:.12f} exceeds service capacity {capacity:.12f}')
    return {'method':method,'capacity_km':capacity,'covered_road_km':used,
            'covered_protected_km':sum(c['protected_km'] for c in selected),
            'covered_zone_a_km':sum(c['zone_a_km'] for c in selected),
            'unused_capacity_km':max(0.,capacity-used),'selected_cell_ids':sorted(ids)}


def allocate_conservative(cells,capacity,objective='zoneA',quantum=QUANTUM_KM):
    number(capacity,'capacity')
    if objective not in ('zoneA','all') or quantum!=QUANTUM_KM:raise ValueError('Unsupported objective or capacity quantum')
    primary='zone_a_km' if objective=='zoneA' else 'protected_km'
    secondary='protected_km' if objective=='zoneA' else 'zone_a_km'
    useful=sorted([c for c in cells if c[primary]>EPS or c[secondary]>EPS],key=lambda c:c['cell_id'])
    cap=capacity
    bins=max(0,min(math.floor((cap+EPS)/quantum),sum(max(1,math.ceil((c['eligible_km']-EPS)/quantum)) for c in useful)))
    if bins>100000:raise ValueError('Capacity state space exceeds the supported pilot size')
    a=[0.]*(bins+1);b=[0.]*(bins+1);used=[0.]*(bins+1);choices=[];weights=[]
    for cell in useful:
        weight=max(1,math.ceil((cell['eligible_km']-EPS)/quantum));weights.append(weight)
        row=bytearray(bins+1)
        for j in range(bins,weight-1,-1):
            x=a[j-weight]+cell[primary];y=b[j-weight]+cell[secondary];z=used[j-weight]+cell['eligible_km']
            if x>a[j]+EPS or (abs(x-a[j])<=EPS and (y>b[j]+EPS or (abs(y-b[j])<=EPS and z<used[j]-EPS))):
                a[j]=x;b[j]=y;used[j]=z;row[j]=1
        choices.append(row)
    selected=[];j=bins
    for i in range(len(useful)-1,-1,-1):
        if choices[i][j]:selected.append(useful[i]['cell_id']);j-=weights[i]
    result=allocation_result(cells,selected,cap,'CONSERVATIVE_10M_DP')
    result['rounded_capacity_used_km']=sum(weights[i]*quantum for i,c in enumerate(useful) if c['cell_id'] in set(selected))
    return result


def allocate_exact(cells,capacity,objective='zoneA'):
    import numpy as np
    from scipy.optimize import Bounds,LinearConstraint,milp
    field='zone_a_km' if objective=='zoneA' else 'protected_km'
    secondary='protected_km' if objective=='zoneA' else 'zone_a_km'
    useful=[c for c in cells if c[field]>EPS or c[secondary]>EPS]
    if not useful or capacity<=0:
        return allocation_result(cells,[],capacity,'SCIPY_MILP_PRIMARY_BENCHMARK')
    # Meter-scale coefficients keep solver feasibility tolerance well below
    # the 1e-6 km length-conservation tolerance used throughout the pipeline.
    weights=np.array([c['eligible_km']*1000 for c in useful])
    def optimize(values):
        with warnings.catch_warnings():
            # SciPy forwards these documented HiGHS tolerances to the solver.
            warnings.filterwarnings('ignore',message='Unrecognized options detected.*',category=RuntimeWarning)
            return milp(-np.array(values),integrality=np.ones(len(useful)),bounds=Bounds(0,1),
                        constraints=LinearConstraint(weights,-np.inf,capacity*1000),
                        options={'time_limit':5.,'mip_rel_gap':0.,'mip_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
    solved=optimize([c[field]*1000 for c in useful])
    if solved.status!=0 or solved.x is None or getattr(solved,'mip_gap',0)>1e-8:
        raise RuntimeError('Exact capacity benchmark not certified: '+solved.message)
    # Only the primary optimum is certified. When it is zero, select any
    # positive secondary coverage that fits, so participation remains meaningful.
    # Avoid a near-equality MILP constraint: it creates numerical degeneracy
    # without strengthening the primary-objective certificate.
    if -float(solved.fun)<=EPS:
        tied=optimize([c[secondary]*1000 for c in useful])
        if tied.status!=0 or tied.x is None or getattr(tied,'mip_gap',0)>1e-8:raise RuntimeError('Zero-primary coverage benchmark not certified')
        solved=tied
    ids=[c['cell_id'] for c,x in zip(useful,solved.x) if x>.5]
    if sum(c['eligible_km'] for c in cells if c['cell_id'] in set(ids))>capacity+1e-6:
        raise RuntimeError('Unrounded benchmark failed the post-solve capacity check')
    result=allocation_result(cells,ids,capacity,'SCIPY_MILP_PRIMARY_BENCHMARK')
    result['solver_status']='OPTIMAL_PRIMARY_OBJECTIVE';return result


def snapshot(projects,budget,towns,rates,effect,objective,caps,capacities):
    return {'budget':budget,'effect':effect,'objective':objective,'towns':towns,
            'baseline_rates':{t:rates[t] for t in towns},'local_caps':{t:caps[t] for t in towns},
            'projects':[{'project_id':p['project_id'],'capital_cost_usd':p['capital_cost_usd'],'coverage_fraction_assumed':p['coverage_fraction_assumed'],
                         'enabled':p.get('enabled',True),'reduction_low':p['reduction_low'],'reduction_fraction':p['reduction_fraction'],'reduction_high':p['reduction_high'],
                         'max_road_km_per_winter':capacities[p['project_id']]} for p in sorted(projects,key=lambda p:p['project_id'])]}


def solve_joint(projects,cells,capacities,budget,towns,effect='central',baseline=5,objective='zoneA',local_caps=None,exact=False):
    number(budget,'budget')
    if not towns or len(set(towns))!=len(towns) or objective not in ('zoneA','all'):raise ValueError('Invalid scope or objective')
    active,rates=active_projects(projects,towns,effect,baseline)
    if set(capacities)!={p['project_id'] for p in projects}:raise ValueError('Capacity IDs must match the projects')
    for value in capacities.values():number(value,'service reach')
    if local_caps is not None and set(local_caps)!=set(towns):raise ValueError('Local budget towns do not match')
    caps={t:budget/len(towns) if local_caps is None else number(local_caps[t],'local ceiling') for t in towns}
    if abs(sum(caps.values())-budget)>1e-6:raise ValueError('Local ceilings must sum to the budget')
    totals=validate_cells(cells,active,towns);profiles=[]
    for p in active:
        subset=[c for c in cells if c['town']==p['town']]
        cap=min(capacities[p['project_id']],totals[p['town']]['eligible_km']*p['coverage_fraction_assumed'])
        if exact:print('Checking unrounded capacity:',p['project_id'],objective,flush=True)
        allocation=allocate_exact(subset,cap,objective) if exact else allocate_conservative(subset,cap,objective)
        factor=rates[p['town']]*p['active_reduction']
        profile={**p,'allocation':allocation,'service_reach_km_assumed':capacities[p['project_id']],
                 'avoided_zone_a_tonnes_simulated':allocation['covered_zone_a_km']*factor,
                 'avoided_all_zones_tonnes_simulated':allocation['covered_protected_km']*factor,
                 'avoided_all_eligible_tonnes_simulated':allocation['covered_road_km']*factor,
                 'baseline_tonnes_simulated':allocation['covered_road_km']*rates[p['town']],
                 'actual_coverage_fraction':allocation['covered_road_km']/totals[p['town']]['eligible_km'] if totals[p['town']]['eligible_km'] else 0,
                 'parameter_status':'SIMULATED service reach, price, baseline and effect; measured selected road-cell geometry',
                 'enabled':p.get('enabled',True) and bool(allocation['selected_cell_ids'])}
        for field in ['avoided_zone_a_tonnes_simulated','avoided_all_zones_tonnes_simulated','avoided_all_eligible_tonnes_simulated']:number(profile[field],'derived reduction')
        profiles.append(profile)
    independent=plan(profiles,budget,towns,caps,objective=objective)
    greedy,_=greedy_plan(profiles,budget,objective)
    plans={'statusQuo':empty_plan(budget),'independent':independent,'greedy':greedy,
           'pooled':plan(profiles,budget,towns,objective=objective),
           'participation':plan(profiles,budget,towns,require_each_town=True,objective=objective),
           'equalSpend':plan(profiles,independent['cost'],towns,objective=objective),
           'equalSpendParticipation':plan(profiles,independent['cost'],towns,require_each_town=True,objective=objective)}
    for result in plans.values():
        if result is None:continue
        for field,allocation_field in [('covered_road_km','covered_road_km'),('covered_zone_a_km','covered_zone_a_km'),('covered_protected_km','covered_protected_km'),('capacity_km','capacity_km')]:
            result[field]=sum(p['allocation'][allocation_field] for p in result['selected'])
        result['selected_cell_ids']=sorted(cid for p in result['selected'] for cid in p['allocation']['selected_cell_ids'])
        if len(result['selected_cell_ids'])!=len(set(result['selected_cell_ids'])):raise ValueError('A road cell was assigned twice')
        uniform={'zoneA':0.,'all':0.,'eligible':0.,'covered_road_km':0.}
        for p in result['selected']:
            t=totals[p['town']];share=p['allocation']['capacity_km']/t['eligible_km'] if t['eligible_km'] else 0
            factor=share*rates[p['town']]*p['active_reduction']
            uniform['zoneA']+=t['zone_a_km']*factor;uniform['all']+=t['protected_km']*factor;uniform['eligible']+=t['eligible_km']*factor;uniform['covered_road_km']+=p['allocation']['capacity_km']
        result['uniform_same_equipment']=uniform
    return {'input_snapshot':snapshot(projects,budget,towns,rates,effect,objective,caps,capacities),'profiles':profiles,'plans':plans,
            'method':'SCIPY_MILP_PRIMARY_BENCHMARK' if exact else 'CONSERVATIVE_10M_DP',
            'quantum_km':QUANTUM_KM,'participation_definition':'At least one enabled package with nonempty eligible road-cell coverage in every town'}


def source_hashes():
    names=['results/planning_v1.json','results/spatial_priority.json','data/processed/planning_cells.geojson','data/parameters/project_capacity.csv',
           'data/parameters/operations_baseline.csv','data/parameters/project_options.csv','data/parameters/scenario_config.json']
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}


def build():
    _,config,projects,rates=load_inputs();initialize_capacities(projects)
    rows=load_capacities(projects);capacities={r['project_id']:r['max_road_km_per_winter'] for r in rows}
    spatial=json.loads((ROOT/'results/spatial_priority.json').read_text());cells=spatial['cells'];references={};checks=[]
    for objective in ['zoneA','all']:
        args=(projects,cells,capacities,config['total_budget_usd'],config['towns'],config['effect'],rates,objective,config['local_budget_usd'])
        conservative=solve_joint(*args)
        try:
            exact=solve_joint(*args,exact=True);status='CERTIFIED_PRIMARY_OBJECTIVE';reason=''
        except RuntimeError as error:
            exact=None;status='NOT_CERTIFIED';reason=str(error)
            print('Benchmark unavailable for',objective,':',reason,flush=True)
        for policy in POLICIES:
            low=conservative['plans'][policy];high=exact['plans'][policy] if exact else None
            if exact and policy not in ['greedy','equalSpend','equalSpendParticipation'] and low is not None:
                if high is None or low[objective]>high[objective]+1e-6:raise ValueError('Conservative result exceeds the unrounded primary optimum')
            checks.append({'objective':objective,'policy':policy,'conservative_objective_t':low[objective] if low else None,'benchmark_objective_t':high[objective] if high else None,'benchmark_status':status,'benchmark_note':reason,
                           'comparison_scope':'Equal total ceiling' if not policy.startswith('equalSpend') else 'Each model uses its own independent actual spending'})
        references[objective]={'input_snapshot':conservative['input_snapshot'],'exact_plans':exact['plans'] if exact else None,'conservative_plans':conservative['plans'],'status':status,'note':reason}
    default=solve_joint(projects,cells,capacities,config['total_budget_usd'],config['towns'],config['effect'],rates,config['objective'],config['local_budget_usd'])
    output={'schema_version':1,'source_sha256':source_hashes(),'capacities':rows,'cells':cells,'default':default,'benchmarks':references,
            'interpretation':'Illustrative service reach, not measured fleet capacity. Whole cells use conservative 10 m capacity accounting. Budget portfolios are enumerated exactly over these conservative project profiles. Saved-input SciPy benchmarks optimize the unrounded primary objective only. No dispatch, concurrent storm, staffing, travel-time, safety or hydrologic model is implied.'}
    (ROOT/'results/joint_planning.json').write_text(json.dumps(output,indent=2,allow_nan=False))
    policy_rows=[];allocations=[]
    for policy,r in default['plans'].items():
        policy_rows.append({'policy':policy,'feasible':r is not None,'capital_usd':r['cost'] if r else None,'road_km':r['covered_road_km'] if r else None,
                            'zone_a_km':r['covered_zone_a_km'] if r else None,'protected_km':r['covered_protected_km'] if r else None,
                            'avoided_zone_a_t_simulated':r['zoneA'] if r else None,'avoided_protected_t_simulated':r['all'] if r else None,
                            'towns_covered':r['townsSelected'] if r else None})
        if r is not None:
            by_id={c['cell_id']:c for c in cells}
            for p in r['selected']:
                for cid in p['allocation']['selected_cell_ids']:
                    c=by_id[cid];allocations.append({'policy':policy,'project_id':p['project_id'],'town':p['town'],'cell_id':cid,'eligible_km':c['eligible_km'],'zone_a_km':c['zone_a_km'],'protected_km':c['protected_km']})
    write_rows(ROOT/'results/joint_policy_comparison.csv',policy_rows)
    with (ROOT/'results/joint_cell_allocations.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['policy','project_id','town','cell_id','eligible_km','zone_a_km','protected_km'],lineterminator='\n');writer.writeheader();writer.writerows(allocations)
    write_rows(ROOT/'results/joint_exact_benchmarks.csv',checks)
    p=default['plans']['pooled'];certified=references[config['objective']]['exact_plans'];reference=certified['pooled'] if certified else None
    print(json.dumps({'pooled_capital':p['cost'],'pooled_road_km':p['covered_road_km'],'pooled_zone_a_t':p['zoneA'],
                      'unrounded_zone_a_t_benchmark':reference['zoneA'] if reference else None,'selected_projects':[p['project_id'] for p in p['selected']]},indent=2))
    return output


if __name__=='__main__':build()
