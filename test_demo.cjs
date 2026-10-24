/* A presentation starts consistently without modifying the user's saved work. */
const assert=require('node:assert/strict'),{harness}=require('./test_experience.cjs');
async function run(){
  const ordinary=harness();ordinary.get('x-budget').value=133000;ordinary.get('x-budget').listeners.input();ordinary.get('joint-reach-HOLDEN_BRINE').value=19;ordinary.get('joint-capacity-editor').listeners.input();
  const saved=Object.fromEntries(ordinary.storage),before=JSON.stringify(saved),demo=harness({search:'?demo=1',stored:saved}),checks=[];
  assert.equal(demo.context.SaltShieldDemo.active,true);assert.equal(demo.get('budget').value,'75000');assert.equal(demo.get('joint-reach-HOLDEN_BRINE').value,'50');assert.equal(demo.get('x-plan-benefit').textContent,'60.68 t');checks.push('demo_ignores_saved_budget_and_reach_and_starts_at_75000');
  assert.equal(demo.get('demo-restart').hidden,false);assert.equal(demo.get('demo-restart-workspace').hidden,false);assert.match(demo.get('draft-status').textContent,/saved drafts unchanged/);checks.push('demo_mode_is_visible_in_both_experience_and_workspace');
  demo.get('demo-budget-45000').listeners.click();assert.equal(demo.get('x-plan-benefit').textContent,'34.35 t');demo.get('x-mode-independent').listeners.click();assert.equal(demo.get('x-plan-benefit').textContent,'20.15 t');checks.push('equal_spend_demo_preset_matches_expected_numbers');
  demo.context.SaltShieldWorkspace.showView('coverage');demo.get('joint-policy').value='participation';demo.get('joint-policy').listeners.change();assert.equal(demo.get('joint-benefit').textContent,'20.15 t');checks.push('every_town_rule_exposes_the_same_spend_tradeoff');
  const checking=demo.get('joint-reach-run').listeners.click();demo.flush(100);await checking;assert.match(demo.get('joint-reach-status').textContent,/9 assumed cases/);assert.equal(demo.get('joint-brief').disabled,false);checks.push('demo_can_check_reach_and_export_current_feasible_plan');
  assert.equal(JSON.stringify(Object.fromEntries(demo.storage)),before);checks.push('presenting_and_editing_in_demo_never_overwrites_saved_drafts');
  demo.get('demo-restart-workspace').listeners.click();assert.equal(demo.context.history.lastUrl,'?demo=1#experience');assert.equal(demo.context.location.reloaded,true);checks.push('restart_returns_to_the_clean_demo_entry');
  const restored=harness({stored:saved});assert.equal(restored.get('budget').value,'133000');assert.equal(restored.get('joint-reach-HOLDEN_BRINE').value,'19');assert.equal(restored.get('demo-restart').hidden,true);checks.push('ordinary_mode_still_restores_the_original_saved_work');
  return {status:'PASS',checks};
}
module.exports={run};if(require.main===module)run().then(r=>console.log(JSON.stringify(r,null,2))).catch(error=>{console.error(error);process.exitCode=1;});
