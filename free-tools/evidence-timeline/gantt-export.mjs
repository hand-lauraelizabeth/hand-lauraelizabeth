import {GANTT_TEMPLATE} from './gantt-template.mjs';
import {zipParts} from './zip-store.mjs';
import {timelineScale,calendarDay,isoDay,prettyDay,xmlText,shortLabel} from './timeline-visual.mjs';
const epoch=calendarDay('1899-12-31');
export function excelDate(iso) {return calendarDay(iso)-epoch+(iso>='1900-03-01'?1:0);}
export function columnName(index) {
  let value='';
  for(let n=index+1;n>0;n=Math.floor((n-1)/26)) value=String.fromCharCode(65+(n-1)%26)+value;
  return value;
}
function spreadsheetText(value) {
  // Escape literal OOXML escape sequences before encoding non-XML code units.
  return xmlText(String(value).replace(/_x[0-9a-f]{4}_/gi,match=>'_x005F_'+match.slice(1))
    .replace(/[\u0000-\u0008\u000b-\u001f\ufffe\uffff]|[\ud800-\udfff]/gu,char=>'_x'+char.charCodeAt(0).toString(16).toUpperCase().padStart(4,'0')+'_'));
}
function cell(ref,value,style,formula) {
  if(formula!==undefined) return `<x:c r="${ref}" s="${style}" t="str"><x:f>${xmlText(formula)}</x:f><x:v>${xmlText(value)}</x:v></x:c>`;
  if(typeof value==='number') return `<x:c r="${ref}" s="${style}"><x:v>${value}</x:v></x:c>`;
  return `<x:c r="${ref}" s="${style}" t="inlineStr"><x:is><x:t xml:space="preserve">${spreadsheetText(value)}</x:t></x:is></x:c>`;
}
const styleCache=new Map();
function styleOf(sheet,ref) {
  const key=sheet+ref;
  if(styleCache.has(key))return styleCache.get(key);
  const match=GANTT_TEMPLATE[sheet].match(new RegExp('<x:c r="'+ref+'" s="(\\d+)"'));
  if(!match)throw Error('Workbook design is missing a required style.');
  styleCache.set(key,match[1]);
  return match[1];
}
export function ganttParts(input,{scope='All entries',total=input.length,filters=''}={}) {
  const scale=timelineScale(input);
  if(!scale)throw Error('Choose a view with at least one entry before downloading.');
  const {rows,first,last,step,buckets}=scale;
  if(rows.some(row=>row.date<'1900-01-01'))throw Error('Excel Gantt dates must be on or after Jan 1, 1900. Use the visual timeline or JSON for earlier records.');
  const parts={...GANTT_TEMPLATE};
  const lastCol=columnName(3+buckets),lastRow=rows.length+8;
  for(const [path,isGantt] of [['xl/worksheets/sheet1.xml',true],['xl/worksheets/sheet2.xml',false]]) {
    const titleStyle=styleOf(path,'A2'),noteStyle=styleOf(path,'A3'),headStyle=styleOf(path,'A8');
    const output=[];
    const addRow=(row,cells,height=25)=>output.push(`<x:row r="${row}" ht="${height}" customHeight="1">${cells.join('')}</x:row>`);
    const notes=[isGantt?'Evidence timeline · Gantt':'Evidence timeline · Full entries',
      scope+' · '+rows.length+' of '+total+' entries'+(filters?' · '+filters:''),
      prettyDay(isoDay(first))+' – '+prettyDay(isoDay(last)),
      isGantt?'◆ Single-day milestone    ■ Supplied date range    Amber cells: editable dates':'Original descriptions, source references, groups, and review labels are retained below.',
      isGantt?'Edit Start / End to update bars within this range. Full descriptions and labels are on Entries.':'Expand row heights to read long descriptions. Editing this source copy does not change Gantt dates.',
      isGantt?'Each column spans '+step+' calendar day'+(step===1?'':'s')+'. Re-export to change the chart range.':'Sources: records supplied by the person preparing this timeline. Labels do not verify a source.'];
    notes.forEach((value,index)=>addRow(index+2,[cell('A'+(index+2),value,index===0?titleStyle:noteStyle)],index===0?30:index===1?40:25));
    const headers=isGantt?['Source reference','Description','Start','End']:['Source reference','Start','End (optional)','Full description','Review status','Entry type','Group','Date type'];
    const headerCells=headers.map((value,col)=>cell(columnName(col)+'8',value,headStyle));
    if(isGantt)for(let bucket=0;bucket<buckets;bucket++)headerCells.push(cell(columnName(bucket+4)+'8',excelDate(isoDay(first+bucket*step)),styleOf(path,'E8')));
    addRow(8,headerCells,32);
    rows.forEach((record,index)=>{
      const row=index+9,baseStyle=styleOf(path,index%2?'A10':'A9');
      const values=isGantt?[record.sourceId,shortLabel(record.claim,160),excelDate(record.date),excelDate(record.endDate||record.date)]:
        [record.sourceId,excelDate(record.date),record.endDate?excelDate(record.endDate):'',record.claim,record.status,record.kind,record.group,record.endDate&&record.endDate!==record.date?'Range':'Milestone'];
      const cells=values.map((value,col)=>cell(columnName(col)+row,value,
        (isGantt&&(col===2||col===3))?styleOf(path,'C9'):(!isGantt&&(col===1||col===2))?styleOf(path,'B9'):baseStyle));
      if(isGantt)for(let bucket=0;bucket<buckets;bucket++) {
        const col=columnName(bucket+4),start=first+bucket*step,end=Math.min(last,start+step-1);
        const endSerial=excelDate(isoDay(end)),startSerial=excelDate(isoDay(start));
        const active=calendarDay(record.date)<=end&&calendarDay(record.endDate||record.date)>=start;
        const symbol=active?(record.date===(record.endDate||record.date)?'◆':'■'):'';
        const formula=`IF(AND(ISNUMBER($C${row}),ISNUMBER($D${row}),$D${row}>=$C${row},$C${row}<=${col}$8+${endSerial-startSerial},$D${row}>=${col}$8),IF($C${row}=$D${row},"◆","■"),"")`;
        cells.push(cell(col+row,symbol,styleOf(path,index%2?'E10':'E9'),formula));
      }
      addRow(row,cells,54);
    });
    parts[path]=parts[path].replace(/<x:sheetData>[\s\S]*?<\/x:sheetData>/,`<x:sheetData>${output.join('')}</x:sheetData>`)
      .replace(/sqref="E9:AB10"/,`sqref="E9:${lastCol}${lastRow}"`)
      .replace(/<x:pageMargins/,`<x:autoFilter ref="A8:${isGantt?'D':'H'}${lastRow}"/><x:pageMargins`);
    // autoFilter belongs before mergeCells and conditional formatting in OOXML.
    parts[path]=parts[path].replace(/<x:autoFilter[^>]*\/>/,'').replace('</x:sheetData>',`</x:sheetData><x:autoFilter ref="A8:${isGantt?'D':'H'}${lastRow}"/>`);
    parts[path]=parts[path].replace('</x:worksheet>','<x:pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/></x:worksheet>');
  }
  parts['xl/sharedStrings.xml']='<?xml version="1.0" encoding="utf-8"?><x:sst xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="0" uniqueCount="0"/>';
  parts['xl/workbook.xml']=parts['xl/workbook.xml'].replace('</x:workbook>','<x:calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/></x:workbook>');
  return parts;
}
export function exportGantt(input,options={}) {return zipParts(ganttParts(input,options));}
