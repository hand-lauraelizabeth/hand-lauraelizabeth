/* Illustrated moving scenes, separate from existing modeled instrument displays. */
const TransitSceneMath=(()=>{
 'use strict';
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
 function curvature(route,distance){
  if(!route?.points?.length||typeof TransitGeography==='undefined')return 0;
  const g=TransitGeography,dist=route.lengthM||10000,p=g.routeAtFraction(route,clamp((distance-240)/dist,0,1)),
    m=g.routeAtFraction(route,clamp(distance/dist,0,1)),q=g.routeAtFraction(route,clamp((distance+240)/dist,0,1));
  if(!p||!m||!q)return 0;
  const angle=(a,b)=>Math.atan2((b.lon-a.lon)*Math.cos(a.lat*Math.PI/180),b.lat-a.lat);
  const delta=angle(m,q)-angle(p,m);
  return clamp(Math.atan2(Math.sin(delta),Math.cos(delta))*200,-92,92);
 }
 function seabed(sample,location){
  if(!sample||!location||typeof TransitTerrain==='undefined'||!Number.isFinite(sample.meters)||sample.meters>=0)return null;
  const meters=TransitTerrain.distance(sample,location);
  return meters<=1800?{depth:-sample.meters,separation:meters}:null;
 }
 return {clamp,curvature,seabed};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitSceneMath;
(function installSceneV3(){
 'use strict';
 if(typeof document==='undefined'||typeof TransitModels==='undefined')return;
 const root=document.getElementById('leh-transit');if(!root||root.dataset.sceneV3==='ready')return;
 root.dataset.sceneV3='ready';
 const $=id=>document.getElementById(id),M=TransitModels,C=TransitSceneMath;
 const style=document.createElement('style');
 style.textContent='#leh-transit .cv-choice{display:flex;gap:.45rem;align-items:center;flex-wrap:wrap;margin:.5rem 0 .2rem}#leh-transit .cv-choice strong{font-size:.76rem;letter-spacing:.08em;text-transform:uppercase;color:#335a4d;margin-right:.35rem}#leh-transit .cv-choice button{min-height:38px;background:#e8f2ec;color:#164739;border:1px solid #9cbcaf;padding:.4rem .75rem}#leh-transit .cv-choice button[aria-pressed="true"]{background:#173d48;color:#fff;border-color:#173d48}#leh-transit .cv-note{font-size:.8rem;color:#4e6c61;line-height:1.5;min-height:1.3rem;margin:.1rem 0 .35rem}#leh-transit .tv-stage.cv-active>svg{display:none!important}#leh-transit .cv-canvas{display:none;position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#04192b}#leh-transit .tv-stage.cv-active>.cv-canvas{display:block}#leh-transit .cv-active .tv-mobile-hud{display:none!important}@media(max-width:600px){#leh-transit .tv-stage.cv-active>.cv-canvas{height:100%}#leh-transit .scene.tv-upgraded:has(.cv-active){height:270px!important;min-height:270px}}';
 document.head.append(style);
 const scenes={flight:$('tl-flight-scene'),train:$('tl-train-scene'),sub:$('tl-sub-scene')},reference=scenes.flight;
 const parent=reference?.parentElement;if(!parent)return;
 const buttons=document.createElement('div');buttons.className='cv-choice';buttons.setAttribute('role','group');buttons.setAttribute('aria-label','Visual mode');
 buttons.innerHTML='<strong>Scene</strong><button id="cv-instruments" type="button" aria-pressed="true">Instrument view</button><button id="cv-outside" type="button" aria-pressed="false">Illustrated moving view</button>';
 const caption=document.createElement('p');caption.className='cv-note';caption.id='cv-note';caption.textContent='Instrument readings are simulated, not operational sensors.';
 parent.insertBefore(buttons,reference);parent.insertBefore(caption,reference);
 const canvases={};
 for(const [kind,scene] of Object.entries(scenes)){
  const stage=scene?.querySelector('.tv-stage');if(!stage)continue;
  const canvas=document.createElement('canvas');canvas.id='cv-'+kind;canvas.className='cv-canvas';canvas.width=960;canvas.height=540;
  canvas.setAttribute('role','img');canvas.setAttribute('aria-label',kind+' procedural external view, not a recording');
  stage.append(canvas);canvases[kind]={stage,canvas,ctx:canvas.getContext('2d')};
 }
 let view='instrument',mode='flight',state=null,route=null,bathymetry=null,terrainSamples=[],dispatchState=null,observing=false;
 const W=960,H=540,fmt=(n,d=0)=>Number(n||0).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
 const rect=(ctx,x,y,w,h,col)=>{ctx.fillStyle=col;ctx.fillRect(x,y,w,h);};
 const segment=(ctx,x,y,ex,ey,col,w=2)=>{ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(ex,ey);ctx.strokeStyle=col;ctx.lineWidth=w;ctx.stroke();};
 const t=(ctx,s,x,y,size=19,col='#ebfff8',weight='600',align='left')=>{ctx.fillStyle=col;ctx.font=weight+' '+size+'px system-ui,sans-serif';ctx.textAlign=align;ctx.fillText(String(s),x,y);ctx.textAlign='left';};
 function panel(ctx,x,y,w,h){ctx.fillStyle='#081c2ce9';ctx.strokeStyle='#679ba3';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect(x,y,w,h,12);ctx.fill();ctx.stroke();}
 function readout(ctx,x,key,value,w=205){panel(ctx,x,21,w,77);t(ctx,key,x+15,46,13,'#9dcad1','800');t(ctx,value,x+15,82,27,'#f5fff9','700');}
 function gradient(ctx,top,bottom){const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,top);g.addColorStop(1,bottom);return g;}
 function flight(ctx,s){
  rect(ctx,0,0,W,H,gradient(ctx,'#135589','#89bfcc'));
  ctx.save();ctx.translate(480,270);ctx.rotate(-(s.bank||0)*Math.PI/180);ctx.translate(-480,-270+(s.flightPath||0)*7);
  rect(ctx,-240,-600,1500,885,gradient(ctx,'#1c4c86','#98d0d3'));
  const phase=(s.heading||0)*.01745;
  for(let layer=0;layer<4;layer++){
   ctx.beginPath();ctx.moveTo(-210,310+layer*48);
   for(let x=-210;x<1180;x+=18)ctx.lineTo(x,310+layer*47+Math.sin(x*.006+layer+phase)*21+Math.sin(x*.013-layer-phase)*11);
   ctx.lineTo(1180,980);ctx.lineTo(-210,980);ctx.closePath();ctx.fillStyle=['#91aa99','#6c9185','#436b68','#2b505a'][layer];ctx.fill();
  }
  for(let k=0;k<14;k++){
   const x=((k*211-(s.heading||0)*5)%1520+1520)%1520-240,y=120+(k*67)%150;
   ctx.beginPath();ctx.ellipse(x,y,80+(k%3)*20,8+(k%4)*4,0,0,Math.PI*2);ctx.fillStyle='#e8f8f52b';ctx.fill();
  }
  ctx.restore();
  ctx.beginPath();ctx.moveTo(0,H);ctx.lineTo(0,468);ctx.quadraticCurveTo(480,415,960,468);ctx.lineTo(960,H);ctx.fillStyle='#0a2130';ctx.fill();
  segment(ctx,425,280,465,280,'#f8e0a0',5);segment(ctx,494,280,534,280,'#f8e0a0',5);segment(ctx,480,269,480,293,'#f8e0a0',4);
  readout(ctx,30,'TRUE AIRSPEED',fmt(s.speed*1.943844)+' kn');
  readout(ctx,258,'ALTITUDE (MODEL)',fmt(s.alt*3.28084)+' ft',226);
  readout(ctx,718,'HEADING',fmt(s.heading)+'°',215);
  panel(ctx,29,397,422,96);t(ctx,'AIRCRAFT MODEL',47,423,14,'#abd9d5','800');t(ctx,M.AIRCRAFT[s.profile]?.name||'Flight demonstrator',47,453,19);t(ctx,'BANK '+fmt(s.bank,0)+'°   PATH '+fmt(s.flightPath,1)+'°',47,480,15,'#d2e9da');
  if(terrainSamples.length){panel(ctx,508,302,422,80);t(ctx,'USGS POINT SAMPLES · NOT A CONTINUOUS TERRAIN MODEL',521,324,12,'#aeddd7','800');t(ctx,terrainSamples.map(x=>x.km+' km: '+fmt(x.meters)+' m').join('  |  '),521,352,16,'#fff1cb','700');}
  panel(ctx,558,397,373,96);t(ctx,'GROUND TRACK / SPEED',574,423,14,'#abd9d5','800');t(ctx,fmt(s.trackDeg??s.heading,0)+'°   '+fmt((s.groundSpeed??s.speed)*1.943844,0)+' kn',574,463,24);
  t(ctx,'PROCEDURAL LANDSCAPE · NOT ACTUAL FLIGHT TERRAIN',480,520,14,'#e1eee6','700','center');
 }
 function train(ctx,s){
  rect(ctx,0,0,W,H,gradient(ctx,'#5495ac','#e3ddc9'));
  const next=route?.stations?.find(v=>v.distanceM>s.pos+.1),structure=String(next?.structure||'').toLowerCase();
  const underground=structure.includes('underground')||structure.includes('subway'),vanish=480+C.curvature(route,s.pos);
  if(underground){
   rect(ctx,0,0,W,H,gradient(ctx,'#132c39','#081c2c'));
   for(let i=0;i<6;i++){const x=i*52;panel(ctx,x,90,960-2*x,438-i*45);}
   for(let i=0;i<8;i++)rect(ctx,i*140+12,118,48,7,'#e3d8b3a0');
  }else{
   ctx.beginPath();ctx.moveTo(0,330);
   for(let x=0;x<=960;x+=20)ctx.lineTo(x,323+24*Math.sin(x*.013));
   ctx.lineTo(960,540);ctx.lineTo(0,540);ctx.fillStyle='#5c877f';ctx.fill();
   for(let i=0;i<18;i++){
    const x=i*65-26,h=40+(i*31)%122;
    rect(ctx,x,339-h,38+i%4*6,h,'#426c7e');
    for(let j=10;j<h;j+=20)rect(ctx,x+8,339-h+j,7,10,'#d9e9b65c');
   }
  }
  ctx.beginPath();ctx.moveTo(vanish-18,257);ctx.lineTo(vanish+18,257);ctx.lineTo(960,540);ctx.lineTo(0,540);ctx.closePath();ctx.fillStyle=underground?'#253941':'#5d6e69';ctx.fill();
  const phase=((s.pos||0)%16)/16;
  for(let i=20;i>=0;i--){
   const t0=(i+phase)/21,y=258+(1-t0*t0)*305,d=(1-t0*t0)*450;
   segment(ctx,vanish-d,y,vanish+d,y,'#c1a98a',3+4*(1-t0));
  }
  for(const a of [-1,1]){segment(ctx,vanish+a*5,256,480+a*320,540,'#d8e5dc',12);segment(ctx,vanish+a*5,256,480+a*320,540,'#334950',5);}
  // A stylized station platform appears near a known GTFS/geometry stop. It is not surveyed station infrastructure.
  const stop=dispatchState?.station||next,distanceToStop=stop?.distance!==undefined?stop.distance-s.pos:stop?.distanceM!==undefined?stop.distanceM-s.pos:null;
  if(Number.isFinite(distanceToStop)&&distanceToStop<=450&&distanceToStop>=-20){
   const proximity=Math.max(0,Math.min(1,1-Math.max(0,distanceToStop)/450));
   const frontY=310+proximity*145,sideX=600-proximity*56;
   ctx.beginPath();ctx.moveTo(vanish+34,265);ctx.lineTo(vanish+66,265);ctx.lineTo(960,500);ctx.lineTo(sideX,frontY);ctx.closePath();
   ctx.fillStyle=underground?'#758d91':'#b6a68f';ctx.fill();
   segment(ctx,vanish+65,265,960,498,'#f6d47e',5+proximity*3);
   const signX=660-proximity*58,signY=274+proximity*55;
   rect(ctx,signX,signY,240,42,'#163b55');
   rect(ctx,signX,signY,240,4,'#f0cc72');
   const name=String(stop?.name||'Station').slice(0,29);
   t(ctx,name,signX+13,signY+28,name.length>22?15:20,'#f4fff9','700');
   t(ctx,'SCHEMATIC PLATFORM · '+Math.max(0,Math.round(distanceToStop))+' m',signX+6,signY+61,13,'#e5fcf3','700');
  }
  ctx.beginPath();ctx.moveTo(0,540);ctx.lineTo(0,459);ctx.quadraticCurveTo(480,415,960,459);ctx.lineTo(960,540);ctx.fillStyle='#0b1d2b';ctx.fill();
  readout(ctx,27,'SPEED',fmt(s.speed*3.6,1)+' km/h');
  readout(ctx,253,'MAPPED DISTANCE',fmt(s.pos/1000,2)+' km',230);
  readout(ctx,721,'GRADE (SET)',fmt(s.grade,1)+'%',210);
  panel(ctx,28,391,483,105);t(ctx,route?'PUBLISHED SERVICE SHAPE':'GENERIC ROUTE',44,415,14,'#a7d7c6','800');
  t(ctx,route?.serviceName||route?.name||'Hypothetical 10 km track',44,447,18);
  t(ctx,(next?'NEXT '+next.name:'SEGMENT END')+'  '+fmt(Math.max(0,(next?.distanceM??s.length)-s.pos))+' m',44,474,16,'#ffe0ad');
  panel(ctx,544,391,388,105);t(ctx,'IDEAL BRAKE / ADHESION',560,417,14,'#a7d7c6','800');
  t(ctx,fmt(s.brakingDistance)+' m  ·  '+fmt(s.adhesion??1,2)+'×',560,457,24,'#f7e5bf','700');
  t(ctx,'Published geometry ≠ surveyed track',560,480,14,'#b8d6cf');
  if(dispatchState?.run){
   const phase=dispatchState.run.phase;
   if(phase==='doors-open'||phase==='at-platform'){
    rect(ctx,567,337,336,37,phase==='doors-open'?'#1d735a':'#815923');
    t(ctx,phase==='doors-open'?'PASSENGER DOORS OPEN · TRAIN HELD':'STOPPED AT PLATFORM · OPEN DOORS',735,361,14,'#ffffff','800','center');
   }
  }
  t(ctx,'PROCEDURAL CAB · MAPPED STATIONS ARE NOT REAL STATION VIEWS',480,522,13,'#c0dbd5','700','center');
 }
 function sub(ctx,s){
  rect(ctx,0,0,W,H,gradient(ctx,'#225f83','#041323'));
  const alpha=C.clamp(s.depth/700,0,.68);
  rect(ctx,0,0,W,H,'rgba(0,6,21,'+alpha.toFixed(3)+')');
  for(let i=0;i<10;i++){ctx.beginPath();ctx.moveTo(i*115,0);ctx.lineTo(i*115+36,0);ctx.lineTo(i*115+260,540);ctx.lineTo(i*115+140,540);ctx.closePath();ctx.fillStyle='#a8eeef0c';ctx.fill();}
  for(let i=0;i<105;i++){
   const x=((i*183+(s.time||0)*Math.max(1,s.speed)*(i%3+1))%990+990)%990,y=((i*79+(s.time||0)*(i%4+1))%560+560)%560;
   ctx.beginPath();ctx.arc(x,y,1+i%3*.45,0,Math.PI*2);ctx.fillStyle=i%4?'#c7f9f24a':'#defcf8b0';ctx.fill();
  }
  for(let i=0;i<5;i++){const y=132+i*70;segment(ctx,50,y,903,y,'#81c3d133',1);t(ctx,fmt(s.depth-120+i*60)+'m',37,y-6,14,'#b7d6e1');}
  ctx.save();ctx.translate(480+Math.sin((s.time||0)/5)*5,291);
  ctx.fillStyle='#d5cea7';ctx.strokeStyle='#f5ebc1';ctx.lineWidth=4;
  ctx.beginPath();ctx.moveTo(-160,-21);ctx.quadraticCurveTo(-196,0,-160,21);ctx.lineTo(132,21);ctx.quadraticCurveTo(196,0,132,-21);ctx.closePath();ctx.fill();ctx.stroke();
  rect(ctx,-26,-42,60,21,'#b5b39c');rect(ctx,1,-60,7,18,'#c9c8ae');
  for(const dx of [-108,-52,50,109]){ctx.beginPath();ctx.arc(dx,1,6,0,Math.PI*2);ctx.fillStyle='#507d89';ctx.fill();}
  ctx.restore();
  readout(ctx,25,'DEPTH (MODEL)',fmt(s.depth,1)+' m',222);
  readout(ctx,271,'PRESSURE',fmt(s.pressure/100000,2)+' bar',215);
  readout(ctx,720,'GROUND TRACK',fmt(s.trackDeg??s.heading)+'°',210);
  const sample=C.seabed(bathymetry,s);
  if(sample){panel(ctx,23,412,453,67);t(ctx,'NOAA GRID CELL · '+fmt(sample.depth)+' m',39,441,18);t(ctx,'Single sample only; not continuous seabed',39,463,14,'#b8dadf');}
  panel(ctx,540,397,390,99);t(ctx,'WATER / GROUND SPEED',556,425,14,'#a7d7df','800');
  t(ctx,fmt(s.speed,2)+' kn / '+fmt(s.groundSpeedKnots??s.speed,2)+' kn',556,459,24);
  t(ctx,'Current '+fmt(s.currentKnots??0,2)+' kn toward '+fmt(s.currentToward??90)+'°',556,483,14,'#d1e4e7');
  t(ctx,'PROCEDURAL VESSEL · NOT A CAMERA / SONAR IMAGE',480,522,14,'#d4e8e8','700','center');
 }
 function draw(){
  if(view!=='outside'||!state||!canvases[mode]?.ctx)return;
  const c=canvases[mode],ctx=c.ctx;ctx.clearRect(0,0,960,540);
  try{if(mode==='flight')flight(ctx,state);else if(mode==='train')train(ctx,state);else sub(ctx,state);}
  catch(e){caption.textContent='Illustrated view is unavailable; Instrument view remains available.';console.error('Transit scene:',e);}
  c.canvas.setAttribute('aria-label',mode+' illustrated procedural scene driven by simulation state. This is not real terrain or recorded vehicle video.');
 }
 let pendingDraw=false;
 function scheduleDraw(){
  if(view!=='outside'||pendingDraw)return;
  pendingDraw=true;
  const next=()=>{pendingDraw=false;draw();};
  if(typeof requestAnimationFrame==='function')requestAnimationFrame(next);
  else next();
 }
 function choose(next){
  view=next;
  $('cv-instruments').setAttribute('aria-pressed',String(view==='instrument'));
  $('cv-outside').setAttribute('aria-pressed',String(view==='outside'));
  for(const value of Object.values(canvases))value.stage.classList.toggle('cv-active',view==='outside');
  caption.textContent=view==='outside'?'Moving scenery is procedural. Published stations or one nearby NOAA grid sample appear only when loaded. Not a camera view or geographic terrain render.':'Instrument readings are simulated and are not operational vehicle sensors.';
  scheduleDraw();
 }
 $('cv-instruments').addEventListener('click',()=>choose('instrument'));
 $('cv-outside').addEventListener('click',()=>choose('outside'));
 root.addEventListener('leh-transit-route-selected',event=>{route=event.detail?.route||null;scheduleDraw();});
 root.addEventListener('leh-transit-route-cleared',()=>{route=null;scheduleDraw();});
 root.addEventListener('leh-transit-seabed-sample',event=>{bathymetry=event.detail?.sample||null;scheduleDraw();});
 root.addEventListener('leh-transit-flight-terrain-samples',event=>{terrainSamples=event.detail?.samples||[];scheduleDraw();});
 root.addEventListener('leh-transit-dispatch-update',event=>{dispatchState=event.detail||null;scheduleDraw();});
 root.addEventListener('leh-transit-state',event=>{if(!event.detail?.state)return;mode=event.detail.mode;state=event.detail.state;observing=event.detail.observing;scheduleDraw();});
 if(root.transitLatest){mode=root.transitLatest.mode;state=root.transitLatest.state;}
 choose('instrument');
})();
