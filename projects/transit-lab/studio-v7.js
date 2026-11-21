/* Transit Lab Studio v7 — accessible, educational visual and modeling enhancements. */
(function transitStudioV7(){
'use strict';
const root=document.getElementById('leh-transit');
if(!root||root.dataset.studioV7==='ready'||typeof TransitModels==='undefined')return;
root.dataset.studioV7='ready';
const $=id=>document.getElementById(id), M=TransitModels;
const modes={flight:'Aircraft',train:'Railway',sub:'Submarine'};
const sourceFor=(type,id)=>{
 const p=(typeof TransitFleetV5!=='undefined'&&TransitFleetV5.entry(type,id))||(typeof TransitHistorical!=='undefined'&&TransitHistorical.references[id]);
 return p||null;
};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
const fmt=(x,d=0)=>Number.isFinite(Number(x))?Number(x).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
const el=(tag,attrs={},text)=>{const n=document.createElement(tag);Object.entries(attrs).forEach(([k,v])=>{if(k==='className')n.className=v;else n.setAttribute(k,String(v));});if(text!==undefined)n.textContent=text;return n;};
const css=document.createElement('style');css.textContent=`
#leh-transit{--studio-bg:#081722;--studio-panel:#102b33;--studio-accent:#7ae1cd;--studio-outline:#567987;max-width:1460px}
#leh-transit .tlx-deck{border:1px solid #284d55;border-radius:15px;overflow:hidden;background:#081722;color:#e3f3f2;box-shadow:0 12px 32px #02191d24}
#leh-transit .tlx-deck h2,#leh-transit .tlx-deck h3{font-family:system-ui,sans-serif;color:#e3f3f2}
#leh-transit .tlx-deck h2{font-size:1.35rem;margin:0}#leh-transit .tlx-deck h3{font-size:1rem;margin:0 0 .55rem}
#leh-transit .tlx-deck p{margin:.4rem 0;color:#abc7ce;font-size:.87rem}
#leh-transit .tlx-head{padding:1rem 1.05rem;background:linear-gradient(108deg,#073840,#153f49,#0d243a);display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.9rem}
#leh-transit .tlx-eyebrow{display:block;color:#9ce8da;letter-spacing:.14em;text-transform:uppercase;font-size:.7rem;font-weight:800}
#leh-transit .tlx-chip{border:1px solid #426e78;padding:.3rem .6rem;border-radius:999px;color:#e0ebea;font-size:.72rem;white-space:nowrap}
#leh-transit .tlx-canvas-shell{position:relative;background:#071924;border-bottom:1px solid #325360;overflow:hidden}
#leh-transit #tlx-canvas{display:block;width:100%;height:auto;aspect-ratio:16 / 8.3;touch-action:pan-y;cursor:crosshair}
#leh-transit .tlx-hud{position:absolute;top:.7rem;left:.7rem;right:.7rem;display:flex;justify-content:space-between;align-items:flex-start;gap:.4rem;pointer-events:none;color:white;font:700 .76rem/1.5 system-ui,sans-serif;text-shadow:0 1px 4px #001}
#leh-transit .tlx-hud span{background:#061c25b8;padding:.4rem .55rem;border-radius:6px}
#leh-transit .tlx-scene-footer{background:#091b28;color:#b7d1d9;padding:.55rem .95rem;font-size:.73rem;display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap}
#leh-transit .tlx-tools{padding:.9rem 1rem;display:grid;gap:.75rem}
#leh-transit .tlx-row{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
#leh-transit .tlx-tools button,#leh-transit .tlx-tools select,#leh-transit .tlx-tools input{font:inherit}
#leh-transit .tlx-deck button{min-height:36px;border:1px solid #4f8992;background:#153d49;color:#effaf7;border-radius:8px;padding:.42rem .65rem;font-weight:700;font-size:.78rem}
#leh-transit .tlx-deck button:hover{background:#1e5a66}#leh-transit .tlx-deck button[data-active=true]{background:#2b6c67;border-color:#96dcc7}
#leh-transit .tlx-deck select,#leh-transit .tlx-deck input[type=date],#leh-transit .tlx-deck input[type=search]{background:#092a32;color:white;border:1px solid #537b83;padding:.48rem;border-radius:7px;max-width:100%}
#leh-transit .tlx-deck a{color:#a3f0dd;text-decoration:underline}
#leh-transit .tlx-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem}
#leh-transit .tlx-toolbar label,#leh-transit .tlx-tools label{font-size:.78rem;color:#c3dada}
#leh-transit .tlx-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}
#leh-transit .tlx-sub{border:1px solid #375d65;background:#0e2731;border-radius:10px;padding:.8rem;min-width:0}
#leh-transit .tlx-mini{font-size:.76rem!important;line-height:1.5;color:#b4cbd0!important}
#leh-transit .tlx-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:.4rem;max-height:252px;overflow:auto}
#leh-transit .tlx-cards button{font-size:.76rem;text-align:left;line-height:1.4;padding:.6rem;white-space:normal;background:#12303a}
#leh-transit .tlx-cards button strong,#leh-transit .tlx-cards button small{display:block}
#leh-transit .tlx-cards button small{color:#9cbfc5;font-size:.67rem;margin-top:.3rem;font-weight:500}
#leh-transit .tlx-controls{display:grid;gap:.4rem}#leh-transit .tlx-controls label{display:grid;grid-template-columns:minmax(120px,1fr) auto;gap:.5rem;align-items:center}
#leh-transit .tlx-controls input[type=range]{grid-column:1/-1;width:100%;accent-color:#70d4c0}
#leh-transit #tlx-machine-summary{border-left:3px solid #86d6c4;padding:.45rem .7rem;color:#d5eae8}
#leh-transit .tlx-test{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.45rem}
#leh-transit .tlx-test>div{background:#0a323d;padding:.5rem;border-radius:7px;font-size:.75rem}
#leh-transit .tlx-test b{display:block;font-size:1.12rem;font-variant-numeric:tabular-nums;color:#d9ffeb}
#leh-transit .tlx-notice{border-left:3px solid #c6a16d;background:#2a292a;padding:.55rem .75rem;border-radius:3px;font-size:.79rem;color:#f5dfc2}
#leh-transit .tlx-integrations{display:grid;gap:.7rem}
#leh-transit .tlx-source{background:#071f28;border:1px solid #31545e;padding:.7rem;border-radius:8px}
#leh-transit .tlx-source img{display:block;width:100%;max-height:250px;object-fit:contain;background:#0a1720;border-radius:6px;margin-top:.5rem}
#leh-transit .tlx-source output{display:block;font-size:.78rem;color:#c4d6d6;margin-top:.5rem;white-space:pre-wrap;overflow-wrap:anywhere}
#leh-transit .tlx-collapsible>summary{font-size:.91rem;font-weight:800;cursor:pointer;color:#f5f9f2;margin-bottom:.4rem}
#leh-transit .tlx-legacy{display:none!important}#leh-transit .tlx-legacy.tlx-show{display:block!important}
#leh-transit .tlx-kbd{font-size:.7rem;color:#98b9c4}
@media(max-width:870px){#leh-transit .tlx-grid{grid-template-columns:1fr}#leh-transit #tlx-canvas{aspect-ratio:16 / 10}}
@media(max-width:480px){#leh-transit .tlx-hud{font-size:.63rem}#leh-transit .tlx-head{padding:.8rem}#leh-transit .tlx-test{grid-template-columns:1fr 1fr}}
@media(prefers-reduced-motion:reduce){#leh-transit #tlx-canvas{transition:none}}
`;
document.head.append(css);
const deck=el('section',{className:'tlx-deck',id:'tlx-deck','aria-label':'Advanced simulation studio'});
deck.innerHTML=`<div class="tlx-head"><div><span class="tlx-eyebrow">Transit Lab / Interactive Studio v7</span><h2>Operate, inspect, compare</h2><p>Immersive model scene · machine hangar · scenario controls · opt-in reference data</p></div><div class="tlx-row"><span class="tlx-chip">EDUCATIONAL SIMULATOR</span><span class="tlx-chip">Teaching models / not certified</span></div></div>
<div class="tlx-canvas-shell"><canvas id="tlx-canvas" width="1200" height="610" tabindex="0" aria-label="Animated conceptual simulation scene, focused keyboard shortcuts available"></canvas><div class="tlx-hud"><span id="tlx-hud-left">MODEL READY</span><span id="tlx-hud-right">STATE / SIMULATED</span></div></div>
<div class="tlx-scene-footer"><span id="tlx-scene-caption">Original procedurally drawn scene, not a camera or reconstruction of an actual location.</span><span id="tlx-fps">Canvas ready · visual only</span></div>
<div class="tlx-tools"><div class="tlx-toolbar"><label for="tlx-camera">View <select id="tlx-camera"><option value="cab">Operator / cockpit</option><option value="exterior">Vehicle exterior</option><option value="scope">Instrument / sonar</option></select></label><label for="tlx-light">Light <select id="tlx-light"><option value="day">Daylight</option><option value="sunset">Sunset</option><option value="night">Night</option></select></label><label for="tlx-weather">Atmosphere <select id="tlx-weather"><option value="clear">Clear</option><option value="rain">Rain</option><option value="fog">Fog</option><option value="snow">Snow (illustrative)</option></select></label><button id="tlx-existing" type="button">Show technical viewport</button><button id="tlx-shot" type="button">Save scene PNG</button></div>
<div class="tlx-row" id="tlx-quick" aria-label="Quick vehicle controls"></div><p class="tlx-mini">Canvas is a conceptual visualization driven by simulated state. Drag horizontally on the scene to bank the aircraft / adjust rail traction / change submarine heading. Keyboard: ← → for steering, ↑ ↓ for throttle or speed, space to start/pause (when this scene is focused). These controls never operate real machines.</p>
<div class="tlx-grid"><section class="tlx-sub"><h3>Machine hangar <small id="tlx-count"></small></h3><p class="tlx-mini">Documented historical identity is separated from illustrative dynamics.</p><input id="tlx-find" type="search" placeholder="Find vehicle or era" aria-label="Find machine"><div id="tlx-machines" class="tlx-cards"></div><p id="tlx-machine-summary" class="tlx-mini" aria-live="polite"></p></section>
<section class="tlx-sub"><h3>What-if engineering bench</h3><p class="tlx-mini">Modify hypothetical coefficients without changing historical source records. The baseline can be restored at any time.</p><div class="tlx-controls"><label for="tlx-mass">Mass / load multiplier <output id="tlx-mass-out">1.00×</output><input type="range" id="tlx-mass" min="75" max="125" value="100" step="5"></label><label for="tlx-power">Power / traction multiplier <output id="tlx-power-out">1.00×</output><input type="range" id="tlx-power" min="60" max="140" value="100" step="5"></label><label for="tlx-resistance">Drag / braking multiplier <output id="tlx-resistance-out">1.00×</output><input type="range" id="tlx-resistance" min="60" max="140" value="100" step="5"></label></div><div class="tlx-row"><button type="button" id="tlx-restore">Restore baseline model</button><button type="button" id="tlx-snapshot">Export test snapshot</button></div><div id="tlx-test" class="tlx-test" aria-live="polite"></div></section></div>
<section class="tlx-sub"><h3>Environmental challenge presets</h3><div id="tlx-scenarios" class="tlx-row"></div><p id="tlx-scenario-note" class="tlx-mini">Scenario presets change existing simulation control inputs. They do not import observations or assert local weather.</p></section>
<details class="tlx-sub tlx-collapsible" id="tlx-integrations"><summary>Reference data studio · opt-in only</summary><p class="tlx-mini">Nothing connects automatically. Each Load button makes a request to the named public provider. These data are observational or geographic reference layers, not validated simulation inputs.</p><div class="tlx-integrations">
<div class="tlx-source"><h3>NASA GIBS satellite context</h3><p class="tlx-mini">Visible reflectance image centered near the simulator's modeled position; not a cockpit view or historical flight imagery. A dated scene may be unavailable/cloud-covered.</p><div class="tlx-row"><label for="tlx-nasa-date">Image date <input type="date" id="tlx-nasa-date" value="2026-11-01" min="2010-01-01" max="2026-11-21"></label><button id="tlx-nasa" type="button">Request NASA image</button><a href="https://nasa-gibs.github.io/gibs-api-docs/access-basics/" target="_blank" rel="noopener noreferrer">NASA GIBS documentation</a></div><output id="tlx-nasa-status">No NASA imagery requested.</output><img id="tlx-nasa-img" alt="NASA GIBS imagery, loaded only by explicit request" hidden></div>
<div class="tlx-source"><h3>NOAA water-level observation</h3><p class="tlx-mini">Fixed public station selection; live observation is shown separately from submarine depth and is never applied to ballast calculations.</p><div class="tlx-row"><label for="tlx-tide-station">Station <select id="tlx-tide-station"><option value="8518750">The Battery, NY (8518750)</option><option value="8443970">Boston, MA (8443970)</option><option value="9414290">San Francisco, CA (9414290)</option></select></label><button id="tlx-noaa" type="button">Request NOAA reading</button><a href="https://api.tidesandcurrents.noaa.gov/api/prod/" target="_blank" rel="noopener noreferrer">NOAA API</a></div><output id="tlx-noaa-status">No NOAA observation requested.</output></div>
<div class="tlx-source"><h3>Rail geographic data and recorded tracks</h3><p class="tlx-mini">Use the existing MTA subway line browser for published reference geometry, or the Data Integration Lab for local GTFS, GeoJSON and recorded-flight files. None is live operational telemetry.</p><div class="tlx-row"><button id="tlx-mta" type="button">Open MTA route browser</button><button id="tlx-data" type="button">Find data import tools</button></div><output id="tlx-mta-status">No public route data requested from this panel.</output></div></div></details>
<div class="tlx-sub"><h3>Contextual learning &amp; evidence</h3><p id="tlx-learning" aria-live="polite">Choose a machine or operate the model to inspect a sourced historical fact and a calculated principle.</p><p class="tlx-notice" id="tlx-boundary">Historical identity may be documented; vehicle response, camera perspective, terrain, weather, and visual effects are educational approximations. Engineering assumptions must be independently validated for operational use.</p></div></div>`;
const main=root.querySelector('.main-stack');
if(!main)return;
main.prepend(deck);
const oldView=$('tl-view-title')?.closest('.panel');if(oldView){oldView.classList.add('tlx-legacy');}
let mode=root.transitLatest?.mode||'flight',state=root.transitLatest?.state||null,observing=false, visualDistance=0,previous=null;
let sceneTime=0, frames=0,lastFpsAt=performance.now(),fps=0, scenario='clear', lastLearn='', modelDirty=false;
const baseline=new Map();
const modId=()=>mode==='flight'?$('tl-plane')?.value:mode==='train'?$('tl-train-profile')?.value:$('hr-sub-vehicle')?.value||'generic';
const selId=()=>mode==='flight'?'tl-plane':mode==='train'?'tl-train-profile':'hr-sub-vehicle';
function selectedName(){return $(selId())?.selectedOptions?.[0]?.textContent?.trim()||'Generic teaching model';}
function getParams(kind,id){return kind==='flight'?M.AIRCRAFT[id]:kind==='train'?M.TRAINS[id]:null;}
function restoreAll(){for(const [key,b] of baseline){const [kind,id]=key.split(':');const p=getParams(kind,id);if(p)Object.assign(p,b);}modelDirty=false;}
function modValues(){return {mass:Number($('tlx-mass').value)/100,power:Number($('tlx-power').value)/100,resistance:Number($('tlx-resistance').value)/100};}
function showTuning(){const {mass,power,resistance}=modValues();$('tlx-mass-out').textContent=mass.toFixed(2)+'×';$('tlx-power-out').textContent=power.toFixed(2)+'×';$('tlx-resistance-out').textContent=resistance.toFixed(2)+'×';
 restoreAll();if(mode==='sub'){$('tlx-test').innerHTML='<div><small>Submarine model</small><b>Buoyancy</b>Use existing trim &amp; current controls</div>';return;}
 const id=modId(),p=getParams(mode,id);if(!p)return;
 const key=mode+':'+id;if(!baseline.has(key))baseline.set(key,{...p});const b=baseline.get(key);
 if(mode==='flight'){p.mass=b.mass*mass;p.thrust=b.thrust*power;p.cd0=b.cd0*resistance;}
 if(mode==='train'){p.traction=b.traction*power;p.brake=b.brake*resistance;}
 modelDirty=[mass,power,resistance].some(v=>v!==1);
 $('tlx-test').replaceChildren();
 const values=mode==='flight'?[['Assumed mass',fmt(p.mass,0)+' kg'],['Modeled thrust',fmt(p.thrust,0)+' N'],['Illustrative Cᴅ₀',fmt(p.cd0,4)]]:[['Traction',fmt(p.traction,2)+' m/s²'],['Brake',fmt(p.brake,2)+' m/s²'],['Model ceiling',fmt(p.limit*3.6,0)+' km/h']];
 values.forEach(([label,val])=>{const cell=el('div');cell.append(el('small',{},label),el('b',{},val));$('tlx-test').append(cell);});
 $('tlx-boundary').textContent=modelDirty?'WHAT-IF ACTIVE: These altered coefficients are not measured or manufacturer-approved for '+selectedName()+'. Restore baseline for comparison.':'Historical identity may be documented; vehicle response, camera perspective, terrain, weather and visual effects are educational approximations. Engineering assumptions must be independently validated for operational use.';
}
function clearTuning(){restoreAll();['tlx-mass','tlx-power','tlx-resistance'].forEach(id=>$(id).value=100);showTuning();}
function renderHangar(){const select=$(selId());if(!select)return;const needle=$('tlx-find').value.toLowerCase();const cards=$('tlx-machines');cards.replaceChildren();let count=0;
 Array.from(select.options).forEach(opt=>{if(opt.disabled)return;const historical=sourceFor(mode,opt.value),name=opt.textContent;if(needle&&!name.toLowerCase().includes(needle))return;
 const btn=el('button',{type:'button','data-active':String(opt.value===select.value)});btn.append(el('strong',{},name),el('small',{},historical?'Archival source · dynamics qualified':'Generic teaching profile'));
 btn.addEventListener('click',()=>{if(opt.value===select.value)return;clearTuning();select.value=opt.value;select.dispatchEvent(new Event('change',{bubbles:true}));renderHangar();});cards.append(btn);count++;});
 $('tlx-count').textContent='('+count+' shown)';
 const record=sourceFor(mode,modId());const summary=$('tlx-machine-summary');summary.replaceChildren();summary.append(document.createTextNode(selectedName()+'. '));
 if(record){summary.append(document.createTextNode((record.assumptions||'Historical identification sourced; modeled response illustrative.').slice(0,320)+' '));if(record.source){const a=el('a',{href:record.source,target:'_blank',rel:'noopener noreferrer'},'Historical source ↗');summary.append(a);}}
 else summary.append(document.createTextNode('Generic model; its speed, controls and handling are not a specific historic vehicle.'));
 updateLearning();showTuning();}
const shortcuts={flight:[['Thrust +10',()=>change('tl-throttle',10)],['Thrust −10',()=>change('tl-throttle',-10)],['Bank left',()=>change('tl-bank',-5)],['Level wings',()=>set('tl-bank',0)],['Bank right',()=>change('tl-bank',5)]],train:[['Power 50%',()=>{set('tl-brake',0);set('tl-traction',50);}],['Coast',()=>{set('tl-traction',0);set('tl-brake',0);}],['Service brake',()=>{set('tl-traction',0);set('tl-brake',55);}],['Full brake',()=>{set('tl-traction',0);set('tl-brake',100);}]],sub:[['Slow ahead',()=>set('tl-sub-speed',3)],['Stop ahead',()=>set('tl-sub-speed',0)],['Dive trim',()=>set('tl-ballast',15)],['Neutral trim',()=>set('tl-ballast',0)],['Rise trim',()=>set('tl-ballast',-15)]]};
function set(id,value){const n=$(id);if(!n)return;n.value=String(clamp(value,Number(n.min||-360),Number(n.max||360)));n.dispatchEvent(new Event('input',{bubbles:true}));}
function change(id,by){const n=$(id);if(n)set(id,Number(n.value)+by);}
function quick(){const host=$('tlx-quick');host.replaceChildren();shortcuts[mode].forEach(([text,fn])=>{const b=el('button',{type:'button'},text);b.addEventListener('click',fn);host.append(b);});host.append(el('span',{className:'tlx-kbd'},'Rapid control changes use existing model inputs, not observed measurements.'));}
const scen={flight:[['Clear','clear'],['Crosswind / gusts','crosswind'],['Low visibility','fog']],train:[['Dry rail','clear'],['Wet rails','wet'],['Low adhesion','slippery']],sub:[['Calm water','clear'],['Current 1.2 kn','current'],['Low salinity','fresh']]};
function renderScenarios(){const host=$('tlx-scenarios');host.replaceChildren();scen[mode].forEach(([label,id])=>{const b=el('button',{type:'button','data-active':String(id===scenario)},label);b.addEventListener('click',()=>applyScenario(id));host.append(b);});}
function applyScenario(id){scenario=id;
 if(mode==='flight'){set('tl-wind',id==='crosswind'?22:0);set('tl-wind-direction',id==='crosswind'?270:90);set('ev-gust',id==='crosswind'?12:0);$('tlx-weather').value=id==='fog'?'fog':'clear';}
 if(mode==='train'){set('ev-adhesion',id==='wet'?.75:id==='slippery'?.45:1);$('tlx-weather').value=id==='clear'?'clear':id==='wet'?'rain':'fog';}
 if(mode==='sub'){set('ev-current',id==='current'?1.2:0);set('ev-current-heading',id==='current'?130:90);set('hr-density',id==='fresh'?1000:1025);$('tlx-weather').value='clear';}
 $('tlx-scenario-note').textContent='Selected '+id+' · hypothetical teaching scenario. Inputs are not NOAA observations, actual adhesion measurements, or authentic historical operating conditions.';
 renderScenarios();}
function modeChange(next){mode=next;previous=null;visualDistance=0;scenario='clear';$('tlx-find').value='';renderHangar();quick();renderScenarios();$('tlx-noaa-status').textContent='No NOAA observation requested for this session.';}
function updateLearning(){if(!state)return;const rec=sourceFor(mode,modId());const facts=rec?.facts||[];let explanation='';
 if(mode==='flight'){const val=Number(state.speed||0)*1.943844;explanation='Modeled true airspeed '+fmt(val,0)+' kn; induced drag, dynamic pressure and stall warning depend on assumed aerodynamic coefficients.';}
 else if(mode==='train')explanation='At '+fmt((state.speed||0)*3.6,1)+' km/h, an ideal stopping-distance calculation uses speed squared, the assumed service brake and track grade.';
 else explanation='At '+fmt(state.depth||0,1)+' m, hydrostatic pressure grows with density and depth; no pressure-hull safety rating is inferred.';
 const fact=facts.length?facts[0]+'. ':'Sourced historical facts are available for named museum/archive profiles. ';
 const key=mode+modId()+fact;if(key===lastLearn&&Math.floor((state.time||0)*2)%20!==0)return;lastLearn=key;
 const host=$('tlx-learning');host.replaceChildren();host.append(document.createTextNode(fact+explanation+' '));
 if(rec?.source)host.append(el('a',{href:rec.source,target:'_blank',rel:'noopener noreferrer'},'Historical record ↗'));
}
function snapshot(){const data={schema:'transit-simulation-study-v7',capturedAt:new Date().toISOString(),simulator:'educational-not-calibrated',mode,machine:modId(),machineLabel:selectedName(),source:sourceFor(mode,modId())?.source||null,modelAdjustments:modValues(),adjustmentsActive:modelDirty,scene:{light:$('tlx-light').value,weather:$('tlx-weather').value,camera:$('tlx-camera').value},environmentScenario:scenario,provenance:'Simulated/illustrative; observed reference requests never merged into vehicle state.',state:state&&Object.fromEntries(Object.entries(state).filter(([,v])=>typeof v==='number'||typeof v==='boolean'||typeof v==='string'))};
 const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a',{href:url,download:'transit-simulation-study-'+mode+'.json'});a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
function drawSave(){const a=el('a',{download:'transit-scene-'+mode+'.png',href:$('tlx-canvas').toDataURL('image/png')});a.click();}
function canvasContext(){const c=$('tlx-canvas'),w=c.clientWidth||1200,h=w/(innerWidth<870?1.6:1200/610),d=Math.min(2,devicePixelRatio||1);if(c.width!==Math.round(w*d)||c.height!==Math.round(h*d)){c.width=Math.round(w*d);c.height=Math.round(h*d);}const g=c.getContext('2d');g.setTransform(d,0,0,d,0,0);return {g,w,h};}
function polygon(g,points,fill){g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fillStyle=fill;g.fill();}
function line(g,pts,stroke,width=1){g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.lineWidth=width;g.strokeStyle=stroke;g.stroke();}
function text(g,label,x,y,size=14,color='#e5fff5',align='left'){g.fillStyle=color;g.font='600 '+size+'px system-ui';g.textAlign=align;g.fillText(label,x,y);g.textAlign='left';}
function sky(g,w,h){const light=$('tlx-light').value,gradient=g.createLinearGradient(0,0,0,h);if(light==='night'){gradient.addColorStop(0,'#041424');gradient.addColorStop(.6,'#113145');gradient.addColorStop(1,'#153d44');}else if(light==='sunset'){gradient.addColorStop(0,'#283a66');gradient.addColorStop(.6,'#ed9872');gradient.addColorStop(1,'#f4bd80');}else{gradient.addColorStop(0,'#25628c');gradient.addColorStop(.6,'#7ebed0');gradient.addColorStop(1,'#c2d5c7');}g.fillStyle=gradient;g.fillRect(0,0,w,h);if(light==='night'){for(let i=0;i<90;i++){const x=((i*1543+37)%997)/997*w,y=((i*369+13)%370)/500*h;g.fillStyle='rgba(236,255,249,.65)';g.fillRect(x,y,i%9===0?2:1,1);}}else{g.fillStyle=light==='sunset'?'#fff0bc':'#f4efb5';g.beginPath();g.arc(w*.78,h*.19,Math.max(18,w*.024),0,Math.PI*2);g.fill();}}
function weather(g,w,h,shift){const kind=$('tlx-weather').value;if(kind==='clear')return;if(kind==='fog'){g.fillStyle='rgba(230,238,236,.42)';g.fillRect(0,0,w,h);return;}g.strokeStyle=kind==='rain'?'rgba(193,225,237,.32)':'rgba(250,255,255,.6)';g.lineWidth=kind==='rain'?1.5:2.5;
 for(let i=0;i<100;i++){const x=((i*251+Math.floor(shift*.8))%1103)/1103*w,y=((i*151+Math.floor(shift*1.7))%653)/653*h;g.beginPath();g.moveTo(x,y);g.lineTo(x-(kind==='rain'?9:3),y+(kind==='rain'?19:4));g.stroke();}}
function flightScene(g,w,h,s,camera){sky(g,w,h);const bank=clamp(Number(s.bank)||0,-45,45)*Math.PI/180,path=clamp(Number(s.flightPath)||0,-12,12),move=visualDistance*.009;g.save();g.translate(w/2,h/2+path*3.6);g.rotate(-bank);g.translate(-w/2,-h/2);
 const horizon=h*.59;polygon(g,[[0,horizon],[w,horizon],[w,h],[0,h]],'#315d55');for(let layer=0;layer<3;layer++){const y=horizon+layer*27,pts=[[0,h]];for(let i=-1;i<=21;i++){const x=i*w/20;const ridge=Math.sin(i*1.8+move*.06+layer)*23+Math.cos(i*.62-layer*3+move*.015)*22;pts.push([x,y+ridge+layer*8]);}pts.push([w,h]);polygon(g,pts,['#658077','#486d62','#234e4d'][layer]);}
 for(let i=0;i<18;i++){const x=((i*243+move*15)%1800)/1800*w,y=horizon+55+(i*83)%160;const size=2+((i*9)%6);g.fillStyle='rgba(19,53,49,.45)';g.beginPath();g.arc(x,y,size,0,Math.PI*2);g.fill();}
 g.restore();
 if(camera==='exterior'){const x=w*.5,y=h*.55;g.save();g.translate(x,y);g.rotate(bank*.4);polygon(g,[[-w*.16,0],[-13,-8],[0,-58],[13,-8],[w*.16,0],[w*.16,10],[12,5],[10,62],[-10,62],[-12,5],[-w*.16,10]],'#d5e1de');polygon(g,[[-19,-9],[0,-52],[19,-9]],'#396e86');g.strokeStyle='#28424d';g.lineWidth=3;g.strokeRect(-5,-15,10,34);g.restore();}
 else{polygon(g,[[0,h],[0,h*.72],[w*.20,h*.76],[w*.29,h],[w*.71,h],[w*.80,h*.76],[w,h*.72],[w,h]],'#0b1d29');line(g,[[w*.20,h*.76],[w*.80,h*.76]],'#547b80',4);
 g.fillStyle='#223b43';g.beginPath();g.arc(w*.5,h*.98,w*.18,Math.PI,0);g.fill();line(g,[[w*.5-36,h*.46],[w*.5+36,h*.46]],'#fff8c8',2);line(g,[[w*.5,h*.46-15],[w*.5,h*.46+15]],'#fff8c8',2);}
 text(g,'TAS '+fmt(s.speed*1.943844,0)+' KN',w*.04,h*.14,Math.max(12,w*.015));text(g,'ALT '+fmt(s.alt,0)+' m',w*.96,h*.14,Math.max(12,w*.015),'#e9fdf5','right');text(g,'HDG '+fmt(s.heading,0)+'°',w/2,h*.1,Math.max(12,w*.016),'#e9fdf5','center');text(g,'SYNTHETIC SCENE · NO TERRAIN CAMERA',w/2,h*.91,Math.max(10,w*.010),'#e3f7da','center');}
function trainScene(g,w,h,s,camera){sky(g,w,h);const horizon=h*.45,shift=(Number(s.pos)||0)*.022,night=$('tlx-light').value==='night';
 polygon(g,[[0,horizon],[w,horizon],[w,h],[0,h]],'#748577');for(let i=0;i<18;i++){const x=((i*263-shift)%1800+1800)%1800/1800*w,hh=30+(i*67)%85;g.fillStyle=night?'#17323c':'#819e8b';g.fillRect(x,horizon-hh,28+(i%4)*19,hh);if(i%4===0){g.fillStyle='#243b32';g.beginPath();g.arc(x+18,horizon-hh,22,0,Math.PI*2);g.fill();}}
 const cx=w*.5,vanish=h*.45,grade=(Number(s.grade)||0)*.01;
 polygon(g,[[cx-11,vanish],[cx+11,vanish],[w*.90,h],[w*.10,h]],'#5a635f');
 line(g,[[cx-5,vanish],[w*.22,h]],'#e5dfd4',5);line(g,[[cx+5,vanish],[w*.78,h]],'#e5dfd4',5);
 for(let i=1;i<17;i++){const z=((i*19+shift)%300+300)%300/300;const spread=z*z;const y=vanish+(h-vanish)*spread;line(g,[[cx-12-w*.3*spread,y],[cx+12+w*.3*spread,y]],'#44372e',1+spread*8);}
 if(camera==='cab'){polygon(g,[[0,0],[w*.09,0],[w*.14,h*.64],[w*.22,h],[0,h]],'#102935');polygon(g,[[w,0],[w*.91,0],[w*.86,h*.64],[w*.78,h],[w,h]],'#102935');polygon(g,[[0,h],[w,h],[w*.80,h*.78],[w*.20,h*.78]],'#102a31');g.fillStyle='#193f42';g.fillRect(w*.3,h*.82,w*.4,Math.max(20,h*.13));}
 else{polygon(g,[[w*.39,h*.52],[w*.61,h*.52],[w*.68,h*.89],[w*.32,h*.89]],'#c0d2cb');polygon(g,[[w*.39,h*.52],[w*.61,h*.52],[w*.59,h*.62],[w*.41,h*.62]],'#19556a');polygon(g,[[w*.34,h*.7],[w*.40,h*.7],[w*.40,h*.77],[w*.34,h*.77]],'#f2e3ab');polygon(g,[[w*.6,h*.7],[w*.66,h*.7],[w*.66,h*.77],[w*.6,h*.77]],'#f2e3ab');}
 if(Number.isFinite(s.nearestStop)){const d=Math.max(0,(s.nearestStop||0)-(s.pos||0));text(g,'NEXT STOP '+fmt(d,0)+' m',w*.05,h*.14,Math.max(13,w*.017),'#f4ffdc');}
 text(g,'SPEED '+fmt(s.speed*3.6,1)+' km/h',w*.95,h*.14,Math.max(13,w*.017),'#f5ffe9','right');text(g,'GRADE '+fmt(grade*100,1)+'%',w*.05,h*.22,Math.max(12,w*.014));text(g,'SCHEMATIC TRACK / MODEL STATE',w/2,h*.95,Math.max(11,w*.011),'#e8f1dc','center');}
function subScene(g,w,h,s,camera){const depth=Math.max(0,s.depth||0),grad=g.createLinearGradient(0,0,0,h);grad.addColorStop(0,'#1c5e77');grad.addColorStop(.5,'#0c334e');grad.addColorStop(1,'#061a2d');g.fillStyle=grad;g.fillRect(0,0,w,h);
 for(let i=0;i<45;i++){const x=((i*331+visualDistance*.05)%1307)/1307*w,y=((i*193+depth*.12)%1049)/1049*h,size=1+(i%4);g.fillStyle='rgba(115,187,211,.23)';g.beginPath();g.arc(x,y,size,0,Math.PI*2);g.fill();}
 const surfaceY=Math.max(-50,Math.min(h*.4,h*.30-depth*.15));if(depth<250){g.fillStyle='#68b1cb';g.fillRect(0,Math.max(0,surfaceY),w,4);for(let i=0;i<30;i++){let x=i*w/29;g.fillStyle='rgba(146,210,224,.3)';g.fillRect(x,Math.max(0,surfaceY)+3,2,50+(i%6)*9);}}
 const bottomY=h*.90;polygon(g,[[0,h],[0,bottomY],[w*.14,bottomY-22],[w*.30,bottomY+8],[w*.45,bottomY-13],[w*.62,bottomY+9],[w*.78,bottomY-24],[w,bottomY-4],[w,h]],'#122c37');
 for(let i=0;i<6;i++){g.strokeStyle='rgba(132,216,226,.12)';g.beginPath();g.arc(w*.51,h*.48,(i+1)*w*.07+(sceneTime*.3)%20,0,Math.PI*2);g.stroke();}
 if(camera==='scope'){g.strokeStyle='#74ddc7';g.lineWidth=2;g.beginPath();g.arc(w/2,h/2,Math.min(w,h)*.39,0,Math.PI*2);g.stroke();line(g,[[w*.12,h*.5],[w*.88,h*.5]],'#71d3c18a');line(g,[[w*.5,h*.11],[w*.5,h*.89]],'#71d3c18a');g.fillStyle='#84f3d0';g.beginPath();g.arc(w*.6,h*.39,5,0,Math.PI*2);g.fill();text(g,'SONAR-STYLE ILLUSTRATION · NO LIVE RETURNS',w*.5,h*.9,Math.max(10,w*.013),'#b3f9e3','center');}
 else{const x=w*.49,y=h*.5+(s.verticalSpeed||0)*5;g.save();g.translate(x,y);const length=w*.28,height=h*.07;g.fillStyle='#8baaa9';g.beginPath();g.ellipse(0,0,length,height,0,0,Math.PI*2);g.fill();polygon(g,[[-length*.3,-height],[-length*.1,-height*2],[length*.03,-height*2],[length*.16,-height]],'#809d9e');polygon(g,[[-length*.93,-height*.2],[-length*1.1,-height*.75],[-length*.85,-height*.55]],'#7a9999');g.fillStyle='#d4e8c3';g.fillRect(length*.6,-height*.1,12,3);g.restore();}
 text(g,'DEPTH '+fmt(depth,1)+' m',w*.05,h*.15,Math.max(13,w*.018),'#e2f7f2');text(g,'PRESSURE '+fmt((s.pressure||101325)/1e5,2)+' bar abs',w*.95,h*.15,Math.max(13,w*.016),'#e2f7f2','right');text(g,'ILLUSTRATIVE WATER COLUMN · NOT BATHYMETRY',w/2,h*.96,Math.max(10,w*.011),'#cfe1d9','center');}
function draw(now){if(!document.contains(deck))return;requestAnimationFrame(draw);const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches; if(reduced&&now-sceneTime<250)return;if(now-sceneTime<28)return;const dt=(now-sceneTime)||34;sceneTime=now;frames++;if(now-lastFpsAt>=1200){fps=Math.round(frames*1000/(now-lastFpsAt));frames=0;lastFpsAt=now;$('tlx-fps').textContent=fmt(fps)+' visual FPS · scene is illustrative';}
 const {g,w,h}=canvasContext();g.clearRect(0,0,w,h);if(!state){text(g,'Start or advance a simulation to render its scene.',w/2,h/2,16,'#e6fff7','center');return;}
 try{if(mode==='flight')flightScene(g,w,h,state,$('tlx-camera').value);if(mode==='train')trainScene(g,w,h,state,$('tlx-camera').value);if(mode==='sub')subScene(g,w,h,state,$('tlx-camera').value);weather(g,w,h,visualDistance*.15+now*.0005);if(observing){g.fillStyle='rgba(6,20,29,.85)';g.fillRect(0,h*.34,w,h*.30);text(g,'IMPORTED POSITION · NO RECORDED CAMERA VIEW',w/2,h*.48,Math.max(13,w*.017),'#fff1db','center');text(g,'The observed track does not provide a verified visual scene.',w/2,h*.56,Math.max(11,w*.013),'#d1e8f0','center');}}
 catch(err){g.fillStyle='#091f27';g.fillRect(0,0,w,h);text(g,'Scene fallback: '+String(err.message).slice(0,80),20,h/2,14);}
}
function stateChanged(data){if(!data?.state)return;const oldMode=mode;if(mode!==data.mode)modeChange(data.mode);const s=data.state;
 if(!previous||oldMode!==mode||s.time<previous.time||s.time===0){visualDistance=0;}
 else if(!data.observing){if(mode==='train')visualDistance+=Math.max(0,(s.pos||0)-(previous.pos||0));else if(Number.isFinite(s.lat)&&Number.isFinite(s.lon)){const north=(s.lat-previous.lat)*111200,east=(s.lon-previous.lon)*111200*Math.cos(s.lat*Math.PI/180);visualDistance+=Math.hypot(north,east);}}
 previous=s;state=s;observing=Boolean(data.observing);
 $('tlx-hud-left').textContent=selectedName().slice(0,38);$('tlx-hud-right').textContent=observing?'IMPORTED · UNVERIFIED':'SIMULATED · '+fmt(s.time||0,1)+' s';
 $('tlx-scene-caption').textContent=mode==='flight'?'Stylized motion-linked geography; no satellite-based or actual cockpit camera.':mode==='train'?'Stylized route illustration; published station geometry, if selected, remains a separate data layer.':'Illustrative water column and vehicle silhouette; no certified bathymetry or hull simulation.';
 if(Math.floor(s.time||0)%5===0)updateLearning();}
const canvas=$('tlx-canvas');let startX=null;
canvas.addEventListener('pointerdown',e=>{startX=e.clientX;canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointerup',e=>{if(startX===null)return;const dx=e.clientX-startX;startX=null;if(Math.abs(dx)<12)return;if(mode==='flight')change('tl-bank',dx/8);else if(mode==='train'){const tr=$('tl-traction');set('tl-brake',0);change('tl-traction',dx/5);}else change('tl-sub-heading',dx/3);});
canvas.addEventListener('keydown',e=>{let handled=true;if(e.key==='ArrowLeft'){if(mode==='flight')change('tl-bank',-5);else if(mode==='sub')change('tl-sub-heading',-5);else change('tl-brake',10);}
 else if(e.key==='ArrowRight'){if(mode==='flight')change('tl-bank',5);else if(mode==='sub')change('tl-sub-heading',5);else change('tl-traction',10);}
 else if(e.key==='ArrowUp'){change(mode==='flight'?'tl-throttle':mode==='train'?'tl-traction':'tl-sub-speed',mode==='sub'?1:5);}
 else if(e.key==='ArrowDown'){change(mode==='flight'?'tl-throttle':mode==='train'?'tl-brake':'tl-sub-speed',mode==='sub'?-1:5);}
 else if(e.key===' '){$('tl-play').click();}else handled=false;if(handled)e.preventDefault();});
$('tlx-existing').addEventListener('click',()=>{const show=oldView&&!oldView.classList.contains('tlx-show');oldView?.classList.toggle('tlx-show',Boolean(show));$('tlx-existing').textContent=show?'Hide technical viewport':'Show technical viewport';});
$('tlx-shot').addEventListener('click',drawSave);
$('tlx-find').addEventListener('input',renderHangar);
['tlx-mass','tlx-power','tlx-resistance'].forEach(id=>$(id).addEventListener('input',showTuning));
$('tlx-restore').addEventListener('click',clearTuning);$('tlx-snapshot').addEventListener('click',snapshot);
$('tlx-mta').addEventListener('click',()=>{root.querySelector('[data-mode=train]')?.click();$('mta-load')?.scrollIntoView({behavior:'smooth',block:'center'});$('tlx-mta-status').textContent='MTA browser located. Load its published data explicitly using its own button.';});
$('tlx-data').addEventListener('click',()=>{const t=$('di-route-wrap')||root.querySelector('.di-lab')||$('tl-import-card');if(t)t.scrollIntoView({behavior:'smooth',block:'center'});});
$('tlx-noaa').addEventListener('click',async()=>{const b=$('tlx-noaa'),out=$('tlx-noaa-status'),station=$('tlx-tide-station').value;b.disabled=true;out.textContent='Requesting NOAA public station data…';try{
 const u='https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'+new URLSearchParams({date:'latest',station,product:'water_level',datum:'MLLW',units:'metric',time_zone:'gmt',format:'json',application:'transit_lab_education'});
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),10000);let resp;try{resp=await fetch(u,{signal:ctl.signal,credentials:'omit',cache:'no-store'});}finally{clearTimeout(timer);}if(!resp.ok)throw Error('HTTP '+resp.status);const obj=await resp.json();if(obj.error)throw Error(obj.error.message||'No observation');const p=obj.data?.[0];if(!p||!Number.isFinite(Number(p.v)))throw Error('No valid numeric reading returned.');
 const str=Number(p.v).toFixed(3)+' m above MLLW · '+String(p.t)+' UTC · station '+station+'. This is a published tide-gauge observation, not submarine local depth or ocean current.';out.textContent=str;
 }catch(err){out.textContent='NOAA request unavailable ('+err.message+'). Check browser access and try the official API link; no observation applied.';}finally{b.disabled=false;}});
function merc(lat,lon){const r=6378137,rad=Math.PI/180;return {x:lon*rad*r,y:Math.log(Math.tan(Math.PI/4+clamp(lat,-85,85)*rad/2))*r};}
$('tlx-nasa').addEventListener('click',()=>{const img=$('tlx-nasa-img'),status=$('tlx-nasa-status'),date=$('tlx-nasa-date').value;
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date)){status.textContent='Select a date.';return;}
 let lat=state?.lat,lon=state?.lon;if(!Number.isFinite(lat)||!Number.isFinite(lon)){lat=40.71;lon=-73.99;status.textContent='Using a fixed New York City example center; model has no geographic coordinates. ';}
 const p=merc(lat,lon),half=90000,bbox=[p.x-half,p.y-half,p.x+half,p.y+half].join(',');const qs=new URLSearchParams({SERVICE:'WMS',VERSION:'1.1.1',REQUEST:'GetMap',LAYERS:'MODIS_Terra_CorrectedReflectance_TrueColor',STYLES:'',FORMAT:'image/jpeg',SRS:'EPSG:3857',WIDTH:'900',HEIGHT:'520',BBOX:bbox,TIME:date});
 img.hidden=true;status.textContent='Requesting NASA GIBS image dated '+date+' at approximate modeled center '+lat.toFixed(3)+', '+lon.toFixed(3)+'. No visual simulation coupling.';
 img.onload=()=>{img.hidden=false;status.textContent='NASA GIBS reference image loaded for requested date '+date+'. Regional, cloud-dependent satellite context; not a live aircraft view or historical recreation. NASA attribution applies.';};
 img.onerror=()=>{img.hidden=true;status.textContent='Image unavailable or blocked by provider/browser. No imagery was applied to the simulator.';};
 img.src='https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?'+qs.toString();});
root.addEventListener('leh-transit-state',e=>stateChanged(e.detail));
root.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{if(mode!==b.dataset.mode){clearTuning();modeChange(b.dataset.mode);}}));
['tl-plane','tl-train-profile','hr-sub-vehicle'].forEach(id=>$(id)?.addEventListener('change',()=>{clearTuning();renderHangar();}));
modeChange(mode);if(root.transitLatest)stateChanged(root.transitLatest);requestAnimationFrame(draw);
})();