const assert=require('node:assert/strict'),E=require('./engine.js');
const cases=[
 [['e2e4','e7e5','d1h5','b8c6','f1c4','g8f6'],'h5f7'],
 [['f2f3','e7e5','g2g4'],'d8h4'],
 [['e2e4','a7a6','e4e5','d7d5'],'e5d6'],
 [['e2e4','e7e5','g1f3','b8c6','f1c4','g8f6'],'e1g1']
];
for(const [line,answer] of cases){
 let s=E.fromFen(E.START);
 for(const id of line){const m=E.makeMove(s,id);assert.ok(m,`Illegal lesson move: ${id}`);s=E.apply(s,m);}
 const next=E.makeMove(s,answer);assert.ok(next,`Illegal answer: ${answer}`);
 assert.notEqual(E.toFen(E.apply(s,next)),E.toFen(s));
}
const fork=E.fromFen('r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1');
const move=E.makeMove(fork,'d5c7');assert.ok(move);assert.match(E.san(fork,move),/Nc7\+/);
console.log('All five chess exercises are legal and the fork gives check.');
