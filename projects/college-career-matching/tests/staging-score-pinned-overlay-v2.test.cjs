'use strict';
const assert=require('node:assert/strict');
const overlay=require('../data/sprint3/college-search-scores.v3.json');
assert.equal(overlay.school_count,6243);
assert.equal(Object.keys(overlay.institutions).length,1247);
assert.equal(overlay.institutions['105330'],undefined);
assert.equal(overlay.institutions['197294'],undefined);
assert.ok(overlay.institutions['208822']);
