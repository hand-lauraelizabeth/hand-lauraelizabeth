/* Browser-like integration smoke test for instrument and procedural scene synchrony.
   Run: node projects/transit-lab/visual-sync-v6-tests.js */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const M=require('./models.js');
const F=require('./historical-fleet-v5.js');
const H=require('./historical-profiles.js');
const drawn={flight:[],train:[],sub:[]};
class Element {
 constructor(id=''){this.id=id;this.dataset={};this.listeners={};this.children=[];this.attributes={};
  this.textContent='';this.value='';this.hidden=false;this.style={};
  this.classList={add(){},toggle(){}};this.parentNode=null;this.parentElement=null;this.className='';}
 addEventListener(type,fn){(this.listeners[type]||(this.listeners[type]=[])).push(fn);}
 dispatchEvent(e){for(const fn of this.listeners[e.type]||[])fn(e);}
 append(child){this.appendChild(child);}
 appendChild(child){this.children.push(child);if(this.kind)child.kind=this.kind;}
 insertBefore(child){this.appendChild(child);}
 replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attributes[k]=String(v);}
 querySelector(s){if(s==='.tv-stage')return this.children.find(e=>e.className==='tv-stage')||null;return null;}
 getContext(){
  const events=drawn[this.kind]||drawn.flight,ctx={};
  for(const k of ['save','restore','beginPath','closePath','roundRect','fill','stroke','moveTo','lineTo',
   'quadraticCurveTo','bezierCurveTo','arc','ellipse','clearRect','translate','rotate'])ctx[k]=()=>{};
  ctx.fillRect=()=>{};ctx.fillText=value=>events.push(String(value));
  ctx.createLinearGradient=()=>({addColorStop(){}});
  return ctx;
 }
}
const nodes=new Map();
function get(id){if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);}
const root=get('leh-transit');
get('tl-plane').value='trainer';get('tl-train-profile').value='metro';
get('hr-sub-vehicle').value='generic';get('tl-mission-station').value='500';get('tl-mission-depth').value='75';
const parent=new Element('parent');
for(const kind of ['flight','train','sub']){
 const scene=get('tl-'+kind+'-scene');scene.kind=kind;scene.parentNode=parent;scene.parentElement=parent;
}
root.transitLatest={mode:'flight',state:M.flightInit()};
const document={getElementById:get,createElement:tag=>new Element(tag),head:new Element('head')};
const scope={document,TransitModels:M,TransitFleetV5:F,TransitHistorical:H,
 requestAnimationFrame:cb=>cb(),console:{error(error){throw error;}}};
for(const file of ['visuals.js','scene-v3.js']){
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,file),'utf8'),scope,{filename:file});
}
assert.equal(root.dataset.visualsV2,'ready');
assert.equal(root.dataset.sceneV3,'ready');
get('cv-outside').dispatchEvent({type:'click'});
M.AIRCRAFT.spirit={...F.flights.spirit.model};
M.TRAINS.mallard={...F.trains.mallard.model};
const flight=M.flightStep({...M.flightInit('spirit'),bank:20,flightPath:4},1);
root.transitLatest={mode:'flight',state:flight};
root.dispatchEvent({type:'leh-transit-state',detail:{mode:'flight',state:flight,observing:false}});
assert.ok(get('tvf-state').textContent.includes('Ryan NYP'));
assert.ok(get('tvf-bank').textContent.includes('20'));
assert.ok(drawn.flight.some(x=>x.includes('Ryan NYP')));
assert.ok(drawn.flight.some(x=>x.includes('VS ')));
const route={lengthM:2000,serviceName:'Illustrative route',points:[{lat:40,lon:-74},{lat:40,lon:-73.98}],
 stations:[{name:'Scheduled platform',distanceM:1000,structure:'Underground'}]};
const train={...M.trainInit('mallard'),pos:950,speed:5,brakingDistance:30,limit:F.trains.mallard.model.limit};
root.dispatchEvent({type:'leh-transit-route-selected',detail:{route}});
root.transitLatest={mode:'train',state:train};
root.dispatchEvent({type:'leh-transit-state',detail:{mode:'train',state:train}});
root.dispatchEvent({type:'leh-transit-dispatch-update',detail:{run:{phase:'approach'},station:{name:'Scheduled platform',distance:1000}}});
assert.equal(get('tvr-remaining').textContent,'50');
assert.ok(get('tvr-title').textContent.includes('MALLARD'));
assert.ok(get('tv-view-summary').textContent.includes('Mallard'));
assert.ok(drawn.train.some(x=>x.includes('STREAMLINED STEAM-LOCO')));
assert.ok(drawn.train.some(x=>x.includes('Scheduled platform')));
const sub={...M.subInit(),depth:210,verticalSpeed:.3,pressure:M.oceanPressure(210),
 hullSpeedKnots:2,requestedSpeedKnots:4,vesselProfile:'holland'};
get('hr-sub-vehicle').value='holland';root.dataset.fleetSub='holland';
root.transitLatest={mode:'sub',state:sub};
root.dispatchEvent({type:'leh-transit-state',detail:{mode:'sub',state:sub}});
const holland=get('tvs-hull-outline').attributes.d;
assert.ok(get('tvs-vessel').textContent.includes('HOLLAND'));
assert.ok(drawn.sub.some(x=>x.includes('DESCENDING')));
assert.ok(drawn.sub.some(x=>x.includes('Command 4.00 kn')));
get('hr-sub-vehicle').value='albacore';root.dataset.fleetSub='albacore';
root.dispatchEvent({type:'leh-transit-fleet-change',detail:{mode:'sub',profile:'albacore'}});
assert.ok(get('tvs-vessel').textContent.includes('ALBACORE'));
assert.notEqual(get('tvs-hull-outline').attributes.d,holland);
root.transitLatest={mode:'flight',state:flight};
root.dispatchEvent({type:'leh-transit-state',detail:{mode:'flight',state:flight,observing:true}});
assert.ok(drawn.flight.some(x=>x.includes('NO EXTERNAL CAMERA RECORDING')));
console.log('Visual V6 integration: historical names, station dispatch, model-driven scene and imported-track boundaries passed.');
