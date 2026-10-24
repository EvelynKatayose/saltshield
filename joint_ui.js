/* Separate capacity-linked scenario, sharing only the explicit investment inputs. */
(() => {
  const data=ANALYSIS.joint,$=id=>document.getElementById(id),labels={statusQuo:'No new investment',independent:'Independent budgets',greedy:'Benefit / cost heuristic',pooled:'Shared budget',participation:'Shared · every town',equalSpend:'Shared · equal actual spending',equalSpendParticipation:'Equal spending · every town'};
  const reachInput=p=>$('joint-reach-'+p.project_id),defaults=Object.fromEntries(data.capacities.map(r=>[r.project_id,r.max_road_km_per_winter])),key='saltshield-joint-reach';
  let currentJoint=null,reference=null,reachAssessment=null,revision=0;
  const km=v=>v.toFixed(2)+' km';
  function readReach(){return Object.fromEntries(originalProjects.map(p=>[p.project_id,numericInput(reachInput(p),niceTown(p.town)+' service reach')]));}
  function saveReach(capacities){try{localStorage.setItem(key,JSON.stringify({source_sha256:data.source_sha256,capacities}));$('joint-draft-status').textContent='Reach saved on this device.';}catch{$('joint-draft-status').textContent='Reach is available for this session. Export to keep a copy.';}}
  function clearMap(){for(const cell of document.querySelectorAll('.joint-cell'))cell.style.fill='#e1e6e2';}
  function renderReach(){
    $('joint-reach-review').setAttribute('aria-busy','false');$('joint-reach-run').disabled=!currentJoint;
    if(reachAssessment&&!SaltShieldJoint.matches(reachAssessment.input_snapshot,currentJoint?.input_snapshot))reachAssessment=null;
    if(!reachAssessment&&currentJoint&&data.reach_sensitivity&&SaltShieldJoint.matches(data.reach_sensitivity.input_snapshot,currentJoint.input_snapshot))reachAssessment=data.reach_sensitivity;
    $('joint-reach-output').hidden=!reachAssessment;$('joint-reach-csv').disabled=!reachAssessment;
    if(!reachAssessment){$('joint-reach-status').textContent=currentJoint?'Reach check needs an update. Run nine cases for the current inputs.':'Enter valid planning inputs before running a reach check.';$('joint-reach-table').innerHTML='';$('joint-reach-selection').innerHTML='';return;}
    const policy=$('joint-policy').value,s=reachAssessment.summaries[policy],objective=currentJoint.input_snapshot.objective;
    $('joint-reach-status').textContent=labels[policy]+' · 9 assumed cases; '+s.feasible_cases+' feasible. '+s.matching_equipment_cases+' retain the current equipment portfolio.'+(s.objective_t_low!==null?' Modeled reduction: '+tonnes(s.objective_t_low)+' to '+tonnes(s.objective_t_high)+'.':'');
    $('joint-reach-table').innerHTML='<table><thead><tr><th>CAL reach</th><th>BRINE reach</th><th>Capital</th><th>Modeled '+(objective==='zoneA'?'Zone A':'A/B/C')+' t</th><th>Same equipment</th><th>Original roads retained</th></tr></thead><tbody>'+reachAssessment.cases.map(c=>{const p=c.plans[policy];return '<tr><th>'+c.cal_multiplier*100+'%</th><td>'+c.brine_multiplier*100+'%</td><td>'+(p?money(p.cost):'Infeasible')+'</td><td>'+(p?p[objective].toFixed(2):'—')+'</td><td>'+(p&&p.same_equipment_as_current!==null?(p.same_equipment_as_current?'Yes':'No'):'—')+'</td><td>'+(p?.retained_base_road_fraction!==null&&p?.retained_base_road_fraction!==undefined?(p.retained_base_road_fraction*100).toFixed(1)+'%':'—')+'</td></tr>';}).join('')+'</tbody></table>';
    $('joint-reach-selection').innerHTML='<table><thead><tr><th>Town / package</th><th>Selected / feasible cases</th></tr></thead><tbody>'+reachAssessment.selection.filter(r=>r.policy===policy).map(r=>{const p=originalProjects.find(p=>p.project_id===r.project_id);return '<tr><th>'+escapeHtml(niceTown(p.town)+' / '+p.project_type)+'</th><td>'+r.selected_cases+' / '+r.feasible_cases+'</td></tr>';}).join('')+'</tbody></table>';
  }
  function updateJoint(){
    revision++;
    try{
      if(!currentInputs||!currentAssessment)throw Error('Enter valid investment inputs to calculate a linked plan.');
      const capacities=readReach(),i=currentInputs;
      currentJoint=SaltShieldJoint.solve(i.projects,data.cells,capacities,i.budget,towns,i.effect,i.baselineRates,i.objective,i.localCaps);
      const savedBenchmark=data.benchmarks[i.objective],inputsMatch=SaltShieldJoint.matches(savedBenchmark.input_snapshot,currentJoint.input_snapshot);
      reference=inputsMatch&&savedBenchmark.exact_plans?savedBenchmark:null;
      const policy=$('joint-policy').value,result=currentJoint.plans[policy];
      if(!(policy in labels))throw Error('Unknown funding rule.');
      $('joint-error').hidden=true;$('joint-output').hidden=false;
      $('joint-json').disabled=false;$('joint-csv').disabled=result===null;$('joint-brief').disabled=result===null;
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
      $('joint-benchmark').textContent=SaltShieldJointBrief.benchmarkMessage(currentJoint,policy,data);
      $('joint-comparison').innerHTML='<table><thead><tr><th>Funding rule</th><th>Capital</th><th>Road km</th><th>Modeled '+(i.objective==='zoneA'?'Zone A':'A/B/C')+' t</th><th>Towns</th></tr></thead><tbody>'+Object.entries(currentJoint.plans).map(([k,r])=>'<tr'+(k===policy?' class="selected"':'')+'><th>'+escapeHtml(labels[k])+'</th><td>'+(r?money(r.cost):'Infeasible')+'</td><td>'+(r?r.covered_road_km.toFixed(2):'—')+'</td><td>'+(r?r[i.objective].toFixed(2):'—')+'</td><td>'+(r?r.townsSelected:'—')+'</td></tr>').join('')+'</tbody></table>';
      saveReach(capacities);
    }catch(err){
      currentJoint=null;reference=null;$('joint-error').textContent=err.message;$('joint-error').hidden=false;$('joint-output').hidden=true;$('joint-json').disabled=true;$('joint-csv').disabled=true;$('joint-brief').disabled=true;clearMap();
    }
    renderReach();
  }
  function download(content,type,name){const url=URL.createObjectURL(new Blob([content],{type})),link=document.createElement('a');link.href=url;link.download=name;link.click();URL.revokeObjectURL(url);}
  $('joint-policy').addEventListener('change',updateJoint);
  $('joint-capacity-editor').addEventListener('input',updateJoint);
  $('joint-reset').addEventListener('click',()=>{originalProjects.forEach(p=>reachInput(p).value=defaults[p.project_id]);updateJoint();});
  $('joint-json').addEventListener('click',()=>{
    if(!currentJoint)return;
    download(JSON.stringify({schema_version:1,model:'CAPACITY_LINKED_WHOLE_CELLS',input_status:'SIMULATED_OR_UNVERIFIED_USER_INPUT',source_sha256:data.source_sha256,interpretation:data.interpretation,selected_policy:$('joint-policy').value,scenario:currentJoint,cells:data.cells,saved_input_benchmark:reference,reach_sensitivity:reachAssessment},null,2),'application/json','saltshield-linked-plan.json');
  });
  $('joint-brief').addEventListener('click',()=>{
    const policy=$('joint-policy').value;if(!currentJoint?.plans[policy])return;
    download(SaltShieldJointBrief.render({scenario:currentJoint,policy,data,sensitivity:reachAssessment,mapSvg:$('joint-map').innerHTML,sources:ANALYSIS.official_sources}),'text/html;charset=utf-8','SaltShield_Linked_Brief.html');
  });
  $('joint-reach-run').addEventListener('click',async()=>{
    if(!currentJoint||!currentInputs)return;
    const token=++revision,i=currentInputs,capacities=readReach(),snapshot=currentJoint.input_snapshot;
    $('joint-reach-run').disabled=true;$('joint-reach-review').setAttribute('aria-busy','true');$('joint-reach-status').textContent='Checking nine reach cases…';
    await new Promise(resolve=>(globalThis.requestAnimationFrame??(fn=>fn()))(resolve));
    if(token!==revision)return;
    try{
      const result=SaltShieldJoint.assessReach(i.projects,data.cells,capacities,i.budget,towns,i.effect,i.baselineRates,i.objective,i.localCaps);
      if(token!==revision||!SaltShieldJoint.matches(snapshot,currentJoint?.input_snapshot))return;
      reachAssessment=result;renderReach();
    }catch(err){reachAssessment=null;renderReach();$('joint-reach-status').textContent='Reach check failed: '+err.message;}
  });
  $('joint-reach-csv').addEventListener('click',()=>{
    if(!reachAssessment||!currentJoint||!SaltShieldJoint.matches(reachAssessment.input_snapshot,currentJoint.input_snapshot))return;
    const policy=$('joint-policy').value,objective=currentJoint.input_snapshot.objective,headers=['case_id','cal_multiplier','brine_multiplier','policy','feasible','capital_usd','objective','objective_t_simulated','road_km','same_equipment_as_current','retained_base_road_fraction','selected_ids_json','selected_cell_ids_json','case_capacities_json','base_input_snapshot_json','source_sha256_json'];
    const rows=reachAssessment.cases.map(c=>{const r=c.plans[policy];return [c.case_id,c.cal_multiplier,c.brine_multiplier,policy,r!==null,r?r.cost:'',objective,r?r[objective]:'',r?r.covered_road_km:'',r?.same_equipment_as_current??'',r?.retained_base_road_fraction??'',JSON.stringify(r?.selected_ids??[]),JSON.stringify(r?.selected_cell_ids??[]),JSON.stringify(c.capacities),JSON.stringify(reachAssessment.input_snapshot),JSON.stringify(data.source_sha256)];});
    const quote=v=>'"'+String(v).replace(/"/g,'""')+'"';download([headers,...rows].map(row=>row.map(quote).join(',')).join('\n'),'text/csv','saltshield-reach-check.csv');
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
