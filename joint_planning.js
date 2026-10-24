/* Whole-cell road selection linked to equipment. Mirrors joint_planning.py.
   The DP is exact on conservative 10 m weights, not on unrounded road lengths. */
(() => {
  const EPS=1e-10,QUANTUM=.01;
  function number(v,label){if(typeof v!=='number'||!Number.isFinite(v)||v<0)throw Error('Invalid '+label);return v;}
  function allocate(cells,capacity,objective='zoneA'){
    number(capacity,'capacity');if(!['zoneA','all'].includes(objective))throw Error('Unsupported objective');
    const primary=objective==='zoneA'?'zone_a_km':'protected_km',secondary=objective==='zoneA'?'protected_km':'zone_a_km';
    const useful=cells.filter(c=>c[primary]>EPS||c[secondary]>EPS).sort((a,b)=>a.cell_id<b.cell_id?-1:a.cell_id>b.cell_id?1:0);
    const cap=capacity,bins=Math.max(0,Math.min(Math.floor((cap+EPS)/QUANTUM),useful.reduce((s,c)=>s+Math.max(1,Math.ceil((c.eligible_km-EPS)/QUANTUM)),0)));
    if(bins>100000)throw Error('Capacity state space exceeds the supported pilot size');
    const a=new Float64Array(bins+1),b=new Float64Array(bins+1),used=new Float64Array(bins+1),choices=[],weights=[];
    for(const cell of useful){
      const weight=Math.max(1,Math.ceil((cell.eligible_km-EPS)/QUANTUM)),row=new Uint8Array(bins+1);weights.push(weight);
      for(let j=bins;j>=weight;j--){
        const x=a[j-weight]+cell[primary],y=b[j-weight]+cell[secondary],z=used[j-weight]+cell.eligible_km;
        if(x>a[j]+EPS||(Math.abs(x-a[j])<=EPS&&(y>b[j]+EPS||(Math.abs(y-b[j])<=EPS&&z<used[j]-EPS)))){
          a[j]=x;b[j]=y;used[j]=z;row[j]=1;
        }
      }
      choices.push(row);
    }
    const selected=[];let j=bins,rounded=0;
    for(let i=useful.length-1;i>=0;i--)if(choices[i][j]){selected.push(useful[i]);j-=weights[i];rounded+=weights[i]*QUANTUM;}
    const sum=f=>selected.reduce((s,c)=>s+c[f],0),covered=sum('eligible_km');
    if(covered>cap+1e-6)throw Error('Road coverage exceeds service capacity');
    return {method:'CONSERVATIVE_10M_DP',capacity_km:cap,covered_road_km:covered,covered_protected_km:sum('protected_km'),covered_zone_a_km:sum('zone_a_km'),unused_capacity_km:Math.max(0,cap-covered),selected_cell_ids:selected.map(c=>c.cell_id).sort(),rounded_capacity_used_km:rounded};
  }
  function snapshot(projects,budget,towns,rates,effect,objective,caps,capacities){
    return {budget,effect,objective,towns,baseline_rates:Object.fromEntries(towns.map(t=>[t,rates[t]])),local_caps:Object.fromEntries(towns.map(t=>[t,caps[t]])),projects:[...projects].sort((a,b)=>a.project_id<b.project_id?-1:a.project_id>b.project_id?1:0).map(p=>({project_id:p.project_id,capital_cost_usd:p.capital_cost_usd,coverage_fraction_assumed:p.coverage_fraction_assumed,enabled:p.enabled??true,reduction_low:p.reduction_low,reduction_fraction:p.reduction_fraction,reduction_high:p.reduction_high,max_road_km_per_winter:capacities[p.project_id]}))};
  }
  function solve(projects,cells,capacities,budget,towns,effect='central',baseline=5,objective='zoneA',localCaps=null){
    const {active,rates,caps}=SaltShieldV1.evaluate(projects,budget,towns,effect,baseline,objective,localCaps);
    if(!capacities||Object.keys(capacities).length!==projects.length||projects.some(p=>!Object.hasOwn(capacities,p.project_id)))throw Error('Capacity IDs must match the projects');
    Object.values(capacities).forEach(v=>number(v,'service reach'));
    const totals=Object.fromEntries(towns.map(t=>[t,{eligible_km:0,protected_km:0,zone_a_km:0}])),seen=new Set();
    for(const c of cells){
      if(seen.has(c.cell_id)||!Object.hasOwn(totals,c.town))throw Error('Duplicate cell or unknown town');seen.add(c.cell_id);
      for(const field of ['eligible_km','protected_km','zone_a_km'])totals[c.town][field]+=number(c[field],'cell length');
      if(c.eligible_km<=0||c.zone_a_km>c.protected_km+1e-8||c.protected_km>c.eligible_km+1e-8)throw Error('Invalid nested cell lengths');
    }
    for(const p of active)for(const [measured,field] of [['covered_centerline_km_measured','eligible_km'],['covered_protected_km_measured','protected_km'],['covered_zone_a_km_measured','zone_a_km']])if(Math.abs(p[measured]-totals[p.town][field])>1e-6)throw Error('Project coverage does not match the frozen road cells');
    const profiles=active.map(p=>{
      const allocation=allocate(cells.filter(c=>c.town===p.town),Math.min(capacities[p.project_id],totals[p.town].eligible_km*p.coverage_fraction_assumed),objective),factor=rates[p.town]*p.active_reduction;
      const profile={...p,allocation,service_reach_km_assumed:capacities[p.project_id],avoided_zone_a_tonnes_simulated:allocation.covered_zone_a_km*factor,avoided_all_zones_tonnes_simulated:allocation.covered_protected_km*factor,avoided_all_eligible_tonnes_simulated:allocation.covered_road_km*factor,baseline_tonnes_simulated:allocation.covered_road_km*rates[p.town],actual_coverage_fraction:totals[p.town].eligible_km?allocation.covered_road_km/totals[p.town].eligible_km:0,parameter_status:'SIMULATED service reach, price, baseline and effect; measured selected road-cell geometry',enabled:p.enabled!==false&&allocation.selected_cell_ids.length>0};
      for(const field of ['avoided_zone_a_tonnes_simulated','avoided_all_zones_tonnes_simulated','avoided_all_eligible_tonnes_simulated'])number(profile[field],'derived reduction');return profile;
    });
    const independent=SaltShield.solve(profiles,budget,towns,caps,false,objective),empty={cost:0,zoneA:0,all:0,eligible:0,selected:[],unspent:budget,townsSelected:0,feasibleCombinations:1};
    const plans={statusQuo:empty,independent,greedy:SaltShieldV1.greedyPlan(profiles,budget,objective).result,pooled:SaltShield.solve(profiles,budget,towns,null,false,objective),participation:SaltShield.solve(profiles,budget,towns,null,true,objective),equalSpend:SaltShield.solve(profiles,independent.cost,towns,null,false,objective),equalSpendParticipation:SaltShield.solve(profiles,independent.cost,towns,null,true,objective)};
    for(const result of Object.values(plans)){
      if(result===null)continue;
      for(const field of ['covered_road_km','covered_zone_a_km','covered_protected_km','capacity_km'])result[field]=result.selected.reduce((s,p)=>s+p.allocation[field],0);
      result.selected_cell_ids=result.selected.flatMap(p=>p.allocation.selected_cell_ids).sort();
      if(new Set(result.selected_cell_ids).size!==result.selected_cell_ids.length)throw Error('A road cell was assigned twice');
      const uniform={zoneA:0,all:0,eligible:0,covered_road_km:0};
      for(const p of result.selected){const t=totals[p.town],share=t.eligible_km?p.allocation.capacity_km/t.eligible_km:0,factor=share*rates[p.town]*p.active_reduction;uniform.zoneA+=t.zone_a_km*factor;uniform.all+=t.protected_km*factor;uniform.eligible+=t.eligible_km*factor;uniform.covered_road_km+=p.allocation.capacity_km;}
      result.uniform_same_equipment=uniform;
    }
    return {input_snapshot:snapshot(projects,budget,towns,rates,effect,objective,caps,capacities),profiles,plans,method:'CONSERVATIVE_10M_DP',quantum_km:QUANTUM,participation_definition:'At least one enabled package with nonempty eligible road-cell coverage in every town'};
  }
  const stable=v=>Array.isArray(v)?v.map(stable):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])])):v;
  const matches=(reference,input)=>JSON.stringify(stable(reference))===JSON.stringify(stable(input));
  function assessReach(projects,cells,capacities,budget,towns,effect='central',baseline=5,objective='zoneA',localCaps=null){
    if(projects.some(p=>!['CAL','BRINE'].includes(p.project_type)))throw Error('Reach checks support CAL and BRINE packages only');
    const base=solve(projects,cells,capacities,budget,towns,effect,baseline,objective,localCaps),byId=new Map(cells.map(c=>[c.cell_id,c])),cases=[];
    for(const cal of [.75,1,1.25])for(const brine of [.75,1,1.25]){
      const reach=Object.fromEntries(projects.map(p=>[p.project_id,capacities[p.project_id]*(p.project_type==='CAL'?cal:brine)]));
      const result=cal===1&&brine===1?base:solve(projects,cells,reach,budget,towns,effect,baseline,objective,localCaps),plans={};
      for(const [policy,r] of Object.entries(result.plans)){
        const original=base.plans[policy];if(r===null){plans[policy]=null;continue;}
        const originalIds=new Set(original?.selected_cell_ids??[]),retained=r.selected_cell_ids.filter(cid=>originalIds.has(cid)).reduce((s,cid)=>s+byId.get(cid).eligible_km,0),ids=r.selected.map(p=>p.project_id).sort();
        plans[policy]={...Object.fromEntries(['cost','zoneA','all','eligible','covered_road_km','townsSelected','selected_cell_ids'].map(k=>[k,r[k]])),selected_ids:ids,same_equipment_as_current:original?matches(ids,original.selected.map(p=>p.project_id).sort()):null,retained_base_road_km:retained,retained_base_road_fraction:original?.covered_road_km>0?retained/original.covered_road_km:null};
      }
      cases.push({case_id:'CAL'+String(Math.round(cal*100)).padStart(3,'0')+'_BRINE'+String(Math.round(brine*100)).padStart(3,'0'),cal_multiplier:cal,brine_multiplier:brine,capacities:reach,plans});
    }
    const summaries={},selection=[];
    for(const policy of Object.keys(base.plans)){
      const feasible=cases.map(c=>c.plans[policy]).filter(r=>r!==null),retention=feasible.map(r=>r.retained_base_road_fraction).filter(v=>v!==null);
      summaries[policy]={feasible_cases:feasible.length,matching_equipment_cases:feasible.filter(r=>r.same_equipment_as_current===true).length,objective_t_low:feasible.length?Math.min(...feasible.map(r=>r[objective])):null,objective_t_high:feasible.length?Math.max(...feasible.map(r=>r[objective])):null,retained_road_fraction_low:retention.length?Math.min(...retention):null,retained_road_fraction_high:retention.length?Math.max(...retention):null};
      for(const p of projects)selection.push({policy,project_id:p.project_id,selected_cases:feasible.filter(r=>r.selected_ids.includes(p.project_id)).length,feasible_cases:feasible.length});
    }
    return {input_snapshot:base.input_snapshot,case_count:cases.length,cases,summaries,selection,interpretation:'Nine deterministic reach cases, not probabilities or confidence intervals. CAL and BRINE service reach each vary independently by -25%, 0%, +25%. Budget, prices, effects, baseline and coverage ceilings stay fixed. Equipment and whole cells are re-optimized in each case. Retention is measured baseline assigned road length that remains assigned, regardless of package. No unrounded optimality claim is made.'};
  }
  globalThis.SaltShieldJoint={allocate,solve,matches,assessReach};
})();
