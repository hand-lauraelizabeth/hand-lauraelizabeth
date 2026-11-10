import {normalizeExact} from './exact-core.mjs';
const day=86400000;
const dateFormat=new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
export function xmlText(value) {
  return String(value).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffe\uffff]|[\ud800-\udfff]/gu,char=>'\\u'+char.charCodeAt(0).toString(16).padStart(4,'0'))
    .replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[char]));
}
export function shortLabel(value,limit=52) {
  const chars=Array.from(value.replace(/\s+/g,' '));
  return chars.length>limit?chars.slice(0,limit-1).join('')+'…':chars.join('');
}
export function calendarDay(iso) {return Math.floor(Date.parse(iso+'T00:00:00Z')/day);}
export function isoDay(value) {return new Date(value*day).toISOString().slice(0,10);}
export function prettyDay(iso) {return dateFormat.format(new Date(iso+'T00:00:00Z'));}
export function timelineScale(input) {
  const rows=normalizeExact(input);
  if(!rows.length) return null;
  const first=calendarDay(rows[0].date);
  const last=Math.max(...rows.map(row=>calendarDay(row.endDate||row.date)));
  const days=last-first+1;
  const step=Math.max(1,Math.ceil(days/24));
  return {rows,first,last,days,step,buckets:Math.ceil(days/step)};
}
export function timelineSVG(input,{scope='All entries',total=input.length,filters='',offset=0,limit=input.length}={}) {
  const scale=timelineScale(input);
  if(!scale) throw Error('Add an entry or choose a view with matching entries first.');
  const {rows,first,last}=scale;
  const shown=rows.slice(offset,offset+limit);
  const width=1120,left=365,right=1070,top=190,rowHeight=68,height=top+shown.length*rowHeight+70;
  const x=value=>left+(calendarDay(value)-first)/Math.max(1,last-first)*(right-left);
  const endY=top+shown.length*rowHeight;
  const parts=[`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="timeline-chart-title timeline-chart-desc">`,
    '<title id="timeline-chart-title">Evidence timeline</title>',
    `<desc id="timeline-chart-desc">${xmlText(scope)}. ${rows.length} of ${total} entries. ${xmlText(prettyDay(isoDay(first))+' to '+prettyDay(isoDay(last)))}. Diamonds mark single-day entries; bars show supplied start and end dates. Descriptions are shortened. ${xmlText(filters)}</desc>`,
    `<rect width="${width}" height="${height}" rx="18" fill="#FAF9F4"/>`,
    '<g font-family="Arial, sans-serif" fill="#223D33">',
    '<text x="28" y="40" font-size="25" font-weight="bold">Evidence timeline</text>',
    `<text x="28" y="69" font-size="14">${xmlText(scope)} · ${rows.length} of ${total} entries · ${xmlText(prettyDay(isoDay(first))+' – '+prettyDay(isoDay(last)))}</text>`,
    '<text x="28" y="97" font-size="14">◆ Single-day milestone    ▰ Supplied date range</text>',
    `<text x="28" y="122" font-size="13">${xmlText(shortLabel(filters||'Entries and review labels supplied by the person preparing this timeline.',145))}</text>`,
    `<text x="28" y="148" font-size="13">${offset||shown.length<rows.length?'Preview: entries '+(offset+1)+'–'+(offset+shown.length)+' of '+rows.length+'. ':''}Descriptions shortened; keep the full entries with your visual.</text>`];
  const ticks=Math.min(4,last-first);
  for(let tick=0;tick<=ticks;tick++) {
    const value=first+Math.round((last-first)*(ticks?tick/ticks:0));
    const pos=x(isoDay(value));
    parts.push(`<line x1="${pos}" y1="${top-12}" x2="${pos}" y2="${endY}" stroke="#DDE5DC"/>`,
      `<text x="${pos}" y="${top-22}" font-size="12" text-anchor="${tick===0?'start':tick===ticks?'end':'middle'}">${xmlText(prettyDay(isoDay(value)))}</text>`);
  }
  shown.forEach((row,index)=>{
    const y=top+index*rowHeight;
    const pos=x(row.date),end=x(row.endDate||row.date),mid=y+24;
    parts.push(`<g><title>${xmlText(row.sourceId+' | '+row.date+(row.endDate?' – '+row.endDate:'')+' | '+row.claim+' | '+row.status+' | '+row.kind+' | '+row.group)}</title>`,
      `<rect x="16" y="${y}" width="1088" height="62" rx="6" fill="${index%2?'#FFFFFF':'#F0F4ED'}"/>`,
      `<text x="28" y="${y+23}" font-size="14" font-weight="bold">${xmlText(shortLabel(row.claim,43))}</text>`,
      `<text x="28" y="${y+45}" font-size="12" fill="#53675A">${xmlText(shortLabel(row.sourceId,44))}</text>`);
    if(row.endDate&&row.endDate!==row.date) parts.push(`<rect x="${pos}" y="${mid-8}" width="${Math.max(3,end-pos)}" height="16" rx="5" fill="#377B5D"/>`);
    else parts.push(`<path d="M ${pos} ${mid-8} l 8 8 -8 8 -8 -8 Z" fill="#755180"/>`);
    parts.push('</g>');
  });
  parts.push(`<text x="28" y="${height-25}" font-size="12" fill="#53675A">Calendar dates only. The tool organizes supplied records; it does not verify events or sources.</text></g></svg>`);
  return parts.join('\n');
}
