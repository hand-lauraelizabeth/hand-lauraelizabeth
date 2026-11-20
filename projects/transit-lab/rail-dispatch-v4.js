/* Transit Lab railway dispatcher: model-only score, dwell, stop and GTFS timing.
   Published service times and station coordinates never become live train telemetry. */
const TransitDispatch=(()=>{
'use strict';
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
const finite=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
function targets(route,length,modelStops){
 const n=Number.isFinite(route?.lengthM)?route.lengthM:length;
 if(!Number.isFinite(n)||n<100)throw Error('Valid route length required.');
 const stations=Array.isArray(route?.stations)?route.stations:[];
 let all=stations.filter(s=>finite(s.distanceM)&&Number(s.distanceM)>=35&&Number(s.distanceM)<=n+3)
  .map(s=>{
   const arrival=finite(s.arrivalSec)?Number(s.arrivalSec):null,departure=finite(s.departureSec)?Number(s.departureSec):null;
   const dwell=arrival!==null&&departure!==null&&departure-arrival>=5&&departure-arrival<=300?departure-arrival:15;
   return {id:String(s.id||s.name||'station'),name:String(s.name||'Mapped station').slice(0,90),distance:clamp(Number(s.distanceM),0,n),scheduled:finite(s.scheduledElapsedSec)?Number(s.scheduledElapsedSec):null,dwell,sourceDwell:dwell!==15&&arrival!==null?'GTFS stop_times':'Classroom default'};
  });
 if(!all.length&&!route){
  all=(modelStops||[2500,5500,10000]).filter(x=>finite(x)&&x>=35&&x<=n+3).map(x=>({id:'model-'+x,name:'Illustrative '+(Number(x)/1000).toFixed(2)+' km station',distance:clamp(Number(x),0,n),scheduled:null,dwell:15,sourceDwell:'Classroom default'}));
 }
 if(!all.length){all=[{id:'segment-end',name:route?'Mapped segment endpoint':'Model route endpoint',distance:n,scheduled:null,dwell:15,sourceDwell:'Classroom default'}];}
 all.sort((a,b)=>a.distance-b.distance);
 let dedup=[];for(const t of all){if(dedup.length&&Math.abs(t.distance-dedup.at(-1).distance)<25)continue;dedup.push(t);}
 if(dedup.at(-1).distance<n-25){
  dedup.push({id:'segment-end',name:route?'Mapped segment endpoint':'Model route endpoint',distance:n,scheduled:null,dwell:15,sourceDwell:'Classroom default'});
 }
 return dedup;
}
function create(route,length,stops){
 const t=targets(route,length,stops);
 return {routeName:route?.name||'Generic railway',source:route?.trip?'Published GTFS trip':route?.stations?.length?'Published service-line station geometry':route?'Mapped line geometry':'Illustrative model markers',
  targets:t,cursor:0,phase:'approach',score:100,completed:0,skipped:0,extraTime:0,doorsSince:null,arrivalTime:null,arrivalDelta:null,
  logs:[],lastState:null,tractionWeightedM:0,peakAcceleration:0,fastest:0,latestStop:null,guardViolations:0};
}
const clock=(run,s)=>Number(s.time||0)+run.extraTime;
function event(run,message,when){run.logs.push({time:when,message});if(run.logs.length>100)run.logs.shift();}
function penalty(run,amount,reason,when){run.score=clamp(run.score-amount,0,100);event(run,'−'+amount+' points: '+reason,when);}
function next(run){return run.targets[run.cursor]||null;}
function skip(run,s,reason){
 const current=next(run);if(!current)return;
 const when=clock(run,s);run.skipped++;penalty(run,22,'Missed '+current.name+' ('+reason+')',when);
 run.cursor++;run.phase=run.cursor>=run.targets.length?'finished':'approach';
 if(run.phase==='finished')event(run,'Run ended with missed target(s).',when);
}
function advance(run,s){
 if(!run||!s||!Number.isFinite(s.pos)||!Number.isFinite(s.speed)||!Number.isFinite(s.time))return run;
 const prev=run.lastState,now=clock(run,s);
 if(prev&&s.time<prev.time-.001)throw Error('Model clock reset: create a new dispatch run.');
 if(prev&&s.pos>=prev.pos){
  const delta=s.pos-prev.pos;run.tractionWeightedM+=delta*clamp(Number(s.throttle)||0,0,100)/100;
 }
 run.peakAcceleration=Math.max(run.peakAcceleration,Math.abs(Number(s.accel)||0));
 run.fastest=Math.max(run.fastest,s.speed);
 run.lastState={time:s.time,pos:s.pos,speed:s.speed};
 if(run.phase==='finished')return run;
 const current=next(run);if(!current){run.phase='finished';return run;}
 if(run.phase==='doors-open')return run;
 if(run.phase==='at-platform'){
  if(s.pos>current.distance+15)skip(run,s,'departed before passenger-service doors opened');
  return run;
 }
 while(run.phase==='approach'){
  const target=next(run);if(!target){run.phase='finished';break;}
  if(s.pos>target.distance+15||target.distance===s.length&&s.terminalOverrun&&s.pos>=target.distance-.1){
   skip(run,s,'passed platform or overran the model endpoint');continue;
  }
  if(Math.abs(s.pos-target.distance)<=15&&s.speed<=.5&&s.time>0){
   run.phase='at-platform';run.arrivalTime=now;
   run.arrivalDelta=target.scheduled===null?null:now-target.scheduled;
   const error=Math.abs(s.pos-target.distance);
   const precisionPenalty=Math.min(8,Math.floor(error/3));
   if(precisionPenalty)penalty(run,precisionPenalty,'platform alignment '+error.toFixed(1)+' m from the target',now);
   if(run.arrivalDelta!==null){
    const timingPenalty=Math.min(12,Math.floor(Math.max(0,Math.abs(run.arrivalDelta)-30)/60)*2);
    if(timingPenalty)penalty(run,timingPenalty,'published arrival offset '+Math.round(run.arrivalDelta)+' s',now);
   }
   event(run,'Platform stop at '+target.name+'; alignment '+error.toFixed(1)+' m; open passenger doors.',now);
   break;
  }
  break;
 }
 return run;
}
function openDoors(run,s){
 const station=next(run);
 if(run.phase!=='at-platform'||!station||!s||s.speed>.5||Math.abs(s.pos-station.distance)>15)return false;
 run.phase='doors-open';run.doorsSince=clock(run,s);run.arrivalTime=run.arrivalTime??clock(run,s);
 event(run,'Doors opened at '+station.name,clock(run,s));return true;
}
function dwellRemaining(run,s){
 if(run.phase!=='doors-open')return null;
 return Math.max(0,(next(run)?.dwell||15)-(clock(run,s)-run.doorsSince));
}
function waitDwell(run,s){
 if(run.phase!=='doors-open'||!s)return 0;
 const remaining=dwellRemaining(run,s);
 const credited=Math.max(0,Math.ceil(remaining*10)/10);
 run.extraTime+=credited;
 event(run,'Advanced passenger-service clock '+credited.toFixed(1)+' s while stationary (classroom action).',clock(run,s));
 return credited;
}
function closeDoors(run,s){
 if(run.phase!=='doors-open'||!s||dwellRemaining(run,s)>.05)return false;
 const station=next(run);event(run,'Doors closed after '+(clock(run,s)-run.doorsSince).toFixed(1)+' s at '+station.name,clock(run,s));
 run.completed++;run.latestStop={...station,actualArrival:run.arrivalTime,timetableDelta:run.arrivalDelta};
 run.cursor++;run.phase=run.cursor>=run.targets.length?'finished':'approach';run.doorsSince=null;
 run.arrivalTime=null;run.arrivalDelta=null;
 if(run.phase==='finished')event(run,'Run complete: '+run.completed+' platform services, '+run.skipped+' missed, score '+run.score+'/100.',clock(run,s));
 return true;
}
function report(run){
 return {route:run.routeName,source:run.source,score:run.score,stopsServed:run.completed,missed:run.skipped,stopTotal:run.targets.length,
  phase:run.phase,elapsedS:run.lastState?.time??0,passengerServiceSeconds:run.extraTime,
  tractionWeightedDistanceM:Math.round(run.tractionWeightedM),maximumModelSpeedKmh:Math.round(run.fastest*36)/10,
  peakModelAccelerationMps2:Math.round(run.peakAcceleration*100)/100,
  targets:run.targets.map(x=>({name:x.name,distanceM:x.distance,scheduledElapsedS:x.scheduled,dwellS:x.dwell,sourceDwell:x.sourceDwell})),
  events:run.logs,disclaimer:'Classroom scoring and hypothetical vehicle dynamics only; not train dispatch, published operating constraints, real energy usage, or safe-operation assessment.'};
}
return {targets,create,advance,next,openDoors,waitDwell,closeDoors,dwellRemaining,clock,report};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitDispatch;
(function installDispatch(){
'use strict';
if(typeof document==='undefined'||typeof TransitModels==='undefined')return;
const root=document.getElementById('leh-transit');if(!root||root.dataset.dispatchV4==='ready')return;
root.dataset.dispatchV4='ready';
const $=id=>document.getElementById(id),D=TransitDispatch,M=TransitModels;
const style=document.createElement('style');
style.textContent='#leh-transit .rd-panel{display:grid;gap:.65rem}#leh-transit .rd-panel .rd-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.5rem}#leh-transit .rd-panel .rd-metric{border:1px solid #b7d8ca;border-radius:9px;padding:.65rem;background:#eaf5ef}#leh-transit .rd-panel .rd-metric span,#leh-transit .rd-panel .rd-metric strong{display:block}#leh-transit .rd-panel .rd-metric span{font-size:.71rem;color:#436c5d}#leh-transit .rd-panel .rd-metric strong{font-size:1.25rem;font-variant-numeric:tabular-nums}#leh-transit .rd-panel .rd-signal{padding:.7rem;background:#173d4a;color:#f3fff7;border-radius:9px;font-size:.92rem;line-height:1.5}#leh-transit .rd-panel .rd-signal.dwell{background:#345c41}#leh-transit .rd-panel .rd-signal.warn{background:#74422c}#leh-transit .rd-panel .rd-meter{width:100%;height:.7rem;accent-color:#327f65}#leh-transit .rd-panel .rd-help{font-size:.83rem;color:var(--muted);line-height:1.5}#leh-transit .rd-panel details summary{cursor:pointer;font-weight:700}#leh-transit .rd-panel ol{max-height:170px;overflow:auto;margin:.55rem 0;padding-left:1.3rem;font-size:.8rem}#leh-transit .rd-panel .rd-buttons{display:flex;gap:.5rem;flex-wrap:wrap}#leh-transit .rd-panel .rd-buttons button{min-width:105px}#leh-transit .rd-cab-overlay{display:none;position:absolute;left:8%;right:8%;bottom:4%;padding:.45rem .6rem;border:1px solid #b0dace8a;border-radius:7px;background:#081c2dea;color:#f9f8e6;font:750 clamp(11px,1.7vw,15px)/1.25 system-ui,sans-serif;text-align:center;z-index:2;pointer-events:none}#leh-transit .tv-stage.cv-active>.rd-cab-overlay{display:block}@media(max-width:550px){#leh-transit .rd-panel .rd-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}#leh-transit .rd-cab-overlay{bottom:6%;font-size:11px}}';
document.head.append(style);
const panel=document.createElement('section');panel.id='rd-panel';panel.className='panel rd-panel';
panel.innerHTML='<div class="top"><div><p class="eyebrow">Play the line</p><h2>Rail dispatch &amp; passenger-service challenge</h2></div><span class="pill">Simulated score</span></div>'+
'<p class="rd-help">Drive to each named station or exercise marker, stop within ±15 m at or below 0.5 m/s, open the doors, complete the modeled dwell, then depart. Missing a station reduces your score. When an official GTFS trip is selected, published arrival times and service calls inform the challenge; all scoring thresholds and vehicle controls are classroom assumptions.</p>'+
'<div class="rd-metrics"><div class="rd-metric"><span>Learning score</span><strong id="rd-score">100 / 100</strong></div><div class="rd-metric"><span>Stops served</span><strong id="rd-stops">0 / 3</strong></div><div class="rd-metric"><span>Distance to target</span><strong id="rd-distance">—</strong></div></div>'+
'<p class="rd-signal" id="rd-status" role="status" aria-live="polite">Switch to Railway to begin.</p>'+
'<progress id="rd-progress" class="rd-meter" max="100" value="0" aria-label="Progress toward the next platform"></progress>'+
'<p class="rd-help" id="rd-schedule">The generic scenario uses invented station markers; published station times require GTFS import.</p>'+
'<div class="rd-buttons"><button type="button" id="rd-open" disabled>Open doors</button><button type="button" id="rd-wait" class="secondary" disabled>Advance dwell</button><button type="button" id="rd-close" disabled>Close doors</button><button type="button" id="rd-restart" class="secondary">Restart run</button><button type="button" id="rd-export" class="secondary">Export run report</button></div>'+
'<details><summary>Dispatch event log (<span id="rd-count">0</span>)</summary><ol id="rd-log"></ol></details>'+
'<p class="rd-help">Door interlock prevents the classroom train from moving with doors open. The passenger-service clock is separate from physical simulation time when you select <strong>Advance dwell</strong>. The traction-weighted distance in exported reports is a teaching proxy, not electrical energy.</p>';
const host=root.querySelector('.main-stack');host?.insertBefore(panel,host.children[1]||null);
const scene=$('tl-train-scene')?.querySelector('.tv-stage');
let overlay=null;if(scene){overlay=document.createElement('div');overlay.className='rd-cab-overlay';scene.append(overlay);}
let route=null,run=null,mode='flight',s=null,previousLogCount=0;
function reset(){
 if(mode!=='train')return;
 const latest=root.transitLatest?.state||M.trainInit($('tl-train-profile')?.value||'metro');
 run=D.create(route,latest.length,latest.stops);
 s=latest;previousLogCount=0;
 D.advance(run,latest);show();
}
function renderLog(){
 if(!run)return;
 const li=$('rd-log');li.replaceChildren();
 for(const x of run.logs.slice(-20).reverse()){
  const el=document.createElement('li');el.textContent='T+'+x.time.toFixed(1)+'s · '+x.message;li.append(el);
 }
 $('rd-count').textContent=String(run.logs.length);
}
function show(){
 panel.hidden=mode!=='train';
 if(!run||!s||mode!=='train')return;
 const stop=D.next(run),clock=D.clock(run,s),remain=stop?stop.distance-s.pos:0;
 $('rd-score').textContent=run.score+' / 100';$('rd-stops').textContent=run.completed+' / '+run.targets.length;
 $('rd-distance').textContent=stop?Math.max(0,Math.round(remain))+' m':'—';
 const fraction=stop?Math.max(0,Math.min(100,100-Math.max(0,remain)/Math.max(1,stop.distance-(run.targets[run.cursor-1]?.distance||0))*100)):100;
 $('rd-progress').value=fraction;
 let message='',type='',caption='';
 if(run.phase==='finished'){
  type=run.skipped?'warn':'dwell';message='RUN FINISHED · '+run.completed+' stops served, '+run.skipped+' missed · learning score '+run.score+'/100.';
 }else if(run.phase==='at-platform'){
  type='dwell';message='PLATFORM STOP · '+stop.name+' · open doors to begin passenger service.';
 }else if(run.phase==='doors-open'){
  type='dwell';const left=D.dwellRemaining(run,s);
  message='DOORS OPEN · '+stop.name+' · '+left.toFixed(1)+' simulated seconds of required dwell remaining.';
 }else{
  const spec=M.TRAINS[s.profile],adhesion=Number(s.adhesion)||1,rate=spec.brake*adhesion+.03+M.G*(s.grade||0)/100;
  const brake=rate>0?s.speed*s.speed/(2*rate):Infinity;
  type=remain<Math.max(80,brake+2*s.speed)&&s.speed>.5?'warn':'';
  message='NEXT · '+stop.name+' · '+Math.max(0,Math.round(remain))+' m · '+(Number.isFinite(brake)?Math.round(brake)+' m ideal model brake distance':'brake estimate unavailable')+'.';
 }
 $('rd-status').textContent=message;$('rd-status').className='rd-signal'+(type?' '+type:'');
 if(stop&&stop.scheduled!==null){
  const when=stop.scheduled,arrival=run.phase==='doors-open'||run.phase==='at-platform'?run.arrivalDelta:null;
  caption='PUBLISHED GTFS ARRIVAL: T+'+(when/60).toFixed(1)+' min after initial scheduled departure. '+(arrival===null?'Model service clock T+'+(clock/60).toFixed(1)+' min; this is not an ETA.':'Arrival difference '+(arrival>=0?'+':'')+Math.round(arrival)+' s relative to published arrival.')+' Station stopping position is estimated from geographic geometry.';
 }else caption=run.source+' · No published arrival clock for this target. Current time T+'+(clock/60).toFixed(1)+' min, including manually advanced dwell.';
 $('rd-schedule').textContent=caption;
 const canOpen=run.phase==='at-platform'&&s.speed<=.5;
 $('rd-open').disabled=!canOpen;$('rd-wait').disabled=run.phase!=='doors-open';
 $('rd-close').disabled=run.phase!=='doors-open'||D.dwellRemaining(run,s)>.05;
 $('rd-wait').textContent=run.phase==='doors-open'?'Complete dwell (+'+D.dwellRemaining(run,s).toFixed(0)+' s)':'Advance dwell';
 if(overlay)overlay.textContent=(run.phase==='doors-open'?'DOORS OPEN · ':run.phase==='at-platform'?'BOARDING · ':run.phase==='finished'?'RUN COMPLETE · ':'NEXT · ')+(stop?.name||run.routeName)+' · '+(run.phase==='doors-open'?'HOLD TRAIN':Math.max(0,Math.round(remain))+' m')+' · '+run.score+' pts';
 if(previousLogCount!==run.logs.length){previousLogCount=run.logs.length;renderLog();}
 root.dispatchEvent(new CustomEvent('leh-transit-dispatch-update',{detail:{run,station:stop,clock}}));
}
$('rd-open').addEventListener('click',()=>{
 if(!run||!s||!D.openDoors(run,s))return;
 const assist=$('ex-assist');if(assist&&assist.checked){assist.checked=false;assist.dispatchEvent(new Event('change',{bubbles:true}));}
 show();
});
$('rd-wait').addEventListener('click',()=>{if(run&&s){D.waitDwell(run,s);show();}});
$('rd-close').addEventListener('click',()=>{if(run&&s&&D.closeDoors(run,s))show();});
$('rd-restart').addEventListener('click',()=>{if(mode==='train')$('tl-reset').click();});
$('rd-export').addEventListener('click',()=>{
 if(!run)return;
 const documentText=JSON.stringify(D.report(run),null,2);
 const url=URL.createObjectURL(new Blob([documentText],{type:'application/json'})),a=document.createElement('a');
 a.href=url;a.download='transit-rail-learning-run.json';document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1200);
});
const prevTrain=M.trainStep;
M.trainStep=(state,dt)=>{
 if(mode==='train'&&run?.phase==='doors-open'){
  // Passenger service is a deliberately enforced game interlock; no actual traction dynamics are claimed in this state.
  const held={...state,speed:0,throttle:0,brake:100};
  const modeled=prevTrain(held,dt);
  return {...modeled,pos:state.pos,speed:0,accel:0,throttle:0,brake:100,doorInterlock:true,terminalOverrun:state.terminalOverrun};
 }
 return prevTrain(state,dt);
};
root.addEventListener('leh-transit-route-selected',event=>{if(event.detail?.route)route=event.detail.route;if(mode==='train')reset();});
root.addEventListener('leh-transit-route-cleared',()=>{route=null;if(mode==='train')reset();});
root.addEventListener('leh-transit-state',event=>{
 const e=event.detail;if(!e?.state)return;
 if(e.mode!==mode){mode=e.mode;s=e.state;if(mode==='train')reset();else panel.hidden=true;return;}
 s=e.state;if(mode!=='train')return;
 if(!run){reset();return;}
 if(s.time<run.lastState?.time-.001){reset();return;}
 D.advance(run,s);show();
});
mode=root.transitLatest?.mode||'flight';panel.hidden=mode!=='train';
if(mode==='train')reset();
})();