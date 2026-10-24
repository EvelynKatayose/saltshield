/* Precomputed spatial cases; deliberately independent of equipment controls. */
(() => {
  const data=ANALYSIS.phase3.spatial;
  const labels={uniform:'均匀覆盖',greedy:'比例贪心',integer:'整片区最优',fractional_bound:'理论上界'};
  const methods=Object.keys(labels), get=id=>document.getElementById(id), km=v=>v.toFixed(2);
  let active=[];
  function updateSpatial() {
    const fraction=Number(get('spatial-fraction').value), method=get('spatial-method').value;
    active=data.cases.filter(c=>c.coverage_fraction===fraction);
    if(active.length!==Object.keys(data.town_totals).length||!methods.includes(method))throw Error('Unknown spatial case');
    const total=key=>active.reduce((s,c)=>s+c.plans[method][key],0);
    const uniform=active.reduce((s,c)=>s+c.plans.uniform.covered_zone_a_km,0);
    get('spatial-summary').textContent=labels[method]+'：道路容量上限 '+km(total('capacity_km'))+' km，实际覆盖 '+km(total('covered_road_km'))+' km，未用容量 '+km(total('unspent_capacity_km'))+' km。覆盖 Zone A '+km(total('covered_zone_a_km'))+' km；均匀基线 '+km(uniform)+' km。';
    get('spatial-table').innerHTML=active.map(c=>'<tr class="town-row"><th colspan="3">'+c.town+' · 上限 '+km(c.plans[method].capacity_km)+' km</th></tr>'+methods.map(m=>'<tr'+(m===method?' class="selected"':'')+'><td>'+labels[m]+'</td><td>'+km(c.plans[m].covered_road_km)+'</td><td>'+km(c.plans[m].covered_zone_a_km)+'</td></tr>').join('')).join('');
    const shares=Object.assign({},...active.map(c=>c.plans[method].cell_shares));
    for(const cell of document.querySelectorAll('.priority-cell')) {
      const s=shares[cell.dataset.cell]||0;
      cell.style.fill=s>0?'#176d63':'#e1e6e2'; cell.style.fillOpacity=s>0?String(.18+.82*s):'1';
    }
  }
  get('spatial-fraction').addEventListener('change',updateSpatial);
  get('spatial-method').addEventListener('change',updateSpatial);
  get('spatial-export').addEventListener('click',()=>{
    const method=get('spatial-method').value, fraction=Number(get('spatial-fraction').value);
    const cells=new Map(data.cells.map(c=>[c.cell_id,c]));
    const rows=[['town','coverage_fraction','method','capacity_km','cell_id','covered_share','covered_road_km','covered_zone_a_km','road_source_sha256']];
    for(const c of active) for(const [id,share] of Object.entries(c.plans[method].cell_shares)) {
      const cell=cells.get(id);
      rows.push([c.town,fraction,method,c.plans[method].capacity_km,id,share,cell.eligible_km*share,cell.zone_a_km*share,data.source_sha256['road_segments.geojson']]);
    }
    const text='\uFEFF'+rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\n')+'\n';
    const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='saltshield-spatial-'+method+'-'+fraction+'.csv';link.click();URL.revokeObjectURL(url);
  });
  updateSpatial();
})();
