/* Transit Operations Console: educational, model-derived coaching and debrief. */
const TransitOperations=(()=>{
'use strict';
const G=9.80665,R=Math.PI/180,clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
function headingError(target,actual){return ((target-actual+540)%360)-180;}
function flightEnvelope(s,p){
 const rho=Math.max(.05,Number.isFinite(s.density)?s.density:1.225*Math.exp(-Math.max(0,s.alt)/8500));
 const bank=clamp(s.bank,-45,45)*R,gamma=clamp(s.flightPath,-12,12)*R;
 const stallSpeed=Math.sqrt(2*p.mass*G*Math.cos(gamma)/(rho*p.wing*p.clMax*Math.max(.4,Math.cos(bank))));
 return {stallSpeed,margin:s.speed/stallSpeed,loadFactor:1/Math.cos(bank),verticalFpm:s.speed*Math.sin(gamma)*196.850394};
}
function railApproach(s,p,target){
 const remaining=target-s.pos,decel=p.brake+.03+G*clamp(s.grade,-4,4)/100;
 const idealStop=decel>0?s.speed*s.speed/(2*decel):Infinity,planning=1.15*(idealStop+2*s.speed);
 return {remaining,idealStop,planning,brakeWindow:s.speed>.5&&planning>=remaining,overshot:remaining< -15||(target===s.length&&Boolean(s.terminalOverrun)),platformStop:!s.terminalOverrun&&Math.abs(remaining)<=15&&s.speed<=.5};
}
function subAssessment(s,target){
 const error=target-s.depth;
 return {error,stable:Math.abs(error)<=5&&Math.abs(s.verticalSpeed)<=.15,pressureBar:s.pressure/100000,nearSurface:s.depth<=10&&s.verticalSpeed<-.5,nearModelBottom:s.depth>=900&&s.verticalSpeed>.5};
}
return {headingError,flightEnvelope,railApproach,subAssessment};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitOperations;
(function operationsConsole(){
'use strict';
if(typeof document==='undefined'||typeof TransitModels==='undefined')return;
const root=document.getElementById('leh-transit');if(!root||root.dataset.operationsConsole==='ready')return;
root.dataset.operationsConsole='ready';
const M=TransitModels,O=TransitOperations,$=id=>document.getElementById(id);
const css=document.createElement('style');
css.textContent='#leh-transit .op-console{display:grid;gap:.7rem;outline-offset:4px}#leh-transit .op-setup{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.75rem;align-items:end}#leh-transit .op-setup label{font-size:.86rem}#leh-transit .op-setup select{width:100%;min-width:0}#leh-transit .op-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.5rem}#leh-transit .op-metric{min-width:0;padding:.65rem;border:1px solid var(--border);border-radius:9px;background:#eff5f0}#leh-transit .op-metric small,#leh-transit .op-metric strong{display:block}#leh-transit .op-metric small{color:var(--muted);font-size:.73rem}#leh-transit .op-metric strong{font-size:1.1rem;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}#leh-transit .op-alert{border-left:4px solid #387b69;background:#eef6ef;padding:.65rem .8rem;border-radius:6px;line-height:1.45;font-size:.9rem}#leh-transit .op-alert[data-level="warn"]{border-color:#b77432;background:#fff2de;color:#543b25}#leh-transit .op-alert[data-level="critical"]{border-color:#bd453d;background:#fff0ee;color:#702e2c}#leh-transit .op-meter{width:100%;height:.7rem;accent-color:#286955}#leh-transit .op-progress-caption,#leh-transit .op-foot{font-size:.79rem;color:var(--muted);margin:0}#leh-transit .op-result{font-size:.87rem;line-height:1.5;margin:.2rem 0}#leh-transit .op-events{border-top:1px solid var(--border);padding-top:.6rem}#leh-transit .op-events summary{cursor:pointer;font-weight:750}#leh-transit .op-events ol{font-size:.82rem;margin:.5rem 0 .2rem;padding-left:1.5rem;max-height:185px;overflow:auto}@media(max-width:500px){#leh-transit .op-setup{grid-template-columns:1fr}#leh-transit .op-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}';
document.head.append(css);
const panel=document.createElement('section');panel.className='panel op-console';panel.tabIndex=0;panel.setAttribute('aria-label','Operator training console');
panel.innerHTML='<div class="top"><div><p class="eyebrow">Practice, assess, improve</p><h2>Operator training console</h2></div><span class="pill calc-pill">Model-based feedback</span></div><p class="small">Practice a measurable maneuver and inspect its assumptions. Alerts are learning cues, <strong>not operational safety indications</strong>.</p><div class="op-setup"><label for="op-target"><span id="op-target-label">Target</span><select id="op-target"></select></label><button id="op-new" type="button" class="secondary">Restart objective</button></div><div class="op-metrics" aria-label="Performance metrics"><div class="op-metric"><small id="op-metric-one-label">Margin</small><strong id="op-metric-one">—</strong></div><div class="op-metric"><small id="op-metric-two-label">Position</small><strong id="op-metric-two">—</strong></div><div class="op-metric"><small id="op-metric-three-label">Rate</small><strong id="op-metric-three">—</strong></div></div><div id="op-alert" class="op-alert" data-level="normal" role="status" aria-live="polite">Choose an objective and start the model.</div><progress id="op-progress" class="op-meter" max="100" value="0" aria-label="Objective progress"></progress><p id="op-progress-label" class="op-progress-caption">Progress has not begun.</p><p id="op-result" class="op-result">No objective completed in this session.</p><div class="actions"><button id="op-export" type="button" class="secondary">Export learning debrief</button></div><details class="op-events"><summary>Simulation event log (<span id="op-count">0</span>)</summary><ol id="op-log"></ol></details><p class="op-foot">Keyboard: focus this console, then P to start/pause, period to advance one second, or R to reset. No live vehicle or navigation system is controlled.</p>';
const main=root.querySelector('.main-stack');if(!main)return;main.insertBefore(panel,main.children[1]||null);
const targets={flight:[['90','East · 090°'],['135','Southeast · 135°'],['180','South · 180°'],['270','West · 270°']],train:[['2500','First station · 2.5 km'],['5500','Second station · 5.5 km'],['10000','Terminus · 10 km']],sub:[['75','Shallow target · 75 m'],['100','Middle target · 100 m'],['150','Deep target · 150 m']]};
const defaults={flight:135,train:2500,sub:75},fmt=(n,d=1)=>Number.isFinite(n)?Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
let mode='',target=135,lastTime=0,hold=0,complete=false,alertKey='',events=[],totalAlerts=0,lastState=null,observing=false;
function appendEvent(message,time){events.push('T+'+fmt(time,1)+'s · '+message);if(events.length>80)events.shift();$('op-count').textContent=String(events.length);const list=$('op-log');list.replaceChildren();for(const text of events.slice(-12).reverse()){const li=document.createElement('li');li.textContent=text;list.append(li);}}
function setAlert(key,level,message,time){if(key===alertKey)return;alertKey=key;$('op-alert').dataset.level=level;$('op-alert').textContent=message;if(level!=='normal'){totalAlerts++;appendEvent('Teaching alert: '+message,time);}}
function configure(k){
 mode=k;target=defaults[k];lastTime=0;hold=0;complete=false;alertKey='';events=[];totalAlerts=0;lastState=null;observing=false;$('op-log').replaceChildren();$('op-count').textContent='0';
 const select=$('op-target');select.replaceChildren();for(const [value,label] of targets[k]){const o=document.createElement('option');o.value=value;o.textContent=label;select.add(o);}select.value=String(target);
 $('op-target-label').textContent={flight:'Target true heading',train:'Target station · schematic',sub:'Target modeled depth'}[k];
 for(const [i,label] of ['one','two','three'].entries())$('op-metric-'+label+'-label').textContent=({flight:['Stall-speed margin','Bank load factor','Modeled vertical speed'],train:['Distance to platform','Planning brake distance','Train speed'],sub:['Depth error','Absolute pressure','Vertical speed']}[k])[i];
 $('op-progress').value=0;$('op-progress-label').textContent='Objective ready.';$('op-result').textContent='No objective completed in this session.';$('op-alert').dataset.level='normal';$('op-alert').textContent='Start or advance the model to begin.';
}
function restart(){hold=0;complete=false;alertKey='';$('op-result').textContent='Objective restarted; model state is unchanged.';appendEvent('Objective restarted · '+target,lastTime);render(lastState,observing);}
function render(s,isObservation){
 if(!s)return;
 const dt=Math.max(0,Math.min(3,s.time-lastTime));let level='normal',key='normal',message='',metrics=[],progress=0,qualified=false,goal='';
 if(isObservation){level='warn';key='observed';message='An imported position is selected. Take simulation controls to begin a new hypothetical trajectory.';metrics=['—','—','—'];$('op-progress-label').textContent='Assessment paused for imported observations.';}
 else if(mode==='flight'){
  const e=O.flightEnvelope(s,M.AIRCRAFT[s.profile]),err=Math.abs(O.headingError(target,s.heading));
  metrics=[fmt(e.margin,2)+'×',fmt(e.loadFactor,2)+' g',fmt(e.verticalFpm,0)+' ft/min'];qualified=err<=5&&Math.abs(s.bank)<=5&&e.margin>=1.2&&s.alt>0;hold=qualified?hold+dt:0;progress=complete?100:Math.min(100,hold/5*100);
  goal='Steer to '+target+'° true, then hold ±5° at bank ≤5° and stall-speed margin ≥1.2× for five simulated seconds.';
  if(s.stalled||e.margin<1){level='critical';key='stall';message='Required lift exceeds the generic CLmax assumption. Stall dynamics and recovery are not simulated.';}
  else if(e.margin<1.2){level='warn';key='margin';message='Low modeled stall-speed margin. Compare speed and bank angle; not aircraft-specific guidance.';}
  else if(s.alt===0){level='warn';key='ground';message='At model altitude boundary; landing and ground interaction are not simulated.';}
  else message=qualified?'Holding the heading and wings-level criteria.':'Steer using bank, then level the wings while monitoring airspeed margin.';
  $('op-progress-label').textContent='Steady heading: '+fmt(hold,1)+' / 5.0 s · heading error '+fmt(err,1)+'°';
 }else if(mode==='train'){
  const a=O.railApproach(s,M.TRAINS[s.profile],target);
  metrics=[fmt(a.remaining,0)+' m',fmt(a.planning,0)+' m',fmt(s.speed*3.6,1)+' km/h'];
  progress=complete?100:Math.max(0,Math.min(99,s.pos/target*99));qualified=a.platformStop;goal='Stop within ±15 m of '+fmt(target/1000,1)+' km, at or below 0.5 m/s.';
  if(a.overshot){level='critical';key='passed';message='Station overshot or crossed the model terminus without stopping. A forced boundary stop does not count; reset to retry.';}
  else if(a.brakeWindow&&a.remaining>15){level='warn';key='brake';message='Planning brake distance has reached the remaining platform distance; compare brake command and response.';}
  else if(a.remaining<=15&&s.speed>.5){level='warn';key='rolling';message='Inside the platform band but not yet at the stopping criterion.';}
  else message='Compare station distance with ideal service-braking distance plus illustrative response and margin.';
  $('op-progress-label').textContent='Travelled '+fmt(s.pos/1000,2)+' km · platform error '+fmt(Math.abs(a.remaining),0)+' m';
 }else{
  const a=O.subAssessment(s,target);
  metrics=[fmt(a.error,1)+' m',fmt(a.pressureBar,2)+' bar',fmt(s.verticalSpeed,2)+' m/s'];
  qualified=a.stable;hold=qualified?hold+dt:0;progress=complete?100:Math.min(100,hold/5*100);
  goal='Hold depth within ±5 m of '+target+' m and vertical rate ≤0.15 m/s for five simulated seconds.';
  if(a.nearModelBottom){level='warn';key='bottom';message='Near the model’s artificial depth boundary, not a validated hull or seabed limit.';}
  else if(a.nearSurface){level='warn';key='surface';message='Near the artificial surface boundary. Surfacing dynamics are not modeled.';}
  else if(Math.abs(s.verticalSpeed)>1.5){level='warn';key='vertical';message='High vertical rate for this exercise. Threshold is illustrative, not vessel guidance.';}
  else message=qualified?'Inside the depth and rate bands; continue holding.':'Allow for ballast-response lag and reduce trim as you approach the target.';
  $('op-progress-label').textContent='Stable depth: '+fmt(hold,1)+' / 5.0 simulated seconds';
 }
 for(let i=0;i<3;i++)$('op-metric-'+['one','two','three'][i]).textContent=metrics[i];$('op-progress').value=progress;
 if(!isObservation&&qualified&&(mode==='train'||hold>=5)&&!complete){complete=true;$('op-progress').value=100;$('op-result').textContent='Objective achieved at T+'+fmt(s.time,1)+' s. '+goal+' Simulated outcomes only.';appendEvent('Objective achieved: '+goal,s.time);}
 if(!complete&&!isObservation)$('op-result').textContent=goal;
 setAlert(key,level,message,s.time);lastTime=s.time;
}
root.addEventListener('leh-transit-state',e=>{
 const d=e.detail;if(!d?.state||!['flight','train','sub'].includes(d.mode))return;
 if(d.mode!==mode){configure(d.mode);appendEvent('Started '+d.mode+' objective',0);}
 else if(d.state.time+.01<lastTime){configure(d.mode);appendEvent('Model reset',0);}
 if(d.mode==='train'&&d.state.pos===d.state.length&&!d.state.terminalOverrun&&lastState&&lastState.pos<d.state.length&&lastState.speed>.5)d.state.terminalOverrun=true;
 if(!d.observing&&observing){alertKey='';appendEvent('Returned to simulated motion',d.state.time);}
 observing=Boolean(d.observing);lastState=d.state;render(d.state,observing);
});
$('op-target').addEventListener('change',()=>{
 target=Number($('op-target').value);const other=mode==='train'?'tl-mission-station':mode==='sub'?'tl-mission-depth':null;
 if(other&&$(other)){$(other).value=String(target);$(other).dispatchEvent(new Event('change',{bubbles:true}));}
 restart();
});
$('op-new').addEventListener('click',restart);
panel.addEventListener('keydown',e=>{
 if(e.altKey||e.ctrlKey||e.metaKey||e.target.closest('button,input,select,textarea,a,summary'))return;
 const key=e.key.toLowerCase(),id=key==='p'?'tl-play':key==='.'?'tl-step':key==='r'?'tl-reset':null;
 if(!id||$(id).disabled)return;e.preventDefault();$(id).click();
});
$('op-export').addEventListener('click',()=>{
 const lines=['TRANSIT SIMULATION LAB · LEARNING DEBRIEF','Browser-local teaching model. Not a real vehicle observation or operational guidance.','Vehicle: '+mode,'Objective: '+$('op-target').selectedOptions[0]?.textContent,'Model elapsed: '+fmt(lastState?.time??0,1)+' seconds','Result: '+(complete?'achieved':'incomplete'),'Teaching alert transitions: '+totalAlerts,'Metrics: '+['one','two','three'].map(k=>$('op-metric-'+k+'-label').textContent+' '+$('op-metric-'+k).textContent).join(' · '),'Generic coefficients; no certified vehicle, signaling, terrain collision, or live telemetry.','','Events',...(events.length?events:['No events'])];
 const url=URL.createObjectURL(new Blob([lines.join('\n')+'\n'],{type:'text/plain;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='transit-'+mode+'-learning-debrief.txt';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1200);
});
configure(root.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode||'flight');
})();
