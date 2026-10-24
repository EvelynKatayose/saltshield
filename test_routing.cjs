/* Exercise the shipped scripts at public subpaths and in offline copies. */
const assert=require('node:assert/strict'),{harness}=require('./test_experience.cjs');
function run(){
  const checks=[],options={protocol:'https:',basePath:'/saltshield/',pathname:'/saltshield/'};
  const home=harness(options);
  assert.equal(home.context.history.lastUrl,'/saltshield/');
  assert.equal(home.document.documentElement.dataset.view,'experience');
  checks.push('public_home_has_no_hash');
  home.context.SaltShieldWorkspace.showView('coverage');
  assert.equal(home.context.history.lastUrl,'/saltshield/coverage/');
  const deep=harness({...options,pathname:'/saltshield/coverage/'});
  assert.equal(deep.document.documentElement.dataset.view,'coverage');
  assert.equal(deep.get('joint-benefit').textContent,'60.68 t');
  checks.push('workspace_navigation_and_direct_reload_use_clean_paths');
  const demo=harness({...options,search:'?demo=1',pathname:'/saltshield/evidence/'});
  demo.get('demo-restart-workspace').listeners.click();
  assert.equal(demo.context.history.lastUrl,'/saltshield/?demo=1');
  assert.equal(demo.context.location.reloaded,true);
  checks.push('demo_restart_preserves_subpath_and_removes_hash');
  const legacy=harness({...options,hash:'#investments'});
  assert.equal(legacy.context.history.lastUrl,'/saltshield/investments/');
  checks.push('legacy_bookmarks_normalize_to_clean_paths');
  assert.equal(home.get('demo-budget-presets').hidden,false);
  home.get('demo-budget-45000').listeners.click();
  assert.equal(home.get('x-plan-benefit').textContent,'34.35 t');
  checks.push('budget_shortcuts_are_visible_and_work_without_demo_mode');
  const file=harness({protocol:'file:',hash:'#coverage'});
  assert.equal(file.context.history.lastUrl,'#coverage');
  checks.push('offline_file_keeps_compatible_navigation');
  return {status:'PASS',checks};
}
module.exports={run};if(require.main===module)try{console.log(JSON.stringify(run(),null,2));}catch(error){console.error(error);process.exitCode=1;}
