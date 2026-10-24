/* Isolated, repeatable presentation session. Saved planning drafts stay intact. */
(() => {
  const active=/(?:^|[?&])demo=1(?:&|$)/.test(globalThis.location?.search??'');
  document.documentElement.dataset.demo=String(active);
  function restart(){
    if(!active)return;
    globalThis.history?.replaceState(null,'','?demo=1#experience');
    globalThis.location?.reload?.();
  }
  function budget(value){if(!active)return;const input=document.getElementById('x-budget');if(input){input.value=value;input.dispatchEvent(new Event('input'));}}
  const presets=document.getElementById('demo-budget-presets');if(presets)presets.hidden=!active;
  for(const value of [75000,45000])document.getElementById('demo-budget-'+value)?.addEventListener('click',()=>budget(value));
  for(const id of ['demo-restart','demo-restart-workspace']){
    const button=document.getElementById(id);if(!button)continue;
    button.hidden=!active;button.addEventListener('click',restart);
  }
  globalThis.SaltShieldDemo={active,restart,budget};
})();
