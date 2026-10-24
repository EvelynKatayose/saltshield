"""Validate cached reanalysis and aggregate by America/New_York calendar dates."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
NY = ZoneInfo('America/New_York')
EXPECTED_UNITS = {'temperature_2m': '°C', 'precipitation': 'mm', 'snowfall': 'cm', 'wind_speed_10m': 'm/s'}


def summarize_season(item, payload):
    h = payload['hourly']; timestamps = h['time']
    if len(timestamps) != len(set(timestamps)) or any(b-a != 3600 for a,b in zip(timestamps,timestamps[1:])):
        raise ValueError('Weather timestamps must be unique consecutive UTC hours')
    for key,unit in EXPECTED_UNITS.items():
        if payload['hourly_units'][key] != unit or len(h[key]) != len(timestamps):
            raise ValueError('Unexpected units or array length for '+key)
    start = datetime.fromisoformat(item['local_start']).replace(tzinfo=NY)
    end = datetime.fromisoformat(item['local_end_exclusive']).replace(tzinfo=NY)
    expected = int((end.astimezone(timezone.utc)-start.astimezone(timezone.utc)).total_seconds()/3600)
    rows=[]; daily=defaultdict(list)
    for i,t in enumerate(timestamps):
        utc=datetime.fromtimestamp(t,timezone.utc); local=utc.astimezone(NY)
        if not start <= local < end:
            continue
        row={'season':item['season'],'timestamp_utc':utc.isoformat(),'timestamp_local':local.isoformat()}
        for key in EXPECTED_UNITS:
            v=h[key][i]
            if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)):
                raise ValueError('Non-finite weather value')
            if key!='temperature_2m' and v is not None and v<0:
                raise ValueError('Negative precipitation, snowfall or wind')
            row[key]=v
        rows.append(row);daily[local.date().isoformat()].append(row)
    if len(rows)!=expected:
        raise ValueError(f'Incomplete local winter: {len(rows)} != {expected}')
    drows=[]
    for day,rr in sorted(daily.items()):
        temp=[r['temperature_2m'] for r in rr if r['temperature_2m'] is not None]
        complete={key:all(r[key] is not None for r in rr) for key in EXPECTED_UNITS}
        drows.append({'season':item['season'],'local_date':day,'hours_in_local_day':len(rr),
                      'temp_min_c':min(temp) if complete['temperature_2m'] else None,
                      'temp_max_c':max(temp) if complete['temperature_2m'] else None,
                      'precipitation_mm':sum(r['precipitation'] for r in rr) if complete['precipitation'] else None,
                      'snowfall_cm':sum(r['snowfall'] for r in rr) if complete['snowfall'] else None,
                      'cold_wet_hours':sum(r['temperature_2m'] is not None and r['precipitation'] is not None and r['temperature_2m']<=2 and r['precipitation']>=.1 for r in rr),
                      'data_kind':'ERA5_REANALYSIS'})
    missing={key:sum(r[key] is None for r in rows) for key in EXPECTED_UNITS}
    complete=lambda key:missing[key]==0
    temps=[r['temperature_2m'] for r in rows if r['temperature_2m'] is not None]
    summary={'season':item['season'],'hours':len(rows),'local_days':len(drows),
             'min_air_temperature_c':min(temps) if complete('temperature_2m') else None,
             'precipitation_total_mm':sum(r['precipitation'] for r in rows) if complete('precipitation') else None,
             'snowfall_total_cm':sum(r['snowfall'] for r in rows) if complete('snowfall') else None,
             'cold_wet_hours':sum(r['cold_wet_hours'] for r in drows),
             'missing_values':missing,'cold_wet_is_lower_bound_due_to_missing_data':bool(missing['temperature_2m'] or missing['precipitation'])}
    return rows,drows,summary


def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def build():
    directory=ROOT/'data/weather';manifest=json.loads((directory/'source_manifest.json').read_text())
    hourly=[];daily=[];summaries=[]
    for item in manifest['responses']:
        content=(directory/item['file']).read_bytes()
        if hashlib.sha256(content).hexdigest()!=item['sha256']:
            raise ValueError('Weather snapshot checksum mismatch')
        rows,days,s=summarize_season(item,json.loads(content));hourly+=rows;daily+=days;summaries.append(s)
    write_csv(directory/'hourly_winter_context.csv',hourly);write_csv(directory/'daily_winter_context.csv',daily)
    result={'manifest_sha256':hashlib.sha256((directory/'source_manifest.json').read_bytes()).hexdigest(),
            'model':'ERA5','data_kind':'REGIONAL_REANALYSIS','reference':{'requested_latitude':manifest['requested_reference_latitude'],'requested_longitude':manifest['requested_reference_longitude'],'grid_latitude':manifest['responses'][0]['grid_latitude'],'grid_longitude':manifest['responses'][0]['grid_longitude']},
            'summaries':summaries,'daily':daily,'total_hours':len(hourly),
            'cold_wet_definition':'Count of hours with 2 m air temperature <= 2 C and preceding-hour precipitation >= 0.1 mm; descriptive threshold, not a road icing diagnosis.',
            'decision_boundary':'Historical context only. This weather does not calibrate baseline salt usage, road-surface conditions, or investment effects.',
            'attribution':manifest['attribution'],'source_documentation':manifest['documentation']}
    (ROOT/'results/weather_context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'seasons':len(summaries),'hours':len(hourly),'days':len(daily),'summaries':summaries},indent=2))
    return result


if __name__=='__main__':build()
