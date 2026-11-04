// Browser-local planning model; date-only, whole-cent arithmetic, no bank connections.
const DAY=86400000;
export const LIMITS=Object.freeze({days:366,events:200,maxAbsCents:1_000_000_000_000});
export function dateUTC(s){
  if(typeof s!=='string'||!/^(\d{4})-(\d{2})-(\d{2})$/.test(s)) throw Error('Use a YYYY-MM-DD date.');
  const [y,m,d]=s.split('-').map(Number);
  if(y<1900||y>2100)throw Error('Date must be within 1900–2100.');
  const v=new Date(Date.UTC(y,m-1,d));
  if(v.getUTCFullYear()!==y||v.getUTCMonth()!==m-1||v.getUTCDate()!==d) throw Error('Invalid calendar date.');
  return v.getTime();
}
export function dateString(t){return new Date(t).toISOString().slice(0,10)}
export function addDays(s,n){if(!Number.isSafeInteger(n)||Math.abs(n)>366) throw Error('Invalid day offset.');return dateString(dateUTC(s)+n*DAY)}
export function parseCents(raw){
  if(typeof raw!=='string'||!/^[-+]?(?:0|[1-9]\d{0,9})(?:\.\d{1,2})?$/.test(raw.trim()))throw Error('Enter a decimal amount with up to two cents.');
  const v=raw.trim(),negative=v.startsWith('-'),parts=v.replace(/^[-+]/,'').split('.');
  const n=Number(parts[0])*100+Number((parts[1]||'').padEnd(2,'0'));
  if(!Number.isSafeInteger(n)||n>LIMITS.maxAbsCents)throw Error('Amount exceeds limit.');
  return negative?-n:n;
}
export function formatCents(c){if(!Number.isSafeInteger(c))throw Error('Invalid cents.');return `${c<0?'-':''}${Math.floor(Math.abs(c)/100)}.${String(Math.abs(c)%100).padStart(2,'0')}`}
function monthlyDate(start,months){
  const [y,m,d]=start.split('-').map(Number),zero=(y*12+m-1)+months;
  const year=Math.floor(zero/12),month=zero%12+1;
  const last=new Date(Date.UTC(year,month,0)).getUTCDate();
  return dateString(Date.UTC(year,month-1,Math.min(d,last)));
}
export function occurrences(event,from,to){
  const first=dateUTC(event.date),begin=dateUTC(from),end=dateUTC(to),out=[];
  if(!['once','weekly','monthly'].includes(event.repeat))throw Error('Invalid repeat value.');
  if(event.repeat==='once'){if(first>=begin&&first<=end)out.push(event.date);return out}
  if(event.repeat==='weekly'){
    let step=Math.max(0,Math.ceil((begin-first)/(7*DAY)));
    for(let t=first+step*7*DAY;t<=end;t+=7*DAY){if(t>=begin)out.push(dateString(t));}
  }else{
    const startDate=new Date(first),beginDate=new Date(begin);
    let month=Math.max(0,(beginDate.getUTCFullYear()-startDate.getUTCFullYear())*12+beginDate.getUTCMonth()-startDate.getUTCMonth()-1);
    for(let s=monthlyDate(event.date,month);Date.parse(s)<=end;s=monthlyDate(event.date,++month)){
      if(Date.parse(s)>=begin)out.push(s);
    }
  }
  return out;
}
export function project({start,end,openingCents,events,shiftId=null,shiftDays=0}){
  const a=dateUTC(start),b=dateUTC(end),span=(b-a)/DAY+1;
  if(span<1||span>LIMITS.days)throw Error('Choose 1–366 days.');
  if(!Number.isSafeInteger(openingCents)||Math.abs(openingCents)>LIMITS.maxAbsCents)throw Error('Invalid opening balance.');
  if(!Array.isArray(events)||events.length>LIMITS.events)throw Error('Too many events.');
  if(!Number.isSafeInteger(shiftDays)||Math.abs(shiftDays)>60)throw Error('Shift days must be a whole number between -60 and 60.');
  if(shiftId===null&&shiftDays!==0)throw Error('Choose an event to shift, or set shift days to 0.');
  const ids=new Set(),byDate=new Map();
  for(const e of events){
    if(typeof e.id!=='string'||!e.id.trim()||ids.has(e.id))throw Error('Event IDs must be unique and nonempty.');
    ids.add(e.id);
    if(typeof e.label!=='string'||!e.label.trim()||e.label.length>120)throw Error('Invalid event label.');
    if(!Number.isSafeInteger(e.cents)||Math.abs(e.cents)>LIMITS.maxAbsCents)throw Error('Invalid event amount.');
    dateUTC(e.date);
    // Move individual occurrences without changing the recurring series anchor.
    // A January 31 bill shifted one day must not become a bill due on the first
    // of every subsequent month.
    const moved=e.id===shiftId&&shiftDays!==0;
    const sourceFrom=moved?addDays(start,-shiftDays):start;
    const sourceTo=moved?addDays(end,-shiftDays):end;
    const from=sourceFrom<'1900-01-01'?'1900-01-01':sourceFrom;
    const to=sourceTo>'2100-12-31'?'2100-12-31':sourceTo;
    if(from>to)continue;
    for(const originalDay of occurrences(e,from,to)){
      const day=moved?addDays(originalDay,shiftDays):originalDay;
      if(!byDate.has(day))byDate.set(day,[]);
      byDate.get(day).push({id:e.id,label:e.label,cents:e.cents});
    }
  }
  if(shiftId!==null&&!ids.has(shiftId))throw Error('Scenario event not found.');
  // The opening amount is before this window's first end-of-day netting.
  // A reported minimum must be an actual projected daily closing balance.
  let balance=openingCents,minimum=null,minDate=null;
  const days=[];
  for(let t=a;t<=b;t+=DAY){
    const date=dateString(t),items=byDate.get(date)||[];
    const change=items.reduce((n,e)=>n+e.cents,0);
    balance+=change;
    if(!Number.isSafeInteger(balance)||Math.abs(balance)>LIMITS.maxAbsCents)throw Error('Projected balance exceeds limit.');
    if(minimum===null||balance<minimum){minimum=balance;minDate=date;}
    days.push({date,changeCents:change,balanceCents:balance,events:items});
  }
  return {days,minimumCents:minimum,minimumDate:minDate,minimumBasis:'projected-end-of-day',endingCents:balance,openingCents,assumption:'End-of-day netting only; actual settlement timing, fees, and availability are not modeled.'};
}
// Defensive spreadsheet export: textual IDs/labels are escaped, not treated as spreadsheet formulas.
export function csvCell(value,numeric=false){const s=String(value);if(numeric&&/^-?\d+\.\d{2}$/.test(s))return s;const guarded=/^[\s\uFEFF]*[=+@\-\t\r＝＋－＠]/u.test(s)?"'"+s:s;return '"'+guarded.replaceAll('"','""')+'"'}
export function exportCSV(result){
  const rows=[['Date','Change (USD)','End-of-day balance (USD)','Event IDs','Event labels']];
  for(const day of result.days)rows.push([day.date,formatCents(day.changeCents),formatCents(day.balanceCents),day.events.map(e=>e.id).join(' | '),day.events.map(e=>e.label).join(' | ')]);
  return rows.map((row,i)=>row.map((value,j)=>csvCell(value,i>0&&(j===1||j===2))).join(',')).join('\r\n')+'\r\n';
}


