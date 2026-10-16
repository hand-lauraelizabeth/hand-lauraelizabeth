'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
for(const name of ['index.html','history-preview.html']){
 const html=fs.readFileSync(__dirname+'/'+name,'utf8');
 assert.match(html,/aria-describedby="(?:status|loadStatus)"/);
}
