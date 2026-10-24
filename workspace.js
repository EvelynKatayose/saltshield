/* Navigation, appearance, and a live brief. No network or model calls. */
(() => {
  const get=id=>document.getElementById(id);
  const views=['overview','investments','coverage','evidence'];
  const titles={experience:'Experience',overview:'Overview',investments:'Investments',coverage:'Road Coverage',evidence:'Evidence'};
  const policies={participation:'Shared funding · a project in every town',pooled:'Shared funding · unrestricted allocation',independent:'Independent town budgets',greedy:'Benefit / cost heuristic',statusQuo:'No new investment'};
  const spatialLabels={integer:'Whole-cell optimum',greedy:'Ratio heuristic',uniform:'Uniform coverage',fractional_bound:'Fractional upper bound'};
  let briefHtml='';
  let restorationNotice='';
  function saveDraft() {
    if(!current||!currentInputs){get('draft-status').textContent='Check investment inputs';return;}
    try{
      const draft={schema_version:2,evidence_sha256:ANALYSIS.phase2.evidence.source.sha256,parameter_fingerprint:ANALYSIS.planning.parameter_fingerprint,inputs:{budget:currentInputs.budget,intensity:currentInputs.intensity,effect:currentInputs.effect,objective:currentInputs.objective,projects:currentInputs.projects.map(p=>({project_id:p.project_id,capital_cost_usd:p.capital_cost_usd,coverage_fraction_assumed:p.coverage_fraction_assumed,enabled:p.enabled}))},coverage:{fraction:String(Number(get('spatial-fraction').value)),method:get('spatial-method').value},brief_policy:get('brief-policy').value};
      if(!globalThis.localStorage)throw Error('Storage unavailable');
      globalThis.localStorage.setItem('saltshield-draft',JSON.stringify(draft));
      get('draft-status').textContent=restorationNotice||'Saved on this device';restorationNotice='';
    }catch{get('draft-status').textContent='Draft storage unavailable';}
  }
  function showView(view,focus=false) {
    if(!['experience',...views].includes(view))view='overview';
    for(const name of ['experience',...views])get(name+'-view').hidden=name!==view;
    document.documentElement.dataset.view=view;
    globalThis.SaltShieldExperience?.visibility(view==='experience');
    for(const button of document.querySelectorAll('[data-view]')) {
      const active=button.dataset.view===view;button.classList.toggle('active',active);
      if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
    }
    get('view-title').textContent=titles[view];
    try{globalThis.history?.replaceState(null,'','#'+view);}catch{}
    globalThis.scrollTo?.({top:0,behavior:'auto'});
    if(focus){const heading=get(view+'-heading');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}}
  }
  for(const button of document.querySelectorAll('[data-view]')) {
    button.addEventListener('click',()=>showView(button.dataset.view,true));
    button.addEventListener('keydown',event=>{
      if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;
      event.preventDefault();
      const delta=['ArrowRight','ArrowDown'].includes(event.key)?1:-1;
      const index=(views.indexOf(button.dataset.view)+delta+views.length)%views.length;
      showView(views[index]);
      document.querySelector('[data-view="'+views[index]+'"]').focus();
    });
  }
  for(const button of document.querySelectorAll('[data-go]'))button.addEventListener('click',()=>showView(button.dataset.go,true));
  globalThis.addEventListener?.('hashchange',()=>showView(globalThis.location.hash.slice(1)));
  showView(globalThis.location?.hash.slice(1)||'experience');

  let appearance='light', followsSystem=true;
  const media=globalThis.matchMedia?.('(prefers-color-scheme: dark)');
  try{const saved=globalThis.localStorage?.getItem('saltshield-appearance');if(['light','dark'].includes(saved)){appearance=saved;followsSystem=false;}else appearance=media?.matches?'dark':'light';}catch{appearance=media?.matches?'dark':'light';}
  function applyAppearance(){document.documentElement.dataset.theme=appearance;get('appearance').setAttribute('aria-label','Use '+(appearance==='light'?'dark':'light')+' appearance');get('appearance').setAttribute('aria-pressed',String(appearance==='dark'));}
  applyAppearance();
  get('appearance').addEventListener('click',()=>{appearance=appearance==='light'?'dark':'light';followsSystem=false;applyAppearance();try{globalThis.localStorage?.setItem('saltshield-appearance',appearance);}catch{}});
  media?.addEventListener('change',event=>{if(followsSystem){appearance=event.matches?'dark':'light';applyAppearance();}});

  function refresh() {
    saveDraft();
    const policy=get('brief-policy').value, plan=current?.[policy];
    const ready=Boolean(current&&currentInputs&&plan);
    get('download-brief').disabled=!ready;get('print-brief').disabled=!ready;
    if(!ready){briefHtml='';get('brief-content').innerHTML='<p class="brief-empty">'+(current?'No feasible plan under this funding rule. Adjust the budget, enable a project in each town, or choose another rule.':'Enter valid investment inputs to prepare the brief.')+'</p>';return;}
    const fraction=Number(get('spatial-fraction').value),method=get('spatial-method').value;
    const cases=ANALYSIS.phase3.spatial.cases.filter(c=>c.coverage_fraction===fraction);
    const spatialTotal=key=>cases.reduce((s,c)=>s+c.plans[method][key],0);
    const uniform=cases.reduce((s,c)=>s+c.plans.uniform.covered_zone_a_km,0);
    const projectRows=towns.map(t=>{const p=plan.selected.find(x=>x.town===t);return '<tr><td>'+escapeHtml(niceTown(t))+'</td><td>'+(p?(p.project_type==='CAL'?'Calibration / controls':'Brine / pre-wetting'):'No project')+'</td><td>'+money(p?.capital_cost_usd||0)+'</td><td>'+(p?(p.coverage_fraction_assumed*100).toFixed(0)+'%':'—')+'</td></tr>';}).join('');
    const metric=(label,value,note)=>'<div class="brief-metric"><span>'+label+'</span><strong>'+value+'</strong><small>'+note+'</small></div>';
    const objective=currentInputs.objective,scope=objective==='all'?'A/B/C':'Zone A';
    const stability=currentAssessment.sensitivity.selection.filter(r=>r.policy===policy&&plan.selected.some(p=>p.project_id===r.project_id)).map(r=>escapeHtml(r.project_id)+': selected in '+r.selected_cases+' / '+r.feasible_cases+' feasible cases').join('; ')||'No equipment selected in this case';
    briefHtml='<p class="small" style="margin-bottom:21px">Uniform coverage model · '+policies[policy]+' · '+escapeHtml(currentInputs.effect)+' assumptions · '+scope+' objective</p><div class="brief-metrics">'+metric('Selected capital',money(plan.cost),'of '+money(currentInputs.budget)+' ceiling')+metric('Modeled '+scope+' reduction',tonnes(plan[objective]),'avoided application per winter')+metric('Towns with a project',plan.townsSelected+' / '+towns.length,money(plan.unspent)+' budget unused')+'</div>'+
      '<table><thead><tr><th>Town</th><th>Equipment package</th><th>Capital</th><th>Coverage</th></tr></thead><tbody>'+projectRows+'</tbody></table>'+
      '<div class="brief-section"><h3>The budget check</h3><p>At the independent plan\'s actual spending of '+money(current.independent.cost)+', unrestricted pooling models '+tonnes(current.equalSpend[objective])+' of avoided '+scope+' application across '+current.equalSpend.townsSelected+' funded towns. '+(current.equalSpendParticipation?'Requiring a project in every town at that spending models '+tonnes(current.equalSpendParticipation[objective])+'.':'Funding every town at that spending is infeasible.')+' At the full ceiling, the ratio heuristic models '+tonnes(current.greedy[objective])+' and the pooled optimum '+tonnes(current.pooled[objective])+'.</p></div>'+
      '<div class="brief-section"><h3>Parameter sensitivity</h3><p>'+stability+'. Tested 27 assumed cases across costs, baseline intensity and effect bounds. These counts are not confidence probabilities.</p></div>'+
      '<div class="brief-section"><h3>Road coverage, considered separately</h3><p>'+spatialLabels[method]+' · '+(fraction*100).toFixed(0)+'% capacity per town. Covers '+spatialTotal('covered_zone_a_km').toFixed(2)+' km of Zone A roads versus '+uniform.toFixed(2)+' km under uniform coverage, using '+spatialTotal('covered_road_km').toFixed(2)+' of '+spatialTotal('capacity_km').toFixed(2)+' km capacity. '+(method==='uniform'||method==='fractional_bound'?'This benchmark permits partial cells. ':'Whole cells are selected. ')+'Planning cells are not validated maintenance routes.</p></div>'+
      '<div class="brief-section"><h3>Assumptions and next checks</h3><p>Mean baseline salt: '+currentInputs.intensity+' t / centerline km / winter. Town profiles scale together. Project prices, coverage and reduction rates are illustrative. Verify town salt logs, existing equipment, service requirements and current vendor quotes before procurement. Results do not predict water concentrations or safe road service.</p></div>'+
      '<div class="brief-section"><p>Sources: MassGIS / MassDOT / MassDEP geometry; <a href="https://www.mass.gov/info-details/dcr-watershed-system-salt-reduction">DCR historical awards</a> (13 grants; $188,251); ERA5 regional context (five winters; 18,144 hours). Weather does not calibrate these benefits. Evidence snapshot: <code>'+ANALYSIS.phase2.evidence.source.sha256.slice(0,12)+'</code>.</p></div>';
    get('brief-content').innerHTML=briefHtml;
  }
  get('brief-policy').addEventListener('change',refresh);
  get('download-brief').addEventListener('click',()=>{
    refresh();if(!briefHtml)return;
    const style='body{font:13px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1d1d1f;max-width:820px;margin:45px auto;padding:0 25px}h1{font-size:30px;letter-spacing:-1px;margin-bottom:0}h3{font-size:13px;margin:15px 0 5px}p{margin:5px 0}.small,small{font-size:10px;color:#6e6e73}.brief-metrics{display:flex;gap:30px;margin:25px 0}.brief-metric{flex:1}.brief-metric span,.brief-metric small{display:block;font-size:10px;color:#6e6e73}.brief-metric strong{display:block;font-size:26px;line-height:1.4}table{width:100%;border-collapse:collapse;font-size:11px}th,td{text-align:left;border-bottom:1px solid #ddd;padding:9px 5px}.brief-section{border-top:1px solid #ddd;padding-top:10px;margin-top:17px}.brief-section p{font-size:11px}a{color:#0066cc}code{font-size:9px}@media print{@page{margin:16mm}body{margin:0;max-width:none;padding:0}.brief-section{break-inside:avoid}}';
    const output='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SaltShield — Decision brief</title><style>'+style+'</style></head><body><p class="small">SALTSHIELD · WACHUSETT RESERVOIR · '+new Date().toISOString().slice(0,10)+'</p><h1>Investment and coverage brief</h1>'+briefHtml+'<p class="small" style="margin-top:20px">Prepared from an illustrative planning scenario. Coverage allocation is independent of the investment budget.</p></body></html>';
    const url=URL.createObjectURL(new Blob([output],{type:'text/html;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='SaltShield_Decision_Brief.html';link.click();URL.revokeObjectURL(url);
  });
  get('print-brief').addEventListener('click',()=>{refresh();if(briefHtml)globalThis.print?.();});
  // Validate the entire saved draft before applying any field. Only operational
  // inputs are restored; measured geometry, evidence and effects are immutable.
  try{
    const raw=globalThis.localStorage?.getItem('saltshield-draft');
    if(raw){
      if(raw.length>2000000)throw Error('Oversized draft');
      const draft=JSON.parse(raw), input=draft.inputs;
      if(draft.schema_version!==2||draft.evidence_sha256!==ANALYSIS.phase2.evidence.source.sha256)throw Error('Different evidence snapshot');
      if(draft.parameter_fingerprint!==undefined&&draft.parameter_fingerprint!==ANALYSIS.planning.parameter_fingerprint)throw Error('Different parameter snapshot');
      const objective=input?.objective??'zoneA';if(!['zoneA','all'].includes(objective))throw Error('Invalid planning objective');
      if(typeof input?.budget!=='number'||typeof input?.intensity!=='number'||!['low','central','high'].includes(input?.effect)||!Array.isArray(input?.projects)||input.projects.length!==originalProjects.length)throw Error('Invalid inputs');
      const pp=new Map(input.projects.map(p=>[p.project_id,p]));
      if(pp.size!==originalProjects.length||originalProjects.some(p=>!pp.has(p.project_id)))throw Error('Invalid project IDs');
      const restored=originalProjects.map(p=>{const q=pp.get(p.project_id);if(typeof q.enabled!=='boolean'||typeof q.capital_cost_usd!=='number'||typeof q.coverage_fraction_assumed!=='number')throw Error('Invalid project controls');return {...p,enabled:q.enabled,capital_cost_usd:q.capital_cost_usd,coverage_fraction_assumed:q.coverage_fraction_assumed};});
      SaltShieldV1.evaluate(restored,input.budget,towns,input.effect,effectiveRates(input.intensity),objective,policyCaps(input.budget));
      if(!['0.25','0.5','0.75','1'].includes(draft.coverage?.fraction)||!Object.keys(spatialLabels).includes(draft.coverage?.method)||!Object.keys(policies).includes(draft.brief_policy))throw Error('Invalid coverage or policy');
      for(const p of restored){const row=document.querySelector('[data-project="'+p.project_id+'"]');row.querySelector('[data-field="cost"]').value=p.capital_cost_usd;row.querySelector('[data-field="coverage"]').value=p.coverage_fraction_assumed*100;row.querySelector('[data-field="enabled"]').checked=p.enabled;}
      get('budget').value=input.budget;get('intensity').value=input.intensity;get('effect').value=input.effect;get('objective').value=objective;
      get('spatial-fraction').value=draft.coverage.fraction;get('spatial-method').value=draft.coverage.method;get('brief-policy').value=draft.brief_policy;
      get('spatial-fraction').dispatchEvent(new Event('change'));update();
      restorationNotice='Draft restored on this device';
    }
  }catch{restorationNotice='Saved draft not restored; defaults loaded';}
  globalThis.SaltShieldWorkspace={refresh,showView};
  refresh();
})();
