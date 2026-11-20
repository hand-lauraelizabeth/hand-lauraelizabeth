/* Source-disclosed environmental teaching scenarios; never inferred real conditions. */
const TransitEnvironment=(()=>{
 'use strict';
 const scenarios={dry:1,wet:.75,low:.45};
 const brakeEstimate=(speed,brake,adhesion,grade=0)=>{
  if(![speed,brake,adhesion,grade].every(Number.isFinite))throw Error('Finite parameters required');
  const decel=brake*Math.max(.3,Math.min(1,adhesion))+.03+9.80665*grade/100;
  return {decel,ideal:decel>0?speed*speed/(2*decel):Infinity,planning:decel>0?1.15*(speed*speed/(2*decel)+2*speed):Infinity};
 };
 const currentVector=(throughWaterKn,heading,currentKn,currentToward)=>{
  const r=Math.PI/180,t=heading*r,c=currentToward*r;
  const north=throughWaterKn*Math.cos(t)+currentKn*Math.cos(c),east=throughWaterKn*Math.sin(t)+currentKn*Math.sin(c);
  return {groundKnots:Math.hypot(north,east),groundTrack:(Math.atan2(east,north)*180/Math.PI+360)%360,northKnots:north,eastKnots:east};
 };
 return {scenarios,brakeEstimate,currentVector};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitEnvironment;
(function installEnvironmentControls(){
 'use strict';
 if(typeof document==='undefined'||typeof TransitModels==='undefined')return;
 const root=document.getElementById('leh-transit');if(!root||root.dataset.environmentV3==='ready')return;root.dataset.environmentV3='ready';
 const $=id=>document.getElementById(id),E=TransitEnvironment,M=TransitModels;
 const style=document.createElement('style');
 style.textContent='#leh-transit .ev-card{margin-top:1rem;border:1px solid #b3cfc9;border-radius:12px;padding:.8rem;background:linear-gradient(135deg,#eef6f2,#f7faf7)}#leh-transit .ev-card h3{font-size:1.04rem;font-family:Georgia,serif;margin:.05rem 0 .5rem}#leh-transit .ev-card p{font-size:.83rem;line-height:1.5}#leh-transit .ev-card select{min-height:40px}#leh-transit .ev-card output{font-weight:750}#leh-transit .ev-metric{padding:.6rem;border-radius:8px;background:#e0eee7;border-left:3px solid #317f6d;font-size:.84rem;line-height:1.5;min-height:45px}';
 document.head.append(style);
 function append(parent,id,title,inner){
  const c=document.createElement('section');c.className='ev-card';c.id=id;c.innerHTML='<h3>'+title+'</h3>'+inner;
  $(parent)?.append(c);return c;
 }
 append('tl-flight-controls','ev-flight','Atmospheric variation',
 '<label for="ev-gust">Modeled wind variation <output id="ev-gust-value">0 kn</output><input type="range" id="ev-gust" min="0" max="30" step="5" value="0"></label><p>Deterministic variation added to the constant wind vector. It is an <strong>illustrative gust experiment</strong>, not a real turbulence model, pilot-report measurement, or a NOAA gust forecast. Use the NOAA weather panel separately for real station surface observations.</p><p id="ev-flight-status" class="ev-metric" role="status">Constant selected wind. Gust variation off.</p>');
 append('tl-train-controls','ev-train','Rail adhesion challenge',
 '<label for="ev-adhesion">Hypothetical wheel–rail contact<select id="ev-adhesion"><option value="1">Baseline · idealized dry (100%)</option><option value=".75">Reduced traction/braking (75%)</option><option value=".45">Severely reduced (45%)</option></select></label><p>Multipliers are <strong>exercise assumptions, not measured rail coefficients</strong>. Both traction and commanded braking are scaled. Track grade remains separately controlled; actual wheel-slide protection, contamination and adhesion recovery are not simulated.</p><p id="ev-train-status" class="ev-metric" role="status">Baseline contact. Select a different condition to compare stopping distance.</p>');
 append('tl-sub-controls','ev-sub','Underwater current challenge',
 '<label for="ev-current">Hypothetical current <output id="ev-current-value">0.0 kn</output><input type="range" id="ev-current" min="0" max="3" step=".25" value="0"></label><label for="ev-current-heading">Current flows toward <output id="ev-current-heading-value">90°</output><input type="range" id="ev-current-heading" min="0" max="359" step="1" value="90"></label><p>The vector adds to the vessel’s through-water motion to estimate ground track. It is a <strong>fixed hypothetical current</strong>, not measured ocean circulation. Current and heading are true bearings, and speed remains in knots.</p><p id="ev-sub-status" class="ev-metric" role="status">No current. Ground track matches commanded heading.</p>');
 for(const id of ['ev-gust','ev-current','ev-current-heading','ev-adhesion'])$(id).addEventListener('input',()=>{
  if(id==='ev-gust')$('ev-gust-value').textContent=$('ev-gust').value+' kn';
  if(id==='ev-current')$('ev-current-value').textContent=Number($('ev-current').value).toFixed(2)+' kn';
  if(id==='ev-current-heading')$('ev-current-heading-value').textContent=$('ev-current-heading').value+'°';
  root.dispatchEvent(new CustomEvent('leh-transit-environment-change',{detail:{id,value:$(id).value}}));
  // Existing simulation controls are sampled on the next Advance tick; do not imply live observations.
  if(root.transitLatest?.state)render(root.transitLatest);
 });
 function fmt(n,d=1){return Number.isFinite(n)?n.toFixed(d):'—';}
 function render(d){
  if(!d?.state)return;const s=d.state;
  if(d.mode==='flight')$('ev-flight-status').textContent='Selected gust variation ±'+$('ev-gust').value+' kn (deterministic, time-varying model). Observations, when loaded, are surface station winds; modeled variation is not measured.';
  if(d.mode==='train'){
   const k=Number($('ev-adhesion').value),spec=M.TRAINS[s.profile];
   const estimate=E.brakeEstimate(s.speed,spec.brake,k,s.grade||0);
   $('ev-train-status').textContent='Multiplier '+fmt(k,2)+'× · at '+fmt(s.speed*3.6)+' km/h, ideal modeled full-brake stop '+(Number.isFinite(estimate.ideal)?fmt(estimate.ideal,0)+' m':'not possible under selected grade')+'. Add operator response and margin: '+(Number.isFinite(estimate.planning)?fmt(estimate.planning,0)+' m':'unbounded')+'. These are teaching values.';
  }
  if(d.mode==='sub'){
   const vector=E.currentVector(Number(s.speed)||0,Number(s.heading)||0,Number($('ev-current').value),Number($('ev-current-heading').value));
   $('ev-sub-status').textContent='Current '+fmt(Number($('ev-current').value),2)+' kn toward '+$('ev-current-heading').value+'° · modeled ground speed '+fmt(vector.groundKnots,2)+' kn · ground track '+fmt(vector.groundTrack,0)+'°. No real ocean data applied.';
  }
 }
 root.addEventListener('leh-transit-state',e=>render(e.detail));
 if(root.transitLatest)render(root.transitLatest);
})();
