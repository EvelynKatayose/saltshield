"""Create offline map, figure, and interactive results report from analysis outputs."""
import base64
import csv
import html
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import PathPatch, Patch
from matplotlib.path import Path as MPath
from pyproj import Transformer
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.ops import transform

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
DATA=ROOT/'data'/'processed'
T=Transformer.from_crs(4326,26986,always_xy=True).transform
COL={'A':'#cce5de','B':'#e9e0bd','C':'#e8edf0','UNZONED':'#f9e3e1','2':'#176d63','1':'#c67a32','0':'#98a2ab','UNKNOWN':'#826796'}

def geo(name):
    return json.loads((DATA/name).read_text())['features']

def components(g,kind):
    if g.geom_type==kind:yield g
    elif hasattr(g,'geoms'):
        for q in g.geoms:yield from components(q,kind)

def polygon_path(g):
    vertices=[];codes=[]
    for poly in components(g,'Polygon'):
        p=orient(poly,1)
        for ring in [p.exterior,*p.interiors]:
            cs=list(ring.coords)
            vertices+=cs
            codes += [MPath.MOVETO]+[MPath.LINETO]*(len(cs)-2)+[MPath.CLOSEPOLY]
    return MPath(vertices,codes)

def figures(a):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#33434b','text.color':'#21343d','savefig.facecolor':'white'})
    roads=geo('road_segments.geojson');towns=geo('study_towns.geojson');water=geo('watershed.geojson');zones=geo('protection_zones.geojson')
    fig=plt.figure(figsize=(14,9.5),layout='constrained')
    grid=fig.add_gridspec(2,2,width_ratios=[1.6,1],height_ratios=[1,1])
    ax=fig.add_subplot(grid[:,0])
    for f in water:
        g=transform(T,shape(f['geometry']));ax.add_patch(PathPatch(polygon_path(g),facecolor='#f5f6f3',edgecolor='#425e68',lw=1.2))
    for f in zones:
        g=transform(T,shape(f['geometry']));ax.add_patch(PathPatch(polygon_path(g),facecolor=COL[f['properties']['zone']],edgecolor='none',alpha=.85))
    for code in ['0','UNKNOWN','1','2']:
        lines=[]
        for f in roads:
            if f['properties']['jurisdiction_code']!=code:continue
            g=transform(T,shape(f['geometry']))
            lines += [list(p.coords) for p in components(g,'LineString')]
        ax.add_collection(LineCollection(lines,colors=COL[code],linewidths=.75 if code in ['1','2'] else .45,alpha=.9))
    for f in towns:
        g=transform(T,shape(f['geometry']));ax.add_patch(PathPatch(polygon_path(g),facecolor='none',edgecolor='#263e48',lw=1.3))
        p=g.representative_point();ax.annotate(f['properties']['town'].title(),(p.x,p.y),xytext=(0,6),textcoords='offset points',ha='center',fontsize=11,fontweight='bold',bbox={'fc':'white','ec':'none','alpha':.85,'pad':3})
    wg=transform(T,shape(water[0]['geometry']));x0,y0,x1,y1=wg.bounds
    ax.set_xlim(x0-800,x1+800);ax.set_ylim(y0-900,y1+900);ax.set_aspect('equal');ax.axis('off')
    ax.set_title('Wachusett Reservoir water-supply watershed\nOfficial GIS, three-town road inventory',loc='left',fontsize=15,pad=18)
    sx=x0+1000;sy=y1-800;ax.plot([sx,sx+5000],[sy,sy],color='#21343d',lw=3);ax.text(sx+2500,sy+350,'5 km',ha='center',fontsize=9)
    ax.annotate('N',xy=(x1-500,y1-500),xytext=(x1-500,y1-2400),arrowprops={'arrowstyle':'-|>','color':'#21343d'},ha='center',fontsize=10)
    ax.legend(handles=[Patch(fc=COL[z],label='Protection zone '+z) for z in 'ABC']+[plt.Line2D([0],[0],color=COL['2'],lw=2,label='Municipal accepted'),plt.Line2D([0],[0],color=COL['1'],lw=2,label='MassDOT'),plt.Line2D([0],[0],color=COL['0'],lw=2,label='Unaccepted / unknown')],loc='upper left',bbox_to_anchor=(0,-.015),frameon=False,ncol=3,fontsize=8)
    names=[s['town'].title() for s in a['summary']]
    ax1=fig.add_subplot(grid[0,1]);left=[0.,0.,0.]
    for code,label in [('2','Municipal'),('1','MassDOT'),('0','Unaccepted'),('UNKNOWN','Unknown')]:
        vals=[sum(r['protected_centerline_km'] for r in a['owners'] if r['town']==t['town'] and r['jurisdiction_code']==code) for t in a['summary']]
        ax1.barh(names,vals,left=left,color=COL[code],label=label,height=.54)
        left=[x+y for x,y in zip(left,vals)]
    for i,v in enumerate(left):ax1.text(v+2,i,f'{v:.2f}',va='center',fontsize=10)
    ax1.set_xlim(0,max(left)*1.21);ax1.invert_yaxis();ax1.set_xlabel('Mapped centerline km within zones A / B / C');ax1.set_title('Protected roads by source jurisdiction',loc='left',pad=15);ax1.grid(axis='x',alpha=.15);ax1.set_axisbelow(True);ax1.legend(loc='lower right',frameon=False,fontsize=8)
    ax2=fig.add_subplot(grid[1,1]);labels=['Holden','Sterling','West Boylston'];aa=[s['eligible_municipal_paved_zone_a_km'] for s in a['summary']]
    ax2.barh(labels,aa,color='#176d63',height=.52)
    for i,v in enumerate(aa):ax2.text(v+.35,i,f'{v:.2f} km',va='center')
    ax2.set_xlim(0,max(aa)*1.3);ax2.invert_yaxis();ax2.set_xlabel('Municipal paved centerline km in zone A');ax2.set_title('Measured road coverage used in the scenario',loc='left',pad=15);ax2.grid(axis='x',alpha=.15);ax2.set_axisbelow(True)
    fig.suptitle('SaltShield  |  Geography is measured. Investment benefits are simulated.',x=.025,ha='left',fontsize=16,fontweight='bold')
    fig.supxlabel('Sources: MassGIS / MassDOT / MassDEP. EPSG:26986 lengths. Jurisdiction is not a verified winter-maintenance contract.\nUnmatched zone sections stay separate. Source-record overlap: 78.8 m; source records are retained.',fontsize=8.5)
    fig.savefig(OUT/'wachusett_map.png',dpi=170);plt.close(fig)
    # Budget outcomes and spending are placed together to expose the source of uplift.
    fig,(ax,bx)=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    comp=a['comparison'];plans=[comp['independent'],comp['pooled'],comp['pooled_at_independent_actual_spend']]
    labs=['Independent\n$75k ceiling','Pooled\n$75k ceiling','Pooled\n$45k ceiling']
    values=[p['avoided_zone_a_tonnes_simulated'] for p in plans]
    ax.bar(labs,values,color=['#9aa5aa','#176d63','#8eb7ab'],width=.55)
    for i,v in enumerate(values):ax.text(i,v+1.4,f'{v:.2f} t',ha='center')
    ax.set_ylim(0,max(values)*1.22);ax.set_ylabel('Simulated avoided application in zone A (t / season)');ax.set_title('Same inputs, different funding constraints',loc='left');ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    spent=[p['spent_usd']/1000 for p in plans];unspent=[p['unspent_usd']/1000 for p in plans]
    bx.bar(labs,spent,color='#176d63',width=.55,label='Spent');bx.bar(labs,unspent,bottom=spent,color='#dce4df',width=.55,label='Unused ceiling')
    for i,v in enumerate(spent):bx.text(i,v/2,f'${v:,.0f}k',ha='center',va='center',color='white')
    bx.set_ylabel('One-time simulated capital ($ thousands)');bx.set_title('Equal ceilings do not mean equal spending',loc='left');bx.legend(frameon=False);bx.grid(axis='y',alpha=.16);bx.set_axisbelow(True)
    fig.suptitle('SIMULATION  |  Costs, full coverage, 5 t/km baseline and reduction rates are assumptions.',fontsize=12,fontweight='bold')
    fig.supxlabel('The equal-spend pooled case leaves one town unfunded. No concentration or verified road-safety outcomes are predicted.',fontsize=9)
    fig.savefig(OUT/'budget_comparison.png',dpi=160);plt.close(fig)


