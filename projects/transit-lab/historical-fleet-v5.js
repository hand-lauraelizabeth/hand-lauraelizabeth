/* Historically sourced vehicle choices, original schematic graphics, and bounded teaching dynamics.
   Public museum and naval facts are never treated as calibrated vehicle-control data. */
const TransitFleetV5=(()=>{
 'use strict';
 const flights={
  fordtrimotor:{
   id:'fordtrimotor',label:'Ford 5-AT Tri-Motor · 1928',year:1928,shape:'trimotor',
   source:'https://airandspace.si.edu/air-and-space-quarterly/issue-17/ford_trimotor_centennial',
   facts:['Three-engine, corrugated-metal commercial transport','Museum reference: 74 ft wingspan and 132 mph maximum speed'],
   assumptions:'Mass, aerodynamic coefficients, thrust, stall threshold, and starting altitude are illustrative; the 132 mph published maximum is a reference, not a full flight envelope.',
   model:{name:'Ford Tri-Motor · museum maximum-speed reference',mass:6100,wing:72,cd0:.042,k:.055,thrust:27000,clMax:1.7,speed:41,alt:1300,throttle:57,maxSpeed:132*.44704}
  },
  spirit:{
   id:'spirit',label:'Ryan NYP Spirit of St. Louis · 1927',year:1927,shape:'monoplane',
   source:'https://airandspace.si.edu/collection-objects/ryan-nyp-spirit-st-louis-charles-lindbergh/nasm_A19280021000',
   additionalSource:'https://aeroresourcesinc.com/uploads/200205-1927%20Ryan%20NYP%20Spirit%20of%20St.%20Louis.pdf',
   facts:['1927 transatlantic aircraft; Smithsonian takeoff weight 5,135 lb','Original design reference: 46 ft wingspan'],
   assumptions:'Historic takeoff weight is used as a point-mass reference. Wing area, aerodynamic coefficients, thrust, the illustrative 112 mph cap, and controls are not a reconstruction of its 1927 flight.',
   model:{name:'Ryan NYP · historical takeoff mass',mass:5135*.45359237,wing:30,cd0:.038,k:.055,thrust:8200,clMax:1.65,speed:39,alt:1200,throttle:56,maxSpeed:112*.44704}
  }
 };
 const trains={
  r1:{
   id:'r1',label:'IND R1 City Car · 1930–1931',year:1930,shape:'subway',
   source:'https://www.nytransitmuseum.org/vintage-fleet/',
   facts:['R1 car #100 built in 1930; historical service 1931–1970','Early steel fleet for New York City IND subway service'],
   assumptions:'The 40 mph model ceiling, traction and service braking are teaching parameters, not published R1 tests or historic signal restrictions.',
   model:{name:'IND R1 · historic car, modeled handling',limit:40*.44704,traction:.72,brake:.88}
  },
  r32:{
   id:'r32',label:'NYCT R32 Brightliner · 1964',year:1964,shape:'stainless',
   source:'https://www.nytransitmuseum.org/R32/',
   additionalSource:'https://www.nytransitmuseum.org/program/r32s/',
   facts:['600 stainless-steel R32 subway cars purchased in 1964','Fleet remained in service until 2022'],
   assumptions:'The 50 mph model ceiling and modeled acceleration/braking are classroom estimates, not R32 acceptance-test data or real-world line limits.',
   model:{name:'NYCT R32 · historic fleet, modeled handling',limit:50*.44704,traction:.95,brake:1.05}
  },
  mallard:{
   id:'mallard',label:'LNER A4 Mallard · 1938',year:1938,shape:'streamline',
   source:'https://blog.railwaymuseum.org.uk/mallard-streamlined-for-speed/',
   facts:['Streamlined A4 steam locomotive no. 4468','Reached 126 mph on 3 July 1938 in a record run'],
   assumptions:'The normal classroom ceiling is 75 mph, deliberately NOT the 126 mph record. The model has generic constant traction/braking, not steam boiler, consist, adhesion or 1938 railway rules.',
   model:{name:'LNER A4 Mallard · record-era reference',limit:75*.44704,traction:.48,brake:.82}
  }
 };
 const subs={
  holland:{
   id:'holland',label:'USS Holland (SS-1) · 1900',year:1900,shape:'early',
   source:'https://www.americanhistory.si.edu/subs/history/subsbeforenuc/early/holland.html',
   additionalSource:'https://www.history.navy.mil/research/histories/ship-histories/danfs/h/holland-i.html',
   facts:['First submarine purchased by the U.S. Navy in 1900','Smithsonian: approximately 5 kn submerged and 8 kn on the surface'],
   assumptions:'The 5 kn submerged ceiling is a historical reference. The acceleration lag and ballast response remain generic teaching mechanics.',
   capKnots:5,responseKnotsPerSec:.12,startingSpeed:2
  },
  albacore:{
   id:'albacore',label:'USS Albacore (AGSS-569) · 1953',year:1953,shape:'teardrop',
   source:'https://www.history.navy.mil/research/histories/ship-histories/danfs/a/albacore-agss-569-iii.html',
   additionalSource:'https://www.ussalbacore.org/uss-albacore',
   facts:['Commissioned in 1953 as an experimental submarine','Hydrodynamic teardrop hull; Navy history lists submerged speed above 20 kn'],
   assumptions:'The simulator is capped at its 20 kn interface ceiling, not Albacore’s maximum. Acceleration, ballast, pressure rating and turning are not calibrated.',
   capKnots:20,responseKnotsPerSec:.32,startingSpeed:3
  }
 };
 const fleet={flight:flights,train:trains,sub:subs};
 const cap=(x,a,b)=>Math.max(a,Math.min(b,x));
 function entry(kind,id){return fleet[kind]?.[id]||null;}
 function nextSubSpeed(prior,requested,dt,id){
  const cfg=subs[id];if(!cfg)return Number(requested)||0;
  const target=cap(Number(requested)||0,0,cfg.capKnots),previous=Number.isFinite(prior)?cap(prior,0,cfg.capKnots):Math.min(cfg.startingSpeed,target);
  const delta=cap(target-previous,-cfg.responseKnotsPerSec*cap(dt,0,2),cfg.responseKnotsPerSec*cap(dt,0,2));
  return cap(previous+delta,0,cfg.capKnots);
 }
 function railCeiling(id){return trains[id]?.model.limit??null;}
 // Existing historical choices also require recognizable visual types.
 const legacy={
  flight:{dc3:{id:'dc3',label:'Douglas DC-3 · 1935',shape:'twin'}},
  train:{gg1:{id:'gg1',label:'PRR GG1 electric · 1934',shape:'electric'},
   r160:{id:'r160',label:'NYCT R160 · 2011 reference',shape:'stainless'}},
  sub:{gato:{id:'gato',label:'USS Harder · Gato class (1943)',shape:'wwii'},
   nautilus:{id:'nautilus',label:'USS Nautilus SSN-571 · 1954',shape:'nuclear'}}
 };
 function artwork(kind,id){return entry(kind,id)||legacy[kind]?.[id]||null;}

 function silhouette(kind,id){
  const a=artwork(kind,id);if(!a)return '';
  let art='';
  if(kind==='flight'){
   const wings='<path d="M80 86 L240 77 L318 77 L540 86 L510 99 L327 100 L276 109 L100 100 Z" fill="#d8e5e6" stroke="#507781" stroke-width="3"/>';
   const body='<path d="M275 39 Q301 17 320 39 L327 122 L310 142 L286 126 Z" fill="#e9f0e9" stroke="#456570" stroke-width="3"/><path d="M260 127 L347 127 L339 143 L265 143Z" fill="#c3d9d7" stroke="#456570" stroke-width="3"/>';
   if(a.shape==='trimotor'||a.shape==='twin'){
    art=wings+body;
    for(const x of (a.shape==='twin'?[232,400]:[205,308,414]))art+='<circle cx="'+x+'" cy="86" r="19" fill="#657a85" stroke="#deefe6" stroke-width="4"/><path d="M'+x+' 57 L'+x+' 115 M'+(x-28)+' 86 L'+(x+28)+' 86" stroke="#819a9c" stroke-width="3"/>';
    for(let x=128;x<515;x+=21)art+='<path d="M'+x+' 87 l-7 8" stroke="#90aeb1" stroke-width="1"/>';
   }else{
    art=wings.replace('M80 86 L240 77 L318 77 L540 86 L510 99 L327 100 L276 109 L100 100','M95 88 L254 78 L323 78 L525 88 L500 101 L325 101 L287 110 L114 101')+body;
    art+='<circle cx="302" cy="62" r="16" fill="#c9d5b7" stroke="#4f7772" stroke-width="4"/><path d="M300 28 L302 95 M270 61 L330 61" stroke="#45696e" stroke-width="3"/>';
   }
  }else if(kind==='train'){
   if(a.shape==='streamline'){
    art='<path d="M98 112 L142 81 L330 81 Q375 89 387 120 L387 135 L95 135Z" fill="#25476e" stroke="#abc4d1" stroke-width="5"/><path d="M157 81 Q249 65 335 78" fill="none" stroke="#eef1d3" stroke-width="4"/><path d="M391 115H514V135H391Z" fill="#475f78"/>';
    for(const x of [162,236,310,426,480])art+='<circle cx="'+x+'" cy="142" r="20" fill="#283a4b" stroke="#aac3bd" stroke-width="5"/>';
    art+='<path d="M118 102 Q145 91 174 96" stroke="#cc9a40" stroke-width="5" fill="none"/>';
   }else if(a.shape==='electric'){
    art='<path d="M80 81 L137 57 H488 L542 81 V137 H80Z" fill="#39566b" stroke="#e5ecdc" stroke-width="5"/><path d="M188 57 L216 29 L247 57 M362 57 L388 29 L423 57" fill="none" stroke="#cfdfdf" stroke-width="5"/><rect x="107" y="82" width="96" height="33" fill="#102e46"/><rect x="416" y="82" width="96" height="33" fill="#102e46"/>';
    for(const x of [130,225,325,420,502])art+='<circle cx="'+x+'" cy="142" r="17" fill="#24394d" stroke="#c1d0cf" stroke-width="5"/>';
   }else{
    art='<rect x="74" y="52" width="474" height="82" rx="12" fill="'+(a.shape==='stainless'?'#a9b9c0':'#467a5e')+'" stroke="#e5ecdc" stroke-width="5"/>';
    for(let x=94;x<526;x+=55){art+='<rect x="'+x+'" y="68" width="40" height="35" rx="3" fill="#122f45" stroke="#d3e2da" stroke-width="2"/>';}
    for(const x of [168,440])art+='<rect x="'+x+'" y="106" width="6" height="27" fill="#e4e6d7"/>';
    if(a.shape==='stainless')for(let y=117;y<132;y+=6)art+='<path d="M80 '+y+'H540" stroke="#edf1f0" stroke-width="2"/>';
    for(const x of [128,230,390,492])art+='<circle cx="'+x+'" cy="144" r="13" fill="#182f40" stroke="#dce7db" stroke-width="4"/>';
   }
   art+='<path d="M40 160H582" stroke="#6ea39a" stroke-width="5"/>';
  }else{
   if(a.shape==='early'||a.shape==='wwii'){
    art='<path d="M80 118 Q55 90 85 73 L462 73 Q527 82 531 112 L487 128 L97 128Z" fill="#728486" stroke="#e3e8d8" stroke-width="5"/><rect x="288" y="41" width="54" height="41" rx="8" fill="#9facaa"/><path d="M314 41V20" stroke="#c4d5d1" stroke-width="6"/>';
   }else{
    art='<path d="M48 107 Q90 56 299 71 Q510 73 564 107 Q512 138 297 138 Q95 141 48 107Z" fill="#7f9fa4" stroke="#dcebe4" stroke-width="5"/><path d="M275 78 L290 31 Q313 17 331 37 L345 81Z" fill="#a5bdbc"/>';

   }
   art+='<path d="M565 107L594 85M565 107L594 132" stroke="#c3d6d3" stroke-width="4"/>';
  }
  return '<svg viewBox="0 0 620 174" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg"><rect width="620" height="174" rx="14" fill="#092338"/><circle cx="530" cy="32" r="61" fill="#2e6676" opacity=".3"/><path d="M0 155H620" stroke="#39778a" stroke-width="1"/>'+art+'</svg>';
 }
 function drawBadge(ctx,kind,id,x=690,y=156){
  const cfg=artwork(kind,id);if(!cfg)return false;
  ctx.save();ctx.fillStyle='#0a2334ed';ctx.strokeStyle='#8cb3b8';ctx.lineWidth=2;
  ctx.beginPath();ctx.roundRect(x-16,y-22,270,113,11);ctx.fill();ctx.stroke();
  ctx.fillStyle='#9fdbd2';ctx.font='700 12px system-ui,sans-serif';ctx.fillText('SELECTED HISTORICAL VEHICLE',x,y+1);
  const label=cfg.label.length>29?cfg.label.slice(0,28)+'…':cfg.label;
  ctx.fillStyle='#fff7d9';ctx.font='700 15px system-ui,sans-serif';ctx.fillText(label,x,y+28);
  ctx.fillStyle='#d3e6e2';ctx.font='11px system-ui,sans-serif';ctx.fillText('SCHEMATIC SHAPE · NOT TO SCALE',x,y+47);
  // Small shape key reflects vehicle type. It is an annotation, not an outside-camera view.
  ctx.strokeStyle='#f0dba9';ctx.fillStyle='#88b4bf';ctx.lineWidth=3;
  if(kind==='flight'){
   ctx.beginPath();ctx.moveTo(x+16,y+71);ctx.lineTo(x+110,y+71);
   ctx.moveTo(x+63,y+55);ctx.lineTo(x+63,y+84);ctx.moveTo(x+37,y+86);ctx.lineTo(x+86,y+86);ctx.stroke();
   const count=cfg.shape==='trimotor'?3:cfg.shape==='twin'?2:1;
   for(let i=0;i<count;i++){const pos=count===3?x+36+i*27:count===2?x+41+i*44:x+63;
    ctx.beginPath();ctx.arc(pos,y+71,6,0,Math.PI*2);ctx.fill();}
  }else if(kind==='train'){
   if(cfg.shape==='streamline'){
    ctx.beginPath();ctx.moveTo(x+15,y+82);ctx.lineTo(x+35,y+63);ctx.lineTo(x+111,y+62);ctx.lineTo(x+130,y+82);ctx.closePath();ctx.fill();ctx.stroke();
   }else{
    ctx.fillRect(x+18,y+63,115,23);
    if(cfg.shape==='electric'){ctx.beginPath();ctx.moveTo(x+45,y+63);ctx.lineTo(x+64,y+53);ctx.lineTo(x+84,y+63);ctx.stroke();}
   }
   for(const off of [39,75,112]){ctx.beginPath();ctx.arc(x+off,y+87,5,0,Math.PI*2);ctx.fill();}
  }else{
   ctx.beginPath();ctx.ellipse(x+75,y+74,cfg.shape==='early'?56:67,cfg.shape==='wwii'?9:15,0,0,Math.PI*2);ctx.fill();ctx.stroke();
   ctx.fillRect(x+70,y+57,cfg.shape==='early'?14:22,13);
  }
  ctx.fillStyle='#accfc8';ctx.font='12px system-ui,sans-serif';ctx.fillText('Model-driven view',x+144,y+76);
  ctx.restore();return true;
 }
 function drawHull(ctx,id){
  const cfg=artwork('sub',id);if(!cfg)return false;
  ctx.fillStyle=id==='holland'?'#90978c':id==='gato'?'#667e81':'#a4b6b4';
  ctx.strokeStyle='#e0e9dc';ctx.lineWidth=4;ctx.beginPath();
  if(id==='holland'){
   ctx.moveTo(-134,-17);ctx.quadraticCurveTo(-166,0,-134,17);
   ctx.lineTo(108,17);ctx.quadraticCurveTo(149,4,108,-17);
  }else if(id==='gato'){
   ctx.moveTo(-172,-3);ctx.quadraticCurveTo(-154,-26,-118,-24);
   ctx.lineTo(125,-24);ctx.quadraticCurveTo(172,-12,174,3);
   ctx.quadraticCurveTo(140,29,80,27);ctx.lineTo(-112,26);ctx.quadraticCurveTo(-168,19,-172,-3);
  }else{
   ctx.moveTo(-183,0);ctx.bezierCurveTo(-145,-39,135,-43,183,0);
   ctx.bezierCurveTo(132,42,-143,39,-183,0);
  }
  ctx.closePath();ctx.fill();ctx.stroke();ctx.fillStyle='#c5d6cd';
  if(id==='holland'){ctx.fillRect(-4,-47,53,33);ctx.fillRect(16,-64,5,17);}
  else if(id==='gato'){
   ctx.fillRect(-22,-47,58,22);ctx.fillRect(-1,-62,11,15);
   ctx.beginPath();ctx.moveTo(-164,-25);ctx.lineTo(151,-25);ctx.strokeStyle='#c7d1c7';ctx.lineWidth=3;ctx.stroke();
  }else{
   ctx.beginPath();ctx.moveTo(-14,-26);ctx.lineTo(3,-69);ctx.lineTo(33,-68);ctx.lineTo(50,-26);ctx.closePath();ctx.fill();
   ctx.fillRect(15,-82,4,16);
   if(id==='nautilus'){ctx.beginPath();ctx.moveTo(-157,-9);ctx.lineTo(-184,-21);ctx.moveTo(-157,9);ctx.lineTo(-184,21);ctx.stroke();}
  }
  ctx.strokeStyle='#dfe7db';ctx.lineWidth=4;ctx.beginPath();
  ctx.moveTo(176,-6);ctx.lineTo(202,-30);ctx.moveTo(176,6);ctx.lineTo(202,30);ctx.stroke();
  return true;
 }
 return {flights,trains,subs,fleet,entry,artwork,nextSubSpeed,railCeiling,silhouette,drawBadge,drawHull};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitFleetV5;
(function installHistoricalFleetV5(){
 'use strict';
 if(typeof document==='undefined'||typeof TransitModels==='undefined'||typeof TransitHistorical==='undefined')return;
 const root=document.getElementById('leh-transit');if(!root||root.dataset.historicalFleetV5==='ready')return;
 root.dataset.historicalFleetV5='ready';
 const F=TransitFleetV5,M=TransitModels,H=TransitHistorical,$=id=>document.getElementById(id);
 for(const [kind,profiles] of Object.entries(F.fleet)){
  for(const [id,entry] of Object.entries(profiles)){
   H.references[id]={label:entry.label,source:entry.source,additionalSource:entry.additionalSource,
    facts:entry.facts,assumptions:entry.assumptions};
   if(kind==='flight')M.AIRCRAFT[id]={...entry.model};
   if(kind==='train')M.TRAINS[id]={...entry.model};
  }
 }
 function addOption(id,value,label){
  const select=$(id);if(!select||Array.from(select.options).some(o=>o.value===value))return;
  const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o);
 }
 for(const e of Object.values(F.flights))addOption('tl-plane',e.id,e.label);
 for(const e of Object.values(F.trains))addOption('tl-train-profile',e.id,e.label);
 for(const e of Object.values(F.subs))addOption('hr-sub-vehicle',e.id,e.label);
 const style=document.createElement('style');
 style.textContent='#leh-transit .hf-preview{margin:.65rem 0;padding:.68rem;border-radius:11px;background:#0c2639;color:#e7f4ee;box-shadow:0 5px 14px #0c263916}#leh-transit .hf-preview svg{width:100%;height:auto;display:block;max-height:155px}#leh-transit .hf-preview h4{font:700 1rem Georgia,serif;color:#f4f8ea;margin:.35rem 0}#leh-transit .hf-preview p{font:.84rem/1.45 system-ui,sans-serif;color:#c1dedc;margin:.4rem 0}#leh-transit .hf-preview .hf-facts{font:.79rem/1.5 system-ui,sans-serif;margin:.35rem 0;padding-left:1.1rem;color:#e2ede2}#leh-transit .hf-preview a{color:#e5d9a1;text-decoration:underline;text-underline-offset:3px}#leh-transit .hf-warning{font:.8rem/1.5 system-ui,sans-serif;background:#fff4d9;color:#503e19;border-left:4px solid #c4942c;padding:.55rem .7rem;border-radius:5px;margin:.5rem 0}';
 document.head.append(style);
 const hosts={flight:$('tl-flight-controls'),train:$('tl-train-controls'),sub:$('tl-sub-controls')},cards={};
 for(const [mode,host] of Object.entries(hosts)){
  if(!host)continue;
  const card=document.createElement('section');card.className='hf-preview';card.id='hf-'+mode+'-preview';card.setAttribute('aria-label','Historic vehicle illustration and provenance');
  host.insertBefore(card,host.querySelector('.hr-panel')||null);cards[mode]=card;
 }
 let routeActive=false;
 function currentId(kind){return kind==='flight'?$('tl-plane')?.value:kind==='train'?$('tl-train-profile')?.value:$('hr-sub-vehicle')?.value;}
 function updateCard(kind){
  const host=cards[kind],id=currentId(kind),cfg=F.artwork(kind,id);if(!host)return;
  if(!cfg){host.hidden=true;return;}host.hidden=false;
  const historical=H.references[id]||cfg,facts=(historical.facts||[]).map(x=>'<li>'+x+'</li>').join('');
  const source=historical.source||cfg.source||'',boundary=historical.assumptions||cfg.assumptions||'Vehicle performance remains an educational model.';
  const railSpec=M.TRAINS[id],subCap=F.subs[id]?.capKnots??(id==='gato'?8.75:20);
  const limit=kind==='train'?'Vehicle model ceiling: '+Math.round((railSpec?.limit||0)/.44704)+' mph; not a route speed limit.':
   kind==='sub'?'Submerged model speed ceiling: '+subCap+' kn; not a depth or safety rating.':
   'Point-mass aircraft handling uses published references and illustrative parameters.';
  host.innerHTML=F.silhouette(kind,id)+'<h4>'+cfg.label+'</h4><ul class="hf-facts">'+facts+'</ul>'+
    '<p>'+limit+'</p><p><strong>Model boundary:</strong> '+boundary+'</p>'+
    (source?'<p><a href="'+source+'" target="_blank" rel="noopener noreferrer">View the historical source</a></p>':'')+
    (kind==='train'&&routeActive?'<p class="hf-warning">Selected published route data describes a modern service line, not an authenticated historical journey. Vehicle-specific signals and limits are not imported.</p>':'');
 }
 function clampVessel(){
  const id=currentId('sub'),cfg=F.subs[id],slider=$('tl-sub-speed');if(!slider)return;
  if(cfg){
   slider.max=String(cfg.capKnots);slider.step=cfg.capKnots<=5?'.25':'.5';
   if(Number(slider.value)>cfg.capKnots){slider.value=String(cfg.capKnots);slider.dispatchEvent(new Event('input',{bubbles:true}));}
  }else if(id==='gato'){slider.max='8.75';slider.step='.25';}
  else{slider.max='20';slider.step='1';}
  root.dataset.fleetSub=id||'generic';
 }
 function renderAll(){updateCard('flight');updateCard('train');updateCard('sub');}
 $('tl-plane')?.addEventListener('change',()=>updateCard('flight'));
 $('tl-train-profile')?.addEventListener('change',()=>updateCard('train'));
 $('hr-sub-vehicle')?.addEventListener('change',()=>{clampVessel();updateCard('sub');root.dispatchEvent(new CustomEvent('leh-transit-fleet-change',{detail:{mode:'sub',profile:currentId('sub')}}));});
 root.addEventListener('leh-transit-route-selected',event=>{routeActive=Boolean(event.detail?.route);updateCard('train');});
 root.addEventListener('leh-transit-route-cleared',()=>{routeActive=false;updateCard('train');});
 const previous=M.subStep;
 M.subStep=(state,dt)=>{
  const id=currentId('sub'),cfg=F.subs[id];if(!cfg)return previous(state,dt);
  const target=state.speed,actual=F.nextSubSpeed(state.hullSpeedKnots,target,dt,id);
  const next=previous({...state,speed:actual},dt);
  return {...next,requestedSpeedKnots:Math.min(cfg.capKnots,Math.max(0,target)),hullSpeedKnots:actual,vesselProfile:id};
 };
 root.addEventListener('leh-transit-state',event=>{
  const d=event.detail;if(!d?.state)return;
  if(d.mode==='sub'&&d.state.time===0)clampVessel();
  const id=d.mode==='sub'?currentId('sub'):d.state.profile;
  const chosen=F.artwork(d.mode,id),badge=$('tl-mode-label');
  if(chosen&&badge){
   const label=chosen.label.split(' · ')[0];
   badge.textContent=label+' · '+(d.mode==='train'&&d.state.routeName?'mapped-route model':'simulated model');
  }
 });
 clampVessel();renderAll();
})();