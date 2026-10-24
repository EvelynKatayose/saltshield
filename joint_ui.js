/* Separate capacity-linked scenario, sharing only the explicit investment inputs. */
(() => {
  const data=ANALYSIS.joint,$=id=>document.getElementById(id),labels={statusQuo:'No new investment',independent:'Independent budgets',greedy:'Benefit / cost heuristic',pooled:'Shared budget',participation:'Shared · every town',equalSpend:'Shared · equal actual spending',equalSpendParticipation:'Equal spending · every town'};
  const reachInput=p=>$('joint-reach-'+p.project_id),defaults=Object.fromEntries(data.capacities.map(r=>[r.project_id,r.max_road_km_per_winter])),key='saltshield-joint-reach';
  let currentJoint=null,reference=null;
  const km=v=>v.toFixed(2)+' km';
  function readReach(){return Object.fromEntries(originalProjects.map(p=>[p.project_id,numericInput(reachInput(p),niceTown(p.town)+' service reach')]));}
  function saveReach(capacities){try{localStorage.setItem(key,JSON.stringify({source_sha256:data.source_sha256,capacities}));$('joint-draft-status').textContent='Reach saved on this device.';}catch{$('joint-draft-status').textContent='Reach is available for this session. Export to keep a copy.';}}
  function clearMap(){for(const cell of document.querySelectorAll('.joint-cell'))cell.style.fill='#e1e6e2';}
  function updateJoint(){
    try{
      if(!currentInputs||!currentAssessment)throw Error('Enter valid investment inputs to calculate a linked plan.');
      const capacities=readReach(),i=currentInputs;
      currentJoint=SaltShieldJoint.solve(i.projects,data.cells,capacities,i.budget,towns,i.effect,i.baselineRates,i.objective,i.localCaps);
      const savedBenchmark=data.benchmarks[i.objective],inputsMatch=SaltShieldJoint.matches(savedBenchmark.input_snapshot,currentJoint.input_snapshot);
      reference=inputsMatch&&savedBenchmark.exact_plans?savedBenchmark:null;
      const policy=$('joint-policy').value,result=currentJoint.plans[policy];
      if(!(policy in labels))throw Error('Unknown funding rule.');
      $('joint-error').hidden=true;$('joint-output').hidden=false;
      $('joint-json').disabled=false;$('joint-csv').disabled=result===null;
      $('joint-benefit-label').textContent=i.objective==='zoneA'?'Modeled Zone A reduction':'Modeled A/B/C reduction';
      $('joint-cost').textContent=result?money(result.cost):'Infeasible';$('joint-unspent').textContent=result?money(result.unspent)+' unspent':'';
      $('joint-length').textContent=result?km(result.covered_road_km):'—';$('joint-capacity').textContent=result?'of '+km(result.capacity_km)+' effective reach':'';
      $('joint-benefit').textContent=result?tonnes(result[i.objective]):'—';
      $('joint-summary').textContent=result?labels[policy]+': '+result.selected.length+' packages across '+result.townsSelected+' towns, covering '+result.selected_cell_ids.length+' whole cells. '+km(result.covered_zone_a_km)+' of assigned road length is in Zone A.':'No feasible plan. Each town needs an enabled, affordable package with at least one cell that fits its capacity.';
      const assigned=new Set(result?.selected_cell_ids??[]);
      for(const cell of document.querySelectorAll('.joint-cell'))cell.style.fill=assigned.has(cell.dataset.cell)?'#007aff':'#e1e6e2';
      $('joint-assignments').innerHTML='<table><thead><tr><th>Town / package</th><th>Road km</th><th>Unused km</th></tr></thead><tbody>'+towns.map(t=>{
        const p=result?.selected.find(p=>p.town===t);return '<tr><th>'+escapeHtml(niceTown(t))+'<br><span class="small">'+(p?escapeHtml(p.project_type)+' · '+p.allocation.selected_cell_ids.length+' cells':'No assignment')+'</span></th><td>'+(p?p.allocation.covered_road_km.toFixed(2):'—')+'</td><td>'+(p?p.allocation.unused_capacity_km.toFixed(2):'—')+'</td></tr>';
      }).join('')+'</tbody></table>';
      $('joint-uniform').textContent=result?'Same equipment, spread uniformly: '+tonnes(result.uniform_same_equipment[i.objective])+' on the selected objective. This fractional benchmark uses the full effective capacity; whole-cell assignments can leave capacity unused.':'No uniform benchmark for an infeasible plan.';
      const certifiable=['statusQuo','independent','pooled','participation'].includes(policy),benchmark=reference?.exact_plans[policy];
      $('joint-benchmark').textContent=inputsMatch&&!savedBenchmark.exact_plans?'Unrounded benchmark not certified for this objective within the solver limit. The conservative rounded-model result remains available; no unrounded optimality claim is made.':!reference?'Saved-input benchmark inactive. One or more inputs changed; no live SciPy optimality claim is made.':!certifiable?'Saved inputs match. This policy is reported without a rounding-gap claim because the heuristic or actual-spend ceiling can change with allocation.':benchmark&&result?'Saved-input SciPy check: '+tonnes(benchmark[i.objective])+' unrounded primary optimum; conservative gap '+tonnes(Math.max(0,benchmark[i.objective]-result[i.objective]))+'. The check applies to these saved inputs only.':'Saved-input SciPy check: no feasible portfolio for this policy.';
      $('joint-comparison').innerHTML='<table><thead><tr><th>Funding rule</th><th>Capital</th><th>Road km</th><th>Modeled '+(i.objective==='zoneA'?'Zone A':'A/B/C')+' t</th><th>Towns</th></tr></thead><tbody>'+Object.entries(currentJoint.plans).map(([k,r])=>'<tr'+(k===policy?' class="selected"':'')+'><th>'+escapeHtml(labels[k])+'</th><td>'+(r?money(r.cost):'Infeasible')+'</td><td>'+(r?r.covered_road_km.toFixed(2):'—')+'</td><td>'+(r?r[i.objective].toFixed(2):'—')+'</td><td>'+(r?r.townsSelected:'—')+'</td></tr>').join('')+'</tbody></table>';
      saveReach(capacities);
    }catch(err){
      currentJoint=null;reference=null;$('joint-error').textContent=err.message;$('joint-error').hidden=false;$('joint-output').hidden=true;$('joint-json').disabled=true;$('joint-csv').disabled=true;clearMap();
    }
  }
  function download(content,type,name){const url=URL.createObjectURL(new Blob([content],{type})),link=document.createElement('a');link.href=url;link.download=name;link.click();URL.revokeObjectURL(url);}
  $('joint-policy').addEventListener('change',updateJoint);
  $('joint-capacity-editor').addEventListener('input',updateJoint);
  $('joint-reset').addEventListener('click',()=>{originalProjects.forEach(p=>reachInput(p).value=defaults[p.project_id]);updateJoint();});
  $('joint-json').addEventListener('click',()=>{
    if(!currentJoint)return;
    download(JSON.stringify({schema_version:1,model:'CAPACITY_LINKED_WHOLE_CELLS',input_status:'SIMULATED_OR_UNVERIFIED_USER_INPUT',source_sha256:data.source_sha256,interpretation:data.interpretation,selected_policy:$('joint-policy').value,scenario:currentJoint,cells:data.cells,saved_input_benchmark:reference},null,2),'application/json','saltshield-linked-plan.json');
  });
  $('joint-csv').addEventListener('click',()=>{
    const policy=$('joint-policy').value,r=currentJoint?.plans[policy];if(!r)return;
    const fields=['policy','project_id','town','cell_id','eligible_km','zone_a_km','protected_km','service_reach_km_simulated','effective_capacity_km','rounding_quantum_km','parameter_status','planning_cells_sha256'],rows=[],byId=new Map(data.cells.map(c=>[c.cell_id,c]));
    for(const p of r.selected)for(const id of p.allocation.selected_cell_ids){const c=byId.get(id);rows.push([policy,p.project_id,p.town,id,c.eligible_km,c.zone_a_km,c.protected_km,p.service_reach_km_assumed,p.allocation.capacity_km,currentJoint.quantum_km,'SIMULATED_REACH_BASELINE_PRICE_AND_EFFECT',data.source_sha256['data/processed/planning_cells.geojson']]);}
    const quote=v=>'"'+String(v).replace(/"/g,'""')+'"';download([fields,...rows].map(row=>row.map(quote).join(',')).join('\n'),'text/csv','saltshield-assigned-cells.csv');
  });
  try{
    const draft=JSON.parse(localStorage.getItem(key)??'null');
    if(draft&&SaltShieldJoint.matches(draft.source_sha256,data.source_sha256)&&draft.capacities&&Object.keys(draft.capacities).length===originalProjects.length&&originalProjects.every(p=>typeof draft.capacities[p.project_id]==='number'&&Number.isFinite(draft.capacities[p.project_id])&&draft.capacities[p.project_id]>=0))originalProjects.forEach(p=>reachInput(p).value=draft.capacities[p.project_id]);
  }catch{/* Fresh saved assumptions remain in place. */}
  globalThis.SaltShieldJointUI={update:updateJoint};updateJoint();
})();
