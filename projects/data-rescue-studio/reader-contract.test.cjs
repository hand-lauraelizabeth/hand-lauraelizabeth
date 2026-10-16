'use strict';
const assert=require('node:assert/strict');
const reader=require('./file-reader.js');
assert.equal(reader.maxBytes,5000000);
console.log('PASS reader size contract');
