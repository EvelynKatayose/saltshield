"""Capacity feasibility, conservative optimality and linked-benefit accounting."""
import copy
import itertools
import json
import math
import random
import unittest

from joint_planning import (ROOT, POLICIES, allocate_conservative, allocate_exact,
                            load_capacities, solve_joint, source_hashes, assess_reach)
from planning_v1 import load_inputs


class JointPlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.config,cls.projects,cls.rates=load_inputs()
        cls.cells=json.loads((ROOT/'results/spatial_priority.json').read_text())['cells']
        cls.capacities={r['project_id']:r['max_road_km_per_winter'] for r in load_capacities(cls.projects)}
        cls.saved=json.loads((ROOT/'results/joint_planning.json').read_text())

    def solve(self,**overrides):
        args=dict(projects=self.projects,cells=self.cells,capacities=self.capacities,budget=75000,towns=self.config['towns'],baseline=self.rates)
        args.update(overrides);return solve_joint(**args)

    def test_rounded_dp_matches_exhaustive_lexicographic_objective(self):
        rng=random.Random(81)
        for objective in ['zoneA','all']:
            primary='zone_a_km' if objective=='zoneA' else 'protected_km';secondary='protected_km' if objective=='zoneA' else 'zone_a_km'
            for trial in range(12):
                cells=[]
                for i in range(7):
                    length=rng.randint(10,250)/1000;protected=length*rng.random();zone=protected*rng.random()
                    cells.append(dict(cell_id=str(i),eligible_km=length,protected_km=protected,zone_a_km=zone))
                capacity=rng.randint(10,600)/1000;limit=math.floor((capacity+1e-10)/.01)
                options=[(sum(c[primary] for c,b in zip(cells,bits) if b),sum(c[secondary] for c,b in zip(cells,bits) if b),-sum(c['eligible_km'] for c,b in zip(cells,bits) if b))
                         for bits in itertools.product([0,1],repeat=len(cells)) if sum(math.ceil((c['eligible_km']-1e-10)/.01) for c,b in zip(cells,bits) if b)<=limit]
                result=allocate_conservative(cells,capacity,objective);ids=set(result['selected_cell_ids'])
                actual=(sum(c[primary] for c in cells if c['cell_id'] in ids),sum(c[secondary] for c in cells if c['cell_id'] in ids),-result['covered_road_km'])
                for a,b in zip(actual,max(options)):self.assertAlmostEqual(a,b,places=9)

    def test_rounding_is_conservative_and_gap_is_possible(self):
        cell=dict(cell_id='x',eligible_km=1.001,protected_km=1.001,zone_a_km=1.)
        low=allocate_conservative([cell],1.005);high=allocate_exact([cell],1.005)
        self.assertEqual(low['selected_cell_ids'],[]);self.assertEqual(high['selected_cell_ids'],['x'])
        self.assertEqual(allocate_conservative([cell],1.01)['selected_cell_ids'],['x'])

    def test_secondary_coverage_keeps_zero_primary_participation_possible(self):
        cells=[dict(cell_id='x',eligible_km=.4,protected_km=.3,zone_a_km=0.)]
        self.assertEqual(allocate_conservative(cells,.5)['selected_cell_ids'],['x'])
        self.assertEqual(allocate_exact(cells,.5)['selected_cell_ids'],['x'])

    def test_saved_inputs_feasibility_and_no_duplicate_cells(self):
        self.assertEqual(self.saved['source_sha256'],source_hashes())
        for objective,case in self.saved['benchmarks'].items():
            for policy,r in case['conservative_plans'].items():
                if r is None:continue
                self.assertEqual(len(r['selected_cell_ids']),len(set(r['selected_cell_ids'])))
                self.assertLessEqual(r['cost'],75000+1e-8)
                for p in r['selected']:
                    a=p['allocation'];self.assertLessEqual(a['covered_road_km'],a['capacity_km']+1e-8)
                    self.assertLessEqual(a['rounded_capacity_used_km'],a['capacity_km']+1e-8)
                if case['exact_plans'] and policy in ['statusQuo','independent','pooled','participation']:
                    self.assertLessEqual(r[objective],case['exact_plans'][policy][objective]+1e-6)
            if case['exact_plans'] is None:
                self.assertEqual(case['status'],'NOT_CERTIFIED');self.assertTrue(case['note'])

    def test_coverage_is_ceiling_not_a_second_reduction_multiplier(self):
        projects=copy.deepcopy(self.projects)
        for p in projects:p['coverage_fraction_assumed']=.5
        result=self.solve(projects=projects)
        by_id={c['cell_id']:c for c in self.cells}
        for p in result['profiles']:
            self.assertLessEqual(p['allocation']['capacity_km'],p['covered_centerline_km_measured']*.5+1e-8)
            km=sum(by_id[cid]['zone_a_km'] for cid in p['allocation']['selected_cell_ids'])
            self.assertAlmostEqual(p['avoided_zone_a_tonnes_simulated'],km*self.rates[p['town']]*p['active_reduction'])

    def test_zero_budget_and_zero_reach(self):
        self.assertEqual(self.solve(budget=0)['plans']['pooled']['selected'],[])
        zero=self.solve(capacities={pid:0 for pid in self.capacities})
        self.assertEqual(zero['plans']['pooled']['selected'],[]);self.assertIsNone(zero['plans']['participation'])

    def test_same_equipment_uniform_reference_is_independent_of_rounding(self):
        result=self.solve()['plans']['pooled'];expected=0.
        for p in result['selected']:
            expected+=p['covered_zone_a_km_measured']*p['allocation']['capacity_km']/p['covered_centerline_km_measured']*self.rates[p['town']]*p['active_reduction']
        self.assertAlmostEqual(result['uniform_same_equipment']['zoneA'],expected)

    def test_invalid_capacity_and_cell_scope_rejected(self):
        for bad in [-1,float('nan'),float('inf')]:
            capacities=dict(self.capacities);capacities[next(iter(capacities))]=bad
            with self.assertRaises(ValueError):self.solve(capacities=capacities)
        with self.assertRaises(ValueError):self.solve(capacities={})
        with self.assertRaises(ValueError):self.solve(cells=self.cells+[self.cells[0]])
        cells=copy.deepcopy(self.cells);cells[0]['eligible_km']+=1
        with self.assertRaises(ValueError):self.solve(cells=cells)

    def test_reach_grid_central_case_and_retention(self):
        check=self.saved['reach_sensitivity'];base=self.saved['default']
        self.assertEqual(check['case_count'],9);self.assertEqual(len(check['cases']),9)
        self.assertEqual(len(check['selection']),42)
        central=next(c for c in check['cases'] if c['cal_multiplier']==c['brine_multiplier']==1)
        for policy,r in central['plans'].items():
            if r is None:continue
            self.assertEqual(r['selected_ids'],sorted(p['project_id'] for p in base['plans'][policy]['selected']))
            self.assertTrue(r['same_equipment_as_current'])
            if r['covered_road_km']>0:self.assertAlmostEqual(r['retained_base_road_fraction'],1.)
        for c in check['cases']:
            for p in self.projects:self.assertAlmostEqual(c['capacities'][p['project_id']],self.capacities[p['project_id']]*(c['cal_multiplier'] if p['project_type']=='CAL' else c['brine_multiplier']))
            for r in c['plans'].values():
                if r is not None and r['retained_base_road_fraction'] is not None:self.assertTrue(0<=r['retained_base_road_fraction']<=1+1e-8)

    def test_reach_expansion_cannot_lower_optimal_primary_benefit(self):
        cases=self.saved['reach_sensitivity']['cases']
        for a in cases:
            for b in cases:
                if a['cal_multiplier']<=b['cal_multiplier'] and a['brine_multiplier']<=b['brine_multiplier']:
                    for policy in ['pooled','independent','participation']:
                        x=a['plans'][policy];y=b['plans'][policy]
                        if x is not None:self.assertIsNotNone(y);self.assertLessEqual(x['zoneA'],y['zoneA']+1e-6)

    def test_no_reach_has_no_participation_or_undefined_retention(self):
        check=assess_reach(self.projects,self.cells,{pid:0 for pid in self.capacities},75000,self.config['towns'],baseline=self.rates)
        self.assertEqual(check['summaries']['participation']['feasible_cases'],0)
        self.assertIsNone(check['summaries']['participation']['objective_t_low'])
        for case in check['cases']:
            self.assertIsNone(case['plans']['participation']);self.assertIsNone(case['plans']['pooled']['retained_base_road_fraction'])
        self.assertTrue(all(r['selected_cases']==0 for r in check['selection']))

    def test_reach_check_does_not_modify_inputs(self):
        projects=copy.deepcopy(self.projects);reach=dict(self.capacities)
        assess_reach(projects,self.cells,reach,45000,self.config['towns'],baseline=self.rates)
        self.assertEqual(projects,self.projects);self.assertEqual(reach,self.capacities)
        projects[0]['project_type']='UNKNOWN'
        with self.assertRaises(ValueError):assess_reach(projects,self.cells,reach,45000,self.config['towns'])


if __name__=='__main__':unittest.main()
