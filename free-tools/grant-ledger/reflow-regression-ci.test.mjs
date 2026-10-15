import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('./styles.css',import.meta.url),'utf8');
assert.match(css,/overflow-wrap:anywhere/);
assert.match(css,/overflow-x:auto/);
console.log('2 responsive-layout contract assertions PASS');
