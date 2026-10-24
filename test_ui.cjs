/* Unit tests for control validation and scenario import/export, without a browser. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

async function run() {
  const root = __dirname;
  const analysis = JSON.parse(fs.readFileSync(path.join(root, 'results/analysis.json'), 'utf8'));
  analysis.phase2 = JSON.parse(fs.readFileSync(path.join(root, 'results/phase2_analysis.json'), 'utf8'));
  const elements = new Map();
  function element(value = '') {
    let inputValue = String(value);
    return { get value() { return inputValue; }, set value(v) { inputValue = String(v); }, checked: true, hidden: false, disabled: false, textContent: '', innerHTML: '', style: {}, listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; } };
  }
  for (const id of ['budget','intensity','effect','planner-error','result-output','export','caps','ind-benefit','ind-cost','ind-projects','ind-bar','pool-benefit','pool-cost','pool-projects','pool-bar','explanation','participation-summary','participation-projects','equal-spend','equal-spend-participation','project-editor','reset-scenario','import-status','import-scenario']) elements.set(id, element());
  const get = id => elements.get(id);
  get('budget').value = '75000'; get('intensity').value = '5'; get('effect').value = 'central';
  const rows = new Map(analysis.phase2.projects.map(p => {
    const fields = new Map([['cost', element(String(p.capital_cost_usd))], ['coverage', element('100')], ['enabled', element()]]);
    return [p.project_id, { fields, querySelector(selector) { return fields.get(selector.match(/data-field="([^"]+)"/)[1]); } }];
  }));
  let exported;
  const context = {
    document: {
      getElementById: get,
      querySelector(selector) { return rows.get(selector.match(/data-project="([^"]+)"/)[1]); },
      querySelectorAll() { return []; },
      createElement() { return { click() {} }; },
    },
    Blob,
    URL: { createObjectURL(blob) { exported = blob; return 'blob:test'; }, revokeObjectURL() {} },
  };
  vm.createContext(context);
  vm.runInContext('const ANALYSIS = ' + JSON.stringify(analysis) + ';\n' + fs.readFileSync(path.join(root, 'simulation.js'), 'utf8') + '\n' + fs.readFileSync(path.join(root, 'phase2_ui.js'), 'utf8'), context);
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
  assert.match(get('participation-summary').textContent, /无可行方案/); checks.push('disabled_town_infeasibility_visible');

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
  await load(invalid); assert.match(get('import-status').textContent, /导入失败/); assert.equal(get('pool-benefit').textContent, '52.56 t'); checks.push('wrong_evidence_snapshot_rejected');

  const missing = JSON.parse(JSON.stringify(payload)); delete missing.inputs.projects[0].enabled;
  await load(missing); assert.match(get('import-status').textContent, /导入失败/); checks.push('incomplete_project_import_rejected');
  return { status: 'PASS', checks };
}

module.exports = { run };
if (require.main === module) run().then(r => console.log(JSON.stringify(r, null, 2))).catch(err => { console.error(err); process.exitCode = 1; });
