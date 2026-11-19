/* Chess Lab — dependency-free 0x88 rules engine. Game state is immutable. */
const ChessEngine = (() => {
  'use strict';
  const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const DIR = {n:[-33,-31,-18,-14,14,18,31,33],b:[-17,-15,15,17],r:[-16,-1,1,16],q:[-17,-16,-15,-1,1,15,16,17],k:[-17,-16,-15,-1,1,15,16,17]};
  const PIECE = {p:100,n:320,b:330,r:500,q:900,k:0};
  const on = x => x>=0 && x<128 && !(x&0x88);
  const side = p => !p || p==='.'?0:p===p.toUpperCase()?1:-1;
  const square = i => 'abcdefgh'[i&7]+(8-(i>>4));
  const index = s => /\b[a-h][1-8]\b/.test(s) ? (8-Number(s[1]))*16+'abcdefgh'.indexOf(s[0]) : -1;
  const id = m => square(m[0])+square(m[1])+(m[2]||'');
  function fromFen(fen) {
    const [placement,active,rights='-',enPassant='-',half='0',full='1'] = String(fen).trim().split(/\s+/);
    const rows=placement?.split('/'); const b=Array(128).fill('.');
    if(rows?.length!==8 || !['w','b'].includes(active) || !/^(-|K?Q?k?q?)$/.test(rights) || !/^(-|[a-h][36])$/.test(enPassant)) throw Error('Invalid FEN fields.');
    rows.forEach((row,r)=>{let c=0;for(const p of row){if(/[1-8]/.test(p)){c+=Number(p);}else{if(!/[kqrbnpKQRBNP]/.test(p)||c>=8)throw Error('Invalid piece placement.');b[r*16+c++]=p;}}if(c!==8)throw Error('Invalid FEN rank.');});
    if(b.filter(p=>p==='K').length!==1||b.filter(p=>p==='k').length!==1)throw Error('Exactly one king per color required.');
    const h=Number(half),f=Number(full);if(!Number.isSafeInteger(h)||h<0||!Number.isSafeInteger(f)||f<1)throw Error('Invalid move counters.');
    const c=(rights.includes('K')?1:0)|(rights.includes('Q')?2:0)|(rights.includes('k')?4:0)|(rights.includes('q')?8:0);
    return {b,t:active==='w'?1:-1,c,ep:enPassant==='-'?-1:index(enPassant),half:h,full:f};
  }
  function toFen(s){const rows=[];for(let r=0;r<8;r++){let row='',empty=0;for(let f=0;f<8;f++){const p=s.b[r*16+f];if(p==='.')empty++;else{if(empty)row+=empty;empty=0;row+=p;}}if(empty)row+=empty;rows.push(row);}const rights=(s.c&1?'K':'')+(s.c&2?'Q':'')+(s.c&4?'k':'')+(s.c&8?'q':'');return [rows.join('/'),s.t===1?'w':'b',rights||'-',s.ep===-1?'-':square(s.ep),s.half,s.full].join(' ');}
  function attacked(s,target,by){
    for(let f=0;f<128;f++){if(!on(f)||side(s.b[f])!==by)continue;
      const p=s.b[f].toLowerCase();if(p==='p'){if(target===f-16*by-1||target===f-16*by+1)return true;continue;}
      for(const d of DIR[p])for(let t=f+d;on(t);t+=d){if(t===target)return true;if(s.b[t]!=='.'||p==='n'||p==='k')break;}
    }return false;
  }
  const inCheck=(s,color=s.t)=>attacked(s,s.b.indexOf(color===1?'K':'k'),-color);
  function apply(s,m){const [f,t,prom,flag='']=m,b=s.b.slice(),p=b[f],captured=b[t];let rights=s.c;
    b[f]='.';b[t]=prom?(s.t===1?prom.toUpperCase():prom):p;
    if(flag==='ep')b[t+16*s.t]='.';
    if(flag==='castle'){const rf=t>f?f+3:f-4,rt=t>f?f+1:f-1;b[rt]=b[rf];b[rf]='.';}
    if(p==='K')rights&=~3;if(p==='k')rights&=~12;
    const rookRights={119:1,112:2,7:4,0:8};
    if(p.toLowerCase()==='r')rights&=~(rookRights[f]||0);
    if(captured.toLowerCase()==='r')rights&=~(rookRights[t]||0);
    return {b,t:-s.t,c:rights,ep:p.toLowerCase()==='p'&&Math.abs(t-f)===32?(t+f)/2:-1,half:p.toLowerCase()==='p'||captured!=='.'||flag==='ep'?0:s.half+1,full:s.full+(s.t===-1?1:0)};
  }
  function pseudo(s){const out=[];for(let f=0;f<128;f++){
    if(!on(f)||side(s.b[f])!==s.t)continue;const p=s.b[f].toLowerCase();
    const add=(t,flag='')=>{if(s.b[t].toLowerCase()==='k')return;if(p==='p'&&((t>>4)===0||(t>>4)===7)){for(const prom of ['q','r','b','n'])out.push([f,t,prom,flag]);}else out.push([f,t,'',flag]);};
    if(p==='p'){const t=f-16*s.t;if(on(t)&&s.b[t]==='.'){add(t);const u=t-16*s.t;if((f>>4)===(s.t===1?6:1)&&s.b[u]==='.')add(u);}for(const d of [-1,1]){const u=t+d;if(!on(u))continue;if(side(s.b[u])===-s.t)add(u);else if(u===s.ep&&s.b[u]==='.'&&s.b[u+16*s.t]===(s.t===1?'p':'P'))add(u,'ep');}}
    else{for(const d of DIR[p])for(let t=f+d;on(t);t+=d){if(side(s.b[t])===s.t)break;add(t);if(s.b[t]!=='.'||p==='n'||p==='k')break;}
      const home=s.t===1?116:4,rook=s.t===1?'R':'r',bits=s.t===1?[1,2]:[4,8];
      if(p==='k'&&f===home&&!inCheck(s)){
        if((s.c&bits[0])&&s.b[f+3]===rook&&s.b[f+1]==='.'&&s.b[f+2]==='.'&&!attacked(s,f+1,-s.t)&&!attacked(s,f+2,-s.t))add(f+2,'castle');
        if((s.c&bits[1])&&s.b[f-4]===rook&&s.b[f-1]==='.'&&s.b[f-2]==='.'&&s.b[f-3]==='.'&&!attacked(s,f-1,-s.t)&&!attacked(s,f-2,-s.t))add(f-2,'castle');
      }
    }
  }return out;}
  const legal=s=>pseudo(s).filter(m=>!inCheck(apply(s,m),s.t));
  function san(s,m){const [f,t,prom,flag]=m,p=s.b[f].toUpperCase(),capture=s.b[t]!=='.'||flag==='ep';let result='';
    if(flag==='castle')result=t>f?'O-O':'O-O-O';else{
      if(p!=='P'){result=p;const others=legal(s).filter(x=>x[0]!==f&&x[1]===t&&s.b[x[0]]===s.b[f]);if(others.length)result+=!others.some(x=>(x[0]&7)===(f&7))?square(f)[0]:!others.some(x=>(x[0]>>4)===(f>>4))?square(f)[1]:square(f);}
      else if(capture)result=square(f)[0];result+=(capture?'x':'')+square(t)+(prom?'='+prom.toUpperCase():'');
    }const next=apply(s,m);return result+(inCheck(next)?legal(next).length?'+':'#':'');
  }
  function positionKey(s){const effectiveEp=s.ep!==-1&&legal(s).some(m=>m[3]==='ep')?s.ep:-1;return s.b.join('')+':'+s.t+':'+s.c+':'+effectiveEp;}
  function insufficient(s){const p=[];for(let i=0;i<128;i++)if(on(i)&&s.b[i]!=='.'&&s.b[i].toLowerCase()!=='k')p.push([s.b[i].toLowerCase(),((i>>4)+(i&7))%2]);return p.length===0||(p.length===1&&['b','n'].includes(p[0][0]))||(p.every(x=>x[0]==='b')&&new Set(p.map(x=>x[1])).size===1);}
  function status(history){const s=history[history.length-1],moves=legal(s),check=inCheck(s),rep=history.filter(p=>positionKey(p)===positionKey(s)).length;
    if(!moves.length)return {done:true,text:check?(s.t===1?'Black':'White')+' wins by checkmate.':'Draw by stalemate.',claim:null};
    if(insufficient(s))return {done:true,text:'Draw: insufficient material.',claim:null};
    if(s.half>=150||rep>=5)return {done:true,text:s.half>=150?'Draw: 75-move rule.':'Draw: fivefold repetition.',claim:null};
    return {done:false,text:(s.t===1?'White':'Black')+' to move'+(check?' — check.':'.'),claim:rep>=3?'threefold repetition':s.half>=100?'50-move rule':null};
  }
  function evaluate(s){let score=0;for(let i=0;i<128;i++)if(on(i)&&s.b[i]!=='.'){const p=s.b[i],v=PIECE[p.toLowerCase()]||0,center=3.5-Math.abs((i&7)-3.5)+(3.5-Math.abs((i>>4)-3.5));score+=side(p)*(v+((p.toLowerCase()==='n'||p.toLowerCase()==='p')?center*4:0));}return score;}
  function choose(s,depth=2){const root=s.t;function seek(pos,n,alpha,beta){const lm=legal(pos);if(!lm.length)return inCheck(pos)?(pos.t===root?-1e6-n:1e6+n):0;if(n===0||insufficient(pos))return evaluate(pos)*root;const sorted=lm.sort((a,b)=>((pos.b[b[1]]==='.'?0:PIECE[pos.b[b[1]].toLowerCase()]||0)-(pos.b[a[1]]==='.'?0:PIECE[pos.b[a[1]].toLowerCase()]||0)));let best=pos.t===root?-Infinity:Infinity;for(const m of sorted){const v=seek(apply(pos,m),n-1,alpha,beta);if(pos.t===root){best=Math.max(best,v);alpha=Math.max(alpha,best);}else{best=Math.min(best,v);beta=Math.min(beta,best);}if(beta<=alpha)break;}return best;}
    const lm=legal(s);if(!lm.length)return null;let max=-Infinity,best=[];for(const m of lm){const score=seek(apply(s,m),Math.max(0,depth-1),-Infinity,Infinity);if(score>max){max=score;best=[m];}else if(score===max)best.push(m);}return best[Math.floor(Math.random()*best.length)];
  }
  function makeMove(s,uci){return legal(s).find(m=>id(m)===uci)||null;}
  function pgn(states,moves){return moves.map((m,i)=>(i%2===0?Math.floor(i/2)+1+'. ':'')+san(states[i],m)).join(' ').trim();}
  return {START,fromFen,toFen,on,side,square,index,id,attacked,inCheck,apply,legal,san,positionKey,status,choose,makeMove,pgn};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=ChessEngine;
