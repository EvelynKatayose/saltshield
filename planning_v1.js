/* Project evaluation mirrors planning_v1.py. All salt effects are illustrative. */
(() => {
  const policies=['statusQuo','independent','greedy','pooled','participation','equalSpend','equalSpendParticipation'];
  function number(v,label){if(typeof v!=='number'||!Number.isFinite(v)||v<0)throw Error('Invalid '+label);return v;}
  const empty=budget=>({cost:0,zoneA:0,all:0,eligible:0,selected:[],unspent:budget,townsSelected:0,feasibleCombinations:1});
  function greedyPlan(active,budget,objective){
    const primary=objective==='zoneA'?'avoided_zone_a_tonnes_simulated':'avoided_all_zones_tonnes_simulated',secondary=objective==='zoneA'?'avoided_all_zones_tonnes_simulated':'avoided_zone_a_tonnes_simulated';
    const ratio=(p,f)=>p.capital_cost_usd?p[f]/p.capital_cost_usd:(p[f]>0?Infinity:0);
    const ordered=[...active].sort((a,b)=>{for(const f of [primary,secondary]){const x=ratio(a,f),y=ratio(b,f);if(x!==y)return x>y?-1:1;}return a.capital_cost_usd-b.capital_cost_usd||(a.project_id<b.project_id?-1:a.project_id>b.project_id?1:0);});
    const result=empty(budget),funded=new Set(),trace=[];
    ordered.forEach((p,i)=>{
      let code;
      if(p.enabled===false)code='DISABLED';else if(p[primary]<=0&&p[secondary]<=0)code='NO_BENEFIT';else if(funded.has(p.town))code='EXCLUSIVE_GROUP_SELECTED';else if(p.capital_cost_usd>result.unspent+1e-8)code='REMAINING_BUDGET';else{
        code='SELECTED';result.selected.push(p);funded.add(p.town);result.cost+=p.capital_cost_usd;result.unspent=budget-result.cost;result.zoneA+=p.avoided_zone_a_tonnes_simulated;result.all+=p.avoided_all_zones_tonnes_simulated;result.eligible+=p.avoided_all_eligible_tonnes_simulated;result.townsSelected++;
      }
      trace.push({project_id:p.project_id,code,rank:i+1,remaining_budget_usd:result.unspent,benefit_per_dollar:Number.isFinite(ratio(p,primary))?ratio(p,primary):null});
    });
    return {result,trace};
  }
  function evaluate(projects,budget,towns,effect='central',baseline=5,objective='zoneA',localCaps=null){
    number(budget,'budget');if(!towns.length||new Set(towns).size!==towns.length)throw Error('Towns must be unique and nonempty');if(!['zoneA','all'].includes(objective))throw Error('Unknown objective');
    if(typeof baseline!=='number'&&(!baseline||Object.keys(baseline).length!==towns.length||towns.some(t=>!Object.hasOwn(baseline,t))))throw Error('Baseline towns must match the study scope');
    const rates=Object.fromEntries(towns.map(t=>[t,number(typeof baseline==='number'?baseline:baseline[t],'town baseline')]));
    SaltShield.materialize(projects,towns,effect,0);
    const active=projects.map(p=>SaltShield.materialize([p],towns,effect,rates[p.town])[0]);
    if(localCaps!==null&&(Object.keys(localCaps).length!==towns.length||towns.some(t=>!Object.hasOwn(localCaps,t))))throw Error('Budget towns must match the study scope');
    const caps=Object.fromEntries(towns.map(t=>[t,localCaps===null?budget/towns.length:number(localCaps[t],'local cap')]));
    if(Math.abs(Object.values(caps).reduce((s,v)=>s+v,0)-budget)>1e-6)throw Error('Local ceilings must sum to the common total budget');
    const independent=SaltShield.solve(active,budget,towns,caps,false,objective),greedy=greedyPlan(active,budget,objective);
    const plans={statusQuo:empty(budget),independent,greedy:greedy.result,pooled:SaltShield.solve(active,budget,towns,null,false,objective),participation:SaltShield.solve(active,budget,towns,null,true,objective),equalSpend:SaltShield.solve(active,independent.cost,towns,null,false,objective),equalSpendParticipation:SaltShield.solve(active,independent.cost,towns,null,true,objective)};
    return {plans,active,rates,caps,trace:greedy.trace};
  }
  function explain(plans,active,budget,towns,objective,caps,trace){
    const rows=[],traceMap=new Map(trace.map(r=>[r.project_id,r]));
    for(const [policy,result] of Object.entries(plans)){
      const ceiling=policy.startsWith('equalSpend')?plans.independent.cost:budget;
      for(const p of active){
        const info={policy,project_id:p.project_id,town:p.town,selected:Boolean(result?.selected.some(q=>q.project_id===p.project_id)),counterfactual_objective_t:null,objective_loss_t:null};let code;
        if(policy==='statusQuo')code='NO_NEW_INVESTMENT_BASELINE';else if(p.enabled===false)code='DISABLED';else if(result===null)code='POLICY_INFEASIBLE';else if(info.selected)code='SELECTED';else if(policy==='greedy'){const item=traceMap.get(p.project_id);code=item.code;info.rank=item.rank;info.remaining_budget_usd=item.remaining_budget_usd;}
        else if(p.avoided_zone_a_tonnes_simulated<=0&&p.avoided_all_zones_tonnes_simulated<=0)code='NO_BENEFIT';else if(p.capital_cost_usd>ceiling+1e-8)code='PROJECT_EXCEEDS_TOTAL_CEILING';else if(policy==='independent'&&p.capital_cost_usd>caps[p.town]+1e-8)code='PROJECT_EXCEEDS_LOCAL_CEILING';else{
          const forced=SaltShield.solve(active,ceiling,towns,policy==='independent'?caps:null,['participation','equalSpendParticipation'].includes(policy),objective,p.project_id);
          if(forced===null)code='NO_FEASIBLE_PORTFOLIO_WITH_PROJECT';else{info.counterfactual_objective_t=forced[objective];info.objective_loss_t=Math.max(0,result[objective]-forced[objective]);code=info.objective_loss_t>1e-8?'LOWER_PORTFOLIO_BENEFIT':'PRIMARY_TIE_SECONDARY_OR_COST';}
        }
        rows.push({...info,code});
      }
    }
    return rows;
  }
  function sensitivity(projects,budget,towns,baseline,objective,caps){
    const cases=[],counts={},feasible={},effects={};
    for(const policy of policies){counts[policy]={};feasible[policy]=0;effects[policy]=Object.fromEntries(projects.map(p=>[p.project_id,new Set()]));}
    for(const cost of [.75,1,1.25])for(const scale of [.75,1,1.25])for(const effect of ['low','central','high']){
      const pp=projects.map(p=>({...p,capital_cost_usd:p.capital_cost_usd*cost})),rates=Object.fromEntries(towns.map(t=>[t,baseline[t]*scale]));
      const {plans}=evaluate(pp,budget,towns,effect,rates,objective,caps),item={cost_multiplier:cost,baseline_multiplier:scale,effect,plans:{}};
      for(const [policy,r] of Object.entries(plans)){
        item.plans[policy]=r===null?null:{cost:r.cost,zoneA:r.zoneA,all:r.all,eligible:r.eligible,unspent:r.unspent,townsSelected:r.townsSelected,selected_ids:r.selected.map(p=>p.project_id).sort()};
        if(r!==null){feasible[policy]++;for(const p of r.selected){counts[policy][p.project_id]=(counts[policy][p.project_id]||0)+1;effects[policy][p.project_id].add(effect);}}
      }
      cases.push(item);
    }
    const selection=[];
    for(const policy of policies)for(const p of projects){const n=counts[policy][p.project_id]||0,d=feasible[policy],e=effects[policy][p.project_id];selection.push({policy,project_id:p.project_id,selected_cases:n,feasible_cases:d,status:!d?'NO_FEASIBLE_CASE':!n?'NEVER_SELECTED':n===d?'ALWAYS_SELECTED':'PARAMETER_SENSITIVE',selected_only_with_optimistic_effect:e.size===1&&e.has('high')});}
    return {case_count:cases.length,cases,selection,interpretation:'27 deterministic cases, not probabilities or confidence intervals. Costs and baseline each vary +/-25%; effects use the illustrative low/central/high bounds. A common baseline multiplier rescales benefits without changing ranking when all rates are positive.'};
  }
  function assess(projects,budget,towns,effect='central',baseline=5,objective='zoneA',localCaps=null,includeSensitivity=true){
    const {plans,active,rates,caps,trace}=evaluate(projects,budget,towns,effect,baseline,objective,localCaps),groups=new Map(),totals={eligible:0,all:0,zoneA:0};
    for(const p of active){const lengths=[p.covered_centerline_km_measured??p.covered_protected_km_measured,p.covered_protected_km_measured,p.covered_zone_a_km_measured];if(groups.has(p.town)&&groups.get(p.town).some((v,i)=>v!==lengths[i]))throw Error('V1 packages in a town must use the same disjoint road group');groups.set(p.town,lengths);}
    for(const [town,[eligible,protectedKm,zoneA]] of groups){totals.eligible+=eligible*rates[town];totals.all+=protectedKm*rates[town];totals.zoneA+=zoneA*rates[town];}
    for(const value of Object.values(totals))number(value,'baseline total');
    return {objective,baseline_rates:rates,baseline_totals_t_simulated:totals,local_caps:caps,plans,project_decisions:explain(plans,active,budget,towns,objective,caps,trace),greedy_trace:trace,sensitivity:includeSensitivity?sensitivity(projects,budget,towns,rates,objective,caps):null};
  }
  globalThis.SaltShieldV1={assess,evaluate};
})();
