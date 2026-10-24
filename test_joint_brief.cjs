/* Test the actual shareable artifact and the common browser/file renderer. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function run(){
  const read=name=>fs.readFileSync(path.join(__dirname,name),'utf8'),data=JSON.parse(read('results/joint_planning.json')),planning=JSON.parse(read('results/planning_v1.json')),context={};vm.createContext(context);
  for(const name of ['simulation.js','planning_v1.js','joint_planning.js','joint_brief.js'])vm.runInContext(read(name),context);
  const built=require('./build_joint_brief.cjs').run(),html=fs.readFileSync(built.output,'utf8'),checks=[];
  assert.ok(html.startsWith('<!doctype html>'));assert.ok(html.includes('lang="en"'));assert.ok(!/<script|<iframe|<link[^>]*stylesheet|<img[^>]*src="https?:/i.test(html));checks.push('standalone_english_artifact_without_external_assets_or_scripts');
  const tags=html.match(/<path class="joint-cell"[^>]*>/g);assert.equal(tags.length,data.cells.length);
  const selected=new Set(data.default.plans.pooled.selected_cell_ids);
  for(const tag of tags){const id=tag.match(/data-cell="([^"]+)"/)[1];assert.ok(tag.includes('fill="'+(selected.has(id)?'#007aff':'#e1e6e2')+'"'));}checks.push('all_map_cells_match_saved_pooled_assignment');
  assert.ok(html.includes('60.68 t'));assert.ok(html.includes('5 retain the current equipment portfolio'));for(const hash of Object.values(data.source_sha256))assert.ok(html.includes(hash));checks.push('saved_metrics_stability_and_full_source_hashes_present');
  const i=data.default.input_snapshot,reach=Object.fromEntries(i.projects.map(p=>[p.project_id,p.max_road_km_per_winter]));
  const changed=context.SaltShieldJoint.solve(planning.projects,data.cells,reach,45000,i.towns,i.effect,i.baseline_rates,i.objective);
  const output=context.SaltShieldJointBrief.render({scenario:changed,policy:'pooled',data,sensitivity:data.reach_sensitivity});
  assert.ok(output.includes(changed.plans.pooled.zoneA.toFixed(2)+' t'));assert.ok(output.includes('No stability claim'));assert.ok(output.includes('benchmark inactive'));assert.ok(!output.includes('60.68 t'));checks.push('changed_budget_cannot_reuse_saved_stability_or_certificate');
  const noInvestment=context.SaltShieldJointBrief.render({scenario:data.default,policy:'statusQuo',data,sensitivity:data.reach_sensitivity});assert.ok(noInvestment.includes('No equipment selected'));assert.ok(!noInvestment.includes('NaN'));checks.push('zero_investment_has_valid_empty_assignment_and_undefined_retention');
  const zero=context.SaltShieldJoint.solve(planning.projects,data.cells,reach,0,i.towns);
  assert.throws(()=>context.SaltShieldJointBrief.render({scenario:zero,policy:'participation',data}));checks.push('infeasible_policy_cannot_create_brief');
  const poisoned=JSON.parse(JSON.stringify(data.default));poisoned.plans.pooled.selected[0].project_type='<img src=x onerror="alert(1)">';
  const escaped=context.SaltShieldJointBrief.render({scenario:poisoned,policy:'pooled',data,sources:{bad:'javascript:alert(1)'}});
  assert.ok(escaped.includes('&lt;img'));assert.ok(!escaped.includes('<img'));assert.ok(!escaped.includes('javascript:'));checks.push('text_is_escaped_and_unsafe_source_link_is_filtered');
  return {status:'PASS',checks,brief_bytes:built.bytes};
}
module.exports={run};if(require.main===module)try{console.log(JSON.stringify(run(),null,2));}catch(error){console.error(error);process.exitCode=1;}
