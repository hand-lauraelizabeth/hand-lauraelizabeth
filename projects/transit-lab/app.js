/* Transit Simulation Lab — browser-local simulations and optional map/CSV input. */
(()=>{'use strict';
const M=TransitModels,$=id=>document.getElementById(id),root=$('leh-transit');if(!root)return;
const facts={
 flight:[['A coordinated, level turn obeys approximately ω = g·tan(bank)/true airspeed, for modest bank angles with sufficient lift. Slower flight at the same bank angle turns faster.','https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/faa-h-8083-25c.pdf'],['Aerodynamic lift: L = ½ρV²SCL. The model estimates the lift coefficient required to support the aircraft in a bank; it does not derive lift from a full aerodynamic simulation.','https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/lift-equation/'],['Drag: D = ½ρV²SCd. This model uses an illustrative drag polar Cd = Cd0 + kCL²; the generic vehicle coefficients are not manufacturer data.','https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/'],['A recorded ground track is not the same as the view out of the cockpit. Recreating a real view requires a timestamped track, camera orientation, atmospheric conditions and licensed geospatial terrain.','https://developers.google.com/maps/documentation/tile/3d-tiles-overview']],
 train:[['When deceleration is constant and starts immediately, stopping distance is v²/(2a). Doubling speed quadruples this idealized distance; reaction time and gradients add important complications.','https://www.physicsclassroom.com/class/1DKin/Lesson-6/Kinematic-Equations'],['For small railway grades, the longitudinal component of gravity is approximately g × grade_fraction. Uphill reduces acceleration; downhill increases it.','https://www.britannica.com/science/inclined-plane'],['Train position and arrival information can come from GTFS Schedule and GTFS Realtime feeds. They do not by themselves supply a validated vehicle dynamics model.','https://gtfs.org/documentation/overview/'],['Signal aspects, adhesion changes, curves, dispatch decisions, and braking curves are outside this introductory straight-track demonstration. A genuine train-operation simulator must model them.','https://gtfs.org/documentation/overview/']],
 sub:[['Absolute pressure increases with depth: P = P_surface + ρgh. Using 1,025 kg/m³ seawater, 10 m adds about one atmosphere.','https://oceanservice.noaa.gov/facts/pressure.html'],['Archimedes’ principle: buoyant force equals the weight of fluid displaced. Neutral buoyancy occurs when the vehicle’s total weight matches its displaced-water weight.','https://www.britannica.com/science/Archimedes-principle'],['A ballast change is not the same as a dive-plane command. A realistic vessel model must account for forward flow, pitch, trim, ballast systems, drag and depth limits.','https://oceanservice.noaa.gov/facts/pressure.html'],['GEBCO provides global bathymetric grids, but their resolution and source quality vary. This demonstration uses a schematic water column, not GEBCO terrain.','https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2026-grid']]
};
let kind='flight',state=M.flightInit(),running=false,clock=null,factIndex=0,map=null,marker=null,trailLayer=null,importLayer=null,imported=[],selectedPoint=-1,observing=false;
let path=[[state.lat,state.lon]],pendingSeconds=0,railRoute=null;
const fm=(v,d=1)=>Number(v).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
function setStatus(txt){$('tl-status').textContent=txt;}
let frameLast=0,frameCarry=0;
function pulse(now){if(!running)return;
 frameCarry+=Math.max(0,Math.min(.15,(now-frameLast)/1000));frameLast=now;
 if(frameCarry>=.05){const dt=frameCarry*Number($('tl-time-scale').value);frameCarry=0;advance(dt);}
 if(running)clock=requestAnimationFrame(pulse);
}
function start(){if(running)return;running=true;frameLast=performance.now();frameCarry=0;$('tl-play').textContent='❚❚ Pause';setStatus('Simulating · time and positions are modeled, not observed.');clock=requestAnimationFrame(pulse);}
function pause(){running=false;if(clock!==null)cancelAnimationFrame(clock);clock=null;$('tl-play').textContent='▶ Start';}
function drawTrainRoute(){
 const scene=$('tl-train-scene'),track=$('tl-track'),meter=railRoute?.lengthM||10000;
 scene.querySelector('p').textContent=railRoute?'Mapped '+(meter/1000).toFixed(2)+' km route · '+railRoute.name+' · station positions approximated from published geographic coordinates':'Illustrative 10 km straight route — no agency or railway represented';
 scene.querySelector('p.small').textContent=railRoute?'Distance follows the published geographic polyline. Model train physics and grade remain hypothetical; station positions are point-to-line matches, not track measurements.':'Station intervals and operating parameters are hypothetical.';
 for(const old of [...track.querySelectorAll('.station')])old.remove();
 let marks=railRoute?[{distanceM:0,name:'Start'},...(railRoute.stations||[]),{distanceM:meter,name:'End'}]:[{distanceM:0,name:'0'},{distanceM:2500,name:'2.5'},{distanceM:5500,name:'5.5'},{distanceM:10000,name:'10 km'}];
 if(marks.length>9){const first=marks[0],last=marks.at(-1);const inner=marks.slice(1,-1);marks=[first,...Array.from({length:6},(_,i)=>inner[Math.round(i*(inner.length-1)/5)]),last];}
 const marker=$('tl-train-marker');
 for(const m of marks){
  const tick=document.createElement('span');tick.className='station';tick.style.left=(Math.max(0,Math.min(100,m.distanceM/meter*100)))+'%';
  tick.textContent=(m.distanceM/1000).toFixed(1);tick.title=m.name+' · '+(m.distanceM/1000).toFixed(2)+' km from mapped origin';
  track.insertBefore(tick,marker);
 }
}
function reset(){pause();if(kind==='flight'){state=M.flightStep(M.flightInit($('tl-plane').value),0);$('tl-throttle').value=state.throttle;$('tl-bank').value=0;$('tl-path').value=0;}else if(kind==='train'){state=M.trainInit($('tl-train-profile').value);$('tl-traction').value=0;$('tl-brake').value=0;$('tl-grade').value=0;
 if(railRoute){const length=railRoute.lengthM,stops=[0,...(railRoute.stations||[]).map(x=>x.distanceM),length].filter(x=>Number.isFinite(x)&&x>=0&&x<=length).sort((a,b)=>a-b);
  state.length=length;state.stops=stops.filter((x,i)=>i===0||x-stops[i-1]>.2);state.nearestStop=state.stops.find(x=>x>0.1)??length;state.routeName=railRoute.name;state.stationCount=railRoute.stations?.length||0;}
 drawTrainRoute();}else{state=M.subInit();$('tl-ballast').value=0;$('tl-sub-speed').value=3;$('tl-sub-heading').value=90;}
 path=(kind==='train'?[]:[[state.lat,state.lon]]);observing=false;selectedPoint=-1;pendingSeconds=0;factIndex=0;setStatus('Model reset. Inputs and measurements are illustrative.');refresh();}
function setMode(next){if(!['flight','train','sub'].includes(next))return;kind=next;for(const btn of root.querySelectorAll('[data-mode]'))btn.setAttribute('aria-pressed',String(btn.dataset.mode===kind));
 $('tl-flight-controls').hidden=kind!=='flight';$('tl-train-controls').hidden=kind!=='train';$('tl-sub-controls').hidden=kind!=='sub';$('tl-flight-scene').hidden=kind!=='flight';$('tl-train-scene').hidden=kind!=='train';$('tl-sub-scene').hidden=kind!=='sub';$('tl-import-card').hidden=kind!=='flight';$('tl-map-card').hidden=kind==='train';reset();}
function sampleControls(){if(kind==='flight'){state.throttle=Number($('tl-throttle').value);state.bank=Number($('tl-bank').value);state.flightPath=Number($('tl-path').value);}else if(kind==='train'){state.throttle=Number($('tl-traction').value);state.brake=Number($('tl-brake').value);state.grade=Number($('tl-grade').value);}else{state.ballast=Number($('tl-ballast').value);state.speed=Number($('tl-sub-speed').value);state.heading=Number($('tl-sub-heading').value);state.waterDensity=Number($('hr-density')?.value||1025);}}
function advance(dt){if(observing){observing=false;selectedPoint=-1;}
 sampleControls();const fn=kind==='flight'?M.flightStep:kind==='train'?M.trainStep:M.subStep;let remaining=Math.min(Math.max(dt,0),15);
 while(remaining>1e-8){const next=Math.min(.25,remaining);state=fn(state,next);remaining-=next;
  if(kind!=='train'){pendingSeconds+=next;if(pendingSeconds>=1){path.push([state.lat,state.lon]);if(path.length>2000)path.shift();pendingSeconds-=1;}}
 }
 if(kind==='train'&&state.pos>=state.length)pause();refresh();}
function output(id,value){$(id).textContent=value;}
function row(label,value,warning=false){return `<div${warning?' class="warning"':''}><span>${label}</span><b>${value}</b></div>`;}
function physics(){if(kind==='flight'){const p=M.AIRCRAFT[state.profile],q=.5*state.density*state.speed**2,rot=state.turnRate;
 $('tl-physics').innerHTML=row('Air density (estimated)',fm(state.density,3)+' kg/m³')+row('Drag (modeled)',fm(state.drag/1000,1)+' kN')+row('Lift coefficient required',fm(state.liftCoefficient,2)) +row('Illustrative CL maximum',fm(p.clMax,2),state.stalled)+row('Turn rate',fm(rot,2)+' °/s')+row('Flight-path angle',fm(state.flightPath,1)+' °');
 $('tl-physics-note').textContent=state.stalled?'Model warning: required lift exceeds assumed CLmax. Stall dynamics are not simulated; continued motion is not physically validated.':'Quasi-steady point-mass model; density uses a simplified exponential atmosphere. Optional wind affects ground track, not the air-relative lift calculation. Weather, ground effect, control surfaces, and stall dynamics are not fully modeled.';
 }else if(kind==='train'){$('tl-physics').innerHTML=row('Distance traveled',fm(state.pos/1000,2)+' km')+row('Net acceleration',fm(state.accel||0,2)+' m/s²')+row('Ideal emergency stop',fm(state.brakingDistance||0,0)+' m')+row(railRoute?'Next mapped stop':'Next station marker',fm((state.nearestStop??2500)/1000,2)+' km')+row('Speed limit · generic',fm(state.limit*3.6,0)+' km/h');$('tl-physics-note').textContent='Ideal stopping distance uses profile maximum braking deceleration, from the current speed, with no reaction delay, adhesion variability or safety margin. Do not use for operations.';
 }else{$('tl-physics').innerHTML=row('Absolute pressure',fm(state.pressure/100000,2)+' bar')+row('Pressure above surface',fm((state.pressure-101325)/100000,2)+' bar')+row('Vertical rate',fm(state.verticalSpeed,2)+' m/s')+row('Ballast mass offset (effective)',fm((state.actualBallast??state.ballast)*50,0)+' kg')+row('Vertical acceleration',fm(state.accel,3)+' m/s²');$('tl-physics-note').textContent='Uses selected constant fluid density ('+fm(state.waterDensity||1025,0)+' kg/m³) and standard sea-level pressure. No measured local salinity, depth-dependent temperature, dynamic trim, hull model or bottom collision.';}}
function refresh(){const secs=Math.floor(state.time);output('tl-time',Math.floor(secs/60)+':'+String(secs%60).padStart(2,'0'));
 if(kind==='flight'){output('tl-speed',fm(state.speed*1.943844,0)+' kn TAS');output('tl-alt',fm(state.alt*3.28084,0)+' ft');output('tl-alt-label','Altitude · MSL model');output('tl-heading',fm(state.heading,0)+'°');$('tl-horizon').style.transform=`translateY(${state.flightPath*1.7}px) rotate(${-state.bank}deg)`;output('tl-mode-label',observing?'Imported · unverified':'Simulated · generic aircraft');}
 else if(kind==='train'){output('tl-speed',fm(state.speed*3.6,1)+' km/h');output('tl-alt',fm(state.pos/1000,2)+' km');output('tl-alt-label','Route position');output('tl-heading',fm(state.grade,1)+'% grade');$('tl-train-marker').style.left=(state.pos/state.length*100)+'%';output('tl-mode-label',railRoute?'Simulated on mapped geometry':'Simulated · straight track');}
 else{output('tl-speed',fm(state.speed,1)+' kn');output('tl-alt',fm(state.depth,1)+' m');output('tl-alt-label','Depth');output('tl-heading',fm(state.heading,0)+'°');$('tl-sub-marker').style.top=Math.max(5,Math.min(87,(state.depth/1000)*87))+'%';output('tl-mode-label','Simulated · buoyancy model');}
 for(const [input,out,suffix] of [['tl-throttle','tl-throttle-value','%'],['tl-bank','tl-bank-value','°'],['tl-path','tl-path-value','°'],['tl-traction','tl-traction-value','%'],['tl-brake','tl-brake-value','%'],['tl-grade','tl-grade-value','%'],['tl-ballast','tl-ballast-value','%'],['tl-sub-speed','tl-sub-speed-value',' kn'],['tl-sub-heading','tl-sub-heading-value','°']])output(out,$(input).value+suffix);
 $('tl-throttle').disabled=kind==='flight'&&state.profile==='glider';$('tl-play').disabled=observing;$('tl-step').disabled=observing;physics();updateGeo();root.transitLatest={mode:kind,state:{...state},observing};root.dispatchEvent(new CustomEvent('leh-transit-state',{detail:root.transitLatest}));}
function displayFact(){const [text,url]=facts[kind][factIndex%facts[kind].length];$('tl-fact').textContent=text;const s=$('tl-sources');s.replaceChildren();for(const [i,[,ref]] of facts[kind].entries()){const a=document.createElement('a');a.href=ref;a.target='_blank';a.rel='noopener noreferrer';a.textContent=['Reference '+(i+1)+': '+new URL(ref).hostname+' ↗'];s.append(a);}}
function getMapPoint(){if(kind==='train'&&root.dataset.routeLat)return {lat:Number(root.dataset.routeLat),lon:Number(root.dataset.routeLon)};return observing&&imported[selectedPoint]?imported[selectedPoint]:state;}
function updateGeo(){if(kind==='train')return;const p=getMapPoint();output('tl-coords',`Coordinates: ${fm(p.lat,5)}°, ${fm(p.lon,5)}° · ${observing?'imported position; provider unverified':'simulated position'}`);$('tl-geo-note').textContent=observing?'Positions originate in an uploaded CSV; values and provider have not been independently verified.':'Track is model output, not ADS-B, an actual flight, or a geographic terrain rendering.';
 const dot=$('tl-geo-dot');dot.style.left=(50+(p.lon-(kind==='flight'?-73.782:-74.55))*180)+'%';dot.style.top=(50-(p.lat-(kind==='flight'?40.644:36.14))*180)+'%';dot.textContent=kind==='flight'?'✈':'◉';
 if(map&&marker){marker.setLatLng([p.lat,p.lon]);const points=observing?imported.map(x=>[x.lat,x.lon]):path;trailLayer.setLatLngs(points);if(observing&&!importLayer){importLayer=window.L.polyline(imported.map(x=>[x.lat,x.lon]),{color:'#7a4ba3',weight:3,dashArray:'6 5'}).addTo(map);}else if(!observing&&importLayer){map.removeLayer(importLayer);importLayer=null;} if(running||observing)map.panTo([p.lat,p.lon],{animate:false});}}
function ensureStylesheet(url){return new Promise((resolve,reject)=>{const l=document.createElement('link');l.rel='stylesheet';l.href=url;l.onload=resolve;l.onerror=()=>reject(Error('Map stylesheet unavailable'));document.head.append(l);});}
function ensureScript(url){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=url;s.onload=resolve;s.onerror=()=>reject(Error('Map library unavailable'));document.head.append(s);});}
async function openMap(){if(map){map.invalidateSize();map.setView([getMapPoint().lat,getMapPoint().lon]);return;}const btn=$('tl-open-map');btn.disabled=true;btn.textContent='Loading map…';try{
 await Promise.all([ensureStylesheet('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'),ensureScript('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js')]);$('tl-geography').hidden=true;$('tl-live-map').hidden=false;
 const p=getMapPoint();map=window.L.map('tl-live-map',{scrollWheelZoom:false}).setView([p.lat,p.lon],11);
 window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:17,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>'}).addTo(map);
 marker=window.L.circleMarker([p.lat,p.lon],{radius:8,color:'#0a4640',weight:3,fillColor:'#f1ba66',fillOpacity:1}).addTo(map).bindPopup('Model location; not a real vehicle position.');trailLayer=window.L.polyline(path,{color:'#9b5324',weight:3}).addTo(map);root.dispatchEvent(new CustomEvent('leh-transit-map-ready',{detail:{map,marker,trailLayer}}));btn.textContent='Recenter map';btn.disabled=false;btn.onclick=()=>map.setView([getMapPoint().lat,getMapPoint().lon],11);updateGeo();setTimeout(()=>map.invalidateSize(),100);
 }catch(e){btn.disabled=false;btn.textContent='Retry real map';setStatus('Real map unavailable; schematic remains available. '+e.message);$('tl-geography').hidden=false;$('tl-live-map').hidden=true;}}
