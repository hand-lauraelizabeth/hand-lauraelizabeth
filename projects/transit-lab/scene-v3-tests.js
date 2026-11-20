const assert=require('node:assert/strict'),C=require('./scene-v3.js');
assert.equal(C.clamp(-2,0,1),0);
assert.equal(C.clamp(4,0,1),1);
assert.equal(C.curvature(null,100),0);
assert.equal(C.curvature({lengthM:1000,points:[]},100),0);
assert.equal(C.seabed(null,{lat:0,lon:0}),null);
console.log('Scene math and missing-data fallback tests passed.');
