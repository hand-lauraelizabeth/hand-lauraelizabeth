import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const html=readFileSync(new URL('./index.html',import.meta.url),'utf8');
const match=html.match(/<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i);
assert.ok(match,'CSP meta must precede executable resources');
const policy=match[1];
let checks=1;
for(const directive of ["default-src 'none'","script-src 'self'","style-src 'self'","connect-src 'none'","img-src 'none'","object-src 'none'","base-uri 'none'","form-action 'none'"]){assert.ok(policy.split(';').map(s=>s.trim()).includes(directive),directive);checks++;}
assert.ok(!policy.includes('unsafe-inline')&&!policy.includes('unsafe-eval'));checks++;
assert.ok(html.indexOf('Content-Security-Policy')<html.indexOf('<script'));checks++;
assert.match(html,/<script type="module" src="app\.mjs"><\/script>/);checks++;
assert.match(html,/<link rel="stylesheet" href="styles\.css">/);checks++;
console.log(`${checks} grant ledger CSP contract assertions PASS`);
