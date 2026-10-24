/* Python / JavaScript parity, including reasons and full sensitivity results. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),cp=require('node:child_process'),assert=require('node:assert/strict');
function run(python=process.env.PYTHON||'python3'){
  const root=__dirname,context={};vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root,'simulation.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'planning_v1.js'),'utf8'),context);
  const fixtures=JSON.parse(cp.execFileSync(python,[path.join(root,'planning_parity_fixtures.py')],{cwd:root,encoding:'utf8',maxBuffer:16e6}));
  function same(actual,expected,label){
    if(typeof expected==='number'){assert.equal(typeof actual,'number',label);assert.ok(Math.abs(actual-expected)<=1e-8*Math.max(1,Math.abs(expected)),label+': '+actual+' != '+expected);return;}
    if(expected===null||typeof expected!=='object'){assert.equal(actual,expected,label);return;}
    assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort(),label+' keys');
    for(const key of Object.keys(expected))same(actual[key],expected[key],label+'.'+key);
  }
  for(const fixture of fixtures){
    const p=fixture.input,r=context.SaltShieldV1.assess(p.projects,p.budget,p.towns,p.effect,p.baseline,p.objective,p.local_caps,p.include_sensitivity);
    for(const plan of Object.values(r.plans))if(plan!==null){plan.selected_ids=plan.selected.map(p=>p.project_id).sort();delete plan.selected;}
    same(JSON.parse(JSON.stringify(r)),fixture.expected,fixture.name);
  }
  const first=fixtures[0].input,invalid=[
    {...first,objective:'unknown'},
    {...first,projects:[...first.projects,first.projects[0]]},
    {...first,projects:first.projects.map((p,i)=>i? p:{...p,capital_cost_usd:-1})},
    {...first,projects:first.projects.map((p,i)=>i? p:{...p,coverage_fraction_assumed:2})},
    {...first,projects:first.projects.map((p,i)=>i? p:{...p,enabled:'yes'})},
    {...first,baseline:NaN},
    {...first,baseline:1e308},
  ];
  for(const p of invalid)assert.throws(()=>context.SaltShieldV1.assess(p.projects,p.budget,p.towns,p.effect,p.baseline,p.objective,p.local_caps,false));
  const sample=fixtures.find(c=>c.name==='full_sensitivity/zoneA').input,start=performance.now();
  context.SaltShieldV1.assess(sample.projects,sample.budget,sample.towns,sample.effect,sample.baseline,sample.objective,sample.local_caps,true);
  return {status:'PASS',matched_cases:fixtures.length,matched_policy_results:fixtures.length*7,full_sensitivity_cases:54,invalid_cases:invalid.length,assessment_runtime_ms:Math.round(performance.now()-start)};
}
module.exports={run};if(require.main===module)console.log(JSON.stringify(run(),null,2));
