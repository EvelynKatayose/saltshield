"""Boundary, accounting, and evidence tests; no network calls."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

from build_evidence import parse_awards
from phase2_model import compare, materialize, plan

ROOT = Path(__file__).resolve().parent


class InvestmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = json.loads((ROOT / 'results/analysis.json').read_text())
        cls.projects = a['projects']
        cls.towns = [s['town'] for s in a['summary']]
        cls.original = a

    def test_original_default_remains_reproducible(self):
        r = compare(self.projects, 75000, self.towns)
        self.assertAlmostEqual(r['pooled']['zoneA'], self.original['comparison']['pooled']['avoided_zone_a_tonnes_simulated'])
        self.assertAlmostEqual(r['independent']['zoneA'], 41.53630144502182)

    def test_equal_spend_participation_exposes_concentration_tradeoff(self):
        r = compare(self.projects, 75000, self.towns)
        self.assertEqual(r['equalSpend']['cost'], 45000)
        self.assertEqual(r['equalSpend']['townsSelected'], 2)
        self.assertEqual(r['equalSpendParticipation']['townsSelected'], 3)
        self.assertAlmostEqual(r['equalSpendParticipation']['zoneA'], r['independent']['zoneA'])

    def test_participation_is_infeasible_below_three_minimum_projects(self):
        self.assertIsNone(compare(self.projects, 30000, self.towns)['participation'])

    def test_disabled_town_is_not_silently_included(self):
        pp = [dict(p, enabled=p['town'] != 'WEST BOYLSTON') for p in self.projects]
        r = compare(pp, 90000, self.towns)
        self.assertIsNone(r['participation'])
        self.assertTrue(all(p['town'] != 'WEST BOYLSTON' for p in r['pooled']['selected']))

    def test_coverage_scales_benefit_not_capital_cost(self):
        p = copy.deepcopy(self.projects[:1]); q = materialize(p, self.towns)[0]
        p[0]['coverage_fraction_assumed'] = .25
        x = materialize(p, self.towns)[0]
        self.assertAlmostEqual(x['avoided_zone_a_tonnes_simulated'], q['avoided_zone_a_tonnes_simulated'] * .25)
        self.assertEqual(x['capital_cost_usd'], q['capital_cost_usd'])

    def test_invalid_operational_inputs_rejected(self):
        for field, value in [('capital_cost_usd', -1), ('capital_cost_usd', float('nan')), ('coverage_fraction_assumed', 1.1), ('enabled', 'yes'), ('reduction_fraction', .9)]:
            pp = copy.deepcopy(self.projects); pp[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                compare(pp, 75000, self.towns)

    def test_unknown_or_duplicate_project_rejected(self):
        with self.assertRaises(ValueError):
            materialize(self.projects + self.projects[:1], self.towns)
        pp = copy.deepcopy(self.projects); pp[0]['town'] = 'OTHER'
        with self.assertRaises(ValueError):
            materialize(pp, self.towns)

    def test_zero_budget_and_zero_baseline_do_not_spend_for_zero_benefit(self):
        self.assertEqual(compare(self.projects, 0, self.towns)['pooled']['cost'], 0)
        self.assertEqual(compare(self.projects, 75000, self.towns, baseline_intensity=0)['pooled']['cost'], 0)

    def test_arbitrary_town_count_not_hardcoded_to_three(self):
        pp = materialize([p for p in self.projects if p['town'] == 'HOLDEN'], ['HOLDEN'])
        self.assertEqual(plan(pp, 30000, ['HOLDEN'])['townsSelected'], 1)

    def test_all_budget_cases_respect_constraints(self):
        for budget in [0, 30000, 45000, 60000, 75000, 90000, 120000]:
            for effect in ['low', 'central', 'high']:
                r = compare(self.projects, budget, self.towns, effect)
                self.assertGreaterEqual(r['pooled']['zoneA'] + 1e-8, r['independent']['zoneA'])
                for mode, result in r.items():
                    if result is None:
                        continue
                    self.assertLessEqual(result['cost'], budget)
                    self.assertEqual(len({p['town'] for p in result['selected']}), len(result['selected']))
                    if mode == 'independent':
                        for p in result['selected']:
                            self.assertLessEqual(p['capital_cost_usd'], budget / len(self.towns))


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (ROOT / 'data/evidence/dcr_salt_reduction_source.html').read_bytes()
        cls.records = parse_awards(cls.content)

    def test_source_snapshot_and_row_count(self):
        manifest = json.loads((ROOT / 'data/evidence/source_manifest.json').read_text())
        self.assertEqual(hashlib.sha256(self.content).hexdigest(), manifest['sha256'])
        self.assertEqual(len(self.records), 18)

    def test_grant_is_not_project_cost(self):
        h = next(r for r in self.records if r['town'] == 'HOLDEN' and r['fiscal_year'] == 2023)
        self.assertEqual(h['grant_award_usd'], 20000)
        self.assertEqual(h['reported_historical_project_total_usd'], 150000)
        self.assertFalse(h['grant_is_equipment_price'])
        self.assertFalse(h['installation_verified'])

    def test_missing_total_cost_stays_missing(self):
        s = next(r for r in self.records if r['town'] == 'STERLING' and r['fiscal_year'] == 2026)
        self.assertEqual(s['grant_award_usd'], 19585)
        self.assertIsNone(s['reported_historical_project_total_usd'])

    def test_target_award_totals(self):
        rr = [r for r in self.records if r['town'] in {'HOLDEN', 'STERLING', 'WEST BOYLSTON'}]
        self.assertEqual(len(rr), 13)
        self.assertEqual(sum(r['grant_award_usd'] for r in rr), 188251)


if __name__ == '__main__':
    unittest.main()
