'use strict';
const assert=require('node:assert/strict');
const reader=require('../file-reader.js');
const core=require('../rescue-core.js');
let checks=0;
const yes=(x,name)=>{assert.ok(x,name);checks++;};
const eq=(a,b,name)=>{assert.deepEqual(a,b,name);checks++;};
const rejects=async(fn,message)=>{await assert.rejects(fn,message);checks++;};
const file=(name,bytes,reportedSize)=>({
 name,size:reportedSize===undefined?bytes.length:reportedSize,
 arrayBuffer:async()=>Uint8Array.from(bytes).buffer
});
(async()=>{
 const valid=file('details.CSV',Buffer.from('ID,Name\n1,Jos\u00e9'));
 eq((await reader.read(valid,core.parseDelimited)).rows[0][1],'Jos\u00e9','valid UTF-8 preserved');
 eq(reader.extension('example.TsV'),'tsv','case-insensitive TSV extension');
 eq((await reader.read(file('example.tsv',Buffer.from('id\tvalue\n1\tdata')),core.parseDelimited)).rows[0][1],'data','TSV parsed correctly');
 eq((await reader.read(file('bom.csv',Buffer.from([0xef,0xbb,0xbf,...Buffer.from('ID\n1')])),core.parseDelimited)).headers[0],'ID','UTF-8 BOM accepted');
 await rejects(()=>reader.read(file('bad.csv.exe',Buffer.from('ID\n1')),core.parseDelimited),/\.csv or \.tsv/);
 await rejects(()=>reader.read(file('bad.csv',Buffer.from([0xc3,0x28])),core.parseDelimited),/Invalid UTF-8/);
 await rejects(()=>reader.read(file('utf16.csv',Buffer.from([0xff,0xfe,0x49,0,0x44,0])),core.parseDelimited),/Invalid UTF-8/);
 await rejects(()=>reader.read(file('binary.csv',Buffer.from([0x49,0x44,0,0x31])),core.parseDelimited),/NUL characters/);
 await rejects(()=>reader.read(file('bad.csv',Buffer.from('id,value\n1,2,3')),core.parseDelimited),/No data was discarded/);
 await rejects(()=>reader.read(file('bad.csv',Buffer.from('id,value\n"unclosed,2')),core.parseDelimited),/Unclosed quoted field/);
 let reads=0;
 const oversized={name:'x.csv',size:reader.maxBytes+1,arrayBuffer:async()=>{reads++;return new ArrayBuffer(0)}};
 await rejects(()=>reader.read(oversized,core.parseDelimited),/larger than 5 MB/);
 eq(reads,0,'oversize rejected before reading bytes');
 const mismatch={name:'mismatch.csv',size:3,arrayBuffer:async()=>new Uint8Array(reader.maxBytes+1).buffer};
 await rejects(()=>reader.read(mismatch,core.parseDelimited),/larger than 5 MB/);
 const exact=Buffer.from('ID\n'+'x'.repeat(reader.maxBytes-3));
 eq(exact.length,reader.maxBytes,'exact 5 MB fixture length');
 const boundary=await reader.read(file('edge.csv',exact),core.parseDelimited);
 eq(boundary.rows[0][0].length,reader.maxBytes-3,'exact 5 MB accepted');
 await rejects(()=>reader.read(file('too-big.csv',Buffer.from('x'),reader.maxBytes+1),core.parseDelimited),/larger than 5 MB/);
 eq(reader.requireFile({name:'safe.csv',size:0,arrayBuffer:async()=>new ArrayBuffer(0)}),'csv','zero-byte metadata passes to parser, parser rejects empty file');
 await rejects(()=>reader.read(file('empty.csv',Buffer.alloc(0)),core.parseDelimited),/no data/i);
 yes(reader.maxBytes===core.MAX_BYTES,'byte limits consistent with parser');
 eq(reader.decode(Buffer.from('a,b\n1,2')),'a,b\n1,2','manual decoder works');
 yes(!reader.decode(Buffer.from('NAME\n=2+2')).includes('\uFFFD'),'valid formula-like text not corrupt');
 console.log('PASS: '+checks+' strict local UTF-8 and byte-size assertions.');
})().catch(e=>{console.error(e);process.exitCode=1;});