def svg_map():
    roads=geo('road_segments.geojson');towns=geo('study_towns.geojson');water=geo('watershed.geojson');zones=geo('protection_zones.geojson')
    w=transform(T,shape(water[0]['geometry']));x0,y0,x1,y1=w.bounds
    scale=min(940/(x1-x0),750/(y1-y0));padx=(1000-(x1-x0)*scale)/2;pady=30
    def xy(pt):return ((pt[0]-x0)*scale+padx,(y1-pt[1])*scale+pady)
    def line(coords,close=False):
        pts=[xy(p) for p in coords]
        return 'M'+'L'.join(f'{x:.2f},{y:.2f}' for x,y in pts)+('Z' if close else '')
    def path_geom(g):
        d=''
        for p in components(g,'Polygon'):
            d+=line(p.exterior.coords,True)
            for ring in p.interiors:d+=line(ring.coords,True)
        for p in components(g,'LineString'):d+=line(p.coords)
        return d
    parts=['<svg viewBox="0 0 1000 830" role="img" aria-label="Official Wachusett watershed, protection zones, three towns and clipped roads"><title>Wachusett official GIS road inventory</title>']
    parts.append(f'<path d="{path_geom(w.simplify(4))}" fill="#f4f6f3" stroke="#4d686e" stroke-width="1.4"/>')
    for f in zones:
        z=f['properties']['zone'];g=transform(T,shape(f['geometry'])).simplify(3)
        parts.append(f'<path d="{path_geom(g)}" fill="{COL[z]}" fill-rule="evenodd" opacity=".85"><title>Protection zone {z}</title></path>')
    for code in ['0','UNKNOWN','1','2']:
        parts.append(f'<g class="road-layer" data-code="{code}" fill="none" stroke="{COL[code]}" stroke-width="1.1" stroke-linecap="round">')
        for f in roads:
            p=f['properties']
            if p['jurisdiction_code']!=code:continue
            g=transform(T,shape(f['geometry'])).simplify(1)
            title=html.escape(f"{p['town'].title()} | {p['street_name'] or 'Unnamed'} | {p['jurisdiction_label']} | zone {p['zone']} | {p['centerline_km']:.3f} km")
            parts.append(f'<path d="{path_geom(g)}"><title>{title}</title></path>')
        parts.append('</g>')
    for f in towns:
        g=transform(T,shape(f['geometry']));parts.append(f'<path d="{path_geom(g.simplify(3))}" fill="none" stroke="#243c45" stroke-width="1.5"/>')
        pt=g.representative_point();x,y=xy((pt.x,pt.y));label=html.escape(f['properties']['town'].title())
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="21" font-family="system-ui" fill="#172e35" paint-order="stroke" stroke="#fff" stroke-width="5" stroke-linejoin="round">{label}</text>')
    xx,yy=xy((x0+1000,y0+700));parts.append(f'<path d="M{xx:.1f},{yy:.1f}h{5000*scale:.1f}" stroke="#21343d" stroke-width="4"/><text x="{xx:.1f}" y="{yy-10:.1f}" font-family="system-ui" font-size="15">5 km</text>')
    parts.append('</svg>');return ''.join(parts)


