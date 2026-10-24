"""Project-based first-version evaluation; exhaustive portfolios, traceable inputs."""
import csv
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path

from phase2_model import materialize, number, plan
from prepare_parameters import DIRECTORY, FILES, write_rows

ROOT=Path(__file__).resolve().parent
POLICIES=['statusQuo','independent','greedy','pooled','participation','equalSpend','equalSpendParticipation']


def parameter_hashes():
    return {name:hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest() for name in FILES}


def active_projects(projects,towns,effect,baseline):
    if isinstance(baseline,dict) and set(baseline)!=set(towns):raise ValueError('Baseline towns must match the study scope')
    rates={t:number(baseline[t], 'town baseline') for t in towns} if isinstance(baseline,dict) else {t:number(baseline,'baseline') for t in towns}
    # One validation pass detects duplicate IDs across town groups.
    materialize(projects,towns,effect,0)
    return [materialize([p],towns,effect,rates[p['town']])[0] for p in projects],rates


def empty_plan(budget):
    return {'cost':0,'zoneA':0,'all':0,'eligible':0,'selected':[],'unspent':budget,'townsSelected':0,'feasibleCombinations':1}


def greedy_plan(active,budget,objective):
    primary='avoided_zone_a_tonnes_simulated' if objective=='zoneA' else 'avoided_all_zones_tonnes_simulated'
    secondary='avoided_all_zones_tonnes_simulated' if objective=='zoneA' else 'avoided_zone_a_tonnes_simulated'
    def ratio(p,field):
        return p[field]/p['capital_cost_usd'] if p['capital_cost_usd'] else (math.inf if p[field]>0 else 0)
    ordered=sorted(active,key=lambda p:(-ratio(p,primary),-ratio(p,secondary),p['capital_cost_usd'],p['project_id']))
    result=empty_plan(budget);trace=[];funded=set()
    for rank,p in enumerate(ordered,1):
        if not p.get('enabled',True):code='DISABLED'
        elif p[primary]<=0 and p[secondary]<=0:code='NO_BENEFIT'
        elif p['town'] in funded:code='EXCLUSIVE_GROUP_SELECTED'
        elif p['capital_cost_usd']>result['unspent']+1e-8:code='REMAINING_BUDGET'
        else:
            code='SELECTED';result['selected'].append(p);funded.add(p['town'])
            result['cost']+=p['capital_cost_usd'];result['unspent']=budget-result['cost']
            result['zoneA']+=p['avoided_zone_a_tonnes_simulated'];result['all']+=p['avoided_all_zones_tonnes_simulated']
            result['eligible']+=p['avoided_all_eligible_tonnes_simulated'];result['townsSelected']+=1
        trace.append({'project_id':p['project_id'],'code':code,'rank':rank,'remaining_budget_usd':result['unspent'],
                      'benefit_per_dollar':None if math.isinf(ratio(p,primary)) else ratio(p,primary)})
    return result,trace


def evaluate(projects,budget,towns,effect='central',baseline=5,objective='zoneA',local_caps=None):
    number(budget,'budget')
    if not towns or len(set(towns))!=len(towns):raise ValueError('Towns must be unique and nonempty')
    if objective not in ('zoneA','all'):raise ValueError('Unknown objective')
    active,rates=active_projects(projects,towns,effect,baseline)
    if local_caps is not None and set(local_caps)!=set(towns):raise ValueError('Budget towns must match the study scope')
    caps={t:budget/len(towns) for t in towns} if local_caps is None else {t:number(local_caps[t],'local cap') for t in towns}
    if abs(sum(caps.values())-budget)>1e-6:raise ValueError('Local ceilings must sum to the common total budget')
    independent=plan(active,budget,towns,caps,objective=objective)
    greedy,trace=greedy_plan(active,budget,objective)
    plans={'statusQuo':empty_plan(budget),'independent':independent,'greedy':greedy,
           'pooled':plan(active,budget,towns,objective=objective),'participation':plan(active,budget,towns,require_each_town=True,objective=objective),
           'equalSpend':plan(active,independent['cost'],towns,objective=objective),
           'equalSpendParticipation':plan(active,independent['cost'],towns,require_each_town=True,objective=objective)}
    return plans,active,rates,caps,trace


