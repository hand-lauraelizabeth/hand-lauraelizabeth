/* Transit Lab: transparent, non-operational learning missions and spherical navigation. */
const TransitMissionMath=(()=>{'use strict';
const EARTH=6371008.8,R=Math.PI/180,D=180/Math.PI;
function normalize(degrees){return (degrees%360+360)%360;}
function distanceBearing(lat1,lon1,lat2,lon2){for(const n of [lat1,lon1,lat2,lon2])if(!Number.isFinite(n))throw Error('Coordinates must be finite.');if(Math.abs(lat1)>90||Math.abs(lat2)>90||Math.abs(lon1)>180||Math.abs(lon2)>180)throw Error('Coordinates outside geographic range.');const a=lat1*R,b=lat2*R,dlat=(lat2-lat1)*R,dlon=(lon2-lon1)*R,h=Math.sin(dlat/2)**2+Math.cos(a)*Math.cos(b)*Math.sin(dlon/2)**2;
 const distance=2*EARTH*Math.asin(Math.sqrt(Math.max(0,Math.min(1,h))));const y=Math.sin(dlon)*Math.cos(b),x=Math.cos(a)*Math.sin(b)-Math.sin(a)*Math.cos(b)*Math.cos(dlon);
 return {distance,bearing:normalize(Math.atan2(y,x)*D)};}
// Destination heading that would cancel steady crosswind, if possible. Mathematical vector estimate only.
function windCorrection(courseDeg,trueAirspeed,windTowardDeg,windSpeed){if(trueAirspeed<=0||!Number.isFinite(trueAirspeed)||windSpeed<0||!Number.isFinite(windSpeed))throw Error('Invalid wind or airspeed.');const c=courseDeg*R,w=windTowardDeg*R;
 const across=windSpeed*Math.sin(w-c),along=windSpeed*Math.cos(w-c);
 if(Math.abs(across)>=trueAirspeed)return {possible:false,across,along};
 const correction=Math.asin(-across/trueAirspeed),groundspeed=trueAirspeed*Math.cos(correction)+along;
 return {possible:groundspeed>0,correctionDeg:correction*D,heading:normalize(courseDeg+correction*D),groundspeed,across,along};}
function approach(distance,speed,maximumBrake,grade=0,reaction=2,margin=.15){const decel=maximumBrake+.03+9.80665*grade/100;const ideal=decel>0?speed**2/(2*decel):Infinity;const estimated=(ideal+reaction*speed)*(1+margin);return {ideal,estimated,remaining:distance,decel,brakeNow:estimated>=distance};}
function depthAssessment(depth,rate,target,heldSeconds=0){const error=depth-target,inside=Math.abs(error)<=5&&Math.abs(rate)<=.15;return {error,inside,complete:inside&&heldSeconds>=5};}
return {distanceBearing,windCorrection,approach,depthAssessment,normalize};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitMissionMath;
(()=>{'use strict';
if(typeof document==='undefined'||!document.getElementById('leh-transit')||typeof TransitModels==='undefined')return;
const $=id=>document.getElementById(id),M=TransitModels,G=TransitMissionMath,root=$('leh-transit');
const style=document.createElement('style');style.textContent=`#leh-transit .mission{margin-top:.9rem;padding:1rem;border:1px solid var(--border);border-radius:12px;background:#fbfdf9}#leh-transit .mission h3{font-size:1.12rem;margin:0 0 .4rem;font-family:Georgia,serif;color:var(--ink)}#leh-transit .mission p{font-size:.88rem;margin:.3rem 0 .7rem}#leh-transit .mission .mission-metric{border-left:4px solid var(--green);background:var(--pale);padding:.7rem;margin:.7rem 0;line-height:1.55;font-size:.9rem}#leh-transit .mission .mission-metric[data-state="warning"]{border-color:#bc7448;background:#fff1df}#leh-transit .mission .mission-metric[data-state="done"]{border-color:#24704f;background:#e0f1e2}#leh-transit .mission select,#leh-transit .mission input[type=number]{width:100%;max-width:100%;padding:.5rem;border:1px solid #93ada0;border-radius:7px;background:white;color:var(--ink)}#leh-transit .mission .mission-coordinates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem}#leh-transit .mission progress{width:100%;height:.8rem}#leh-transit .mission label{font-size:.84rem}#leh-transit .mission .mission-note{color:var(--muted);font-size:.81rem}`;document.head.append(style);
function add(id,markup){const sec=document.createElement('section');sec.className='mission';sec.innerHTML=markup;$(id).append(sec);return sec;}
add('tl-flight-controls',`<h3>Navigation challenge</h3><p>Choose a geographic target and steer using a true bearing. This is <strong>not</strong> a published route, ATC instruction, terrain-avoidance model, or approach procedure.</p><label for="tl-nav-target">Waypoint <select id="tl-nav-target"><option value="lga">LaGuardia reference point (NYC public geographic reference)</option><option value="jfk">JFK reference point (FAA published)</option><option value="custom">Custom latitude / longitude</option></select></label><div id="tl-nav-custom" class="mission-coordinates" hidden><label for="tl-nav-lat">Latitude <input id="tl-nav-lat" type="number" step="0.00001" min="-90" max="90" value="40.77472"></label><label for="tl-nav-lon">Longitude <input id="tl-nav-lon" type="number" step="0.00001" min="-180" max="180" value="-73.87222"></label></div><div id="tl-nav-readout" class="mission-metric" role="status" aria-live="polite">Choose a target to start navigating.</div><p class="mission-note">True bearing and distance use a spherical Earth approximation. Wind correction is an ideal constant-wind vector estimate, not flight guidance. <a href="https://www.faa.gov/air_traffic/publications/atpubs/aip_html/part3_ad_2.0_new_york.html" target="_blank" rel="noopener">FAA JFK reference</a> · <a href="https://zr.planning.nyc.gov/article-vi/chapter-1/61-41" target="_blank" rel="noopener">NYC LaGuardia geographic reference</a>.</p>`);
add('tl-train-controls',`<h3>Stop at the platform</h3><p>Choose a marker on the illustrative straight track, then aim to stop within ±15 m at less than 0.5 m/s. Stops are hypothetical.</p><label for="tl-mission-station">Target station <select id="tl-mission-station"><option value="2500">2.5 km</option><option value="5500">5.5 km</option><option value="10000">10 km terminus</option></select></label><progress id="tl-mission-train-progress" max="100" value="0" aria-label="Progress toward the selected station"></progress><div class="mission-metric" id="tl-mission-train-readout" role="status" aria-live="polite">Set traction to begin. Start braking before the station.</div><p class="mission-note">The readout uses hypothetical constant deceleration and grade; no adhesion, signaling, or timetable protection.</p>`);
add('tl-sub-controls',`<h3>Depth-control challenge</h3><p>Bring the modeled craft within 5 m of a target depth, with less than 0.15 m/s vertical speed, and hold for 5 simulated seconds.</p><label for="tl-mission-depth">Target depth <select id="tl-mission-depth"><option value="75">75 m</option><option value="100">100 m</option><option value="150">150 m</option></select></label><div class="mission-metric" id="tl-mission-sub-readout" role="status" aria-live="polite">Adjust ballast and advance time to try a controlled depth change.</div><p class="mission-note">This is an abstract buoyancy exercise. Ballast response, underwater obstacles, trim, dive planes and vessel safety limits are not represented.</p>`);
let current={mode:'flight',state:M.flightInit(),observing:false},lastTrain=null,hold=0,lastSubTime=0,trainPassed=false;
const TARGETS={lga:{lat:40+46/60+29/3600,lon:-(73+52/60+20/3600),label:'LGA'},jfk:{lat:40+38/60+23.741/3600,lon:-(73+46/60+43.292/3600),label:'JFK'}};
function fmt(v,d=1){return Number(v).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
function renderFlight(){if(current.mode!=='flight')return;const el=$('tl-nav-readout'),s=current.state;
 if(current.observing){el.dataset.state='warning';el.textContent='Imported track is an unverified observation. Take simulation controls to begin the navigation challenge.';return;}
 let p=TARGETS[$('tl-nav-target').value];if(!p){const lat=Number($('tl-nav-lat').value),lon=Number($('tl-nav-lon').value);if(!$('tl-nav-lat').value||!$('tl-nav-lon').value||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180){el.dataset.state='warning';el.textContent='Enter valid latitude and longitude.';return;}p={lat,lon,label:'Custom waypoint'};}
 try{const nav=G.distanceBearing(s.lat,s.lon,p.lat,p.lon),tas=s.speed*Math.cos(s.flightPath*Math.PI/180),windSpeed=Number($('tl-wind')?.value||0)*.514444,windDir=Number($('tl-wind-direction')?.value||90),w=G.windCorrection(nav.bearing,tas,windDir,windSpeed);
 const near=nav.distance<=500;el.dataset.state=near?'done':!w.possible?'warning':'normal';const eta=w.possible?fmt(nav.distance/w.groundspeed/60,1)+' min':'not available';el.textContent=`${p.label}: ${fmt(nav.distance/1852,2)} NM away · true bearing ${fmt(nav.bearing,0)}° · current nose heading ${fmt(s.heading,0)}° · ${near?'Target vicinity reached (within 500 m).':w.possible?'Idealized steady-wind heading '+fmt(w.heading,0)+'°; track-aligned groundspeed '+fmt(w.groundspeed*1.943844,0)+' kn; ETA '+eta+'.':'Chosen airspeed cannot maintain this course against the modeled wind.'}`;
 }catch(e){el.dataset.state='warning';el.textContent=e.message;}}
function renderTrain(){if(current.mode!=='train')return;const el=$('tl-mission-train-readout'),s=current.state,target=Number($('tl-mission-station').value),d=target-s.pos,guess=G.approach(Math.max(0,d),s.speed,M.TRAINS[s.profile].brake,s.grade),near=Math.abs(d)<=15&&s.speed<.5;
 if(lastTrain&&lastTrain.pos<=target+15&&s.pos>target+15)trainPassed=true;
 el.dataset.state=near?'done':trainPassed?'warning':guess.brakeNow&&s.speed>.5?'warning':'normal';
 el.textContent=near?`Platform stop achieved in this model: ${fmt(s.pos,1)} m, ${fmt(s.speed*3.6,1)} km/h. Within ±15 m and below 0.5 m/s.`:
 trainPassed?`Station marker passed at ${fmt(s.pos,0)} m; target was ${fmt(target,0)} m. Reset the model to retry.`:
 `${fmt(Math.max(0,d),0)} m to target · ${fmt(s.speed*3.6,1)} km/h · modeled response/brake distance ${fmt(guess.estimated,0)} m. ${guess.brakeNow&&s.speed>.5?'Braking window reached under assumed conditions.':s.speed<.5?'Stopped before the platform; try adjusting traction.':'Compare distance with braking margin.'}`;
 $('tl-mission-train-progress').value=Math.max(0,Math.min(100,s.pos/target*100));lastTrain=s;}
function renderSub(){if(current.mode!=='sub')return;const s=current.state,target=Number($('tl-mission-depth').value),a=G.depthAssessment(s.depth,s.verticalSpeed,target,hold),el=$('tl-mission-sub-readout');el.dataset.state=a.complete?'done':a.inside?'normal':Math.abs(a.error)>30?'warning':'normal';el.textContent=`Depth ${fmt(s.depth,1)} m; target ${target} m (${fmt(Math.abs(a.error),1)} m ${a.error>=0?'below':'above'} target); vertical rate ${fmt(s.verticalSpeed,2)} m/s. ${a.complete?'Goal achieved for five simulated seconds.':a.inside?'Within target band: stable for '+fmt(hold,1)+' / 5 s.':'Adjust ballast to approach, then reduce your vertical rate.'}`;}
function refresh(){renderFlight();renderTrain();renderSub();}
root.addEventListener('leh-transit-route-selected',event=>{
 const r=event.detail?.route;if(!r||!Number.isFinite(r.lengthM))return;
 const select=$('tl-mission-station');select.replaceChildren();
 const stations=(r.stations||[]).filter(st=>st.distanceM>=100&&st.distanceM<=r.lengthM);
 const targets=stations.map(st=>[st.distanceM,st.name+' · '+(st.distanceM/1000).toFixed(2)+' km']);
 targets.push([r.lengthM,'Mapped segment end · '+(r.lengthM/1000).toFixed(2)+' km']);
 for(const [value,label] of targets){const o=document.createElement('option');o.value=String(Math.round(value*10)/10);o.textContent=label;select.add(o);}
 const note=$('tl-train-controls').querySelector('.mission > p');if(note)note.textContent='Choose a published station centroid matched to the selected route geometry. Aim to stop within an illustrative ±15 m band below 0.5 m/s. Distance is measured on the published line, not surveyed track chainage.';
 trainPassed=false;lastTrain=null;renderTrain();
});
root.addEventListener('leh-transit-route-cleared',()=>{
 const select=$('tl-mission-station');select.replaceChildren();
 for(const [value,label] of [['2500','2.5 km'],['5500','5.5 km'],['10000','10 km terminus']]){const o=document.createElement('option');o.value=value;o.textContent=label;select.add(o);}
 const note=$('tl-train-controls').querySelector('.mission > p');if(note)note.textContent='Choose a marker on the illustrative straight track, then aim to stop within ±15 m at less than 0.5 m/s. Stops are hypothetical.';
 trainPassed=false;lastTrain=null;renderTrain();
});
root.addEventListener('leh-transit-state',event=>{const d=event.detail;if(!d?.state)return;const next=d.mode;if(next==='sub'){const dt=d.state.time-lastSubTime;if(current.mode!=='sub'||dt<0)hold=0;const within=G.depthAssessment(d.state.depth,d.state.verticalSpeed,Number($('tl-mission-depth').value)).inside;hold=within?hold+Math.max(0,Math.min(1,dt)):0;lastSubTime=d.state.time;}if(next!=='train')lastTrain=null;current={mode:next,state:d.state,observing:d.observing};refresh();});
$('tl-nav-target').addEventListener('change',()=>{$('tl-nav-custom').hidden=$('tl-nav-target').value!=='custom';renderFlight();});for(const id of ['tl-nav-lat','tl-nav-lon','tl-wind','tl-wind-direction'])$(id)?.addEventListener('input',renderFlight);
$('tl-mission-station').addEventListener('change',()=>{trainPassed=false;lastTrain=null;renderTrain();});$('tl-mission-depth').addEventListener('change',()=>{hold=0;renderSub();});
$('tl-reset').addEventListener('click',()=>{trainPassed=false;hold=0;lastTrain=null;lastSubTime=0;refresh();});
root.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{hold=0;lastTrain=null;trainPassed=false;refresh();}));
refresh();
})();
