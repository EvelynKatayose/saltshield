/* Immersive presentation. Artwork and the quantitative planner stay distinct. */
(() => {
  const $=id=>document.getElementById(id),root=$('experience-view');if(!root||!$('x-snow-canvas'))return;
  const winter=SaltShieldWinter,media=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)'),scenes=[],cells=ANALYSIS.joint.cells,cellTown=new Map(cells.map(c=>[c.cell_id,c.town]));
  let paused=Boolean(media?.matches),userMotionChoice=false,active=root.hidden===false,frame=null,last=0,mode='pooled',stage='snow',scenario=null;
  function makeScene(id,kind){
    const canvas=$(id),model=winter.create({kind,count:kind==='hero'?260:145,seed:kind==='hero'?71:41});let ctx=null;
    try{ctx=canvas.getContext?.('2d');}catch{}
    const scene={canvas,model,ctx,visible:true,width:0,height:0};scenes.push(scene);
    function resize(){if(!ctx)return;const box=canvas.getBoundingClientRect(),dpr=Math.min(globalThis.devicePixelRatio||1,2);scene.width=box.width;scene.height=box.height;canvas.width=Math.round(box.width*dpr);canvas.height=Math.round(box.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);winter.draw(ctx,model,scene.width,scene.height);}
    const point=event=>{const box=canvas.getBoundingClientRect();return {x:(event.clientX-box.left)/box.width,y:(event.clientY-box.top)/box.height};};
    canvas.addEventListener('pointermove',event=>{
      const p=point(event);winter.interact(model,p.x,p.y,kind==='lab'&&event.buttons===1&&stage==='salt'?'salt':'gust');
      if(kind==='hero'&&!paused){$('x-hero-art').style.setProperty('--look-x',((p.x-.5)*-8)+'px');$('x-hero-art').style.setProperty('--look-y',((p.y-.5)*-5)+'px');}
      if(paused)winter.draw(ctx,model,scene.width,scene.height);
    });
    canvas.addEventListener('pointerdown',event=>{const p=point(event);if(kind==='lab')winter.interact(model,p.x,p.y,stage==='salt'?'salt':'ripple');else winter.interact(model,p.x,p.y,p.x>.55&&p.y>.45?'ripple':'gust');if(paused)winter.draw(ctx,model,scene.width,scene.height);});
    if(globalThis.ResizeObserver&&ctx)new ResizeObserver(resize).observe(canvas);else globalThis.addEventListener?.('resize',resize);
    scene.resize=resize;resize();return scene;
  }
  const hero=makeScene('x-snow-canvas','hero'),lab=makeScene('x-lab-canvas','lab');$('x-lab-fallback').hidden=Boolean(lab.ctx);$('x-lab-fallback').setAttribute('aria-hidden',String(Boolean(lab.ctx)));$('x-lab-canvas').hidden=!lab.ctx;
  function allowed(){return active&&!paused&&!document.hidden&&scenes.some(s=>s.ctx&&s.visible);}
  function tick(now){frame=null;if(!allowed())return;if(!last)last=now;const dt=Math.min((now-last)/1000,.05);if(now-last>=30){for(const s of scenes)if(s.visible&&s.ctx){winter.step(s.model,dt);winter.draw(s.ctx,s.model,s.width,s.height);}last=now;}frame=globalThis.requestAnimationFrame?.(tick)??null;}
  function animate(){if(frame!==null&&!allowed()){globalThis.cancelAnimationFrame?.(frame);frame=null;last=0;}if(frame===null&&allowed()&&globalThis.requestAnimationFrame)frame=requestAnimationFrame(tick);}
  function motion(){root.dataset.motion=paused?'paused':'playing';$('x-motion').setAttribute('aria-pressed',String(paused));$('x-motion').textContent=paused?'Resume motion  ▷':'Pause motion  Ⅱ';if(paused)for(const s of scenes)winter.draw(s.ctx,s.model,s.width,s.height);animate();}
  $('x-motion').addEventListener('click',()=>{paused=!paused;userMotionChoice=true;motion();});
  media?.addEventListener('change',event=>{if(!userMotionChoice){paused=event.matches;motion();}});document.addEventListener?.('visibilitychange',animate);
  const status={snow:'Snow · move the cursor to create a small gust.',salt:'Salt · add grains with the button or press and drag on the scene.',water:'Water · grains follow an illustrative connection. Tap to create ripples.'};
  function setStage(value){stage=value;winter.stage(lab.model,value);for(const name of ['snow','salt','water'])$('x-stage-'+name).setAttribute('aria-pressed',String(name===value));$('x-stage-status').textContent=status[value];$('x-canvas-hint').textContent=value==='salt'?'Press and drag to scatter illustrated salt':value==='water'?'Tap the water to make a ripple':'Brush the snowfall with your cursor';if(value==='water'&&!lab.model.grains.length)winter.interact(lab.model,.55,.3,'salt');winter.draw(lab.ctx,lab.model,lab.width,lab.height);}
  for(const value of ['snow','salt','water'])$('x-stage-'+value).addEventListener('click',()=>setStage(value));
  $('x-add-salt').addEventListener('click',()=>{setStage('salt');winter.interact(lab.model,.5,.28,'salt');winter.draw(lab.ctx,lab.model,lab.width,lab.height);});
  $('x-ripple').addEventListener('click',()=>{setStage('water');winter.interact(lab.model,.66,.8,'ripple');winter.draw(lab.ctx,lab.model,lab.width,lab.height);});
  $('x-clear').addEventListener('click',()=>{lab.model.grains=[];lab.model.ripples=[];lab.model.emitted=0;setStage('snow');});
  $('x-snowfall').addEventListener('input',()=>{const value=Number($('x-snowfall').value)/100;if(Number.isFinite(value)&&value>=0&&value<=1){for(const s of scenes){s.model.snowfall=value;winter.draw(s.ctx,s.model,s.width,s.height);}}});
  for(const button of document.querySelectorAll('[data-x-scroll]'))button.addEventListener('click',()=>$(button.dataset.xScroll==='x-live'?'x-live-workbench':button.dataset.xScroll)?.scrollIntoView?.({behavior:paused?'auto':'smooth',block:'start'}));
  if(globalThis.IntersectionObserver){
    root.classList.add('x-enhanced');const reveal=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){e.target.classList.add('is-revealed');reveal.unobserve(e.target);}},{threshold:.12});for(const el of document.querySelectorAll('.x-reveal'))reveal.observe(el);
    const visible=new IntersectionObserver(entries=>{for(const e of entries){const s=scenes.find(s=>s.canvas===e.target);if(s)s.visible=e.isIntersecting;}animate();},{rootMargin:'100px'});for(const s of scenes)visible.observe(s.canvas);
    const chapters=new IntersectionObserver(entries=>{if(!active)return;for(const e of entries)if(e.isIntersecting)setStage(e.target.dataset.xChapter);},{rootMargin:'-30% 0px -40% 0px'});for(const el of document.querySelectorAll('[data-x-chapter]'))chapters.observe(el);
  }
  function highlight(town){for(const element of document.querySelectorAll('.experience-cell'))element.style.opacity=!town||cellTown.get(element.dataset.cell)===town?'1':'.2';}
  function renderPlan(){
    const result=scenario?.plans[mode];$('x-model-error').hidden=Boolean(result);$('x-model-output').hidden=!result;
    if(!result){$('x-model-error').textContent='Check the project inputs in the planning workspace to update this comparison.';for(const el of document.querySelectorAll('.experience-cell'))el.style.fill='#163744';return;}
    const i=scenario.input_snapshot,budget=$('x-budget'),capMax=Math.max(150000,Math.ceil(i.budget/1000)*1000);budget.max=capMax;budget.value=i.budget;$('x-budget-value').textContent=money(i.budget);$('x-budget-max').textContent=money(capMax);
    $('x-plan-cost').textContent=money(result.cost);$('x-plan-unspent').textContent=money(result.unspent)+' unspent';$('x-plan-roads').textContent=result.covered_road_km.toFixed(2)+' km';$('x-plan-cells').textContent=result.selected_cell_ids.length+' whole planning cells';$('x-plan-benefit').textContent=tonnes(result[i.objective]);$('x-plan-benefit-label').textContent=i.objective==='zoneA'?'Modeled Zone A reduction':'Modeled A/B/C reduction';
    for(const policy of ['independent','pooled']){const selected=new Set(scenario.plans[policy].selected_cell_ids);for(const el of document.querySelectorAll('.experience-cell-'+policy))el.style.fill=selected.has(el.dataset.cell)?(policy==='pooled'?'#87debf':'#8babb8'):'#173943';}
    $('x-town-plans').innerHTML=i.towns.map(t=>{const p=result.selected.find(p=>p.town===t),a=p?.allocation,share=a&&a.capacity_km?a.covered_road_km/a.capacity_km:0;return '<button class="x-town-row" data-x-town="'+escapeHtml(t)+'"><span class="x-town-top"><span>'+escapeHtml(niceTown(t))+'</span><strong>'+money(p?.capital_cost_usd??0)+'</strong></span><span class="x-town-detail"><span>'+(p?escapeHtml(p.project_type)+' · '+a.selected_cell_ids.length+' cells':'No package selected')+'</span><span>'+(a?a.covered_road_km.toFixed(2)+' / '+a.capacity_km.toFixed(0)+' km':'—')+'</span></span><span class="x-capacity-track"><i style="width:'+(share*100).toFixed(2)+'%"></i></span></button>';}).join('');
    for(const button of document.querySelectorAll('[data-x-town]')){for(const event of ['pointerenter','focus'])button.addEventListener(event,()=>highlight(button.dataset.xTown));for(const event of ['pointerleave','blur'])button.addEventListener(event,()=>highlight(null));}
    const ind=scenario.plans.independent,pool=scenario.plans.pooled,difference=pool[i.objective]-ind[i.objective],costDifference=pool.cost-ind.cost;
    const maximum=Math.max(ind[i.objective],pool[i.objective],0);
    $('x-compare-scope').textContent=(i.objective==='zoneA'?'Zone A':'A/B/C')+' · simulated t / winter';
    for(const policy of ['independent','pooled']){
      const plan=scenario.plans[policy];
      $('x-compare-'+policy+'-benefit').textContent=tonnes(plan[i.objective]);
      $('x-compare-'+policy+'-bar').style.width=(maximum?100*plan[i.objective]/maximum:0).toFixed(2)+'%';
      $('x-compare-'+policy+'-detail').textContent=money(plan.cost)+' selected capital · '+plan.townsSelected+' of '+i.towns.length+' towns funded';
    }
    $('x-result-comparison').textContent='Sharing models '+tonnes(difference)+' more avoided application'+(costDifference===0?' at the same actual spending.':', with '+money(Math.abs(costDifference))+' '+(costDifference>0?'more':'less')+' selected capital.');
    const equal=scenario.plans.equalSpend;$('x-equal-spend').textContent='At the independent plan’s actual spending of '+money(ind.cost)+', sharing models '+tonnes(equal[i.objective])+' across '+equal.townsSelected+' towns, compared with '+tonnes(ind[i.objective])+' independently. Buying additional equipment and reallocating the same spending are different comparisons.';
  }
  function choosePlan(value){mode=value;for(const v of ['independent','pooled'])for(const prefix of ['x-mode-','x-compare-'])$(prefix+v).setAttribute('aria-pressed',String(v===value));renderPlan();}
  for(const value of ['independent','pooled'])for(const prefix of ['x-mode-','x-compare-'])$(prefix+value).addEventListener('click',()=>choosePlan(value));
  $('x-budget').addEventListener('input',()=>{$('budget').value=$('x-budget').value;$('budget').dispatchEvent(new Event('input'));});
  function split(){const value=Math.max(0,Math.min(100,Number($('x-map-split').value)));$('x-map-pooled').style.clipPath='inset(0 0 0 '+value+'%)';$('x-map-divider').style.left=value+'%';}
  $('x-map-split').addEventListener('input',split);split();
  // The visible divider supports direct pointer dragging, in addition to the
  // native range control and its keyboard/touch accessibility.
  const compare=$('x-compare-map');let dragging=false;
  compare.addEventListener('pointerdown',e=>{if(e.target?.tagName==='INPUT'||e.pointerType==='touch')return;const b=compare.getBoundingClientRect();if(Math.abs(e.clientX-b.left-b.width*Number($('x-map-split').value)/100)<35){dragging=true;compare.setPointerCapture?.(e.pointerId);}});
  compare.addEventListener('pointermove',e=>{if(!dragging)return;const b=compare.getBoundingClientRect();$('x-map-split').value=Math.max(0,Math.min(100,(e.clientX-b.left)/b.width*100));split();});
  compare.addEventListener('pointerup',()=>{dragging=false;});compare.addEventListener('pointercancel',()=>{dragging=false;});
  globalThis.SaltShieldExperience={sync(value){scenario=value;renderPlan();},visibility(value){active=value;if(active)for(const s of scenes)s.resize();animate();},state(){return {stage,mode,paused,salt_particles:lab.model.grains.length,ripples:lab.model.ripples.length};}};
  scenario=globalThis.SaltShieldJointUI?.getState?.()??null;renderPlan();motion();
})();