def report(a):
    def num(v):return f'{v:,.2f}'
    measured=''.join(f"<tr><th>{s['town'].title()}</th><td>{num(s['within_watershed_centerline_km'])}</td><td>{num(s['protected_centerline_km'])}</td><td>{num(s['zone_a_centerline_km'])}</td><td>{num(s['eligible_municipal_paved_zone_a_km'])}</td></tr>" for s in a['summary'])
    ownership=''.join(f"<tr><td>{r['town'].title()}</td><td>{html.escape(r['jurisdiction_label'])}</td><td>{num(r['protected_centerline_km'])}</td></tr>" for r in a['owners'])
    sources=''.join(f'<li><a href="{u}" target="_blank" rel="noreferrer">{k.replace("_"," ").title()}</a></li>' for k,u in a['official_sources'].items())
    template=(ROOT/'report_template.html').read_text()
    from planning_v1 import parameter_hashes
    planning=json.loads((OUT/'planning_v1.json').read_text())
    if planning['base_analysis_sha256']!=hashlib.sha256((OUT/'analysis.json').read_bytes()).hexdigest() or planning['parameter_sha256']!=parameter_hashes():
        raise ValueError('Planning inputs changed. Run planning_v1.py before building the report.')
    a={**a,'planning':planning}
    operations_rows=''.join('<tr><th>'+html.escape(r['town_id'].title())+'</th><td>'+html.escape(r['baseline_t_per_centerline_km_per_winter'])+'</td><td>'+html.escape(r['data_status'])+'</td><td>'+html.escape(r['source'])+'</td></tr>' for r in planning['operations'])
    parameter_project_rows=''.join('<tr><th>'+html.escape(p['town'].title()+' / '+p['project_type'])+'</th><td>'+format(p['capital_cost_usd'],',.0f')+'</td><td>'+str(round(p['reduction_low']*100))+'% / '+str(round(p['reduction_fraction']*100))+'% / '+str(round(p['reduction_high']*100))+'%</td><td>'+html.escape(p['input_source'])+'</td></tr>' for p in planning['projects'])
    template=template.replace('__PARAMETER_PANEL__',(ROOT/'parameter_panel.html').read_text().replace('__OPERATIONS_ROWS__',operations_rows).replace('__PARAMETER_PROJECT_ROWS__',parameter_project_rows).replace('__PARAMETER_FINGERPRINT__',planning['parameter_fingerprint'][:16]))
    phase2_path=OUT/'phase2_analysis.json'
    if phase2_path.exists():
        a={**a,'phase2':json.loads(phase2_path.read_text())}
        phase2=a['phase2']
        if phase2['base_analysis_sha256'] != hashlib.sha256((OUT/'analysis.json').read_bytes()).hexdigest():
            raise ValueError('Phase 2 inputs are stale. Run phase2_model.py after run_analysis.py.')
        evidence=phase2['evidence']
        summary_rows=''.join(f"<tr><th>{s['town'].title()}</th><td>{s['award_count']}</td><td>${s['historical_grant_total_usd']:,}</td><td>FY{s['latest_award_fiscal_year']}</td></tr>" for s in evidence['town_summary'])
        categories={'spreader_controls':'Spreader controls','brine_production':'Brine production','brine_application':'Brine application','plow_blades':'Plow blades','storage_or_facility':'Storage / facilities','temperature_sensors':'Temperature sensors'}
        award_rows=''.join('<tr><td>FY'+str(r['fiscal_year'])+' / '+r['town'].title()+'</td><td>'+html.escape(' / '.join(categories[x] for x in r['equipment_categories']))+'</td><td>$'+format(r['grant_award_usd'],',')+'</td><td>'+('$'+format(r['reported_historical_project_total_usd'],',') if r['reported_historical_project_total_usd'] is not None else 'Not reported')+'</td><td><a href="'+html.escape(r['source_url'],quote=True)+'" target="_blank" rel="noreferrer">DCR</a></td></tr>' for r in evidence['records'])
        editor_rows=''.join('<tr data-project="'+p['project_id']+'"><th>'+p['town'].title()+' / '+p['project_type']+'</th><td><input type="checkbox" '+('checked ' if p['enabled'] else '')+'data-field="enabled" aria-label="Include '+p['town'].title()+' '+p['project_type']+'"></td><td><input type="number" min="0" step="1000" value="'+str(p['capital_cost_usd'])+'" data-field="cost" aria-label="'+p['town'].title()+' '+p['project_type']+' assumed cost"></td><td><input type="number" min="0" max="100" step="10" value="'+str(p['coverage_fraction_assumed']*100)+'" data-field="coverage" aria-label="'+p['town'].title()+' '+p['project_type']+' assumed coverage"></td><td>'+str(round(p['reduction_low']*100))+'% / '+str(round(p['reduction_fraction']*100))+'% / '+str(round(p['reduction_high']*100))+'%</td></tr>' for p in planning['projects'])
        planner=(ROOT/'phase2_panel.html').read_text().replace('__PROJECT_EDITOR_ROWS__',editor_rows).replace('value="75000"','value="'+str(planning['config']['total_budget_usd'])+'"').replace('value="5"','value="'+str(planning['baseline_reference_mean'])+'"')
        for value in [planning['config']['objective'],planning['config']['effect']]:planner=planner.replace('value="'+value+'">','value="'+value+'" selected>')
        template=template.replace('__PLANNER_PANEL__',planner)
        template=template.replace('__EVIDENCE_PANEL__',(ROOT/'evidence_panel.html').read_text().replace('__AWARD_SUMMARY_ROWS__',summary_rows).replace('__AWARD_RECORD_ROWS__',award_rows))
    else:
        raise ValueError('Build evidence and phase2_model.py before creating the workspace.')
    phase3_files=[OUT/'spatial_priority.json',OUT/'weather_context.json']
    if any(p.exists() for p in phase3_files):
        if not all(p.exists() for p in phase3_files):
            raise ValueError('Run both build_weather.py and spatial_priority.py before building phase 3.')
        from phase3_report import load_results, panel, priority_svg
        a={**a,'phase3':load_results()}
        panels=panel(a['phase3'])
        from joint_planning import source_hashes
        joint=json.loads((OUT/'joint_planning.json').read_text())
        if joint['source_sha256']!=source_hashes():
            raise ValueError('Linked planning inputs changed. Run joint_planning.py before building the report.')
        a={**a,'joint':joint}
        capacity_rows=''.join('<tr><th>'+html.escape(r['town_id'].title()+' / '+r['project_id'].rsplit('_',1)[1])+'</th><td><input id="joint-reach-'+r['project_id']+'" type="number" min="0" step="1" value="'+str(r['max_road_km_per_winter'])+'" aria-label="'+html.escape(r['project_id']+' simulated service reach')+'"></td></tr>' for r in joint['capacities'])
        linked_panel=(ROOT/'joint_panel.html').read_text().replace('__CAPACITY_ROWS__',capacity_rows).replace('__JOINT_MAP__',priority_svg().replace('class="priority-cell"','class="joint-cell"'))
        template=template.replace('__WEATHER_PANEL__',panels['weather']).replace('__SPATIAL_PANEL__',linked_panel+panels['spatial'])
    else:
        raise ValueError('Build weather and spatial outputs before creating the workspace.')
    maximum=max(s['within_watershed_centerline_km'] for s in a['summary'])
    town_cards=''.join(f'<div class="town-detail"><div class="town-name"><span>{s["town"].title()}</span><span>{num(s["within_watershed_centerline_km"])} <em>km</em></span></div><div class="town-strip"><span style="width:{s["within_watershed_centerline_km"]/maximum*100:.2f}%"></span></div><small>{num(s["eligible_municipal_paved_zone_a_km"])} km of eligible Zone A roads</small></div>' for s in a['summary'])
    replacements={'__MAP__':svg_map(),'__MEASURED_ROWS__':measured,'__OWNER_ROWS__':ownership,'__SOURCES__':sources,'__ANALYSIS_JSON__':json.dumps(a,ensure_ascii=False).replace('</','<\\/'),'__SOLVER_JS__':(ROOT/'simulation.js').read_text()+'\n'+(ROOT/'planning_v1.js').read_text()+'\n'+(ROOT/'joint_planning.js').read_text()+'\n'+(ROOT/'joint_brief.js').read_text(),
                  '__WORKSPACE_CSS__':(ROOT/'workspace.css').read_text(),'__PLANNER_JS__':(ROOT/'phase2_ui.js').read_text()+'\n'+(ROOT/'planning_ui.js').read_text(),'__SPATIAL_JS__':(ROOT/'phase3_ui.js').read_text()+'\n'+(ROOT/'joint_ui.js').read_text(),'__WORKSPACE_JS__':(ROOT/'workspace.js').read_text(),
                  '__TOWN_CARDS__':town_cards,'__TOTAL_ROADS__':num(sum(s['within_watershed_centerline_km'] for s in a['summary'])),'__ELIGIBLE_A__':num(sum(s['eligible_municipal_paved_zone_a_km'] for s in a['summary']))}
    for key,value in replacements.items():template=template.replace(key,value)
    (OUT/'SaltShield_Wachusett.html').write_text(template)
    print('Report created:',OUT/'SaltShield_Wachusett.html')

if __name__=='__main__':
    a=json.loads((OUT/'analysis.json').read_text())
    figures(a)
    report(a)
