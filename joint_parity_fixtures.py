"""Emit linked cases for the JavaScript implementation, including edge cases."""
import copy
import json
from joint_planning import ROOT, load_capacities, solve_joint, assess_reach
from planning_v1 import load_inputs


def fixtures():
    _,config,projects,rates=load_inputs();cells=json.loads((ROOT/'results/spatial_priority.json').read_text())['cells']
    capacities={r['project_id']:r['max_road_km_per_winter'] for r in load_capacities(projects)}
    cases=[]
    settings=[('default',75000,'zoneA','central'),('all',75000,'all','central'),('zero_budget',0,'zoneA','central'),('low_budget',30000,'zoneA','low'),('same_spend',45000,'zoneA','high'),('full_budget',90000,'all','high')]
    settings.extend((name,75000,'zoneA','central') for name in ['zero_reach','tiny_reach','fractional_reach','half_coverage','disabled_town','free_projects','unequal_baseline','unequal_caps'])
    for name,budget,objective,effect in settings:
        pp=copy.deepcopy(projects);reach=dict(capacities);rr=dict(rates);caps={t:budget/3 for t in config['towns']}
        if name=='zero_reach':reach={pid:0 for pid in reach}
        if name=='tiny_reach':reach={pid:.005 for pid in reach}
        if name=='fractional_reach':reach={pid:17.319 for pid in reach}
        if name=='half_coverage':
            for p in pp:p['coverage_fraction_assumed']=.5
        if name=='disabled_town':
            for p in pp:
                if p['town']==config['towns'][0]:p['enabled']=False
        if name=='free_projects':
            for p in pp:p['capital_cost_usd']=0
        if name=='unequal_baseline':rr={t:(i+1)*2.75 for i,t in enumerate(config['towns'])}
        if name=='unequal_caps':caps={t:v for t,v in zip(config['towns'],[15000,30000,30000])}
        result=solve_joint(pp,cells,reach,budget,config['towns'],effect,rr,objective,caps)
        sensitivity=assess_reach(pp,cells,reach,budget,config['towns'],effect,rr,objective,caps) if name in ['default','all','zero_reach','disabled_town','low_budget'] else None
        cases.append(dict(name=name,projects=pp,capacities=reach,budget=budget,towns=config['towns'],effect=effect,baseline=rr,objective=objective,local_caps=caps,expected=result,expected_reach=sensitivity))
    return dict(cells=cells,cases=cases)


if __name__=='__main__':print(json.dumps(fixtures(),allow_nan=False))
