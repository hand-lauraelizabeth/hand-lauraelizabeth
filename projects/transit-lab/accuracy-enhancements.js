/* Transit teaching upgrades: wind vectors, station approach, pump lag, replay. Educational estimates only. */
(()=>{'use strict';
if(typeof TransitModels==='undefined'||!document.getElementById('leh-transit'))return;
const M=TransitModels,$=id=>document.getElementById(id),r=Math.PI/180,d=180/Math.PI;
const css=document.createElement('style');css.textContent='#leh-transit .tl-extension{border-top:1px solid #d2ded5;margin-top:1rem;padding-top:.8rem}#leh-transit .tl-extension h3{font-size:1.05rem;margin:.2rem 0 .5rem;color:#173d31}#leh-transit .tl-extension p{font-size:.88rem;line-height:1.45}#leh-transit .tl-extra-output{padding:.7rem;background:#eaf1ea;border-radius:8px;margin:.6rem 0;font-size:.92rem;line-height:1.5}#leh-transit .tl-extra-output.warning{background:#fff0dd;border:1px solid #d4a363}';
document.head.append(css);
function add(target,html){const div=document.createElement('section');div.className='tl-extension';div.innerHTML=html;$(target).append(div);return div;}
add('tl-flight-controls','<h3>Wind &amp; ground track</h3><p>Illustrative steady wind. Direction is where wind blows <b>toward</b>, not the usual weather-report “from” bearing.</p><div class="control"><label for="tl-wind">Wind speed <output id="tl-wind-value">0 kn</output></label><input id="tl-wind" type="range" min="0" max="80" value="0"></div><div class="control"><label for="tl-wind-direction">Wind toward <output id="tl-wind-direction-value">90°</output></label><input id="tl-wind-direction" type="range" min="0" max="359" value="90"></div><div id="tl-wind-output" class="tl-extra-output" role="status">Wind is zero; track follows heading.</div>');
add('tl-train-controls','<h3>Station approach advisor</h3><p>Teaching estimate: constant grade, full service brake, 2-second response, and 15% margin. Not a signaling or operational rule.</p><div id="tl-rail-output" class="tl-extra-output" role="status">Move to calculate the distance to the next station.</div>');
add('tl-sub-controls','<h3>Ballast response</h3><p>The requested trim changes gradually at 3 percentage points per simulated second. Pumps, trim moments, dive planes and hull limits are not modeled.</p><div id="tl-ballast-output" class="tl-extra-output" role="status">Neutral ballast trim.</div>');
add('tl-track-tools','<h3>Recorded-position replay</h3><p>Imported samples replay at their timestamps, with gaps shown as jumps. This is not live tracking or interpolated terrain.</p><label for="tl-replay-speed">Recorded-time speed <select id="tl-replay-speed"><option value="60">60×</option><option value="300" selected>300×</option><option value="900">900×</option></select></label><div class="actions"><button type="button" id="tl-replay">▶ Replay positions</button><button type="button" id="tl-stop-replay" class="secondary">Pause replay</button></div><p id="tl-track-replay-status" role="status">Select a point to begin.</p>');
const flight=M.flightStep,train=M.trainStep,sub=M.subStep,seen={};let timer=null,times=[],idx=0,anchor=0,recordedStart=0;
function fmt(x,n=1){return Number(x).toLocaleString('en-US',{maximumFractionDigits:n,minimumFractionDigits:n});}
function show(){
 if(seen.flight){
  const s=seen.flight;$('tl-wind-output').textContent='Groundspeed '+fmt(s.groundSpeed*1.943844,0)+' kn · ground track '+fmt(s.trackDeg,0)+'° · heading '+fmt(s.heading,0)+'° · equivalent airspeed '+fmt(s.equivalentAirspeed*1.943844,0)+' kn. Only wind affects the ground track; lift calculations use air-relative speed.';
 }
 if(seen.train){
  const s=seen.train,spec=M.TRAINS[s.profile],remaining=Math.max(0,s.nearestStop-s.pos),decel=Math.max(.05,spec.brake+.03+M.G*s.grade/100),ideal=M.brakingDistance(s.speed,decel),advice=(ideal+2*s.speed)*1.15;
  const el=$('tl-rail-output');el.classList.toggle('warning',advice>=remaining&&s.speed>.1);
  el.textContent=(s.speed<.1?'Stopped':advice>=remaining?'Braking window reached (model only)':'Approach margin available')+'. Station '+fmt(remaining,0)+' m ahead · ideal braking distance '+fmt(ideal,0)+' m · response-and-margin estimate '+fmt(advice,0)+' m. Real systems also require adhesion, gradients, signal and speed-profile data.';
 }
 if(seen.sub){
  const s=seen.sub;$('tl-ballast-output').textContent='Command '+fmt(s.ballast,0)+'% · effective trim '+fmt(s.actualBallast,1)+'% · vertical rate '+fmt(s.verticalSpeed,2)+' m/s · absolute pressure '+fmt(s.pressure/1e5,2)+' bar. Display depth limit is not a rated hull limit.';
 }
}
function update(){if(typeof requestAnimationFrame==='function')requestAnimationFrame(show);else show();}
M.flightStep=function(s,dt){
 const v=flight(s,dt),ws=Number($('tl-wind').value)*.514444,dir=Number($('tl-wind-direction').value)*r,n=ws*Math.cos(dir),e=ws*Math.sin(dir);
 const loc=M.moveLatLon(v.lat,v.lon,n*dt,e*dt),air=v.speed*Math.cos(v.flightPath*r),gn=air*Math.cos(v.heading*r)+n,ge=air*Math.sin(v.heading*r)+e;
 seen.flight=Object.assign({},v,loc,{groundSpeed:Math.hypot(gn,ge),trackDeg:(Math.atan2(ge,gn)*d+360)%360,equivalentAirspeed:v.speed*Math.sqrt(v.density/1.225)});update();return seen.flight;
};
M.trainStep=function(s,dt){seen.train=train(s,dt);update();return seen.train;};
M.subStep=function(s,dt){
 const target=M.clamp(s.ballast,-100,100),actual=Number.isFinite(s.actualBallast)?s.actualBallast:0,step=actual+M.clamp(target-actual,-3*dt,3*dt);
 const v=sub(Object.assign({},s,{ballast:step}),dt);seen.sub=Object.assign({},v,{ballast:target,actualBallast:step});update();return seen.sub;
};
for(const id of ['tl-wind','tl-wind-direction'])$(id).addEventListener('input',()=>{$('tl-wind-value').textContent=$('tl-wind').value+' kn';$('tl-wind-direction-value').textContent=$('tl-wind-direction').value+'°';update();});
function stop(message){if(timer!==null){clearInterval(timer);timer=null;}$('tl-replay').textContent='▶ Replay positions';if(message)$('tl-track-replay-status').textContent=message;}
async function loadTimes(){const f=$('tl-csv').files?.[0];if(!f)throw Error('Choose a recorded CSV.');return M.parseTrackCsv(await f.text()).map(x=>x.t);}
$('tl-csv').addEventListener('change',()=>{stop('New track selected.');times=[];});
$('leh-transit').addEventListener('leh-transit-track-loaded',event=>{stop('Imported track loaded for replay.');times=(event.detail?.points||[]).map(p=>p.t);idx=0;});
$('tl-replay').addEventListener('click',async()=>{
 if(timer!==null){stop('Replay paused.');return;}
 try{
  if(!times.length)times=await loadTimes();if(times.length<2)throw Error('At least two recorded positions are required. One-point imports can still initialize a hypothetical simulation.');
  idx=Number($('tl-scrub').value);if(idx>=times.length-1){idx=0;$('tl-scrub').value='0';$('tl-scrub').dispatchEvent(new Event('input',{bubbles:true}));}
  recordedStart=times[idx];anchor=performance.now();$('tl-replay').textContent='❚❚ Pause replay';
  timer=setInterval(()=>{
   const now=recordedStart+(performance.now()-anchor)*Number($('tl-replay-speed').value);
   while(idx+1<times.length&&times[idx+1]<=now)idx++;
   if(Number($('tl-scrub').value)!==idx){$('tl-scrub').value=String(idx);$('tl-scrub').dispatchEvent(new Event('input',{bubbles:true}));}
   $('tl-track-replay-status').textContent='Imported, unverified position '+(idx+1)+'/'+times.length+' · '+new Date(times[idx]).toISOString();
   if(idx===times.length-1)stop('Recorded replay complete.');
  },100);
 }catch(error){stop('Replay unavailable: '+error.message);}
});
$('tl-stop-replay').addEventListener('click',()=>stop('Replay paused.'));
$('tl-take').addEventListener('click',()=>stop('Observation-to-simulation handoff; subsequent motion is hypothetical.'));
$('tl-clear-track').addEventListener('click',()=>{stop('Recorded track cleared.');times=[];});
for(const tab of document.querySelectorAll('#leh-transit [data-mode]'))tab.addEventListener('click',()=>stop('Switch to the aircraft tab to replay a track.'));
const aside=document.querySelector('#leh-transit .side-stack'),challenge=document.createElement('section');challenge.className='panel';challenge.innerHTML='<h2>Try a physics challenge</h2><p id="tl-challenge" role="status"></p>';aside.append(challenge);
function challengeText(){const kind=document.querySelector('#leh-transit [data-mode][aria-pressed="true"]')?.dataset.mode;
 $('tl-challenge').textContent=kind==='flight'?'Set a 40 kn wind toward east, then compare ground track and heading at the initial 45° heading.':kind==='train'?'Accelerate toward 2.5 km, then compare distance remaining with the brake-and-response estimate.':'Command +60% ballast trim, advance several seconds, and watch the pump lag and pressure response.';}
for(const tab of document.querySelectorAll('#leh-transit [data-mode]'))tab.addEventListener('click',challengeText);
challengeText();
})();