const assert=require('node:assert/strict'),E=require('./engine.js');
const start=E.fromFen(E.START);assert.equal(start.t,1);
const white=E.choose(start,1);assert.ok(white,'Computer can make a first move for White');
const post=E.apply(start,white);assert.equal(post.t,-1);
assert.ok(E.legal(post).length>0,'Human Black has legal replies');
const black=E.legal(post)[0],after=E.apply(post,black);assert.equal(after.t,1);
const whiteAgain=E.choose(after,1);assert.ok(whiteAgain,'Computer can reply as White');
assert.equal(E.fromFen(E.toFen(post)).t,-1,'FEN round trip preserves turn');
console.log('Computer White / human Black move sequence passed.');
