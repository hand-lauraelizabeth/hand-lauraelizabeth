/* Chess Lab extension: inspectable position coach and FEN-aware PGN. */
(()=>{'use strict';
if(typeof ChessEngine==='undefined'||!document.getElementById('leh-chess'))return;
const E=ChessEngine,$=id=>document.getElementById(id);
E.pgn=function(states,moves){
  if(!states.length)return '';
  const initial=E.toFen(states[0]);
  const header=initial===E.START?'':'[SetUp "1"]\n[FEN "'+initial+'"]\n\n';
  const movesText=moves.map((move,i)=>{
    const state=states[i],number=state.t===1?state.full+'. ':i===0?state.full+'... ':'';
    return number+E.san(state,move);
  }).join(' ');
  const end=E.status(states),result=end.done?end.text.includes('checkmate')?(states.at(-1).t===1?'0-1':'1-0'):'1/2-1/2':'*';
  return header+(movesText?movesText+' ':'')+result;
};
const panel=document.createElement('section');panel.className='panel cl-coach';
panel.setAttribute('aria-labelledby','cl-coach-title');
panel.innerHTML='<div class="panel-top"><h2 id="cl-coach-title">Position coach</h2><button id="cl-analyze" type="button" class="subtle">Refresh analysis</button></div><p class="small">Rule-derived opportunities, not an optimal-move or rated-engine claim.</p><div id="cl-coach-summary" role="status" aria-live="polite"></div><p id="cl-coach-candidates" class="small"></p><p id="cl-coach-threats" class="small"></p><details><summary>How is this calculated?</summary><p class="small">The legal-move engine identifies checks and captures. An attacked piece may also be defended. Material points exclude kings and do not measure positional compensation. All analysis runs in the browser.</p></details>';
document.querySelector('#leh-chess .aside-stack')?.insertBefore(panel,document.querySelector('#leh-chess .aside-stack').children[1]);
const value={p:1,n:3,b:3,r:5,q:9,k:0},name={p:'pawn',n:'knight',b:'bishop',r:'rook',q:'queen'};
function analyze(){
 try{
  const s=E.fromFen($('cl-fen').value.trim()),lm=E.legal(s),who=s.t===1?'White':'Black',st=E.status([s]);
  let balance=0;
  for(let i=0;i<128;i++)if(E.on(i)&&s.b[i]!=='.')balance+=E.side(s.b[i])*value[s.b[i].toLowerCase()];
  const checks=[],captures=[],attacked=[];
  for(const m of lm){
   if(E.inCheck(E.apply(s,m)))checks.push(E.san(s,m));
   if(s.b[m[1]]!=='.'||m[3]==='ep')captures.push(E.san(s,m));
  }
  for(let i=0;i<128;i++)if(E.on(i)&&E.side(s.b[i])===s.t&&s.b[i].toLowerCase()!=='k'&&E.attacked(s,i,-s.t))attacked.push(name[s.b[i].toLowerCase()]+' on '+E.square(i));
  const material=balance===0?'material equal':(balance>0?'White':'Black')+' ahead '+Math.abs(balance)+' material points';
  $('cl-coach-summary').textContent=(st.done?st.text:who+' to move')+' · '+lm.length+' legal moves · '+material+'.';
  $('cl-coach-candidates').textContent=st.done?'Game over.':'Candidate checks: '+(checks.slice(0,4).join(', ')||'none')+' ('+checks.length+' total). Candidate captures: '+(captures.slice(0,4).join(', ')||'none')+' ('+captures.length+' total). These are not necessarily good moves.';
  $('cl-coach-threats').textContent=attacked.length?'Pieces currently under attack: '+attacked.slice(0,5).join(', ')+'. Attacked does not mean undefended.':'No non-king pieces of the player to move are currently under attack.';
 }catch(error){$('cl-coach-summary').textContent='Cannot analyze this FEN.';$('cl-coach-candidates').textContent=error.message;$('cl-coach-threats').textContent='';}
}
$('cl-analyze').addEventListener('click',analyze);
new MutationObserver(analyze).observe($('cl-moves'),{childList:true});
analyze();
})();