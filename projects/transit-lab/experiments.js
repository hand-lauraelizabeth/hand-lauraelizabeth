(function experimentLab(){
"use strict";
const Calc={
 error:(target,heading)=>((target-heading+540)%360+360)%360-180,
 clamp:(x,a,b)=>Math.max(a,Math.min(b,x)),
 brake:(v,d,a,g)=>{const decel=a+.03+9.80665*g/100;const stop=decel>0?v*v/(2*decel):Infinity;return {stop,act:d<=stop+Math.max(2,v*.15)};}
};
Calc.bank=(target,heading)=>Calc.clamp(Calc.error(target,heading)*.35,-18,18);
Calc.ballast=(target,depth,rate)=>Calc.clamp((target-depth)*8-rate*150,-100,100);
Calc.train=(s,target,profile)=>{const d=target-s.pos;if(d<=15&&s.speed<=.35)return {throttle:0,brake:100,note:"Holding near platform"};return Calc.brake(s.speed,d,profile.brake,s.grade).act?{throttle:0,brake:100,note:"Braking"}:{throttle:d<350?35:65,brake:0,note:"Accelerating"};};
if(typeof module!=="undefined"&&module.exports!==undefined)module.exports=Calc;
if(typeof document==="undefined"||typeof TransitModels==="undefined")return;
const root=document.getElementById("leh-transit"),M=TransitModels,$=id=>document.getElementById(id);if(!root)return;
const css=document.createElement("style");
css.textContent="#leh-transit .ex-lab{display:grid;gap:.8rem}#leh-transit .ex-lab select,#leh-transit .ex-lab input[type=number]{display:block;width:100%;box-sizing:border-box;padding:.5rem;background:white;color:var(--ink);border:1px solid #90a99a;border-radius:8px}#leh-transit .ex-lab .ex-row{display:flex;gap:.5rem;flex-wrap:wrap}#leh-transit .ex-lab .ex-assist{background:var(--pale);border:1px solid var(--border);padding:.75rem;border-radius:10px}#leh-transit .ex-lab .ex-assist label{display:flex;align-items:center;gap:.5rem}#leh-transit .ex-lab svg{width:100%;height:auto;display:block;background:#f5f8f5;border:1px solid var(--border);border-radius:8px}#leh-transit .ex-lab .ex-note{font-size:.85rem;line-height:1.5;color:var(--muted)}";
document.head.append(css);
const panel=document.createElement("section");panel.className="panel ex-lab";
panel.innerHTML='<h2>Experiment studio</h2><p class="ex-note">Load a scenario, inspect the model’s response, and export simulated—not observed—measurements.</p><label for="ex-scenario">Starting scenario<select id="ex-scenario"></select></label><div class="ex-row"><button type="button" id="ex-load">Load scenario</button><button type="button" id="ex-export" class="secondary">Export CSV</button></div><p id="ex-status" class="ex-note" role="status">Choose a scenario or operate the existing controls.</p><div class="ex-assist"><label for="ex-assist"><input id="ex-assist" type="checkbox"><strong id="ex-assist-label">Illustrative heading assist</strong></label><label id="ex-heading-wrap" for="ex-heading">Target heading, ° true<input id="ex-heading" type="number" min="0" max="359" value="135"></label><p id="ex-assist-status" class="ex-note" role="status">Assistant off.</p><p class="ex-note">Simplified feedback only; not autopilot, signaling, or vessel control. Manual input disengages the assistant.</p></div><label for="ex-metric">Telemetry signal<select id="ex-metric"></select></label><svg id="ex-graph" viewBox="0 0 440 165" role="img" aria-label="Simulated telemetry graph"></svg><p id="ex-summary" class="ex-note" role="status"></p>';
const aside=root.querySelector(".side-stack");aside.insertBefore(panel,aside.children[1]||null);
const presets={
 flight:[["wind","Trainer · 35 kn crosswind",{plane:"trainer",throttle:65,wind:35,windTo:90,path:0,heading:45,assist:false}],["steer","Trainer · turn to 135°",{plane:"trainer",throttle:65,wind:15,windTo:180,path:0,heading:135,assist:true}],["glide","Glider · power-off descent",{plane:"glider",throttle:0,wind:12,windTo:270,path:-3,heading:45,assist:false}]],
 train:[["metro","Metro · assisted 2.5 km stop",{profile:"metro",station:2500,grade:0,assist:true}],["downhill","Metro · downhill approach",{profile:"metro",station:2500,grade:-2,assist:true}],["regional","Regional · 5.5 km stop",{profile:"regional",station:5500,grade:0,assist:true}]],
 sub:[["neutral","Neutral trim · manual",{target:75,assist:false}],["dive","Depth assistant · 100 m",{target:100,assist:true}],["deeper","Depth assistant · 150 m",{target:150,assist:true}]]
};
const keys={flight:[["tas","True airspeed (kn)"],["gs","Groundspeed (kn)"],["alt","Altitude (ft)"]],train:[["speed","Speed (km/h)"],["position","Distance (km)"],["remaining","Distance to station (m)"]],sub:[["depth","Depth (m)"],["vertical","Vertical speed (m/s)"],["pressure","Absolute pressure (bar)"]]};
let mode="flight",records=[],last=-1;const fmt=x=>Number(x).toFixed(1);
function options(id,items){$(id).replaceChildren();for(const [value,label] of items){const o=document.createElement("option");o.value=value;o.textContent=label;$(id).append(o);}}
function graph(){
const k=$("ex-metric").value,r=records.slice(-240),svg=$("ex-graph");if(!r.length){svg.innerHTML='<text x="20" y="85" font-size="13" fill="#476154">Press Start or Advance 1 s.</text>';$("ex-summary").textContent="No simulated readings recorded.";return;}
const v=r.map(x=>x[k]),min=Math.min(...v),max=Math.max(...v),d=Math.max(.1,(max-min)*.15,Math.abs(max)*.02),lo=min-d,hi=max+d,t0=r[0].time,t1=r.at(-1).time;
const pts=r.map(s=>`${(26+(t1===t0?.5:(s.time-t0)/(t1-t0))*390).toFixed(2)},${(12+(hi-s[k])/(hi-lo)*127).toFixed(2)}`).join(" ");
svg.innerHTML=`<line x1="26" y1="139" x2="416" y2="139" stroke="#9cb9a4"/><polyline points="${pts}" fill="none" stroke="#246a52" stroke-width="2.5"/><text x="28" y="11" font-size="11">${fmt(hi)}</text><text x="28" y="156" font-size="11">${fmt(lo)}</text><text x="416" y="156" text-anchor="end" font-size="11">${fmt(t1)} s</text>`;
svg.setAttribute("aria-label",`${k}: ${fmt(min)} to ${fmt(max)}, ending at ${fmt(v.at(-1))}, simulated.`);$("ex-summary").textContent=`${records.length} samples · ${k}: ${fmt(v.at(-1))}, range ${fmt(min)}–${fmt(max)}. Model output, not observation.`;}
function configure(k){mode=k;records=[];last=-1;options("ex-scenario",presets[k]);options("ex-metric",keys[k]);$("ex-assist").checked=false;$("ex-heading-wrap").hidden=k!=="flight";$("ex-assist-label").textContent=k==="flight"?"Heading-control assistant":k==="train"?"Assisted station stop":"Depth-control assistant";$("ex-assist-status").textContent="Assistant off.";graph();}
const prior={flight:M.flightStep,train:M.trainStep,sub:M.subStep};
M.flightStep=(s,dt)=>{if(mode!=="flight"||!$("ex-assist").checked)return prior.flight(s,dt);const target=Number($("ex-heading").value),bank=Calc.bank(target,s.heading);$("tl-bank").value=String(Math.round(bank));$("ex-assist-status").textContent=`Bank ${fmt(bank)}° · error ${fmt(Calc.error(target,s.heading))}°`;return prior.flight({...s,bank},dt);};
M.trainStep=(s,dt)=>{if(mode!=="train"||!$("ex-assist").checked)return prior.train(s,dt);const target=Number($("tl-mission-station").value)||2500,c=Calc.train(s,target,M.TRAINS[s.profile]);$("tl-traction").value=String(c.throttle);$("tl-brake").value=String(c.brake);$("ex-assist-status").textContent=`${c.note} · ${fmt(Math.max(0,target-s.pos))} m away.`;return prior.train({...s,throttle:c.throttle,brake:c.brake},dt);};
M.subStep=(s,dt)=>{if(mode!=="sub"||!$("ex-assist").checked)return prior.sub(s,dt);const target=Number($("tl-mission-depth").value)||75,ballast=Calc.ballast(target,s.depth,s.verticalSpeed);$("tl-ballast").value=String(Math.round(ballast));$("ex-assist-status").textContent=`Trim ${fmt(ballast)}% toward ${fmt(target)} m.`;return prior.sub({...s,ballast},dt);};
for(const id of ["tl-bank","tl-traction","tl-brake","tl-ballast"])$(id).addEventListener("input",()=>{if($("ex-assist").checked){$("ex-assist").checked=false;$("ex-assist-status").textContent="Disengaged by manual input."; }});
$("ex-assist").addEventListener("change",()=>{$("ex-assist-status").textContent=$("ex-assist").checked?"Illustrative assistant enabled.":"Manual controls active.";});
$("ex-metric").addEventListener("change",graph);
function input(id,value){$(id).value=String(value);$(id).dispatchEvent(new Event("input",{bubbles:true}));}
$("ex-load").addEventListener("click",()=>{const preset=presets[mode].find(x=>x[0]===$("ex-scenario").value);if(!preset)return;const x=preset[2];$("ex-assist").checked=false;
if(mode==="flight")$("tl-plane").value=x.plane;if(mode==="train")$("tl-train-profile").value=x.profile;$("tl-reset").click();
if(mode==="flight"){for(const [id,v] of Object.entries({"tl-throttle":x.throttle,"tl-bank":0,"tl-path":x.path,"tl-wind":x.wind,"tl-wind-direction":x.windTo}))input(id,v);$("ex-heading").value=String(x.heading);}
else if(mode==="train"){input("tl-grade",x.grade);input("tl-traction",65);input("tl-brake",0);$("tl-mission-station").value=String(x.station);$("tl-mission-station").dispatchEvent(new Event("change"));}
else{input("tl-ballast",0);$("tl-mission-depth").value=String(x.target);$("tl-mission-depth").dispatchEvent(new Event("change"));}
records=[];last=-1;$("ex-assist").checked=x.assist;$("ex-assist-status").textContent=x.assist?"Illustrative assistant enabled.":"Manual control.";$("ex-status").textContent=preset[1]+" loaded. Press Start or Advance 1 s.";graph();});
root.addEventListener("leh-transit-state",e=>{const o=e.detail;if(!o?.state)return;if(o.mode!==mode)configure(o.mode);const s=o.state;if(s.time<last||s.time===0&&last>0){records=[];last=-1;graph();}if(o.observing||s.time<last+.95)return;
const data=o.mode==="flight"?{tas:s.speed*1.943844,gs:(s.groundSpeed??s.speed)*1.943844,alt:s.alt*3.28084,heading:s.heading,track:s.trackDeg??s.heading,lat:s.lat,lon:s.lon}:o.mode==="train"?{speed:s.speed*3.6,position:s.pos/1000,remaining:(Number($("tl-mission-station").value)||2500)-s.pos,brake:s.brake,grade:s.grade}:{depth:s.depth,vertical:s.verticalSpeed,pressure:s.pressure/1e5,ballast:s.actualBallast??s.ballast};
records.push({time:s.time,...data});if(records.length>2400)records.shift();last=s.time;graph();});
$("ex-export").addEventListener("click",()=>{if(!records.length){$("ex-status").textContent="Advance the model before exporting.";return;}const columns=Object.keys(records[0]),csv=[columns.join(","),...records.map(row=>columns.map(k=>row[k]).join(","))].join("\r\n");const url=URL.createObjectURL(new Blob([csv],{type:"text/csv"})),a=document.createElement("a");a.href=url;a.download="simulated-"+mode+"-telemetry.csv";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);$("ex-status").textContent="Exported "+records.length+" local simulated readings.";});
root.querySelectorAll("[data-mode]").forEach(b=>b.addEventListener("click",()=>{if(b.dataset.mode!==mode)configure(b.dataset.mode);}));
configure(root.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode||"flight");
})();