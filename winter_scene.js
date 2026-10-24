/* Bounded, deterministic illustration physics. Never an input to salt accounting. */
(() => {
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  function create({seed=71,kind='lab',count=160}={}){
    let state=seed>>>0;const random=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};
    const model={kind,stage:'snow',time:0,snowfall:.55,wind:0,pointer:null,grains:[],ripples:[],random,snow:[],emitted:0};
    for(let i=0;i<clamp(count,0,320);i++)model.snow.push({x:random(),y:random(),depth:.2+random()*.8,phase:random()*6.28,vx:0,vy:0});return model;
  }
  function stage(model,value){if(!['snow','salt','water'].includes(value))throw Error('Unknown illustration stage');model.stage=value;}
  function interact(model,x,y,type='gust'){
    if(!Number.isFinite(x)||!Number.isFinite(y))return;
    x=clamp(x,0,1);y=clamp(y,0,1);model.pointer={x,y,age:0};model.wind=(x-.5)*.3;
    if(type==='salt'){
      for(let i=0;i<18;i++)model.grains.push({x:clamp(x+(model.random()-.5)*.07,.02,.98),y:Math.min(y,.35),vx:(model.random()-.5)*.12,vy:-model.random()*.08,size:1+model.random()*2,travel:0,phase:model.random()*6.28,landed:false});
      model.grains=model.grains.slice(-240);model.emitted+=18;
    }
    if(type==='ripple'){model.ripples.push({x,y:model.kind==='hero'?y:clamp(y,.7,.95),age:0});model.ripples=model.ripples.slice(-20);}
  }
  const road=x=>.415+Math.sin(x*4.1)*.028;
  function step(model,seconds){
    const dt=clamp(Number.isFinite(seconds)?seconds:0,0,.05);model.time+=dt;
    if(model.pointer){model.pointer.age+=dt;if(model.pointer.age>1.2)model.pointer=null;}
    for(const s of model.snow){
      if(model.pointer){const dx=s.x-model.pointer.x,dy=s.y-model.pointer.y,d=Math.hypot(dx,dy);if(d<.14&&d>.00001){const f=(.14-d)/.14*.9*dt;s.vx+=dx/d*f;s.vy+=dy/d*f;}}
      s.x+=(model.wind*.12+Math.sin(model.time*.35+s.phase)*.008+s.vx)*dt;s.y+=(.025+s.depth*.07+s.vy)*dt;s.vx*=Math.exp(-dt*2.4);s.vy*=Math.exp(-dt*2.4);
      if(s.y>1.04){s.y=-.04;s.x=model.random();}if(s.y<-.1)s.y=1;if(s.x>1.05)s.x=-.05;if(s.x<-.05)s.x=1.05;
    }
    for(const g of model.grains){
      if(!g.landed){g.vy+=.4*dt;g.y+=g.vy*dt;g.x=clamp(g.x+g.vx*dt,.01,.99);if(g.y>=road(g.x)){g.y=road(g.x);g.landed=true;}}
      if(g.landed&&model.stage==='water'){g.travel=Math.min(1,g.travel+dt*.13);if(g.travel>=1){model.ripples.push({x:.66+(g.x-.5)*.12,y:.79+(g.x-.5)*.07,age:0});g.finished=true;}}
    }
    model.grains=model.grains.filter(g=>!g.finished);model.ripples=model.ripples.slice(-20);for(const r of model.ripples)r.age+=dt;model.ripples=model.ripples.filter(r=>r.age<3.5);
  }
  function draw(ctx,m,w,h){
    if(!ctx||w<=0||h<=0)return;ctx.clearRect(0,0,w,h);
    if(m.kind==='lab'){
      const sky=ctx.createLinearGradient(0,0,0,h);sky.addColorStop(0,'#a8c8d8');sky.addColorStop(.42,'#d0e4ea');sky.addColorStop(.6,'#e0ebed');sky.addColorStop(1,'#4a8898');ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);
      const glow=ctx.createRadialGradient(w*.72,h*.14,0,w*.72,h*.14,w*.42);glow.addColorStop(0,'rgba(255,248,220,.38)');glow.addColorStop(.5,'rgba(255,248,220,.08)');glow.addColorStop(1,'rgba(255,248,220,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
      for(let layer=0;layer<3;layer++){ctx.beginPath();ctx.moveTo(0,h);for(let x=0;x<=w+10;x+=10)ctx.lineTo(x,h*(.16+layer*.07+Math.sin(x/w*5+layer)*.045+Math.cos(x/w*13+layer)*.009));ctx.lineTo(w,h);ctx.closePath();ctx.fillStyle=['#7a9ba8','#526d7a','#2e505d'][layer];ctx.fill();}
      // Snow-covered slope and an asphalt ribbon, viewed obliquely.
      ctx.beginPath();ctx.moveTo(0,h*.3);ctx.bezierCurveTo(w*.32,h*.24,w*.55,h*.4,w,h*.35);ctx.lineTo(w,h*.67);ctx.bezierCurveTo(w*.6,h*.73,w*.27,h*.57,0,h*.68);ctx.closePath();const slope=ctx.createLinearGradient(0,h*.3,0,h*.68);slope.addColorStop(0,'#eaf3f6');slope.addColorStop(.5,'#dce9ed');slope.addColorStop(1,'#c8d9de');ctx.fillStyle=slope;ctx.fill();
      const ribbon=(width,color)=>{ctx.beginPath();for(let x=-10;x<=w+10;x+=8){const y=road(x/w)*h;if(x===-10)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.lineWidth=width;ctx.strokeStyle=color;ctx.stroke();};ribbon(h*.105,'#f7fbfc');ribbon(h*.068,'#3d5360');
      ctx.setLineDash([w*.023,w*.028]);ribbon(1,'#b9c7cc');ctx.setLineDash([]);
      for(let i=0;i<39;i++){
        const x=((i*97)%997)/997*w,y=h*(.245+Math.sin(i*2.13)*.037),height=h*(.035+((i*17)%23)/460);ctx.fillStyle=i%3===0?'#143a48':i%3===1?'#2a5868':'#1e4a58';
        ctx.beginPath();ctx.moveTo(x,y-height);ctx.lineTo(x-height*.36,y+height*.2);ctx.lineTo(x+height*.36,y+height*.2);ctx.closePath();ctx.fill();ctx.strokeStyle='#bfd9de';ctx.lineWidth=.8;ctx.beginPath();ctx.moveTo(x,y-height);ctx.lineTo(x-height*.21,y-height*.35);ctx.stroke();
      }
      const lake=ctx.createLinearGradient(0,h*.65,0,h);lake.addColorStop(0,'#3a8098');lake.addColorStop(.5,'#1a5a78');lake.addColorStop(1,'#0a3a54');ctx.beginPath();ctx.moveTo(0,h*.7);ctx.bezierCurveTo(w*.24,h*.6,w*.63,h*.76,w,h*.62);ctx.lineTo(w,h);ctx.lineTo(0,h);ctx.closePath();ctx.fillStyle=lake;ctx.fill();
      for(let i=0;i<19;i++){const y=h*(.72+i*.014);ctx.beginPath();for(let x=0;x<=w;x+=12){const yy=y+Math.sin(x/w*15+m.time*.65+i*.8)*1.8;if(x===0)ctx.moveTo(x,yy);else ctx.lineTo(x,yy);}ctx.strokeStyle='rgba(150,212,221,'+(.04+(i%3)*.02)+')';ctx.lineWidth=.7;ctx.stroke();}
      // Schematic surface connection. It does not encode a hydrologic route.
      ctx.beginPath();ctx.moveTo(w*.55,h*.44);ctx.bezierCurveTo(w*.47,h*.53,w*.74,h*.57,w*.66,h*.79);ctx.strokeStyle=m.stage==='water'?'#9ee0ea':'#b4d1d8';ctx.lineWidth=m.stage==='water'?10:6;ctx.stroke();
      for(let i=0;i<3;i++){const x=w*(.2+i*.23+Math.sin(m.time*.18+i)*.025),y=h*(.86+Math.sin(i*3.7)*.035);ctx.save();ctx.translate(x,y);ctx.scale(i%2?-1:1,1);ctx.fillStyle='#a5dae71e';ctx.beginPath();ctx.ellipse(0,0,13,4.5,0,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.moveTo(-11,0);ctx.lineTo(-20,-5);ctx.lineTo(-20,5);ctx.closePath();ctx.fill();ctx.restore();}
      for(const g of m.grains){
        let x=g.x,y=g.y;if(g.travel>0){const t=g.travel,u=1-t;x=u*u*u*g.x+3*u*u*t*.47+3*u*t*t*.74+t*t*t*(.66+(g.x-.5)*.12);y=u*u*u*road(g.x)+3*u*u*t*.53+3*u*t*t*.57+t*t*t*(.79+(g.x-.5)*.07);}
        ctx.save();ctx.translate(x*w,y*h);ctx.rotate(g.phase+g.travel*6);ctx.globalAlpha=1-g.travel*.75;ctx.fillStyle='#fff4cf';ctx.fillRect(-g.size,-g.size,g.size*2,g.size*2);ctx.restore();
      }
    }
    for(const s of m.snow){if(s.depth>m.snowfall+.12)continue;ctx.beginPath();ctx.arc(s.x*w,s.y*h,.5+s.depth*(m.kind==='hero'?2:1.5),0,Math.PI*2);ctx.fillStyle='rgba(242,252,255,'+(.25+s.depth*.6)+')';ctx.fill();}
    for(const r of m.ripples){ctx.beginPath();ctx.ellipse(r.x*w,r.y*h,(8+r.age*32)*(w/700),(.5+r.age*7)*(h/450),0,0,Math.PI*2);ctx.strokeStyle='rgba(173,232,235,'+(Math.max(0,1-r.age/3.5)*.8)+')';ctx.lineWidth=1;ctx.stroke();}
  }
  globalThis.SaltShieldWinter={create,stage,step,interact,draw,road};
})();