// CSV is a lossy spreadsheet interchange format. Reject formula-like text in
// the user-facing CSV path; provide a lossless JSON alternative instead.
// The historical exportCSV function remains for independent legacy regression
// fixtures, but the interface uses exportSafeCSV exclusively.
export function csvExportRisk(result){
  if(!result||!Array.isArray(result.days))throw Error('Invalid projection for export.');
  // Refuse control bytes that can be dropped, reinterpreted, or split by
  // spreadsheet importers. Preserve the exact text through JSON instead.
  const unsupportedControl=/[\u0000-\u0009\u000B\u000C\u000E-\u001F\u007F-\u009F\u2028\u2029]/u;
  // Spreadsheet reopen/resave can change CSV quoting. Conservatively reject
  // formula text after separators/quotes; lossless JSON remains available.
  const separatorFormula=/[,;"'][\p{White_Space}\p{Default_Ignorable_Code_Point}]*[-=+@＝＋＠－]/u;
  for(const day of result.days){
    for(const event of day.events){
      for(const field of ['id','label']){
        const value=String(event[field]);
        if(/^[\p{White_Space}\p{Default_Ignorable_Code_Point}]*[-=+@＝＋＠－]/u.test(value)||
           /^[\t\r\n]/u.test(value)||
           /[\r\n][\p{White_Space}\p{Default_Ignorable_Code_Point}]*[-=+@＝＋＠－]/u.test(value)||
           /[\u202A-\u202E\u2066-\u2069]/u.test(value)||
           unsupportedControl.test(value)||separatorFormula.test(value)){
          return {field,eventId:event.id,reason:'formula-like text, invisible direction controls or unsupported control characters'};
        }
      }
    }
  }
  return null;
}
export function exportSafeCSV(result){
  const risk=csvExportRisk(result);
  if(risk)throw Error('CSV export blocked: '+risk.field+' contains '+risk.reason+'. Export lossless JSON instead.');
  return exportCSV(result);
}
export function exportJSON(result){
  if(!result||!Array.isArray(result.days))throw Error('Invalid projection for export.');
  return JSON.stringify({schema:'cash-flow-scenario/v1',...result},null,2)+'\n';
}
