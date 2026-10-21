import assert from 'node:assert/strict';
import {readExactJSON,SCHEMA} from './json-import.mjs';
const json=JSON.stringify({schema:SCHEMA,records:[]});
const b=new TextEncoder().encode(json);
const f={name:'synthetic.json',size:b.length,arrayBuffer:async()=>b.buffer};
assert.deepEqual(await readExactJSON(f),[]);
console.log('PASS: JSON file decode');
