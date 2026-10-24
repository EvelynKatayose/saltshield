/* Offline UI: geometry and evidence are immutable; scenario controls are assumptions. */
const towns = ANALYSIS.summary.map(s => s.town);
const money = v => '$' + v.toLocaleString('en-US', { maximumFractionDigits: 0 });
const tonnes = v => v.toFixed(2) + ' t';
const originalProjects = ANALYSIS.phase2.projects;
let current = null, currentInputs = null;
function niceTown(t) { return t.toLowerCase().replace(/\b\w/g, x => x.toUpperCase()); }
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, x => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[x])); }
function planRows(plan) {
  if (!plan) return '';
  return '<table><thead><tr><th>城镇</th><th>选择</th><th>投入</th></tr></thead><tbody>' + towns.map(t => {
    const p = plan.selected.find(x => x.town === t);
    return '<tr><td>' + escapeHtml(niceTown(t)) + '</td><td>' + (p ? escapeHtml(p.project_type) : '不投资') + '</td><td>' + money(p ? p.capital_cost_usd : 0) + '</td></tr>';
  }).join('') + '</tbody></table>';
}
function numericInput(input, label, max = Infinity) {
  const value = input.value.trim() === '' ? NaN : Number(input.value);
  if (!Number.isFinite(value) || value < 0 || value > max) throw new Error(label + '需要填写范围内的有效数字。');
  return value;
}
function inputs() {
  const budget = numericInput(document.getElementById('budget'), '预算');
  const intensity = numericInput(document.getElementById('intensity'), '基准强度');
  const effect = document.getElementById('effect').value;
  const projects = originalProjects.map(p => {
    const row = document.querySelector('[data-project="' + p.project_id + '"]');
    return { ...p,
      capital_cost_usd: numericInput(row.querySelector('[data-field="cost"]'), niceTown(p.town) + '成本'),
      coverage_fraction_assumed: numericInput(row.querySelector('[data-field="coverage"]'), niceTown(p.town) + '覆盖率', 100) / 100,
      enabled: row.querySelector('[data-field="enabled"]').checked,
      input_basis: 'SIMULATED_OR_UNVERIFIED_USER_INPUT',
    };
  });
  return { budget, intensity, effect, projects };
}
function update() {
  const error = document.getElementById('planner-error'), output = document.getElementById('result-output');
  try {
    currentInputs = inputs();
    current = SaltShield.compare(currentInputs.projects, currentInputs.budget, towns, currentInputs.effect, currentInputs.intensity);
    error.hidden = true; output.hidden = false; document.getElementById('export').disabled = false;
    const { independent: i, pooled: p, participation: f, equalSpend: e, equalSpendParticipation: ef } = current;
    document.getElementById('caps').textContent = '独立模式每镇上限 ' + money(currentInputs.budget / towns.length) + '；共享总上限 ' + money(currentInputs.budget) + '。所有项目成本与覆盖率保持一致。';
    for (const [key, result] of [['ind', i], ['pool', p]]) {
      document.getElementById(key + '-benefit').textContent = tonnes(result.zoneA);
      document.getElementById(key + '-cost').textContent = money(result.cost);
      document.getElementById(key + '-projects').innerHTML = planRows(result);
      document.getElementById(key + '-bar').style.width = result.zoneA / Math.max(i.zoneA, p.zoneA, 1) * 100 + '%';
    }
    document.getElementById('explanation').textContent = '共享模式多减少 ' + tonnes(p.zoneA - i.zoneA) + ' 的 Zone A 模拟施盐，同时多投入 ' + money(p.cost - i.cost) + '。独立／共享未用预算分别为 ' + money(i.unspent) + '／' + money(p.unspent) + '。';
    document.getElementById('participation-summary').textContent = f ? money(f.cost) + ' 投入，' + tonnes(f.zoneA) + ' 模拟减少施盐，三个城镇均选中项目。' : '无可行方案：预算不足以覆盖每镇至少一个启用项目，或某镇没有启用项目。';
    document.getElementById('participation-projects').innerHTML = planRows(f);
    document.getElementById('equal-spend').textContent = '把共享上限限制为独立模式实际投入 ' + money(i.cost) + '：模拟减少 ' + tonnes(e.zoneA) + '；有 ' + e.townsSelected + ' 个城镇选中项目。';
    document.getElementById('equal-spend-participation').textContent = ef ? '同样实际投入，并要求每镇至少一个项目：模拟减少 ' + tonnes(ef.zoneA) + '，选中 ' + ef.townsSelected + ' 个城镇。' : '同样实际投入下，“每镇至少一个项目”无可行方案。';
  } catch (err) {
    current = null; currentInputs = null; error.textContent = err.message; error.hidden = false; output.hidden = true; document.getElementById('export').disabled = true;
  }
}
for (const id of ['budget', 'intensity']) document.getElementById(id).addEventListener('input', update);
document.getElementById('effect').addEventListener('change', update);
document.getElementById('project-editor').addEventListener('input', update);
for (const input of document.querySelectorAll('[data-toggle]')) input.addEventListener('change', () => {
  for (const layer of document.querySelectorAll('.road-layer')) if (layer.dataset.code === input.dataset.toggle) layer.style.display = input.checked ? '' : 'none';
});
document.getElementById('reset-scenario').addEventListener('click', () => {
  document.getElementById('budget').value = 75000; document.getElementById('intensity').value = 5; document.getElementById('effect').value = 'central';
  for (const p of originalProjects) {
    const row = document.querySelector('[data-project="' + p.project_id + '"]');
    row.querySelector('[data-field="cost"]').value = p.capital_cost_usd;
    row.querySelector('[data-field="coverage"]').value = p.coverage_fraction_assumed * 100;
    row.querySelector('[data-field="enabled"]').checked = true;
  }
  document.getElementById('import-status').textContent = ''; update();
});
document.getElementById('export').addEventListener('click', () => {
  if (!current) return;
  const payload = { schema_version: 2, source_sha256: ANALYSIS.phase2.evidence.source.sha256, inputs: currentInputs, result: current, input_status: 'SIMULATED_OR_UNVERIFIED_USER_INPUT' };
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = 'saltshield-phase2-scenario.json'; link.click(); URL.revokeObjectURL(url);
});
document.getElementById('import-scenario').addEventListener('change', async event => {
  const status = document.getElementById('import-status');
  try {
    const file = event.target.files[0]; if (!file) return;
    if (file.size > 2000000) throw new Error('情景文件超过 2 MB。');
    const data = JSON.parse(await file.text());
    if (data.schema_version !== 2 || data.source_sha256 !== ANALYSIS.phase2.evidence.source.sha256) throw new Error('情景版本或证据快照不匹配。');
    if (typeof data.inputs?.budget !== 'number' || typeof data.inputs?.intensity !== 'number' || !['low','central','high'].includes(data.inputs?.effect)) throw new Error('预算、强度或效果情景缺失。');
    if (!Array.isArray(data.inputs?.projects) || data.inputs.projects.length !== originalProjects.length) throw new Error('项目数量不匹配。');
    const incoming = new Map(data.inputs.projects.map(p => [p.project_id, p]));
    if (incoming.size !== originalProjects.length || originalProjects.some(p => !incoming.has(p.project_id))) throw new Error('项目编号不匹配。');
    // Only operational controls are imported; geometry and official evidence stay immutable.
    const normalized = originalProjects.map(p => {
      const q = incoming.get(p.project_id);
      if (typeof q.enabled !== 'boolean' || typeof q.coverage_fraction_assumed !== 'number' || typeof q.capital_cost_usd !== 'number') throw new Error('项目输入字段不完整。');
      return { ...p, capital_cost_usd: q.capital_cost_usd, coverage_fraction_assumed: q.coverage_fraction_assumed, enabled: q.enabled };
    });
    SaltShield.compare(normalized, data.inputs.budget, towns, data.inputs.effect, data.inputs.intensity);
    for (const p of normalized) {
      const row = document.querySelector('[data-project="' + p.project_id + '"]');
      row.querySelector('[data-field="cost"]').value = p.capital_cost_usd;
      row.querySelector('[data-field="coverage"]').value = p.coverage_fraction_assumed * 100;
      row.querySelector('[data-field="enabled"]').checked = p.enabled;
    }
    document.getElementById('budget').value = data.inputs.budget; document.getElementById('intensity').value = data.inputs.intensity; document.getElementById('effect').value = data.inputs.effect;
    update(); status.textContent = '情景已导入；数值仍为未核验规划输入。';
  } catch (err) { status.textContent = '导入失败：' + err.message; }
  event.target.value = '';
});
update();
