// Synthetic-only regression: JSON import must reject ambiguous provenance identifiers.
import assert from 'node:assert/strict';
import {parseWorkspaceJSON} from './import.mjs';
const valid={version:1,requests:[{id:'R-001',jurisdiction:'federal',agency:'Example Agency',stage:'draft',submittedOn:'',agencyTrackingId:'00009',description:'Synthetic request'}],events:[]};
const source=JSON.stringify(valid);
assert.equal(parseWorkspaceJSON(source).requests[0].agencyTrackingId,'00009');
const ambiguous=source.replace('"id":"R-001"','"id":"SHADOW","\\u0069d":"R-001"');
assert.throws(()=>parseWorkspaceJSON(ambiguous),/Duplicate JSON object key/);
console.log('PASS: strict JSON import rejects escaped duplicate provenance key');
