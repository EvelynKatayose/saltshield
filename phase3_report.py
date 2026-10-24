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
    parts=['<svg viewBox="0 0 960 730" role="img" aria-label="一公里规划片区覆盖比较"><title>Wachusett: illustrative planning cell allocation</title>',
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
    weather=data['weather'];spatial=data['spatial']; ref=weather['reference']
    def val(v,digits=1):return '缺值' if v is None else f'{v:,.{digits}f}'
    rows=''.join(f'<tr><th>{s["season"]}</th><td>{s["hours"]:,}</td><td>{val(s["min_air_temperature_c"])}</td><td>{val(s["precipitation_total_mm"])}</td><td>{val(s["snowfall_total_cm"])}</td><td>{s["cold_wet_hours"]}</td></tr>' for s in weather['summaries'])
    missing=sum(sum(s['missing_values'].values()) for s in weather['summaries'])
    return f'''<section class="panel" id="weather-panel"><h2>第三阶段 · 五个冬季的区域天气背景</h2>
<p><span class="status">历史再分析</span>每季为纽约时区 11 月 1 日至次年 3 月 31 日，共 {weather['total_hours']:,} 小时；变量缺值 {missing} 个。ERA5 约 0.25° 网格，实际参考点 {ref['grid_latitude']}°N / {abs(ref['grid_longitude'])}°W。</p>
<div class="scroll"><table><thead><tr><th>冬季</th><th>小时数</th><th>最低气温 °C</th><th>降水 mm</th><th>降雪 cm</th><th>低温伴降水小时</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="small">降水含雨雪水当量；降雪为模型给出的积算降雪深度，不能与水当量相加。“低温伴降水”仅统计 2 米气温 ≤ 2°C 且前一小时降水 ≥ 0.1 mm 的时段。这是描述性阈值，不能诊断道路结冰。此表没有参与设备收益或用盐强度计算。</p>
<p class="small">来源：ERA5 / Copernicus Climate Change Service，经 <a href="https://open-meteo.com/en/docs/historical-weather-api" target="_blank" rel="noreferrer">Open-Meteo Historical Weather API</a>；Open-Meteo 数据 CC BY 4.0。单一粗网格只提供区域背景，没有逐路段路温或现场传感器观测。</p></section>
<section class="panel" id="spatial-panel"><h2>有限覆盖能力，应优先选择哪些道路片区？</h2>
<p><span class="status">规划容量为模拟</span>把三镇可纳入的市镇铺装道路分入 {spatial['cell_count']} 个 1 km 网格片区。每镇独立设置相同覆盖比例，以 Zone A 覆盖公里数为目标；计算单独进行，不改变上方预算比较。</p>
<div class="controls"><label>每镇可覆盖的道路公里上限<select id="spatial-fraction"><option value="0.25">各镇道路总长的 25%</option><option value="0.5">50%</option><option value="0.75">75%</option><option value="1">100%</option></select></label>
<label>地图显示<select id="spatial-method"><option value="integer">整片区最优方案</option><option value="greedy">按 Zone A 比例贪心选择</option><option value="uniform">均匀覆盖基线</option><option value="fractional_bound">允许切分的理论上界</option></select></label><button type="button" id="spatial-export">下载当前片区清单 CSV</button></div>
<p id="spatial-summary" class="detail" aria-live="polite"></p><div class="two"><div class="map-panel">{priority_svg()}<p class="small">浅灰：未选片区；绿色：覆盖片区（允许切分的情景用深浅表示比例）；深色线：全部可纳入的 Zone A 道路。片区悬停可查看公里数。网格从 EPSG:26986 的整公里坐标起算，并裁剪至城镇与汇水区交集。</p></div>
<div><h3>相同公里上限的结果对照</h3><div class="scroll"><table><thead><tr><th>城镇 / 方式</th><th>覆盖道路 km</th><th>覆盖 Zone A km</th></tr></thead><tbody id="spatial-table"></tbody></table></div><p class="small note">整片区最优使用整数规划，必须选取整个片区内的可纳入道路；贪心方式按 Zone A 占比排序。均匀基线是假设每段道路均匀覆盖相同比例，理论上界允许部分片区覆盖；后二者不代表可直接执行的整片区方案。未用满的容量单列保留。</p></div></div>
<p class="small note">覆盖上限是示例，未由设备或车队实测。1 km 片区不是已核验养护路线；模型未计行驶衔接、天气同步、工时、仓储和道路安全服务约束。保留基础道路记录的约 78.8 m 来源重叠，切网格本身不增加长度。Zone A 道路覆盖量是空间筛查指标，不能直接换算成水体浓度改善或实测减盐量。</p></section>'''


STYLE='\n#spatial-panel .map-panel svg{max-height:650px}#spatial-table .town-row th{background:#f1f5f0;text-align:left}#spatial-table tr.selected{background:#e8f3ed}.priority-cell:hover{stroke:#172e35;stroke-width:2}\n'
