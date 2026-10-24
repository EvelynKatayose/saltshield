"""Hand-checkable portfolio tests and operational-table boundaries."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from planning_v1 import ROOT,assess,load_inputs
from prepare_parameters import FILES,write_rows


def project(pid,town,cost,zone_a,protected=None):
    protected=zone_a if protected is None else protected
    return {'project_id':pid,'town':town,'project_type':'TEST','capital_cost_usd':cost,
            'covered_centerline_km_measured':protected,'covered_protected_km_measured':protected,
            'covered_zone_a_km_measured':zone_a,'reduction_low':1,'reduction_fraction':1,'reduction_high':1,
            'coverage_fraction_assumed':1,'enabled':True}


class PortfolioTests(unittest.TestCase):
    def test_knapsack_counterexample_beats_ratio_heuristic(self):
        pp=[project('A','A',10,6),project('B','B',20,10),project('C','C',30,12)]
        a=assess(pp,50,['A','B','C'],baseline=1,include_sensitivity=False)
        self.assertEqual(a['plans']['greedy']['zoneA'],16)
        self.assertEqual(a['plans']['pooled']['zoneA'],22)
        self.assertEqual({p['project_id'] for p in a['plans']['pooled']['selected']},{'B','C'})

    def test_protected_objective_can_change_the_portfolio(self):
        pp=[project('A','A',30,1,100),project('B','B',30,10,10)]
        z=assess(pp,30,['A','B'],baseline=1,include_sensitivity=False)
        p=assess(pp,30,['A','B'],baseline=1,objective='all',include_sensitivity=False)
        self.assertEqual(z['plans']['pooled']['selected'][0]['project_id'],'B')
        self.assertEqual(p['plans']['pooled']['selected'][0]['project_id'],'A')

    def test_baseline_not_counted_twice_for_alternative_packages(self):
        pp=[project('A1','A',10,2,10),project('A2','A',20,2,10),project('B','B',10,1,5)]
        pp[0]['coverage_fraction_assumed']=.5
        r=assess(pp,30,['A','B'],baseline={'A':2,'B':3},include_sensitivity=False)
        self.assertEqual(r['baseline_totals_t_simulated'],{'eligible':35,'all':35,'zoneA':7})
        self.assertLessEqual(r['plans']['pooled']['eligible'],35)
        self.assertEqual(len({p['town'] for p in r['plans']['pooled']['selected']}),len(r['plans']['pooled']['selected']))

    def test_zero_budget_and_zero_effect_baselines(self):
        pp=[project('A','A',10,5)]
        self.assertEqual(assess(pp,0,['A'],include_sensitivity=False)['plans']['pooled']['cost'],0)
        r=assess(pp,10,['A'],baseline=0,include_sensitivity=False)
        self.assertEqual(r['plans']['pooled']['cost'],0)
        self.assertEqual(r['plans']['statusQuo']['zoneA'],0)

    def test_zero_cost_projects_are_json_safe_and_budget_feasible(self):
        pp=[project('A','A',0,5)]
        r=assess(pp,0,['A'],baseline=1)
        self.assertEqual(r['plans']['greedy']['zoneA'],5)
        self.assertIsNone(r['greedy_trace'][0]['benefit_per_dollar'])
        json.dumps(r,allow_nan=False)

    def test_counterfactual_explanation_matches_manual_objective_loss(self):
        pp=[project('A','A',30,1,100),project('B','B',30,10,10)]
        r=assess(pp,30,['A','B'],baseline=1,include_sensitivity=False)
        reason=next(x for x in r['project_decisions'] if x['policy']=='pooled' and x['project_id']=='A')
        self.assertEqual(reason['code'],'LOWER_PORTFOLIO_BENEFIT');self.assertEqual(reason['objective_loss_t'],9)
        reason=next(x for x in r['project_decisions'] if x['policy']=='independent' and x['project_id']=='A')
        self.assertEqual(reason['code'],'PROJECT_EXCEEDS_LOCAL_CEILING')

    def test_disabled_and_infeasible_participation_are_distinct(self):
        pp=[project('A','A',10,1),project('B','B',10,1)];pp[1]['enabled']=False
        r=assess(pp,20,['A','B'],include_sensitivity=False)
        self.assertIsNone(r['plans']['participation'])
        reasons={x['project_id']:x['code'] for x in r['project_decisions'] if x['policy']=='participation'}
        self.assertEqual(reasons,{'A':'POLICY_INFEASIBLE','B':'DISABLED'})

    def test_bad_scopes_caps_and_nonmatching_road_groups_rejected(self):
        pp=[project('A','A',10,1)]
        for kw in [{'objective':'unknown'},{'local_caps':{'A':5}},{'local_caps':{'A':10,'OTHER':0}},{'baseline':float('nan')},{'baseline':{'OTHER':5}}]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):assess(pp,10,['A'],include_sensitivity=False,**kw)
        with self.assertRaises(ValueError):assess([project('large','A',10,10)],10,['A'],baseline=1e308,include_sensitivity=False)
        pp.append(project('A2','A',10,2))
        with self.assertRaises(ValueError):assess(pp,10,['A'],include_sensitivity=False)

    def test_27_case_counts_and_capacity_bounds(self):
        _,config,pp,rates=load_inputs()
        r=assess(pp,config['total_budget_usd'],config['towns'],baseline=rates)
        self.assertEqual(r['sensitivity']['case_count'],27)
        for case in r['sensitivity']['cases']:
            plans=case['plans']
            self.assertGreaterEqual(plans['pooled']['zoneA']+1e-8,plans['greedy']['zoneA'])
            self.assertGreaterEqual(plans['pooled']['zoneA']+1e-8,plans['independent']['zoneA'])
            for plan in plans.values():
                if plan is not None:self.assertLessEqual(plan['cost'],config['total_budget_usd']+1e-8)
        for row in r['sensitivity']['selection']:
            cases=[c['plans'][row['policy']] for c in r['sensitivity']['cases'] if c['plans'][row['policy']] is not None]
            self.assertEqual(row['feasible_cases'],len(cases))
            self.assertEqual(row['selected_cases'],sum(row['project_id'] in c['selected_ids'] for c in cases))


class ParameterTableTests(unittest.TestCase):
    def test_unknown_lane_and_operating_cost_fields_remain_blank(self):
        import csv
        with (ROOT/'data/parameters/operations_baseline.csv').open(encoding='utf-8-sig') as f:ops=list(csv.DictReader(f))
        with (ROOT/'data/parameters/project_options.csv').open(encoding='utf-8-sig') as f:pp=list(csv.DictReader(f))
        self.assertTrue(all(not r['application_rate_kg_per_lane_km'] and not r['applications_per_season'] for r in ops))
        self.assertTrue(all(not p['annual_cost_change_usd'] for p in pp))

    def test_parameter_loader_does_not_silently_use_unsupported_costs(self):
        import csv
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            for name in FILES:shutil.copyfile(ROOT/'data/parameters'/name,directory/name)
            with (directory/'project_options.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            rows[0]['annual_cost_change_usd']='1000';write_rows(directory/'project_options.csv',rows)
            with patch('planning_v1.DIRECTORY',directory),self.assertRaisesRegex(ValueError,'Annual operating costs'):load_inputs()


if __name__=='__main__':unittest.main()
