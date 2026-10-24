/* Clean hosted URLs, with file-based navigation retained for offline copies. */
(() => {
  const views=['experience','overview','investments','coverage','evidence'];
  const web=/^https?:$/.test(globalThis.location?.protocol??'');
  const configured=document.getElementById('saltshield-base')?.content||'/';
  const base='/'+configured.split('/').filter(Boolean).join('/')+(configured==='/'?'':'/');
  function view(){
    const legacy=(globalThis.location?.hash??'').slice(1);
    if(views.includes(legacy))return legacy;
    if(web){
      const path=globalThis.location.pathname??base;
      const section=path.startsWith(base)?path.slice(base.length).replace(/\/$/,''):'';
      if(views.includes(section))return section;
    }
    return 'experience';
  }
  function url(name,search=globalThis.location?.search??''){
    if(!views.includes(name))name='experience';
    return web?base+(name==='experience'?'':name+'/')+search:search+'#'+name;
  }
  globalThis.SaltShieldRouter={web,base,view,url,demoURL:()=>url('experience','?demo=1')};
  for(const link of document.querySelectorAll('a[data-go]'))link.href=url(link.dataset.go);
  for(const link of document.querySelectorAll('.x-demo-launch'))link.href=url('experience','?demo=1');
})();
