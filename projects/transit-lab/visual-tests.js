/* node projects/transit-lab/visual-tests.js */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const model=require('./models.js');
const scripts=fs.readFileSync(path.join(__dirname,'visuals.js'),'utf8');
const map=new Map(),listeners=new Map();
let uid=0;
function node(id){
  return {id,dataset:{},style:{},value:'',innerHTML:'',textContent:'',children:[],attrs:{},events:{},
    classList:{add(n){this.added=n}},
    append(...items){for(const item of items){this.children.push(item);item.parentNode=this}},
    appendChild(item){this.append(item);return item},
    insertBefore(item){this.append(item)},
    replaceChildren(){this.children=[]},
    setAttribute(k,v){this.attrs[k]=String(v)},
    addEventListener(event,fn){(this.events[event]??=[]).push(fn)},
    dispatchEvent(event){for(const fn of this.events[event.type]??[])fn(event)},
    querySelector(selector){return selector==='.readouts'?get('readouts'):null}
  };
}
function get(id){if(!map.has(id))map.set(id,node(id));return map.get(id);}
const panel=get('viewport-panel'),root=get('leh-transit');
for(const scene of ['tl-flight-scene','tl-train-scene','tl-sub-scene'])get(scene).parentNode=panel;
root.dataset={};root.addEventListener=(event,fn)=>listeners.set(event,fn);
const document={getElementById:get,createElement:tag=>node(tag+'-'+ ++uid),head:{append(){}}};
get('tl-mission-station').value='2500';get('tl-mission-depth').value='150';get('tl-plane').value='trainer';
const context={document,TransitModels:model,Number,Math,console,Event:class Event{constructor(type){this.type=type;this.bubbles=true}}};
vm.runInNewContext(scripts,context,{filename:'visuals.js'});
const update=listeners.get('leh-transit-state');
assert.equal(typeof update,'function');
assert.equal(root.dataset.visualsV2,'ready');
const stages=['tl-flight-scene','tl-train-scene','tl-sub-scene'].map(id=>get(id).children[0]);
for(const stage of stages){
  assert.match(stage.innerHTML,/<svg\b/);
  assert.match(stage.innerHTML,/<\/svg>/);
  assert.equal(stage.children.length,1,'each stage includes a mobile metric strip');
  assert.equal(stage.children[0].children.length,4,'four readable mobile measurements');
}
let state=model.flightStep(model.flightInit(),1);
update({detail:{mode:'flight',state,observing:false}});
assert.equal(get('tvmf-2').textContent,'45°');
assert.match(get('tvf-vs').textContent,/0 fpm/);
assert.match(get('tv-view-summary').textContent,/no satellite terrain/);
update({detail:{mode:'flight',state:{...state,flightPath:6,speed:60},observing:false}});
assert.ok(parseFloat(get('tvf-vs').textContent.replace(/,/g,''))>600,'vertical speed must be feet per minute, not feet per hour');
update({detail:{mode:'flight',state,observing:true}});
assert.match(get('tvf-state').textContent,/CSV SELECTED/);
state=model.trainStep({...model.trainInit(),throttle:90},1);
update({detail:{mode:'train',state,observing:false}});
assert.match(get('tvmr-0').textContent,/km\/h/);
assert.match(get('tvr-stop').textContent,/IDEAL STOP/);
state=model.subStep({...model.subInit(),ballast:40},1);
update({detail:{mode:'sub',state,observing:false}});
assert.match(get('tvms-1').textContent,/bar/);
assert.match(get('tvs-scale').textContent,/VIEW 0/);
assert.match(get('tl-view-title').textContent,/Submarine/);
assert.match(scripts,/prefers-reduced-motion/);
assert.match(scripts,/max-width:600px/);
assert.match(scripts,/FLIGHT PATH IS NOT BODY PITCH/);
console.log('Visual layer tests passed: three SVG views, four mobile metrics per mode, model-state updates, observation boundaries, accessibility labels and units.');
