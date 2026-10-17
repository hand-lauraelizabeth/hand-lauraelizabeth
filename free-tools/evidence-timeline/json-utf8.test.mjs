import assert from 'node:assert/strict';
import {readExactJSON} from './json-import.mjs';
const bad=Uint8Array.from([195,40]);
const file={name:'synthetic.json',size:bad.length,arrayBuffer:async()=>bad.buffer};
await assert.rejects(()=>readExactJSON(file),/UTF-8/);
console.log('PASS: invalid UTF-8 rejected');
