const assert=require('node:assert/strict');const m=require('./models.js');
function near(a,b,tol=1e-6){assert.ok(Math.abs(a-b)<=tol,`${a} differs from ${b}`);}
near(m.brakingDistance(20,1),200);near(m.oceanPressure(0),101325);near(m.oceanPressure(100),101325+1025*m.G*100);
const a=m.flightInit();near(a.speed,55);const straight=m.flightStep({...a,bank:0,flightPath:0,throttle:0},1);near(straight.heading,a.heading);near(straight.alt,a.alt);assert.ok(straight.speed<a.speed);assert.ok(straight.lat>a.lat&&straight.lon>a.lon);
const banked=m.flightStep({...a,bank:20,throttle:60},1);assert.ok(banked.heading>a.heading);assert.ok(banked.turnRate>0);
const climbed=m.flightStep({...a,flightPath:6},1);assert.ok(climbed.alt>a.alt);assert.ok(climbed.speed<a.speed || climbed.speed>a.speed); // finite
const tr=m.trainInit(),tr2=m.trainStep({...tr,throttle:100},10);assert.ok(tr2.speed>0&&tr2.pos>0);const tr3=m.trainStep({...tr2,throttle:0,brake:100},10);assert.ok(tr3.speed<tr2.speed);
const end=m.trainStep({...m.trainInit(),pos:9999,speed:20,throttle:0,brake:0},1);
assert.equal(end.pos,end.length);assert.equal(end.speed,0);assert.equal(end.terminalOverrun,true,'end-of-track clamp must not count as a successful stop');
const sub=m.subInit(),sub2=m.subStep({...sub,ballast:100},4);assert.ok(sub2.depth>sub.depth);const sub3=m.subStep({...sub,ballast:-100},4);assert.ok(sub3.depth<sub.depth);
const pts=m.parseTrackCsv('time_iso,latitude,longitude,altitude_m,groundspeed_mps,heading_deg\n2026-11-19T12:00:00Z,40.5,-73.7,1500,50,90\n2026-11-19T12:01:00Z,40.6,-73.6,1600,52,91');assert.equal(pts.length,2);
assert.throws(()=>m.parseTrackCsv('time_iso,latitude,longitude,altitude_m\n2026-11-19T12:00:00Z,91,-73.7,1500'));
console.log('Transit model tests passed: SI pressure, braking distance, acceleration, turn kinematics, altitude, buoyancy and track validation.');
