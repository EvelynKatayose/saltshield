"""Weather calendar/missingness and spatial capacity/optimality tests."""
import copy
import hashlib
import itertools
import json
import unittest
from datetime import datetime, timezone

from build_weather import EXPECTED_UNITS, NY, summarize_season
from spatial_priority import ROOT, allocate, fingerprint


class WeatherTests(unittest.TestCase):
    def fixture(self):
        item={'season':'test','local_start':'2021-11-07','local_end_exclusive':'2021-11-08'}
        start=datetime(2021,11,7,tzinfo=NY).astimezone(timezone.utc)
        end=datetime(2021,11,8,tzinfo=NY).astimezone(timezone.utc)
        times=list(range(int(start.timestamp()),int(end.timestamp()),3600))
        h={'time':times, 'temperature_2m':[1.]*len(times), 'precipitation':[.1]*len(times),
           'snowfall':[0.]*len(times),'wind_speed_10m':[2.]*len(times)}
        return item,{'hourly':h,'hourly_units':EXPECTED_UNITS.copy()}

    def test_repeated_dst_hour_retained_with_distinct_utc_offsets(self):
        rows,days,s=summarize_season(*self.fixture())
        self.assertEqual(s['hours'],25);self.assertEqual(days[0]['hours_in_local_day'],25)
        repeated=[r['timestamp_local'] for r in rows if 'T01:00:00' in r['timestamp_local']]
        self.assertEqual(len(repeated),2);self.assertNotEqual(repeated[0],repeated[1])

    def test_missing_value_is_not_treated_as_zero(self):
        item,p=self.fixture();p['hourly']['temperature_2m'][0]=None;p['hourly']['precipitation'][1]=None
        _,days,s=summarize_season(item,p)
        self.assertIsNone(s['min_air_temperature_c']);self.assertIsNone(s['precipitation_total_mm'])
        self.assertIsNone(days[0]['precipitation_mm']);self.assertEqual(s['cold_wet_hours'],23)
        self.assertTrue(s['cold_wet_is_lower_bound_due_to_missing_data'])

    def test_timestamp_gaps_units_and_nonfinite_values_rejected(self):
        item,p=self.fixture()
        for kind in ['gap','unit','nan','negative']:
            q=copy.deepcopy(p)
            if kind=='gap':q['hourly']['time'][1]+=3600
            if kind=='unit':q['hourly_units']['snowfall']='mm'
            if kind=='nan':q['hourly']['temperature_2m'][0]=float('nan')
            if kind=='negative':q['hourly']['precipitation'][0]=-1
            with self.subTest(kind=kind),self.assertRaises(ValueError):summarize_season(item,q)

    def test_five_cached_winters_complete_and_checksummed(self):
        manifest=json.loads((ROOT/'data/weather/source_manifest.json').read_text())
        result=json.loads((ROOT/'results/weather_context.json').read_text())
        self.assertEqual(len(manifest['responses']),5);self.assertEqual(result['total_hours'],18144)
        self.assertEqual(sum(s['local_days'] for s in result['summaries']),756)
        for item in manifest['responses']:
            content=(ROOT/'data/weather'/item['file']).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(),item['sha256'])
            _,_,s=summarize_season(item,json.loads(content))
            self.assertEqual(s,next(x for x in result['summaries'] if x['season']==item['season']))
            self.assertTrue(all(n==0 for n in s['missing_values'].values()))


class SpatialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=json.loads((ROOT/'results/spatial_priority.json').read_text())
        cls.cells=cls.result['cells']

    def test_integer_matches_exhaustive_solution_when_greedy_fails(self):
        cells=[{'cell_id':str(i),'eligible_km':w,'zone_a_km':v,'protected_km':w}
               for i,(w,v) in enumerate([(10,6),(20,10),(30,12)])]
        brute=max(sum(c['zone_a_km'] for c,b in zip(cells,bits) if b)
                  for bits in itertools.product([0,1],repeat=3)
                  if sum(c['eligible_km'] for c,b in zip(cells,bits) if b)<=50)
        integer=allocate(cells,50,'integer');greedy=allocate(cells,50,'greedy')
        self.assertAlmostEqual(integer['covered_zone_a_km'],brute)
        self.assertGreater(integer['covered_zone_a_km'],greedy['covered_zone_a_km'])

    def test_grid_totals_conserve_measured_eligible_length(self):
        base=json.loads((ROOT/'results/analysis.json').read_text())
        for town,total in self.result['town_totals'].items():
            subset=[c for c in self.cells if c['town']==town]
            original=next(s for s in base['summary'] if s['town']==town)
            for key in ['eligible_km','zone_a_km','protected_km']:
                self.assertAlmostEqual(sum(c[key] for c in subset),total[key],places=6)
            self.assertAlmostEqual(total['zone_a_km'],original['eligible_municipal_paved_zone_a_km'],places=6)
        self.assertEqual(self.result['source_sha256'],fingerprint())
        self.assertEqual(self.result['planning_cells_sha256'],hashlib.sha256((ROOT/'data/processed/planning_cells.geojson').read_bytes()).hexdigest())
        self.assertLess(self.result['max_unassigned_segment_m'],1e-6)
        self.assertEqual(len({c['cell_id'] for c in self.cells}),len(self.cells))

    def test_all_cases_capacity_membership_and_objective_bounds(self):
        by_id={c['cell_id']:c for c in self.cells}
        self.assertEqual(len(self.result['cases']),12)
        for case in self.result['cases']:
            plans=case['plans']
            self.assertLessEqual(plans['greedy']['covered_zone_a_km'],plans['integer']['covered_zone_a_km']+1e-6)
            self.assertLessEqual(plans['integer']['covered_zone_a_km'],plans['fractional_bound']['covered_zone_a_km']+1e-6)
            for method,p in plans.items():
                self.assertLessEqual(p['covered_road_km'],p['capacity_km']+1e-6)
                self.assertAlmostEqual(p['covered_zone_a_km'],sum(by_id[cid]['zone_a_km']*share for cid,share in p['cell_shares'].items()))
                for cid,share in p['cell_shares'].items():
                    self.assertEqual(by_id[cid]['town'],case['town']);self.assertTrue(0<share<=1)
                    if method in ['integer','greedy']:self.assertEqual(share,1)

    def test_full_capacity_covers_all_and_zero_capacity_selects_none(self):
        for town in self.result['town_totals']:
            cells=[c for c in self.cells if c['town']==town]
            for method in ['uniform','greedy','integer','fractional_bound']:
                self.assertEqual(allocate(cells,0,method)['covered_road_km'],0)
                r=allocate(cells,sum(c['eligible_km'] for c in cells),method)
                self.assertAlmostEqual(r['covered_zone_a_km'],sum(c['zone_a_km'] for c in cells))

    def test_report_has_both_panels_and_no_unresolved_placeholders(self):
        report=(ROOT/'results/SaltShield_Wachusett.html').read_text()
        for key in ['weather-panel','spatial-panel','spatial-fraction','spatial-export']:
            self.assertIn('id="'+key+'"',report)
        self.assertNotIn('__ANALYSIS_JSON__',report);self.assertNotIn('__MAP__',report)


if __name__=='__main__':unittest.main()
