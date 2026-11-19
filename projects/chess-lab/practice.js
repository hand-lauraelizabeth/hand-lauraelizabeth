/* Chess Lab: five playable, rule-checked mini-lessons; all analysis stays local. */
(()=>{'use strict';
if(typeof ChessEngine==='undefined'||!document.getElementById('leh-chess'))return;
const E=ChessEngine,$=id=>document.getElementById(id),root=$('leh-chess');
const tasks=[
 {id:'mate-white',title:'Mate in one · White',prefix:['e2e4','e7e5','d1h5','b8c6','f1c4','g8f6'],answer:'h5f7',hint:'Find a forcing queen move against f7. Verify that every escape and defense fails.',why:'Qxf7# attacks the black king with protection from the bishop on c4. The king cannot capture the queen on f7.'},
 {id:'mate-black',title:'Mate in one · Black',prefix:['f2f3','e7e5','g2g4'],answer:'d8h4',hint:'Look at the weakened diagonal toward White’s king.',why:'Qh4# uses the open e1–h4 diagonal. White’s king has no legal answer to the check.'},
 {id:'en-passant',title:'An unusual pawn capture',prefix:['e2e4','a7a6','e4e5','d7d5'],answer:'e5d6',hint:'The black pawn has just moved two squares; there is one special capture available immediately.',why:'exd6 e.p. captures the pawn that advanced from d7 to d5. En passant is legal only on the immediately following turn.'},
 {id:'castle',title:'Castle to safety',prefix:['e2e4','e7e5','g1f3','b8c6','f1c4','g8f6'],answer:'e1g1',hint:'The king can move two squares toward a rook if castling conditions are met.',why:'O-O is kingside castling: the king moves e1→g1 and the rook moves h1→f1. Neither king transit square may be attacked.'},
 {id:'fork',title:'Knight fork · White',fen:'r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1',answer:'d5c7',hint:'Look for a knight check that also attacks the rook on a8.',why:'Nc7+ gives check to the king on e8 while attacking the rook on a8. This is a fork, though the later outcome depends on Black’s reply.'}
];
function position(task){let s=E.fromFen(task.fen||E.START);for(const uci of task.prefix||[]){const m=E.makeMove(s,uci);if(!m)throw Error('Invalid practice line: '+task.id+' '+uci);s=E.apply(s,m);}const move=E.makeMove(s,task.answer);if(!move)throw Error('Invalid practice answer: '+task.id);return {start:E.toFen(s),expected:E.toFen(E.apply(s,move)),san:E.san(s,move)};}
const computed=tasks.map(t=>({...t,...position(t)}));let active=null,completed=new Set(),attempted=false;
const panel=document.createElement('section');panel.className='panel cl-practice';panel.setAttribute('aria-labelledby','cl-practice-title');
panel.innerHTML=`<div class="panel-top"><h2 id="cl-practice-title">Practice a position</h2><span class="pill" id="cl-practice-progress">0 / 5</span></div><p class="small">Five short chess challenges with real legal positions. Load one, play the move on the board, and receive an explanation. No account or score tracking.</p><label for="cl-practice-select">Choose a challenge</label><select id="cl-practice-select">${computed.map((t,i)=>`<option value="${i}">${t.title}</option>`).join('')}</select><div class="actions"><button type="button" id="cl-practice-load">Load challenge</button><button type="button" id="cl-practice-hint" class="subtle">Hint</button><button type="button" id="cl-practice-reveal" class="subtle">Reveal answer</button></div><p id="cl-practice-message" role="status" aria-live="polite" class="practice-result">Select a challenge, then play on the board.</p><button type="button" id="cl-practice-next" hidden>Next challenge →</button><p class="small">Practice positions are illustrations, not chess-engine evaluations of the best continuation.</p>`;
const aside=root.querySelector('.aside-stack');aside?.insertBefore(panel,aside.firstChild);
const msg=$('cl-practice-message'),progress=$('cl-practice-progress');
function updateProgress(){progress.textContent=completed.size+' / '+computed.length+' completed';}
function load(){const task=computed[Number($('cl-practice-select').value)];active=task;attempted=false;$('cl-practice-next').hidden=true;$('cl-mode').value='local';$('cl-mode').dispatchEvent(new Event('change',{bubbles:true}));$('cl-fen').value=task.start;$('cl-load-fen').click();msg.textContent='Challenge loaded: '+task.title+'. Select a piece and make your move.';updateProgress();}
function examine(){if(!active)return;const current=$('cl-fen').value.trim();if(current===active.start){if(attempted){msg.textContent='Back at the starting position. Try again.';}return;}
 if(current===active.expected){completed.add(active.id);msg.textContent='Correct — '+active.san+'. '+active.why;$('cl-practice-next').hidden=false;updateProgress();}
 else if(!attempted){attempted=true;msg.textContent='That is a legal move, but not the target of this challenge. Use Undo, then try the hint.';}
}
$('cl-practice-load').addEventListener('click',load);
$('cl-practice-hint').addEventListener('click',()=>{if(!active){msg.textContent='Load a challenge first.';return;}msg.textContent=active.hint;});
$('cl-practice-reveal').addEventListener('click',()=>{if(!active){msg.textContent='Load a challenge first.';return;}msg.textContent='Example: '+active.san+'. '+active.why+' Use Undo or reload the challenge to try it yourself.';});
$('cl-practice-next').addEventListener('click',()=>{$('cl-practice-select').value=String((computed.findIndex(x=>x.id===active?.id)+1)%computed.length);load();});
$('cl-practice-select').addEventListener('change',()=>{active=null;msg.textContent='Press Load challenge to start this position.';$('cl-practice-next').hidden=true;});
const moves=$('cl-moves');if(moves)new MutationObserver(examine).observe(moves,{childList:true});
updateProgress();
})();