def explain(plans,active,budget,towns,objective,caps,trace):
    rows=[];trace_by_id={r['project_id']:r for r in trace}
    for policy,result in plans.items():
        ceiling=plans['independent']['cost'] if policy.startswith('equalSpend') else budget
        for p in active:
            info={'policy':policy,'project_id':p['project_id'],'town':p['town'],'selected':bool(result and any(q['project_id']==p['project_id'] for q in result['selected'])),
                  'counterfactual_objective_t':None,'objective_loss_t':None}
            if policy=='statusQuo':code='NO_NEW_INVESTMENT_BASELINE'
            elif not p.get('enabled',True):code='DISABLED'
            elif result is None:code='POLICY_INFEASIBLE'
            elif info['selected']:code='SELECTED'
            elif policy=='greedy':
                item=trace_by_id[p['project_id']];code=item['code'];info.update({'rank':item['rank'],'remaining_budget_usd':item['remaining_budget_usd']})
            elif p['avoided_zone_a_tonnes_simulated']<=0 and p['avoided_all_zones_tonnes_simulated']<=0:code='NO_BENEFIT'
            elif p['capital_cost_usd']>ceiling+1e-8:code='PROJECT_EXCEEDS_TOTAL_CEILING'
            elif policy=='independent' and p['capital_cost_usd']>caps[p['town']]+1e-8:code='PROJECT_EXCEEDS_LOCAL_CEILING'
            else:
                forced=plan(active,ceiling,towns,caps if policy=='independent' else None,
                            policy in ['participation','equalSpendParticipation'],objective,p['project_id'])
                if forced is None:code='NO_FEASIBLE_PORTFOLIO_WITH_PROJECT'
                else:
                    info['counterfactual_objective_t']=forced[objective]
                    info['objective_loss_t']=max(0.,result[objective]-forced[objective])
                    if info['objective_loss_t']>1e-8:code='LOWER_PORTFOLIO_BENEFIT'
                    else:code='PRIMARY_TIE_SECONDARY_OR_COST'
            info['code']=code;rows.append(info)
    return rows


def sensitivity(projects,budget,towns,baseline,objective,caps):
    cases=[];counts={policy:Counter() for policy in POLICIES};feasible=Counter();effects={policy:{p['project_id']:set() for p in projects} for policy in POLICIES}
    for cost,scale,effect in itertools.product([.75,1,1.25],[.75,1,1.25],['low','central','high']):
        pp=[dict(p,capital_cost_usd=p['capital_cost_usd']*cost) for p in projects]
        rates={t:v*scale for t,v in baseline.items()}
        plans,*_=evaluate(pp,budget,towns,effect,rates,objective,caps)
        case={'cost_multiplier':cost,'baseline_multiplier':scale,'effect':effect,'plans':{}}
        for policy,r in plans.items():
            case['plans'][policy]=None if r is None else {k:v for k,v in r.items() if k not in ['selected','feasibleCombinations']}
            if r is not None:
                ids=sorted(p['project_id'] for p in r['selected']);case['plans'][policy]['selected_ids']=ids
                feasible[policy]+=1;counts[policy].update(ids)
                for pid in ids:effects[policy][pid].add(effect)
        cases.append(case)
    selection=[]
    for policy in POLICIES:
        for p in projects:
            n=counts[policy][p['project_id']];d=feasible[policy]
            selection.append({'policy':policy,'project_id':p['project_id'],'selected_cases':n,'feasible_cases':d,
                              'status':'NO_FEASIBLE_CASE' if not d else ('NEVER_SELECTED' if not n else ('ALWAYS_SELECTED' if n==d else 'PARAMETER_SENSITIVE')),
                              'selected_only_with_optimistic_effect':effects[policy][p['project_id']]=={'high'}})
    return {'case_count':len(cases),'cases':cases,'selection':selection,
            'interpretation':'27 deterministic cases, not probabilities or confidence intervals. Costs and baseline each vary +/-25%; effects use the illustrative low/central/high bounds. A common baseline multiplier rescales benefits without changing ranking when all rates are positive.'}


def assess(projects,budget,towns,effect='central',baseline=5,objective='zoneA',local_caps=None,include_sensitivity=True):
    plans,active,rates,caps,trace=evaluate(projects,budget,towns,effect,baseline,objective,local_caps)
    groups={}
    for p in active:
        lengths=(p.get('covered_centerline_km_measured',p['covered_protected_km_measured']),p['covered_protected_km_measured'],p['covered_zone_a_km_measured'])
        if p['town'] in groups and groups[p['town']]!=lengths:raise ValueError('V1 packages in a town must use the same disjoint road group')
        groups[p['town']]=lengths
    baseline_totals={'eligible':0.,'all':0.,'zoneA':0.}
    for town,(eligible,protected,zone_a) in groups.items():
        baseline_totals['eligible']+=eligible*rates[town];baseline_totals['all']+=protected*rates[town];baseline_totals['zoneA']+=zone_a*rates[town]
    for value in baseline_totals.values():number(value,'baseline total')
    return {'objective':objective,'baseline_rates':rates,'baseline_totals_t_simulated':baseline_totals,'local_caps':caps,'plans':plans,
            'project_decisions':explain(plans,active,budget,towns,objective,caps,trace),'greedy_trace':trace,
            'sensitivity':sensitivity(projects,budget,towns,rates,objective,caps) if include_sensitivity else None}


