(function visualsLab(){
"use strict";
const root=document.getElementById("leh-transit");
if(!root||typeof TransitModels==="undefined"||root.dataset.visualsV2==="ready")return;
root.dataset.visualsV2="ready";
const M=TransitModels,$=id=>document.getElementById(id);
const SVG="http://www.w3.org/2000/svg";
const safe=(v,a=-1e9,b=1e9)=>Math.max(a,Math.min(b,Number.isFinite(Number(v))?Number(v):0));
const fmt=(v,d=0)=>safe(v).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const windKts=()=>safe($("tl-wind")?.value,0,150);
const css=document.createElement("style");
css.textContent=`
#leh-transit{--tv-night:#091f2b;--tv-mint:#a7f5d8;--tv-aqua:#4de3c0;--tv-amber:#f6cd86}
#leh-transit .lab-hero{background:linear-gradient(120deg,#0a3435 0%,#12463d 53%,#18384a 100%);border-bottom:3px solid #c9a366}
#leh-transit .tabs{gap:.45rem;padding:.55rem 1rem;background:#dfece7}
#leh-transit .tabs button{border:1px solid transparent;border-radius:9px;padding:.65rem 1rem;line-height:1.35;flex:1 1 120px}
#leh-transit .tabs button[aria-pressed=true]{border-color:#6e9b88;box-shadow:0 2px 0 #245a48;background:#fff}
#leh-transit .panel{box-shadow:0 3px 14px #112d2710}
#leh-transit .readouts>div{background:#f0f7f2;border:1px solid #d7e6dd;padding:.72rem .65rem}
#leh-transit .readouts strong{font-size:clamp(1.03rem,2.1vw,1.25rem)}
#leh-transit .scene.tv-upgraded{background:var(--tv-night);border:1px solid #255567;height:auto;min-height:220px;aspect-ratio:16 / 9;max-height:none;overflow:hidden}
#leh-transit .scene.tv-upgraded>:not(.tv-stage){display:none!important}
#leh-transit .tv-stage{width:100%;height:100%;position:absolute;inset:0;overflow:hidden}
#leh-transit .tv-stage svg{display:block;width:100%;height:100%;color:#f6fff9}
#leh-transit .tv-stage svg text{font-family:system-ui,-apple-system,Segoe UI,sans-serif;pointer-events:none}
#leh-transit .tv-stage .tv-monospace{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.035em}
#leh-transit .tv-stage .tv-soft{fill:#b6d6d4}
#leh-transit .tv-stage .tv-tiny{font-size:16px;letter-spacing:1.2px}
#leh-transit .tv-stage .tv-label{font-size:20px;font-weight:700}
#leh-transit .tv-stage .tv-digit{font-size:41px;font-weight:800;letter-spacing:1px}
#leh-transit .tv-stage .tv-copy{font-size:19px;font-weight:650}
#leh-transit .tv-quick{display:flex;flex-wrap:wrap;align-items:center;gap:.48rem;margin:.15rem 0 .8rem}
#leh-transit .tv-quick .tv-quick-label{font-size:.76rem;text-transform:uppercase;letter-spacing:.09em;font-weight:800;color:#506b5d;margin-right:.15rem}
#leh-transit .tv-quick button{min-height:38px;padding:.43rem .75rem;border:1px solid #b2d2c3;background:#edf7f1;color:#214b3a;font-weight:700}
#leh-transit .tv-quick button:hover{background:#dceee3}
#leh-transit .tv-detail{border:1px solid var(--border);border-radius:9px;margin-top:.55rem;padding:.52rem .75rem;background:#f4faf6;font-size:.85rem}
#leh-transit .tv-detail summary{cursor:pointer;font-weight:800;color:#205841}
#leh-transit .tv-detail p{margin:.55rem 0 .3rem!important;font-size:.85rem;line-height:1.55}
#leh-transit .tv-summary{color:#385c50;font-size:.83rem;line-height:1.45;margin:.45rem 0}
#leh-transit #tl-physics{font-size:.91rem}
#leh-transit input[type=range]{min-height:30px;touch-action:pan-y}
#leh-transit .control{padding:.18rem 0}
#leh-transit .scene.tv-upgraded:focus-visible{outline:3px solid #2474b1;outline-offset:3px}
@media(max-width:750px){#leh-transit .body-grid{grid-template-columns:1fr}#leh-transit .scene.tv-upgraded{aspect-ratio:5 / 3;min-height:235px}#leh-transit .tabs{position:sticky;top:0;z-index:6}#leh-transit .tv-quick button{flex:1 1 auto}}
@media(max-width:480px){#leh-transit .scene.tv-upgraded{aspect-ratio:4 / 3;min-height:245px}#leh-transit .readouts{grid-template-columns:repeat(2,minmax(0,1fr))}#leh-transit .tv-quick .tv-quick-label{flex:1 1 100%}#leh-transit .tabs button{font-size:.82rem;padding:.58rem .35rem;flex:1 1 29%;min-width:0}}
@media(prefers-reduced-motion:reduce){#leh-transit .tv-stage *,#leh-transit .tv-stage *::before,#leh-transit .tv-stage *::after{animation:none!important;transition:none!important}}
`;
document.head.append(css);
const flight=`
<svg viewBox="0 0 960 540" preserveAspectRatio="xMidYMid meet" role="presentation" aria-hidden="true">
<defs>
<linearGradient id="tvf-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#144b80"/><stop offset="1" stop-color="#62bdd3"/></linearGradient>
<linearGradient id="tvf-ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a98e68"/><stop offset="1" stop-color="#3e6656"/></linearGradient>
<clipPath id="tvf-round"><rect x="262" y="69" width="436" height="380" rx="21"/></clipPath>
</defs>
<rect width="960" height="540" fill="#061820"/>
<rect x="16" y="16" width="928" height="507" rx="20" fill="#092b37" stroke="#265c65" stroke-width="2"/>
<rect x="34" y="32" width="892" height="34" rx="8" fill="#102f39"/>
<circle cx="52" cy="49" r="5" fill="#5fddae"/><text x="66" y="56" class="tv-tiny" fill="#dbf6ef">FLIGHT LAB · INSTRUMENT VIEW</text>
<text id="tvf-state" x="914" y="55" fill="#f6cd86" text-anchor="end" class="tv-tiny">GENERIC · SIMULATED</text>
<g clip-path="url(#tvf-round)">
<rect x="262" y="69" width="436" height="380" fill="#163e54"/>
<g id="tvf-horizon" transform="rotate(0 480 259)">
<rect x="-200" y="-700" width="1400" height="960" fill="url(#tvf-sky)"/>
<rect x="-200" y="259" width="1400" height="1250" fill="url(#tvf-ground)"/>
<path d="M-160 259H1150" stroke="#fff" stroke-width="4"/>
<g stroke="#f1f7ed" stroke-width="2" opacity=".8" fill="none">
<path d="M410 169h140M430 199h100M410 229h140M430 289h100M410 319h140M430 349h100"/>
</g>
<g fill="#fff" font-size="16" font-family="system-ui"><text x="390" y="175">15</text><text x="398" y="235">5</text><text x="398" y="324">5</text><text x="390" y="353">15</text></g>
</g>
</g>
<rect x="262" y="69" width="436" height="380" rx="21" fill="none" stroke="#74b4bc" stroke-width="2"/>
<g stroke="#ffffff" stroke-width="5" fill="none" stroke-linecap="round">
<path d="M420 260h43l17 11 17-11h43"/>
<path d="M472 271v14m16-14v14"/>
</g>
<path d="M480 76l-10 15h20z" fill="#f5ce7e"/>
<path d="M343 149q137-103 274 0" fill="none" stroke="#a4cbd0" stroke-width="2" stroke-dasharray="8 10"/>
<g id="tvf-bank-pointer"><path d="M480 120l-9 15h18z" fill="#f4ce80"/></g>
<rect x="35" y="86" width="206" height="314" rx="14" fill="#081e2a" stroke="#467c86"/>
<text x="55" y="116" class="tv-tiny tv-soft">TRUE AIRSPEED · kn</text>
<text id="tvf-speed" x="138" y="221" fill="#ecfff7" class="tv-digit tv-monospace" text-anchor="middle">000</text>
<path d="M68 245h137" stroke="#649aa5" stroke-width="2"/>
<text id="tvf-gs" x="138" y="279" class="tv-copy" fill="#9df2db" text-anchor="middle">GS — kn</text>
<text x="138" y="317" class="tv-tiny tv-soft" text-anchor="middle">GROUND SPEED</text>
<text x="138" y="361" class="tv-tiny" fill="#f1cf94" text-anchor="middle">WIND / TRACK</text>
<rect x="719" y="86" width="207" height="314" rx="14" fill="#081e2a" stroke="#467c86"/>
<text x="739" y="116" class="tv-tiny tv-soft">ALTITUDE · ft MSL*</text>
<text id="tvf-alt" x="822" y="221" fill="#ecfff7" class="tv-digit tv-monospace" text-anchor="middle">0</text>
<path d="M749 245h148" stroke="#649aa5" stroke-width="2"/>
<text id="tvf-vs" x="822" y="281" fill="#9df2db" class="tv-copy" text-anchor="middle">VS —</text>
<text x="822" y="318" class="tv-tiny tv-soft" text-anchor="middle">FT PER MINUTE</text>
<text x="822" y="361" class="tv-tiny" fill="#f1cf94" text-anchor="middle">FPA PROXY</text>
<rect x="255" y="462" width="450" height="43" rx="9" fill="#061b24" stroke="#4c8590"/>
<text x="280" y="490" class="tv-copy" fill="#a4e7ce">HDG</text>
<text id="tvf-heading" x="387" y="490" class="tv-copy tv-monospace" fill="#fff">045°</text>
<text x="500" y="490" class="tv-copy" fill="#a4e7ce">TRACK</text>
<text id="tvf-track" x="617" y="490" class="tv-copy tv-monospace" fill="#fff">045°</text>
<text id="tvf-bank" x="43" y="450" class="tv-tiny" fill="#f7da9f">BANK 0°</text>
<text id="tvf-fpa" x="916" y="450" text-anchor="end" class="tv-tiny" fill="#f7da9f">PATH 0°</text>
<text x="480" y="523" text-anchor="middle" font-size="13" fill="#a4bbc3">*INDICATIVE MODEL VALUES · FLIGHT PATH IS NOT BODY PITCH · NO REAL CAMERA VIEW</text>
</svg>`;
const train=`
<svg viewBox="0 0 960 540" preserveAspectRatio="xMidYMid meet" role="presentation" aria-hidden="true">
<defs>
<linearGradient id="tvr-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4d93a6"/><stop offset=".95" stop-color="#d8e8db"/></linearGradient>
<linearGradient id="tvr-ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#596c64"/><stop offset="1" stop-color="#1b3034"/></linearGradient>
<clipPath id="tvr-glass"><rect x="18" y="70" width="924" height="383" rx="12"/></clipPath>
</defs>
<rect width="960" height="540" fill="#071e27"/>
<rect x="14" y="14" width="932" height="510" rx="20" fill="#092a33" stroke="#3e7775" stroke-width="2"/>
<g clip-path="url(#tvr-glass)">
<rect x="18" y="70" width="924" height="383" fill="url(#tvr-sky)"/>
<path d="M0 258L78 203L130 242L220 170L330 250L400 218L516 257L600 190L709 252L785 205L960 257V500H0Z" fill="#789d92" opacity=".65"/>
<path d="M0 292L140 246L330 274L480 261L670 274L850 245L960 289V540H0Z" fill="url(#tvr-ground)"/>
<g fill="#425d60" opacity=".85"><rect x="100" y="220" width="38" height="63"/><rect x="150" y="208" width="51" height="72"/><rect x="800" y="224" width="61" height="79"/><rect x="865" y="217" width="34" height="95"/></g>
<path d="M479 257L170 525M481 257L795 525" fill="none" stroke="#e1e8db" stroke-width="14"/>
<path d="M479 257L170 525M481 257L795 525" fill="none" stroke="#273941" stroke-width="6"/>
<path d="M479 257L288 525M481 257L675 525" fill="none" stroke="#9db7ac" stroke-width="3" stroke-dasharray="18 18"/>
<g id="tvr-ties" stroke="#aa9474" stroke-width="8" stroke-linecap="round">
<path d="M456 286h48"/><path d="M440 314h80"/><path d="M414 352h132"/><path d="M376 399h208"/><path d="M310 455h340"/><path d="M244 505h472"/>
</g>
<path d="M479 258V122" stroke="#607e78" stroke-width="5"/>
<path d="M240 173h480l-27-24H265z" fill="none" stroke="#496d68" stroke-width="7"/>
<path d="M145 72L297 220M815 72L663 220" stroke="#d7e9e0" stroke-width="7" opacity=".5"/>
</g>
<rect x="18" y="70" width="924" height="383" rx="12" fill="none" stroke="#598b8b" stroke-width="2"/>
<rect x="36" y="30" width="452" height="52" rx="10" fill="#092a34" opacity=".96" stroke="#396e74"/>
<text x="51" y="62" class="tv-tiny" fill="#d2f7e5">RAIL LAB · CAB VIEW · HYPOTHETICAL 10 km</text>
<rect x="672" y="90" width="252" height="116" rx="15" fill="#061c27" stroke="#83ada9" stroke-width="2"/>
<text x="697" y="121" class="tv-tiny tv-soft">TRAIN SPEED</text>
<text id="tvr-speed" x="798" y="175" class="tv-digit tv-monospace" text-anchor="middle" fill="#f4fff6">0</text>
<text x="901" y="174" class="tv-tiny" text-anchor="end" fill="#b4ddcf">km/h</text>
<rect x="36" y="94" width="305" height="126" rx="15" fill="#071f2a" opacity=".96" stroke="#83ada9" stroke-width="2"/>
<text x="55" y="128" class="tv-tiny tv-soft">DISTANCE TO SELECTED STATION</text>
<text id="tvr-remaining" x="55" y="175" class="tv-digit tv-monospace" fill="#f4fff6">2500</text>
<text x="263" y="170" class="tv-tiny" fill="#b4ddcf">m</text>
<rect x="0" y="452" width="960" height="88" fill="#061b24"/>
<text id="tvr-grade" x="44" y="491" class="tv-copy" fill="#c0dfd3">GRADE 0%</text>
<text id="tvr-brake" x="44" y="524" class="tv-tiny" fill="#edcb88">BRAKE COMMAND 0%</text>
<text id="tvr-cue" x="916" y="488" text-anchor="end" class="tv-copy" fill="#a9f3ce">APPROACH</text>
<text id="tvr-stop" x="916" y="520" text-anchor="end" class="tv-tiny" fill="#c4dfd7">IDEAL STOP — m</text>
<rect x="365" y="504" width="224" height="12" rx="6" fill="#203f45"/>
<rect id="tvr-progress" x="365" y="504" width="0" height="12" rx="6" fill="#4de3c0"/>
</svg>`;
const sub=`
<svg viewBox="0 0 960 540" preserveAspectRatio="xMidYMid meet" role="presentation" aria-hidden="true">
<defs>
<linearGradient id="tvs-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#205f83"/><stop offset=".45" stop-color="#0e4261"/><stop offset="1" stop-color="#061d36"/></linearGradient>
<linearGradient id="tvs-hull" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f8e9ad"/><stop offset=".5" stop-color="#c6b46f"/><stop offset="1" stop-color="#827e55"/></linearGradient>
</defs>
<rect width="960" height="540" fill="#031720"/>
<rect x="14" y="14" width="932" height="510" rx="20" fill="#092c41" stroke="#2d7084" stroke-width="2"/>
<rect x="32" y="76" width="896" height="395" rx="12" fill="url(#tvs-sea)"/>
<g stroke="#8ecfe0" stroke-opacity=".19"><path d="M32 175H928M32 271H928M32 366H928M32 464H928" stroke-dasharray="7 11"/></g>
<path d="M32 76h896" stroke="#9ce5e7" stroke-width="5"/>
<g fill="#99d5df" opacity=".35"><circle cx="563" cy="115" r="6"/><circle cx="596" cy="170" r="4"/><circle cx="692" cy="330" r="3"/><circle cx="534" cy="420" r="5"/><circle cx="655" cy="240" r="3"/></g>
<rect x="32" y="76" width="134" height="395" fill="#061e30" fill-opacity=".6"/>
<g class="tv-monospace" fill="#d5eeee" font-size="19"><text x="52" y="106">0 m</text><text id="tvs-tick1" x="52" y="202">50 m</text><text id="tvs-tick2" x="52" y="298">100 m</text><text id="tvs-tick3" x="52" y="393">150 m</text><text id="tvs-tick4" x="52" y="460">200 m</text></g>
<path d="M166 77v393" stroke="#b0dce2" stroke-width="2"/>
<g id="tvs-target-line">
<path d="M167 242h530" stroke="#f5c97d" stroke-dasharray="11 10" stroke-width="3"/>
<rect x="577" y="222" width="114" height="35" rx="7" fill="#634d2e" stroke="#e9bc69"/>
<text id="tvs-target" x="634" y="245" text-anchor="middle" font-size="18" fill="#fff0cd">75m TARGET</text>
</g>
<g id="tvs-boat" transform="translate(0 0)">
<path d="M326 257h254a41 34 0 0 1 0 68H326a41 34 0 0 1 0-68z" fill="url(#tvs-hull)" stroke="#f0e4b2" stroke-width="3"/>
<path d="M417 257v-27h45v27" fill="#cab776" stroke="#e5d699" stroke-width="3"/>
<path d="M377 291h161" stroke="#7b744f" stroke-width="5"/>
<circle cx="530" cy="289" r="10" fill="#4e7278" stroke="#d4d7a4" stroke-width="3"/>
<path d="M318 266l-29-19v89l29-19z" fill="#ad9560"/>
</g>
<rect x="36" y="28" width="480" height="47" rx="10" fill="#082636" stroke="#458294"/>
<text x="57" y="58" class="tv-tiny" fill="#d5f5f4">SUBMARINE LAB · SCHEMATIC WATER COLUMN</text>
<rect x="710" y="96" width="201" height="112" rx="13" fill="#071d2b" stroke="#6eb6bf" stroke-width="2"/>
<text x="729" y="125" class="tv-tiny tv-soft">DEPTH · m</text>
<text id="tvs-depth" x="810" y="176" text-anchor="middle" class="tv-digit tv-monospace" fill="#f7fff7">50.0</text>
<rect x="710" y="230" width="201" height="105" rx="13" fill="#071d2b" stroke="#6eb6bf" stroke-width="2"/>
<text x="729" y="259" class="tv-tiny tv-soft">ABS PRESSURE · bar</text>
<text id="tvs-pressure" x="810" y="310" text-anchor="middle" class="tv-digit tv-monospace" fill="#f7fff7">6.0</text>
<rect x="32" y="472" width="896" height="58" fill="#051c2a"/>
<text id="tvs-rate" x="54" y="508" class="tv-copy" fill="#c5e7df">VERTICAL RATE 0.00 m/s</text>
<text id="tvs-ballast" x="905" y="508" text-anchor="end" class="tv-copy" fill="#f3d49c">BALLAST TRIM 0%</text>
<text id="tvs-scale" x="702" y="66" class="tv-tiny" fill="#b6e2e0">VIEW 0–200 m</text>
<text x="480" y="537" text-anchor="middle" font-size="13" fill="#accbd1">NO BATHYMETRY · NO SEAFLOOR COLLISION MODEL · NOT A VESSEL SAFETY GAUGE</text>
</svg>`;
function install(id,markup){
  const scene=$(id);if(!scene)return;
  const stage=document.createElement("div");stage.className="tv-stage";stage.innerHTML=markup;
  scene.appendChild(stage);scene.classList.add("tv-upgraded");scene.setAttribute("tabindex","0");
}
install("tl-flight-scene",flight);
install("tl-train-scene",train);
install("tl-sub-scene",sub);
const modelNote=document.createElement("p");modelNote.className="tv-summary";modelNote.id="tv-view-summary";
modelNote.textContent="Calculated displays are based on a generic model, not real vehicle sensors.";
const primary=$("tl-flight-scene")?.parentNode;
const readouts=primary?.querySelector(".readouts");
if(primary&&readouts)primary.insertBefore(modelNote,readouts);
const quick=document.createElement("div");quick.className="tv-quick";quick.setAttribute("role","group");quick.setAttribute("aria-label","Quick simulation controls");
if(primary&&readouts)primary.insertBefore(quick,readouts);
const details=document.createElement("details");details.className="tv-detail";
details.innerHTML='<summary>How to interpret this view</summary><p id="tv-view-explainer">All illustrations are drawn from hypothetical model state.</p>';
primary?.appendChild(details);
const quickGroups={
flight:[["Level bank","tl-bank",0],["Level flight path","tl-path",0],["Thrust 70%","tl-throttle",70]],
train:[["Coast","tl-traction",0],["Service brake 70%","tl-brake",70],["Full model brake","tl-brake",100]],
sub:[["Neutral trim","tl-ballast",0],["Light dive trim","tl-ballast",20],["Light rise trim","tl-ballast",-20]]
};
function quickButtons(kind){
 quick.replaceChildren();const name=document.createElement("span");name.className="tv-quick-label";name.textContent="Quick commands";quick.append(name);
 for(const [label,id,value] of quickGroups[kind]){
  const button=document.createElement("button");button.type="button";button.textContent=label;
  button.addEventListener("click",()=>{const el=$(id);if(!el||el.disabled)return;el.value=String(value);el.dispatchEvent(new Event("input",{bubbles:true}));});quick.append(button);
 }
}
const modeTitle={flight:"Flight instrument view",train:"Rail cab schematic",sub:"Submarine depth display"};
const explainer={
flight:"This resembles the organization of a primary flight display: airspeed, altitude, bank, and heading. The central horizon follows the model’s flight-path angle as a visual proxy; flight-path angle is not body pitch. Grounds­peed includes an optional steady-wind estimate. It is not a camera, terrain view, or approved PFD.",
train:"The view represents a hypothetical straight track from a forward cab perspective. The speed, station separation, grade and ideal stopping-distance cue come from the current simplified model. No actual rail alignment, signaling, dispatch rules, adhesion variation or gradient profile is supplied.",
sub:"This is a conceptual depth cross-section, not a sonar image. Boat position, hydrostatic pressure, ballast trim and vertical motion are computed from a highly simplified buoyancy model. The depth scale rescales for clarity and is labeled; there is no measured bathymetry or safe operating depth."
};
const updateText=(id,txt)=>{const e=$(id);if(e)e.textContent=txt;};
const setTransform=(id,t)=>{const e=$(id);if(e)e.setAttribute("transform",t);};
function renderFlight(s,observing){
 const hd=safe(s.heading,0,360),bank=safe(s.bank,-45,45),path=safe(s.flightPath,-12,12);
 const knots=safe(s.speed,0,360)*1.943844,gs=safe(s.groundSpeed??s.speed,0,500)*1.943844;
 const vs=safe(s.speed,0,500)*Math.sin(path*Math.PI/180)*196.8503937*60;
 const track=safe(s.trackDeg??s.heading,0,360);
 setTransform("tvf-horizon",`rotate(${-bank.toFixed(2)} 480 259) translate(0 ${Math.round(path*5)})`);
 updateText("tvf-speed",fmt(knots,0));updateText("tvf-gs","GS "+fmt(gs,0)+" kn");
 updateText("tvf-alt",fmt(s.alt*3.28084,0));updateText("tvf-vs",fmt(vs,0)+" fpm");
 updateText("tvf-heading",fmt(hd,0)+"°");updateText("tvf-track",fmt(track,0)+"°");
 updateText("tvf-bank","BANK "+fmt(bank,1)+"°");updateText("tvf-fpa","PATH "+fmt(path,1)+"°");
 const state=observing?"CSV SELECTED · VIEW NOT RECORDED":s.stalled?"LIFT WARNING · MODEL LIMIT":"GENERIC · SIMULATED";
 updateText("tvf-state",state);
 $("tl-flight-scene")?.setAttribute("aria-label",`Generic flight model: airspeed ${fmt(knots,0)} knots, altitude ${fmt(s.alt*3.28084,0)} feet, ground track ${fmt(track,0)} degrees, bank ${fmt(bank,1)} degrees. This is not a cockpit camera or measured attitude.`);
}
function renderTrain(s){
 const target=Number($("tl-mission-station")?.value)||s.nearestStop||2500,d=target-s.pos,profile=M.TRAINS[s.profile],decel=profile.brake+.03+9.80665*s.grade/100;
 const ideal=decel>0?s.speed*s.speed/(2*decel):Infinity;
 const due=ideal+Math.max(2,s.speed*.15)>=d;
 updateText("tvr-speed",fmt(s.speed*3.6,1));
 updateText("tvr-remaining",fmt(d,0));
 updateText("tvr-grade","GRADE "+fmt(s.grade,1)+"%");
 updateText("tvr-brake","BRAKE COMMAND "+fmt(s.brake,0)+"%");
 updateText("tvr-stop","IDEAL STOP "+(Number.isFinite(ideal)?fmt(ideal,0):"n/a")+" m");
 updateText("tvr-cue",s.speed<.3?"STOPPED":d<0?"MARKER PASSED":due?"BRAKE CUE":"APPROACH");
 $("tvr-cue")?.setAttribute("fill",due&&s.speed>.3?"#f5be77":"#a9f3ce");
 const pct=safe(s.pos/Math.max(1,target)*220,0,220);
 $("tvr-progress")?.setAttribute("width",pct.toFixed(1));
 setTransform("tvr-ties",`translate(0 ${Math.round(s.pos%20)*.65})`);
 $("tl-train-scene")?.setAttribute("aria-label",`Generic rail cab schematic: speed ${fmt(s.speed*3.6,1)} kilometers per hour, ${fmt(d,0)} meters to selected stop, full-model braking distance ${Number.isFinite(ideal)?fmt(ideal,0):"undefined"} meters.`);
}
function renderSub(s){
 const target=safe(Number($("tl-mission-depth")?.value)||75,0,1000),depth=safe(s.depth,0,1000);
 const max= Math.min(1000,Math.max(200,Math.ceil(Math.max(target,depth)*1.18/200)*200));
 const y=v=>76+safe(v/max,0,1)*385;
 setTransform("tvs-boat",`translate(0 ${(y(depth)-289).toFixed(1)})`);
 setTransform("tvs-target-line",`translate(0 ${(y(target)-242).toFixed(1)})`);
 for(let i=1;i<=4;i++)updateText("tvs-tick"+i,fmt(max*i/4,0)+" m");
 updateText("tvs-scale","VIEW 0–"+fmt(max,0)+" m");
 updateText("tvs-target",fmt(target,0)+"m TARGET");
 updateText("tvs-depth",fmt(depth,1));updateText("tvs-pressure",fmt(s.pressure/1e5,1));
 updateText("tvs-rate","VERTICAL RATE "+fmt(s.verticalSpeed,2)+" m/s");
 updateText("tvs-ballast","TRIM "+fmt(s.actualBallast??s.ballast,1)+"%");
 $("tl-sub-scene")?.setAttribute("aria-label",`Submarine buoyancy schematic: depth ${fmt(depth,1)} meters, pressure ${fmt(s.pressure/1e5,1)} bar absolute, vertical speed ${fmt(s.verticalSpeed,2)} meters per second. No mapped seafloor.`);
}
let mode="flight",lastDescription=-1;
function update(e){
 const data=e.detail;if(!data?.state)return;
 const next=data.mode;
 if(next!==mode){mode=next;quickButtons(mode);updateText("tv-view-explainer",explainer[mode]);updateText("tl-view-title",modeTitle[mode]);}
 if(mode==="flight")renderFlight(data.state,data.observing);
 else if(mode==="train")renderTrain(data.state);
 else renderSub(data.state);
 const state=data.state,t=state.time||0;
 if(Math.floor(t/3)!==lastDescription||data.observing){
 lastDescription=Math.floor(t/3);
 const label=mode==="flight"
  ?data.observing?"Imported CSV selected. This conceptual cockpit shows model values, not observed orientation or a recreated view.":`Generic aircraft. Heading ${fmt(state.heading,0)}°, groundspeed ${fmt((state.groundSpeed??state.speed)*1.943844,0)} kn; no satellite terrain or live flight feed.`
  :mode==="train"?`Illustrative track position ${fmt(state.pos/1000,2)} km, speed ${fmt(state.speed*3.6,1)} km/h; no real route or signals.`
  :`Schematic depth ${fmt(state.depth,1)} m, ${fmt(state.pressure/1e5,1)} bar absolute; no mapped seafloor.`;
 updateText("tv-view-summary",label);
 }
}
root.addEventListener("leh-transit-state",update);
quickButtons(mode);updateText("tv-view-explainer",explainer[mode]);updateText("tl-view-title",modeTitle[mode]);
const initial=M.flightInit($("tl-plane")?.value||"trainer");
renderFlight(initial,false);
})();
