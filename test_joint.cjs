/* Cross-language parity runs against the actual measured road cells. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),cp=require('node:child_process'),assert=require('node:assert/strict');
function run(python='python3'){
  const raw=cp.execFileSync(python,[path.join(__dirname,'joint_parity_fixtures.py')],{cwd:__dirname,encoding:'utf8',maxBuffer:12e6,timeout:120000});
  const fixtures=JSON.parse(raw),context={};vm.createContext(context);
  for(const file of ['simulation.js','planning_v1.js','joint_planning.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,file),'utf8'),context);
  let policyChecks=0,profileChecks=0,reachPolicyChecks=0;const timings=[],reachTimings=[];
  function near(a,b,label){assert.ok(Math.abs(a-b)<1e-6,label+': '+a+' != '+b);}
  for(const f of fixtures.cases){
    const start=performance.now(),actual=context.SaltShieldJoint.solve(f.projects,fixtures.cells,f.capacities,f.budget,f.towns,f.effect,f.baseline,f.objective,f.local_caps);timings.push(performance.now()-start);
    for(const [policy,expected] of Object.entries(f.expected.plans)){
      const r=actual.plans[policy];assert.equal(r===null,expected===null,f.name+'/'+policy);if(r===null)continue;
      for(const field of ['cost','zoneA','all','eligible','covered_road_km','covered_zone_a_km','covered_protected_km','capacity_km'])near(r[field],expected[field],f.name+'/'+policy+'/'+field);
      assert.equal(JSON.stringify(r.selected.map(p=>p.project_id).sort()),JSON.stringify(expected.selected.map(p=>p.project_id).sort()),f.name+'/'+policy+'/equipment');
      assert.equal(JSON.stringify(r.selected_cell_ids),JSON.stringify(expected.selected_cell_ids),f.name+'/'+policy+'/cells');policyChecks++;
    }
    for(let i=0;i<actual.profiles.length;i++){
      const a=actual.profiles[i],b=f.expected.profiles[i];assert.equal(JSON.stringify(a.allocation.selected_cell_ids),JSON.stringify(b.allocation.selected_cell_ids));
      near(a.avoided_zone_a_tonnes_simulated,b.avoided_zone_a_tonnes_simulated,f.name+'/profile');profileChecks++;
    }
    assert.ok(context.SaltShieldJoint.matches(f.expected.input_snapshot,actual.input_snapshot));
    const changed=JSON.parse(JSON.stringify(actual.input_snapshot));changed.projects[0].max_road_km_per_winter+=.001;assert.ok(!context.SaltShieldJoint.matches(changed,actual.input_snapshot));
    if(f.expected_reach){
      const began=performance.now(),check=context.SaltShieldJoint.assessReach(f.projects,fixtures.cells,f.capacities,f.budget,f.towns,f.effect,f.baseline,f.objective,f.local_caps);reachTimings.push(performance.now()-began);
      assert.equal(check.case_count,9);assert.equal(check.cases.length,9);
      for(let i=0;i<9;i++)for(const [policy,expected] of Object.entries(f.expected_reach.cases[i].plans)){
        const a=check.cases[i].plans[policy];assert.equal(a===null,expected===null);if(a===null)continue;
        for(const field of ['cost','zoneA','all','eligible','covered_road_km','retained_base_road_km'])near(a[field],expected[field],f.name+'/reach/'+policy+'/'+field);
        assert.equal(JSON.stringify(a.selected_ids),JSON.stringify(expected.selected_ids));assert.equal(JSON.stringify(a.selected_cell_ids),JSON.stringify(expected.selected_cell_ids));assert.equal(a.same_equipment_as_current,expected.same_equipment_as_current);
        if(expected.retained_base_road_fraction===null)assert.equal(a.retained_base_road_fraction,null);else near(a.retained_base_road_fraction,expected.retained_base_road_fraction,'retention');reachPolicyChecks++;
      }
      for(const [policy,s] of Object.entries(f.expected_reach.summaries))for(const [key,value] of Object.entries(s)){if(value===null)assert.equal(check.summaries[policy][key],null);else near(check.summaries[policy][key],value,policy+'/'+key);}
      assert.equal(JSON.stringify(check.selection),JSON.stringify(f.expected_reach.selection));
    }
  }
  const first=fixtures.cases[0];for(const value of [-1,NaN,Infinity])assert.throws(()=>context.SaltShieldJoint.solve(first.projects,fixtures.cells,{...first.capacities,[first.projects[0].project_id]:value},first.budget,first.towns));
  const report={status:'PASS',cases:fixtures.cases.length,policy_checks:policyChecks,profile_checks:profileChecks,reach_policy_checks:reachPolicyChecks,max_browser_engine_ms:Math.round(Math.max(...timings)),max_reach_check_ms:Math.round(Math.max(...reachTimings)),method:'Conservative 10 m whole-cell DP and nine-case reach checks, checked against Python; saved-input unrounded SciPy comparisons are separate',source_sha256:JSON.parse(fs.readFileSync(path.join(__dirname,'results/joint_planning.json'))).source_sha256};
  fs.writeFileSync(path.join(__dirname,'results/joint_validation.json'),JSON.stringify(report,null,2)+'\n');return report;
}
module.exports={run};if(require.main===module)try{console.log(JSON.stringify(run(process.argv[2]||'python3'),null,2));}catch(err){console.error(err);process.exitCode=1;}