def load_inputs():
    a=json.loads((ROOT/'results/analysis.json').read_text());config=json.loads((DIRECTORY/'scenario_config.json').read_text())
    if config['base_analysis_sha256']!=hashlib.sha256((ROOT/'results/analysis.json').read_bytes()).hexdigest():raise ValueError('Parameter geography is stale')
    towns=config['towns'];expected=[s['town'] for s in a['summary']]
    if towns!=expected or config['watershed_id']!='6000000-01S' or config['unit_basis']!='CENTERLINE_KM_PER_WINTER':raise ValueError('Unsupported pilot scope or unit')
    with (DIRECTORY/'operations_baseline.csv').open(encoding='utf-8-sig',newline='') as f:operations=list(csv.DictReader(f))
    if len(operations)!=len(towns) or {r['town_id'] for r in operations}!=set(towns):raise ValueError('One baseline row per town is required')
    rates={};groups={}
    for r in operations:
        if r['unit_basis']!='CENTERLINE_KM_PER_WINTER' or r['watershed_id']!=config['watershed_id']:raise ValueError('Unsupported baseline units or watershed')
        if r['application_rate_kg_per_lane_km'] or r['applications_per_season']:raise ValueError('Per-lane/event inputs require a verified lane model before use')
        if r['data_status']!='SIMULATED' or not r['source']:raise ValueError('This pilot accepts explicitly simulated baselines with provenance only')
        rates[r['town_id']]=number(float(r['baseline_t_per_centerline_km_per_winter']),'baseline')
        groups[r['town_id']]=r['road_group_id']
    with (DIRECTORY/'project_options.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    original={p['project_id']:p for p in a['projects']};projects=[]
    if len(rows)!=len(original) or len({r['project_id'] for r in rows})!=len(original) or {r['project_id'] for r in rows}!=set(original):raise ValueError('V1 requires the six pilot project IDs')
    for r in rows:
        p=original[r['project_id']]
        if r['town_id']!=p['town'] or r['project_type']!=p['project_type'] or r['coverage_group_id']!=groups[p['town']] or r['exclusive_group']!=p['town']:raise ValueError('Unverified project coverage or exclusivity')
        if r['annual_cost_change_usd']:raise ValueError('Annual operating costs are not modeled; leave unknown costs blank')
        if r['enabled'] not in ['true','false'] or r['data_status']!='SIMULATED' or not r['source']:raise ValueError('Invalid status or missing source')
        projects.append(dict(p,capital_cost_usd=float(r['capital_cost_usd']),reduction_low=float(r['reduction_low']),reduction_fraction=float(r['reduction_mid']),reduction_high=float(r['reduction_high']),coverage_fraction_assumed=float(r['coverage_fraction']),enabled=r['enabled']=='true',input_source=r['source']))
    if config['sensitivity']!={'cost_multipliers':[.75,1,1.25],'baseline_multipliers':[.75,1,1.25],'effects':['low','central','high']}:raise ValueError('Unsupported sensitivity configuration')
    return a,config,projects,rates


def build():
    a,config,projects,rates=load_inputs()
    result={'schema_version':1,'base_analysis_sha256':config['base_analysis_sha256'],'parameter_sha256':parameter_hashes(),'config':config,'projects':projects,
            'baseline_intensity_by_town':rates,'baseline_reference_mean':sum(rates.values())/len(rates),
            'default':assess(projects,config['total_budget_usd'],config['towns'],config['effect'],rates,config['objective'],config['local_budget_usd'])}
    with (DIRECTORY/'operations_baseline.csv').open(encoding='utf-8-sig',newline='') as f:result['operations']=list(csv.DictReader(f))
    result['parameter_fingerprint']=hashlib.sha256(json.dumps(result['parameter_sha256'],sort_keys=True).encode()).hexdigest()
    (ROOT/'results/planning_v1.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    assessment=result['default'];policy_rows=[]
    for policy,r in assessment['plans'].items():
        policy_rows.append({'policy':policy,'feasible':r is not None,'budget_ceiling_usd':config['total_budget_usd'] if not policy.startswith('equalSpend') else assessment['plans']['independent']['cost'],
                            'capital_usd':r['cost'] if r else None,'avoided_eligible_t_simulated':r['eligible'] if r else None,
                            'avoided_protected_t_simulated':r['all'] if r else None,'avoided_zone_a_t_simulated':r['zoneA'] if r else None,
                            'towns_funded':r['townsSelected'] if r else None,'selected_projects':';'.join(p['project_id'] for p in r['selected']) if r else ''})
    write_rows(ROOT/'results/investment_baselines.csv',policy_rows)
    write_rows(ROOT/'results/project_decisions.csv',assessment['project_decisions'])
    write_rows(ROOT/'results/project_stability.csv',assessment['sensitivity']['selection'])
    case_rows=[]
    for i,c in enumerate(assessment['sensitivity']['cases'],1):
        for policy,r in c['plans'].items():
            case_rows.append({'case':i,'policy':policy,**{k:v for k,v in c.items() if k!='plans'},'feasible':r is not None,'cost_usd':r['cost'] if r else None,'zone_a_t_simulated':r['zoneA'] if r else None,'protected_t_simulated':r['all'] if r else None,'selected_ids':';'.join(r['selected_ids']) if r else ''})
    write_rows(ROOT/'results/investment_sensitivity.csv',case_rows)
    print(json.dumps({'policies':len(policy_rows),'sensitivity_cases':len(assessment['sensitivity']['cases']),'policy_case_rows':len(case_rows),'baseline_t':assessment['baseline_totals_t_simulated']},indent=2))
    return result


if __name__=='__main__':build()
