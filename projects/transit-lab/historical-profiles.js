/* Historical reference profiles and source-aware environmental inputs.
   Verified metadata drives bounded choices; all motion still uses simplified dynamics. */
const TransitHistorical=(()=>{
 'use strict';
 const references={
  dc3:{label:'Douglas DC-3 · 1935',source:'https://airandspace.si.edu/collection-objects/douglas-dc-3/nasm_A19530075000',
   additionalSource:'https://www.museumofflight.org/exhibits-and-events/aircraft/douglas-dc-3',
   facts:['1935 first flight','11,430 kg historical gross mass','987 ft² wing area','370 km/h published top speed'],
   assumptions:'Point-mass drag, thrust, CLmax and maneuver behavior remain illustrative, not DC-3 flight-test data.'},
  gg1:{label:'Pennsylvania Railroad GG1 · 1934',source:'https://www.asme.org/about-asme/engineering-history/landmarks/83-penn-rr-gg1-electric-locomotive-4800',
   facts:['1934 prototype','4,620 continuous horsepower','Passenger service exceeding 100 mph'],
   assumptions:'A 100 mph model speed ceiling and generic train traction and braking; route and train consist are not reproduced.'},
  gato:{label:'USS Harder · Gato class (1943)',source:'https://www.history.navy.mil/research/histories/ship-histories/danfs/h/harder-i.html',
   facts:['Gato-class fleet submarine','8.75 kn published submerged speed','2,424 tons published submerged displacement'],
   assumptions:'Submerged forward-speed ceiling used; generic one-dimensional buoyancy model, not a Gato hull or ballast system.'},
  nautilus:{label:'USS Nautilus SSN-571 · 1954',source:'https://www.history.navy.mil/research/histories/ship-histories/danfs/n/nautilus-ssn-571-iv.html',
   facts:['Commissioned in 1954','4,092 tons published submerged displacement','Published submerged speed above 20 kn'],
   assumptions:'Simulation retains its existing 20 kn interface limit; propulsion, trim, hull rating and thermal systems are not modeled.'}
 };
 const dc3={name:'Douglas DC-3 · historical-reference inputs',mass:11430,wing:987*.09290304,
  cd0:.035,k:.05,thrust:42000,clMax:1.6,speed:75,alt:1600,throttle:48,maxSpeed:370/3.6};
 const gg1={name:'PRR GG1 · historical-reference ceiling',limit:100*.44704,traction:.5,brake:.92};
 function observedWind(properties){
  const speed=properties?.windSpeed?.value,from=properties?.windDirection?.value;
  if(!Number.isFinite(speed)||speed<0||!Number.isFinite(from))throw Error('Observation does not include a valid wind speed and direction.');
  const date=Date.parse(properties.timestamp);
  if(!Number.isFinite(date))throw Error('Observation timestamp is unavailable.');
  return {speedKnots:speed*1.943844,fromDeg:((from%360)+360)%360,towardDeg:((from+180)%360+360)%360,observedAt:new Date(date).toISOString(),ageMinutes:(Date.now()-date)/60000};
 }
 return {references,dc3,gg1,observedWind};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitHistorical;
(function historicalLab(){
 'use strict';
 if(typeof document==='undefined'||typeof TransitModels==='undefined')return;
 const root=document.getElementById('leh-transit');
 if(!root||root.dataset.historicalLab==='ready')return;root.dataset.historicalLab='ready';
 const M=TransitModels,H=TransitHistorical,$=id=>document.getElementById(id);
 M.AIRCRAFT.dc3={...H.dc3};
 M.TRAINS.gg1={...H.gg1};
 function addOption(selectId,value,label){
  const s=$(selectId);if(!s||Array.from(s.options).some(o=>o.value===value))return;
  const option=document.createElement('option');option.value=value;option.textContent=label;s.append(option);
 }
 addOption('tl-plane','dc3','Douglas DC-3 · historical reference (1935)');
 addOption('tl-train-profile','gg1','PRR GG1 · historic electric locomotive (1934)');
 const style=document.createElement('style');
 style.textContent='#leh-transit .hr-panel{background:#f0f6f0;border:1px solid #b8d0c1;border-radius:10px;padding:.8rem;margin:.75rem 0;line-height:1.5}#leh-transit .hr-panel p{font-size:.84rem}#leh-transit .hr-panel a{font-size:.84rem}#leh-transit .hr-panel h3{font-size:1.04rem;margin:.1rem 0 .45rem;font-family:Georgia,serif}#leh-transit .hr-panel ul{padding-left:1.15rem;margin:.4rem 0;font-size:.83rem}#leh-transit .hr-panel label{display:block;margin:.4rem 0}#leh-transit .hr-panel .actions{margin:.45rem 0}';
 document.head.append(style);
 function panel(host,id,title,html){const d=document.createElement('section');d.className='hr-panel';d.id=id;d.innerHTML='<h3>'+title+'</h3>'+html;$(host).append(d);return d;}
 panel('tl-flight-controls','hr-flight','Historical aircraft source',
  '<div id="hr-flight-details">Select the DC-3 to see documented vehicle specifications and model assumptions.</div>');
 panel('tl-train-controls','hr-rail','Historical locomotive source',
  '<div id="hr-rail-details">Select the GG1 to view documented historical specifications and the modeled values.</div>');
 panel('tl-sub-controls','hr-sub','Submarine reference',
  '<label for="hr-sub-vehicle">Historical vessel<select id="hr-sub-vehicle"><option value="generic">Generic buoyancy demonstration</option><option value="gato">USS Harder · Gato class (1943)</option><option value="nautilus">USS Nautilus SSN-571 (1954)</option></select></label><div id="hr-sub-details"></div>');
 panel('tl-flight-controls','hr-weather','NOAA station-wind challenge',
  '<p>Load a recent National Weather Service observation, then explicitly apply its measured <strong>surface wind</strong> to the simplified constant-wind flight model. This does not represent winds aloft, runway conditions or a historical flight.</p><label for="hr-airport">Observation station<select id="hr-airport"><option value="KJFK">New York JFK (KJFK)</option><option value="KLGA">LaGuardia (KLGA)</option><option value="KEWR">Newark Liberty (KEWR)</option></select></label><div class="actions"><button id="hr-load-wind" type="button" class="secondary">Load observed wind</button><button id="hr-use-wind" type="button" disabled>Apply to simulation</button></div><p id="hr-wind-status" role="status">No external observation requested.</p><a href="https://www.weather.gov/documentation/services-web-api" target="_blank" rel="noopener">NOAA/NWS observation source and service limits</a>');
 panel('tl-sub-controls','hr-water','Environmental density experiment',
  '<label for="hr-density">Water density (hypothetical)<select id="hr-density"><option value="1025">Seawater reference · 1,025 kg/m³</option><option value="1000">Fresh water · 1,000 kg/m³</option><option value="1015">Brackish example · 1,015 kg/m³</option><option value="1030">Denser seawater example · 1,030 kg/m³</option></select></label><p>Fixed displacement volume: changing fluid density changes buoyancy and hydrostatic pressure. These are illustrative environments, not current ocean measurements.</p>');
 function sourceLink(ref){
  const a=document.createElement('a');a.href=ref.source;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Historical reference: '+new URL(ref.source).hostname;return a;
 }
 function details(id,ref){
  const host=$(id);host.replaceChildren();
  if(!ref){const p=document.createElement('p');p.textContent='Generic model: no historical aircraft or locomotive specification asserted.';host.append(p);return;}
  const ul=document.createElement('ul');
  for(const fact of ref.facts){const li=document.createElement('li');li.textContent=fact;ul.append(li);}
  const p=document.createElement('p');p.textContent='Simulation boundary: '+ref.assumptions;
  host.append(ul,p,sourceLink(ref));
  if(ref.additionalSource){const a=document.createElement('a');a.href=ref.additionalSource;a.target='_blank';a.rel='noopener noreferrer';a.textContent=' · Wing-area reference: Museum of Flight';host.append(a);}
 }
 function render(){
  details('hr-flight-details',$('tl-plane').value==='dc3'?H.references.dc3:null);
  details('hr-rail-details',$('tl-train-profile').value==='gg1'?H.references.gg1:null);
  details('hr-sub-details',H.references[$('hr-sub-vehicle').value]||null);
 }
 function vesselConfig(){
  const id=$('hr-sub-vehicle').value,slider=$('tl-sub-speed');
  slider.max=id==='gato'?'8.75':'20';slider.step=id==='gato'?'.25':'1';
  if(Number(slider.value)>Number(slider.max)){slider.value=slider.max;slider.dispatchEvent(new Event('input',{bubbles:true}));}
 }
 $('tl-plane').addEventListener('change',render);
 $('tl-train-profile').addEventListener('change',render);
 $('hr-sub-vehicle').addEventListener('change',()=>{vesselConfig();render();$('tl-reset').click();});
 $('hr-density').addEventListener('change',()=>{const s=$('hr-water').querySelector('p');s.textContent='Selected density '+$('hr-density').value+' kg/m³. Model changes at the next simulation step. Environmental examples are not observations.';});
 let lastWind=null;
 $('hr-load-wind').addEventListener('click',async()=>{
  const button=$('hr-load-wind'),station=$('hr-airport').value;
  button.disabled=true;$('hr-use-wind').disabled=true;lastWind=null;
  $('hr-wind-status').textContent='Requesting station observation from NOAA/NWS…';
  try{
   const response=await fetch('https://api.weather.gov/stations/'+encodeURIComponent(station)+'/observations/latest',{headers:{Accept:'application/geo+json'}});
   if(!response.ok)throw Error('NWS returned HTTP '+response.status);
   const json=await response.json(),w=H.observedWind(json.properties);
   if(w.ageMinutes< -5||w.ageMinutes>180)throw Error('Latest station observation is outside the 3-hour freshness window; not applying stale wind.');
   lastWind={...w,station};
   $('hr-wind-status').textContent=station+' · observed '+w.observedAt+' · '+w.speedKnots.toFixed(1)+' kn FROM '+w.fromDeg.toFixed(0)+'° (model input is TOWARD '+w.towardDeg.toFixed(0)+'°). Observation age '+Math.max(0,w.ageMinutes).toFixed(0)+' min. Surface wind only.';
   $('hr-use-wind').disabled=false;
  }catch(e){$('hr-wind-status').textContent='Observation unavailable: '+e.message+'. The manual wind controls remain available; browser cross-origin restrictions may apply.';}
  finally{button.disabled=false;}
 });
 $('hr-use-wind').addEventListener('click',()=>{
  if(!lastWind)return;
  if(!$('tl-wind')||!$('tl-wind-direction'))return;
  $('tl-wind').value=String(Math.min(80,Math.round(lastWind.speedKnots)));
  $('tl-wind-direction').value=String(Math.round(lastWind.towardDeg)%360);
  for(const id of ['tl-wind','tl-wind-direction'])$(id).dispatchEvent(new Event('input',{bubbles:true}));
  $('hr-wind-status').textContent='Applied '+lastWind.station+' surface wind measured '+lastWind.observedAt+' as a constant illustrative wind vector. Surface measurement does not represent wind aloft or a historical flight.';
 });
 root.addEventListener('leh-transit-state',e=>{
  if(e.detail?.mode==='sub'&&e.detail?.state?.time===0)vesselConfig();
 });
 render();vesselConfig();
})();
