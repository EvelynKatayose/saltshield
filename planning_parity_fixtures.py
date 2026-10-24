"""Emit deterministic Python expectations for the independent JS implementation."""
import copy
import itertools
import json

from planning_v1 import assess,load_inputs


def compact(result):
    r=copy.deepcopy(result)
    for plan in r['plans'].values():
        if plan is not None:
            plan['selected_ids']=sorted(p['project_id'] for p in plan.pop('selected'))
    return r


def fixtures():
    _,config,original,rates=load_inputs();towns=config['towns'];cases=[]
    for variant in ['default','disabled_town','free_project','partial_coverage','nonuniform_baseline']:
        for budget,effect,objective in itertools.product([0,30000,45000,75000,90000],['low','central','high'],['zoneA','all']):
            pp=copy.deepcopy(original);baseline=rates.copy()
            if variant=='disabled_town':
                for p in pp:
                    if p['town']==towns[-1]:p['enabled']=False
            if variant=='free_project':pp[0]['capital_cost_usd']=0
            if variant=='partial_coverage':
                for p in pp:p['coverage_fraction_assumed']=.5 if p['project_type']=='CAL' else .25
            if variant=='nonuniform_baseline':baseline=dict(zip(towns,[2.,4.,7.]))
            inputs={'projects':pp,'budget':budget,'towns':towns,'effect':effect,'baseline':baseline,'objective':objective,'local_caps':None,'include_sensitivity':False}
            cases.append({'name':f'{variant}/{budget}/{effect}/{objective}','input':inputs,'expected':compact(assess(**inputs))})
    for objective in ['zoneA','all']:
        inputs={'projects':original,'budget':75000,'towns':towns,'effect':'central','baseline':rates,'objective':objective,'local_caps':config['local_budget_usd'],'include_sensitivity':True}
        cases.append({'name':'full_sensitivity/'+objective,'input':inputs,'expected':compact(assess(**inputs))})
    return cases


if __name__=='__main__':print(json.dumps(fixtures(),allow_nan=False))
