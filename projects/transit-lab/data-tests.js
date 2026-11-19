const assert=require('node:assert/strict');
const D=require('./data-adapters.js'),M=require('./models.js');
const state=(t,lat=40.7,lon=-73.9,icao='abc123')=>[icao,'LEARN01','US',t,t,lon,lat,900,false,82,45,0,null,930,null];
const one=D.parseOpenSky({time:1700000100,states:[state(1700000100)]});
assert.equal(one.aircraft.length,1);
assert.equal(one.aircraft[0].icao24,'abc123');
assert.equal(one.aircraft[0].points[0].alt,930);
const multi=D.parseOpenSky([
 {time:1700000100,states:[state(1700000100),state(1700000100),['bad']]},
 {time:1700000200,states:[state(1700000200,40.71,-73.89)]}
]);
assert.equal(multi.aircraft[0].samples,2,'Duplicate timestamps coalesce');
assert.ok(multi.stats.skipped>0);
const normalized=D.toFlightCSV(multi.aircraft[0].points),converted=M.parseTrackCsv(normalized);
assert.equal(converted.length,2);
assert.equal(converted[0].lat,40.7);
assert.equal(converted[1].heading,45);
assert.throws(()=>D.parseOpenSky({time:1700000100,states:[['bad']]}));
assert.throws(()=>D.parseOpenSky({time:1700000100,states:'not an array'}));
const gtfs='shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n' +
 'R,40.700,-73.900,20\nR,40.710,-73.890,30\nQ,40.760,-73.980,10\nQ,40.761,-73.979,11';
const routes=D.parseGTFSShapes(gtfs);
assert.equal(routes.length,2);assert.ok(routes[0].lengthM>100);
assert.throws(()=>D.parseGTFSShapes('shape_id,shape_pt_lat,shape_pt_lon\n'));
const gj=D.parseGeoJSON({type:'FeatureCollection',features:[{type:'Feature',properties:{name:'Test line'},geometry:{type:'LineString',coordinates:[[-73.9,40.7],[-73.89,40.71]]}}]});
assert.equal(gj[0].name,'Test line');
assert.ok(Math.abs(gj[0].lengthM-routes[0].lengthM)<1);
assert.throws(()=>D.parseGeoJSON({type:'Point',coordinates:[1,2]}));
assert.throws(()=>D.parseGeoJSON({type:'LineString',coordinates:[[200,0],[201,1]]}));
const projected=D.projection(gj[0].points);
assert.equal(projected.length,2);
assert.ok(projected.every(p=>p.x>0&&p.x<640&&p.y>0&&p.y<240));
console.log('Data adapters passed: OpenSky snapshots, timestamps, normalization, GTFS geometry, GeoJSON bounds and route projection.');
