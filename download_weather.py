"""Fetch five complete regional winters; no forecasts or road-surface inference."""
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parent
DIRECTORY = ROOT / 'data/weather'
VARIABLES = ['temperature_2m', 'precipitation', 'snowfall', 'wind_speed_10m']


def prepare_requests():
    w = json.loads((ROOT / 'data/processed/watershed.geojson').read_text())['features'][0]
    forward = Transformer.from_crs(4326, 26986, always_xy=True).transform
    inverse = Transformer.from_crs(26986, 4326, always_xy=True).transform
    center = transform(inverse, transform(forward, shape(w['geometry'])).centroid)
    requests = []
    for start in range(2021, 2026):
        params = {'latitude': round(center.y, 6), 'longitude': round(center.x, 6),
                  'start_date': f'{start}-11-01', 'end_date': f'{start+1}-04-01',
                  'hourly': ','.join(VARIABLES), 'models': 'era5', 'timezone': 'UTC',
                  'timeformat': 'unixtime', 'wind_speed_unit': 'ms'}
        requests.append({'season': f'{start}-{start+1}', 'file': f'era5_{start}_{start+1}.json',
                         'url': 'https://archive-api.open-meteo.com/v1/archive?' + urllib.parse.urlencode(params),
                         'local_start': f'{start}-11-01', 'local_end_exclusive': f'{start+1}-04-01'})
    plan = {'requested_reference_latitude': round(center.y, 6), 'requested_reference_longitude': round(center.x, 6),
            'model': 'ERA5', 'spatial_resolution_degrees': .25, 'variables': VARIABLES,
            'documentation': 'https://open-meteo.com/en/docs/historical-weather-api',
            'attribution': 'ERA5 / Copernicus Climate Change Service via Open-Meteo; Open-Meteo data CC BY 4.0 attribution required.',
            'data_kind': 'HISTORICAL_GRIDDED_REANALYSIS_NOT_ROAD_SENSOR_OBSERVATIONS', 'requests': requests}
    DIRECTORY.mkdir(exist_ok=True)
    (DIRECTORY / 'request_plan.json').write_text(json.dumps(plan, indent=2))
    return plan


def finalize(plan):
    logs = json.loads((DIRECTORY / 'download_log.json').read_text())
    entries = []
    for item in plan['requests']:
        file = DIRECTORY / item['file']; payload = json.loads(file.read_text())
        if payload.get('error') or not payload.get('hourly', {}).get('time'):
            raise ValueError('Invalid weather response for ' + item['season'])
        entries.append({**item, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                        'retrieved_at': logs[item['file']], 'grid_latitude': payload['latitude'],
                        'grid_longitude': payload['longitude'], 'elevation_m': payload.get('elevation'),
                        'raw_hour_count': len(payload['hourly']['time']), 'units': payload['hourly_units']})
    manifest = {**plan, 'responses': entries,
                'limitation': 'One coarse regional reference grid. No local road temperatures, treatment rates, accident probabilities or causal salt-use estimates are inferred.'}
    (DIRECTORY / 'source_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'model': 'ERA5', 'seasons': len(entries), 'reference': [plan['requested_reference_latitude'], plan['requested_reference_longitude']]}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--plan-only', action='store_true'); parser.add_argument('--finalize', action='store_true')
    args = parser.parse_args(); plan = prepare_requests()
    if args.plan_only:
        print(json.dumps(plan, indent=2))
    elif args.finalize:
        finalize(plan)
    else:
        logs = {}
        for item in plan['requests']:
            with urllib.request.urlopen(item['url'], timeout=90) as response:
                payload = json.load(response)
            (DIRECTORY / item['file']).write_text(json.dumps(payload))
            logs[item['file']] = datetime.now(timezone.utc).isoformat()
        (DIRECTORY / 'download_log.json').write_text(json.dumps(logs, indent=2)); finalize(plan)
