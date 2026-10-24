/* Evaluation tables and exports; all numbers come from the numerical module. */
(() => {
  const get=id=>document.getElementById(id);
  const names={statusQuo:'No new investment',independent:'Independent optimum',greedy:'Benefit / cost heuristic',pooled:'Pooled optimum',participation:'Pooled · every town',equalSpend:'Pooled · equal actual spend',equalSpendParticipation:'Equal spend · every town'};
  const patterns={NEVER_SELECTED:'Never selected',ALWAYS_SELECTED:'Selected in every feasible case',PARAMETER_SENSITIVE:'Changes with assumptions',NO_FEASIBLE_CASE:'No feasible case'};
  function reason(row){
    const fixed={SELECTED:'Included in this portfolio.',DISABLED:'Disabled in the project inputs.',NO_BENEFIT:'No modeled reduction under these coverage and effect assumptions.',EXCLUSIVE_GROUP_SELECTED:'A mutually exclusive project for this town was selected earlier in the ratio ordering.',PROJECT_EXCEEDS_TOTAL_CEILING:'This project alone exceeds this funding rule\'s total ceiling.',PROJECT_EXCEEDS_LOCAL_CEILING:'This project alone exceeds its town\'s independent budget ceiling.',NO_FEASIBLE_PORTFOLIO_WITH_PROJECT:'Requiring this project leaves no portfolio satisfying this rule\'s budget and participation constraints.',POLICY_INFEASIBLE:'No feasible portfolio exists under the selected funding rule.',NO_NEW_INVESTMENT_BASELINE:'No projects are purchased in the current-state baseline.',PRIMARY_TIE_SECONDARY_OR_COST:'Matches the primary objective. Secondary protected / Zone A benefits, lower cost, then input order break ties.'};
    if(row.code==='LOWER_PORTFOLIO_BENEFIT')return 'Requiring this project lowers the best achievable objective by '+tonnes(row.objective_loss_t)+'.';
    if(row.code==='REMAINING_BUDGET')return 'At rank '+row.rank+', only '+money(row.remaining_budget_usd)+' remained. The heuristic could not purchase this project.';
    return fixed[row.code]||row.code;
  }
  function render(){
    const valid=Boolean(currentAssessment&&currentInputs);get('comparison-export').disabled=!valid;get('sensitivity-export').disabled=!valid;if(!valid)return;
    const a=currentAssessment,baseline=a.baseline_totals_t_simulated;
    get('baseline-totals').textContent='Illustrative baseline on eligible municipal paved roads: '+tonnes(baseline.eligible)+' total, including '+tonnes(baseline.all)+' in A/B/C and '+tonnes(baseline.zoneA)+' in Zone A. Current-state avoided application is zero. All reduction columns are modeled tonnes per winter.';
    get('baseline-comparison').innerHTML=['statusQuo','independent','greedy','pooled'].map(mode=>{const p=a.plans[mode];return '<tr><th>'+names[mode]+'</th><td>'+money(p.cost)+'</td><td>'+tonnes(p.eligible)+'</td><td>'+tonnes(p.all)+'</td><td>'+tonnes(p.zoneA)+'</td><td>'+p.townsSelected+' / '+towns.length+'</td></tr>';}).join('');
    const gain=a.plans.pooled[currentInputs.objective]-a.plans.greedy[currentInputs.objective];
    get('baseline-comparison-note').textContent=Math.abs(gain)<1e-8?'The pooled optimum and ratio heuristic reach the same objective in this case. No optimization gain is claimed.':'The pooled optimum adds '+tonnes(gain)+' on the selected objective over the ratio heuristic. Selected spending may differ; inspect the capital column and equal-spend check.';
    const policy=get('decision-policy').value,decisions=a.project_decisions.filter(r=>r.policy===policy);
    get('project-decisions').innerHTML=decisions.map(r=>'<tr><th>'+escapeHtml(niceTown(r.town))+' / '+escapeHtml(originalProjects.find(p=>p.project_id===r.project_id).project_type)+'</th><td'+(r.selected?' class="decision-selected"':'')+'>'+(r.selected?'Selected':'Not selected')+'</td><td>'+escapeHtml(reason(r))+'</td></tr>').join('');
    const records=a.sensitivity.selection.filter(r=>r.policy===policy);
    get('stability-summary').textContent=names[policy]+' · '+a.sensitivity.case_count+' assumed cases. '+(records[0]?.feasible_cases??0)+' have a feasible portfolio. Selection is assessed at the project level; it does not establish real-world effectiveness.';
    get('project-stability').innerHTML=records.map(r=>{const p=originalProjects.find(x=>x.project_id===r.project_id);return '<tr><th>'+escapeHtml(niceTown(p.town))+' / '+p.project_type+'</th><td>'+r.selected_cases+' / '+r.feasible_cases+'</td><td>'+patterns[r.status]+(r.selected_only_with_optimistic_effect?' · selected only with optimistic effects':'')+'</td></tr>';}).join('');
  }
  function download(rows,name){
    if(!rows.length)return;const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))];
    const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
    const text='\uFEFF'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(quote).join(',')).join('\n')+'\n';
    const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=name;link.click();URL.revokeObjectURL(url);
  }
  get('decision-policy').addEventListener('change',render);
  get('comparison-export').addEventListener('click',()=>{if(!currentAssessment)return;download(Object.entries(currentAssessment.plans).map(([policy,p])=>({policy,objective:currentInputs.objective,total_budget_usd:currentInputs.budget,feasible:p!==null,capital_usd:p?.cost,avoided_eligible_t_simulated:p?.eligible,avoided_protected_t_simulated:p?.all,avoided_zone_a_t_simulated:p?.zoneA,towns_funded:p?.townsSelected,selected_ids:p?.selected.map(x=>x.project_id).join(';'),parameter_fingerprint:ANALYSIS.planning.parameter_fingerprint})),'SaltShield_Investment_Comparison.csv');});
  get('sensitivity-export').addEventListener('click',()=>{if(!currentAssessment)return;const rows=[];currentAssessment.sensitivity.cases.forEach((c,i)=>{for(const [policy,p] of Object.entries(c.plans))rows.push({case:i+1,policy,cost_multiplier:c.cost_multiplier,baseline_multiplier:c.baseline_multiplier,effect:c.effect,objective:currentInputs.objective,feasible:p!==null,capital_usd:p?.cost,avoided_protected_t_simulated:p?.all,avoided_zone_a_t_simulated:p?.zoneA,selected_ids:p?.selected_ids.join(';')});});download(rows,'SaltShield_Investment_Sensitivity.csv');});
  globalThis.SaltShieldEvaluationUI={render};render();
})();
