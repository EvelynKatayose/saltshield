"""Create offline map, figure, and interactive results report from analysis outputs."""
import base64
import csv
import html
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
    replacements={'__MAP__':svg_map(),'__MEASURED_ROWS__':measured,'__OWNER_ROWS__':ownership,'__SOURCES__':sources,'__ANALYSIS_JSON__':json.dumps(a,ensure_ascii=False).replace('</','<\\/'),'__SOLVER_JS__':(ROOT/'simulation.js').read_text()}
    for key,value in replacements.items():template=template.replace(key,value)
    (OUT/'SaltShield_Wachusett.html').write_text(template)
    print('Report created:',OUT/'SaltShield_Wachusett.html')

if __name__=='__main__':
    a=json.loads((OUT/'analysis.json').read_text())
    figures(a)
    report(a)
