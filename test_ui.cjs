/* Unit tests for control validation and scenario import/export, without a browser. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

async function run() {
  const root = __dirname;
  const analysis = JSON.parse(fs.readFileSync(path.join(root, 'results/analysis.json'), 'utf8'));
  analysis.phase2 = JSON.parse(fs.readFileSync(path.join(root, 'results/phase2_analysis.json'), 'utf8'));
  analysis.planning=JSON.parse(fs.readFileSync(path.join(root,'results/planning_v1.json'),'utf8'));
  analysis.joint=JSON.parse(fs.readFileSync(path.join(root,'results/joint_planning.json'),'utf8'));
  const spatial = JSON.parse(fs.readFileSync(path.join(root, 'results/spatial_priority.json'), 'utf8'));
  const elements = new Map();
  function element(value = '') {
    let inputValue = String(value);
    const classes=new Set();
    return { get value() { return inputValue; }, set value(v) { inputValue = String(v); }, checked: true, hidden: false, disabled: false, textContent: '', innerHTML: '', style: {}, dataset:{}, attributes:{}, listeners: {}, classList:{toggle(key,on){if(on)classes.add(key);else classes.delete(key);},contains(key){return classes.has(key);}}, setAttribute(k,v){this.attributes[k]=v;},removeAttribute(k){delete this.attributes[k];},focus(){this.focused=true;},dispatchEvent(e){this.listeners[e.type]?.(e);},addEventListener(type, fn) { this.listeners[type] = fn; } };
  }
  for (const id of ['budget','intensity','effect','planner-error','result-output','export','caps','ind-benefit','ind-cost','ind-projects','ind-bar','pool-benefit','pool-cost','pool-projects','pool-bar','explanation','participation-summary','participation-projects','equal-spend','equal-spend-participation','project-editor','reset-scenario','import-status','import-scenario']) elements.set(id, element());
  const get = id => elements.get(id);
  for(const id of ['objective','ind-benefit-label','pool-benefit-label','comparison-export','baseline-totals','baseline-comparison','baseline-comparison-note','decision-policy','project-decisions','stability-summary','project-stability','sensitivity-export'])elements.set(id,element());
  get('objective').value='zoneA';get('decision-policy').value='pooled';
  elements.set('experience-view',element());elements.set('experience-heading',element());
  for(const id of ['joint-policy','joint-json','joint-csv','joint-reset','joint-draft-status','joint-capacity-editor','joint-error','joint-output','joint-benefit-label','joint-cost','joint-unspent','joint-length','joint-capacity','joint-benefit','joint-summary','joint-assignments','joint-uniform','joint-benchmark','joint-comparison'])elements.set(id,element());
  get('joint-policy').value='pooled';
  for(const id of ['joint-brief','joint-map','joint-reach-review','joint-reach-run','joint-reach-csv','joint-reach-status','joint-reach-output','joint-reach-table','joint-reach-selection'])elements.set(id,element());
  for(const r of analysis.joint.capacities)elements.set('joint-reach-'+r.project_id,element(r.max_road_km_per_winter));
  const viewNames=['overview','investments','coverage','evidence'];
  for(const id of ['view-title','brief-policy','brief-content','download-brief','print-brief','appearance','draft-status',...viewNames.map(v=>v+'-view'),...viewNames.map(v=>v+'-heading')])elements.set(id,element());
  get('brief-policy').value='participation';
  const navigation=viewNames.map(v=>Object.assign(element(),{dataset:{view:v}}));
  const storage=new Map();let printed=false;
  get('budget').value = '75000'; get('intensity').value = '5'; get('effect').value = 'central';
  for (const id of ['spatial-fraction','spatial-method','spatial-export','spatial-summary','spatial-table']) elements.set(id, element());
  get('spatial-fraction').value = '.25'; get('spatial-method').value = 'integer';
  const mapCells = spatial.cells.map(c => ({dataset:{cell:c.cell_id},style:{}}));
  const jointCells=spatial.cells.map(c=>({dataset:{cell:c.cell_id},style:{}}));
  const rows = new Map(analysis.phase2.projects.map(p => {
    const fields = new Map([['cost', element(String(p.capital_cost_usd))], ['coverage', element('100')], ['enabled', element()]]);
    return [p.project_id, { fields, querySelector(selector) { return fields.get(selector.match(/data-field="([^"]+)"/)[1]); } }];
  }));
  let exported;
  const context = {
    document: {
      getElementById: get,
      querySelector(selector) { if(selector.startsWith('[data-view='))return navigation.find(n=>n.dataset.view===selector.match(/data-view="([^"]+)"/)[1]);return rows.get(selector.match(/data-project="([^"]+)"/)[1]); },
      querySelectorAll(selector) { return selector === '.priority-cell' ? mapCells : selector==='.joint-cell'?jointCells:(selector==='[data-view]'?navigation:[]); },
      documentElement:{dataset:{}},
      createElement() { return { click() {} }; },
    },
    Blob,Event,
    localStorage:{getItem(k){return storage.get(k);},setItem(k,v){storage.set(k,v);}},
    print(){printed=true;},
    URL: { createObjectURL(blob) { exported = blob; return 'blob:test'; }, revokeObjectURL() {} },
  };
  vm.createContext(context);
  // Execute the shipped report, so integration/embedding failures are caught too.
  const report = fs.readFileSync(path.join(root, 'results/SaltShield_Wachusett.html'), 'utf8');
  get('joint-map').innerHTML=report.match(/id="joint-map">([\s\S]*?)<\/div>/)[1];
  const scripts = [...report.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  assert.equal(scripts.length, 4);
  vm.runInContext(scripts.join('\n'), context);
  assert.equal(get('pool-benefit').textContent, '84.84 t');
  const checks = ['default_results'];

  rows.get('HOLDEN_BRINE').fields.get('coverage').value = '50';
  context.update();
  assert.notEqual(get('pool-benefit').textContent, '84.84 t'); checks.push('coverage_updates_results');

  rows.get('HOLDEN_CAL').fields.get('cost').value = '';
  context.update();
  assert.equal(get('result-output').hidden, true); assert.equal(get('export').disabled, true);
  assert.ok(get('planner-error').textContent.length); checks.push('invalid_input_hides_stale_results');

  get('reset-scenario').listeners.click();
  assert.equal(get('pool-benefit').textContent, '84.84 t'); assert.equal(get('export').disabled, false); checks.push('reset_restores_defaults');

  for (const type of ['CAL', 'BRINE']) rows.get('WEST_BOYLSTON_' + type).fields.get('enabled').checked = false;
  context.update();
  assert.match(get('participation-summary').textContent, /No feasible plan/); checks.push('disabled_town_infeasibility_visible');

  get('reset-scenario').listeners.click();
  get('budget').value = '45000'; context.update();
  assert.match(get('equal-spend').textContent, /52\.56 t/);
  assert.match(get('equal-spend-participation').textContent, /41\.54 t/); checks.push('participation_tradeoff_visible');

  get('export').listeners.click();
  const payload = JSON.parse(await exported.text());
  assert.equal(payload.schema_version, 2); assert.equal(payload.inputs.budget, 45000);
  assert.equal(payload.source_sha256, analysis.phase2.evidence.source.sha256); checks.push('export_contains_evidence_and_inputs');

  get('reset-scenario').listeners.click();
  const input = get('import-scenario');
  async function load(value) { const data = JSON.stringify(value); input.files = [{ size: Buffer.byteLength(data), text: async () => data }]; await input.listeners.change({ target: input }); }
  // Imported length values cannot change immutable measured geometry.
  payload.inputs.projects[0].covered_zone_a_km_measured = 999999;
  await load(payload);
  assert.equal(get('budget').value, '45000');
  assert.equal(get('pool-benefit').textContent, '52.56 t'); checks.push('import_roundtrip_ignores_geometry_tampering');

  const invalid = JSON.parse(JSON.stringify(payload)); invalid.source_sha256 = 'wrong';
  await load(invalid); assert.match(get('import-status').textContent, /Import failed/); assert.equal(get('pool-benefit').textContent, '52.56 t'); checks.push('wrong_evidence_snapshot_rejected');

  const missing = JSON.parse(JSON.stringify(payload)); delete missing.inputs.projects[0].enabled;
  await load(missing); assert.match(get('import-status').textContent, /Import failed/); checks.push('incomplete_project_import_rejected');

  assert.match(get('spatial-summary').textContent, /39\.56 km/);
  assert.match(get('spatial-summary').textContent, /20\.77 km/);
  assert.ok(mapCells.some(c => c.style.fill === '#176d63')); checks.push('spatial_default_and_map_render');

  get('spatial-fraction').value = '1'; get('spatial-fraction').listeners.change();
  assert.match(get('spatial-summary').textContent, /83\.07 km/);
  assert.ok(mapCells.every(c => c.style.fill === '#176d63')); checks.push('spatial_full_capacity_covers_all');

  get('spatial-fraction').value = '.25'; get('spatial-method').value = 'uniform'; get('spatial-method').listeners.change();
  assert.ok(mapCells.every(c => Math.abs(Number(c.style.fillOpacity)-(.18+.82*.25))<1e-10));
  assert.match(get('spatial-summary').textContent, /Uniform coverage/); checks.push('uniform_map_uses_fractional_shading');

  get('spatial-method').value = 'integer'; get('spatial-method').listeners.change(); get('spatial-export').listeners.click();
  const csv = await exported.text();
  assert.ok(csv.includes('road_source_sha256'));assert.ok(csv.includes(spatial.source_sha256['road_segments.geojson']));
  assert.ok(csv.includes('"integer"'));assert.ok(!csv.includes('"uniform"'));checks.push('spatial_csv_matches_active_case');

  navigation[1].listeners.click();assert.equal(get('investments-view').hidden,false);assert.equal(get('overview-view').hidden,true);assert.equal(get('view-title').textContent,'Investments');
  navigation[1].listeners.keydown({key:'ArrowRight',preventDefault(){}});assert.equal(get('coverage-view').hidden,false);assert.equal(navigation[2].attributes['aria-current'],'page');checks.push('workspace_navigation_and_keyboard');

  get('appearance').listeners.click();assert.equal(context.document.documentElement.dataset.theme,'dark');assert.equal(storage.get('saltshield-appearance'),'dark');
  get('appearance').listeners.click();assert.equal(context.document.documentElement.dataset.theme,'light');checks.push('appearance_switch_persists');

  get('reset-scenario').listeners.click();assert.match(get('brief-content').innerHTML,/84\.84 t/);assert.match(get('brief-content').innerHTML,/39\.56 km/);
  get('budget').value='45000';context.update();assert.match(get('brief-content').innerHTML,/41\.54 t/);checks.push('brief_tracks_investment_inputs');
  get('spatial-fraction').value='.5';get('spatial-fraction').listeners.change();assert.match(get('brief-content').innerHTML,/63\.62 km/);checks.push('brief_tracks_spatial_case');

  get('brief-policy').value='pooled';get('brief-policy').listeners.change();assert.match(get('brief-content').innerHTML,/52\.56 t/);
  get('download-brief').listeners.click();const brief=await exported.text();assert.ok(brief.startsWith('<!doctype html>'));assert.ok(brief.includes('lang="en"'));assert.ok(brief.includes('52.56 t'));assert.ok(brief.includes('illustrative'));assert.ok(!brief.includes('<script>'));checks.push('downloadable_brief_matches_selected_policy');
  get('print-brief').listeners.click();assert.equal(printed,true);checks.push('print_uses_current_brief');

  get('budget').value='';context.update();assert.equal(get('download-brief').disabled,true);assert.equal(get('print-brief').disabled,true);assert.ok(!get('brief-content').innerHTML.includes('52.56 t'));checks.push('invalid_inputs_clear_brief');
  get('reset-scenario').listeners.click();get('brief-policy').value='participation';get('budget').value='30000';context.update();assert.match(get('brief-content').innerHTML,/No feasible plan/);assert.equal(get('download-brief').disabled,true);checks.push('infeasible_policy_cannot_export_brief');

  assert.ok(!/[\u3400-\u9fff]/.test(report));checks.push('entire_offline_report_is_english');

  get('reset-scenario').listeners.click();get('budget').value='60000';context.update();
  get('spatial-fraction').value='.5';get('spatial-fraction').listeners.change();
  const savedDraft=JSON.parse(storage.get('saltshield-draft'));assert.equal(savedDraft.inputs.budget,60000);assert.equal(savedDraft.coverage.fraction,'0.5');
  get('budget').value='';context.update();assert.equal(JSON.parse(storage.get('saltshield-draft')).inputs.budget,60000);checks.push('autosave_keeps_last_valid_inputs');

  // Simulate fresh script execution over freshly reset controls, using only the
  // browser-local draft as persisted state. Geometry tampering must be ignored.
  function reload(draft){
    storage.set('saltshield-draft',JSON.stringify(draft));get('budget').value='75000';get('intensity').value='5';get('effect').value='central';get('spatial-fraction').value='0.25';get('spatial-method').value='integer';get('brief-policy').value='participation';
    for(const p of analysis.phase2.projects){const rr=rows.get(p.project_id);rr.fields.get('cost').value=p.capital_cost_usd;rr.fields.get('coverage').value='100';rr.fields.get('enabled').checked=true;}
    const fresh={document:context.document,Blob,Event,URL:context.URL,localStorage:context.localStorage};vm.createContext(fresh);vm.runInContext(scripts.join('\n'),fresh);return fresh;
  }
  savedDraft.inputs.projects[0].covered_zone_a_km_measured=999999;reload(savedDraft);
  assert.equal(get('budget').value,'60000');assert.equal(get('spatial-fraction').value,'0.5');assert.match(get('brief-content').innerHTML,/63\.62 km/);assert.ok(!get('brief-content').innerHTML.includes('999999'));checks.push('reload_restores_draft_without_geometry_mutation');
  const wrongDraft=JSON.parse(JSON.stringify(savedDraft));wrongDraft.evidence_sha256='wrong';reload(wrongDraft);
  assert.equal(get('budget').value,'75000');assert.match(get('draft-status').textContent,/not restored/);checks.push('draft_from_other_evidence_snapshot_rejected');

  assert.match(get('baseline-comparison').innerHTML,/No new investment/);assert.match(get('baseline-comparison').innerHTML,/Benefit \/ cost heuristic/);
  assert.match(get('baseline-comparison-note').textContent,/same objective/);assert.match(get('baseline-totals').textContent,/1,?476\.20 t|1476\.20 t/);checks.push('four_baselines_and_no_false_gain_claim');
  get('decision-policy').value='independent';get('decision-policy').listeners.change();assert.match(get('project-decisions').innerHTML,/independent budget ceiling/);checks.push('project_exclusion_reasons_visible');
  assert.match(get('stability-summary').textContent,/27 assumed cases/);assert.match(get('project-stability').innerHTML,/Changes with assumptions|Selected in every|Never selected/);checks.push('sensitivity_selection_patterns_visible');

  get('objective').value='all';get('objective').listeners.change();assert.equal(get('pool-benefit-label').textContent,'Modeled A/B/C reduction');assert.match(get('brief-content').innerHTML,/A\/B\/C objective/);checks.push('objective_switch_updates_cards_and_brief');
  get('comparison-export').listeners.click();const comparisonCsv=await exported.text();assert.ok(comparisonCsv.includes('"statusQuo"'));assert.ok(comparisonCsv.includes('"greedy"'));assert.ok(comparisonCsv.includes('parameter_fingerprint'));checks.push('four_baseline_comparison_csv_export');
  get('sensitivity-export').listeners.click();const sensitivityCsv=await exported.text();assert.equal(sensitivityCsv.trim().split('\n').length,190);checks.push('sensitivity_csv_contains_189_policy_cases');
  get('export').listeners.click();const allScenario=JSON.parse(await exported.text());assert.equal(allScenario.inputs.objective,'all');assert.equal(allScenario.assessment.sensitivity.case_count,27);assert.equal(allScenario.parameter_fingerprint,analysis.planning.parameter_fingerprint);
  get('reset-scenario').listeners.click();await load(allScenario);assert.equal(get('objective').value,'all');checks.push('objective_and_assessment_export_roundtrip');
  allScenario.parameter_fingerprint='wrong';await load(allScenario);assert.match(get('import-status').textContent,/parameter snapshot does not match/);checks.push('changed_parameter_snapshot_import_rejected');
  get('brief-policy').value='statusQuo';get('brief-policy').listeners.change();assert.match(get('brief-content').innerHTML,/No equipment selected/);assert.ok(!get('download-brief').disabled);checks.push('current_state_brief_supported');
  get('reset-scenario').listeners.click();get('joint-reset').listeners.click();get('joint-policy').value='pooled';get('joint-policy').listeners.change();
  assert.equal(get('joint-benefit').textContent,analysis.joint.default.plans.pooled.zoneA.toFixed(2)+' t');assert.match(get('joint-benchmark').textContent,/unrounded primary optimum/);assert.ok(jointCells.some(c=>c.style.fill==='#007aff'));checks.push('joint_default_map_and_saved_input_benchmark');
  const reachProject=analysis.joint.default.plans.pooled.selected.find(p=>p.project_type==='BRINE').project_id;
  const before=get('joint-benefit').textContent;get('joint-reach-'+reachProject).value='0';get('joint-capacity-editor').listeners.input();assert.match(get('joint-benchmark').textContent,/benchmark inactive/);assert.notEqual(get('joint-benefit').textContent,before);checks.push('reach_changes_plan_and_invalidates_benchmark');
  get('joint-json').listeners.click();const linked=JSON.parse(await exported.text());assert.equal(linked.model,'CAPACITY_LINKED_WHOLE_CELLS');assert.equal(linked.saved_input_benchmark,null);assert.equal(linked.scenario.input_snapshot.projects.find(p=>p.project_id===reachProject).max_road_km_per_winter,0);checks.push('linked_export_contains_current_inputs_without_stale_certificate');
  get('joint-csv').listeners.click();const jointCsv=await exported.text();assert.ok(jointCsv.includes('planning_cells_sha256'));assert.ok(jointCsv.includes(analysis.joint.source_sha256['data/processed/planning_cells.geojson']));assert.equal(jointCsv.trim().split('\n').length,linked.scenario.plans.pooled.selected_cell_ids.length+1);checks.push('linked_csv_matches_assigned_cells');
  get('joint-reach-'+reachProject).value='';get('joint-capacity-editor').listeners.input();assert.equal(get('joint-output').hidden,true);assert.equal(get('joint-json').disabled,true);assert.ok(jointCells.every(c=>c.style.fill==='#e1e6e2'));checks.push('invalid_reach_clears_stale_plan_and_map');
  get('joint-reset').listeners.click();for(const r of analysis.joint.capacities)get('joint-reach-'+r.project_id).value='0';get('joint-policy').value='participation';get('joint-capacity-editor').listeners.input();assert.equal(get('joint-cost').textContent,'Infeasible');assert.equal(get('joint-csv').disabled,true);checks.push('zero_reach_cannot_satisfy_participation');
  get('joint-reset').listeners.click();get('joint-policy').value='pooled';get('budget').value='60000';context.update();assert.match(get('joint-benchmark').textContent,/benchmark inactive/);checks.push('investment_budget_change_invalidates_joint_certificate');
  get('budget').value='';context.update();assert.equal(get('joint-output').hidden,true);assert.equal(get('joint-json').disabled,true);checks.push('invalid_investments_clear_joint_outputs');
  get('reset-scenario').listeners.click();get('objective').value='all';get('objective').listeners.change();assert.equal(get('joint-benefit-label').textContent,'Modeled A/B/C reduction');assert.equal(get('joint-output').hidden,false);
  if(!analysis.joint.benchmarks.all.exact_plans)assert.match(get('joint-benchmark').textContent,/not certified/);checks.push('uncertified_objective_stays_available_without_optimality_claim');
  get('reset-scenario').listeners.click();get('joint-reach-HOLDEN_BRINE').value='19';get('joint-capacity-editor').listeners.input();const jointDraft=JSON.parse(storage.get('saltshield-joint-reach'));assert.equal(jointDraft.capacities.HOLDEN_BRINE,19);get('joint-reach-HOLDEN_BRINE').value='50';reload(JSON.parse(storage.get('saltshield-draft')));assert.equal(get('joint-reach-HOLDEN_BRINE').value,'19');checks.push('reach_restores_from_valid_device_draft');
  assert.ok(!/__JOINT_MAP__|__CAPACITY_ROWS__/.test(report));checks.push('linked_panel_has_no_unresolved_placeholders');
  get('reset-scenario').listeners.click();get('joint-reset').listeners.click();get('joint-policy').value='pooled';get('joint-policy').listeners.change();
  assert.match(get('joint-reach-status').textContent,/9 assumed cases/);assert.equal((get('joint-reach-table').innerHTML.match(/<tr>/g)||[]).length,10);assert.equal(get('joint-reach-csv').disabled,false);checks.push('saved_nine_case_reach_check_renders');
  get('joint-brief').listeners.click();const linkedBrief=await exported.text();assert.ok(linkedBrief.startsWith('<!doctype html>'));assert.ok(linkedBrief.includes('60.68 t'));assert.ok(linkedBrief.includes('<svg'));assert.ok(linkedBrief.includes('Nine assumed cases'));assert.ok(linkedBrief.includes(analysis.joint.source_sha256['data/processed/planning_cells.geojson']));assert.ok(!linkedBrief.includes('<script>'));checks.push('linked_brief_contains_map_inputs_reach_cases_and_sources');
  get('joint-reach-HOLDEN_BRINE').value='18';get('joint-capacity-editor').listeners.input();assert.equal(get('joint-reach-csv').disabled,true);assert.equal(get('joint-reach-table').innerHTML,'');
  get('joint-brief').listeners.click();assert.ok((await exported.text()).includes('No stability claim'));checks.push('changed_reach_clears_stale_stability_in_ui_and_brief');
  await get('joint-reach-run').listeners.click();assert.match(get('joint-reach-status').textContent,/9 assumed cases/);get('joint-json').listeners.click();const checkedJSON=JSON.parse(await exported.text());assert.equal(checkedJSON.reach_sensitivity.case_count,9);assert.equal(checkedJSON.reach_sensitivity.input_snapshot.projects.find(p=>p.project_id==='HOLDEN_BRINE').max_road_km_per_winter,18);checks.push('manual_reach_check_tracks_edited_inputs');
  get('joint-policy').value='independent';get('joint-policy').listeners.change();get('joint-reach-csv').listeners.click();const reachCSV=await exported.text();assert.equal(reachCSV.trim().split('\n').length,10);assert.ok(reachCSV.includes('"independent"'));assert.ok(!reachCSV.includes('"pooled"'));assert.ok(reachCSV.includes('base_input_snapshot_json'));checks.push('reach_csv_matches_selected_policy_and_input_snapshot');
  get('joint-reach-HOLDEN_BRINE').value='';get('joint-capacity-editor').listeners.input();assert.equal(get('joint-brief').disabled,true);assert.equal(get('joint-reach-csv').disabled,true);checks.push('invalid_reach_disables_brief_and_sensitivity_exports');
  get('joint-reset').listeners.click();get('budget').value='60000';get('budget').listeners.input();const pending=get('joint-reach-run').listeners.click();get('budget').value='45000';get('budget').listeners.input();await pending;assert.equal(get('joint-reach-csv').disabled,true);assert.match(get('joint-reach-status').textContent,/needs an update/);checks.push('input_change_cancels_pending_reach_check');
  get('reset-scenario').listeners.click();for(const r of analysis.joint.capacities)get('joint-reach-'+r.project_id).value='0';get('joint-policy').value='participation';get('joint-capacity-editor').listeners.input();await get('joint-reach-run').listeners.click();assert.match(get('joint-reach-status').textContent,/0 feasible/);assert.equal(get('joint-brief').disabled,true);checks.push('infeasible_participation_has_no_brief_or_false_stability');
  get('joint-reset').listeners.click();get('joint-policy').value='statusQuo';get('joint-policy').listeners.change();get('joint-brief').listeners.click();assert.ok((await exported.text()).includes('No equipment selected'));checks.push('linked_zero_investment_brief_is_valid');
  return { status: 'PASS', checks };
}

module.exports = { run };
if (require.main === module) run().then(r => console.log(JSON.stringify(r, null, 2))).catch(err => { console.error(err); process.exitCode = 1; });
