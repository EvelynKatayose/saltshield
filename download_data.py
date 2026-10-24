"""Download official public ArcGIS extracts for the SaltShield pilot.
Run once with network access. run_analysis.py subsequently works offline.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parent / 'data' / 'raw'
SERVICES = {
    'roads': 'https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/MassDOTRoads_gdb/FeatureServer/0',
    'towns': 'https://services1.arcgis.com/hGdibHYSPO59RG1h/ArcGIS/rest/services/Massachusetts_Municipalities_Hosted/FeatureServer/0',
    'watershed': 'https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/Surface_Water_Supply_Watersheds/FeatureServer/0',
    **{'zone_'+z:'https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/ZoneABC/FeatureServer/'+str(i) for i,z in enumerate('ABC')},
}

def request(url, params, post=True):
    encoded=urllib.parse.urlencode(params).encode()
    req=urllib.request.Request(url if post else url+'?'+encoded.decode(),data=encoded if post else None,headers={'User-Agent':'SaltShield-pilot/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=90) as r:
                d=json.load(r)
            if 'error' in d:raise RuntimeError(d['error'])
            return d
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)

def save(name,d):
    (RAW/name).write_text(json.dumps(d,ensure_ascii=False))

def query(service,**params):
    return request(service+'/query',{'f':'geojson','outFields':'*','outSR':4326,'returnGeometry':'true',**params})

def flat(coords):
    if isinstance(coords[0],(int,float)):yield coords
    else:
        for c in coords:yield from flat(c)

def main():
    RAW.mkdir(parents=True,exist_ok=True)
    log=[]
    for k,u in SERVICES.items():save(k+'_metadata.json',request(u,{'f':'json'},False))
    towns=query(SERVICES['towns'],where="TOWN IN ('HOLDEN','STERLING','WEST BOYLSTON')")
    assert len(towns['features'])==3
    save('towns.geojson',towns)
    points=[p for f in towns['features'] for p in flat(f['geometry']['coordinates'])]
    bbox=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
    ids=request(SERVICES['roads']+'/query',{'f':'json','where':'1=1','geometry':','.join(map(str,bbox)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'})['objectIds']
    ids.sort();save('road_ids.json',ids)
    features=[]
    for i in range(0,len(ids),500):
        d=query(SERVICES['roads'],objectIds=','.join(map(str,ids[i:i+500])))
        assert not d.get('exceededTransferLimit')
        features.extend(d['features'])
        print('Roads',len(features),'/',len(ids))
    assert len(features)==len(ids)==len({f['properties']['OBJECTID'] for f in features})
    save('roads.geojson',{'type':'FeatureCollection','features':features})
    water=query(SERVICES['watershed'],where="SOURCE_ID = '6000000-01S' AND SITE_NAME = 'WACHUSETT RESERVOIR'")
    assert len(water['features'])==1
    save('watershed.geojson',water)
    zones=[]
    for z in 'ABC':
        d=query(SERVICES['zone_'+z],where="SOURCE_ID = '6000000-01S'")
        assert not d.get('exceededTransferLimit') and d['features']
        save('zone_'+z+'.geojson',d);zones.extend(d['features'])
    save('protection_zones.geojson',{'type':'FeatureCollection','features':zones})
    for k,u in SERVICES.items():log.append({'dataset':k,'service':u,'retrieved_at':datetime.now(timezone.utc).isoformat(),'scope':'three-town bounding box for roads; SOURCE_ID 6000000-01S for water layers; three named towns'})
    save('sources_download_log.json',log)

if __name__=='__main__':main()
