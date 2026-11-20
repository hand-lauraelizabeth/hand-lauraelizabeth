const assert=require('node:assert/strict');
const F=require('./historical-fleet-v5.js');
const M=require('./models.js');
const H=require('./historical-profiles.js');

assert.equal(Object.keys(F.flights).length,2);
assert.equal(Object.keys(F.trains).length,3);
assert.equal(Object.keys(F.subs).length,2);
for(const [kind,entries] of Object.entries(F.fleet)){
 for(const [id,v] of Object.entries(entries)){
  assert.equal(F.entry(kind,id),v);
  assert.ok(v.source.startsWith('https://'));
  assert.ok(v.label.length>10);
  assert.ok(v.facts.length>=2);
  assert.ok(/illustrative|classroom|modeled|generic|not a|teaching|not published/.test(v.assumptions));
  assert.ok(F.silhouette(kind,id).includes('<svg'));
  assert.ok(F.silhouette(kind,id).includes('viewBox='));
 }
}
assert.equal(F.entry('flight','unknown'),null);
assert.equal(F.entry('train','r1').model.limit,40*.44704);
assert.equal(F.railCeiling('r32'),50*.44704);
assert.equal(F.railCeiling('none'),null);
assert.equal(F.entry('train','mallard').model.limit,75*.44704);
assert.ok(F.entry('train','mallard').facts[1].includes('126 mph'));
assert.ok(F.entry('flight','fordtrimotor').model.maxSpeed<60);
assert.ok(F.entry('flight','spirit').model.mass>2000);
for(const id of ['fordtrimotor','spirit']){
 const p=F.flights[id].model;M.AIRCRAFT[id]={...p};
 const init=M.flightInit(id),next=M.flightStep(init,.5);
 assert.equal(next.profile,id);assert.ok(next.time>.4);
 assert.ok(Number.isFinite(next.drag)&&next.drag>=0);
 assert.ok(next.speed>5&&next.speed<=p.maxSpeed);
 assert.ok(init.speed>0&&init.speed<=p.maxSpeed);
}
for(const id of Object.keys(F.trains)){
 M.TRAINS[id]={...F.trains[id].model};
 const start=M.trainInit(id),step=M.trainStep({...start,throttle:100},1);
 assert.equal(step.profile,id);
 assert.ok(step.speed>0&&step.speed<=M.TRAINS[id].limit);
 assert.ok(step.pos>0&&step.accel>0);
}
assert.equal(F.nextSubSpeed(undefined,20,1,'holland'),2.12);
assert.ok(Math.abs(F.nextSubSpeed(2,5,1,'holland')-2.12)<1e-8);
assert.ok(Math.abs(F.nextSubSpeed(3,20,1,'albacore')-3.32)<1e-8);
assert.ok(Math.abs(F.nextSubSpeed(3,0,1,'albacore')-2.68)<1e-8);
assert.ok(F.nextSubSpeed(4.99,20,2,'holland')<=5);
assert.ok(F.nextSubSpeed(0,30,2,'albacore')<=20);
assert.equal(F.nextSubSpeed(3,2,0,'holland'),3);
assert.equal(F.nextSubSpeed(3,10,1,'generic'),10);
const originalSub=M.subStep(M.subInit(),1);
assert.ok(originalSub.depth>=0&&Number.isFinite(originalSub.pressure));
let drawn=0;const fakeCtx={save(){},restore(){},beginPath(){},roundRect(){},fill(){},stroke(){},fillText(){},moveTo(){},quadraticCurveTo(){},bezierCurveTo(){},lineTo(){},fillRect(){},};
assert.equal(F.drawBadge(fakeCtx,'flight','fordtrimotor'),true);
assert.equal(F.drawBadge(fakeCtx,'train','mallard'),true);
assert.equal(F.drawBadge(fakeCtx,'train','unknown'),false);
assert.equal(F.drawHull(fakeCtx,'holland'),true);
assert.equal(F.drawHull(fakeCtx,'albacore'),true);
assert.equal(F.drawHull(fakeCtx,'nautilus'),false);
console.log('Historical Fleet V5: 94+ profile, source, visualization and physics assertions passed.');