function trackSelection(){if(!imported.length)return;selectedPoint=Number($('tl-scrub').value);observing=true;pause();const p=imported[selectedPoint];output('tl-track-info',`${selectedPoint+1}/${imported.length} · ${p.time_iso} · ${fm(p.lat,5)}°, ${fm(p.lon,5)}° · ${fm(p.alt,0)} m`);setStatus('Viewing an imported position. Source and track authenticity have not been verified.');refresh();}
function ingestTrack(tracks,origin='CSV file (unverified)'){
 if(!Array.isArray(tracks)||!tracks.length||tracks.length>10000)throw Error('Track needs 1–10,000 valid positions.');
 imported=tracks;$('tl-track-tools').hidden=false;$('tl-scrub').max=String(tracks.length-1);$('tl-scrub').value='0';
 output('tl-record-count','1 / '+tracks.length);output('tl-import-status',tracks.length+' imported positions from '+origin+'. Origin and authenticity are unverified. Data stays in this browser.');
 setMode('flight');trackSelection();root.dispatchEvent(new CustomEvent('leh-transit-track-loaded',{detail:{points:tracks,origin}}));
}
$('tl-csv').addEventListener('change',async e=>{const file=e.target.files?.[0];if(!file)return;try{if(file.size>3e6)throw Error('Maximum CSV size is 3 MB.');ingestTrack(M.parseTrackCsv(await file.text()),'local CSV');}catch(err){output('tl-import-status','Import failed: '+err.message);}});
root.dataset.dataLabNativeImport='ready';
root.addEventListener('leh-transit-import',event=>{try{
 const detail=event.detail||{};if(typeof TransitDataAdapters==='undefined')throw Error('Integration adapter unavailable.');
 const points=M.parseTrackCsv(TransitDataAdapters.toFlightCSV(detail.points));
 ingestTrack(points,'OpenSky-format JSON (not authenticated)');
 }catch(err){output('tl-import-status','Integration failed: '+err.message);}
});
$('tl-scrub').addEventListener('input',()=>{output('tl-record-count',(Number($('tl-scrub').value)+1)+' / '+imported.length);trackSelection();});
$('tl-take').addEventListener('click',()=>{if(!imported.length||selectedPoint<0)return;pause();const p=imported[selectedPoint],base=M.flightInit($('tl-plane').value);state={...base,lat:p.lat,lon:p.lon,alt:p.alt,speed:base.speed,heading:p.heading===null?base.heading:p.heading};path=[[state.lat,state.lon]];observing=false;selectedPoint=-1;setStatus('New hypothetical trajectory from an imported point. The generic airspeed is used; imported groundspeed is not assumed to be true airspeed. Subsequent positions are simulated.');refresh();});
$('tl-clear-track').addEventListener('click',()=>{imported=[];observing=false;selectedPoint=-1;$('tl-track-tools').hidden=true;$('tl-csv').value='';output('tl-import-status','No track imported.');if(importLayer&&map){map.removeLayer(importLayer);importLayer=null;}refresh();});
root.addEventListener('leh-transit-route-selected',e=>{
 const r=e.detail?.route;
 if(!r||!Array.isArray(r.points)||r.points.length<2||!Number.isFinite(r.lengthM)||r.lengthM<100||r.lengthM>2000000)return;
 railRoute=r;
 if(kind==='train'){reset();setStatus('Route '+r.name+' loaded: '+(r.lengthM/1000).toFixed(2)+' km of mapped geometry and '+(r.stations?.length||0)+' matched stations. Model physics remain hypothetical.');}
});
root.addEventListener('leh-transit-route-cleared',()=>{railRoute=null;delete root.dataset.routeLat;delete root.dataset.routeLon;if(kind==='train'){reset();setStatus('Generic 10 km railway restored.');}});
root.querySelectorAll('[data-mode]').forEach(btn=>btn.addEventListener('click',()=>setMode(btn.dataset.mode)));
$('tl-play').addEventListener('click',()=>running?pause():start());$('tl-step').addEventListener('click',()=>{pause();advance(1);setStatus('Advanced the simulation one second.');});$('tl-reset').addEventListener('click',reset);$('tl-open-map').addEventListener('click',openMap);
$('tl-next-fact').addEventListener('click',()=>{factIndex++;displayFact();});
$('tl-plane').addEventListener('change',reset);$('tl-train-profile').addEventListener('change',reset);
for(const id of ['tl-throttle','tl-bank','tl-path','tl-traction','tl-brake','tl-grade','tl-ballast','tl-sub-speed','tl-sub-heading'])$(id).addEventListener('input',()=>{sampleControls();refresh();});
const prevSetMode=setMode;for(const btn of root.querySelectorAll('[data-mode]'))btn.addEventListener('click',()=>{factIndex=0;displayFact();});displayFact();setMode('flight');})();
