/* Exact, dependency-free investment scenarios. Operational inputs are assumptions. */
(function (global) {
  function number(value, label, high = Infinity) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > high) throw new Error('Invalid ' + label);
    return value;
  }
  function materialize(projects, towns, effect = 'central', baselineIntensity = 5) {
    number(baselineIntensity, 'baseline intensity');
    if (!['low', 'central', 'high'].includes(effect)) throw new Error('Unknown effect scenario');
    const field = { low: 'reduction_low', central: 'reduction_fraction', high: 'reduction_high' }[effect];
    const ids = new Set();
    return projects.map(p => {
      if (ids.has(p.project_id) || !towns.includes(p.town)) throw new Error('Duplicate project or unknown town');
      ids.add(p.project_id);
      number(p.capital_cost_usd, 'cost');
      const coverage = number(p.coverage_fraction_assumed ?? 1, 'coverage fraction', 1);
      if (p.enabled !== undefined && typeof p.enabled !== 'boolean') throw new Error('Enabled must be boolean');
      for (const f of ['reduction_low', 'reduction_fraction', 'reduction_high']) number(p[f], f, 1);
      if (!(p.reduction_low <= p.reduction_fraction && p.reduction_fraction <= p.reduction_high)) throw new Error('Reduction range must be ordered');
      number(p.covered_zone_a_km_measured, 'Zone A length');
      number(p.covered_protected_km_measured, 'protected length');
      if (p.covered_zone_a_km_measured > p.covered_protected_km_measured + 1e-8) throw new Error('Zone A coverage exceeds protected roads');
      const centerline=number(p.covered_centerline_km_measured ?? p.covered_protected_km_measured,'eligible length');
      if(p.covered_protected_km_measured>centerline+1e-8)throw new Error('Protected coverage exceeds eligible roads');
      const factor = baselineIntensity * coverage * p[field];
      for(const mass of [centerline*baselineIntensity*coverage,p.covered_zone_a_km_measured*factor,p.covered_protected_km_measured*factor,centerline*factor])number(mass,'derived mass');
      return { ...p, coverage_fraction_assumed: coverage, active_reduction: p[field], avoided_zone_a_tonnes_simulated: p.covered_zone_a_km_measured * factor, avoided_all_zones_tonnes_simulated: p.covered_protected_km_measured * factor,avoided_all_eligible_tonnes_simulated:centerline*factor,baseline_tonnes_simulated:centerline*baselineIntensity*coverage };
    });
  }
  function solve(projects, budget, towns, localCaps = null, requireEachTown = false, objective='zoneA',forceProjectId=null) {
    number(budget, 'budget');
    if(!['zoneA','all'].includes(objective))throw new Error('Unknown objective');
    if (!towns.length || new Set(towns).size !== towns.length) throw new Error('Towns must be unique and nonempty');
    if (localCaps) for (const t of towns) number(localCaps[t], 'local cap');
    const options = towns.map(t => [null, ...projects.filter(p => p.town === t && p.enabled !== false)]);
    if(forceProjectId!==null){const forced=projects.find(p=>p.project_id===forceProjectId&&p.enabled!==false);if(!forced)return null;options[towns.indexOf(forced.town)]=[forced];}
    let best = null, feasible = 0;
    function visit(index, selected) {
      if (index < options.length) {
        for (const option of options[index]) visit(index + 1, option ? [...selected, option] : selected);
        return;
      }
      if (requireEachTown && selected.length !== towns.length) return;
      const cost = selected.reduce((v, p) => v + p.capital_cost_usd, 0);
      if (cost > budget + 1e-8) return;
      if (localCaps && towns.some(t => selected.filter(p => p.town === t).reduce((v, p) => v + p.capital_cost_usd, 0) > localCaps[t] + 1e-8)) return;
      const zoneA = selected.reduce((v, p) => v + p.avoided_zone_a_tonnes_simulated, 0);
      const all = selected.reduce((v, p) => v + p.avoided_all_zones_tonnes_simulated, 0);
      feasible++;
      const value=objective==='zoneA'?zoneA:all,secondary=objective==='zoneA'?all:zoneA;
      if (!best || value > best[objective] || (value === best[objective] && (secondary > best[objective==='zoneA'?'all':'zoneA'] || (secondary === best[objective==='zoneA'?'all':'zoneA'] && cost < best.cost)))) best = { cost, zoneA, all, eligible:selected.reduce((v,p)=>v+(p.avoided_all_eligible_tonnes_simulated??p.avoided_all_zones_tonnes_simulated),0),selected, unspent: budget - cost, townsSelected: selected.length };
    }
    visit(0, []);
    return best ? { ...best, feasibleCombinations: feasible } : null;
  }
  function compare(projects, budget, towns, effect = 'central', baselineIntensity = 5,objective='zoneA') {
    const ps = materialize(projects, towns, effect, baselineIntensity);
    const independent = solve(ps, budget, towns, Object.fromEntries(towns.map(t => [t, budget / towns.length])),false,objective);
    const pooled = solve(ps, budget, towns,null,false,objective);
    const participation = solve(ps, budget, towns, null, true,objective);
    const equalSpend = solve(ps, independent.cost, towns,null,false,objective);
    const equalSpendParticipation = solve(ps, independent.cost, towns, null, true,objective);
    return { independent, pooled, participation, equalSpend, equalSpendParticipation };
  }
  global.SaltShield = { solve, compare, materialize };
})(globalThis);
