"""Offline report fragments for regional weather and spatial allocation."""
import hashlib
import html
import json

from shapely.geometry import shape
from shapely.ops import transform

from spatial_priority import DATA, FORWARD, ROOT, OUT, fingerprint


def load_results():
    spatial=json.loads((OUT/'spatial_priority.json').read_text())
    weather=json.loads((OUT/'weather_context.json').read_text())
    if spatial['source_sha256'] != fingerprint():
        raise ValueError('Spatial output is stale. Run spatial_priority.py.')
    if spatial['planning_cells_sha256'] != hashlib.sha256((DATA/'planning_cells.geojson').read_bytes()).hexdigest():
        raise ValueError('Planning-cell geometry does not match spatial results. Run spatial_priority.py.')
    manifest=ROOT/'data/weather/source_manifest.json'
    if weather['manifest_sha256'] != hashlib.sha256(manifest.read_bytes()).hexdigest():
        raise ValueError('Weather output is stale. Run build_weather.py.')
    for item in json.loads(manifest.read_text())['responses']:
        if hashlib.sha256((manifest.parent/item['file']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Weather snapshot checksum mismatch')
    return {'spatial':spatial,'weather':weather}


def priority_svg():
    water=json.loads((DATA/'watershed.geojson').read_text())['features'][0]
    w=transform(FORWARD,shape(water['geometry']));x0,y0,x1,y1=w.bounds
    scale=min(900/(x1-x0),680/(y1-y0)); ox=(960-(x1-x0)*scale)/2
    def line(coords):
        return 'M'+'L'.join(f'{(x-x0)*scale+ox:.2f},{(y1-y)*scale+25:.2f}' for x,y,*_ in coords)
    def paths(g):
        if g.geom_type=='Polygon':
            return line(g.exterior.coords)+'Z'+''.join(line(r.coords)+'Z' for r in g.interiors)
        if g.geom_type=='LineString':return line(g.coords)
        return ''.join(paths(p) for p in getattr(g,'geoms',[]))
    parts=['<svg viewBox="0 0 960 730" role="img" aria-label="One-kilometer planning cell coverage comparison"><title>Wachusett: illustrative planning cell allocation</title>',
           f'<path d="{paths(w.simplify(4))}" fill="#f7f8f5" fill-rule="evenodd" stroke="#6c8387"/>']
    for f in json.loads((DATA/'planning_cells.geojson').read_text())['features']:
        p=f['properties']; g=transform(FORWARD,shape(f['geometry'])).simplify(3)
        title=html.escape(f"{p['town'].title()} | {p['cell_id']} | roads {p['eligible_km']:.2f} km | Zone A {p['zone_a_km']:.2f} km")
        parts.append(f'<path class="priority-cell" data-cell="{p["cell_id"]}" d="{paths(g)}" fill="#e1e6e2" fill-rule="evenodd" stroke="#fff" stroke-width=".7"><title>{title}</title></path>')
    for f in json.loads((DATA/'road_segments.geojson').read_text())['features']:
        p=f['properties']
        if not p['eligible_simulated_municipal_project'] or p['zone']!='A':continue
        g=transform(FORWARD,shape(f['geometry'])).simplify(2)
        parts.append(f'<path d="{paths(g)}" fill="none" stroke="#203c40" stroke-width="1.8" pointer-events="none"/>')
    for f in json.loads((DATA/'study_towns.geojson').read_text())['features']:
        g=transform(FORWARD,shape(f['geometry']));pt=g.representative_point()
        parts.append(f'<path d="{paths(g.simplify(3))}" fill="none" stroke="#68817d" stroke-width="1"/>')
        parts.append(f'<text x="{(pt.x-x0)*scale+ox:.1f}" y="{(y1-pt.y)*scale+25:.1f}" text-anchor="middle" font-size="19" fill="#203c40" paint-order="stroke" stroke="white" stroke-width="5">{html.escape(f["properties"]["town"].title())}</text>')
    xx=ox+25;yy=700
    parts.append(f'<path d="M{xx},{yy}h{5000*scale:.1f}" stroke="#203c40" stroke-width="3"/><text x="{xx}" y="{yy-8}" font-size="15">5 km</text></svg>')
    return ''.join(parts)


def panel(data):
    weather=data['weather']; spatial=data['spatial']; ref=weather['reference']
    def val(v):return 'Missing' if v is None else f'{v:,.1f}'
    rows=''.join(f'<tr><th>{s["season"]}</th><td>{s["hours"]:,}</td><td>{val(s["min_air_temperature_c"])}</td><td>{val(s["precipitation_total_mm"])}</td><td>{val(s["snowfall_total_cm"])}</td><td>{s["cold_wet_hours"]}</td></tr>' for s in weather['summaries'])
    replacements={'__WEATHER_HOURS__':f'{weather["total_hours"]:,}', '__MISSING__':str(sum(sum(s['missing_values'].values()) for s in weather['summaries'])),
                  '__GRID_LAT__':str(ref['grid_latitude']), '__GRID_LON__':str(abs(ref['grid_longitude'])), '__WEATHER_SUMMARY_ROWS__':rows,
                  '__PRIORITY_MAP__':priority_svg(), '__CELL_COUNT__':str(spatial['cell_count'])}
    panels={}
    for name in ['weather','spatial']:
        content=(ROOT/(name+'_panel.html')).read_text()
        for key,value in replacements.items():content=content.replace(key,value)
        panels[name]=content
    return panels
