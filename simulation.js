/* Exact, dependency-free scenario solver. Inputs and outputs are simulated. */
(function (global) {
  function solve(projects, budget, towns, localCaps = null) {
    let best = null;
    const options = towns.map(t => [null, ...projects.filter(p => p.town === t)]);
    for (const a of options[0]) for (const b of options[1]) for (const c of options[2]) {
      const selected = [a, b, c].filter(Boolean);
      const cost = selected.reduce((v, p) => v + p.capital_cost_usd, 0);
      if (cost > budget + 1e-8) continue;
      if (localCaps && towns.some(t => selected.filter(p => p.town === t).reduce((v, p) => v + p.capital_cost_usd, 0) > localCaps[t] + 1e-8)) continue;
      const zoneA = selected.reduce((v, p) => v + p.avoided_zone_a_tonnes_simulated, 0);
      const all = selected.reduce((v, p) => v + p.avoided_all_zones_tonnes_simulated, 0);
      if (!best || zoneA > best.zoneA || (zoneA === best.zoneA && (all > best.all || (all === best.all && cost < best.cost)))) {
        best = { cost, zoneA, all, selected, unspent: budget - cost };
      }
    }
    return best;
  }
  function compare(projects, budget, towns, effect = 'central') {
    if (!Number.isFinite(budget) || budget < 0) throw new Error('Budget must be nonnegative.');
    const ps = projects.map(p => {
      const r = effect === 'low' ? p.reduction_low : effect === 'high' ? p.reduction_high : p.reduction_fraction;
      const ratio = r / p.reduction_fraction;
      return { ...p, active_reduction: r, avoided_zone_a_tonnes_simulated: p.avoided_zone_a_tonnes_simulated * ratio, avoided_all_zones_tonnes_simulated: p.avoided_all_zones_tonnes_simulated * ratio };
    });
    const independent = solve(ps, budget, towns, Object.fromEntries(towns.map(t => [t, budget / towns.length])));
    const pooled = solve(ps, budget, towns);
    const equalSpend = solve(ps, independent.cost, towns);
    return { independent, pooled, equalSpend };
  }
  global.SaltShield = { solve, compare };
})(globalThis);
